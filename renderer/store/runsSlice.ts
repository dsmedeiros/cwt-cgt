import { create } from 'zustand';

export interface RunMetrics {
  fsP95?: number;
  phi?: number;
  R?: number;
  overlapMin?: number;
  kappaChange?: number;
  guardExceeded?: boolean;
  phiFlipError?: number;
  rFlipError?: number;
}

export interface RunSummary {
  id: string;
  createdAt: string;
  phase: string | null;
  experiment: string | null;
  status: string | null;
  command: string | null;
  workdir: string | null;
  seed: number | null;
  paramsJson: unknown;
  axes: unknown;
  graph: unknown;
  centerJson: unknown;
  metrics: RunMetrics | null;
  stdoutPath: string | null;
  stderrPath: string | null;
  artifactsPath: string | null;
  pythonExe: string | null;
  gitSha: string | null;
  pipFreezePath: string | null;
}

export interface QueryRunsOptions {
  phase?: string;
  experiment?: string;
  limit?: number;
}

export interface RunsSliceState {
  runs: RunSummary[];
  selectedRunId: string | null;
  selectRun: (runId: string | null) => void;
  queryRuns: (options?: QueryRunsOptions) => Promise<RunSummary[]>;
  refreshRuns: (options?: QueryRunsOptions) => Promise<RunSummary[]>;
  setRuns: (runs: RunSummary[]) => void;
}

interface ElectronLike {
  registry?: {
    queryRuns?: (options?: QueryRunsOptions) => Promise<unknown>;
  };
  ipcRenderer?: {
    invoke?: (channel: string, ...args: unknown[]) => Promise<unknown>;
  };
}

declare global {
  interface Window {
    electron?: ElectronLike;
  }
}

function getElectron(): ElectronLike | undefined {
  if (typeof window === 'undefined') {
    return undefined;
  }
  return window.electron;
}

function normalizeNumber(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number.parseFloat(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return undefined;
}

function normalizeBoolean(value: unknown): boolean | undefined {
  if (typeof value === 'boolean') {
    return value;
  }
  if (typeof value === 'string') {
    if (value.toLowerCase() === 'true') {
      return true;
    }
    if (value.toLowerCase() === 'false') {
      return false;
    }
  }
  return undefined;
}

function coerceMetrics(raw: unknown): RunMetrics | null {
  if (!raw || typeof raw !== 'object') {
    return null;
  }
  const source = raw as Record<string, unknown>;
  const metrics: RunMetrics = {};

  const numberKeys: [keyof RunMetrics, string[]][] = [
    ['fsP95', ['fsP95', 'fs_p95', 'fsp95', 'fs']],
    ['phi', ['phi', 'Φ', 'phiValue']],
    ['R', ['R', 'r', 'rho']],
    ['overlapMin', ['overlapMin', 'overlap_min']],
    ['kappaChange', ['kappaChange', 'kappa_change']],
    ['phiFlipError', ['phiFlipError', 'phi_flip_error']],
    ['rFlipError', ['rFlipError', 'r_flip_error']],
  ];

  for (const [key, candidates] of numberKeys) {
    for (const name of candidates) {
      const value = normalizeNumber(source[name]);
      if (typeof value !== 'undefined') {
        metrics[key] = value;
        break;
      }
    }
  }

  const guard = normalizeBoolean(source.guardExceeded ?? source.guard_exceeded);
  if (typeof guard !== 'undefined') {
    metrics.guardExceeded = guard;
  }

  const hasValues = Object.values(metrics).some((value) => typeof value !== 'undefined');
  return hasValues ? metrics : null;
}

interface RawRunRecord {
  id?: unknown;
  createdAt?: unknown;
  created_at?: unknown;
  phase?: unknown;
  experiment?: unknown;
  status?: unknown;
  command?: unknown;
  workdir?: unknown;
  seed?: unknown;
  paramsJson?: unknown;
  params_json?: unknown;
  axes?: unknown;
  graph?: unknown;
  centerJson?: unknown;
  center_json?: unknown;
  metrics?: unknown;
  metricsJson?: unknown;
  metrics_json?: unknown;
  stdoutPath?: unknown;
  stdout_path?: unknown;
  stderrPath?: unknown;
  stderr_path?: unknown;
  artifactsPath?: unknown;
  artifacts_path?: unknown;
  pythonExe?: unknown;
  python_exe?: unknown;
  gitSha?: unknown;
  git_sha?: unknown;
  pipFreezePath?: unknown;
  pip_freeze_path?: unknown;
}

function normalizeRunRecord(raw: RawRunRecord): RunSummary | null {
  const id = typeof raw.id === 'string' ? raw.id : undefined;
  const createdAt = (typeof raw.createdAt === 'string' ? raw.createdAt : undefined) ??
    (typeof raw.created_at === 'string' ? raw.created_at : undefined);

  if (!id || !createdAt) {
    return null;
  }

  const pickString = (value: unknown): string | null => {
    if (typeof value === 'string') {
      return value;
    }
    return value == null ? null : String(value);
  };

  const pickNullableString = (value: unknown): string | null => {
    const picked = pickString(value);
    return picked === '' ? null : picked;
  };

  const pickNullableNumber = (value: unknown): number | null => {
    const normalized = normalizeNumber(value);
    return typeof normalized === 'number' ? normalized : null;
  };

  const metricsSource = raw.metrics ?? raw.metricsJson ?? raw.metrics_json ?? null;
  const metrics = coerceMetrics(metricsSource);

  return {
    id,
    createdAt,
    phase: pickNullableString(raw.phase),
    experiment: pickNullableString(raw.experiment),
    status: pickNullableString(raw.status),
    command: pickNullableString(raw.command),
    workdir: pickNullableString(raw.workdir),
    seed: pickNullableNumber(raw.seed),
    paramsJson: raw.paramsJson ?? raw.params_json ?? null,
    axes: raw.axes ?? null,
    graph: raw.graph ?? null,
    centerJson: raw.centerJson ?? raw.center_json ?? null,
    metrics,
    stdoutPath: pickNullableString(raw.stdoutPath ?? raw.stdout_path),
    stderrPath: pickNullableString(raw.stderrPath ?? raw.stderr_path),
    artifactsPath: pickNullableString(raw.artifactsPath ?? raw.artifacts_path),
    pythonExe: pickNullableString(raw.pythonExe ?? raw.python_exe),
    gitSha: pickNullableString(raw.gitSha ?? raw.git_sha),
    pipFreezePath: pickNullableString(raw.pipFreezePath ?? raw.pip_freeze_path),
  };
}

async function callQueryRuns(options?: QueryRunsOptions): Promise<RunSummary[]> {
  const electron = getElectron();
  const results: unknown[] = [];

  try {
    if (electron?.registry?.queryRuns) {
      const value = await electron.registry.queryRuns(options);
      if (Array.isArray(value)) {
        results.push(...value);
      }
    } else if (electron?.ipcRenderer?.invoke) {
      const value = await electron.ipcRenderer.invoke('registry.queryRuns', options);
      if (Array.isArray(value)) {
        results.push(...value);
      }
    }
  } catch (error) {
    console.error('Failed to query runs', error);
  }

  const normalized: RunSummary[] = [];
  for (const item of results) {
    const run = normalizeRunRecord(item as RawRunRecord);
    if (run) {
      normalized.push(run);
    }
  }

  return normalized;
}

export const useRunsStore = create<RunsSliceState>((set, get) => ({
  runs: [],
  selectedRunId: null,
  selectRun: (runId) => {
    set({ selectedRunId: runId });
  },
  setRuns: (runs) => {
    set((state) => {
      let selectedRunId = state.selectedRunId;
      if (selectedRunId && !runs.some((run) => run.id === selectedRunId)) {
        selectedRunId = runs.length > 0 ? runs[0].id : null;
      }
      if (!selectedRunId && runs.length > 0) {
        selectedRunId = runs[0].id;
      }
      return { runs: [...runs], selectedRunId };
    });
  },
  queryRuns: async (options) => {
    const runs = await callQueryRuns(options);
    return runs;
  },
  refreshRuns: async (options) => {
    const runs = await get().queryRuns(options);
    set((state) => {
      let selectedRunId = state.selectedRunId;
      if (!selectedRunId && runs.length > 0) {
        selectedRunId = runs[0].id;
      }
      if (selectedRunId && !runs.some((run) => run.id === selectedRunId)) {
        selectedRunId = runs.length > 0 ? runs[0].id : null;
      }
      return { runs, selectedRunId };
    });
    return runs;
  },
}));
