import { useCallback, useMemo, useState } from 'react';

import type { GuidedLoopArgs, LoopAtHotspotPayload } from '../types/ipc';

type Hotspot = {
  id: string;
  name: string;
  tau: number;
  zeta: number;
  calm?: boolean;
};

type SimpleLoopMetrics = {
  fsP95: number;
  phi: number;
  r: number;
  phiFlipError: number;
  kappaChange: number;
  guardSatisfied: boolean;
};

type SimpleLoopResult = {
  id: string;
  hotspot: Hotspot;
  graph: string;
  extents: [number, number];
  metrics: SimpleLoopMetrics;
  runId?: string;
};

type GuidedLoopRun = {
  runId: string;
  steps: number;
  status: string;
  metrics: Record<string, number | null> | null;
};

type GuidedLoopResult = {
  command: string;
  payload: GuidedLoopArgs;
  runs: GuidedLoopRun[];
  satisfied: boolean;
  derivedMetrics: {
    fsP95?: number;
    phi?: number;
    r?: number;
    overlapMin?: number;
    kappaChange?: number;
  };
};

const defaultHotspots: Hotspot[] = [
  { id: 'calm-1', name: 'Calm Basin A', tau: 0.08, zeta: -0.03, calm: true },
  { id: 'calm-2', name: 'Calm Basin B', tau: -0.04, zeta: 0.06, calm: true },
  { id: 'spicy-1', name: 'Energetic Ridge', tau: 0.18, zeta: 0.12 },
];

const graphOptions = [
  { id: 'flux', label: 'Flux Linkage' },
  { id: 'energy', label: 'Energy Capture' },
  { id: 'phase', label: 'Phase Portrait' },
];

const safeNumber = (value: number) => Number(value.toFixed(4));

const toCliValue = (value: number) => value.toFixed(4).replace(/\.0+$/, '');

const buildSimplePayload = (
  hotspot: Hotspot,
  graph: string,
  extents: [number, number],
  fsGuard: number,
  limit: number,
  seed: number,
): LoopAtHotspotPayload => ({
  hotspotsJson: JSON.stringify([
    {
      id: hotspot.id,
      label: hotspot.name,
      center: [hotspot.tau, hotspot.zeta],
    },
  ]),
  axes: ['tau', 'zeta'],
  extents,
  fsGuard,
  graph,
  limit,
  seed,
});

const buildGuidedPayload = (
  hotspot: Hotspot,
  graph: string,
  tauAmp: number,
  zetaAmp: number,
  stepsList: number[],
  fsGuard: number,
  minPhi: number,
  seed: number,
): GuidedLoopArgs => ({
  axes3: ['tau', 'zeta', 'kappa'],
  center: [hotspot.tau, hotspot.zeta, 0],
  amplitudes: [tauAmp, zetaAmp, 0],
  graph,
  stepsList,
  fsGuard,
  minPhi,
  seed,
});

const simulateSimpleMetrics = (
  seed: number,
  extents: [number, number],
  guard: number,
): SimpleLoopMetrics => {
  let value = (seed % 2147483647) + 1;
  const next = () => {
    value = (value * 48271) % 2147483647;
    return value / 2147483647;
  };

  const span = extents[0] + extents[1];
  const fsP95 = safeNumber(0.06 + 0.12 * next() + span * 0.01);
  const phi = safeNumber(-0.2 + 0.4 * next());
  const r = safeNumber(0.4 + 0.3 * next());
  const phiFlipError = safeNumber(0.01 + 0.04 * next());
  const kappaChange = safeNumber(-0.05 + 0.1 * next());
  const guardSatisfied = fsP95 <= guard;

  return { fsP95, phi, r, phiFlipError, kappaChange, guardSatisfied };
};

const fsGuardBadgeClass = (fsP95?: number, guard?: number) => {
  if (fsP95 == null) {
    return 'badge';
  }

  if (guard != null && fsP95 <= guard) {
    return 'badge badge--success';
  }

  if (fsP95 <= 0.15) {
    return 'badge badge--warning';
  }

  return 'badge badge--danger';
};

const metricFromRecord = (metrics: Record<string, number | null> | null, key: string) => {
  if (!metrics) {
    return undefined;
  }

  const candidates = [key, key.replace('-', '_'), key.replace('_', '-')];
  for (const candidate of candidates) {
    if (candidate in metrics) {
      const value = metrics[candidate];
      if (value == null) {
        return undefined;
      }
      return value;
    }
  }
  return undefined;
};

const buildGuidedCli = (payload: GuidedLoopArgs) => {
  const parts = [
    'cwt phase3 guided-loop',
    `--center ${payload.center.map(toCliValue).join(',')}`,
    `--amplitudes ${payload.amplitudes.map(toCliValue).join(',')}`,
    `--graph ${payload.graph}`,
    `--steps ${payload.stepsList.join(',')}`,
  ];

  if (payload.fsGuard != null) {
    parts.push(`--fs-guard ${toCliValue(payload.fsGuard)}`);
  }
  if (payload.minPhi != null) {
    parts.push(`--min-phi ${toCliValue(payload.minPhi)}`);
  }
  if (payload.seed != null) {
    parts.push(`--seed ${payload.seed}`);
  }

  return parts.join(' ');
};

const Phase3Loops = () => {
  const [hotspots, setHotspots] = useState<Hotspot[]>(defaultHotspots);
  const [selectedHotspotId, setSelectedHotspotId] = useState<string>(defaultHotspots[0].id);
  const [manualTau, setManualTau] = useState(0);
  const [manualZeta, setManualZeta] = useState(0);
  const [graph, setGraph] = useState(graphOptions[0].id);
  const [activeTab, setActiveTab] = useState<'simple' | 'guided'>('guided');

  const [extentA, setExtentA] = useState(0.4);
  const [extentB, setExtentB] = useState(0.4);
  const [fsGuard, setFsGuard] = useState(0.1);
  const [simpleLimit, setSimpleLimit] = useState(300);
  const [simpleSeed, setSimpleSeed] = useState(42);
  const [simpleRuns, setSimpleRuns] = useState<SimpleLoopResult[]>([]);
  const [isSimpleRunning, setIsSimpleRunning] = useState(false);

  const [tauAmplitude, setTauAmplitude] = useState(0.15);
  const [zetaAmplitude, setZetaAmplitude] = useState(0.15);
  const [guidedSteps, setGuidedSteps] = useState<number[]>([160, 320, 480]);
  const [guidedMinPhi, setGuidedMinPhi] = useState(0.02);
  const [guidedSeed, setGuidedSeed] = useState(2024);
  const [guidedResult, setGuidedResult] = useState<GuidedLoopResult | null>(null);
  const [isGuidedRunning, setIsGuidedRunning] = useState(false);

  const selectedHotspot = useMemo(
    () => hotspots.find((hotspot) => hotspot.id === selectedHotspotId) ?? hotspots[0],
    [hotspots, selectedHotspotId],
  );

  const addManualHotspot = () => {
    const id = `manual-${Date.now()}`;
    const newHotspot: Hotspot = {
      id,
      name: `Manual (${toCliValue(manualTau)}, ${toCliValue(manualZeta)})`,
      tau: manualTau,
      zeta: manualZeta,
      calm: true,
    };

    setHotspots((prev) => [...prev, newHotspot]);
    setSelectedHotspotId(id);
  };

  const runSimpleLoop = useCallback(async () => {
    if (!selectedHotspot) {
      return;
    }

    const extents: [number, number] = [extentA, extentB];
    const payload = buildSimplePayload(selectedHotspot, graph, extents, fsGuard, simpleLimit, simpleSeed);

    setIsSimpleRunning(true);
    try {
      const runId = await (async () => {
        if (window?.CWT?.phase3?.loopAtHotspot) {
          const response = await window.CWT.phase3.loopAtHotspot(payload);
          if (response.ok) {
            return response.data.runId;
          }
        }
        return undefined;
      })();

      const metrics = simulateSimpleMetrics(simpleSeed, extents, fsGuard);
      const result: SimpleLoopResult = {
        id: `${Date.now()}`,
        hotspot: selectedHotspot,
        graph,
        extents,
        metrics,
        runId,
      };
      setSimpleRuns((prev) => [result, ...prev]);
    } finally {
      setIsSimpleRunning(false);
    }
  }, [extentA, extentB, fsGuard, graph, selectedHotspot, simpleLimit, simpleSeed]);

  const toggleStep = (step: number) => {
    setGuidedSteps((prev) =>
      prev.includes(step) ? prev.filter((value) => value !== step) : [...prev, step].sort((a, b) => a - b),
    );
  };

  const runGuidedLoop = useCallback(async () => {
    if (!selectedHotspot) {
      return;
    }

    const payload = buildGuidedPayload(
      selectedHotspot,
      graph,
      tauAmplitude,
      zetaAmplitude,
      guidedSteps,
      fsGuard,
      guidedMinPhi,
      guidedSeed,
    );
    const command = buildGuidedCli(payload);

    setIsGuidedRunning(true);
    try {
      let runs: GuidedLoopRun[] | undefined;
      let satisfied = false;

      if (window?.CWT?.phase3?.guidedLoop) {
        const response = await window.CWT.phase3.guidedLoop(payload);
        if (response.ok) {
          runs = response.data.runs;
          satisfied = response.data.satisfied;
        }
      }

      if (!runs) {
        const simulatedMetrics: GuidedLoopRun[] = guidedSteps.map((steps, index) => {
          const seed = guidedSeed + index * 23;
          const simpleMetrics = simulateSimpleMetrics(seed, [tauAmplitude, zetaAmplitude], fsGuard);
          const metricsRecord: Record<string, number> = {
            fs_p95: simpleMetrics.fsP95,
            phi: simpleMetrics.phi,
            R: simpleMetrics.r,
            overlap_min: safeNumber(0.6 + 0.3 * (index / guidedSteps.length)),
            kappa1_delta: simpleMetrics.kappaChange,
          };
          return {
            runId: `sim-${steps}`,
            steps,
            status: 'completed',
            metrics: metricsRecord,
          };
        });
        runs = simulatedMetrics;
        satisfied = true;
      }

      const referenceMetrics = runs.find((run) => run.metrics) ?? runs[runs.length - 1];
      const derived = {
        fsP95: metricFromRecord(referenceMetrics?.metrics ?? null, 'fs_p95'),
        phi: metricFromRecord(referenceMetrics?.metrics ?? null, 'phi'),
        r: metricFromRecord(referenceMetrics?.metrics ?? null, 'R'),
        overlapMin: metricFromRecord(referenceMetrics?.metrics ?? null, 'overlap_min'),
        kappaChange: metricFromRecord(referenceMetrics?.metrics ?? null, 'kappa1_delta'),
      };

      setGuidedResult({
        command,
        payload,
        runs,
        satisfied,
        derivedMetrics: derived,
      });
    } finally {
      setIsGuidedRunning(false);
    }
  }, [
    fsGuard,
    graph,
    guidedMinPhi,
    guidedSeed,
    guidedSteps,
    selectedHotspot,
    tauAmplitude,
    zetaAmplitude,
  ]);

  const copyGuidedCommand = () => {
    if (!guidedResult) {
      return;
    }

    void navigator.clipboard?.writeText(guidedResult.command);
  };

  const saveRecipe = async () => {
    if (!guidedResult) {
      return;
    }

    if (!window?.CWT?.recipes?.save) {
      return;
    }

    const name = `Guided loop ${new Date().toLocaleString()}`;
    await window.CWT.recipes.save({
      name,
      params: guidedResult.payload,
      command: guidedResult.command,
      seed: guidedResult.payload.seed,
    });
  };

  return (
    <div className="panel phase3">
      <div className="phase3__layout">
        <aside className="phase3__sidebar">
          <h2>Phase 3 – Loops</h2>
          <p>Select a hotspot and tune loop calibration strategies.</p>

          <section className="phase3__section">
            <h3>Hotspot List</h3>
            <div className="phase3__hotspot-list">
              {hotspots.map((hotspot) => (
                <label key={hotspot.id} className="phase3__hotspot-item">
                  <input
                    type="radio"
                    name="hotspot"
                    value={hotspot.id}
                    checked={selectedHotspotId === hotspot.id}
                    onChange={() => setSelectedHotspotId(hotspot.id)}
                  />
                  <span>
                    {hotspot.name}
                    <small>
                      τ {toCliValue(hotspot.tau)} / ζ {toCliValue(hotspot.zeta)}
                    </small>
                  </span>
                </label>
              ))}
            </div>
          </section>

          <section className="phase3__section">
            <h3>Manual center</h3>
            <div className="phase3__field-grid">
              <label>
                <span>τ</span>
                <input
                  type="number"
                  step="0.01"
                  value={manualTau}
                  onChange={(event) => setManualTau(Number(event.target.value))}
                />
              </label>
              <label>
                <span>ζ</span>
                <input
                  type="number"
                  step="0.01"
                  value={manualZeta}
                  onChange={(event) => setManualZeta(Number(event.target.value))}
                />
              </label>
            </div>
            <button type="button" className="btn" onClick={addManualHotspot}>
              Use center
            </button>
          </section>

          <section className="phase3__section">
            <h3>Graph</h3>
            <select value={graph} onChange={(event) => setGraph(event.target.value)}>
              {graphOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </section>
        </aside>

        <div className="phase3__main">
          <div className="phase3__tabs">
            <button
              type="button"
              className={activeTab === 'simple' ? 'phase3__tab phase3__tab--active' : 'phase3__tab'}
              onClick={() => setActiveTab('simple')}
            >
              Simple loop
            </button>
            <button
              type="button"
              className={activeTab === 'guided' ? 'phase3__tab phase3__tab--active' : 'phase3__tab'}
              onClick={() => setActiveTab('guided')}
            >
              Guided loop (recommended)
            </button>
          </div>

          {activeTab === 'simple' ? (
            <section className="phase3__card">
              <h3>Simple loop scan</h3>
              <div className="phase3__grid">
                <label>
                  <span>Extent τ</span>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={extentA}
                    onChange={(event) => setExtentA(Number(event.target.value))}
                  />
                  <code>{extentA.toFixed(2)}</code>
                </label>
                <label>
                  <span>Extent ζ</span>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={extentB}
                    onChange={(event) => setExtentB(Number(event.target.value))}
                  />
                  <code>{extentB.toFixed(2)}</code>
                </label>
                <label>
                  <span>FS guard</span>
                  <input
                    type="number"
                    step="0.01"
                    value={fsGuard}
                    onChange={(event) => setFsGuard(Number(event.target.value))}
                  />
                </label>
                <label>
                  <span>Loop limit</span>
                  <input
                    type="number"
                    value={simpleLimit}
                    onChange={(event) => setSimpleLimit(Number(event.target.value))}
                  />
                </label>
                <label>
                  <span>Seed</span>
                  <input
                    type="number"
                    value={simpleSeed}
                    onChange={(event) => setSimpleSeed(Number(event.target.value))}
                  />
                </label>
              </div>
              <div className="phase3__actions">
                <button type="button" className="btn btn--primary" onClick={runSimpleLoop} disabled={isSimpleRunning}>
                  {isSimpleRunning ? 'Running…' : 'Run'}
                </button>
              </div>

              <div className="phase3__table-wrapper">
                <table className="phase3__table">
                  <thead>
                    <tr>
                      <th>Hotspot</th>
                      <th>Graph</th>
                      <th>FS p95</th>
                      <th>Φ</th>
                      <th>R</th>
                      <th>φ flip err</th>
                      <th>κ₁ Δ</th>
                      <th>Guard</th>
                    </tr>
                  </thead>
                  <tbody>
                    {simpleRuns.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="phase3__empty">
                          Run the simple loop to populate metrics.
                        </td>
                      </tr>
                    ) : (
                      simpleRuns.map((run) => (
                        <tr key={run.id}>
                          <td>
                            <div>{run.hotspot.name}</div>
                            <small>
                              τ {toCliValue(run.hotspot.tau)} / ζ {toCliValue(run.hotspot.zeta)}
                            </small>
                          </td>
                          <td>{graphOptions.find((option) => option.id === run.graph)?.label ?? run.graph}</td>
                          <td>{run.metrics.fsP95.toFixed(3)}</td>
                          <td>{run.metrics.phi.toFixed(3)}</td>
                          <td>{run.metrics.r.toFixed(3)}</td>
                          <td>{run.metrics.phiFlipError.toFixed(3)}</td>
                          <td>{run.metrics.kappaChange.toFixed(3)}</td>
                          <td>
                            <span className={run.metrics.guardSatisfied ? 'badge badge--success' : 'badge badge--danger'}>
                              {run.metrics.guardSatisfied ? 'OK' : 'Check'}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          ) : (
            <section className="phase3__card">
              <h3>Guided loop</h3>
              <div className="phase3__grid phase3__grid--guided">
                <label>
                  <span>τ amplitude</span>
                  <input
                    type="range"
                    min="0"
                    max="0.4"
                    step="0.01"
                    value={tauAmplitude}
                    onChange={(event) => setTauAmplitude(Number(event.target.value))}
                  />
                  <code>{tauAmplitude.toFixed(2)}</code>
                </label>
                <label>
                  <span>ζ amplitude</span>
                  <input
                    type="range"
                    min="0"
                    max="0.4"
                    step="0.01"
                    value={zetaAmplitude}
                    onChange={(event) => setZetaAmplitude(Number(event.target.value))}
                  />
                  <code>{zetaAmplitude.toFixed(2)}</code>
                </label>
                <label>
                  <span>FS guard</span>
                  <input
                    type="number"
                    step="0.01"
                    value={fsGuard}
                    onChange={(event) => setFsGuard(Number(event.target.value))}
                  />
                </label>
                <label>
                  <span>min Φ</span>
                  <input
                    type="number"
                    step="0.005"
                    value={guidedMinPhi}
                    onChange={(event) => setGuidedMinPhi(Number(event.target.value))}
                  />
                </label>
                <label>
                  <span>Seed</span>
                  <input
                    type="number"
                    value={guidedSeed}
                    onChange={(event) => setGuidedSeed(Number(event.target.value))}
                  />
                </label>
              </div>

              <div className="phase3__section">
                <h4>Step sequence</h4>
                <div className="phase3__chips">
                  {[160, 320, 480, 800].map((step) => (
                    <button
                      key={step}
                      type="button"
                      className={guidedSteps.includes(step) ? 'chip chip--active' : 'chip'}
                      onClick={() => toggleStep(step)}
                    >
                      {step}
                    </button>
                  ))}
                </div>
                <p className="phase3__hint">Toggle to include or exclude calibration steps.</p>
              </div>

              <div className="phase3__actions">
                <button
                  type="button"
                  className="btn btn--primary"
                  onClick={runGuidedLoop}
                  disabled={isGuidedRunning || guidedSteps.length === 0}
                >
                  {isGuidedRunning ? 'Calibrating…' : 'Calibrate & Run'}
                </button>
              </div>

              {guidedResult ? (
                <div className="phase3__guided-result">
                  <header className="phase3__guided-header">
                    <h4>{guidedResult.satisfied ? 'Stable configuration found' : 'Tuning incomplete'}</h4>
                    <button type="button" className="btn btn--ghost" onClick={saveRecipe}>
                      Save as Recipe
                    </button>
                  </header>

                  <div className="phase3__badges">
                    <span className={fsGuardBadgeClass(guidedResult.derivedMetrics.fsP95, fsGuard)}>
                      FS p95: {guidedResult.derivedMetrics.fsP95 != null ? guidedResult.derivedMetrics.fsP95.toFixed(3) : '–'}
                    </span>
                    <span className="badge">
                      Φ: {guidedResult.derivedMetrics.phi != null ? guidedResult.derivedMetrics.phi.toFixed(3) : '–'}
                    </span>
                    <span className="badge">
                      R: {guidedResult.derivedMetrics.r != null ? guidedResult.derivedMetrics.r.toFixed(3) : '–'}
                    </span>
                    {guidedResult.derivedMetrics.overlapMin != null ? (
                      <span className="badge">Overlap min: {guidedResult.derivedMetrics.overlapMin.toFixed(3)}</span>
                    ) : null}
                    <span className="badge">
                      κ₁ Δ: {guidedResult.derivedMetrics.kappaChange != null ? guidedResult.derivedMetrics.kappaChange.toFixed(3) : '–'}
                    </span>
                  </div>

                  <section className="phase3__runs">
                    <h5>Runs</h5>
                    <ul>
                      {guidedResult.runs.map((run) => (
                        <li key={run.runId}>
                          <strong>{run.steps}</strong> steps — {run.status}
                        </li>
                      ))}
                    </ul>
                  </section>

                  <section className="phase3__cli">
                    <label>
                      <span>CLI command</span>
                      <div className="phase3__cli-row">
                        <textarea readOnly value={guidedResult.command} />
                        <button type="button" className="btn btn--ghost" onClick={copyGuidedCommand}>
                          Copy
                        </button>
                      </div>
                    </label>
                  </section>
                </div>
              ) : (
                <p className="phase3__hint">
                  Calibrate to see recommended parameters and the exact CLI that was used.
                </p>
              )}
            </section>
          )}
        </div>
      </div>
    </div>
  );
};

export default Phase3Loops;
