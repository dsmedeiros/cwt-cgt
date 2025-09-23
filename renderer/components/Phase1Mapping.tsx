import React, {
  ChangeEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import path from 'path';
import { cmdGateBRidgeFinder } from '../../electron/runner/commands';
import type { GateBRidgeFinderOptions } from '../../electron/runner/commands';
import { useEnvStore } from '../store/envSlice';
import { useRunsStore } from '../store/runsSlice';

interface ElectronBridge {
  env?: Record<string, unknown>;
  runs?: Record<string, unknown>;
  files?: Record<string, unknown>;
  ipcRenderer?: {
    invoke?: (channel: string, ...args: unknown[]) => Promise<unknown>;
    on?: (channel: string, listener: (...args: unknown[]) => void) => void;
    off?: (channel: string, listener: (...args: unknown[]) => void) => void;
    removeListener?: (channel: string, listener: (...args: unknown[]) => void) => void;
  };
}

declare global {
  interface Window {
    electron?: ElectronBridge;
    require?: (module: string) => unknown;
  }
}

const AXIS_OPTIONS: Array<{ label: string; value: [string, string] }> = [
  { label: 'ρ vs τ', value: ['rho', 'tau'] },
  { label: 'τ vs ζ', value: ['tau', 'zeta'] },
  { label: 'τ vs ζ_phase', value: ['tau', 'zeta_phase'] },
];

interface AxisRangeLimits {
  min: number;
  max: number;
  step: number;
}

const RANGE_DEFAULTS: Record<string, [number, number]> = {
  rho: [0.0, 3.0],
  tau: [0.5, 3.0],
  zeta: [0.0, 1.5],
  zeta_phase: [-0.5, 0.5],
};

const RANGE_LIMITS: Record<string, AxisRangeLimits> = {
  rho: { min: -1, max: 4, step: 0.1 },
  tau: { min: 0, max: 4, step: 0.05 },
  zeta: { min: 0, max: 2, step: 0.05 },
  zeta_phase: { min: -Math.PI, max: Math.PI, step: 0.05 },
};

const GRAPH_OPTIONS = ['ring3', 'random_regular', 'small_world', 'scale_free', 'modular'];

const HOTSPOTS_RELATIVE_PATH = path.join('artifacts', '_ui', 'hotspots.json');

function getElectron(): ElectronBridge | undefined {
  if (typeof window === 'undefined') {
    return undefined;
  }
  return window.electron;
}

function formatError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'string') {
    return error;
  }
  try {
    return JSON.stringify(error);
  } catch (serializationError) {
    return String(error);
  }
}

async function invokeIpc(channel: string, ...args: unknown[]): Promise<unknown> {
  const electron = getElectron();
  const ipc = electron?.ipcRenderer;
  if (ipc?.invoke) {
    return ipc.invoke(channel, ...args);
  }
  throw new Error('IPC renderer bridge is not available.');
}

async function callBridgeFunction(paths: string[][], channel: string, ...args: unknown[]): Promise<unknown | null> {
  const electron = getElectron();
  if (electron) {
    for (const segments of paths) {
      let target: unknown = electron;
      for (const segment of segments) {
        if (!target || typeof target !== 'object') {
          target = undefined;
          break;
        }
        target = (target as Record<string, unknown>)[segment];
      }
      if (typeof target === 'function') {
        return await Promise.resolve((target as (...inner: unknown[]) => unknown)(...args));
      }
    }
  }

  if (channel) {
    try {
      return await invokeIpc(channel, ...args);
    } catch (error) {
      if (paths.length) {
        throw error;
      }
    }
  }

  return null;
}

function pickString(value: unknown): string | null {
  if (typeof value === 'string') {
    return value;
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    return String(value);
  }
  return null;
}

function pickStrategy(value: unknown): 'module' | 'script' | null {
  const text = pickString(value)?.toLowerCase();
  if (!text) {
    return null;
  }
  if (text === 'module') {
    return 'module';
  }
  if (text === 'script' || text === 'direct') {
    return 'script';
  }
  return null;
}

interface EnvDetectResult {
  pythonExe: string | null;
  strategy: 'module' | 'script';
  repoRoot: string | null;
}

async function detectEnvironment(): Promise<EnvDetectResult> {
  const response =
    (await callBridgeFunction([
      ['env', 'detect'],
      ['env', 'autoDetect'],
      ['env', 'detectEnvironment'],
    ], 'env.detect')) ?? {};

  const source = (response && typeof response === 'object' ? response : {}) as Record<string, unknown>;

  const pythonCandidates = [
    pickString(source.pythonExe),
    pickString(source.python),
    pickString(source.exe),
    pickString(source.path),
    pickString(source.command),
  ].filter((candidate): candidate is string => typeof candidate === 'string' && candidate.length > 0);

  const pythonExe = pythonCandidates.length > 0 ? pythonCandidates[0] : null;

  let strategy = pickStrategy(source.strategy ?? source.mode ?? source.runnerMode);
  if (!strategy) {
    const moduleMode = typeof source.moduleMode === 'boolean' ? source.moduleMode : undefined;
    strategy = moduleMode ? 'module' : 'script';
  }

  const repoRoot =
    pickString(source.repoRoot ?? source.repo ?? source.root ?? source.cwd ?? source.projectRoot) ?? null;

  if (!pythonExe) {
    throw new Error('Unable to detect a Python interpreter.');
  }

  return {
    pythonExe,
    strategy: strategy ?? 'script',
    repoRoot,
  };
}

interface CreateRunOptions {
  phase?: string | null;
  experiment?: string | null;
  cmd: string;
  args?: string[];
  cwd?: string;
  seed?: number;
  paramsJson?: unknown;
  axes?: unknown;
  graph?: unknown;
  workdir?: string | null;
}

async function createRun(options: CreateRunOptions): Promise<string> {
  const response = await callBridgeFunction([
    ['runs', 'create'],
    ['runner', 'create'],
    ['run', 'create'],
  ], 'runs.create', options);

  const runId = pickString(response);
  if (!runId) {
    throw new Error('Run creation did not return a run identifier.');
  }
  return runId;
}

let fsModulePromise: Promise<typeof import('fs')> | null = null;

async function getFsModule(): Promise<typeof import('fs') | null> {
  if (!fsModulePromise) {
    try {
      fsModulePromise = import('fs');
    } catch (error) {
      fsModulePromise = Promise.resolve(null as unknown as typeof import('fs'));
    }
  }

  try {
    const module = await fsModulePromise;
    return module;
  } catch (error) {
    return null;
  }
}

async function readTextFile(filePath: string): Promise<string | null> {
  const fs = await getFsModule();
  if (fs?.promises?.readFile) {
    try {
      return await fs.promises.readFile(filePath, 'utf8');
    } catch (error) {
      // Continue to IPC fallback.
    }
  }

  const result = await callBridgeFunction([
    ['files', 'readText'],
    ['files', 'readFile'],
  ], 'files.readText', filePath);

  if (typeof result === 'string') {
    return result;
  }

  if (result instanceof Uint8Array) {
    try {
      return new TextDecoder().decode(result);
    } catch (error) {
      return null;
    }
  }

  return null;
}

async function readBinaryFile(filePath: string): Promise<Uint8Array | null> {
  const fs = await getFsModule();
  if (fs?.promises?.readFile) {
    try {
      const buffer = await fs.promises.readFile(filePath);
      return buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
    } catch (error) {
      // Continue to IPC fallback.
    }
  }

  const result = await callBridgeFunction([
    ['files', 'readBinary'],
    ['files', 'readBuffer'],
    ['files', 'readFile'],
  ], 'files.readBinary', filePath);

  if (result instanceof Uint8Array) {
    return result;
  }
  if (typeof Buffer !== 'undefined' && typeof Buffer.from === 'function' && typeof result === 'string') {
    return new Uint8Array(Buffer.from(result, 'base64'));
  }
  return null;
}

async function ensureDirectory(dirPath: string): Promise<void> {
  const fs = await getFsModule();
  if (fs?.promises?.mkdir) {
    try {
      await fs.promises.mkdir(dirPath, { recursive: true });
      return;
    } catch (error) {
      // Continue to IPC fallback.
    }
  }

  await callBridgeFunction([
    ['files', 'ensureDir'],
  ], 'files.ensureDir', dirPath);
}

async function writeJsonFile(filePath: string, data: unknown): Promise<void> {
  const fs = await getFsModule();
  const payload = JSON.stringify(data, null, 2);
  if (fs?.promises?.writeFile) {
    try {
      await fs.promises.writeFile(filePath, payload, 'utf8');
      return;
    } catch (error) {
      // Continue to IPC fallback.
    }
  }

  await callBridgeFunction([
    ['files', 'writeText'],
    ['files', 'writeFile'],
  ], 'files.writeText', filePath, payload);
}

interface MetricsGrid {
  axis0Name: string;
  axis1Name: string;
  axis0Values: number[];
  axis1Values: number[];
  omegaValues: number[][];
}

interface HotspotEntry {
  indices: [number, number];
  coordinates: Record<string, number>;
  omegaAbs: number;
}

interface GraphResult {
  graph: string;
  heatmapImage: string | null;
  metrics: MetricsGrid | null;
  hotspots: HotspotEntry[];
  topOmegaPath: string;
  metricsPath: string | null;
}

interface HotspotRecord {
  graph: string;
  axes: [string, string];
  coordinates: Record<string, number>;
  omegaAbs: number;
  sourcePath: string;
  addedAt: string;
}

function parseNumber(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number.parseFloat(trimmed);
  if (Number.isFinite(parsed)) {
    return parsed;
  }
  return null;
}

function parseMetricsCsv(csvText: string): MetricsGrid | null {
  const lines = csvText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  if (lines.length < 2) {
    return null;
  }

  const header = lines[0].split(',').map((token) => token.trim());
  if (header.length < 4) {
    return null;
  }

  const axis0Name = header[0];
  const axis1Name = header[1];
  const axis0Set = new Set<number>();
  const axis1Set = new Set<number>();
  const values = new Map<number, Map<number, number>>();

  for (let i = 1; i < lines.length; i += 1) {
    const tokens = lines[i].split(',');
    if (tokens.length < 4) {
      continue;
    }
    const axis0Value = parseNumber(tokens[0]);
    const axis1Value = parseNumber(tokens[1]);
    const omegaValue = parseNumber(tokens[3]);
    if (axis0Value == null || axis1Value == null || omegaValue == null) {
      continue;
    }

    axis0Set.add(axis0Value);
    axis1Set.add(axis1Value);

    if (!values.has(axis0Value)) {
      values.set(axis0Value, new Map());
    }
    values.get(axis0Value)?.set(axis1Value, omegaValue);
  }

  const axis0Values = Array.from(axis0Set).sort((a, b) => a - b);
  const axis1Values = Array.from(axis1Set).sort((a, b) => a - b);
  if (!axis0Values.length || !axis1Values.length) {
    return null;
  }

  const omegaValues: number[][] = axis0Values.map(() => axis1Values.map(() => NaN));
  for (let i = 0; i < axis0Values.length; i += 1) {
    const axis0Value = axis0Values[i];
    const rowMap = values.get(axis0Value);
    if (!rowMap) {
      continue;
    }
    for (let j = 0; j < axis1Values.length; j += 1) {
      const axis1Value = axis1Values[j];
      const omegaValue = rowMap.get(axis1Value);
      if (typeof omegaValue === 'number' && Number.isFinite(omegaValue)) {
        omegaValues[i][j] = omegaValue;
      }
    }
  }

  return {
    axis0Name,
    axis1Name,
    axis0Values,
    axis1Values,
    omegaValues,
  };
}

function buildDataUrl(buffer: Uint8Array, mimeType: string): string {
  let binary = '';
  for (let i = 0; i < buffer.length; i += 1) {
    binary += String.fromCharCode(buffer[i]);
  }
  if (typeof btoa === 'function') {
    return `data:${mimeType};base64,${btoa(binary)}`;
  }
  if (typeof Buffer !== 'undefined' && typeof Buffer.from === 'function') {
    return `data:${mimeType};base64,${Buffer.from(binary, 'binary').toString('base64')}`;
  }
  return '';
}

function formatNumber(value: number): string {
  if (!Number.isFinite(value)) {
    return '';
  }
  if (Math.abs(value) >= 100 || Math.abs(value) < 0.01) {
    return value.toExponential(2);
  }
  return value.toFixed(3);
}

type PlotlyModule = {
  react: (root: HTMLElement, data: unknown[], layout?: unknown, config?: unknown) => Promise<unknown>;
  purge?: (root: HTMLElement) => void;
};

let plotlyInstance: PlotlyModule | null = null;
let plotlyLoadPromise: Promise<PlotlyModule> | null = null;

async function ensurePlotly(): Promise<PlotlyModule | null> {
  if (plotlyInstance) {
    return plotlyInstance;
  }
  if (!plotlyLoadPromise) {
    plotlyLoadPromise = import('plotly.js-dist-min') as Promise<PlotlyModule>;
  }
  try {
    const module = await plotlyLoadPromise;
    const candidate = module as unknown as { default?: PlotlyModule };
    plotlyInstance = candidate?.default ?? (module as unknown as PlotlyModule);
    return plotlyInstance;
  } catch (error) {
    plotlyLoadPromise = null;
    return null;
  }
}

function AxisRangeControl({
  axis,
  label,
  range,
  onChange,
}: {
  axis: string;
  label: string;
  range: [number, number];
  onChange: (axis: string, range: [number, number]) => void;
}): JSX.Element {
  const limits = RANGE_LIMITS[axis] ?? { min: -10, max: 10, step: 0.1 };
  const [minValue, maxValue] = range;

  const handleMinChange = (event: ChangeEvent<HTMLInputElement>) => {
    const next = Number.parseFloat(event.target.value);
    if (Number.isNaN(next)) {
      return;
    }
    const clamped = Math.min(next, maxValue);
    onChange(axis, [clamped, maxValue]);
  };

  const handleMaxChange = (event: ChangeEvent<HTMLInputElement>) => {
    const next = Number.parseFloat(event.target.value);
    if (Number.isNaN(next)) {
      return;
    }
    const clamped = Math.max(next, minValue);
    onChange(axis, [minValue, clamped]);
  };

  return (
    <div className="range-control">
      <div className="range-label">{label}</div>
      <div className="range-inputs">
        <label>
          <span>Min</span>
          <input
            type="number"
            step={limits.step}
            min={limits.min}
            max={limits.max}
            value={minValue}
            onChange={handleMinChange}
          />
        </label>
        <input
          type="range"
          min={limits.min}
          max={limits.max}
          step={limits.step}
          value={minValue}
          onChange={handleMinChange}
        />
        <input
          type="range"
          min={limits.min}
          max={limits.max}
          step={limits.step}
          value={maxValue}
          onChange={handleMaxChange}
        />
        <label>
          <span>Max</span>
          <input
            type="number"
            step={limits.step}
            min={limits.min}
            max={limits.max}
            value={maxValue}
            onChange={handleMaxChange}
          />
        </label>
      </div>
    </div>
  );
}

function useHotspotFilePath(repoRoot: string | null): string {
  return useMemo(() => {
    if (repoRoot) {
      return path.join(repoRoot, HOTSPOTS_RELATIVE_PATH);
    }
    if (typeof process !== 'undefined' && typeof process.cwd === 'function') {
      return path.join(process.cwd(), HOTSPOTS_RELATIVE_PATH);
    }
    return HOTSPOTS_RELATIVE_PATH;
  }, [repoRoot]);
}

export default function Phase1Mapping(): JSX.Element {
  const repoRootFromStore = useEnvStore((state) => state.repoRoot);
  const runs = useRunsStore((state) => state.runs);
  const refreshRuns = useRunsStore((state) => state.refreshRuns);

  const [axes, setAxes] = useState<[string, string]>(AXIS_OPTIONS[0].value);
  const [ranges, setRanges] = useState<Record<string, [number, number]>>({ ...RANGE_DEFAULTS });
  const [gridSize, setGridSize] = useState<number>(21);
  const [bootstrap, setBootstrap] = useState<number>(256);
  const [topK, setTopK] = useState<number>(12);
  const [seed, setSeed] = useState<number>(7);
  const [selectedGraphs, setSelectedGraphs] = useState<Set<string>>(new Set(['ring3', 'random_regular']));

  const [isRunning, setIsRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [runOutputDir, setRunOutputDir] = useState<string | null>(null);
  const [detectedRepoRoot, setDetectedRepoRoot] = useState<string | null>(null);
  const [graphResults, setGraphResults] = useState<GraphResult[]>([]);
  const [selectedGraphKey, setSelectedGraphKey] = useState<string | null>(null);
  const [hotspotList, setHotspotList] = useState<HotspotRecord[]>([]);
  const [hotspotError, setHotspotError] = useState<string | null>(null);
  const [lastHotspotSaved, setLastHotspotSaved] = useState<string | null>(null);

  const plotContainerRef = useRef<HTMLDivElement | null>(null);
  const activeRun = useMemo(() => runs.find((run) => run.id === activeRunId) ?? null, [runs, activeRunId]);
  const repoRoot = detectedRepoRoot ?? repoRootFromStore ?? null;
  const hotspotFilePath = useHotspotFilePath(repoRoot);

  const selectedGraphResult = useMemo(
    () => graphResults.find((result) => result.graph === selectedGraphKey) ?? null,
    [graphResults, selectedGraphKey]
  );

  useEffect(() => {
    if (!graphResults.length) {
      setSelectedGraphKey(null);
      return;
    }

    setSelectedGraphKey((previous) => {
      if (previous && graphResults.some((result) => result.graph === previous)) {
        return previous;
      }
      return graphResults[0]?.graph ?? null;
    });
  }, [graphResults]);

  useEffect(() => {
    let cancelled = false;
    const loadHotspots = async () => {
      try {
        const directory = path.dirname(hotspotFilePath);
        await ensureDirectory(directory);
        const content = await readTextFile(hotspotFilePath);
        if (cancelled) {
          return;
        }
        if (!content) {
          setHotspotList([]);
          return;
        }
        const parsed = JSON.parse(content) as HotspotRecord[];
        if (Array.isArray(parsed)) {
          setHotspotList(parsed);
        } else {
          setHotspotList([]);
        }
      } catch (error) {
        if (!cancelled) {
          setHotspotError(formatError(error));
        }
      }
    };

    void loadHotspots();

    return () => {
      cancelled = true;
    };
  }, [hotspotFilePath]);

  useEffect(() => {
    if (!activeRunId) {
      return;
    }

    const refresh = () => {
      void refreshRuns();
    };

    refresh();

    const interval = window.setInterval(refresh, 5000);

    return () => {
      window.clearInterval(interval);
    };
  }, [activeRunId, refreshRuns]);

  const handleAxesChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    const option = AXIS_OPTIONS.find((item) => item.value.join(':') === value);
    if (option) {
      setAxes(option.value);
    }
  }, []);

  const handleRangeChange = useCallback((axis: string, rangeValue: [number, number]) => {
    setRanges((prev) => ({ ...prev, [axis]: rangeValue }));
  }, []);

  const handleGraphToggle = useCallback((graph: string) => {
    setSelectedGraphs((prev) => {
      const next = new Set(prev);
      if (next.has(graph)) {
        next.delete(graph);
      } else {
        next.add(graph);
      }
      return next;
    });
  }, []);

  const handleGraphResultSelect = useCallback((event: ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value;
    setSelectedGraphKey(value || null);
  }, []);

  const handleNumericChange = useCallback(
    (setter: (value: number) => void) =>
      (event: ChangeEvent<HTMLInputElement>) => {
        const value = Number.parseInt(event.target.value, 10);
        if (!Number.isNaN(value)) {
          setter(value);
        }
      },
    []
  );

  const loadGraphArtifacts = useCallback(
    async (outputDir: string, graphsToLoad: Iterable<string>): Promise<void> => {
      const results: GraphResult[] = [];
      for (const graph of graphsToLoad) {
        const graphDir = path.join(outputDir, graph);
        const topOmegaPath = path.join(graphDir, 'top_omega_tiles.json');
        const metricsPath = path.join(graphDir, 'metrics.csv');
        const heatmapPath = path.join(graphDir, 'omega_heatmap.png');

        const topOmegaText = await readTextFile(topOmegaPath);
        if (!topOmegaText) {
          continue;
        }

        let hotspots: HotspotEntry[] = [];
        try {
          const parsed = JSON.parse(topOmegaText) as {
            axes?: unknown;
            top_tiles?: unknown;
          };
          if (Array.isArray(parsed?.top_tiles)) {
            hotspots = (parsed.top_tiles as unknown[])
              .map((item) => {
                if (!item || typeof item !== 'object') {
                  return null;
                }
                const source = item as Record<string, unknown>;
                const coordinates = source.coordinates;
                const omegaAbs = typeof source.omega_abs === 'number' ? source.omega_abs : null;
                const indices = Array.isArray(source.indices) ? source.indices : null;
                if (
                  !coordinates ||
                  typeof coordinates !== 'object' ||
                  omegaAbs == null ||
                  !indices ||
                  indices.length !== 2
                ) {
                  return null;
                }
                const normalizedCoords: Record<string, number> = {};
                for (const [key, value] of Object.entries(coordinates)) {
                  if (typeof value === 'number' && Number.isFinite(value)) {
                    normalizedCoords[key] = value;
                  }
                }
                if (!Object.keys(normalizedCoords).length) {
                  return null;
                }
                const [i, j] = indices as [number, number];
                return {
                  indices: [Number(i), Number(j)] as [number, number],
                  coordinates: normalizedCoords,
                  omegaAbs,
                };
              })
              .filter((entry): entry is HotspotEntry => entry !== null);
          }
        } catch (error) {
          // Ignore JSON errors, skip this graph.
          continue;
        }

        const metricsText = await readTextFile(metricsPath);
        const metrics = metricsText ? parseMetricsCsv(metricsText) : null;

        const heatmapBinary = await readBinaryFile(heatmapPath);
        const heatmapImage = heatmapBinary ? buildDataUrl(heatmapBinary, 'image/png') : null;

        results.push({
          graph,
          heatmapImage,
          metrics,
          hotspots,
          topOmegaPath,
          metricsPath: metrics ? metricsPath : null,
        });
      }
      setGraphResults(results);
    },
    []
  );

  useEffect(() => {
    if (!activeRun || activeRun.status !== 'done') {
      return;
    }
    if (!runOutputDir) {
      return;
    }
    void loadGraphArtifacts(runOutputDir, selectedGraphs);
  }, [activeRun, loadGraphArtifacts, runOutputDir, selectedGraphs]);

  const handleRunMapping = useCallback(async () => {
    setRunError(null);
    setLastHotspotSaved(null);
    setGraphResults([]);
    setIsRunning(true);
    try {
      const env = await detectEnvironment();
      setDetectedRepoRoot(env.repoRoot);
      const graphsList = Array.from(selectedGraphs);
      if (!graphsList.length) {
        throw new Error('Select at least one graph to scan.');
      }

      const now = new Date();
      const timestamp = now.toISOString().replace(/[:.]/g, '-');
      const baseDir = env.repoRoot ?? (typeof process !== 'undefined' && typeof process.cwd === 'function'
        ? process.cwd()
        : '');
      const outputDir = path.join(baseDir, 'artifacts', 'phase1-mapping', timestamp);

      await ensureDirectory(outputDir);

      const options: GateBRidgeFinderOptions = {
        axes,
        gridSize,
        bootstrap,
        topK,
        seed,
        graphs: graphsList,
        ranges: {
          rho: ranges.rho,
          tau: ranges.tau,
          zeta: ranges.zeta,
          zetaPhase: ranges.zeta_phase,
        },
        outDir: outputDir,
        strategy: env.strategy,
      };

      const command = cmdGateBRidgeFinder(env.pythonExe, options);

      const paramsPayload = {
        axes,
        ranges,
        gridSize,
        bootstrap,
        topK,
        seed,
        graphs: graphsList,
        outputDir,
      };

      const runId = await createRun({
        phase: 'phase1',
        experiment: 'gateB_ridge_finder',
        cmd: command.cmd,
        args: command.args,
        cwd: command.cwd,
        seed,
        paramsJson: paramsPayload,
        axes,
        graph: graphsList,
        workdir: outputDir,
      });

      setActiveRunId(runId);
      setRunOutputDir(outputDir);
    } catch (error) {
      setRunError(formatError(error));
    } finally {
      setIsRunning(false);
    }
  }, [axes, bootstrap, gridSize, ranges, seed, selectedGraphs, topK]);

  const handleAddHotspot = useCallback(
    async (entry: HotspotEntry | null, graph: string, sourcePath: string) => {
      if (!entry) {
        return;
      }
      const record: HotspotRecord = {
        graph,
        axes,
        coordinates: entry.coordinates,
        omegaAbs: entry.omegaAbs,
        sourcePath,
        addedAt: new Date().toISOString(),
      };
      const nextList = [...hotspotList, record];
      try {
        const directory = path.dirname(hotspotFilePath);
        await ensureDirectory(directory);
        await writeJsonFile(hotspotFilePath, nextList);
        setHotspotList(nextList);
        setLastHotspotSaved(`${graph}:${record.omegaAbs.toFixed(3)}`);
        setHotspotError(null);
      } catch (error) {
        setHotspotError(formatError(error));
      }
    },
    [axes, hotspotFilePath, hotspotList]
  );

  useEffect(() => {
    const container = plotContainerRef.current;
    const result = selectedGraphResult;
    if (!container) {
      return;
    }

    let mounted = true;
    const renderPlot = async () => {
      if (!result?.metrics) {
        container.innerHTML = '';
        return;
      }

      const plotly = await ensurePlotly();
      if (!plotly || !mounted) {
        return;
      }

      const { axis0Values, axis1Values, omegaValues, axis0Name, axis1Name } = result.metrics;
      const xMin = axis1Values[0];
      const xMax = axis1Values[axis1Values.length - 1];
      const yMin = axis0Values[0];
      const yMax = axis0Values[axis0Values.length - 1];

      const data: Array<Record<string, unknown>> = [
        {
          type: 'heatmap',
          x: axis1Values,
          y: axis0Values,
          z: omegaValues,
          colorscale: 'Viridis',
          colorbar: { title: '|Ω|' },
        },
      ];

      if (result.hotspots.length) {
        const tauValues: number[] = [];
        const secondAxisValues: number[] = [];
        const markerText: string[] = [];
        for (const entry of result.hotspots) {
          const tauValue = entry.coordinates.tau;
          const otherAxisKey = axes[0] === 'tau' ? axes[1] : axes[0];
          const otherValue = entry.coordinates[otherAxisKey];
          if (typeof tauValue === 'number' && typeof otherValue === 'number') {
            if (axes[0] === 'tau') {
              tauValues.push(otherValue);
              secondAxisValues.push(tauValue);
            } else if (axes[1] === 'tau') {
              tauValues.push(tauValue);
              secondAxisValues.push(otherValue);
            }
            markerText.push(`|Ω|=${formatNumber(entry.omegaAbs)}`);
          }
        }
        if (tauValues.length === secondAxisValues.length && tauValues.length > 0) {
          data.push({
            type: 'scatter',
            mode: 'markers',
            x: tauValues,
            y: secondAxisValues,
            text: markerText,
            marker: {
              color: '#ffffff',
              size: 8,
              line: { color: '#333333', width: 1 },
              symbol: 'x',
            },
            name: 'Top Ω',
          });
        }
      }

      const images = result.heatmapImage
        ? [
            {
              source: result.heatmapImage,
              xref: 'x',
              yref: 'y',
              x: xMin,
              y: yMin,
              sizex: xMax - xMin || 1,
              sizey: yMax - yMin || 1,
              sizing: 'stretch',
              opacity: 0.5,
              layer: 'below' as const,
              xanchor: 'left' as const,
              yanchor: 'bottom' as const,
            },
          ]
        : [];

      const layout: Record<string, unknown> = {
        title: `${result.graph} |Ω| heatmap`,
        xaxis: { title: axis1Name },
        yaxis: { title: axis0Name },
        margin: { l: 60, r: 20, b: 60, t: 40 },
        images,
      };

      await plotly.react(container, data, layout, { responsive: true });
    };

    void renderPlot();

    return () => {
      mounted = false;
      const plotly = plotlyInstance;
      if (plotly && typeof plotly.purge === 'function' && container) {
        try {
          plotly.purge(container);
        } catch (error) {
          // ignore purge errors
        }
      }
    };
  }, [axes, selectedGraphResult]);

  const renderHotspotRows = (): JSX.Element[] => {
    if (!graphResults.length) {
      return [];
    }
    const rows: JSX.Element[] = [];
    graphResults.forEach((result) => {
      result.hotspots.forEach((entry, index) => {
        const tauValue = entry.coordinates.tau;
        const otherAxis = axes[0] === 'tau' ? axes[1] : axes[0];
        const otherValue = entry.coordinates[otherAxis];
        rows.push(
          <tr key={`${result.graph}-${index}`}>
            <td>{index + 1}</td>
            <td>{formatNumber(entry.omegaAbs)}</td>
            <td>{tauValue != null ? formatNumber(tauValue) : '—'}</td>
            <td>{otherValue != null ? formatNumber(otherValue) : '—'}</td>
            <td>{result.graph}</td>
            <td>{result.topOmegaPath}</td>
            <td>
              <button type="button" onClick={() => void handleAddHotspot(entry, result.graph, result.topOmegaPath)}>
                Add to Hotspot List
              </button>
            </td>
          </tr>
        );
      });
    });
    return rows;
  };

  const isRunButtonDisabled = isRunning || selectedGraphs.size === 0;

  return (
    <div className="phase1-mapping">
      <section className="controls">
        <h2>Phase 1 Mapping Controls</h2>
        <div className="control-group">
          <h3>Axes</h3>
          <div className="axis-options">
            {AXIS_OPTIONS.map((option) => (
              <label key={option.label}>
                <input
                  type="radio"
                  name="axes"
                  value={option.value.join(':')}
                  checked={axes[0] === option.value[0] && axes[1] === option.value[1]}
                  onChange={handleAxesChange}
                />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="control-group">
          <h3>Ranges</h3>
          <AxisRangeControl axis="rho" label="ρ" range={ranges.rho} onChange={handleRangeChange} />
          <AxisRangeControl axis="tau" label="τ" range={ranges.tau} onChange={handleRangeChange} />
          <AxisRangeControl axis="zeta" label="ζ" range={ranges.zeta} onChange={handleRangeChange} />
          <AxisRangeControl axis="zeta_phase" label="ζ_phase" range={ranges.zeta_phase} onChange={handleRangeChange} />
        </div>

        <div className="control-group numeric-inputs">
          <label>
            <span>Grid size</span>
            <input type="number" value={gridSize} min={3} max={201} onChange={handleNumericChange(setGridSize)} />
          </label>
          <label>
            <span>Bootstrap</span>
            <input type="number" value={bootstrap} min={32} onChange={handleNumericChange(setBootstrap)} />
          </label>
          <label>
            <span>Top-K</span>
            <input type="number" value={topK} min={1} onChange={handleNumericChange(setTopK)} />
          </label>
          <label>
            <span>Seed</span>
            <input type="number" value={seed} onChange={handleNumericChange(setSeed)} />
          </label>
        </div>

        <div className="control-group graphs">
          <h3>Graphs</h3>
          <div className="graph-options">
            {GRAPH_OPTIONS.map((graph) => (
              <label key={graph}>
                <input
                  type="checkbox"
                  checked={selectedGraphs.has(graph)}
                  onChange={() => handleGraphToggle(graph)}
                />
                <span>{graph}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="control-group run-action">
          <button type="button" onClick={() => void handleRunMapping()} disabled={isRunButtonDisabled}>
            {isRunning ? 'Running…' : 'Run Mapping'}
          </button>
          {runError ? <div className="error-message">{runError}</div> : null}
          {activeRun ? <div className="run-status">Run status: {activeRun.status}</div> : null}
          {runOutputDir ? <div className="output-dir">Output: {runOutputDir}</div> : null}
        </div>
      </section>

      <section className="results">
        <h2>Results</h2>
        {!graphResults.length ? <p>No results yet. Run the mapping to generate artifacts.</p> : null}
        {graphResults.length ? (
          <div className="heatmap-preview">
            <h3>Heatmap Preview</h3>
            <div className="graph-selection">
              <label>
                <span>Graph</span>
                <select value={selectedGraphKey ?? ''} onChange={handleGraphResultSelect}>
                  {graphResults.map((result) => (
                    <option key={result.graph} value={result.graph}>
                      {result.graph}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div ref={plotContainerRef} className="heatmap-plot" />
            {selectedGraphResult?.metricsPath ? (
              <div className="metrics-path">Metrics CSV: {selectedGraphResult.metricsPath}</div>
            ) : null}
          </div>
        ) : null}

        {graphResults.length ? (
          <div className="hotspot-table">
            <h3>Top-{topK} Hotspots</h3>
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>|Ω|</th>
                  <th>τ</th>
                  <th>{axes[0] === 'tau' ? axes[1] : axes[0]}</th>
                  <th>Graph</th>
                  <th>Source</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>{renderHotspotRows()}</tbody>
            </table>
          </div>
        ) : null}

        {lastHotspotSaved ? <div className="status-message">Saved hotspot {lastHotspotSaved}.</div> : null}
        {hotspotError ? <div className="error-message">{hotspotError}</div> : null}
        {hotspotList.length ? (
          <div className="hotspot-summary">
            <h3>Hotspot List ({hotspotList.length})</h3>
            <ul>
              {hotspotList.slice(-5).map((record, index) => (
                <li key={`${record.graph}-${record.addedAt}-${index}`}>
                  {record.graph}: |Ω|={formatNumber(record.omegaAbs)} from {record.sourcePath}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>
    </div>
  );
}
