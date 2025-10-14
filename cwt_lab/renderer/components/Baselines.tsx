import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';

import HelpDrawer from './HelpDrawer';
import { baselines as baselinesIpc } from '../ipc';
import type {
  BaselineModel,
  BaselineRunErrorEvent,
  BaselineRunExitEvent,
  BaselineRunResult,
  BaselineRunStreamEvent,
} from '../types/ipc';

const DEFAULT_AXIS_MAP_PATH = 'cwt-sim/baselines/axis_map.yml';

type BaselineFormValues = {
  graphKind: string;
  graphRows: string;
  graphCols: string;
  graphParams: string;
  axisA: string;
  axisB: string;
  rangeAStart: string;
  rangeAEnd: string;
  rangeBStart: string;
  rangeBEnd: string;
  gridA: string;
  gridB: string;
  steps: string;
  seed: string;
  topK: string;
  enableLoops: boolean;
  loopTopK: string;
  loopDeltaScale: string;
  fsGuard: string;
  mapToCwt: boolean;
};

type ObservablesColumn = { key: string; label: string };

type TopTileRow = {
  coordinates: string;
  omegaAbs: string;
  observables: Record<string, string>;
};

type LoopSummary = {
  id: string;
  title: string;
  metrics: Array<{ label: string; value: string }>;
  flags: string[];
  trustworthy: boolean;
};

type BaselineArtifacts = {
  outputDir: string;
  heatmapPath: string | null;
  topTiles: TopTileRow[];
  topTileCount: number;
  observables: ObservablesColumn[];
  loopSummaries: LoopSummary[];
};

const MODEL_DEFAULTS: Record<BaselineModel, BaselineFormValues> = {
  ising: {
    graphKind: 'lattice_2d',
    graphRows: '16',
    graphCols: '16',
    graphParams: '',
    axisA: 'T',
    axisB: 'h',
    rangeAStart: '1.0',
    rangeAEnd: '4.0',
    rangeBStart: '-0.3',
    rangeBEnd: '0.3',
    gridA: '25',
    gridB: '25',
    steps: '200',
    seed: '42',
    topK: '10',
    enableLoops: true,
    loopTopK: '3',
    loopDeltaScale: '1.0',
    fsGuard: '',
    mapToCwt: true,
  },
  kuramoto: {
    graphKind: 'ring3',
    graphRows: '0',
    graphCols: '0',
    graphParams: 'n=32',
    axisA: 'kappa',
    axisB: 'sigma',
    rangeAStart: '0.0',
    rangeAEnd: '4.0',
    rangeBStart: '0.0',
    rangeBEnd: '2.0',
    gridA: '25',
    gridB: '25',
    steps: '400',
    seed: '123',
    topK: '10',
    enableLoops: true,
    loopTopK: '3',
    loopDeltaScale: '1.0',
    fsGuard: '',
    mapToCwt: true,
  },
  percolation: {
    graphKind: 'lattice_2d',
    graphRows: '32',
    graphCols: '32',
    graphParams: '',
    axisA: 'p',
    axisB: 'zeta',
    rangeAStart: '0.2',
    rangeAEnd: '0.8',
    rangeBStart: '-0.2',
    rangeBEnd: '0.2',
    gridA: '25',
    gridB: '25',
    steps: '128',
    seed: '7',
    topK: '10',
    enableLoops: true,
    loopTopK: '3',
    loopDeltaScale: '1.0',
    fsGuard: '',
    mapToCwt: true,
  },
  sis: {
    graphKind: 'random_regular',
    graphRows: '0',
    graphCols: '0',
    graphParams: 'n=32,degree=3',
    axisA: 'beta',
    axisB: 'gamma',
    rangeAStart: '0.05',
    rangeAEnd: '0.5',
    rangeBStart: '0.01',
    rangeBEnd: '0.2',
    gridA: '20',
    gridB: '20',
    steps: '200',
    seed: '21',
    topK: '10',
    enableLoops: false,
    loopTopK: '1',
    loopDeltaScale: '1.0',
    fsGuard: '',
    mapToCwt: true,
  },
};

const OBSERVABLE_FIELDS: Record<BaselineModel, ObservablesColumn[]> = {
  ising: [
    { key: 'M_mean', label: 'M̄' },
    { key: 'M_abs_mean', label: '|M|̄' },
    { key: 'chi_est', label: 'χ̂' },
    { key: 'energy_density', label: 'Energy density' },
    { key: 'C_est', label: 'Ĉ' },
  ],
  kuramoto: [
    { key: 'r_mean', label: 'r̄' },
    { key: 'order_parameter_mag', label: '|ρ|' },
    { key: 'spectral_radius', label: 'Spectral radius' },
    { key: 'spectral_gap', label: 'Spectral gap' },
  ],
  percolation: [
    { key: 'S_mean', label: 'S̄' },
    { key: 'S_var', label: 'Var(S)' },
    { key: 'giant_fraction', label: 'Giant fraction' },
    { key: 'threshold_estimate', label: 'Threshold' },
  ],
  sis: [],
};

const MODEL_HELP_CONTENT: Record<BaselineModel, { title: string; analogy: string; bullets: string[] }> = {
  ising: {
    title: 'Ising baseline tips',
    analogy:
      'Treat the spin lattice like a weather grid: warm colours indicate turbulence that often precedes avalanches.',
    bullets: [
      'Low fields and moderate temperatures usually reveal the clearest ridge; broaden the range if the heatmap looks flat.',
      'Coupling controls how rigidly spins follow their neighbours. Tighten it before increasing warm-up sweeps.',
      'Loops catch sign flips in magnetisation – a triggered FS guard means the plaquette collapsed, so widen the delta scale.',
    ],
  },
  kuramoto: {
    title: 'Kuramoto baseline tips',
    analogy: 'Think of oscillators as a choir: κ conducts tempo while σ injects discordant notes.',
    bullets: [
      'A sharp |φ| peak signals synchronisation; if it is muted, increase sample steps to average out jitter.',
      'Use graph parameters to try denser coupling networks – random-regular graphs surface different locking bands.',
      'Set an FS guard threshold before looping to detect when curvature spikes are numerical artefacts.',
    ],
  },
  percolation: {
    title: 'Percolation baseline tips',
    analogy: 'Percolation behaves like dye seeping through porous rock; once enough pores align the flood begins.',
    bullets: [
      'Track S̄ and giant_fraction together – diverging values imply you are skimming the threshold ridge.',
      'Derivative along ζ hints at anisotropy; if flat, expand the secondary axis to capture more drift.',
      'Enable loops when the ridge is sharp to compare against theoretical pc predictions without running Phase 3.',
    ],
  },
  sis: {
    title: 'SIS baseline preview',
    analogy: 'The SIS controls are a sketch of the infection plane – once implementation lands this pane will drive it.',
    bullets: [
      'The infection (β) and recovery (γ) sliders are placeholders until the simulation backend is wired up.',
      'Seed and steps persist so you can reuse this layout when the engine is available.',
      'For now the CLI simply echoes configuration – expect a notification here once dynamics are implemented.',
    ],
  },
};

const parseFiniteNumber = (value: unknown): number | null => {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value === 'string' && value.trim().length > 0) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : null;
  }
  return null;
};

const formatNumber = (value: unknown, digits = 3): string => {
  const numeric = parseFiniteNumber(value);
  if (numeric === null) {
    return '—';
  }
  if (Math.abs(numeric) >= 1000 || Math.abs(numeric) < 0.001) {
    return numeric.toExponential(2);
  }
  const fixed = numeric.toFixed(digits);
  return fixed.replace(/\.0+$/, '').replace(/(\.\d*?)0+$/, '$1');
};

const normalizePath = (value: string): string => value.replace(/\\/g, '/');

const joinPath = (base: string, segment: string): string => {
  if (!base) {
    return segment;
  }
  const normalizedBase = normalizePath(base).replace(/\/+$/, '');
  const normalizedSegment = normalizePath(segment).replace(/^\/+/, '');
  return `${normalizedBase}/${normalizedSegment}`;
};

const toFileUrl = (path: string): string => {
  const normalized = normalizePath(path);
  if (/^[A-Za-z]:/.test(normalized)) {
    return encodeURI(`file:///${normalized}`);
  }
  return encodeURI(`file://${normalized.startsWith('/') ? normalized : `/${normalized}`}`);
};

const parseCsv = (raw: string): Array<Record<string, string>> => {
  const rows: string[][] = [];
  let current = '';
  let row: string[] = [];
  let inQuotes = false;

  const flushField = () => {
    row.push(current);
    current = '';
  };

  const flushRow = () => {
    if (row.length === 0) {
      return;
    }
    rows.push(row);
    row = [];
  };

  for (let i = 0; i < raw.length; i += 1) {
    const char = raw[i];
    if (inQuotes) {
      if (char === '"') {
        if (raw[i + 1] === '"') {
          current += '"';
          i += 1;
        } else {
          inQuotes = false;
        }
      } else {
        current += char;
      }
      continue;
    }

    if (char === '"') {
      inQuotes = true;
      continue;
    }
    if (char === ',') {
      flushField();
      continue;
    }
    if (char === '\r') {
      continue;
    }
    if (char === '\n') {
      flushField();
      flushRow();
      continue;
    }
    current += char;
  }
  flushField();
  flushRow();

  if (rows.length === 0) {
    return [];
  }
  const [header, ...body] = rows;
  const trimmedHeader = header.map((item) => item.trim());
  return body
    .filter((entries) => entries.some((entry) => entry.trim().length > 0))
    .map((entries) => {
      const record: Record<string, string> = {};
      trimmedHeader.forEach((name, index) => {
        record[name] = entries[index] ?? '';
      });
      return record;
    });
};

const flattenArtifactNodes = (nodes: unknown[]): Array<{ name: string; path: string }> => {
  const result: Array<{ name: string; path: string }> = [];
  for (const entry of nodes) {
    if (!entry || typeof entry !== 'object') {
      continue;
    }
    const node = entry as { name?: unknown; path?: unknown; type?: unknown; children?: unknown };
    if (node.type === 'file' && typeof node.name === 'string' && typeof node.path === 'string') {
      result.push({ name: node.name, path: node.path });
    } else if (node.type === 'directory' && Array.isArray(node.children)) {
      result.push(...flattenArtifactNodes(node.children));
    }
  }
  return result;
};

const formatCoordinates = (coordinates: Record<string, unknown>): string => {
  const entries = Object.entries(coordinates)
    .filter(([key]) => key)
    .map(([key, value]) => `${key}=${formatNumber(value, 3)}`);
  return entries.length > 0 ? entries.join(', ') : 'n/a';
};

const buildLoopSummary = (payload: unknown, filePath: string, model: BaselineModel): LoopSummary => {
  const base: LoopSummary = {
    id: filePath,
    title: 'Loop report',
    metrics: [],
    flags: [],
    trustworthy: false,
  };
  if (!payload || typeof payload !== 'object') {
    return base;
  }
  const meta = payload as Record<string, unknown>;
  const indices = Array.isArray(meta.indices) ? meta.indices : [];
  if (indices.length === 2) {
    base.title = `Tile [${indices[0]}, ${indices[1]}]`;
  }

  const center = typeof meta.center === 'object' && meta.center ? (meta.center as Record<string, unknown>) : null;
  const loop = typeof meta.loop === 'object' && meta.loop ? (meta.loop as Record<string, unknown>) : null;

  let omegaAbs: number | null = null;
  if (loop) {
    omegaAbs = parseFiniteNumber(loop.omega_abs);
    if (omegaAbs !== null) {
      base.metrics.push({ label: '|Ω|', value: formatNumber(omegaAbs) });
    }
    const area = parseFiniteNumber(loop.area);
    if (area !== null) {
      base.metrics.push({ label: 'Loop area', value: formatNumber(area) });
    }
    if (loop.fs_guard_triggered) {
      base.flags.push('FS guard triggered');
    }
    if (loop.sign_flip_detected) {
      base.flags.push('Sign flip detected');
    }
  }

  if (center) {
    const centerOmega = parseFiniteNumber(center.omega ?? center.omega_abs);
    if (centerOmega !== null) {
      base.metrics.push({ label: 'Center Ω', value: formatNumber(centerOmega) });
    }
    if (center.M_mean !== undefined) {
      const magnetisation = parseFiniteNumber(center.M_mean);
      if (magnetisation !== null) {
        base.metrics.push({ label: 'M̄', value: formatNumber(magnetisation) });
      }
    }
    if (center.r_mean !== undefined) {
      const rMean = parseFiniteNumber(center.r_mean);
      if (rMean !== null) {
        base.metrics.push({ label: 'r̄', value: formatNumber(rMean) });
      }
    }
    const coordinatePairs = Object.entries(center)
      .filter(([key, value]) => typeof value === 'number' && !['omega', 'omega_abs', 'M_mean', 'r_mean'].includes(key))
      .slice(0, 2)
      .map(([key, value]) => `${key}=${formatNumber(value)}`);
    if (coordinatePairs.length > 0) {
      base.metrics.push({ label: 'Center', value: coordinatePairs.join(', ') });
    }
  }

  let phiAbs: number | null = parseFiniteNumber(meta.phi_abs);
  if (phiAbs !== null) {
    base.metrics.push({ label: '|φ|', value: formatNumber(phiAbs) });
  }

  if (Array.isArray(meta.orientations)) {
    for (const entry of meta.orientations) {
      if (!entry || typeof entry !== 'object') {
        continue;
      }
      const orientation = entry as Record<string, unknown>;
      const name = typeof orientation.orientation === 'string' ? orientation.orientation : 'orientation';
      const phiValue = parseFiniteNumber(orientation.phi);
      if (phiValue !== null) {
        phiAbs = Math.max(phiAbs ?? 0, Math.abs(phiValue));
      }
      const fsP95 = parseFiniteNumber(orientation.fs_p95);
      const parts: string[] = [];
      if (phiValue !== null) {
        parts.push(`φ=${formatNumber(phiValue)}`);
      }
      if (fsP95 !== null) {
        parts.push(`fsₚ₉₅=${formatNumber(fsP95)}`);
      }
      if (orientation.fs_guard_exceeded) {
        base.flags.push(`${name} guard exceeded`);
      }
      if (parts.length > 0) {
        base.metrics.push({ label: name, value: parts.join(', ') });
      }
    }
  }

  if (meta.fs_guard_exceeded) {
    base.flags.push('FS guard exceeded');
  }

  const uniqueFlags = Array.from(new Set(base.flags));
  base.flags = uniqueFlags;

  const guardHit = base.flags.some((flag) => flag.toLowerCase().includes('guard'));
  const trustScore = !guardHit && ((phiAbs !== null && phiAbs > 0.2) || (omegaAbs !== null && omegaAbs > 0.2));
  base.trustworthy = trustScore;

  if (center && !base.title.includes('Tile')) {
    const coordinateSummary = Object.entries(center)
      .filter(([key, value]) => typeof value === 'number' && ['kappa', 'sigma', 'temperature', 'field'].includes(key))
      .map(([key, value]) => `${key}=${formatNumber(value)}`)
      .join(', ');
    if (coordinateSummary) {
      base.title = `Loop at ${coordinateSummary}`;
    }
  }

  return base;
};

const loadArtifactsForRun = async (
  model: BaselineModel,
  run: BaselineRunResult,
): Promise<BaselineArtifacts> => {
  const resolvedDir = run.outputDir ?? run.artifactsDir;
  if (!resolvedDir) {
    throw new Error('Baseline run did not report an artifact directory.');
  }
  const artifactsApi = window?.CWT?.artifacts;
  if (!artifactsApi?.readFile) {
    throw new Error('Artifacts IPC is unavailable.');
  }

  const normalizedDir = normalizePath(resolvedDir);
  const heatmapPath = joinPath(normalizedDir, 'omega_abs_heatmap.png');
  const topTilesPath = joinPath(normalizedDir, 'top_omega_tiles.json');
  const metricsPath = joinPath(normalizedDir, 'metrics.csv');

  const [topTilesPayload, metricsPayload] = await Promise.all([
    artifactsApi.readFile({ path: topTilesPath }),
    artifactsApi.readFile({ path: metricsPath }),
  ]);

  const topTilesRaw = topTilesPayload?.contents ?? '';
  if (!topTilesRaw) {
    throw new Error('top_omega_tiles.json is missing or empty.');
  }
  const topTilesJson = JSON.parse(topTilesRaw) as Record<string, unknown>;
  const metricsRows = parseCsv(metricsPayload?.contents ?? '');
  const axes = Array.isArray(topTilesJson.axes)
    ? (topTilesJson.axes as Array<Record<string, unknown>>)
        .map((axis) => (typeof axis.name === 'string' ? axis.name : null))
        .filter((axis): axis is string => Boolean(axis))
    : [];

  const metricsByIndex = new Map<string, Record<string, string>>();
  for (const row of metricsRows) {
    const key = axes
      .map((axis) => row[`${axis}_index`] ?? row[`${axis}_INDEX`] ?? '')
      .join(',');
    if (!key.includes('')) {
      metricsByIndex.set(key, row);
    }
  }

  const observables = OBSERVABLE_FIELDS[model];
  const tiles = Array.isArray(topTilesJson.top_tiles)
    ? (topTilesJson.top_tiles as Array<Record<string, unknown>>)
    : [];

  const rows: TopTileRow[] = tiles.map((entry) => {
    const indices = Array.isArray(entry.indices) ? (entry.indices as Array<number | string>) : [];
    const indexKey = indices.join(',');
    const coordinates =
      entry.coordinates && typeof entry.coordinates === 'object'
        ? (entry.coordinates as Record<string, unknown>)
        : {};
    const metricsRow = metricsByIndex.get(indexKey) ?? {};
    const observableValues: Record<string, string> = {};
    for (const column of observables) {
      const raw = metricsRow[column.key];
      observableValues[column.key] = raw != null && raw !== '' ? formatNumber(raw) : '—';
    }
    return {
      coordinates: formatCoordinates(coordinates),
      omegaAbs: formatNumber(entry.omega_abs ?? metricsRow.omega_abs),
      observables: observableValues,
    };
  });

  let loopSummaries: LoopSummary[] = [];
  const loopsDir = joinPath(normalizedDir, 'loops');
  if (artifactsApi.list) {
    try {
      const listing = await artifactsApi.list({ under: loopsDir });
      if (Array.isArray(listing)) {
        const files = flattenArtifactNodes(listing).filter((node) => node.name.endsWith('.json'));
        if (files.length > 0) {
          const reports = await Promise.all(
            files.map(async (file) => {
              const payload = await artifactsApi.readFile({ path: file.path });
              const data = payload?.contents ? JSON.parse(payload.contents) : null;
              return buildLoopSummary(data, file.path, model);
            }),
          );
          loopSummaries = reports;
        }
      }
    } catch {
      loopSummaries = [];
    }
  }

  return {
    outputDir: normalizedDir,
    heatmapPath,
    topTiles: rows,
    topTileCount: rows.length,
    observables,
    loopSummaries,
  };
};

const createInitialState = (): Record<BaselineModel, BaselineFormValues> => ({
  ising: { ...MODEL_DEFAULTS.ising },
  kuramoto: { ...MODEL_DEFAULTS.kuramoto },
  percolation: { ...MODEL_DEFAULTS.percolation },
  sis: { ...MODEL_DEFAULTS.sis },
});

export default function Baselines() {
  const [model, setModel] = useState<BaselineModel>('ising');
  const [formsByModel, setFormsByModel] = useState<Record<BaselineModel, BaselineFormValues>>(createInitialState);
  const form = formsByModel[model];
  const [running, setRunning] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [logByRunId, setLogByRunId] = useState<Record<string, string>>({});
  const [displayRunId, setDisplayRunId] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<BaselineRunResult | null>(null);
  const [artifacts, setArtifacts] = useState<BaselineArtifacts | null>(null);
  const [artifactsError, setArtifactsError] = useState<string | null>(null);
  const [artifactsLoading, setArtifactsLoading] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);

  const pendingRunRef = useRef(false);
  const activeRunRef = useRef<string | null>(null);

  const updateForm = (patch: Partial<BaselineFormValues>) => {
    setFormsByModel((previous) => ({
      ...previous,
      [model]: { ...previous[model], ...patch },
    }));
  };

  useEffect(() => {
    const stopOutput = baselinesIpc.onOutput((event: BaselineRunStreamEvent) => {
      setLogByRunId((current) => ({
        ...current,
        [event.runId]: (current[event.runId] ?? '') + event.chunk,
      }));
      if (pendingRunRef.current && !activeRunRef.current) {
        activeRunRef.current = event.runId;
        pendingRunRef.current = false;
        setDisplayRunId(event.runId);
      }
    });
    const stopExit = baselinesIpc.onExit((event: BaselineRunExitEvent) => {
      if (!activeRunRef.current) {
        activeRunRef.current = event.runId;
      }
      if (event.runId === activeRunRef.current) {
        setRunning(false);
        if (event.code === 0) {
          setStatusMessage('Baseline run completed successfully.');
          setErrorMessage(null);
        } else {
          const code = event.code ?? 'unknown';
          setStatusMessage(`Baseline run exited with code ${code}.`);
          setErrorMessage(`Baseline run failed (code ${code}).`);
        }
      }
    });
    const stopError = baselinesIpc.onError((event: BaselineRunErrorEvent) => {
      if (!activeRunRef.current) {
        activeRunRef.current = event.runId;
      }
      if (event.runId === activeRunRef.current) {
        setRunning(false);
        setErrorMessage(event.message ?? 'Baseline run failed.');
      }
    });
    return () => {
      stopOutput();
      stopExit();
      stopError();
    };
  }, []);

  useEffect(() => {
    if (!lastResult) {
      return;
    }
    let cancelled = false;
    setArtifactsLoading(true);
    setArtifactsError(null);
    loadArtifactsForRun(lastResult.model, lastResult)
      .then((data) => {
        if (cancelled) {
          return;
        }
        setArtifacts(data);
        setArtifactsLoading(false);
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        setArtifacts(null);
        setArtifactsError((error as Error).message ?? 'Failed to load artifacts.');
        setArtifactsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [lastResult]);

  const handleModelChange = (event: FormEvent<HTMLSelectElement>) => {
    const next = event.currentTarget.value as BaselineModel;
    setModel(next);
    setStatusMessage(null);
    setErrorMessage(null);
  };

  const buildArgs = (): { args: string[]; env: Record<string, string> | null } => {
    const args: string[] = [];
    if (form.graphKind.trim()) {
      args.push('--graph-kind', form.graphKind.trim());
    }
    const graphParams = form.graphParams
      .split(/[\n,;]+/)
      .map((entry) => entry.trim())
      .filter((entry) => entry.length > 0);
    for (const param of graphParams) {
      args.push('--graph-param', param);
    }

    const gridA = parseFiniteNumber(form.gridA);
    const gridB = parseFiniteNumber(form.gridB);
    if (gridA && gridB) {
      args.push('--grid-size', String(Math.trunc(gridA)), String(Math.trunc(gridB)));
    }

    if (model === 'ising' || model === 'percolation') {
      const axisA = form.axisA.trim();
      const axisB = form.axisB.trim();
      if (axisA && axisB) {
        args.push('--axes', axisA, axisB);
      }
      const rangeAStart = parseFiniteNumber(form.rangeAStart);
      const rangeAEnd = parseFiniteNumber(form.rangeAEnd);
      if (axisA && rangeAStart !== null && rangeAEnd !== null) {
        args.push('--range', axisA, String(rangeAStart), String(rangeAEnd));
      }
      const rangeBStart = parseFiniteNumber(form.rangeBStart);
      const rangeBEnd = parseFiniteNumber(form.rangeBEnd);
      if (axisB && rangeBStart !== null && rangeBEnd !== null) {
        args.push('--range', axisB, String(rangeBStart), String(rangeBEnd));
      }
      const rows = parseFiniteNumber(form.graphRows);
      const cols = parseFiniteNumber(form.graphCols);
      if (rows && cols) {
        args.push('--lattice-size', String(Math.trunc(rows)), String(Math.trunc(cols)));
      }
    } else if (model === 'kuramoto') {
      const kappaMin = parseFiniteNumber(form.rangeAStart);
      const kappaMax = parseFiniteNumber(form.rangeAEnd);
      if (kappaMin !== null && kappaMax !== null) {
        args.push('--coupling-range', String(kappaMin), String(kappaMax));
      }
      const sigmaMin = parseFiniteNumber(form.rangeBStart);
      const sigmaMax = parseFiniteNumber(form.rangeBEnd);
      if (sigmaMin !== null && sigmaMax !== null) {
        args.push('--disorder-range', String(sigmaMin), String(sigmaMax));
      }
    }

    const topK = parseFiniteNumber(form.topK);
    if (topK !== null) {
      args.push('--top-k', String(Math.trunc(topK)));
    }

    if (form.enableLoops) {
      args.push('--enable-loops');
      const loopTopK = parseFiniteNumber(form.loopTopK);
      if (loopTopK !== null) {
        args.push('--loop-top-k', String(Math.trunc(loopTopK)));
      }
      const loopDelta = parseFiniteNumber(form.loopDeltaScale);
      if (loopDelta !== null) {
        args.push('--loop-delta-scale', String(loopDelta));
      }
    }

    const env: Record<string, string> | null = form.fsGuard.trim()
      ? { CWT_LOOP_FS_GUARD: form.fsGuard.trim() }
      : null;

    return { args, env };
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (running) {
      return;
    }
    setStatusMessage('Launching baseline run…');
    setErrorMessage(null);
    setRunning(true);
    pendingRunRef.current = true;
    activeRunRef.current = null;
    setDisplayRunId(null);
    setLogByRunId({});

    const { args, env } = buildArgs();
    try {
      const payload = {
        model,
        axisMap: form.mapToCwt ? DEFAULT_AXIS_MAP_PATH : null,
        steps: form.steps.trim() ? form.steps.trim() : null,
        seed: form.seed.trim() ? form.seed.trim() : null,
        args,
        env,
      };
      const result = await baselinesIpc.run(payload);
      setLastResult(result);
      setStatusMessage('Baseline run finished. Fetching artifacts…');
    } catch (error) {
      setRunning(false);
      setErrorMessage((error as Error).message ?? 'Baseline run failed.');
      setStatusMessage('Baseline run failed.');
    }
  };

  const currentLog = displayRunId ? logByRunId[displayRunId] ?? '' : '';
  const helpContent = MODEL_HELP_CONTENT[model];
  const alignedWithTheory = useMemo(() => {
    if (!artifacts || artifacts.loopSummaries.length === 0) {
      return false;
    }
    return artifacts.loopSummaries.some((summary) => summary.trustworthy);
  }, [artifacts]);
  const observablesColumns = artifacts?.observables ?? OBSERVABLE_FIELDS[model];
  const stepsValue = parseFiniteNumber(form.steps);
  const seedValue = parseFiniteNumber(form.seed);

  return (
    <section className="baselines">
      <header className="baselines__header">
        <div>
          <h2>Baselines</h2>
          <p className="baselines__subtitle">
            Configure and launch reference scans across classic statistical models. Results persist between runs so you can iterate.
          </p>
        </div>
        <div className="baselines__header-actions">
          <button
            type="button"
            className="baselines__tips-button"
            onClick={() => setHelpOpen(true)}
            aria-label="Show baseline model tips"
          >
            Model tips
          </button>
        </div>
      </header>

      <form className="baselines__form" onSubmit={handleSubmit} aria-label="Baseline configuration">
        <fieldset className="baselines__fieldset" disabled={running}>
          <div className="baselines__form-grid">
            <label className="baselines__field">
              <span className="baselines__field-label">Model</span>
              <select value={model} onChange={handleModelChange}>
                <option value="ising">Ising</option>
                <option value="kuramoto">Kuramoto</option>
                <option value="percolation">Percolation</option>
                <option value="sis">SIS (preview)</option>
              </select>
            </label>

            <label className="baselines__field">
              <span className="baselines__field-label">Graph kind</span>
              <input
                type="text"
                value={form.graphKind}
                onChange={(event) => updateForm({ graphKind: event.currentTarget.value })}
                placeholder="lattice_2d"
              />
            </label>

            <label className="baselines__field">
              <span className="baselines__field-label">Graph rows</span>
              <input
                type="number"
                inputMode="numeric"
                value={form.graphRows}
                onChange={(event) => updateForm({ graphRows: event.currentTarget.value })}
              />
            </label>

            <label className="baselines__field">
              <span className="baselines__field-label">Graph cols</span>
              <input
                type="number"
                inputMode="numeric"
                value={form.graphCols}
                onChange={(event) => updateForm({ graphCols: event.currentTarget.value })}
              />
            </label>

            <label className="baselines__field baselines__field--wide">
              <span className="baselines__field-label">Graph params</span>
              <textarea
                value={form.graphParams}
                onChange={(event) => updateForm({ graphParams: event.currentTarget.value })}
                rows={2}
                placeholder="n=32,degree=3"
              />
            </label>

            <label className="baselines__field">
              <span className="baselines__field-label">Axis A</span>
              <input
                type="text"
                value={form.axisA}
                onChange={(event) => updateForm({ axisA: event.currentTarget.value })}
                placeholder="T"
              />
            </label>

            <label className="baselines__field">
              <span className="baselines__field-label">Axis B</span>
              <input
                type="text"
                value={form.axisB}
                onChange={(event) => updateForm({ axisB: event.currentTarget.value })}
                placeholder="h"
              />
            </label>

            <div className="baselines__field-group">
              <span className="baselines__field-label">Axis A range</span>
              <div className="baselines__field-pair">
                <input
                  type="text"
                  value={form.rangeAStart}
                  onChange={(event) => updateForm({ rangeAStart: event.currentTarget.value })}
                  placeholder="start"
                />
                <input
                  type="text"
                  value={form.rangeAEnd}
                  onChange={(event) => updateForm({ rangeAEnd: event.currentTarget.value })}
                  placeholder="end"
                />
              </div>
            </div>

            <div className="baselines__field-group">
              <span className="baselines__field-label">Axis B range</span>
              <div className="baselines__field-pair">
                <input
                  type="text"
                  value={form.rangeBStart}
                  onChange={(event) => updateForm({ rangeBStart: event.currentTarget.value })}
                  placeholder="start"
                />
                <input
                  type="text"
                  value={form.rangeBEnd}
                  onChange={(event) => updateForm({ rangeBEnd: event.currentTarget.value })}
                  placeholder="end"
                />
              </div>
            </div>

            <div className="baselines__field-group">
              <span className="baselines__field-label">Grid size</span>
              <div className="baselines__field-pair">
                <input
                  type="number"
                  inputMode="numeric"
                  value={form.gridA}
                  onChange={(event) => updateForm({ gridA: event.currentTarget.value })}
                  placeholder="rows"
                />
                <input
                  type="number"
                  inputMode="numeric"
                  value={form.gridB}
                  onChange={(event) => updateForm({ gridB: event.currentTarget.value })}
                  placeholder="cols"
                />
              </div>
            </div>

            <label className="baselines__field">
              <span className="baselines__field-label">Steps</span>
              <input
                type="number"
                inputMode="numeric"
                value={form.steps}
                onChange={(event) => updateForm({ steps: event.currentTarget.value })}
                placeholder="200"
              />
            </label>

            <label className="baselines__field">
              <span className="baselines__field-label">Seed</span>
              <input
                type="number"
                inputMode="numeric"
                value={form.seed}
                onChange={(event) => updateForm({ seed: event.currentTarget.value })}
                placeholder="42"
              />
            </label>

            <label className="baselines__field">
              <span className="baselines__field-label">Top K</span>
              <input
                type="number"
                inputMode="numeric"
                value={form.topK}
                onChange={(event) => updateForm({ topK: event.currentTarget.value })}
                min={1}
              />
            </label>

            <label className="baselines__field">
              <span className="baselines__field-label">FS guard threshold</span>
              <input
                type="text"
                value={form.fsGuard}
                onChange={(event) => updateForm({ fsGuard: event.currentTarget.value })}
                placeholder="e.g. 0.9"
              />
            </label>

            <label className="baselines__checkbox">
              <input
                type="checkbox"
                checked={form.mapToCwt}
                onChange={(event) => updateForm({ mapToCwt: event.currentTarget.checked })}
              />
              <span>Map axes to CWT defaults</span>
            </label>

            <label className="baselines__checkbox">
              <input
                type="checkbox"
                checked={form.enableLoops}
                onChange={(event) => updateForm({ enableLoops: event.currentTarget.checked })}
              />
              <span>Enable loop analysis</span>
            </label>

            <label className="baselines__field baselines__field--compact">
              <span className="baselines__field-label">Loop Top K</span>
              <input
                type="number"
                inputMode="numeric"
                value={form.loopTopK}
                onChange={(event) => updateForm({ loopTopK: event.currentTarget.value })}
                min={1}
                disabled={!form.enableLoops}
              />
            </label>

            <label className="baselines__field baselines__field--compact">
              <span className="baselines__field-label">Loop Δ scale</span>
              <input
                type="text"
                value={form.loopDeltaScale}
                onChange={(event) => updateForm({ loopDeltaScale: event.currentTarget.value })}
                disabled={!form.enableLoops}
              />
            </label>
          </div>
        </fieldset>

        <footer className="baselines__actions">
          <button type="submit" className="baselines__submit" disabled={running}>
            {running ? 'Running…' : 'Run baseline'}
          </button>
          <div className="baselines__meta">
            {stepsValue !== null ? <span>Steps: {stepsValue}</span> : null}
            {seedValue !== null ? <span>Seed: {seedValue}</span> : null}
            {form.mapToCwt ? <span>Axis map: linked</span> : <span>Axis map: manual</span>}
          </div>
        </footer>
      </form>

      <section className="baselines__status" aria-live="polite">
        {statusMessage ? <p className="baselines__status-message">{statusMessage}</p> : null}
        {errorMessage ? <p className="baselines__status-error">{errorMessage}</p> : null}
      </section>

      <section className="baselines__log" aria-label="Baseline run output">
        <header className="baselines__log-header">
          <h3>Run output</h3>
          {displayRunId ? <code className="baselines__run-id">{displayRunId}</code> : null}
        </header>
        <pre className="baselines__log-body" data-running={running}>
          {currentLog.trim().length > 0 ? currentLog : 'No output yet.'}
        </pre>
      </section>

      <section className="baselines__results" aria-live="polite">
        <header className="baselines__results-header">
          <h3>Results</h3>
          {alignedWithTheory ? (
            <span className="baselines__badge" role="status">
              ✅ Aligned with theory
            </span>
          ) : null}
        </header>

        {artifactsLoading ? <p>Loading artifacts…</p> : null}
        {artifactsError ? <p className="baselines__status-error">{artifactsError}</p> : null}

        {artifacts ? (
          <div className="baselines__results-grid">
            <figure className="baselines__heatmap" aria-label="Omega heatmap">
              {artifacts.heatmapPath ? (
                <img src={toFileUrl(artifacts.heatmapPath)} alt="Baseline heatmap" />
              ) : (
                <div className="baselines__heatmap-missing">Heatmap artifact unavailable.</div>
              )}
              <figcaption>
                |Ω| heatmap · saved under <code>{artifacts.outputDir}</code>
              </figcaption>
            </figure>

            <div className="baselines__topk">
              <header>
                <h4>Top {artifacts.topTileCount} tiles</h4>
              </header>
              <div className="baselines__table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th scope="col">Coordinates</th>
                      <th scope="col">|Ω|</th>
                      {observablesColumns.map((column) => (
                        <th scope="col" key={column.key}>
                          {column.label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {artifacts.topTiles.length === 0 ? (
                      <tr>
                        <td colSpan={2 + observablesColumns.length}>No top tiles reported.</td>
                      </tr>
                    ) : (
                      artifacts.topTiles.map((row, index) => (
                        <tr key={`${row.coordinates}-${index}`}>
                          <td>{row.coordinates}</td>
                          <td>{row.omegaAbs}</td>
                          {observablesColumns.map((column) => (
                            <td key={column.key}>{row.observables[column.key]}</td>
                          ))}
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="baselines__loops">
              <header>
                <h4>Loop analysis</h4>
              </header>
              {artifacts.loopSummaries.length === 0 ? (
                <p>No loop reports generated.</p>
              ) : (
                <div className="baselines__loop-grid">
                  {artifacts.loopSummaries.map((summary) => (
                    <article
                      key={summary.id}
                      className={summary.trustworthy ? 'baselines__loop baselines__loop--trusted' : 'baselines__loop'}
                    >
                      <header className="baselines__loop-header">
                        <h5>{summary.title}</h5>
                        {summary.trustworthy ? <span className="baselines__loop-flag">Theory aligned</span> : null}
                      </header>
                      <dl className="baselines__loop-metrics">
                        {summary.metrics.map((metric) => (
                          <div key={`${summary.id}-${metric.label}`}>
                            <dt>{metric.label}</dt>
                            <dd>{metric.value}</dd>
                          </div>
                        ))}
                      </dl>
                      {summary.flags.length > 0 ? (
                        <ul className="baselines__loop-flags">
                          {summary.flags.map((flag) => (
                            <li key={`${summary.id}-${flag}`}>{flag}</li>
                          ))}
                        </ul>
                      ) : null}
                    </article>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : null}
      </section>

      <HelpDrawer
        open={helpOpen}
        title={helpContent.title}
        analogy={helpContent.analogy}
        bullets={helpContent.bullets}
        onClose={() => setHelpOpen(false)}
      />
    </section>
  );
}
