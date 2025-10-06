import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { usePhase1Experiments } from '../hooks/usePhase1Experiments';
import type { ArtifactNode } from '../utils/artifacts';
import { sanitizeArtifactNodes } from '../utils/artifacts';

type ExperimentNavigationContextValue = {
  artifactsRoot: string | null;
  experiments: ArtifactNode[];
  experimentsError: string | null;
  experimentsLoading: boolean;
  selectedExperimentPath: string | null;
  setSelectedExperimentPath: (path: string | null) => void;
  refreshExperiments: () => void;
  hasArtifactsApi: boolean;
  substrates: ArtifactNode[];
  substratesError: string | null;
  substratesLoading: boolean;
  selectedSubstratePath: string | null;
  setSelectedSubstratePath: (path: string | null) => void;
  refreshSubstrates: () => void;
};

const ExperimentNavigationContext = createContext<ExperimentNavigationContextValue | null>(null);

const useArtifactsApi = () =>
  typeof window !== 'undefined' ? window?.CWT?.artifacts : undefined;

const ExperimentNavigationProvider = ({ children }: { children: React.ReactNode }) => {
  const {
    artifactsRoot,
    experiments,
    experimentsError,
    experimentsLoading,
    selectedExperimentPath,
    setSelectedExperimentPath,
    refresh,
    hasArtifactsApi,
  } = usePhase1Experiments();

  const [substrates, setSubstrates] = useState<ArtifactNode[]>([]);
  const [substratesError, setSubstratesError] = useState<string | null>(null);
  const [substratesLoading, setSubstratesLoading] = useState(false);
  const [selectedSubstratePath, setSelectedSubstratePath] = useState<string | null>(null);
  const [substratesRefreshToken, setSubstratesRefreshToken] = useState(0);

  useEffect(() => {
    let cancelled = false;

    if (!selectedExperimentPath) {
      setSubstrates([]);
      setSelectedSubstratePath(null);
      setSubstratesError(experiments.length === 0 ? null : 'Select an experiment to list substrates.');
      setSubstratesLoading(false);
      return () => {
        cancelled = true;
      };
    }

    const api = useArtifactsApi();
    if (!api?.list) {
      setSubstrates([]);
      setSelectedSubstratePath(null);
      setSubstratesError('Artifact listing is unavailable in this build.');
      setSubstratesLoading(false);
      return () => {
        cancelled = true;
      };
    }

    const fetchSubstrates = async () => {
      setSubstratesLoading(true);
      setSubstratesError(null);
      try {
        const response = await api.list({ under: selectedExperimentPath });
        if (cancelled) {
          return;
        }
        if (!response.ok) {
          setSubstrates([]);
          setSelectedSubstratePath(null);
          setSubstratesError(response.error ?? 'Failed to list substrates.');
          return;
        }

        const nodes = sanitizeArtifactNodes(response.data);
        const directories = nodes.filter((node) => node.type === 'directory');
        setSubstrates(directories);
        if (directories.length === 0) {
          setSelectedSubstratePath(null);
          setSubstratesError('No substrate directories found under this experiment.');
        } else {
          setSubstratesError(null);
          setSelectedSubstratePath((previous) => {
            if (previous && directories.some((dir) => dir.path === previous)) {
              return previous;
            }
            return directories[0]?.path ?? null;
          });
        }
      } catch (error) {
        if (cancelled) {
          return;
        }
        const message = error instanceof Error ? error.message : String(error);
        setSubstrates([]);
        setSelectedSubstratePath(null);
        setSubstratesError(message);
      } finally {
        if (!cancelled) {
          setSubstratesLoading(false);
        }
      }
    };

    void fetchSubstrates();

    return () => {
      cancelled = true;
    };
  }, [experiments, hasArtifactsApi, selectedExperimentPath, substratesRefreshToken]);

  useEffect(() => {
    setSelectedSubstratePath(null);
  }, [selectedExperimentPath]);

  const refreshExperiments = useCallback(() => {
    setSubstrates([]);
    setSelectedSubstratePath(null);
    setSubstratesError(null);
    refresh();
  }, [refresh]);

  const refreshSubstrates = useCallback(
    () => setSubstratesRefreshToken((token) => token + 1),
    [],
  );

  const value = useMemo<ExperimentNavigationContextValue>(
    () => ({
      artifactsRoot,
      experiments,
      experimentsError,
      experimentsLoading,
      selectedExperimentPath,
      setSelectedExperimentPath,
      refreshExperiments,
      hasArtifactsApi,
      substrates,
      substratesError,
      substratesLoading,
      selectedSubstratePath,
      setSelectedSubstratePath,
      refreshSubstrates,
    }),
    [
      artifactsRoot,
      experiments,
      experimentsError,
      experimentsLoading,
      selectedExperimentPath,
      setSelectedExperimentPath,
      refreshExperiments,
      hasArtifactsApi,
      substrates,
      substratesError,
      substratesLoading,
      selectedSubstratePath,
      refreshSubstrates,
    ],
  );

  return (
    <ExperimentNavigationContext.Provider value={value}>
      {children}
    </ExperimentNavigationContext.Provider>
  );
};

const useExperimentNavigation = () => {
  const context = useContext(ExperimentNavigationContext);
  if (!context) {
    throw new Error('useExperimentNavigation must be used within ExperimentNavigationProvider');
  }
  return context;
};

export { ExperimentNavigationProvider, useExperimentNavigation };
