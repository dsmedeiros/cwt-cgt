import type {
  RegistryRunRecord,
  RunDiagnosticsBundle,
  RecipeRecord,
} from '../types/ipc';

export type DemoRun = {
  record: RegistryRunRecord;
  log: string;
  diagnostics: RunDiagnosticsBundle;
};

export type DemoArtifact = {
  id: string;
  phase: string;
  title: string;
  summary: string;
  tags: string[];
  updatedAt: string;
  metrics: Array<{
    label: string;
    value: number;
    unit?: string;
    delta?: number;
    higherIsBetter?: boolean;
    direction?: 'up' | 'down';
  }>;
  traces: Array<{
    name: string;
    x: number[];
    y: number[];
    mode?: 'lines' | 'markers' | 'lines+markers';
  }>;
};

export type DemoRecipe = {
  record: RecipeRecord;
  metrics: Array<{
    label: string;
    value: number;
    unit?: string;
    direction: 'up' | 'down';
  }>;
  history: Array<{
    iteration: number;
    phiFlux: number;
    guard: number;
  }>;
};

const now = Date.now();

let autoId = 0;
const nextId = () => {
  autoId += 1;
  return `demo-auto-${autoId}`;
};

const makeRun = (
  overrides: Partial<RegistryRunRecord>,
  log: string,
  diagnosticsPath: string,
): DemoRun => ({
  record: {
    id: overrides.id ?? nextId(),
    status: overrides.status ?? 'complete',
    command: overrides.command ?? 'python -m cwt.sim.run',
    args: overrides.args ?? ['--config', 'configs/loop.yaml'],
    cwd: overrides.cwd ?? '/opt/cwt',
    phase: overrides.phase ?? 'phase3',
    experiment: overrides.experiment ?? 'loop_tau_zeta',
    label: overrides.label ?? null,
    createdAt: overrides.createdAt ?? now - 60 * 60 * 1000,
    updatedAt: overrides.updatedAt ?? now - 30 * 60 * 1000,
    artifactsDir: overrides.artifactsDir ?? '/opt/cwt/artifacts/demo',
    metrics: overrides.metrics ?? {
      phi_flux: 1.42,
      fs_guard: 0.62,
      omega_peak: 0.018,
    },
  },
  log,
  diagnostics: {
    zipPath: diagnosticsPath,
    files: ['run.log', 'metrics.json', 'config.yaml'],
  },
});

export const demoRuns: DemoRun[] = [
  makeRun(
    {
      id: 'demo-run-001',
      status: 'complete',
      phase: 'phase1',
      experiment: 'map_rho_tau',
      createdAt: now - 6 * 60 * 60 * 1000,
      updatedAt: now - 5.5 * 60 * 60 * 1000,
      metrics: { phi_flux: 1.08, coverage: 0.74, omega_peak: 0.011 },
    },
    `Bootstrapping Phase-1 sweep\nResolved tile grid at 41×41\nΦ guard satisfied (0.92)\n`,
    '/opt/cwt/artifacts/demo/demo-run-001.zip',
  ),
  makeRun(
    {
      id: 'demo-run-002',
      status: 'running',
      phase: 'phase3',
      experiment: 'guided_loop',
      createdAt: now - 90 * 60 * 1000,
      updatedAt: now - 2 * 60 * 1000,
      metrics: { phi_flux: 1.67, fs_guard: 0.71, omega_peak: 0.023 },
    },
    `Launching guided loop\nIteration 18/64 : Φ=1.58, fs=0.62\nIteration 32/64 : Φ=1.61, fs=0.64\n`,
    '/opt/cwt/artifacts/demo/demo-run-002.zip',
  ),
  makeRun(
    {
      id: 'demo-run-003',
      status: 'failed',
      phase: 'phase4',
      experiment: 'wilson_loop',
      createdAt: now - 5 * 60 * 60 * 1000,
      updatedAt: now - 4.8 * 60 * 60 * 1000,
      metrics: { phi_flux: 0.94, fs_guard: 0.88, omega_peak: 0.009 },
    },
    `Starting Wilson loop integration\nWarning: guard drift exceeded at step 144\nRun terminated by guard rail`,
    '/opt/cwt/artifacts/demo/demo-run-003.zip',
  ),
  makeRun(
    {
      id: 'demo-run-004',
      status: 'complete',
      phase: 'phase5',
      experiment: 'graph_family',
      createdAt: now - 48 * 60 * 60 * 1000,
      updatedAt: now - 47.5 * 60 * 60 * 1000,
      metrics: { phi_flux: 1.92, fs_guard: 0.58, persistence: 0.82 },
    },
    `Running topology sweep (ring3, watts_strogatz_p001, periodic_lattice)\nBest Φ observed: 1.92 at τ=0.24, ζ=0.03\nSaved recipe demo-recipe-001`,
    '/opt/cwt/artifacts/demo/demo-run-004.zip',
  ),
  makeRun(
    {
      id: 'demo-run-005',
      status: 'aborted',
      phase: 'phase2',
      experiment: 'correlate',
      createdAt: now - 24 * 60 * 60 * 1000,
      updatedAt: now - 23.8 * 60 * 60 * 1000,
      metrics: { phi_flux: 0.0, fs_guard: 0.0, omega_peak: 0.0 },
    },
    `Loading metrics bundle (3 directories)\nUser aborted after 12 seconds`,
    '/opt/cwt/artifacts/demo/demo-run-005.zip',
  ),
];

export const demoArtifacts: DemoArtifact[] = [
  {
    id: 'artifact-phase1-overview',
    phase: 'phase1',
    title: 'Phase-1 sweep heatmap',
    summary:
      'Dense coverage across 0.55 ≤ τ ≤ 0.72 with a saddle ridge in ζ. Guard satisfied with margin.',
    tags: ['heatmap', 'coverage', 'phase1'],
    updatedAt: new Date(now - 5 * 60 * 60 * 1000).toISOString(),
    metrics: [
      { label: 'Max |Ω|', value: 0.021, unit: '', direction: 'up', higherIsBetter: true },
      { label: 'Coverage', value: 0.78, unit: 'fraction', direction: 'up', higherIsBetter: true },
      { label: 'Guard margin', value: 0.12, unit: '', direction: 'up', higherIsBetter: true },
    ],
    traces: [
      {
        name: 'Ω ridge',
        x: Array.from({ length: 21 }, (_, index) => 0.55 + index * 0.01),
        y: [
          0.91, 0.96, 1.02, 1.08, 1.15, 1.22, 1.26, 1.32, 1.37, 1.41, 1.47, 1.5, 1.48, 1.44, 1.38, 1.31, 1.27, 1.2,
          1.12, 1.05, 0.98,
        ],
        mode: 'lines',
      },
    ],
  },
  {
    id: 'artifact-phase2-correlate',
    phase: 'phase2',
    title: 'Feature correlation snapshot',
    summary: 'Spectral gap and Kuramoto r jointly explain 72% of the Φ uplift variance.',
    tags: ['correlation', 'phase2', 'report'],
    updatedAt: new Date(now - 16 * 60 * 60 * 1000).toISOString(),
    metrics: [
      { label: 'Spectral gap r', value: 0.68, unit: '', direction: 'up', higherIsBetter: true },
      { label: 'Kuramoto r', value: 0.54, unit: '', direction: 'up', higherIsBetter: true },
      { label: 'Trace g', value: -0.31, unit: '', direction: 'down', higherIsBetter: false },
    ],
    traces: [
      {
        name: 'ROC',
        x: [0, 0.08, 0.14, 0.2, 0.26, 0.33, 0.4, 0.48, 0.57, 0.66, 0.75, 0.82, 0.9, 0.96, 1],
        y: [0, 0.18, 0.32, 0.46, 0.58, 0.69, 0.76, 0.82, 0.87, 0.91, 0.94, 0.96, 0.98, 0.99, 1],
        mode: 'lines',
      },
    ],
  },
  {
    id: 'artifact-phase3-loop',
    phase: 'phase3',
    title: 'Guided loop trace',
    summary: 'Guided loop settled after 48 steps with sustained Φ > 1.6 and guard margin 0.08.',
    tags: ['loop', 'timeseries', 'phase3'],
    updatedAt: new Date(now - 9 * 60 * 60 * 1000).toISOString(),
    metrics: [
      { label: 'Peak Φ', value: 1.64, unit: '', direction: 'up', higherIsBetter: true },
      { label: 'Guard margin', value: 0.08, unit: '', direction: 'up', higherIsBetter: true },
      { label: 'Convergence steps', value: 48, unit: 'steps', direction: 'down', higherIsBetter: false },
    ],
    traces: [
      {
        name: 'Φ',
        x: Array.from({ length: 48 }, (_, index) => index + 1),
        y: [
          0.92, 0.97, 1.03, 1.08, 1.12, 1.17, 1.23, 1.28, 1.34, 1.38, 1.41, 1.45, 1.49, 1.52, 1.55, 1.57, 1.6, 1.61,
          1.62, 1.63, 1.63, 1.63, 1.62, 1.62, 1.62, 1.62, 1.61, 1.61, 1.61, 1.6, 1.6, 1.6, 1.6, 1.61, 1.61, 1.61, 1.62,
          1.62, 1.62, 1.63, 1.63, 1.63, 1.64, 1.64, 1.64, 1.64, 1.64,
        ],
        mode: 'lines',
      },
    ],
  },
  {
    id: 'artifact-phase4-scan',
    phase: 'phase4',
    title: 'Wilson loop comparison',
    summary: '3D explorer reveals latent saddle – compare vs planar baseline to pick next axes.',
    tags: ['phase4', '3d', 'comparison'],
    updatedAt: new Date(now - 30 * 60 * 60 * 1000).toISOString(),
    metrics: [
      { label: 'Wilson flux', value: 1.38, unit: '', direction: 'up', higherIsBetter: true },
      { label: 'Baseline Φ', value: 1.12, unit: '', direction: 'up', higherIsBetter: true },
      { label: 'Delta Φ', value: 0.26, unit: '', direction: 'up', higherIsBetter: true },
    ],
    traces: [
      {
        name: '3D path Φ',
        x: Array.from({ length: 32 }, (_, index) => index),
        y: [
          0.98, 1.02, 1.08, 1.12, 1.19, 1.22, 1.28, 1.31, 1.34, 1.36, 1.37, 1.36, 1.35, 1.34, 1.33, 1.35, 1.36, 1.37,
          1.39, 1.38, 1.37, 1.36, 1.35, 1.34, 1.33, 1.32, 1.31, 1.3, 1.29, 1.29, 1.3, 1.31,
        ],
        mode: 'lines',
      },
      {
        name: '2D baseline Φ',
        x: Array.from({ length: 32 }, (_, index) => index),
        y: Array.from({ length: 32 }, () => 1.12),
        mode: 'lines',
      },
    ],
  },
];

const makeRecipeRecord = (
  overrides: Partial<RecipeRecord>,
): RecipeRecord => ({
  id: overrides.id ?? nextId(),
  name: overrides.name ?? 'Demo recipe',
  description:
    overrides.description ??
    'Pre-optimised protocol derived from demo run. Provides a guard-compliant launch point.',
  basedOnRunId: overrides.basedOnRunId ?? 'demo-run-004',
  params: overrides.params ?? {
    metrics: {
      phiFlux: 1.92,
      fsGuard: 0.58,
      persistence: 0.82,
    },
    derivedMetrics: {
      omegaPeak: 0.021,
      guardMargin: 0.12,
    },
  },
  command: overrides.command ?? 'cwt-sim run --config configs/demo.yaml',
  seed: overrides.seed ?? 314159,
  envInfo: overrides.envInfo ?? { python: '3.11.4', cuda: '12.3' },
  createdAt: overrides.createdAt ?? new Date(now - 3 * 60 * 60 * 1000).toISOString(),
});

export const demoRecipes: DemoRecipe[] = [
  {
    record: makeRecipeRecord({
      id: 'demo-recipe-001',
      name: 'Aurora ridge stabiliser',
      createdAt: new Date(now - 20 * 60 * 60 * 1000).toISOString(),
    }),
    metrics: [
      { label: 'Φ flux', value: 1.92, unit: '', direction: 'up' },
      { label: 'Guard margin', value: 0.12, unit: '', direction: 'up' },
      { label: 'Persistence', value: 0.82, unit: '', direction: 'up' },
    ],
    history: Array.from({ length: 12 }, (_, index) => ({
      iteration: index,
      phiFlux: 1.1 + index * 0.07 + Math.sin(index / 2) * 0.02,
      guard: 0.25 - index * 0.01,
    })),
  },
  {
    record: makeRecipeRecord({
      id: 'demo-recipe-002',
      name: 'Helios harmonic booster',
      createdAt: new Date(now - 36 * 60 * 60 * 1000).toISOString(),
      params: {
        metrics: { phiFlux: 1.78, fsGuard: 0.63, persistence: 0.74 },
        derivedMetrics: { omegaPeak: 0.018, guardMargin: 0.09 },
      },
    }),
    metrics: [
      { label: 'Φ flux', value: 1.78, unit: '', direction: 'up' },
      { label: 'Guard margin', value: 0.09, unit: '', direction: 'up' },
      { label: 'Persistence', value: 0.74, unit: '', direction: 'up' },
    ],
    history: Array.from({ length: 12 }, (_, index) => ({
      iteration: index,
      phiFlux: 1.05 + index * 0.065 + Math.cos(index / 3) * 0.03,
      guard: 0.27 - index * 0.012,
    })),
  },
  {
    record: makeRecipeRecord({
      id: 'demo-recipe-003',
      name: 'Borealis guard sentinel',
      createdAt: new Date(now - 12 * 60 * 60 * 1000).toISOString(),
      params: {
        metrics: { phiFlux: 1.65, fsGuard: 0.52, persistence: 0.88 },
        derivedMetrics: { omegaPeak: 0.016, guardMargin: 0.16 },
      },
    }),
    metrics: [
      { label: 'Φ flux', value: 1.65, unit: '', direction: 'up' },
      { label: 'Guard margin', value: 0.16, unit: '', direction: 'up' },
      { label: 'Persistence', value: 0.88, unit: '', direction: 'up' },
    ],
    history: Array.from({ length: 12 }, (_, index) => ({
      iteration: index,
      phiFlux: 1.02 + index * 0.06 + Math.sin(index / 3) * 0.01,
      guard: 0.23 - index * 0.008,
    })),
  },
];

export const demoData = {
  runs: demoRuns,
  artifacts: demoArtifacts,
  recipes: demoRecipes,
};
