import type { StateCreator } from 'zustand';

import type { EnvCandidate, EnvConfig } from '../types/ipc';

export type PythonEnvInfo = {
  candidates: EnvCandidate[];
  selected: EnvCandidate | null;
  config: EnvConfig | null;
  status: 'unknown' | 'available' | 'missing';
  error?: string;
};

export type EnvSlice = {
  environment: PythonEnvInfo;
  setEnvironment: (env: PythonEnvInfo) => void;
};

export const createEnvSlice: StateCreator<EnvSlice, [], [], EnvSlice> = (set) => ({
  environment: {
    candidates: [],
    selected: null,
    config: null,
    status: 'unknown',
    error: undefined,
  },
  setEnvironment: (environment) => set({ environment }),
});
