import type { PythonEnvironment } from './env';

export type Phase = 1 | 2 | 3 | 4 | 5;

export type CommandSpec = {
  phase: Phase;
  argv: string[];
  cwd?: string;
};

const phaseEntrypoints: Record<Phase, string> = {
  1: 'phase1_mapping.py',
  2: 'phase2_features.py',
  3: 'phase3_loops.py',
  4: 'phase4_explorer3d.py',
  5: 'phase5_optimize.py',
};

export const buildPhaseCommand = (
  env: PythonEnvironment,
  phase: Phase,
  runId: string,
): CommandSpec => {
  const script = phaseEntrypoints[phase];

  return {
    phase,
    argv: [env.executable, '-m', 'cwt_sim.pipeline', script, '--run', runId],
  };
};

export const buildRegistryRefresh = (): CommandSpec => ({
  phase: 1,
  argv: ['echo', 'registry refresh not yet implemented'],
});
