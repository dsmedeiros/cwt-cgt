import type { LoopStdoutMetrics } from './parsers';

export type CalibrationState = {
  runId: string;
  metrics: LoopStdoutMetrics[];
  iteration: number;
};

export const createCalibrationState = (runId: string): CalibrationState => ({
  runId,
  metrics: [],
  iteration: 0,
});

export const updateCalibration = (
  state: CalibrationState,
  metrics: LoopStdoutMetrics[],
): CalibrationState => ({
  ...state,
  metrics: [...state.metrics, ...metrics],
  iteration: state.iteration + 1,
});

export const pickNextPhase = (state: CalibrationState): number => {
  if (state.metrics.length === 0) {
    return 1;
  }

  const lastMetric = state.metrics[state.metrics.length - 1];
  if (lastMetric.value != null && lastMetric.value < 0.5) {
    return 5;
  }

  return ((state.iteration + 1) % 5) + 1;
};
