import { useCallback, useMemo, useState } from 'react';

import { formatValidationMessage, validateAxis, validateExtent, validateSeed } from '../../shared/validators';
import { useCommandRegistration } from '../commandCenter';
import { phase1 } from '../ipc';
import { useExperimentNavigation } from '../navigation/ExperimentNavigationContext';

const AXIS_OPTIONS = ['rho', 'tau', 'zeta', 'zeta_phase', 'kappa'] as const;

type AxisOption = (typeof AXIS_OPTIONS)[number];

const DEFAULT_AXIS_RANGES: Record<AxisOption, [number, number]> = {
  rho: [0, 3],
  tau: [0.5, 3],
  zeta: [0, 1.5],
  zeta_phase: [-0.5, 0.5],
  kappa: [0.5, 1.5],
};

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
      setLastRunId(result.runId ?? null);
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

  return (
    <div className="panel phase1">
      <header className="phase1__header">
        <h2>Phase 1 – Mapping</h2>
        <p>
          Configure a coarse sweep across two axes to scout the landscape before diving deeper into loops.
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
    </div>
  );
};

export default Phase1Mapping;
