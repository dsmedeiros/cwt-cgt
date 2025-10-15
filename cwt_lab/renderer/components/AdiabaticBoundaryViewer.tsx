import { useEffect, useMemo, useRef, useState } from 'react';
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

export type AdiabaticBoundaryStatusUpdate =
  | {
      status: 'idle';
      requestId: number;
      hotspotId: string | null;
      graphId: string | null;
    }
  | {
      status: 'running';
      requestId: number;
      hotspotId: string | null;
      graphId: string | null;
    }
  | {
      status: 'success';
      requestId: number;
      hotspotId: string | null;
      graphId: string | null;
      result: AdiabaticBoundaryResult;
    }
  | {
      status: 'error';
      requestId: number;
      hotspotId: string | null;
      graphId: string | null;
      error: string;
    };

export type AdiabaticCalmUpdate = {
  hotspotId: string | null;
  graphId: string | null;
  calm: boolean;
  requestId: number | null;
};

type ViewerHotspot = {
  id: string;
  name: string;
  coordinates?: Partial<Record<string, number>>;
  calm?: boolean;
};

type AdiabaticBoundaryViewerProps = {
  hotspot: ViewerHotspot | null;
  graphId: string | null;
  experimentDir: string | null;
  substrateDir: string | null;
  extentSeeds: number[] | null;
  stepSeeds: number[] | null;
  gridSizeSeed: number | null;
  planeAxes: [string, string] | null;
  onResult?: (update: AdiabaticBoundaryStatusUpdate) => void;
  onCalm?: (update: AdiabaticCalmUpdate) => void;
};

type RunOverrides = {
  center?: Partial<Record<string, number>> | null;
  extents?: number[] | null;
  steps?: number[] | null;
  gridSize?: number | null;
  auto?: boolean;
};

const formatSeeds = (values: number[] | null | undefined) =>
  values && values.length > 0
    ? values
        .filter((value) => Number.isFinite(value))
        .map((value) => Number(value))
        .join(', ')
    : '';

const sanitizeNumber = (value: number | null | undefined) =>
  typeof value === 'number' && Number.isFinite(value) ? value : null;

const axisLabelMap: Record<string, string> = {
  rho: 'ρ',
  tau: 'τ',
  zeta: 'ζ',
  zeta_phase: 'ζ_phase',
  kappa: 'κ',
};

const labelForAxis = (axis: string) => axisLabelMap[axis] ?? axis;

const AdiabaticBoundaryViewer = ({
  hotspot,
  graphId,
  experimentDir,
  substrateDir,
  extentSeeds,
  stepSeeds,
  gridSizeSeed,
  planeAxes,
  onResult,
  onCalm,
}: AdiabaticBoundaryViewerProps) => {
  const axisA = planeAxes?.[0] ?? 'tau';
  const axisB = planeAxes?.[1] ?? 'zeta';
  const axisALabel = labelForAxis(axisA);
  const axisBLabel = labelForAxis(axisB);
  const hotspotCenterA = hotspot?.coordinates ? hotspot.coordinates[axisA] : undefined;
  const hotspotCenterB = hotspot?.coordinates ? hotspot.coordinates[axisB] : undefined;

  const [centerAxisA, setCenterAxisA] = useState('');
  const [centerAxisB, setCenterAxisB] = useState('');
  const [extentsInput, setExtentsInput] = useState('');
  const [stepsInput, setStepsInput] = useState('');
  const [gridSizeInput, setGridSizeInput] = useState('');
  const [result, setResult] = useState<AdiabaticBoundaryResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [calmFlag, setCalmFlag] = useState<boolean>(Boolean(hotspot?.calm));
  const requestCounterRef = useRef(0);

  const notifyStatus = (update: Omit<AdiabaticBoundaryStatusUpdate, 'requestId'> & {
    requestId?: number;
  }) => {
    const requestId = update.requestId ?? requestCounterRef.current;
    if (!onResult) {
      return;
    }
    onResult({
      ...update,
      requestId,
    } as AdiabaticBoundaryStatusUpdate);
  };

  const runAnalysis = async (overrides?: RunOverrides) => {
    const centerOverride = overrides?.center ?? null;
    const extentOverride = overrides?.extents;
    const stepsOverride = overrides?.steps;
    const gridOverride = overrides?.gridSize;

    const axisAOverride = centerOverride?.[axisA] ?? null;
    const axisBOverride = centerOverride?.[axisB] ?? null;

    const axisACenter = axisAOverride ?? parseNumber(centerAxisA);
    const axisBCenter = axisBOverride ?? parseNumber(centerAxisB);
    if (axisACenter == null || axisBCenter == null) {
      const message = `Provide numeric values for the ${axisALabel} and ${axisBLabel} center.`;
      setError(message);
      notifyStatus({
        status: 'error',
        hotspotId: hotspot?.id ?? null,
        graphId,
        error: message,
        requestId: requestCounterRef.current,
      });
      return;
    }

    const extents = extentOverride ?? parseFloatList(extentsInput);
    if (!extents || extents.length === 0) {
      const message = 'Provide at least one numeric extent (comma or space separated).';
      setError(message);
      notifyStatus({
        status: 'error',
        hotspotId: hotspot?.id ?? null,
        graphId,
        error: message,
        requestId: requestCounterRef.current,
      });
      return;
    }

    const steps = stepsOverride ?? parseIntegerList(stepsInput);
    if (!steps || steps.length === 0) {
      const message = 'Provide at least one integer step count (comma or space separated).';
      setError(message);
      notifyStatus({
        status: 'error',
        hotspotId: hotspot?.id ?? null,
        graphId,
        error: message,
        requestId: requestCounterRef.current,
      });
      return;
    }

    const gridSizeNumber = gridOverride ?? parseIntegerList(gridSizeInput)?.[0];
    if (gridSizeNumber == null || gridSizeNumber <= 0) {
      const message = 'Grid size must be a positive integer.';
      setError(message);
      notifyStatus({
        status: 'error',
        hotspotId: hotspot?.id ?? null,
        graphId,
        error: message,
        requestId: requestCounterRef.current,
      });
      return;
    }

    if (!window?.CWT?.phase3?.cmdAdiabaticBoundary) {
      const message = 'Adiabatic boundary command is unavailable.';
      setError(message);
      notifyStatus({
        status: 'error',
        hotspotId: hotspot?.id ?? null,
        graphId,
        error: message,
        requestId: requestCounterRef.current,
      });
      return;
    }

    requestCounterRef.current += 1;
    const requestId = requestCounterRef.current;
    const context = {
      hotspotId: hotspot?.id ?? null,
      graphId,
      requestId,
    } as const;

    setIsRunning(true);
    setError(null);
    notifyStatus({ status: 'running', ...context });

    try {
      const centerParts = [
        `${axisA}=${toCliValue(axisACenter)}`,
        `${axisB}=${toCliValue(axisBCenter)}`,
      ];
      const response = await window.CWT.phase3.cmdAdiabaticBoundary({
        center: centerParts.join(','),
        axes: [axisA, axisB],
        extents: extents.map((value) => toCliValue(value)),
        steps,
        gridSize: gridSizeNumber,
        experimentDir: experimentDir ?? undefined,
        substrateDir: substrateDir ?? undefined,
        hotspotId: hotspot?.id,
        graphId: graphId ?? undefined,
      });
      if (!response.ok) {
        throw new Error(response.error ?? 'Failed to run adiabatic boundary sweep');
      }
      if (requestId !== requestCounterRef.current) {
        return;
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
      notifyStatus({ status: 'success', ...context, result: response.data });
      if (onCalm) {
        onCalm({
          hotspotId: hotspot?.id ?? null,
          graphId,
          calm: calmFlag,
          requestId,
        });
      }
    } catch (analysisError) {
      if (requestId !== requestCounterRef.current) {
        return;
      }
      const message =
        analysisError instanceof Error ? analysisError.message : String(analysisError);
      setError(message);
      notifyStatus({ status: 'error', ...context, error: message });
    } finally {
      if (requestId === requestCounterRef.current) {
        setIsRunning(false);
      }
    }
  };

  useEffect(() => {
    const axisASeed = sanitizeNumber(hotspotCenterA) ?? 0;
    const axisBSeed = sanitizeNumber(hotspotCenterB) ?? 0;
    setCenterAxisA(axisASeed.toString());
    setCenterAxisB(axisBSeed.toString());
  }, [hotspot?.id, axisA, axisB, hotspotCenterA, hotspotCenterB]);

  useEffect(() => {
    setExtentsInput(formatSeeds(extentSeeds));
  }, [extentSeeds?.length, extentSeeds]);

  useEffect(() => {
    setStepsInput(formatSeeds(stepSeeds));
  }, [stepSeeds?.length, stepSeeds]);

  useEffect(() => {
    setGridSizeInput(gridSizeSeed != null ? Math.round(gridSizeSeed).toString() : '');
  }, [gridSizeSeed]);

  useEffect(() => {
    setCalmFlag(Boolean(hotspot?.calm));
  }, [hotspot?.id, hotspot?.calm]);

  useEffect(() => {
    setResult(null);
    setError(null);
    setSelectedKey(null);
    notifyStatus({
      status: 'idle',
      hotspotId: hotspot?.id ?? null,
      graphId,
    });
  }, [
    hotspot?.id,
    hotspotCenterA,
    hotspotCenterB,
    axisA,
    axisB,
    graphId,
    extentSeeds,
    stepSeeds,
    gridSizeSeed,
  ]);

  const handleCalmToggle = (checked: boolean) => {
    setCalmFlag(checked);
    if (onCalm) {
      onCalm({
        hotspotId: hotspot?.id ?? null,
        graphId,
        calm: checked,
        requestId: requestCounterRef.current,
      });
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
          <h3>
            Adiabatic boundary
            {hotspot ? <span className="adiabatic__hotspot"> — {hotspot.name}</span> : null}
          </h3>
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
          <span>{`Center ${axisALabel}`}</span>
          <input
            type="number"
            step="0.01"
            value={centerAxisA}
            onChange={(event) => setCenterAxisA(event.target.value)}
          />
        </label>
        <label>
          <span>{`Center ${axisBLabel}`}</span>
          <input
            type="number"
            step="0.01"
            value={centerAxisB}
            onChange={(event) => setCenterAxisB(event.target.value)}
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
        <label className="adiabatic__controls--toggle">
          <span>Calm basin</span>
          <input
            type="checkbox"
            checked={calmFlag}
            onChange={(event) => handleCalmToggle(event.target.checked)}
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
