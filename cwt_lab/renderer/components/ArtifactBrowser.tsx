import { useEffect, useMemo, useState } from 'react';
import Plot from 'react-plotly.js';
import type { Data, Layout } from 'plotly.js';

import { useDemoMode, type DemoArtifact } from '../demo/DemoModeContext';

const buildTraceData = (artifact: DemoArtifact): Data[] =>
  artifact.traces.map((trace) => ({
    x: trace.x,
    y: trace.y,
    mode: trace.mode ?? 'lines',
    name: trace.name,
    type: 'scatter',
    hovertemplate: '%{y:.3f} at %{x:.3f}<extra></extra>',
  }));

const layoutForArtifact = (artifact: DemoArtifact): Partial<Layout> => ({
  title: artifact.title,
  margin: { t: 36, r: 12, b: 36, l: 48 },
  height: 320,
  template: 'plotly_dark',
  paper_bgcolor: 'transparent',
  plot_bgcolor: 'transparent',
  font: { family: 'Inter, sans-serif' },
  legend: { orientation: 'h', y: -0.2 },
});

const formatMetricValue = (value: number, unit?: string) => {
  const formatted = Math.abs(value) < 0.01 || Math.abs(value) > 100 ? value.toExponential(2) : value.toFixed(3);
  return unit ? `${formatted} ${unit}` : formatted;
};

const ArtifactBrowser = () => {
  const { enabled, artifacts } = useDemoMode();
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

  return (
    <div className="panel artifact-browser">
      <header className="artifact-browser__header">
        <div>
          <h2>Artifact Browser</h2>
          <p>
            Explore saved outputs from recent runs. Enable demo mode to load curated artifacts instantly or plug in your
            own workspace to browse live data.
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

      {!enabled ? (
        <p className="artifact-browser__placeholder">
          Demo mode is currently disabled. Toggle it in the header to load pre-baked analysis artifacts.
        </p>
      ) : filtered.length === 0 ? (
        <p className="artifact-browser__placeholder">No artifacts match the active filters.</p>
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
                {selected.metrics.map((metric) => (
                  <div key={metric.label} className="artifact-browser__metric">
                    <span className="artifact-browser__metric-label">{metric.label}</span>
                    <strong>{formatMetricValue(metric.value, metric.unit)}</strong>
                  </div>
                ))}
              </div>
              <Plot
                data={buildTraceData(selected)}
                layout={layoutForArtifact(selected)}
                useResizeHandler
                className="artifact-browser__plot"
                style={{ width: '100%', height: '100%' }}
                config={{ displayModeBar: false }}
              />
            </section>
          ) : null}
        </div>
      )}
    </div>
  );
};

export default ArtifactBrowser;
