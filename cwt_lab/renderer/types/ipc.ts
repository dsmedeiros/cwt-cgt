import type { AdiabaticBoundaryResult } from '../../shared/adiabatic';

export type IpcEnvelope<T> = { ok: true; data: T } | { ok: false; error: string; data?: T };

export type PythonStrategy = 'module' | 'py_path' | 'installed';

export type BaselineModel = 'ising' | 'kuramoto' | 'percolation' | 'sis';

export type BaselineRunPayload = {
  model: BaselineModel;
  axisMap?: string | null;
  mapToCwt?: boolean | null;
  outputDir?: string | null;
  steps?: number | string | null;
  seed?: number | string | null;
  args?: Array<string | number | null>;
  env?: Record<string, string | number | boolean | null | undefined> | null;
};

export type BaselineRunResult = {
  runId: string;
  model: BaselineModel;
  outputDir: string | null;
  artifactsDir: string;
  command: string;
  args: string[];
  cwd: string;
  cli: string;
  status: 'complete';
  startedAt: number;
  completedAt: number;
  loopMetrics: Record<string, number | null> | null;
};

export type BaselineRunStreamEvent = {
  runId: string;
  stream: 'stdout' | 'stderr';
  chunk: string;
};

export type BaselineRunExitEvent = {
  runId: string;
  code: number | null;
  signal: NodeJS.Signals | null;
};

export type BaselineRunErrorEvent = {
  runId: string;
  message: string;
};

export type GraphFamilyThumbnail = {
  name: string;
  path: string | null;
  dataUrl: string | null;
};

export type GraphFamilySummary = {
  name: string;
  degreeEntropy: number | null;
  clustering: number | null;
  modularity: number | null;
  peakAbsOmega: number | null;
  kappaMean: number | null;
  ridgeAuc: number | null;
  phiMissing: boolean;
  phiFlux: number | null;
  phiFluxMissing: boolean;
  phiGuardOk: boolean;
  fsP95: number | null;
  fsBoundary: number | null;
  fsExceeded: boolean;
  medianAbsOmega: number | null;
  thumbnail: GraphFamilyThumbnail | null;
};

export type GraphFamilyCommandResult = {
  outputDir: string;
  summaryPath: string;
  stdout: string;
  stderr: string;
  axes: [string, string];
  extent: number;
  gridSize: number;
  seed: number;
  runtimeSeconds: number | null;
  families: GraphFamilySummary[];
  command: string;
  args: string[];
  cli: string;
};

export type GraphFamilyCommandPayload = {
  families: string[];
  axes: [string, string];
  gridSize: number;
  extents: number;
  seed: number;
  experimentDir?: string;
};

export type AdiabaticBoundaryRunPayload = {
  outDir?: string;
  experimentDir?: string;
  [extra: string]: unknown;
};

export type InverseDesignControlPoint = {
  index: number;
  axisA: number;
  axisB: number;
};

export type InverseDesignPathSummary = {
  magnitude: number | null;
  guardFraction: number | null;
  length: number | null;
  phiMissing: boolean;
};

export type InverseDesignOptimisedSummary = InverseDesignPathSummary & {
  improvement: number | null;
  controlPoints: InverseDesignControlPoint[];
};

export type InverseDesignCommandResult = {
  stdout: string;
  stderr: string;
  outputDir: string;
  baseline: InverseDesignPathSummary | null;
  optimised: InverseDesignOptimisedSummary | null;
  acceptance: string | null;
  command: string;
  args: string[];
  cli: string;
};

export type InverseDesignCommandPayload = {
  axes: [string, string];
  center: [number, number];
  extentPair: [number, number];
  budgetSteps?: number;
  maxFs?: number;
  targetIndex?: number;
  experimentDir?: string;
};

export type NoiseRobustTrial = {
  seed: number;
  rGamma: number | null;
  overlapAverage: number | null;
  minOverlap: number | null;
  fsSteps: number[];
};

export type NoiseRobustPoint = {
  phaseStd: number;
  ampStd: number;
  delayStd: number;
  signPersistence: number | null;
  overlapMean: number | null;
  coherenceMean: number | null;
  quantized: boolean;
  fsP95: number | null;
  fsMax: number | null;
  trials: NoiseRobustTrial[];
};

export type NoiseRobustGraph = {
  name: string;
  axes: [string, string];
  flux: number | null;
  overlapThreshold: number | null;
  coherenceThreshold: number | null;
  points: NoiseRobustPoint[];
};

export type NoiseRobustCommandResult = {
  stdout: string;
  stderr: string;
  outputDir: string;
  recordsPath: string;
  reportPath: string | null;
  graphs: NoiseRobustGraph[];
  numTrials?: number;
  loopSteps?: number;
  command: string;
  args: string[];
  cli: string;
};

export type NoiseRobustCommandPayload = {
  phaseStd?: number[];
  ampStd?: number[];
  delayStd?: number[];
  numTrials?: number;
  loopSteps?: number;
  gridSize?: number;
  axes?: [string, string];
  experimentDir?: string;
};

export type CouplingVariantSummary = {
  beta: number;
  etaQ: number | null;
  phi: number | null;
  phiMissing: boolean;
  rValue: number | null;
  fsP95: number | null;
  fsBoundary: number | null;
  guardExceeded: boolean;
  runId: string;
  variantConfig: string;
  runDir: string;
};

export type CouplingTunerResult = {
  outputDir: string;
  baselineConfig: string;
  variants: CouplingVariantSummary[];
  bestIndex: number | null;
  commands: string[];
};

export type CouplingTunerPayload = {
  configPath: string;
  betas: number[];
  etaQ?: number | number[];
  experimentDir?: string;
};

export type BetaSweepRunRecord = {
  beta: number;
  runId: string;
  status: string;
};

export type BetaSweepResult = {
  runs: BetaSweepRunRecord[];
  tempDir: string;
  stagingDir?: string;
};

export type Phase2FeatureName = 'spectral_gap' | 'kuramoto_r' | 'grad_r' | 'trace_g';

export type Phase2FeatureStat = {
  name: Phase2FeatureName;
  correlation: number | null;
  sampleSize: number;
  hotCount: number;
  coldCount: number;
  meanHot: number | null;
  meanCold: number | null;
};

export type Phase2Sample = {
  omegaAbs: number | null;
  features: Partial<Record<Phase2FeatureName, number | null>>;
};

export type Phase2RocPoint = {
  threshold: number;
  tpr: number;
  fpr: number;
};

export type Phase2CorrelateResult = {
  features: Phase2FeatureStat[];
  auc?: number;
  roc?: { feature: Phase2FeatureName; points: Phase2RocPoint[] };
  threshold: number | null;
  samples: Phase2Sample[];
};

export type Phase2BrowseResult = {
  canceled: boolean;
  directories: string[];
};

export type Phase2CorrelatePayload = {
  metricsDirs: string[];
  thresholdMode: 'absolute' | 'percentile';
  thresholdValue?: number;
  percentile?: number;
};

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
  phase2MetricsRoot: string | null;
  pythonPath: string | null;
  strategy: PythonStrategy | null;
};

export type EnvBrowseResult = {
  canceled: boolean;
  path: string | null;
};

export type RunCreatePayload = {
  experiment: string;
  args?: Record<string, unknown>;
  workdir?: string;
  timeoutMs?: number;
};

export type RunCreateResult = {
  runId: string;
};

export type RunPreviewPayload = {
  experiment: string;
  args?: Record<string, unknown>;
  workdir?: string;
};

export type RunPreviewResult = {
  command: string;
  args: string[];
  cwd: string;
  env: Record<string, string>;
  cli: string;
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
  maxBytes?: number;
};

export type RunDeletePayload = {
  runId: string;
};

export type RunDeleteResult = {
  runId: string;
};

export type RunTailChunk = {
  output: string;
  nextFromByte: number;
  startFromByte: number;
  totalBytes: number;
  hasMoreBefore: boolean;
  status: string;
  failureDetails: string | null;
};

export type RunDiagnosticsBundle = {
  zipPath: string;
  files: string[];
};

export type RegistryRunRecord = {
  id: string;
  status: 'pending' | 'running' | 'complete' | 'failed' | 'aborted';
  command: string;
  args: string[];
  cwd: string;
  phase: string | null;
  experiment: string | null;
  label: string | null;
  createdAt: number;
  updatedAt: number;
  artifactsDir: string;
  metrics: Record<string, number | null> | null;
};

export type ArtifactFile = {
  path: string;
  relativePath: string;
  updatedAt: number;
  type: 'file' | 'directory';
};

export type RunArtifactEncoding = 'utf-8' | 'base64';

export type RunReadArtifactPayload = {
  runId: string;
  relativePath: string;
  encoding?: RunArtifactEncoding;
};

export type RunReadArtifactResult = {
  path: string;
  contents: string;
  encoding: RunArtifactEncoding;
};

export type LoopAtHotspotPayload = {
  hotspotsJson: string;
  axes: [string, string];
  extents: [number, ...number[]];
  fsGuard: number;
  graph: string;
  limit: number;
  seed: number;
  microScan?: boolean;
  readoutTarget?: number;
  neighborSettleSteps?: number;
  adaptLevels?: number;
  saveSummary?: string;
  experimentDir?: string;
  [extra: string]: unknown;
};

export type Phase3BrowseHotspotsResult = {
  canceled: boolean;
  path: string | null;
  contents: string | null;
};

export type GuidedLoopSummary = {
  path: string;
  axes: [string, string];
  extents: [number, number];
  center: Record<string, number>;
  centerVector?: [number, number, number];
  amplitudes?: [number, number, number];
  label: string;
  metadata?: Record<string, unknown>;
  omegaAbs?: number | null;
};

export type GuidedLoopArgs = {
  axes3: [string, string, string];
  center: [number, number, number];
  amplitudes: [number, number, number];
  graph: string;
  stepsList: number[];
  fsGuard?: number;
  minPhi?: number;
  settle?: number;
  handleSteps?: number;
  seed?: number;
  etaQ?: number;
  zeta?: number;
  omegaScale?: number;
  outputDir?: string;
  summary?: GuidedLoopSummary;
  experimentDir?: string;
  [extra: string]: unknown;
};

export type ArtifactsListPayload = {
  under?: string;
};

export type ArtifactsReadFilePayload = {
  path: string;
};

export type ArtifactsWatchPayload = {
  under?: string;
  depth?: number;
};

export type ArtifactsUnwatchPayload = {
  id: number;
};

export type ArtifactsWatchEvent = {
  id: number;
  kind: 'add' | 'change' | 'unlink' | 'addDir' | 'unlinkDir';
  path: string;
  relativePath: string;
  updatedAt: number;
  type: 'file' | 'directory';
};

export type RegistryQueryPayload = {
  id?: string;
  phase?: string;
  experiment?: string;
  limit?: number;
};

export type RecipeSavePayload = {
  name: string;
  description?: string;
  basedOnRunId?: string | null;
  params: Record<string, unknown>;
  command: string;
  seed?: number | null;
  envInfo?: unknown;
};

export type RecipeRunPayload = {
  id: string;
  experimentDir?: string;
};

export type RecipeExportPayload = {
  id: string;
};

export type RecipeRecord = {
  id: string;
  name: string;
  description: string;
  basedOnRunId: string | null;
  params: Record<string, unknown>;
  command: string;
  seed: number | null;
  envInfo: unknown;
  createdAt: string;
};

export interface RendererIpc {
  shutdown: () => Promise<void>;
  env: {
    detect: () => Promise<IpcEnvelope<EnvDetectResult>>;
    setPythonPath: (path: string) => Promise<IpcEnvelope<EnvCandidate>>;
    getConfig: () => Promise<IpcEnvelope<EnvConfig>>;
    browsePythonExecutable: () => Promise<IpcEnvelope<EnvBrowseResult>>;
    setPhase2MetricsRoot: (
      payload: { path: string | null },
    ) => Promise<IpcEnvelope<{ path: string | null }>>;
  };
  run: {
    create: (payload: RunCreatePayload) => Promise<IpcEnvelope<RunCreateResult>>;
    preview: (payload: RunPreviewPayload) => Promise<IpcEnvelope<RunPreviewResult>>;
    abort: (payload: RunAbortPayload) => Promise<IpcEnvelope<RunAbortResult>>;
    tail: (payload: RunTailPayload) => Promise<IpcEnvelope<RunTailChunk>>;
    openArtifacts: (payload: { runId: string }) => Promise<IpcEnvelope<ArtifactFile[]>>;
    collectDiagnostics: (payload: { runId: string }) => Promise<IpcEnvelope<RunDiagnosticsBundle>>;
    delete: (payload: RunDeletePayload) => Promise<IpcEnvelope<RunDeleteResult>>;
    readArtifact: (
      payload: RunReadArtifactPayload,
    ) => Promise<IpcEnvelope<RunReadArtifactResult>>;
  };
  baselines: {
    run: (payload: BaselineRunPayload) => Promise<IpcEnvelope<BaselineRunResult>>;
    onOutput: (listener: (event: BaselineRunStreamEvent) => void) => () => void;
    onExit: (listener: (event: BaselineRunExitEvent) => void) => () => void;
    onError: (listener: (event: BaselineRunErrorEvent) => void) => () => void;
  };
  phase1: {
    map: (params: Record<string, unknown>) => Promise<IpcEnvelope<RunCreateResult>>;
  };
  phase2: {
    browseMetricsDirs: () => Promise<IpcEnvelope<Phase2BrowseResult>>;
    correlate: (payload: Phase2CorrelatePayload) => Promise<IpcEnvelope<Phase2CorrelateResult>>;
    saveSnapshot: (payload: unknown) => Promise<IpcEnvelope<{ path: string }>>;
  };
  phase3: {
    browseHotspots: () => Promise<IpcEnvelope<Phase3BrowseHotspotsResult>>;
    loopAtHotspot: (params: LoopAtHotspotPayload) => Promise<IpcEnvelope<RunCreateResult>>;
    guidedLoop: (
      params: GuidedLoopArgs,
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
    adiabaticBoundary: (
      payload: AdiabaticBoundaryRunPayload,
    ) => Promise<IpcEnvelope<RunCreateResult>>;
    cmdAdiabaticBoundary: (
      params?: Record<string, unknown>,
    ) => Promise<IpcEnvelope<AdiabaticBoundaryResult>>;
  };
  phase4: {
    wilson3d: (params: Record<string, unknown>) => Promise<IpcEnvelope<RunCreateResult>>;
    torusPlateau: (params: Record<string, unknown>) => Promise<IpcEnvelope<RunCreateResult>>;
  };
  phase5: {
    graphFamily: (params: Record<string, unknown>) => Promise<IpcEnvelope<RunCreateResult>>;
    cmdGraphFamily: (
      params: GraphFamilyCommandPayload,
    ) => Promise<IpcEnvelope<GraphFamilyCommandResult>>;
    inverseDesign: (params: Record<string, unknown>) => Promise<IpcEnvelope<RunCreateResult>>;
    cmdInverseDesign: (
      params: InverseDesignCommandPayload,
    ) => Promise<IpcEnvelope<InverseDesignCommandResult>>;
    noiseRobust: (params: Record<string, unknown>) => Promise<IpcEnvelope<RunCreateResult>>;
    cmdNoiseRobust: (
      params: NoiseRobustCommandPayload,
    ) => Promise<IpcEnvelope<NoiseRobustCommandResult>>;
    betaSweep: (
      params: { configPath: string; betas: number[]; experimentDir?: string },
    ) => Promise<IpcEnvelope<BetaSweepResult>>;
    couplingTuner: (
      params: CouplingTunerPayload,
    ) => Promise<IpcEnvelope<CouplingTunerResult>>;
  };
  artifacts: {
    list: (payload?: ArtifactsListPayload) => Promise<IpcEnvelope<unknown>>;
    readFile: (
      payload: ArtifactsReadFilePayload,
    ) => Promise<IpcEnvelope<{ path: string; contents: string }>>;
    watch: (
      payload?: ArtifactsWatchPayload,
    ) => Promise<IpcEnvelope<{ id: number }>>;
    unwatch: (
      payload: ArtifactsUnwatchPayload,
    ) => Promise<IpcEnvelope<{ id: number }>>;
    onDidChange: (listener: (event: ArtifactsWatchEvent) => void) => () => void;
  };
  registry: {
    query: (
      payload?: RegistryQueryPayload,
    ) => Promise<IpcEnvelope<RegistryRunRecord[]>>;
  };
  recipes: {
    list: () => Promise<IpcEnvelope<RecipeRecord[]>>;
    save: (payload: RecipeSavePayload) => Promise<IpcEnvelope<RecipeRecord>>;
    run: (payload: RecipeRunPayload) => Promise<IpcEnvelope<RunCreateResult>>;
    export: (
      payload: RecipeExportPayload,
    ) => Promise<IpcEnvelope<{ zipPath: string; attachments: string[] }>>;
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
