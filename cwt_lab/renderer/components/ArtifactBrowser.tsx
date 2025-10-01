import { useEffect, useMemo, useState } from 'react';
import Plot from 'react-plotly.js';
import type { Data, Layout } from 'plotly.js';

import { useDemoMode, type DemoArtifact } from '../demo/DemoModeContext';
import type { RegistryRunRecord } from '../types/ipc';

type ArtifactMetric = {
  label: string;
  value: number;
  unit?: string;
};

type ArtifactPlot = {
  data: Data[];
  layout: Partial<Layout>;
};

type ArtifactEntry = {
  id: string;
  phase: string;
  title: string;
  summary: string;
  tags: string[];
  updatedAt: string;
  metrics: ArtifactMetric[];
  plot: ArtifactPlot | null;
};

const BASE_LAYOUT: Partial<Layout> = {
  margin: { t: 36, r: 12, b: 48, l: 56 },
  height: 320,
  paper_bgcolor: 'transparent',
  plot_bgcolor: 'transparent',
  font: { family: 'Inter, sans-serif' },
  legend: { orientation: 'h', y: -0.2 },
};

const METRIC_LABEL_OVERRIDES: Record<string, { label: string; unit?: string }> = {
  phi_flux: { label: 'Φ flux' },
  phi_sum: { label: 'Φ sum' },
  phi_forward: { label: 'Φ forward' },
  phi_reverse: { label: 'Φ reverse' },
  phi: { label: 'Φ' },
  guard_margin: { label: 'Guard margin' },
  fs_guard: { label: 'FS guard', unit: 'rad' },
  fs_boundary: { label: 'FS boundary', unit: 'rad' },
  fs_p95: { label: 'FS p95', unit: 'rad' },
  fs_mean: { label: 'FS mean', unit: 'rad' },
  fs_guard_exceeded: { label: 'Guard exceeded' },
  fs_exceeded: { label: 'Guard exceeded' },
  kuramoto_r: { label: 'Kuramoto r' },
  r_value: { label: 'R' },
  r: { label: 'R' },
  coverage: { label: 'Coverage' },
  persistence: { label: 'Persistence' },
  runtime_seconds: { label: 'Runtime', unit: 's' },
  peak_abs_omega: { label: '|Ω| peak' },
  median_abs_omega: { label: '|Ω| median' },
  ridge_auc: { label: 'Ridge AUC' },
  fs_guard_ok: { label: 'Guard ok' },
};

const isNonEmptyString = (value: unknown): value is string => typeof value === 'string' && value.trim().length > 0;

const normaliseMetricLabel = (key: string): { label: string; unit?: string } => {
  const override = METRIC_LABEL_OVERRIDES[key];
  if (override) {
    return override;
  }
  const readable = key
    .replace(/_/g, ' ')
    .replace(/\b([a-z])/g, (match) => match.toUpperCase())
    .replace(/\bFs\b/, 'FS')
    .replace(/\bPhi\b/, 'Φ');
  return { label: readable };
};

const formatMetricValue = (value: number, unit?: string) => {
  const magnitude = Math.abs(value);
  const formatted = magnitude !== 0 && (magnitude < 0.01 || magnitude > 1_000)
    ? value.toExponential(2)
    : value.toFixed(3);
  return unit ? `${formatted} ${unit}` : formatted;
};

const mapDemoArtifact = (artifact: DemoArtifact): ArtifactEntry => ({
  id: artifact.id,
  phase: artifact.phase,
  title: artifact.title,
  summary: artifact.summary,
  tags: artifact.tags,
  updatedAt: artifact.updatedAt,
  metrics: artifact.metrics.map(({ label, value, unit }) => ({ label, value, unit })),
  plot: {
    data: artifact.traces.map((trace) => ({
      x: trace.x,
      y: trace.y,
      mode: trace.mode ?? 'lines',
      name: trace.name,
      type: 'scatter',
      hovertemplate: '%{y:.3f} at %{x:.3f}<extra></extra>',
    })),
    layout: {
      ...BASE_LAYOUT,
      title: { text: artifact.title },
    },
  },
});

const buildMetricsArray = (metrics: Record<string, number | null> | null): ArtifactMetric[] => {
  if (!metrics) {
    return [];
  }
  const entries: ArtifactMetric[] = [];
  for (const [key, raw] of Object.entries(metrics)) {
    if (typeof raw !== 'number' || !Number.isFinite(raw)) {
      continue;
    }
    const { label, unit } = normaliseMetricLabel(key);
    entries.push({ label, value: raw, unit });
  }
  entries.sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
  return entries;
};

const buildMetricsPlot = (title: string, metrics: ArtifactMetric[]): ArtifactPlot | null => {
  if (metrics.length === 0) {
    return null;
  }
  const slice = metrics.slice(0, Math.min(metrics.length, 6));
  const trace: Data = {
    type: 'bar',
    x: slice.map((metric) => metric.label),
    y: slice.map((metric) => metric.value),
    name: 'Metrics',
    marker: { color: '#2563eb' },
    hovertemplate: '<b>%{x}</b><br>%{y:.3f}<extra></extra>',
  };
  return {
    data: [trace],
    layout: {
      ...BASE_LAYOUT,
      title: { text: `${title} metrics` },
      xaxis: { automargin: true },
      yaxis: { automargin: true },
    },
  };
};

const buildFamiliesPlot = (
  title: string,
  summary: Record<string, unknown> | null,
): ArtifactPlot | null => {
  if (!summary || !Array.isArray(summary.families)) {
    return null;
  }
  const families = summary.families as Array<Record<string, unknown>>;
  const points = families
    .map((family) => {
      const name = isNonEmptyString(family.name) ? family.name : null;
      const phiFlux = typeof family.phi_flux === 'number' ? family.phi_flux : null;
      const guard = typeof family.fs_p95 === 'number' ? family.fs_p95 : null;
      if (!name || phiFlux == null) {
        return null;
      }
      return { name, phiFlux, guard };
    })
    .filter((entry): entry is { name: string; phiFlux: number; guard: number | null } => entry !== null);

  if (points.length === 0) {
    return null;
  }

  const trace: Data = {
    type: 'bar',
    x: points.map((point) => point.name),
    y: points.map((point) => point.phiFlux),
    name: 'Φ flux',
    marker: { color: '#f97316' },
    hovertemplate: points.some((point) => point.guard != null)
      ? '<b>%{x}</b><br>Φ=%{y:.3f}<br>FS p95=%{customdata:.3f}<extra></extra>'
      : '<b>%{x}</b><br>Φ=%{y:.3f}<extra></extra>',
    customdata: points.map((point) => (point.guard != null ? point.guard : null)),
  };

  return {
    data: [trace],
    layout: {
      ...BASE_LAYOUT,
      title: { text: `${title} families` },
      xaxis: { automargin: true },
      yaxis: { automargin: true },
    },
  };
};

const readRunSummary = async (runId: string): Promise<Record<string, unknown> | null> => {
  if (typeof window === 'undefined' || !window.CWT?.run?.readArtifact) {
    return null;
  }
  try {
    const response = await window.CWT.run.readArtifact({ runId, relativePath: 'summary.json' });
    if (!response.ok) {
      return null;
    }
    const parsed = JSON.parse(response.data.contents) as unknown;
    if (!parsed || typeof parsed !== 'object') {
      return null;
    }
    return parsed as Record<string, unknown>;
  } catch {
    return null;
  }
};

const buildSummaryText = (
  run: RegistryRunRecord,
  metrics: ArtifactMetric[],
  summary: Record<string, unknown> | null,
): string => {
  if (summary) {
    if (isNonEmptyString((summary as Record<string, unknown>).description)) {
      return ((summary as Record<string, unknown>).description as string).trim();
    }
    if (Array.isArray(summary.highlights)) {
      const firstHighlight = summary.highlights.find(isNonEmptyString);
      if (firstHighlight) {
        return firstHighlight.trim();
      }
    }
    if (isNonEmptyString(summary.summary)) {
      return (summary.summary as string).trim();
    }
  }

  if (metrics.length > 0) {
    return metrics
      .slice(0, Math.min(metrics.length, 3))
      .map((metric) => `${metric.label}: ${formatMetricValue(metric.value, metric.unit)}`)
      .join(' • ');
  }

  const status = run.status ? run.status.replace(/^\w/, (char) => char.toUpperCase()) : 'Unknown status';
  return `${status} — awaiting summary metrics.`;
};

const collectTags = (run: RegistryRunRecord, summary: Record<string, unknown> | null): string[] => {
  const tags = new Set<string>();
  if (isNonEmptyString(run.experiment)) {
    tags.add(run.experiment!);
  }
  if (isNonEmptyString(run.status)) {
    tags.add(run.status!);
  }
  if (summary) {
    if (Array.isArray(summary.tags)) {
      for (const tag of summary.tags) {
        if (isNonEmptyString(tag)) {
          tags.add(tag);
        }
      }
    }
    if (Array.isArray(summary.families)) {
      for (const entry of summary.families as Array<Record<string, unknown>>) {
        if (isNonEmptyString(entry.name)) {
          tags.add(entry.name);
        }
      }
    }
  }
  return Array.from(tags).slice(0, 6);
};

const buildArtifactFromRun = async (run: RegistryRunRecord): Promise<ArtifactEntry> => {
  const summary = await readRunSummary(run.id);
  const metrics = buildMetricsArray(run.metrics ?? null);
  const title = isNonEmptyString(run.label)
    ? run.label!
    : isNonEmptyString(run.experiment)
    ? run.experiment!
    : `Run ${run.id}`;

  const familiesPlot = buildFamiliesPlot(title, summary);
  const plot = familiesPlot ?? buildMetricsPlot(title, metrics);

  return {
    id: run.id,
    phase: run.phase ?? 'unassigned',
    title,
    summary: buildSummaryText(run, metrics, summary),
    tags: collectTags(run, summary),
    updatedAt: new Date(run.updatedAt).toISOString(),
    metrics,
    plot,
  };
};

type LiveArtifactsState = {
  artifacts: ArtifactEntry[];
  loading: boolean;
  error: string | null;
};

const useLiveArtifacts = (active: boolean): LiveArtifactsState => {
  const [state, setState] = useState<LiveArtifactsState>({ artifacts: [], loading: false, error: null });

  useEffect(() => {
    let cancelled = false;

    if (!active) {
      setState({ artifacts: [], loading: false, error: null });
      return;
    }

    if (typeof window === 'undefined' || !window.CWT?.registry?.query) {
      setState({ artifacts: [], loading: false, error: 'Artifact APIs are unavailable in this environment.' });
      return;
    }

    setState((prev) => ({ ...prev, loading: true, error: null }));

    const fetchArtifacts = async () => {
      try {
        const response = await window.CWT.registry.query({ limit: 200 });
        if (!response.ok) {
          throw new Error(response.error ?? 'Failed to query registry');
        }
        const runs = response.data as RegistryRunRecord[];
        const artifacts = await Promise.all(runs.map((run) => buildArtifactFromRun(run)));
        artifacts.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
        if (!cancelled) {
          setState({ artifacts, loading: false, error: null });
        }
      } catch (error) {
        if (!cancelled) {
          setState({
            artifacts: [],
            loading: false,
            error: error instanceof Error ? error.message : String(error),
          });
        }
      }
    };

    void fetchArtifacts();

    return () => {
      cancelled = true;
    };
  }, [active]);

  return state;
};

const ArtifactBrowser = () => {
  const { enabled: demoEnabled, artifacts: demoArtifacts } = useDemoMode();
  const { artifacts: liveArtifacts, loading, error } = useLiveArtifacts(!demoEnabled);

  const artifacts = useMemo<ArtifactEntry[]>(
    () => (demoEnabled ? demoArtifacts.map(mapDemoArtifact) : liveArtifacts),
    [demoEnabled, demoArtifacts, liveArtifacts],
  );
  const [phaseFilter, setPhaseFilter] = useState<string>('all');
  const [query, setQuery] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (!artifacts.length) {
      setSelectedId(null);
      return;
    }
    setSelectedId((prev) => (prev && artifacts.some((artifact) => artifact.id === prev) ? prev : artifacts[0]?.id ?? null));
  }, [artifacts]);

  const phases = useMemo(() => {
    const set = new Set<string>();
    artifacts.forEach((artifact) => set.add(artifact.phase));
    return Array.from(set).sort();
  }, [artifacts]);

  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return artifacts.filter((artifact) => {
      if (phaseFilter !== 'all' && artifact.phase !== phaseFilter) {
        return false;
      }
      if (!normalizedQuery) {
        return true;
      }
      const haystack = [artifact.title, artifact.summary, ...artifact.tags].join(' ').toLowerCase();
      return haystack.includes(normalizedQuery);
    });
  }, [artifacts, phaseFilter, query]);

  const selected = useMemo(() => filtered.find((artifact) => artifact.id === selectedId) ?? filtered[0] ?? null, [
    filtered,
    selectedId,
  ]);

  const isLoading = !demoEnabled && loading;
  const loadError = !demoEnabled ? error : null;

  return (
    <div className="panel artifact-browser">
      <header className="artifact-browser__header">
        <div>
          <h2>Artifact Browser</h2>
          <p>
            Explore saved outputs from recent runs. Toggle demo mode to preview curated examples or run new experiments to
            populate live artifacts.
          </p>
        </div>
        <div className="artifact-browser__filters">
          <label className="artifact-browser__filter">
            <span>Phase</span>
            <select value={phaseFilter} onChange={(event) => setPhaseFilter(event.target.value)}>
              <option value="all">All phases</option>
              {phases.map((phase) => (
                <option key={phase} value={phase}>
                  {phase}
                </option>
              ))}
            </select>
          </label>
          <label className="artifact-browser__filter">
            <span>Search</span>
            <input
              type="search"
              placeholder="Filter by name or tag"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
        </div>
      </header>

      {isLoading ? (
        <p className="artifact-browser__placeholder">Loading artifacts…</p>
      ) : loadError ? (
        <p className="artifact-browser__placeholder">Unable to load artifacts: {loadError}</p>
      ) : filtered.length === 0 ? (
        <p className="artifact-browser__placeholder">
          {artifacts.length === 0
            ? 'No artifacts found yet. Launch runs to generate analysis outputs or enable demo mode for curated samples.'
            : 'No artifacts match the active filters.'}
        </p>
      ) : (
        <div className="artifact-browser__body">
          <aside className="artifact-browser__list" aria-label="Artifacts">
            <ul>
              {filtered.map((artifact) => (
                <li key={artifact.id}>
                  <button
                    type="button"
                    className={
                      artifact.id === selected?.id
                        ? 'artifact-browser__item artifact-browser__item--active'
                        : 'artifact-browser__item'
                    }
                    onClick={() => setSelectedId(artifact.id)}
                  >
                    <div>
                      <strong>{artifact.title}</strong>
                      <p>{artifact.summary}</p>
                    </div>
                    <div className="artifact-browser__tags">
                      <span className="artifact-browser__phase">{artifact.phase}</span>
                      {artifact.tags.slice(0, 3).map((tag) => (
                        <span key={tag} className="artifact-browser__tag">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </aside>
          {selected ? (
            <section className="artifact-browser__details" aria-live="polite">
              <header>
                <h3>{selected.title}</h3>
                <p>{selected.summary}</p>
                <small>Updated {new Date(selected.updatedAt).toLocaleString()}</small>
              </header>
              <div className="artifact-browser__metrics">
                {selected.metrics.length > 0 ? (
                  selected.metrics.map((metric) => (
                    <div key={metric.label} className="artifact-browser__metric">
                      <span className="artifact-browser__metric-label">{metric.label}</span>
                      <strong>{formatMetricValue(metric.value, metric.unit)}</strong>
                    </div>
                  ))
                ) : (
                  <p className="artifact-browser__placeholder artifact-browser__placeholder--inline">
                    No numeric metrics recorded for this artifact yet.
                  </p>
                )}
              </div>
              {selected.plot ? (
                <Plot
                  data={selected.plot.data}
                  layout={selected.plot.layout}
                  useResizeHandler
                  className="artifact-browser__plot"
                  style={{ width: '100%', height: '100%' }}
                  config={{ displayModeBar: false }}
                />
              ) : (
                <p className="artifact-browser__placeholder artifact-browser__placeholder--inline">
                  No visual preview available for this artifact.
                </p>
              )}
            </section>
          ) : null}
        </div>
      )}
    </div>
  );
};

export default ArtifactBrowser;
