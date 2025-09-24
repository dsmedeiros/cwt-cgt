import { useMemo, useState } from 'react';

import type {
  GraphFamilyCommandPayload,
  GraphFamilyCommandResult,
  GraphFamilySummary,
} from '../types/ipc';

type FamilyOption = {
  id: string;
  label: string;
  description: string;
};

const familyOptions: FamilyOption[] = [
  { id: 'ring', label: 'Ring', description: 'Directed ring with heterogeneous delays.' },
  { id: 'rr', label: 'Random regular', description: '3-regular digraph ensemble.' },
  { id: 'sw', label: 'Small-world', description: 'Watts–Strogatz perturbation of a ring lattice.' },
  { id: 'sf', label: 'Scale-free', description: 'Barabási–Albert style heavy-tailed hub distribution.' },
  { id: 'mod', label: 'Modular', description: 'Two-community digraph with dense intra-links.' },
];

const defaultAxes: [string, string] = ['tau', 'zeta'];

const formatScientific = (value: number | null | undefined) => {
  if (value == null || Number.isNaN(value)) {
    return '—';
  }
  const safe = Number(value);
  if (!Number.isFinite(safe)) {
    return '—';
  }
  if (Math.abs(safe) >= 1e4 || Math.abs(safe) <= 1e-3) {
    return safe.toExponential(2);
  }
  return safe.toFixed(3);
};

const formatFloat = (value: number | null | undefined, digits = 3) => {
  if (value == null || Number.isNaN(value) || !Number.isFinite(value)) {
    return '—';
  }
  return Number(value).toFixed(digits);
};

const buildPayload = (
  families: Set<string>,
  axisA: string,
  axisB: string,
  gridSize: number,
  extent: number,
  seed: number,
): GraphFamilyCommandPayload => ({
  families: Array.from(families.values()),
  axes: [axisA, axisB],
  gridSize,
  extents: extent,
  seed,
});

const Phase5Optimize = () => {
  const [selectedFamilies, setSelectedFamilies] = useState<Set<string>>(
    () => new Set(familyOptions.map((option) => option.id)),
  );
  const [axisA, setAxisA] = useState(defaultAxes[0]);
  const [axisB, setAxisB] = useState(defaultAxes[1]);
  const [gridSizeInput, setGridSizeInput] = useState('21');
  const [extentInput, setExtentInput] = useState('0.02');
  const [seedInput, setSeedInput] = useState('123');
  const [result, setResult] = useState<GraphFamilyCommandResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleFamily = (id: string) => {
    setSelectedFamilies((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const sortedFamilies = useMemo<GraphFamilySummary[]>(() => {
    if (!result) {
      return [];
    }
    const entries = [...result.families];
    entries.sort((a, b) => {
      if (a.phiGuardOk !== b.phiGuardOk) {
        return a.phiGuardOk ? -1 : 1;
      }
      const aPhi = a.phiFlux ?? Number.NEGATIVE_INFINITY;
      const bPhi = b.phiFlux ?? Number.NEGATIVE_INFINITY;
      return Number(bPhi) - Number(aPhi);
    });
    return entries;
  }, [result]);

  const runAnalysis = async () => {
    if (!window?.CWT?.phase5?.cmdGraphFamily) {
      setError('Graph family command is unavailable in this build.');
      return;
    }

    const trimmedAxisA = axisA.trim();
    const trimmedAxisB = axisB.trim();
    if (!trimmedAxisA || !trimmedAxisB) {
      setError('Provide names for both loop axes.');
      return;
    }

    if (trimmedAxisA.toLowerCase() === trimmedAxisB.toLowerCase()) {
      setError('Axes must be distinct.');
      return;
    }

    const families = new Set(Array.from(selectedFamilies).map((item) => item.trim()).filter(Boolean));
    if (families.size === 0) {
      setError('Select at least one graph family.');
      return;
    }

    const gridSize = Number.parseInt(gridSizeInput, 10);
    if (!Number.isFinite(gridSize) || gridSize <= 0) {
      setError('Grid size must be a positive integer.');
      return;
    }

    const extent = Number.parseFloat(extentInput);
    if (!Number.isFinite(extent) || extent <= 0) {
      setError('Extent must be a positive number.');
      return;
    }

    const seed = Number.parseInt(seedInput, 10);
    if (!Number.isFinite(seed)) {
      setError('Seed must be numeric.');
      return;
    }

    setIsRunning(true);
    setError(null);
    setResult(null);

    try {
      const payload = buildPayload(families, trimmedAxisA, trimmedAxisB, gridSize, extent, seed);
      const response = await window.CWT.phase5.cmdGraphFamily(payload);
      if (!response.ok) {
        throw new Error(response.error ?? 'Graph family analysis failed');
      }
      setResult(response.data);
    } catch (analysisError) {
      setError(analysisError instanceof Error ? analysisError.message : String(analysisError));
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="panel phase5">
      <h2>Phase 5 – Optimization</h2>
      <p className="phase5__lede">
        Survey curated graph families, extract curvature statistics, and compare loop performance
        under Fubini–Study guards.
      </p>

      <div className="phase5__layout">
        <section className="phase5__controls">
          <h3>Topology sweep</h3>
          <p>Select candidate ensembles and sampling parameters, then launch an in-process sweep.</p>

          <div className="phase5__families">
            {familyOptions.map((family) => {
              const checked = selectedFamilies.has(family.id);
              return (
                <label key={family.id} className="phase5__family-option">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleFamily(family.id)}
                  />
                  <span>
                    <strong>{family.label}</strong>
                    <small>{family.description}</small>
                  </span>
                </label>
              );
            })}
          </div>

          <div className="phase5__input-grid">
            <label>
              Axis 1
              <input value={axisA} onChange={(event) => setAxisA(event.target.value)} />
            </label>
            <label>
              Axis 2
              <input value={axisB} onChange={(event) => setAxisB(event.target.value)} />
            </label>
            <label>
              Grid size
              <input
                value={gridSizeInput}
                onChange={(event) => setGridSizeInput(event.target.value)}
              />
            </label>
            <label>
              Extent
              <input
                value={extentInput}
                onChange={(event) => setExtentInput(event.target.value)}
              />
            </label>
            <label>
              Seed
              <input value={seedInput} onChange={(event) => setSeedInput(event.target.value)} />
            </label>
          </div>

          <button className="phase5__run" onClick={runAnalysis} disabled={isRunning}>
            {isRunning ? 'Running…' : 'Run topology sweep'}
          </button>

          {error ? <p className="phase5__error">{error}</p> : null}
        </section>

        <section className="phase5__results">
          <div className="phase5__results-header">
            <h3>Leaderboard</h3>
            {result ? (
              <div className="phase5__run-meta">
                <span>
                  Axes:&nbsp;
                  <code>
                    {result.axes[0]} × {result.axes[1]}
                  </code>
                </span>
                <span>
                  Grid:&nbsp;
                  <code>{result.gridSize}</code> pts, extent <code>{formatFloat(result.extent)}</code>
                </span>
                <span>
                  Seed:&nbsp;<code>{result.seed}</code>
                </span>
                {result.runtimeSeconds != null ? (
                  <span>
                    Runtime:&nbsp;
                    <code>{formatFloat(result.runtimeSeconds, 2)} s</code>
                  </span>
                ) : null}
              </div>
            ) : (
              <p className="phase5__placeholder">Run the sweep to populate the leaderboard.</p>
            )}
          </div>

          {sortedFamilies.length > 0 ? (
            <div className="phase5__leaderboard">
              {sortedFamilies.map((family) => {
                const phiValue = formatFloat(family.phiFlux, 4);
                const phiBadgeClass = family.phiGuardOk
                  ? 'badge badge--success'
                  : family.fsExceeded
                  ? 'badge badge--danger'
                  : 'badge badge--warning';
                const fsSummary =
                  family.fsP95 != null && family.fsBoundary != null
                    ? `${formatFloat(family.fsP95, 3)} vs ${formatFloat(family.fsBoundary, 3)}`
                    : '—';
                return (
                  <article key={family.name} className="phase5__leaderboard-item">
                    <header>
                      <h4>{family.name}</h4>
                      <span className={phiBadgeClass}>
                        Φ {family.phiGuardOk ? '' : '(warn)'} {phiValue}
                      </span>
                    </header>
                    <div className="phase5__metrics">
                      <dl>
                        <div>
                          <dt>median |Ω|</dt>
                          <dd>{formatScientific(family.medianAbsOmega)}</dd>
                        </div>
                        <div>
                          <dt>κ̄₁</dt>
                          <dd>{formatFloat(family.kappaMean)}</dd>
                        </div>
                        <div>
                          <dt>FS p95 / bound</dt>
                          <dd>{fsSummary}</dd>
                        </div>
                        <div>
                          <dt>Modularity</dt>
                          <dd>{formatFloat(family.modularity)}</dd>
                        </div>
                      </dl>
                      {family.thumbnail?.dataUrl ? (
                        <img
                          className="phase5__thumbnail"
                          src={family.thumbnail.dataUrl}
                          alt={`${family.name} FS thumbnail`}
                        />
                      ) : (
                        <div className="phase5__thumbnail phase5__thumbnail--empty">No preview</div>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          ) : null}

          {result ? (
            <details className="phase5__logs">
              <summary>Execution log</summary>
              <pre>{result.stdout.trim() || '(no stdout)'}</pre>
              {result.stderr.trim() ? <pre className="phase5__stderr">{result.stderr}</pre> : null}
              <p>
                Artifacts:&nbsp;
                <code>{result.outputDir}</code>
              </p>
            </details>
          ) : null}
        </section>
      </div>
    </div>
  );
};

export default Phase5Optimize;
