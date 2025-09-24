import { useCallback, useMemo, useState } from 'react';
import Plot from 'react-plotly.js';
import type { Layout, PlotData } from 'plotly.js';

import type { ArtifactFile } from '../types/ipc';

const DEFAULT_AXES: [string, string] = ['tau', 'zeta_phase'];
const DEFAULT_GRID_SIZE = 33;
const DEFAULT_DISORDER = '0.0, 0.02, 0.05';
const DEFAULT_TAU_CENTER = '0.28';
const DEFAULT_TAU_EXTENT = '0.22';
const DEFAULT_ZETA_CENTER = '0.5';
const DEFAULT_ZETA_EXTENT = '0.5';

const formatNumber = (value: number | null | undefined, digits = 3) => {
  if (value == null || Number.isNaN(value)) {
    return '–';
  }
  return Number(value).toFixed(digits);
};

const parseNumberList = (value: string): number[] | null => {
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

const parseFloatInput = (value: string): number | null => {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
};

const buildTorusPayload = (
  axes: [string, string],
  gridSize: number,
  disorders: number[],
  tauCenter: number,
  tauExtent: number,
  zetaCenter: number,
  zetaExtent: number,
) => ({
  axes,
  gridSize,
  disorderList: disorders,
  centersExtents: {
    [axes[0]]: { center: tauCenter, extent: tauExtent },
    [axes[1]]: { center: zetaCenter, extent: zetaExtent },
  },
});

type PlateauHeatmap = {
  axes: string[];
  x: number[];
  y: number[];
  values: number[][];
  coverage: number[][];
  min_value: number;
  max_value: number;
};

type PlateauSample = {
  disorder: number;
  integral: number;
  phi_missing: boolean;
  guard_fraction: number;
  min_overlap: number;
  closing_tiles: number;
  heatmap?: PlateauHeatmap | null;
};

type PlateauSummary = {
  axes: string[];
  grid_size: number;
  steps: number;
  center: Record<string, number>;
  extents: Record<string, number>;
  disorder: number[];
  samples: PlateauSample[];
  stable: boolean;
  stability_notes?: string[];
  jump_notes?: string[];
};

type WarningLevel = 'warning' | 'danger';

type WarningNote = {
  level: WarningLevel;
  message: string;
};

const TorusPlateauViewer = () => {
  const [axisA, setAxisA] = useState(DEFAULT_AXES[0]);
  const [axisB, setAxisB] = useState(DEFAULT_AXES[1]);
  const [gridSizeInput, setGridSizeInput] = useState(() => DEFAULT_GRID_SIZE.toString());
  const [disorderInput, setDisorderInput] = useState(DEFAULT_DISORDER);
  const [tauCenter, setTauCenter] = useState(DEFAULT_TAU_CENTER);
  const [tauExtent, setTauExtent] = useState(DEFAULT_TAU_EXTENT);
  const [zetaCenter, setZetaCenter] = useState(DEFAULT_ZETA_CENTER);
  const [zetaExtent, setZetaExtent] = useState(DEFAULT_ZETA_EXTENT);

  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [commandPreview, setCommandPreview] = useState('');
  const [commandPreviewError, setCommandPreviewError] = useState<string | null>(null);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [summary, setSummary] = useState<PlateauSummary | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [isLoadingSummary, setIsLoadingSummary] = useState(false);
  const [selectedSampleIndex, setSelectedSampleIndex] = useState(0);

  useEffect(() => {
    let cancelled = false;

    const updatePreview = async () => {
      const axes: [string, string] = [axisA.trim(), axisB.trim()];
      const gridSize = Number(gridSizeInput);
      const disorders = parseNumberList(disorderInput) ?? [];
      const tauCenterValue = parseFloatInput(tauCenter);
      const tauExtentValue = parseFloatInput(tauExtent);
      const zetaCenterValue = parseFloatInput(zetaCenter);
      const zetaExtentValue = parseFloatInput(zetaExtent);

      const inputsValid =
        axes[0].length > 0 &&
        axes[1].length > 0 &&
        Number.isInteger(gridSize) &&
        gridSize > 0 &&
        disorders.length > 0 &&
        tauCenterValue != null &&
        tauExtentValue != null &&
        tauExtentValue > 0 &&
        zetaCenterValue != null &&
        zetaExtentValue != null &&
        zetaExtentValue > 0;

      if (!inputsValid) {
        setCommandPreview('');
        setCommandPreviewError('Adjust parameters to preview the command.');
        return;
      }

      if (!window?.CWT?.run?.preview) {
        setCommandPreview('');
        setCommandPreviewError('Command preview unavailable in this environment.');
        return;
      }

      const payload = buildTorusPayload(
        axes,
        gridSize,
        disorders,
        tauCenterValue,
        tauExtentValue,
        zetaCenterValue,
        zetaExtentValue,
      );

      try {
        const response = await window.CWT.run.preview({
          experiment: 'experiments.torus_plateau.run',
          args: payload,
        });
        if (cancelled) {
          return;
        }
        if (response.ok) {
          setCommandPreview(response.data.cli);
          setCommandPreviewError(null);
        } else {
          setCommandPreview('');
          setCommandPreviewError(response.error ?? 'Unable to preview command.');
        }
      } catch (previewError) {
        if (cancelled) {
          return;
        }
        setCommandPreview('');
        setCommandPreviewError(
          previewError instanceof Error ? previewError.message : String(previewError),
        );
      }
    };

    void updatePreview();

    return () => {
      cancelled = true;
    };
  }, [axisA, axisB, gridSizeInput, disorderInput, tauCenter, tauExtent, zetaCenter, zetaExtent]);

  const loadSummary = useCallback(async (runId: string) => {
    if (!window?.CWT?.run?.openArtifacts || !window.CWT.run.readArtifact) {
      setSummaryError('Artifact inspection APIs are unavailable in this environment.');
      return;
    }

    setIsLoadingSummary(true);
    setSummaryError(null);

    try {
      const artifactsResponse = await window.CWT.run.openArtifacts({ runId });
      if (!artifactsResponse.ok) {
        throw new Error(artifactsResponse.error ?? 'Failed to list artifacts for the run.');
      }

      const files = artifactsResponse.data as ArtifactFile[];
      const summaryFile = files.find(
        (file) => file.type === 'file' && file.relativePath.endsWith('summary.json'),
      );

      if (!summaryFile) {
        setSummary(null);
        setSummaryError('Summary not found yet. Retry once artifacts finish writing.');
        return;
      }

      const readResponse = await window.CWT.run.readArtifact({
        runId,
        relativePath: summaryFile.relativePath,
      });
      if (!readResponse.ok) {
        throw new Error(readResponse.error ?? 'Failed to read summary artifact.');
      }

      try {
        const parsedSummary = JSON.parse(readResponse.data.contents) as PlateauSummary;
        setSummary(parsedSummary);
        setSelectedSampleIndex(0);
      } catch (parseError) {
        throw new Error(
          parseError instanceof Error
            ? `Failed to parse summary: ${parseError.message}`
            : 'Failed to parse summary file.',
        );
      }
    } catch (loadError) {
      setSummary(null);
      setSummaryError(loadError instanceof Error ? loadError.message : String(loadError));
    } finally {
      setIsLoadingSummary(false);
    }
  }, []);

  const runExperiment = useCallback(async () => {
    if (!window?.CWT?.phase4?.torusPlateau) {
      setError('Torus plateau launch API is unavailable.');
      return;
    }

    const axes: [string, string] = [axisA.trim(), axisB.trim()];
    if (!axes[0] || !axes[1]) {
      setError('Provide names for both axes.');
      return;
    }

    const gridSize = Number(gridSizeInput);
    if (!Number.isInteger(gridSize) || gridSize <= 0) {
      setError('Grid size must be a positive integer.');
      return;
    }

    const disorders = parseNumberList(disorderInput);
    if (!disorders || disorders.length === 0) {
      setError('Provide at least one disorder strength (comma or space separated).');
      return;
    }

    const tauCenterValue = parseFloatInput(tauCenter);
    const tauExtentValue = parseFloatInput(tauExtent);
    const zetaCenterValue = parseFloatInput(zetaCenter);
    const zetaExtentValue = parseFloatInput(zetaExtent);

    if (
      tauCenterValue == null ||
      tauExtentValue == null ||
      tauExtentValue <= 0 ||
      zetaCenterValue == null ||
      zetaExtentValue == null ||
      zetaExtentValue <= 0
    ) {
      setError('Provide numeric center and positive extent values for τ and ζ.');
      return;
    }

    const payload = buildTorusPayload(
      axes,
      gridSize,
      disorders,
      tauCenterValue,
      tauExtentValue,
      zetaCenterValue,
      zetaExtentValue,
    );

    setIsRunning(true);
    setError(null);
    setSummary(null);
    setSummaryError(null);
    setCurrentRunId(null);

    try {
      const response = await window.CWT.phase4.torusPlateau(payload);
      if (!response.ok) {
        throw new Error(response.error ?? 'Failed to launch torus plateau run.');
      }

      const runId = response.data.runId;
      setCurrentRunId(runId ?? null);

      if (runId) {
        loadSummary(runId);
      } else {
        setSummaryError('Run identifier was not returned; unable to locate summary.');
      }
    } catch (launchError) {
      setError(launchError instanceof Error ? launchError.message : String(launchError));
    } finally {
      setIsRunning(false);
    }
  }, [axisA, axisB, disorderInput, gridSizeInput, loadSummary, tauCenter, tauExtent, zetaCenter, zetaExtent]);

  const selectedSample = summary?.samples?.[selectedSampleIndex];

  const handleRetrySummary = useCallback(() => {
    if (currentRunId) {
      void loadSummary(currentRunId);
    }
  }, [currentRunId, loadSummary]);

  const heatmapPlot = useMemo(() => {
    if (!selectedSample?.heatmap) {
      return null;
    }
    const heatmap = selectedSample.heatmap;
    const x = heatmap.x;
    const y = heatmap.y;
    const z = heatmap.values.map((row) => row.map((value) => (Number.isFinite(value) ? value : 0)));
    const maxAbs = Math.max(Math.abs(heatmap.min_value ?? 0), Math.abs(heatmap.max_value ?? 0));
    const zmax = maxAbs > 0 ? maxAbs : undefined;

    const heatmapTrace: Partial<PlotData> = {
      type: 'heatmap',
      x,
      y,
      z,
      colorscale: 'RdBu',
      reversescale: true,
      colorbar: { title: { text: '∫Φ' } },
    };

    if (zmax !== undefined) {
      heatmapTrace.zmax = zmax;
      heatmapTrace.zmin = -zmax;
    }

    const data: Partial<PlotData>[] = [heatmapTrace];

    const layout: Partial<Layout> = {
      title: { text: `Integrated Φ at disorder ${formatNumber(selectedSample.disorder, 3)}` },
      xaxis: {
        title: { text: summary?.axes?.[0] ?? heatmap.axes?.[0] ?? 'τ' },
        zeroline: false,
      },
      yaxis: {
        title: { text: summary?.axes?.[1] ?? heatmap.axes?.[1] ?? 'ζ' },
        zeroline: false,
      },
      margin: { t: 50, r: 20, b: 60, l: 60 },
      height: 480,
      autosize: true,
    };

    return { data, layout };
  }, [selectedSample, summary?.axes]);

  const warnings = useMemo(() => {
    if (!selectedSample) {
      return [];
    }
    const notes: WarningNote[] = [];

    if (selectedSample.phi_missing) {
      notes.push({ level: 'danger', message: 'Curvature tiles were missing; integral forced to zero.' });
    }

    if (Number.isFinite(selectedSample.guard_fraction)) {
      if (selectedSample.guard_fraction > 0.25) {
        notes.push({ level: 'danger', message: `FS guard triggered on ${formatNumber(selectedSample.guard_fraction * 100, 1)}% of steps.` });
      } else if (selectedSample.guard_fraction > 0.1) {
        notes.push({ level: 'warning', message: `Moderate FS guard activity (${formatNumber(selectedSample.guard_fraction * 100, 1)}% of steps).` });
      }
    }

    if (Number.isFinite(selectedSample.min_overlap)) {
      if (selectedSample.min_overlap < 0.05) {
        notes.push({ level: 'danger', message: `Minimum overlap ${formatNumber(selectedSample.min_overlap, 3)} indicates gap closing.` });
      } else if (selectedSample.min_overlap < 0.1) {
        notes.push({ level: 'warning', message: `Overlap dipped to ${formatNumber(selectedSample.min_overlap, 3)}.` });
      }
    }

    if (selectedSample.closing_tiles > 0) {
      notes.push({ level: 'danger', message: `${selectedSample.closing_tiles} plaquettes reported overlap < 0.1.` });
    }

    if (selectedSample.heatmap?.coverage) {
      const uncovered = selectedSample.heatmap.coverage.reduce(
        (acc, row) => acc + row.filter((value) => !Number.isFinite(value) || value <= 0).length,
        0,
      );
      if (uncovered > 0) {
        notes.push({ level: 'warning', message: `${uncovered} heatmap bins had zero curvature coverage.` });
      }
    }

    return notes;
  }, [selectedSample]);

  const noteList = useMemo(() => {
    const items: string[] = [];
    if (!summary) {
      return items;
    }
    if (!summary.stable) {
      items.push('Plateau stability criteria were not met.');
    } else {
      items.push('Plateau appears stable across sampled disorders.');
    }
    if (summary.stability_notes?.length) {
      items.push(...summary.stability_notes);
    }
    if (summary.jump_notes?.length) {
      items.push(...summary.jump_notes);
    }
    return items;
  }, [summary]);

  return (
    <div className="panel torus">
      <aside className="torus__sidebar">
        <h2>Phase 4 – Torus Plateau</h2>
        <p>Launch a toroidal curvature survey and inspect the integrated flux plateau across disorder strengths.</p>

        <section className="torus__section">
          <h3>Axes</h3>
          <label className="torus__field">
            <span>Axis 1</span>
            <input type="text" value={axisA} onChange={(event) => setAxisA(event.target.value)} />
          </label>
          <label className="torus__field">
            <span>Axis 2</span>
            <input type="text" value={axisB} onChange={(event) => setAxisB(event.target.value)} />
          </label>
        </section>

        <section className="torus__section">
          <h3>Grid &amp; disorder</h3>
          <label className="torus__field">
            <span>Grid size (per cycle)</span>
            <input
              type="number"
              min={4}
              value={gridSizeInput}
              onChange={(event) => setGridSizeInput(event.target.value)}
            />
          </label>
          <label className="torus__field">
            <span>Disorder strengths</span>
            <textarea
              value={disorderInput}
              onChange={(event) => setDisorderInput(event.target.value)}
              rows={3}
            />
            <small>Comma or space separated values.</small>
          </label>
        </section>

        <section className="torus__section">
          <h3>τ/ζ window</h3>
          <label className="torus__field">
            <span>τ center</span>
            <input type="text" value={tauCenter} onChange={(event) => setTauCenter(event.target.value)} />
          </label>
          <label className="torus__field">
            <span>τ extent</span>
            <input type="text" value={tauExtent} onChange={(event) => setTauExtent(event.target.value)} />
          </label>
          <label className="torus__field">
            <span>ζ center</span>
            <input type="text" value={zetaCenter} onChange={(event) => setZetaCenter(event.target.value)} />
          </label>
          <label className="torus__field">
            <span>ζ extent</span>
            <input type="text" value={zetaExtent} onChange={(event) => setZetaExtent(event.target.value)} />
          </label>
        </section>

        <section className="torus__actions">
          <button className="btn btn--primary" type="button" onClick={runExperiment} disabled={isRunning}>
            {isRunning ? 'Launching…' : 'Run torus survey'}
          </button>
        </section>

        {error ? <div className="torus__error">{error}</div> : null}
        <code className="torus__command">{commandPreview || 'Preview unavailable'}</code>
        {commandPreviewError ? <div className="torus__error">{commandPreviewError}</div> : null}
        {currentRunId ? <p className="torus__status">Run ID: {currentRunId}</p> : null}
      </aside>

      <section className="torus__main">
        {isLoadingSummary ? <div className="torus__loading">Collecting summary from run…</div> : null}
        {summaryError ? (
          <div className="torus__error">
            {summaryError}
            {currentRunId ? (
              <>
                {' '}
                <button
                  type="button"
                  className="link-button"
                  onClick={handleRetrySummary}
                  disabled={isLoadingSummary}
                >
                  Retry
                </button>
              </>
            ) : null}
          </div>
        ) : null}

        {summary ? (
          <>
            <section className="torus__section">
              <h3>Disorder sweep</h3>
              <ul className="torus__disorder-list">
                {summary.samples.map((sample, index) => {
                  const isActive = index === selectedSampleIndex;
                  return (
                    <li key={`disorder-${sample.disorder}-${index}`}>
                      <button
                        type="button"
                        className={isActive ? 'torus__disorder-button torus__disorder-button--active' : 'torus__disorder-button'}
                        onClick={() => setSelectedSampleIndex(index)}
                      >
                        {`σ=${formatNumber(sample.disorder, 3)}`}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>

            <section className="torus__section">
              {heatmapPlot ? (
                <Plot
                  data={heatmapPlot.data}
                  layout={heatmapPlot.layout}
                  className="torus__heatmap"
                  config={{ displayModeBar: false, responsive: true }}
                />
              ) : (
                <div className="torus__empty">No curvature heatmap was generated for this disorder sample.</div>
              )}
            </section>

            {selectedSample ? (
              <section className="torus__section torus__metrics">
                <div className="torus__metric">
                  <span className="torus__metric-label">Integrated Φ</span>
                  <span className="torus__metric-value">{formatNumber(selectedSample.integral, 4)}</span>
                </div>
                <div className="torus__metric">
                  <span className="torus__metric-label">FS guard fraction</span>
                  <span className="torus__metric-value">{formatNumber(selectedSample.guard_fraction, 3)}</span>
                </div>
                <div className="torus__metric">
                  <span className="torus__metric-label">Min overlap</span>
                  <span className="torus__metric-value">{formatNumber(selectedSample.min_overlap, 3)}</span>
                </div>
              </section>
            ) : null}

            {warnings.length ? (
              <section className="torus__section torus__warnings">
                {warnings.map((note, index) => (
                  <div
                    key={`warning-${index}`}
                    className={note.level === 'danger' ? 'torus__warning torus__warning--danger' : 'torus__warning'}
                  >
                    {note.message}
                  </div>
                ))}
              </section>
            ) : null}

            {noteList.length ? (
              <section className="torus__section torus__notes">
                <h3>Stability notes</h3>
                <ul>
                  {noteList.map((note, index) => (
                    <li key={`note-${index}`}>{note}</li>
                  ))}
                </ul>
              </section>
            ) : null}
          </>
        ) : (
          <div className="torus__empty">Run the torus survey to view integrated flux plateaus.</div>
        )}
      </section>
    </div>
  );
};

export default TorusPlateauViewer;
