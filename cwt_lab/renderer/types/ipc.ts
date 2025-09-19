export type IpcEnvelope<T> = { ok: true; data: T } | { ok: false; error: string; data?: T };

export type PythonStrategy = 'module' | 'py_path' | 'installed';

export type EnvCandidate = {
  path: string;
  version: string | null;
  ok: boolean;
  strategy: PythonStrategy | null;
  error?: string;
};

export type EnvDetectResult = {
  candidates: EnvCandidate[];
  selected: EnvCandidate | null;
};

export type EnvConfig = {
  repoRoot: string;
  artifactsRoot: string;
  pythonPath: string | null;
  strategy: PythonStrategy | null;
};

export type RunCreatePayload = {
  experiment: string;
  args?: Record<string, unknown>;
  workdir?: string;
};

export type RunCreateResult = {
  runId: string;
};

export type RunAbortPayload = {
  runId: string;
};

export type RunAbortResult = {
  runId: string;
};

export type RunTailPayload = {
  runId: string;
  fromByte?: number;
};

export type RunTailChunk = {
  output: string;
  nextFromByte: number;
  status: string;
};

export type ArtifactsListPayload = {
  under?: string;
};

export type RegistryQueryPayload = {
  phase?: string;
  experiment?: string;
  limit?: number;
};

export type RecipeSavePayload = {
  name: string;
  params: Record<string, unknown>;
  command: string;
  seed?: number;
  envInfo?: unknown;
};

export type RecipeRunPayload = {
  id: string;
};

export interface RendererIpc {
  shutdown: () => Promise<void>;
  env: {
    detect: () => Promise<IpcEnvelope<EnvDetectResult>>;
    setPythonPath: (path: string) => Promise<IpcEnvelope<EnvCandidate>>;
    getConfig: () => Promise<IpcEnvelope<EnvConfig>>;
  };
  run: {
    create: (payload: RunCreatePayload) => Promise<IpcEnvelope<RunCreateResult>>;
    abort: (payload: RunAbortPayload) => Promise<IpcEnvelope<RunAbortResult>>;
    tail: (payload: RunTailPayload) => Promise<IpcEnvelope<RunTailChunk>>;
    openArtifacts: (payload: { runId: string }) => Promise<IpcEnvelope<unknown>>;
  };
  phase1: {
    map: (params: Record<string, unknown>) => Promise<IpcEnvelope<RunCreateResult>>;
  };
  phase2: {
    correlate: (
      payload: {
        metricsDirs: string[];
        thresholdMode?: string;
        thresholdValue?: number;
        percentile?: number;
      },
    ) => Promise<IpcEnvelope<unknown>>;
  };
  phase3: {
    loopAtHotspot: (params: Record<string, unknown>) => Promise<IpcEnvelope<RunCreateResult>>;
    guidedLoop: (
      params: Record<string, unknown>,
    ) => Promise<
      IpcEnvelope<{
        runs: Array<{
          runId: string;
          steps: number;
          status: string;
          metrics: Record<string, number | null> | null;
        }>;
        satisfied: boolean;
      }>
    >;
  };
  phase4: {
    wilson3d: (params: Record<string, unknown>) => Promise<IpcEnvelope<RunCreateResult>>;
    torusPlateau: (params: Record<string, unknown>) => Promise<IpcEnvelope<RunCreateResult>>;
  };
  phase5: {
    graphFamily: (params: Record<string, unknown>) => Promise<IpcEnvelope<RunCreateResult>>;
    inverseDesign: (params: Record<string, unknown>) => Promise<IpcEnvelope<RunCreateResult>>;
    noiseRobust: (params: Record<string, unknown>) => Promise<IpcEnvelope<RunCreateResult>>;
    betaSweep: (
      params: { configPath: string; betas: number[] },
    ) => Promise<
      IpcEnvelope<{
        runs: Array<{ beta: number; runId: string; status: string }>;
        tempDir: string;
      }>
    >;
  };
  artifacts: {
    list: (payload?: ArtifactsListPayload) => Promise<IpcEnvelope<unknown>>;
  };
  registry: {
    query: (payload?: RegistryQueryPayload) => Promise<IpcEnvelope<unknown>>;
  };
  recipes: {
    list: () => Promise<IpcEnvelope<unknown>>;
    save: (payload: RecipeSavePayload) => Promise<IpcEnvelope<unknown>>;
    run: (payload: RecipeRunPayload) => Promise<IpcEnvelope<RunCreateResult>>;
  };
  ping: (payload: string) => Promise<IpcEnvelope<{ pong: string }>>;
  version: () => Promise<IpcEnvelope<{ version: string }>>;
}

declare global {
  interface Window {
    CWT: RendererIpc;
  }
}

export type { RendererIpc as PreloadApi };
