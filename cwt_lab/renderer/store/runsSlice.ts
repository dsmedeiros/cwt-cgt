import type { StateCreator } from 'zustand';

export type RunSummary = {
  id: string;
  status: 'pending' | 'running' | 'complete' | 'failed';
  createdAt: number;
};

export type RunsSlice = {
  runs: RunSummary[];
  setRuns: (runs: RunSummary[]) => void;
};

export const createRunsSlice: StateCreator<RunsSlice, [], [], RunsSlice> = (set) => ({
  runs: [],
  setRuns: (runs) => set({ runs }),
});
