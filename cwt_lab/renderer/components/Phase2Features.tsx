import { type ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
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

const formatNumber = (value: number | null | undefined, digits = 3) => {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '–';
  }
  return Number(value).toFixed(digits);
};

const isFiniteNumber = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value);

const uniqueDirsFromFiles = (files: FileList | null): string[] => {
  if (!files) {
    return [];
  }
  const dirs = new Set<string>();
  Array.from(files).forEach((file) => {
    if (file.name.toLowerCase() !== 'metrics.csv') {
      return;
    }
    const candidate = (file as File & { path?: string }).path;
    if (!candidate) {
      return;
    }
    const slashIndex = Math.max(candidate.lastIndexOf('/'), candidate.lastIndexOf('\\'));
    dirs.add(slashIndex >= 0 ? candidate.slice(0, slashIndex) : candidate);
  });
  return Array.from(dirs);
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

  return `Predictive markers: ${fragments.join(' ')}${thresholdSummary}`;
};

const Phase2Features = () => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
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

  useEffect(() => {
    if (fileInputRef.current) {
      fileInputRef.current.setAttribute('webkitdirectory', 'true');
      fileInputRef.current.setAttribute('directory', 'true');
    }
  }, []);

  const handleBrowse = () => {
    fileInputRef.current?.click();
  };

  const onFilesSelected = (event: ChangeEvent<HTMLInputElement>) => {
    const dirs = uniqueDirsFromFiles(event.target.files);
    if (dirs.length > 0) {
      setMetricsDirs((prev) => Array.from(new Set([...prev, ...dirs])));
    }
    // reset input to allow selecting same directory again
    event.target.value = '';
  };

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
      if (abortRef.current?.aborted) {
        return;
      }
      setIsLoading(false);
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
          line: { dash: 'dot', color: '#999' },
          hoverinfo: 'skip',
        } as Data,
      ],
      layout: {
        margin: { t: 20, r: 10, b: 40, l: 40 },
        xaxis: { title: { text: 'False positive rate' }, range: [0, 1] },
        yaxis: { title: { text: 'True positive rate' }, range: [0, 1] },
        height: 240,
        legend: { orientation: 'h' },
      } as Partial<Layout>,
    };
  }, [result]);

  const scatterPoints = useMemo(() => {
    if (!result || !scatterFeature) {
      return [];
    }
    return result.samples
      .map((sample) => {
        const omega = sample.omegaAbs;
        const featureValue = sample.features[scatterFeature] ?? null;
        const hot = isFiniteNumber(result.threshold) && isFiniteNumber(omega)
          ? (omega as number) >= (result.threshold as number)
          : null;
        return {
          omega,
          value: featureValue,
          hot,
        };
      })
      .filter((entry) => isFiniteNumber(entry.omega) && isFiniteNumber(entry.value));
  }, [result, scatterFeature]);

  const scatterTrace = useMemo(() => {
    if (!scatterPoints.length || !scatterFeature) {
      return null;
    }

    const filtered = scatterPoints.filter((point) =>
      scatterScale === 'log' ? (point.omega as number) > 0 : true,
    );
    if (filtered.length === 0) {
      return null;
    }
    const colors = filtered.map((point) =>
      point.hot === null
        ? 'rgba(100,149,237,0.7)'
        : point.hot
        ? 'rgba(220,53,69,0.7)'
        : 'rgba(65,105,225,0.7)',
    );

    return {
      data: [
        {
          x: filtered.map((point) => point.omega as number),
          y: filtered.map((point) => point.value as number),
          type: 'scatter',
          mode: 'markers',
          marker: {
            color: colors,
            size: 8,
            line: { color: '#fff', width: 1 },
          },
          name: FEATURE_DISPLAY_NAMES[scatterFeature] ?? scatterFeature,
          hovertemplate: '|Ω|=%{x:.3f}<br>Feature=%{y:.3f}<extra></extra>',
        } as Data,
      ],
      layout: {
        margin: { t: 20, r: 10, b: 50, l: 60 },
        xaxis: {
          title: { text: '|Ω|' },
          type: scatterScale,
          rangemode: scatterScale === 'log' ? 'tozero' : undefined,
        },
        yaxis: {
          title: { text: FEATURE_DISPLAY_NAMES[scatterFeature] ?? scatterFeature },
        },
        height: 320,
        shapes:
          isFiniteNumber(result?.threshold)
            ? [
                {
                  type: 'line',
                  x0: result?.threshold ?? undefined,
                  x1: result?.threshold ?? undefined,
                  y0: Math.min(...filtered.map((point) => point.value as number)),
                  y1: Math.max(...filtered.map((point) => point.value as number)),
                  line: { color: 'rgba(220,53,69,0.6)', width: 2, dash: 'dash' },
                },
              ]
            : [],
      } as Partial<Layout>,
    };
  }, [scatterPoints, scatterFeature, scatterScale, result]);

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
    <div className="panel">
      <h2>Phase 2 – Feature Correlations</h2>
      <p>
        Load Phase‑1 metrics directories to inspect how engineered features correlate with thermal outcomes.
        Choose a classification threshold on |Ω| and compare correlation strength, ROC/AUC estimates, and
        per-sample scatter relationships.
      </p>

      <section className="controls">
        <h3>Inputs</h3>
        <div className="control-group">
          <button type="button" onClick={handleBrowse} disabled={isLoading}>
            Select Phase‑1 output directories
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            style={{ display: 'none' }}
            onChange={onFilesSelected}
          />
        </div>
        {metricsDirs.length > 0 && (
          <ul className="dir-list">
            {metricsDirs.map((dir) => (
              <li key={dir}>
                <span>{dir}</span>
                <button type="button" onClick={() => removeDir(dir)} disabled={isLoading}>
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="control-group threshold">
          <label>
            <input
              type="radio"
              name="thresholdMode"
              value="absolute"
              checked={thresholdMode === 'absolute'}
              onChange={() => setThresholdMode('absolute')}
              disabled={isLoading}
            />
            Absolute |Ω|
          </label>
          <input
            type="number"
            value={absoluteThreshold}
            onChange={(event) => setAbsoluteThreshold(event.target.value)}
            disabled={isLoading || thresholdMode !== 'absolute'}
            step="0.01"
          />

          <label>
            <input
              type="radio"
              name="thresholdMode"
              value="percentile"
              checked={thresholdMode === 'percentile'}
              onChange={() => setThresholdMode('percentile')}
              disabled={isLoading}
            />
            Percentile
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
          {thresholdMode === 'percentile' ? (
            <small className="field-hint">
              Keeps only the hottest percentile of tiles.
              {percentileError ? <span className="field-error"> {percentileError}</span> : null}
            </small>
          ) : (
            <small className="field-hint">Switch to percentile mode to clip noisy extremes.</small>
          )}
        </div>

        <div className="control-group">
          <button type="button" onClick={runCorrelation} disabled={isAnalyzeDisabled} title={analyzeTitle ?? undefined}>
            {isLoading ? 'Analyzing…' : 'Analyze correlations'}
          </button>
        </div>
      </section>

      {error && <div className="error">{error}</div>}

      {result && (
        <section className="results">
          <h3>Feature selection</h3>
          <div className="feature-checkboxes">
            {result.features.map((feature) => (
              <label key={feature.name}>
                <input
                  type="checkbox"
                  checked={selectedFeatures.includes(feature.name)}
                  onChange={() => toggleFeature(feature.name)}
                />
                {FEATURE_DISPLAY_NAMES[feature.name] ?? feature.name}
              </label>
            ))}
          </div>

          <div className="charts">
            <div className="chart">
              <h4>Correlation strength</h4>
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
                <p>No features selected.</p>
              )}
            </div>
            <div className="chart">
              <h4>ROC / AUC</h4>
              {rocCurve ? (
                <Plot data={rocCurve.data} layout={rocCurve.layout} config={{ displayModeBar: false }} />
              ) : (
                <p>ROC curve unavailable for the current selection.</p>
              )}
              {isFiniteNumber(result.auc) && (
                <p className="auc">AUC ≈ {formatNumber(result.auc, 3)}</p>
              )}
            </div>
          </div>

          <div className="scatter-controls">
            <label>
              Feature for scatter plot
              <select
                value={scatterFeature ?? ''}
                onChange={(event) =>
                  setScatterFeature((event.target.value as Phase2FeatureName) || null)
                }
              >
                {result.features.map((feature) => (
                  <option key={feature.name} value={feature.name}>
                    {FEATURE_DISPLAY_NAMES[feature.name] ?? feature.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Scale
              <select value={scatterScale} onChange={(event) => setScatterScale(event.target.value as 'linear' | 'log')}>
                <option value="linear">Linear</option>
                <option value="log">Log</option>
              </select>
            </label>
          </div>

          <div className="chart">
            <h4>Scatter (feature vs |Ω|)</h4>
            {scatterTrace ? (
              <Plot
                data={scatterTrace.data}
                layout={scatterTrace.layout}
                config={{ displayModeBar: false }}
              />
            ) : (
              <p>No scatter data available.</p>
            )}
          </div>

          <div className="summary">
            <h4>Plain-English summary</h4>
            <p>{summary}</p>
          </div>

          <div className="snapshot">
            <button type="button" onClick={handleSaveSnapshot} disabled={isLoading}>
              Save snapshot
            </button>
            {snapshotStatus && <span className="status">{snapshotStatus}</span>}
          </div>

          <table className="stats-table">
            <thead>
              <tr>
                <th>Feature</th>
                <th>r</th>
                <th>Samples</th>
                <th>Hot mean</th>
                <th>Cold mean</th>
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
        </section>
      )}
    </div>
  );
};

export default Phase2Features;
