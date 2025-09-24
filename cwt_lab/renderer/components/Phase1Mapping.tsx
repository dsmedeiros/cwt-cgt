import { useMemo, useState } from 'react';

import { createDecisionGateEngine } from '../decisionGate';
import { formatValidationMessage, validateAxis, validateExtent } from '../../shared/validators';

const AXIS_OPTIONS = ['rho', 'tau', 'zeta', 'sigma', 'omega'];

const simulatePhase1Metrics = (seed: number, extent: number) => {
  const base = Math.sin(seed * 12.9898 + extent * 78.233) * 43758.5453;
  const normalized = base - Math.floor(base);
  const maxOmega = Number(((normalized < 0.35 ? normalized * 4e-6 : normalized * 5e-5 + 1e-5)).toFixed(7));
  const coverage = Number(Math.min(1, 0.45 + extent * 0.65).toFixed(2));
  return { maxOmega, coverage };
};

const Phase1Mapping = () => {
  const decisionGate = useMemo(() => createDecisionGateEngine(), []);
  const [axisPrimary, setAxisPrimary] = useState(AXIS_OPTIONS[0]);
  const [axisSecondary, setAxisSecondary] = useState(AXIS_OPTIONS[1]);
  const [extent, setExtent] = useState(0.6);
  const [seed, setSeed] = useState(2024);
  const [isRunning, setIsRunning] = useState(false);
  const [maxOmega, setMaxOmega] = useState<number | null>(null);
  const [coverage, setCoverage] = useState<number | null>(null);
  const [tipMessage, setTipMessage] = useState<string | null>(null);

  const axisPrimaryValidation = useMemo(() => validateAxis('phase1', axisPrimary), [axisPrimary]);
  const axisSecondaryValidation = useMemo(() => validateAxis('phase1', axisSecondary), [axisSecondary]);
  const extentValidation = useMemo(() => validateExtent(extent), [extent]);
  const extentError = formatValidationMessage(extentValidation);
  const axisPairError = axisPrimary === axisSecondary ? 'Select two distinct axes.' : null;

  const runDisabledReason = extentValidation.ok
    ? axisPairError ?? (axisPrimaryValidation.ok && axisSecondaryValidation.ok ? undefined : 'Invalid axis selection.')
    : extentValidation.message;
  const isRunDisabled = isRunning || Boolean(runDisabledReason);
  const runTitle = isRunning ? 'Mapping already running.' : runDisabledReason;

  const runMapping = () => {
    if (!extentValidation.ok) {
      return;
    }
    setIsRunning(true);
    setTimeout(() => {
      const metrics = simulatePhase1Metrics(seed, extentValidation.value);
      setMaxOmega(metrics.maxOmega);
      setCoverage(metrics.coverage);
      const tip = decisionGate.evaluate({
        phase: 'phase1',
        omegaMaxAbs: metrics.maxOmega,
      });
      setTipMessage(tip);
      setIsRunning(false);
    }, 160);
  };

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
      <section className="phase1__controls">
        <div className="phase1__field">
          <label htmlFor="phase1-axis-primary">Primary axis</label>
          <select
            id="phase1-axis-primary"
            value={axisPrimary}
            onChange={(event) => setAxisPrimary(event.target.value)}
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
            onChange={(event) => setAxisSecondary(event.target.value)}
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
            value={seed}
            onChange={(event) => setSeed(Number(event.target.value))}
          />
          <small className="field-hint">Tweak to sample a different pseudo-map.</small>
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
              {axisPrimary} / {axisSecondary}
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
        </ul>
      </section>
    </div>
  );
};

export default Phase1Mapping;
