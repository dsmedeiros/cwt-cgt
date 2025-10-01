import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Plot from 'react-plotly.js';
import type { Data, Layout } from 'plotly.js';

import { phase2 } from '../ipc';
import { formatValidationMessage, validatePercentile } from '../../shared/validators';
import type { Phase2CorrelateResult, Phase2FeatureName, Phase2RocPoint } from '../types/ipc';
import { useCommandRegistration } from '../commandCenter';

const FEATURE_DISPLAY_NAMES: Record<Phase2FeatureName, string> = {
  spectral_gap: 'Spectral gap',
  kuramoto_r: 'Readout bias R',
  grad_r: '∇r',
  trace_g: 'Trace g',
};

const FEATURE_DESCRIPTIONS: Record<Phase2FeatureName, string> = {
  spectral_gap:
    'Shows how separated the two dominant signal modes are. Large gaps imply cleaner contrast between hot and cold behaviour.',
  kuramoto_r:
    'Measures how strongly the readout phases align. Higher R suggests the system locked into a coherent hot state.',
  grad_r:
    'Captures how quickly the readout bias changes across the layout. Steep gradients can hint at unstable or localized heating.',
  trace_g:
    'Summarises the total strength of the coupling matrix. Higher trace g can mean the system transfers heat more efficiently.',
};

const SCALE_DESCRIPTIONS: Record<'linear' | 'log', string> = {
  linear:
    'Linear keeps equal spacing between values so you can see raw differences. It is best when feature values cover a narrow range.',
  log:
    'Log compresses very large numbers and stretches small ones. Use it when a few outliers hide the structure near zero.',
};

const formatNumber = (value: number | null | undefined, digits = 3) => {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '–';
  }
  return Number(value).toFixed(digits);
};

const isFiniteNumber = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value);

const describeCorrelationStrength = (value: number) => {
  if (value >= 0.6) {
    return 'strong separation between hot and cold tiles';
  }
  if (value >= 0.3) {
    return 'some predictive power, though additional data could help';
  }
  return 'weak separation—consider gathering more samples or adjusting the threshold';
};

const describeNextSteps = (value: number) => {
  if (value >= 0.6) {
    return 'The signal is clear enough to move into Phase 3 unless other checks disagree.';
  }
  if (value >= 0.3) {
    return 'You can explore Phase 3, but plan to confirm by rerunning Phase 1 if resources allow.';
  }
  return 'Hold on Phase 3 for now; re-run Phase 1 with different settings or more samples to firm up the trend.';
};

const buildSummary = (result: Phase2CorrelateResult | null): string => {
  if (!result || result.features.length === 0) {
    return 'Predictive markers: No feature statistics available.';
  }

  const ranked = result.features
    .filter((feature) => isFiniteNumber(feature.correlation))
    .sort((a, b) => Math.abs((b.correlation as number) ?? 0) - Math.abs((a.correlation as number) ?? 0))
    .slice(0, 3);

  if (ranked.length === 0) {
    return 'Predictive markers: No reliable correlations detected.';
  }

  const fragments = ranked.map((feature) => {
    const label = FEATURE_DISPLAY_NAMES[feature.name] ?? feature.name;
    const direction = (feature.correlation as number) >= 0 ? 'High' : 'Low';
    const target = (feature.correlation as number) >= 0 ? 'hot tiles' : 'cold tiles';
    return `${direction} ${label} correlates with ${target} (r=${formatNumber(feature.correlation, 2)}).`;
  });

  const thresholdSummary = isFiniteNumber(result.threshold)
    ? ` Threshold applied at |Ω| ≈ ${formatNumber(result.threshold, 2)}.`
    : '';

  const strongest = ranked[0];
  const maxAbs = Math.abs(strongest?.correlation ?? 0);
  const strengthSummary = maxAbs > 0 ? ` Overall this indicates ${describeCorrelationStrength(maxAbs)}.` : '';
  const nextSteps = maxAbs > 0 ? ` ${describeNextSteps(maxAbs)}` : '';
  const aucSummary = isFiniteNumber(result.auc)
    ? ` The ROC/AUC estimate (≈${formatNumber(result.auc, 2)}) shows how reliably the chosen threshold separates hot from cold outcomes.`
    : '';

  return `Predictive markers: ${fragments.join(' ')}${thresholdSummary}${strengthSummary}${aucSummary}${nextSteps}`;
};

const Phase2Features = () => {
  const [metricsDirs, setMetricsDirs] = useState<string[]>([]);
  const [thresholdMode, setThresholdMode] = useState<'absolute' | 'percentile'>('absolute');
  const [absoluteThreshold, setAbsoluteThreshold] = useState('1.0');
  const [percentileThreshold, setPercentileThreshold] = useState('90');
  const [selectedFeatures, setSelectedFeatures] = useState<Phase2FeatureName[]>([]);
  const [scatterFeature, setScatterFeature] = useState<Phase2FeatureName | null>(null);
  const [scatterScale, setScatterScale] = useState<'linear' | 'log'>('linear');
  const [result, setResult] = useState<Phase2CorrelateResult | null>(null);
  const [summary, setSummary] = useState<string>(buildSummary(null));
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [snapshotStatus, setSnapshotStatus] = useState<string | null>(null);
  const abortRef = useRef<{ aborted: boolean } | null>(null);

  const percentileValidation = useMemo(() => validatePercentile(percentileThreshold), [percentileThreshold]);
  const percentileError = thresholdMode === 'percentile' ? formatValidationMessage(percentileValidation) : null;
  const isAnalyzeDisabled = isLoading || (thresholdMode === 'percentile' && !percentileValidation.ok);
  const analyzeTitle = isLoading
    ? 'Correlation analysis already running.'
    : thresholdMode === 'percentile' && !percentileValidation.ok
      ? percentileValidation.message
      : undefined;

  const handleBrowse = useCallback(async () => {
    try {
      const { canceled, directories } = await phase2.browseMetricsDirs();
      if (canceled) {
        return;
      }

      const sanitized = Array.from(
        new Set(
          directories
            .map((dir) => dir.trim())
            .filter((dir): dir is string => dir.length > 0),
        ),
      );

      if (sanitized.length === 0) {
        return;
      }

      setMetricsDirs((prev) => {
        const next = [...prev];
        sanitized.forEach((dir) => {
          if (!next.includes(dir)) {
            next.push(dir);
          }
        });
        return next;
      });
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [setError, setMetricsDirs]);

  const removeDir = (dir: string) => {
    setMetricsDirs((prev) => prev.filter((entry) => entry !== dir));
  };

  const validateThreshold = useCallback((): number | null => {
    if (thresholdMode === 'absolute') {
      const value = Number(absoluteThreshold);
      if (!Number.isFinite(value)) {
        setError('Absolute threshold must be numeric.');
        return null;
      }
      return value;
    }
    if (!percentileValidation.ok) {
      setError(percentileValidation.message);
      return null;
    }
    return percentileValidation.value;
  }, [absoluteThreshold, percentileValidation, thresholdMode]);

  const runCorrelation = useCallback(async () => {
    if (metricsDirs.length === 0) {
      setError('Select at least one Phase-1 output directory.');
      return;
    }
    const thresholdValue = validateThreshold();
    if (thresholdValue === null) {
      return;
    }

    abortRef.current = { aborted: false };
    setIsLoading(true);
    setError(null);
    setSnapshotStatus(null);
    try {
      const payload =
        thresholdMode === 'absolute'
          ? { metricsDirs, thresholdMode, thresholdValue }
          : { metricsDirs, thresholdMode, percentile: thresholdValue };
      const stats = await phase2.correlate(payload);
      if (abortRef.current?.aborted) {
        return;
      }
      setResult(stats);
      const names = stats.features.map((feature) => feature.name);
      setSelectedFeatures(names);
      setScatterFeature((prev) => (prev && names.includes(prev) ? prev : names[0] ?? null));
      setSummary(buildSummary(stats));
    } catch (err) {
      if (abortRef.current?.aborted) {
        return;
      }
      setResult(null);
      setSummary(buildSummary(null));
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      if (!abortRef.current?.aborted) {
        setIsLoading(false);
      }
    }
  }, [metricsDirs, thresholdMode, validateThreshold]);

  const abortCorrelation = useCallback(() => {
    if (!isLoading || !abortRef.current) {
      return;
    }
    abortRef.current.aborted = true;
    setIsLoading(false);
    setSummary(buildSummary(null));
    setError('Correlation aborted by user.');
  }, [isLoading]);


  useEffect(() => {
    return () => {
      if (abortRef.current) {
        abortRef.current.aborted = true;
      }
    };
  }, []);

  const runRegistration = useMemo(
    () => ({ handler: () => void runCorrelation(), description: 'Run Phase-2 correlation' }),
    [runCorrelation],
  );
  const abortRegistration = useMemo(
    () => (isLoading ? { handler: abortCorrelation, description: 'Abort Phase-2 correlation' } : null),
    [abortCorrelation, isLoading],
  );

  useCommandRegistration({
    run: runRegistration,
    abort: abortRegistration,
  });

  const toggleFeature = (name: Phase2FeatureName) => {
    setSelectedFeatures((prev) =>
      prev.includes(name) ? prev.filter((entry) => entry !== name) : [...prev, name],
    );
  };

  const barData = useMemo(() => {
    if (!result) {
      return null;
    }
    const active = result.features.filter((feature) => selectedFeatures.includes(feature.name));
    if (active.length === 0) {
      return null;
    }
    return {
      x: active.map((feature) => FEATURE_DISPLAY_NAMES[feature.name] ?? feature.name),
      y: active.map((feature) => feature.correlation ?? 0),
      type: 'bar' as const,
      marker: {
        color: active.map((feature) =>
          (feature.correlation ?? 0) >= 0 ? 'rgba(34,139,34,0.7)' : 'rgba(220,53,69,0.7)',
        ),
      },
      text: active.map((feature) => formatNumber(feature.correlation, 2)),
      textposition: 'auto' as const,
    } as Data;
  }, [result, selectedFeatures]);

  const rocCurve = useMemo(() => {
    if (!result?.roc) {
      return null;
    }
    const points = result.roc.points as Phase2RocPoint[];
    if (!points.length) {
      return null;
    }
    const sorted = [...points].sort((a, b) => a.fpr - b.fpr);
    return {
      data: [
        {
          x: sorted.map((point) => point.fpr),
          y: sorted.map((point) => point.tpr),
          type: 'scatter',
          mode: 'lines+markers',
          name: FEATURE_DISPLAY_NAMES[result.roc.feature] ?? result.roc.feature,
          line: { color: 'rgba(65,105,225,0.8)', width: 2 },
          marker: { size: 6 },
        } as Data,
        {
          x: [0, 1],
          y: [0, 1],
          type: 'scatter',
          mode: 'lines',
          name: 'Chance',
          line: { dash: 'dash', color: 'rgba(107,114,128,0.6)' },
        } as Data,
      ],
      layout: {
        margin: { t: 30, r: 10, b: 50, l: 45 },
        xaxis: { title: { text: 'FPR' }, range: [0, 1] },
        yaxis: { title: { text: 'TPR' }, range: [0, 1] },
        height: 320,
      } as Partial<Layout>,
    };
  }, [result]);

  type ScatterPoint = { value: number; omega: number };
  const scatterPoints = useMemo<ScatterPoint[] | null>(() => {
    if (!result || !scatterFeature) {
      return null;
    }
    const points = result.samples
      .map((sample) => {
        const value = sample.features?.[scatterFeature] ?? null;
        const omega = sample.omegaAbs;
        if (!Number.isFinite(value) || !Number.isFinite(omega)) {
          return null;
        }
        return { value: value as number, omega: omega as number } satisfies ScatterPoint;
      })
      .filter((point): point is ScatterPoint => point !== null);
    return points.length > 0 ? points : null;
  }, [result, scatterFeature]);

  const scatterTrace = useMemo(() => {
    if (!scatterPoints?.length || !scatterFeature) {
      return null;
    }
    return {
      data: [
        {
          x: scatterPoints.map((point) => point.value),
          y: scatterPoints.map((point) => point.omega),
          type: 'scatter',
          mode: 'markers',
          marker: { size: 6, color: 'rgba(37,99,235,0.75)' },
          name: FEATURE_DISPLAY_NAMES[scatterFeature] ?? scatterFeature,
        } as Data,
      ],
      layout: {
        margin: { t: 30, r: 10, b: 60, l: 60 },
        xaxis: {
          title: { text: FEATURE_DISPLAY_NAMES[scatterFeature] ?? scatterFeature },
          type: scatterScale,
        },
        yaxis: { title: { text: '|Ω|' }, type: 'linear' },
        height: 320,
      } as Partial<Layout>,
    };
  }, [scatterPoints, scatterFeature, scatterScale]);

  const handleSaveSnapshot = useCallback(async () => {
    if (!result) {
      return;
    }
    const thresholdValue = validateThreshold();
    if (thresholdValue === null) {
      return;
    }
    setSnapshotStatus('Saving snapshot…');
    try {
      const payload = {
        metricsDirs,
        threshold: {
          mode: thresholdMode,
          value: thresholdValue,
        },
        appliedThreshold: result.threshold,
        selectedFeatures,
        scatterFeature,
        scatterScale,
        summary,
        result,
      };
      const response = await phase2.saveSnapshot(payload);
      setSnapshotStatus(`Snapshot saved to ${response.path}`);
    } catch (err) {
      setSnapshotStatus(`Failed to save snapshot: ${err instanceof Error ? err.message : String(err)}`);
    }
  }, [
    metricsDirs,
    thresholdMode,
    selectedFeatures,
    scatterFeature,
    scatterScale,
    summary,
    result,
    validateThreshold,
  ]);

  return (
    <div className="panel phase2">
      <header className="phase2__header">
        <h2>Phase 2 – Feature Correlations</h2>
        <p>
          Load Phase‑1 metrics directories to inspect how engineered features correlate with thermal outcomes.
          Tune the |Ω| decision threshold to explore correlation strength, ROC/AUC estimates, and per-sample
          scatter relationships before advancing to subsequent phases.
        </p>
      </header>

      <section className="phase2__inputs" aria-labelledby="phase2-inputs-heading">
        <div className="phase2__inputs-heading">
          <h3 id="phase2-inputs-heading">Inputs</h3>
          <p className="field-hint">Select one or more Phase‑1 output directories produced by mapping runs.</p>
        </div>
        <div className="phase2__actions">
          <button
            type="button"
            className="btn btn--primary"
            onClick={handleBrowse}
            disabled={isLoading}
          >
            Select Phase‑1 output directories
          </button>
        </div>
        {metricsDirs.length > 0 ? (
          <ul className="phase2__dir-list">
            {metricsDirs.map((dir) => (
              <li key={dir} className="phase2__dir-item">
                <span className="phase2__dir-label">{dir}</span>
                <button
                  type="button"
                  className="btn btn--ghost btn--small"
                  onClick={() => removeDir(dir)}
                  disabled={isLoading}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="phase2__empty">No metrics directories selected yet.</p>
        )}

        <fieldset className="phase2__threshold">
          <legend>Classification threshold</legend>
          <div className="phase2__threshold-options">
            <label className="phase2__radio">
              <input
                type="radio"
                name="thresholdMode"
                value="absolute"
                checked={thresholdMode === 'absolute'}
                onChange={() => setThresholdMode('absolute')}
                disabled={isLoading}
              />
              <span>Absolute |Ω|</span>
            </label>
            <input
              type="number"
              value={absoluteThreshold}
              onChange={(event) => setAbsoluteThreshold(event.target.value)}
              disabled={isLoading || thresholdMode !== 'absolute'}
              step="0.01"
            />

            <label className="phase2__radio">
              <input
                type="radio"
                name="thresholdMode"
                value="percentile"
                checked={thresholdMode === 'percentile'}
                onChange={() => setThresholdMode('percentile')}
                disabled={isLoading}
              />
              <span>Percentile</span>
            </label>
            <input
              type="number"
              min="1"
              max="99"
              value={percentileThreshold}
              onChange={(event) => setPercentileThreshold(event.target.value)}
              disabled={isLoading || thresholdMode !== 'percentile'}
              step="1"
            />
          </div>
          <p className="field-hint">
            {thresholdMode === 'percentile' ? (
              <>
                Keeps only the hottest percentile of tiles.
                {percentileError ? <span className="field-error"> {percentileError}</span> : null}
              </>
            ) : (
              'Switch to percentile mode to clip noisy extremes.'
            )}
          </p>
        </fieldset>

        <div className="phase2__actions">
          <button
            type="button"
            className="btn btn--primary"
            onClick={runCorrelation}
            disabled={isAnalyzeDisabled}
            title={analyzeTitle ?? undefined}
          >
            {isLoading ? 'Analyzing…' : 'Analyze correlations'}
          </button>
        </div>
        {error ? <div className="phase2__error" role="alert">{error}</div> : null}
      </section>

      {result ? (
        <section className="phase2__results" aria-live="polite">
          <header className="phase2__results-header">
            <h3>Feature selection</h3>
            <div className="phase2__results-actions">
              <button
                type="button"
                className="btn btn--ghost btn--small"
                onClick={handleSaveSnapshot}
                disabled={isLoading}
              >
                Save snapshot
              </button>
              {snapshotStatus ? (
                <span
                  className={`phase2__status${snapshotStatus.startsWith('Failed') ? ' phase2__status--error' : ''}`}
                  role="status"
                >
                  {snapshotStatus}
                </span>
              ) : null}
            </div>
          </header>

          <div className="phase2__feature-selector">
            {result.features.map((feature) => (
              <label key={feature.name} className="phase2__checkbox">
                <input
                  type="checkbox"
                  checked={selectedFeatures.includes(feature.name)}
                  onChange={() => toggleFeature(feature.name)}
                />
                <span title={FEATURE_DESCRIPTIONS[feature.name] ?? undefined}>
                  {FEATURE_DISPLAY_NAMES[feature.name] ?? feature.name}
                </span>
              </label>
            ))}
          </div>

          <div className="phase2__charts">
            <article className="phase2__chart">
              <h4>
                <span title="Shows how tightly each feature tracks the hot-vs-cold outcome. Bars near ±1 signal a strong link, while values near 0 mean the feature has little predictive value.">
                  Correlation strength
                </span>
              </h4>
              {barData ? (
                <Plot
                  data={[barData]}
                  layout={{
                    margin: { t: 30, r: 10, b: 60, l: 60 },
                    yaxis: { title: { text: 'Point-biserial r' }, range: [-1, 1] },
                    height: 320,
                  } as Partial<Layout>}
                  config={{ displayModeBar: false }}
                />
              ) : (
                <p className="phase2__empty">Select at least one feature to render the bar chart.</p>
              )}
            </article>
            <article className="phase2__chart">
              <h4>
                <span title="Compares the true-positive and false-positive rates across thresholds. Curves that bow toward the top-left and AUC values near 1.0 indicate reliable hot/cold separation.">
                  ROC / AUC
                </span>
              </h4>
              {rocCurve ? (
                <Plot data={rocCurve.data} layout={rocCurve.layout} config={{ displayModeBar: false }} />
              ) : (
                <p className="phase2__empty">ROC curve unavailable for the current selection.</p>
              )}
              {isFiniteNumber(result.auc) ? (
                <p className="phase2__auc">AUC ≈ {formatNumber(result.auc, 3)}</p>
              ) : null}
            </article>
          </div>

          <div className="phase2__scatter-controls">
            <label>
              <span title="Highlight how an individual feature changes as tile temperatures cross your |Ω| cut. Use the descriptions below or hover over each option for more context.">
                Feature for scatter plot
              </span>
              <select
                value={scatterFeature ?? ''}
                onChange={(event) => setScatterFeature((event.target.value as Phase2FeatureName) || null)}
                aria-describedby="scatter-feature-hint"
              >
                {result.features.map((feature) => (
                  <option
                    key={feature.name}
                    value={feature.name}
                    title={FEATURE_DESCRIPTIONS[feature.name] ?? undefined}
                  >
                    {FEATURE_DISPLAY_NAMES[feature.name] ?? feature.name}
                  </option>
                ))}
              </select>
              <p className="field-hint" id="scatter-feature-hint">
                {scatterFeature ? FEATURE_DESCRIPTIONS[scatterFeature] : 'Select a feature to view its relationship to |Ω|.'}
              </p>
            </label>
            <label>
              <span title="Switch between linear and logarithmic x-axes. Each view keeps the same story but emphasises different parts of the feature range.">
                Scale
              </span>
              <select
                value={scatterScale}
                onChange={(event) => setScatterScale(event.target.value as 'linear' | 'log')}
                aria-describedby="scatter-scale-hint"
              >
                <option value="linear" title={SCALE_DESCRIPTIONS.linear}>
                  Linear
                </option>
                <option value="log" title={SCALE_DESCRIPTIONS.log}>
                  Log
                </option>
              </select>
              <p className="field-hint" id="scatter-scale-hint">
                {SCALE_DESCRIPTIONS[scatterScale]}
              </p>
            </label>
          </div>

          <article className="phase2__chart phase2__chart--wide">
            <h4>Scatter (feature vs |Ω|)</h4>
            {scatterTrace ? (
              <Plot data={scatterTrace.data} layout={scatterTrace.layout} config={{ displayModeBar: false }} />
            ) : (
              <p className="phase2__empty">No scatter data available.</p>
            )}
          </article>

          <section className="phase2__summary">
            <h4>Plain-language summary</h4>
            <p>{summary}</p>
          </section>

          <div className="phase2__table-wrapper">
            <table className="phase2__table">
              <thead>
                <tr>
                  <th scope="col">Feature</th>
                  <th scope="col">r</th>
                  <th scope="col">Samples</th>
                  <th scope="col">Hot mean</th>
                  <th scope="col">Cold mean</th>
                </tr>
              </thead>
              <tbody>
                {result.features.map((feature) => (
                  <tr key={feature.name}>
                    <td>{FEATURE_DISPLAY_NAMES[feature.name] ?? feature.name}</td>
                    <td>{formatNumber(feature.correlation, 3)}</td>
                    <td>{feature.sampleSize}</td>
                    <td>{formatNumber(feature.meanHot, 3)}</td>
                    <td>{formatNumber(feature.meanCold, 3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : (
        <p className="phase2__placeholder" role="status">
          Run the correlation analysis to populate feature rankings, ROC curves, and scatter comparisons.
        </p>
      )}
    </div>
  );

};

export default Phase2Features;
