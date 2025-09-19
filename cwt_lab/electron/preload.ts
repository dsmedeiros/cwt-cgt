import { contextBridge, ipcRenderer } from 'electron';

type Envelope<T> = { ok: true; data: T } | { ok: false; error: string };

type Api = {
  shutdown: () => Promise<void>;
  env: {
    detect: () => Promise<Envelope<{ executable: string | null; venvRoot: string | null; status: 'available' }>>;
    setPythonPath: (path: string) => Promise<Envelope<{ executable: string | null; venvRoot: string | null }>>;
    getConfig: () => Promise<Envelope<{ repoRoot: string; cwtSimRoot: string; artifactsRoot: string; registryPath: string; recipesPath: string }>>;
  };
  run: {
    create: (
      payload: { experiment: string; args?: Record<string, unknown>; workdir?: string },
    ) => Promise<Envelope<{ runId: string }>>;
    abort: (payload: { runId: string }) => Promise<Envelope<{ runId: string }>>;
    tail: (payload: { runId: string; fromByte?: number }) => Promise<Envelope<{ output: string; nextFromByte: number; status: string }>>;
    openArtifacts: (payload: { runId: string }) => Promise<Envelope<unknown>>;
  };
  phase1: {
    map: (params: Record<string, unknown>) => Promise<Envelope<{ runId: string }>>;
  };
  phase2: {
    correlate: (
      payload: { metricsDirs: string[]; thresholdMode?: string; thresholdValue?: number; percentile?: number },
    ) => Promise<Envelope<unknown>>;
  };
  phase3: {
    loopAtHotspot: (params: Record<string, unknown>) => Promise<Envelope<{ runId: string }>>;
    guidedLoop: (
      params: Record<string, unknown>,
    ) => Promise<
      Envelope<{
        runs: Array<{ runId: string; steps: number; status: string; metrics: Record<string, number | null> | null }>;
        satisfied: boolean;
      }>
    >;
  };
  phase4: {
    wilson3d: (params: Record<string, unknown>) => Promise<Envelope<{ runId: string }>>;
    torusPlateau: (params: Record<string, unknown>) => Promise<Envelope<{ runId: string }>>;
  };
  phase5: {
    graphFamily: (params: Record<string, unknown>) => Promise<Envelope<{ runId: string }>>;
    inverseDesign: (params: Record<string, unknown>) => Promise<Envelope<{ runId: string }>>;
    noiseRobust: (params: Record<string, unknown>) => Promise<Envelope<{ runId: string }>>;
    betaSweep: (
      params: { configPath: string; betas: number[] },
    ) => Promise<
      Envelope<{
        runs: Array<{ beta: number; runId: string; status: string }>;
        tempDir: string;
      }>
    >;
  };
  artifacts: {
    list: (payload?: { under?: string }) => Promise<Envelope<unknown>>;
  };
  registry: {
    query: () => Promise<Envelope<unknown>>;
  };
  recipes: {
    list: () => Promise<Envelope<unknown>>;
    save: (
      payload: { name: string; params: Record<string, unknown>; command: string; seed?: number; envInfo?: unknown },
    ) => Promise<Envelope<unknown>>;
    run: (payload: { id: string }) => Promise<Envelope<{ runId: string }>>;
  };
  ping: (payload: string) => Promise<Envelope<{ pong: string }>>;
  version: () => Promise<Envelope<{ version: string }>>;
};

const invoke = <T>(channel: string, payload?: unknown) => ipcRenderer.invoke(channel, payload) as Promise<Envelope<T>>;

const api: Api = {
  shutdown: () => ipcRenderer.invoke('cwt:shutdown'),
  env: {
    detect: () => invoke('cwt:env:detect'),
    setPythonPath: (path) => invoke('cwt:env:set-python-path', path),
    getConfig: () => invoke('cwt:env:get-config'),
  },
  run: {
    create: (payload) => invoke('cwt:run:create', payload),
    abort: (payload) => invoke('cwt:run:abort', payload),
    tail: (payload) => invoke('cwt:run:tail', payload),
    openArtifacts: (payload) => invoke('cwt:run:open-artifacts', payload),
  },
  phase1: {
    map: (params) => invoke('cwt:phase1:map', params),
  },
  phase2: {
    correlate: (payload) => invoke('cwt:phase2:correlate', payload),
  },
  phase3: {
    loopAtHotspot: (params) => invoke('cwt:phase3:loop-at-hotspot', params),
    guidedLoop: (params) => invoke('cwt:phase3:guided-loop', params),
  },
  phase4: {
    wilson3d: (params) => invoke('cwt:phase4:wilson3d', params),
    torusPlateau: (params) => invoke('cwt:phase4:torus-plateau', params),
  },
  phase5: {
    graphFamily: (params) => invoke('cwt:phase5:graph-family', params),
    inverseDesign: (params) => invoke('cwt:phase5:inverse-design', params),
    noiseRobust: (params) => invoke('cwt:phase5:noise-robust', params),
    betaSweep: (params) => invoke('cwt:phase5:beta-sweep', params),
  },
  artifacts: {
    list: (payload) => invoke('cwt:artifacts:list', payload),
  },
  registry: {
    query: () => invoke('cwt:registry:query'),
  },
  recipes: {
    list: () => invoke('cwt:recipes:list'),
    save: (payload) => invoke('cwt:recipes:save', payload),
    run: (payload) => invoke('cwt:recipes:run', payload),
  },
  ping: (payload) => invoke('cwt:ping', payload),
  version: () => invoke('cwt:get-version'),
};

const frozenApi: Readonly<Api> = Object.freeze(api);

contextBridge.exposeInMainWorld('cwtLab', frozenApi);

export type PreloadApi = typeof frozenApi;
