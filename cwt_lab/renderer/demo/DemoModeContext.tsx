import { createContext, useContext, useMemo } from 'react';
import type { ReactNode } from 'react';

import { demoData, type DemoArtifact, type DemoRecipe, type DemoRun } from './demoData';

type DemoModeContextValue = {
  enabled: boolean;
  toggle: () => void;
  runs: DemoRun[];
  artifacts: DemoArtifact[];
  recipes: DemoRecipe[];
};

const DemoModeContext = createContext<DemoModeContextValue | undefined>(undefined);

type DemoModeProviderProps = {
  enabled: boolean;
  onToggle: () => void;
  children: ReactNode;
};

export const DemoModeProvider = ({ enabled, onToggle, children }: DemoModeProviderProps) => {
  const value = useMemo(
    () => ({
      enabled,
      toggle: onToggle,
      runs: enabled ? demoData.runs : [],
      artifacts: enabled ? demoData.artifacts : [],
      recipes: enabled ? demoData.recipes : [],
    }),
    [enabled, onToggle],
  );

  return <DemoModeContext.Provider value={value}>{children}</DemoModeContext.Provider>;
};

export const useDemoMode = () => {
  const context = useContext(DemoModeContext);
  if (!context) {
    throw new Error('useDemoMode must be used within DemoModeProvider');
  }
  return context;
};

export type { DemoArtifact, DemoRecipe, DemoRun } from './demoData';
