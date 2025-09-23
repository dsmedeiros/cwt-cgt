import { useMemo, useState } from 'react';
import Plot from 'react-plotly.js';
import type { Datum, Layout, PlotData } from 'plotly.js';

import type {
  AdiabaticBoundaryResult,
  AdiabaticHistogram,
  AdiabaticSurfaceSample,
} from '../../shared/adiabatic';

const formatNumber = (value: number | null | undefined, digits = 3) => {
  if (value == null || Number.isNaN(value)) {
    return '–';
  }
  return Number(value).toFixed(digits);
};

const buildSurfaceMatrix = (surface: AdiabaticSurfaceSample[]) => {
  const extentSet = new Set<number>();
  const stepSet = new Set<number>();
  for (const sample of surface) {
    extentSet.add(sample.extent);
    stepSet.add(sample.steps);
  }

  const extents = Array.from(extentSet).sort((a, b) => a - b);
  const steps = Array.from(stepSet).sort((a, b) => a - b);
  const map = new Map<string, number | null>();
  for (const sample of surface) {
    map.set(`${sample.extent}|${sample.steps}`, sample.kappa1 ?? null);
  }

  const matrix = extents.map((extent) =>
    steps.map((stepsValue) => map.get(`${extent}|${stepsValue}`) ?? null),
  );

  return { extents, steps, matrix };
};

const estimateHistogramDomain = (surface: AdiabaticSurfaceSample[]) => {
  const fsValues = surface
    .map((sample) => sample.fsP95)
    .filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
  if (fsValues.length === 0) {
    return 0.4;
  }
  const maxValue = Math.max(...fsValues);
  return Math.max(0.4, maxValue * 1.25);
};

const buildHistogramTrace = (
  histogram: AdiabaticHistogram,
  surface: AdiabaticSurfaceSample[],
) => {
  const domain = estimateHistogramDomain(surface);
  const binCount = histogram.bins.length;
  if (binCount === 0) {
    return { x: [], y: [] };
  }
  const step = domain / binCount;
  const x = histogram.bins.map((_, index) => Number(((index + 0.5) * step).toFixed(4)));
  return { x, y: histogram.bins };
};

const DEFAULT_CENTER = { tau: 0.8, zeta: 0 };
const DEFAULT_EXTENTS = [0.02, 0.04, 0.08];
const DEFAULT_STEPS = [400, 200, 120, 80];
const DEFAULT_GRID_SIZE = 6;

const parseNumber = (value: string): number | null => {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }

  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
};

const parseFloatList = (value: string): number[] | null => {
  const tokens = value
    .split(/[\s,]+/)
    .map((token) => token.trim())
    .filter((token) => token.length > 0);
  if (tokens.length === 0) {
    return null;
  }

  const parsed: number[] = [];
  for (const token of tokens) {
    const numberValue = Number(token);
    if (!Number.isFinite(numberValue)) {
      return null;
    }
    parsed.push(numberValue);
  }
  return parsed;
};

const parseIntegerList = (value: string): number[] | null => {
  const floats = parseFloatList(value);
  if (!floats) {
    return null;
  }
  const parsed: number[] = [];
  for (const entry of floats) {
    if (!Number.isFinite(entry)) {
      return null;
    }
    const rounded = Math.round(entry);
    if (Math.abs(entry - rounded) > 1e-6) {
      return null;
    }
    parsed.push(rounded);
  }
  return parsed;
};

const toCliValue = (value: number) => Number(value.toFixed(6)).toString();

const AdiabaticBoundaryViewer = () => {
  const [centerTau, setCenterTau] = useState(() => DEFAULT_CENTER.tau.toString());
  const [centerZeta, setCenterZeta] = useState(() => DEFAULT_CENTER.zeta.toString());
  const [extentsInput, setExtentsInput] = useState(() => DEFAULT_EXTENTS.join(', '));
  const [stepsInput, setStepsInput] = useState(() => DEFAULT_STEPS.join(', '));
  const [gridSizeInput, setGridSizeInput] = useState(() => DEFAULT_GRID_SIZE.toString());
  const [result, setResult] = useState<AdiabaticBoundaryResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  const runAnalysis = async () => {
    if (!window?.CWT?.phase3?.cmdAdiabaticBoundary) {
      setError('Adiabatic boundary command is unavailable.');
      return;
    }

    const tau = parseNumber(centerTau);
    const zeta = parseNumber(centerZeta);
    if (tau == null || zeta == null) {
      setError('Provide numeric values for the τ and ζ center.');
      return;
    }

    const extents = parseFloatList(extentsInput);
    if (!extents || extents.length === 0) {
      setError('Provide at least one numeric extent (comma or space separated).');
      return;
    }

    const steps = parseIntegerList(stepsInput);
    if (!steps || steps.length === 0) {
      setError('Provide at least one integer step count (comma or space separated).');
      return;
    }

    const gridSizeNumber = parseIntegerList(gridSizeInput)?.[0];
    if (gridSizeNumber == null || gridSizeNumber <= 0) {
      setError('Grid size must be a positive integer.');
      return;
    }

    setIsRunning(true);
    setError(null);
    try {
      const response = await window.CWT.phase3.cmdAdiabaticBoundary({
        center: `tau=${toCliValue(tau)},zeta=${toCliValue(zeta)}`,
        extents: extents.map((value) => toCliValue(value)),
        steps,
        gridSize: gridSizeNumber,
      });
      if (!response.ok) {
        throw new Error(response.error ?? 'Failed to run adiabatic boundary sweep');
      }
      setResult(response.data);
      const preferred = response.data.recommendation;
      if (preferred) {
        setSelectedKey(`${preferred.extent}|${preferred.steps}`);
      } else if (response.data.histograms.length > 0) {
        const first = response.data.histograms[0];
        setSelectedKey(`${first.extent}|${first.steps}`);
      } else {
        setSelectedKey(null);
      }
    } catch (analysisError) {
      setError(analysisError instanceof Error ? analysisError.message : String(analysisError));
    } finally {
      setIsRunning(false);
    }
  };

  const surfaceMatrix = useMemo(() => {
    if (!result?.surface?.length) {
      return null;
    }
    return buildSurfaceMatrix(result.surface);
  }, [result]);

  const histogramOptions = useMemo(() => {
    if (!result) {
      return [] as Array<{ key: string; label: string }>;
    }
    return result.histograms.map((hist) => ({
      key: `${hist.extent}|${hist.steps}`,
      label: `Extent ${hist.extent.toFixed(3)} — Steps ${hist.steps}`,
    }));
  }, [result]);

  const activeHistogram = useMemo(() => {
    if (!result || !selectedKey) {
      return null;
    }
    return result.histograms.find((hist) => `${hist.extent}|${hist.steps}` === selectedKey) ?? null;
  }, [result, selectedKey]);

  const activeSurfaceSample = useMemo(() => {
    if (!result || !selectedKey) {
      return null;
    }
    const [extentText, stepsText] = selectedKey.split('|');
    const extent = Number(extentText);
    const steps = Number(stepsText);
    return (
      result.surface.find(
        (sample) => Math.abs(sample.extent - extent) < 1e-6 && sample.steps === steps,
      ) ?? null
    );
  }, [result, selectedKey]);

  const histogramTrace = useMemo(() => {
    if (!activeHistogram || !result) {
      return { x: [], y: [] };
    }
    return buildHistogramTrace(activeHistogram, result.surface);
  }, [activeHistogram, result]);

  const surfacePlot = useMemo(() => {
    if (!surfaceMatrix) {
      return null;
    }
    const data: Partial<PlotData>[] = [
      {
        type: 'surface',
        x: surfaceMatrix.steps,
        y: surfaceMatrix.extents,
        z: surfaceMatrix.matrix as unknown as Datum[][],
        colorscale: 'Viridis',
        showscale: true,
      },
    ];
    const layout: Partial<Layout> = {
      autosize: true,
      margin: { l: 40, r: 10, b: 40, t: 10 },
      scene: {
        xaxis: { title: { text: 'Steps' } },
        yaxis: { title: { text: 'Extent' } },
        zaxis: { title: { text: 'κ₁' } },
      },
    };
    return { data, layout };
  }, [surfaceMatrix]);

  const histogramPlot = useMemo(() => {
    if (histogramTrace.x.length === 0 || histogramTrace.y.length === 0) {
      return null;
    }
    const data: Partial<PlotData>[] = [
      {
        type: 'bar',
        x: histogramTrace.x as unknown as Datum[],
        y: histogramTrace.y as unknown as Datum[],
        marker: { color: '#2563eb' },
      },
    ];
    const layout: Partial<Layout> = {
      autosize: true,
      margin: { l: 40, r: 10, b: 40, t: 10 },
      xaxis: { title: { text: 'FS distance (rad)' } },
      yaxis: { title: { text: 'Normalized count' } },
    };
    return { data, layout };
  }, [histogramTrace]);

  return (
    <div className="adiabatic">
      <header className="adiabatic__header">
        <div>
          <h3>Adiabatic boundary</h3>
          <p>Map κ₁ across step counts and loop extents to highlight adiabatic safety margins.</p>
        </div>
        <div className="adiabatic__actions">
          <button
            type="button"
            className="btn btn--primary"
            onClick={runAnalysis}
            disabled={isRunning}
          >
            {isRunning ? 'Mapping…' : 'Find boundary'}
          </button>
        </div>
      </header>

      <div className="adiabatic__controls">
        <label>
          <span>Center τ</span>
          <input
            type="number"
            step="0.01"
            value={centerTau}
            onChange={(event) => setCenterTau(event.target.value)}
          />
        </label>
        <label>
          <span>Center ζ</span>
          <input
            type="number"
            step="0.01"
            value={centerZeta}
            onChange={(event) => setCenterZeta(event.target.value)}
          />
        </label>
        <label className="adiabatic__controls--wide">
          <span>Extent sweep (comma or space separated)</span>
          <input
            type="text"
            value={extentsInput}
            onChange={(event) => setExtentsInput(event.target.value)}
            placeholder="0.02, 0.04, 0.08"
          />
        </label>
        <label className="adiabatic__controls--wide">
          <span>Step counts (comma or space separated)</span>
          <input
            type="text"
            value={stepsInput}
            onChange={(event) => setStepsInput(event.target.value)}
            placeholder="400, 200, 120, 80"
          />
        </label>
        <label>
          <span>Grid size</span>
          <input
            type="number"
            min={1}
            step={1}
            value={gridSizeInput}
            onChange={(event) => setGridSizeInput(event.target.value)}
          />
        </label>
      </div>

      {error ? <div className="adiabatic__error">{error}</div> : null}

      {result ? (
        <>
          <div className="adiabatic__badges">
            {result.recommendation ? (
              <span className="badge badge--success">
                Safe zone ≤ extent {formatNumber(result.recommendation.extent, 3)}, steps ≥{' '}
                {result.recommendation.steps}
              </span>
            ) : (
              <span className="badge">Boundary not yet determined</span>
            )}
            {result.fsGuard.recommended != null ? (
              <span className="badge">
                FS guard ≈ {formatNumber(result.fsGuard.recommended, 3)} rad (p95)
              </span>
            ) : null}
            {result.fsGuard.maxObserved != null ? (
              <span className="badge">
                Observed max FS p95 {formatNumber(result.fsGuard.maxObserved, 3)} rad
              </span>
            ) : null}
            {result.referenceKappa != null ? (
              <span className="badge">Reference κ₁ {formatNumber(result.referenceKappa, 3)}</span>
            ) : null}
          </div>

          {surfacePlot ? (
            <div className="adiabatic__plot">
              <Plot
                data={surfacePlot.data}
                layout={surfacePlot.layout}
                config={{ displaylogo: false, responsive: true }}
                style={{ width: '100%', height: '100%' }}
              />
            </div>
          ) : (
            <p className="adiabatic__hint">No surface samples were produced.</p>
          )}

          <div className="adiabatic__grid">
            <section className="adiabatic__section">
              <h4>Boundary trace</h4>
              <table className="adiabatic__table">
                <thead>
                  <tr>
                    <th>Extent</th>
                    <th>Boundary steps</th>
                    <th>κ₁ at boundary</th>
                    <th>FS p95</th>
                  </tr>
                </thead>
                <tbody>
                  {result.boundary.length > 0 ? (
                    result.boundary.map((point) => (
                      <tr key={point.extent}>
                        <td>{formatNumber(point.extent, 3)}</td>
                        <td>{point.boundarySteps ?? '–'}</td>
                        <td>{formatNumber(point.boundaryKappa, 3)}</td>
                        <td>{formatNumber(point.boundaryFsP95, 3)}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className="adiabatic__empty">
                        Boundary samples unavailable.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </section>

            <section className="adiabatic__section">
              <h4>FS step histogram</h4>
              {histogramOptions.length > 0 ? (
                <label className="adiabatic__field">
                  <span>Select extent/steps</span>
                  <select
                    value={selectedKey ?? ''}
                    onChange={(event) => setSelectedKey(event.target.value || null)}
                  >
                    <option value="">Choose a sample…</option>
                    {histogramOptions.map((option) => (
                      <option key={option.key} value={option.key}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <p className="adiabatic__hint">Histogram data not found.</p>
              )}

              {activeHistogram && histogramPlot ? (
                <div className="adiabatic__histogram">
                  <Plot
                    data={histogramPlot.data}
                    layout={histogramPlot.layout}
                    config={{ displaylogo: false, responsive: true }}
                    style={{ width: '100%', height: '100%' }}
                  />
                  {activeSurfaceSample ? (
                    <p className="adiabatic__hint">
                      Sample FS p95 {formatNumber(activeSurfaceSample.fsP95, 3)} rad, κ₁{' '}
                      {formatNumber(activeSurfaceSample.kappa1, 3)}.
                    </p>
                  ) : null}
                </div>
              ) : null}
            </section>
          </div>
        </>
      ) : (
        <p className="adiabatic__hint">
          Trigger the sweep to generate κ₁ surfaces, FS histograms, and the inferred boundary.
        </p>
      )}
    </div>
  );
};

export default AdiabaticBoundaryViewer;
