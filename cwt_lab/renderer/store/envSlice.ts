import type { StateCreator } from 'zustand';

export type PythonEnvInfo = {
  executable: string | null;
  venvRoot: string | null;
  status: 'unknown' | 'available' | 'missing';
};

export type EnvSlice = {
  environment: PythonEnvInfo;
  setEnvironment: (env: PythonEnvInfo) => void;
};

export const createEnvSlice: StateCreator<EnvSlice, [], [], EnvSlice> = (set) => ({
  environment: {
    executable: null,
    venvRoot: null,
    status: 'unknown',
  },
  setEnvironment: (environment) => set({ environment }),
});
