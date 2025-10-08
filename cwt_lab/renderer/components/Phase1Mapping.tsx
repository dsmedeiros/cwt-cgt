import { useCallback, useEffect, useMemo, useState } from 'react';

import { formatValidationMessage, validateAxis, validateExtent, validateSeed } from '../../shared/validators';
import { useCommandRegistration } from '../commandCenter';
import { phase1, runs } from '../ipc';
import { useExperimentNavigation } from '../navigation/ExperimentNavigationContext';
import type { ArtifactFile } from '../types/ipc';
import {
  findPhase1HeatmapGroups,
  formatPhase1GraphLabel,
  formatPhase1SubstrateLabel,
  phase1HeatmapKinds,
  type Phase1HeatmapKind,
} from '../utils/artifacts';
import Phase1HeatmapViewer, { type HeatmapImage } from './Phase1HeatmapViewer';

const AXIS_OPTIONS = ['rho', 'tau', 'zeta', 'zeta_phase', 'kappa'] as const;

type AxisOption = (typeof AXIS_OPTIONS)[number];

const DEFAULT_AXIS_RANGES: Record<AxisOption, [number, number]> = {
  rho: [0, 3],
  tau: [0.5, 3],
  zeta: [0, 1.5],
  zeta_phase: [-0.5, 0.5],
  kappa: [0.5, 1.5],
};

type HeatmapState = {
  status: 'idle' | 'loading' | 'ready' | 'error';
  runId: string | null;
  items: HeatmapImage[];
  message: string | null;
};

const HEATMAP_POLL_INTERVAL_MS = 3_000;

type AxisRangeSnapshot = {
  axis: AxisOption;
  range: [number, number];
};

const formatAxisLabel = (axis: AxisOption) => axis.replace(/_/g, ' ');

const scaleRange = (axis: AxisOption, extent: number): [number, number] => {
  const [min, max] = DEFAULT_AXIS_RANGES[axis];
  const center = (min + max) / 2;
  const halfWidth = ((max - min) / 2) * extent;
  return [center - halfWidth, center + halfWidth];
};

const computeCoverageFraction = (
  primaryAxis: AxisOption,
  secondaryAxis: AxisOption,
  extent: number,
): number | null => {
  const primarySpan = DEFAULT_AXIS_RANGES[primaryAxis][1] - DEFAULT_AXIS_RANGES[primaryAxis][0];
  const secondarySpan = DEFAULT_AXIS_RANGES[secondaryAxis][1] - DEFAULT_AXIS_RANGES[secondaryAxis][0];
  if (primarySpan <= 0 || secondarySpan <= 0) {
    return null;
  }
  const scaledPrimary = primarySpan * extent;
  const scaledSecondary = secondarySpan * extent;
  const baselineArea = primarySpan * secondarySpan;
  if (baselineArea <= 0) {
    return null;
  }
  return (scaledPrimary * scaledSecondary) / baselineArea;
};

const formatRange = (range: [number, number]) => `${range[0].toFixed(3)} … ${range[1].toFixed(3)}`;

const describeHeatmapKind = (kind: Phase1HeatmapKind) =>
  kind === 'omega_heatmap' ? '|Ω| heatmap' : 'Population heatmap';

const formatHeatmapLabel = (substrate: string, graph: string, kind: Phase1HeatmapKind) => {
  const substrateLabel = formatPhase1SubstrateLabel(substrate);
  const graphLabel = formatPhase1GraphLabel(graph);
  const kindLabel = describeHeatmapKind(kind);
  if (substrateLabel === graphLabel) {
    return `${substrateLabel} – ${kindLabel}`;
  }
  return `${substrateLabel} • ${graphLabel} – ${kindLabel}`;
};

const deriveMaxOmegaValue = (input: unknown): number | null => {
  if (!input) {
    return null;
  }

  const visited = new WeakSet<object>();
  let result: number | null = null;

  const pushValue = (value: unknown) => {
    if (typeof value === 'number' && Number.isFinite(value)) {
      result = result == null ? value : Math.max(result, value);
    } else if (typeof value === 'string') {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) {
        result = result == null ? parsed : Math.max(result, parsed);
      }
    }
  };

  const visit = (node: unknown) => {
    if (!node) {
      return;
    }
    if (Array.isArray(node)) {
      for (const item of node) {
        visit(item);
      }
      return;
    }
    if (typeof node === 'object') {
      const objectNode = node as Record<string, unknown>;
      if (visited.has(objectNode)) {
        return;
      }
      visited.add(objectNode);
      if ('omega_abs' in objectNode) {
        pushValue(objectNode.omega_abs);
      }
      if ('omegaAbs' in objectNode) {
        pushValue(objectNode.omegaAbs);
      }
      for (const value of Object.values(objectNode)) {
        visit(value);
      }
    }
  };

  visit(input);
  return result;
};

const Phase1Mapping = () => {
  const { refreshExperiments } = useExperimentNavigation();
  const [axisPrimary, setAxisPrimary] = useState<AxisOption>(AXIS_OPTIONS[0]);
  const [axisSecondary, setAxisSecondary] = useState<AxisOption>(AXIS_OPTIONS[1]);
  const [extent, setExtent] = useState(0.6);
  const [seedInput, setSeedInput] = useState('2024');
  const [isRunning, setIsRunning] = useState(false);
  const [maxOmega, setMaxOmega] = useState<number | null>(null);
  const [coverage, setCoverage] = useState<number | null>(null);
  const [tipMessage, setTipMessage] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastRunId, setLastRunId] = useState<string | null>(null);
  const [lastRanges, setLastRanges] = useState<
    | { primary: AxisRangeSnapshot; secondary: AxisRangeSnapshot }
    | null
  >(null);
  const [heatmapState, setHeatmapState] = useState<HeatmapState>({
    status: 'idle',
    runId: null,
    items: [],
    message: null,
  });
  const [activeHeatmap, setActiveHeatmap] = useState<HeatmapImage | null>(null);

  const handleHeatmapOpen = useCallback((heatmap: HeatmapImage) => {
    setActiveHeatmap(heatmap);
  }, []);

  const handleHeatmapClose = useCallback(() => {
    setActiveHeatmap(null);
  }, []);

  const isViewerOpen = activeHeatmap != null;

  const axisPrimaryValidation = useMemo(() => validateAxis('phase1', axisPrimary), [axisPrimary]);
  const axisSecondaryValidation = useMemo(() => validateAxis('phase1', axisSecondary), [axisSecondary]);
  const extentValidation = useMemo(() => validateExtent(extent), [extent]);
  const seedValidation = useMemo(() => validateSeed(seedInput), [seedInput]);
  const extentError = formatValidationMessage(extentValidation);
  const seedError = formatValidationMessage(seedValidation);
  const axisPairError = axisPrimary === axisSecondary ? 'Select two distinct axes.' : null;

  const runDisabledReason = (() => {
    if (!extentValidation.ok) {
      return extentValidation.message;
    }
    if (!seedValidation.ok) {
      return seedValidation.message;
    }
    if (axisPairError) {
      return axisPairError;
    }
    if (!axisPrimaryValidation.ok || !axisSecondaryValidation.ok) {
      return 'Invalid axis selection.';
    }
    return undefined;
  })();
  const isRunDisabled = isRunning || Boolean(runDisabledReason);
  const runTitle = isRunning ? 'Mapping already running.' : runDisabledReason;

  const updateMaxOmegaFromArtifacts = useCallback(
    async (runId: string, artifacts: ArtifactFile[], isCancelled: () => boolean) => {
      const topOmegaEntry = artifacts.find((artifact) => {
        if (artifact.type !== 'file') {
          return false;
        }
        const normalized = artifact.relativePath.replace(/\\/g, '/');
        return normalized.endsWith('top_omega_tiles.json');
      });

      if (!topOmegaEntry) {
        return;
      }

      try {
        const response = await runs.readArtifact({
          runId,
          relativePath: topOmegaEntry.relativePath,
        });
        if (isCancelled()) {
          return;
        }
        const parsed = JSON.parse(response.contents) as unknown;
        const derived = deriveMaxOmegaValue(parsed);
        if (isCancelled()) {
          return;
        }
        if (typeof derived === 'number' && Number.isFinite(derived)) {
          setMaxOmega(derived);
        }
      } catch (error) {
        if (!isCancelled()) {
          console.warn(`Failed to refresh max |Ω| from run ${runId}:`, error);
        }
      }
    },
    [setMaxOmega],
  );

  const loadHeatmaps = useCallback(
    async (runId: string, isCancelled: () => boolean) => {
      try {
        const artifacts = await runs.openArtifacts(runId);
        if (isCancelled()) {
          return;
        }

        const groups = findPhase1HeatmapGroups(artifacts);
        const gallery: HeatmapImage[] = [];
        const failures: string[] = [];

        for (const group of groups) {
          for (const kind of phase1HeatmapKinds) {
            const fileEntry = group.files[kind];
            if (!fileEntry) {
              continue;
            }
            try {
              const artifact = await runs.readArtifact({
                runId,
                relativePath: fileEntry.relativePath,
                encoding: 'base64',
              });
              if (isCancelled()) {
                return;
              }
              if (artifact.encoding !== 'base64') {
                failures.push(fileEntry.normalizedPath);
                continue;
              }
              gallery.push({
                substrate: group.substrate,
                graph: group.graph,
                kind,
                relativePath: fileEntry.normalizedPath,
                dataUrl: `data:image/png;base64,${artifact.contents}`,
                label: formatHeatmapLabel(group.substrate, group.graph, kind),
              });
            } catch (error) {
              if (!isCancelled()) {
                console.warn(
                  `Failed to read heatmap artifact ${fileEntry.relativePath} for run ${runId}:`,
                  error,
                );
              }
              failures.push(fileEntry.normalizedPath);
            }
          }
        }

        if (isCancelled()) {
          return;
        }

        const message = failures.length
          ? `Some heatmaps could not be loaded (${failures.length}).`
          : gallery.length === 0
          ? 'No heatmap images were produced for this run.'
          : null;

        setHeatmapState({ status: 'ready', runId, items: gallery, message });
        await updateMaxOmegaFromArtifacts(runId, artifacts, isCancelled);
      } catch (error) {
        if (isCancelled()) {
          return;
        }
        setHeatmapState({
          status: 'error',
          runId,
          items: [],
          message: error instanceof Error ? error.message : String(error),
        });
      }
    },
    [updateMaxOmegaFromArtifacts],
  );

  const runMapping = useCallback(async () => {
    if (
      !extentValidation.ok ||
      !seedValidation.ok ||
      !axisPrimaryValidation.ok ||
      !axisSecondaryValidation.ok ||
      axisPairError
    ) {
      return;
    }

    const primaryAxis = axisPrimaryValidation.value as AxisOption;
    const secondaryAxis = axisSecondaryValidation.value as AxisOption;
    const extentValue = extentValidation.value;
    const seedValue = seedValidation.value;

    const primaryRange = scaleRange(primaryAxis, extentValue);
    const secondaryRange = scaleRange(secondaryAxis, extentValue);
    const payload: Record<string, unknown> = {
      axes: [primaryAxis, secondaryAxis],
      seed: seedValue,
      [`${primaryAxis}Range`]: primaryRange,
      [`${secondaryAxis}Range`]: secondaryRange,
    };

    setIsRunning(true);
    setErrorMessage(null);
    setStatusMessage(null);
    setTipMessage(null);

    try {
      const result = await phase1.map(payload);
      const coverageFraction = computeCoverageFraction(primaryAxis, secondaryAxis, extentValue);
      setCoverage(coverageFraction);
      setMaxOmega(null);
      const nextRunId = result.runId ?? null;
      setLastRunId(nextRunId);
      setHeatmapState({
        status: 'loading',
        runId: nextRunId,
        items: [],
        message: 'Waiting for the latest run to finish…',
      });
      setLastRanges({
        primary: { axis: primaryAxis, range: primaryRange },
        secondary: { axis: secondaryAxis, range: secondaryRange },
      });
      let nextTip: string | null = null;
      if (coverageFraction != null) {
        if (coverageFraction < 0.15) {
          nextTip =
            'Sweep window is extremely narrow. Increase the extent before moving on to avoid missing ridges.';
        } else if (coverageFraction > 0.85) {
          nextTip =
            'Sweep window spans almost the full default range. Consider tightening the extent to focus later phases.';
        }
      }
      setTipMessage(nextTip);
      setStatusMessage(`Mapping run ${result.runId} launched. Track progress in the Run Board.`);
      refreshExperiments();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setIsRunning(false);
    }
  }, [
    axisPairError,
    axisPrimaryValidation,
    axisSecondaryValidation,
    extentValidation,
    refreshExperiments,
    seedValidation,
  ]);

  const runRegistration = useMemo(
    () => ({ handler: () => void runMapping(), description: 'Run Phase-1 mapping' }),
    [runMapping],
  );

  useCommandRegistration({
    run: runRegistration,
  });

  useEffect(() => {
    if (!lastRunId) {
      setHeatmapState((current) =>
        current.status === 'idle'
          ? current
          : { status: 'idle', runId: null, items: [], message: null },
      );
      return;
    }

    let cancelled = false;
    let pollHandle: ReturnType<typeof setTimeout> | null = null;

    const isCancelled = () => cancelled;

    const poll = async (): Promise<void> => {
      if (cancelled) {
        return;
      }
      try {
        const response = await window?.CWT?.registry?.query?.({ id: lastRunId });
        if (!response) {
          throw new Error('Run registry IPC is unavailable');
        }
        if (!response.ok) {
          throw new Error(response.error ?? 'Failed to query run status.');
        }
        const [record] = response.data ?? [];
        if (!record) {
          throw new Error(`Run ${lastRunId} not found in the registry.`);
        }
        if (record.status === 'complete') {
          await loadHeatmaps(lastRunId, isCancelled);
          return;
        }
        if (record.status === 'failed' || record.status === 'aborted') {
          setHeatmapState({
            status: 'error',
            runId: lastRunId,
            items: [],
            message:
              record.status === 'failed'
                ? 'Run failed before producing heatmaps.'
                : 'Run was aborted before producing heatmaps.',
          });
          return;
        }

        setHeatmapState((current) => {
          if (current.status === 'loading' && current.runId === lastRunId) {
            return current;
          }
          return {
            status: 'loading',
            runId: lastRunId,
            items: [],
            message: 'Waiting for the latest run to finish…',
          };
        });

        pollHandle = setTimeout(poll, HEATMAP_POLL_INTERVAL_MS);
      } catch (error) {
        if (cancelled) {
          return;
        }
        setHeatmapState({
          status: 'error',
          runId: lastRunId,
          items: [],
          message: error instanceof Error ? error.message : String(error),
        });
      }
    };

    setHeatmapState({
      status: 'loading',
      runId: lastRunId,
      items: [],
      message: 'Waiting for the latest run to finish…',
    });

    void poll();

    return () => {
      cancelled = true;
      if (pollHandle) {
        clearTimeout(pollHandle);
      }
    };
  }, [lastRunId, loadHeatmaps]);

  return (
    <div className={`panel phase1${isViewerOpen ? ' phase1--viewer-open' : ''}`}>
      <header className="phase1__header">
        <h2>Phase 1 – Mapping</h2>
        <p>
          Configure a coarse sweep across two axes to scout the landscape before diving deeper into
          loops. Once a run finishes, preview the generated heatmaps below to spot promising
          substrates quickly.
        </p>
      </header>
      {tipMessage ? (
        <div className="decision-banner" role="status">
          <div>
            <strong>Next step tip:</strong>
            <span>{` ${tipMessage}`}</span>
          </div>
          <button
            type="button"
            className="btn btn--ghost btn--small"
            onClick={() => setTipMessage(null)}
            aria-label="Dismiss tip"
          >
            ×
          </button>
        </div>
      ) : null}
      {errorMessage ? (
        <div className="phase1__error" role="alert">{errorMessage}</div>
      ) : null}
      {statusMessage ? (
        <p className="phase1__status-note" role="status">{statusMessage}</p>
      ) : null}
      <section className="phase1__controls">
        <div className="phase1__field">
          <label htmlFor="phase1-axis-primary">Primary axis</label>
          <select
            id="phase1-axis-primary"
            value={axisPrimary}
            onChange={(event) => setAxisPrimary(event.target.value as AxisOption)}
          >
            {AXIS_OPTIONS.map((axis) => (
              <option key={axis} value={axis}>
                {axis}
              </option>
            ))}
          </select>
          <small className="field-hint">Baseline axis for the sweep plane.</small>
        </div>
        <div className="phase1__field">
          <label htmlFor="phase1-axis-secondary">Secondary axis</label>
          <select
            id="phase1-axis-secondary"
            value={axisSecondary}
            onChange={(event) => setAxisSecondary(event.target.value as AxisOption)}
          >
            {AXIS_OPTIONS.map((axis) => (
              <option key={axis} value={axis}>
                {axis}
              </option>
            ))}
          </select>
          <small className="field-hint">
            Companion axis to complete the mapping grid.
            {axisPairError ? <span className="field-error"> {axisPairError}</span> : null}
          </small>
        </div>
        <div className="phase1__field">
          <label htmlFor="phase1-extent">
            Extent <strong>{extent.toFixed(2)}</strong>
          </label>
          <input
            id="phase1-extent"
            type="range"
            min="0.1"
            max="1"
            step="0.05"
            value={extent}
            onChange={(event) => setExtent(Number(event.target.value))}
          />
          <small className="field-hint">
            Width of the exploration window.
            {extentError ? <span className="field-error"> {extentError}</span> : null}
          </small>
        </div>
        <div className="phase1__field">
          <label htmlFor="phase1-seed">Seed</label>
          <input
            id="phase1-seed"
            type="number"
            value={seedInput}
            onChange={(event) => setSeedInput(event.target.value)}
          />
          <small className="field-hint">
            Tweak to sample a different pseudo-map.
            {seedError ? <span className="field-error"> {seedError}</span> : null}
          </small>
        </div>
        <div className="phase1__actions">
          <button
            type="button"
            className="btn btn--primary"
            onClick={runMapping}
            disabled={isRunDisabled}
            title={runTitle ?? undefined}
          >
            {isRunning ? 'Mapping…' : 'Run mapping'}
          </button>
        </div>
      </section>
      <section className="phase1__results">
        <h3>Latest sweep</h3>
        <ul>
          <li>
            <span className="phase1__metric-label">Axes</span>
            <strong>
              {lastRanges
                ? `${formatAxisLabel(lastRanges.primary.axis)} / ${formatAxisLabel(lastRanges.secondary.axis)}`
                : `${formatAxisLabel(axisPrimary)} / ${formatAxisLabel(axisSecondary)}`}
            </strong>
          </li>
          <li>
            <span className="phase1__metric-label">Primary range</span>
            <strong>
              {lastRanges ? formatRange(lastRanges.primary.range) : '–'}
            </strong>
          </li>
          <li>
            <span className="phase1__metric-label">Secondary range</span>
            <strong>
              {lastRanges ? formatRange(lastRanges.secondary.range) : '–'}
            </strong>
          </li>
          <li>
            <span className="phase1__metric-label">Max |Ω|</span>
            <strong>{maxOmega != null ? maxOmega.toExponential(2) : '–'}</strong>
          </li>
          <li>
            <span className="phase1__metric-label">Tile coverage</span>
            <strong>{coverage != null ? `${(coverage * 100).toFixed(0)}%` : '–'}</strong>
          </li>
          <li>
            <span className="phase1__metric-label">Run ID</span>
            <strong>{lastRunId ?? '–'}</strong>
          </li>
        </ul>
      </section>
      <section className="phase1__heatmaps">
        <h3>Heatmaps</h3>
        {heatmapState.status === 'ready' && heatmapState.items.length > 0 ? (
          <>
            <div
              className={`phase1__heatmaps-grid${isViewerOpen ? ' phase1__heatmaps-grid--expanded' : ''}`}
            >
              {heatmapState.items.map((item) => (
                <figure
                  key={`${item.substrate}-${item.graph}-${item.kind}`}
                  className="phase1__heatmap"
                >
                  <button
                    type="button"
                    className="phase1__heatmap-button"
                    onClick={() => handleHeatmapOpen(item)}
                    aria-label={`View heatmap for ${item.label}`}
                  >
                    <img src={item.dataUrl} alt={item.label} loading="lazy" />
                  </button>
                  <figcaption>{item.label}</figcaption>
                </figure>
              ))}
            </div>
            {heatmapState.message ? (
              <p className="phase1__heatmaps-note">{heatmapState.message}</p>
            ) : null}
          </>
        ) : (
          <p className="phase1__heatmaps-status">
            {(() => {
              if (heatmapState.status === 'loading') {
                return heatmapState.message ?? 'Waiting for the latest run to finish…';
              }
              if (heatmapState.status === 'error') {
                return heatmapState.message ?? 'Heatmaps could not be loaded.';
              }
              if (heatmapState.status === 'ready') {
                return heatmapState.message ?? 'No heatmap images were produced for this run.';
              }
              return 'Run a mapping sweep to generate heatmaps.';
            })()}
          </p>
        )}
      </section>
      {isViewerOpen && activeHeatmap ? (
        <Phase1HeatmapViewer heatmap={activeHeatmap} onClose={handleHeatmapClose} />
      ) : null}
    </div>
  );
};

export default Phase1Mapping;
