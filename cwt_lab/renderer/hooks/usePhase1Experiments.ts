import { useCallback, useEffect, useMemo, useState } from 'react';

import type { ArtifactNode } from '../utils/artifacts';
import { findArtifactNodeByName, isGuidLike, sanitizeArtifactNodes } from '../utils/artifacts';

type UsePhase1ExperimentsOptions = {
  /**
   * When true, only include experiments that contain Phase 1 ridge outputs.
   * Defaults to true because most downstream phases require Phase 1 artifacts.
   */
  requirePhase1Outputs?: boolean;
};

type UsePhase1ExperimentsResult = {
  artifactsRoot: string | null;
  experiments: ArtifactNode[];
  experimentsError: string | null;
  experimentsLoading: boolean;
  selectedExperimentPath: string | null;
  setSelectedExperimentPath: (path: string | null) => void;
  refresh: () => void;
  hasArtifactsApi: boolean;
};

const hasPhase1Outputs = (node: ArtifactNode) =>
  Boolean(findArtifactNodeByName(node.children ?? [], 'top_omega_tiles.json'));

const EXPERIMENTS_UNCONFIGURED_MESSAGE =
  'Artifacts workspace root not configured. Open Env Doctor to set a base directory.';

const EXPERIMENTS_API_UNAVAILABLE_MESSAGE = 'Artifact listing is unavailable in this build.';

export const usePhase1Experiments = (
  options: UsePhase1ExperimentsOptions = {},
): UsePhase1ExperimentsResult => {
  const { requirePhase1Outputs = true } = options;
  const [artifactsRoot, setArtifactsRoot] = useState<string | null>(null);
  const [experiments, setExperiments] = useState<ArtifactNode[]>([]);
  const [experimentsError, setExperimentsError] = useState<string | null>(null);
  const [experimentsLoading, setExperimentsLoading] = useState(false);
  const [selectedExperimentPath, setSelectedExperimentPath] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);

  const hasArtifactsApi = useMemo(
    () => typeof window !== 'undefined' && Boolean(window?.CWT?.artifacts?.list),
    [],
  );

  useEffect(() => {
    let cancelled = false;

    const loadConfig = async () => {
      if (typeof window === 'undefined' || !window?.CWT?.env?.getConfig) {
        setArtifactsRoot(null);
        return;
      }

      try {
        const response = await window.CWT.env.getConfig();
        if (cancelled) {
          return;
        }
        if (response.ok) {
          setArtifactsRoot(response.data.phase2MetricsRoot ?? response.data.artifactsRoot ?? null);
        } else {
          setArtifactsRoot(null);
        }
      } catch {
        if (!cancelled) {
          setArtifactsRoot(null);
        }
      }
    };

    void loadConfig();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    if (!artifactsRoot) {
      setExperiments([]);
      setSelectedExperimentPath(null);
      setExperimentsError(EXPERIMENTS_UNCONFIGURED_MESSAGE);
      setExperimentsLoading(false);
      return () => {
        cancelled = true;
      };
    }

    if (!hasArtifactsApi) {
      setExperiments([]);
      setSelectedExperimentPath(null);
      setExperimentsError(EXPERIMENTS_API_UNAVAILABLE_MESSAGE);
      setExperimentsLoading(false);
      return () => {
        cancelled = true;
      };
    }

    const fetchExperiments = async () => {
      setExperimentsLoading(true);
      setExperimentsError(null);
      try {
        const response = await window!.CWT!.artifacts!.list?.({ under: artifactsRoot });
        if (cancelled) {
          return;
        }
        if (!response?.ok) {
          setExperiments([]);
          setSelectedExperimentPath(null);
          setExperimentsError(response?.error ?? 'Failed to list experiments.');
          return;
        }

        const nodes = sanitizeArtifactNodes(response.data);
        const directories = nodes.filter((node) => node.type === 'directory' && isGuidLike(node.relativePath));
        const filtered = requirePhase1Outputs ? directories.filter(hasPhase1Outputs) : directories;

        setExperiments(filtered);
        if (filtered.length === 0) {
          const message = directories.length > 0
            ? 'No Phase 1 experiments found under the configured root.'
            : 'No experiment folders with GUID names found under the configured root.';
          setExperimentsError(message);
          setSelectedExperimentPath(null);
          return;
        }

        setExperimentsError(null);
        setSelectedExperimentPath((previous) => {
          if (previous && filtered.some((entry) => entry.path === previous)) {
            return previous;
          }
          return filtered[0]?.path ?? null;
        });
      } catch (error) {
        if (cancelled) {
          return;
        }
        const message = error instanceof Error ? error.message : String(error);
        setExperiments([]);
        setSelectedExperimentPath(null);
        setExperimentsError(message);
      } finally {
        if (!cancelled) {
          setExperimentsLoading(false);
        }
      }
    };

    void fetchExperiments();

    return () => {
      cancelled = true;
    };
  }, [artifactsRoot, hasArtifactsApi, refreshToken, requirePhase1Outputs]);

  const refresh = useCallback(() => setRefreshToken((token) => token + 1), []);

  return {
    artifactsRoot,
    experiments,
    experimentsError,
    experimentsLoading,
    selectedExperimentPath,
    setSelectedExperimentPath,
    refresh,
    hasArtifactsApi,
  };
};

export type { UsePhase1ExperimentsResult };
