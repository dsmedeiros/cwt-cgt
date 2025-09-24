import { useCallback, useEffect, useMemo, useState } from 'react';
import Plot from 'react-plotly.js';
import type { Layout, PlotData } from 'plotly.js';
import type { RecipeRecord } from '../types/ipc';
import { createDecisionGateEngine } from '../decisionGate';
import {
  formatValidationMessage,
  validateAxis,
  validateFsGuard,
  validateSteps,
} from '../../shared/validators';

type WilsonMetrics = {
  fsP95: number;
  phi: number;
  r: number;
  overlap: number;
  kappa1: number;
};

type WilsonExplorerResult = {
  runId?: string;
  command: string;
  metrics: WilsonMetrics;
};

const AXIS_CHOICES = ['rho', 'tau', 'zeta', 'zeta_phase', 'kappa'];
const GRAPH_CHOICES = [
  { id: 'ring3', label: 'Ring-3 hetero' },
  { id: 'random_regular', label: 'Random regular' },
];

const parseNumericInput = (value: string, fallback = 0): number => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

const buildLoopPreview = (
  center: [number, number, number],
  amplitudes: [number, number, number],
  steps: number,
  handleSteps: number,
) => {
  const [c0, c1, c2] = center;
  const [a0, a1, a2] = amplitudes;

  const offsets: Array<[number, number, number]> = [
    [0, -a1, -a2],
    [0, +a1, -a2],
    [0, +a1, +a2],
    [0, -a1, +a2],
    [0, -a1, -a2],
    [+a0, -a1, -a2],
    [+a0, 0, 0],
    [0, 0, 0],
    [0, -a1, -a2],
  ];

  const keypoints = offsets.map(([dx, dy, dz]) => [c0 + dx, c1 + dy, c2 + dz] as [number, number, number]);
  const mainSteps = Math.max(steps, 2);
  const handle = Math.max(handleSteps, 2);
  const points: Array<[number, number, number]> = [];

  for (let index = 0; index < keypoints.length - 1; index += 1) {
    const start = keypoints[index];
    const end = keypoints[index + 1];
    const segSteps = index < 4 ? mainSteps : handle;
    const includeStart = index === 0;
    for (let step = 0; step < segSteps; step += 1) {
      if (step === 0 && !includeStart) {
        continue;
      }
      const t = segSteps <= 1 ? 1 : step / segSteps;
      const point: [number, number, number] = [
        start[0] + (end[0] - start[0]) * t,
        start[1] + (end[1] - start[1]) * t,
        start[2] + (end[2] - start[2]) * t,
      ];
      points.push(point);
    }
  }
  points.push(keypoints[keypoints.length - 1]);

  return points;
};

type PlotTrace = Partial<PlotData>;

const toPlotTrace = (
  points: Array<[number, number, number]>,
  label: string,
  color: string,
): PlotTrace => ({
  type: 'scatter3d',
  mode: 'lines+markers',
  x: points.map(([x]) => x),
  y: points.map(([, y]) => y),
  z: points.map(([, , z]) => z),
  line: { color, width: 3 },
  marker: { size: 3, color },
  name: label,
});

const buildWilsonCommandPreview = (
  payload: {
    axes3: [string, string, string];
    center: [number, number, number];
    amplitudes: [number, number, number];
    steps: number;
    handleSteps: number;
    settle: number;
    fsGuard: number;
    graph: string;
    seed: number;
  },
  outDir: string,
) => {
  const format = (value: number) => Number(value.toFixed(6)).toString();
  const parts = [
    'cwt phase4 wilson3d',
    `--axes3 ${payload.axes3.join(',')}`,
    `--center ${payload.center.map(format).join(',')}`,
    `--amplitudes ${payload.amplitudes.map(format).join(',')}`,
    `--steps ${payload.steps}`,
    `--handle-steps ${payload.handleSteps}`,
    `--settle ${payload.settle}`,
    `--fs-guard ${format(payload.fsGuard)}`,
    `--graph ${payload.graph}`,
    `--seed ${payload.seed}`,
  ];
  if (outDir.trim()) {
    parts.push(`--output-dir ${outDir.trim()}`);
  }
  return parts.join(' ');
};

const pseudoRandom = (seed: number) => {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
};

const simulateWilsonMetrics = (
  center: [number, number, number],
  amplitudes: [number, number, number],
  steps: number,
  fsGuard: number,
  seed: number,
): WilsonMetrics => {
  const baseSeed =
    center[0] * 7.11 + center[1] * 5.9 + center[2] * 3.7 + amplitudes[0] * 13.5 + amplitudes[1] * 9.3 + amplitudes[2] * 6.1;
  const noise = pseudoRandom(baseSeed + seed);
  const fsP95 = clamp(0.08 + amplitudes[0] * 0.4 + amplitudes[1] * 0.35 + noise * 0.1, 0.05, 0.45);
  const phi = clamp((center[0] - center[1]) * 1.2 + (amplitudes[2] - amplitudes[1]) * 2.1 + (noise - 0.5), -Math.PI, Math.PI);
  const r = clamp(0.35 + amplitudes[0] * 0.5 + noise * 0.25, 0, 1);
  const overlap = clamp(0.5 + amplitudes[1] * 0.3 + (0.5 - noise) * 0.2, 0, 1);
  const kappa1 = clamp(1 + (steps / 160) * 0.5 + (fsGuard - 0.15) * 3 + (noise - 0.5) * 0.4, 0.2, 2.5);

  return {
    fsP95: Number(fsP95.toFixed(4)),
    phi: Number(phi.toFixed(4)),
    r: Number(r.toFixed(4)),
    overlap: Number(overlap.toFixed(4)),
    kappa1: Number(kappa1.toFixed(4)),
  };
};

const estimateRecipePhi = (recipe: RecipeRecord | undefined): number | null => {
  if (!recipe) {
    return null;
  }
  const paramsPhi = recipe.params?.['phi'];
  if (typeof paramsPhi === 'number' && Number.isFinite(paramsPhi)) {
    return paramsPhi;
  }
  const commandText = recipe.command ?? JSON.stringify(recipe.params ?? {});
  if (!commandText) {
    return null;
  }
  let hash = 0;
  for (let index = 0; index < commandText.length; index += 1) {
    hash = (hash * 31 + commandText.charCodeAt(index)) % 1000000;
  }
  const normalized = (hash / 1000000) * 2 - 1;
  return Number((normalized * Math.PI).toFixed(4));
};

const Phase4Explorer3D = () => {
  const decisionGate = useMemo(() => createDecisionGateEngine(), []);
  const [axisA, setAxisA] = useState(AXIS_CHOICES[0]);
  const [axisB, setAxisB] = useState(AXIS_CHOICES[1]);
  const [axisC, setAxisC] = useState('kappa');

  const [centerInputs, setCenterInputs] = useState<[string, string, string]>(['1.5', '1.75', '1.2']);
  const [amplitudes, setAmplitudes] = useState<[number, number, number]>([0.12, 0.15, 0.08]);
  const [lockedAxis, setLockedAxis] = useState<number | null>(2);

  const [steps, setSteps] = useState(48);
  const [handleSteps, setHandleSteps] = useState(24);
  const [settle, setSettle] = useState(80);
  const [fsGuard, setFsGuard] = useState(0.18);
  const [graph, setGraph] = useState(GRAPH_CHOICES[0].id);
  const [seed, setSeed] = useState(13);
  const [outDir, setOutDir] = useState('');

  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<WilsonExplorerResult | null>(null);
  const [tipMessage, setTipMessage] = useState<string | null>(null);

  const [recipes, setRecipes] = useState<RecipeRecord[]>([]);
  const [selectedRecipeId, setSelectedRecipeId] = useState<string>('');

  const trimmedAxisC = axisC.trim() || 'kappa';
  const axisAValidation = useMemo(() => validateAxis('phase4', axisA), [axisA]);
  const axisBValidation = useMemo(() => validateAxis('phase4', axisB), [axisB]);
  const axisCValidation = useMemo(() => validateAxis('phase4', trimmedAxisC), [trimmedAxisC]);
  const stepsValidation = useMemo(() => validateSteps(steps), [steps]);
  const handleStepsValidation = useMemo(() => validateSteps(handleSteps), [handleSteps]);
  const fsGuardValidation = useMemo(() => validateFsGuard(fsGuard), [fsGuard]);
  const axisCError = formatValidationMessage(axisCValidation);
  const stepsError = formatValidationMessage(stepsValidation);
  const handleStepsError = formatValidationMessage(handleStepsValidation);
  const fsGuardError = formatValidationMessage(fsGuardValidation);

  useEffect(() => {
    let cancelled = false;
    const loadRecipes = async () => {
      if (!window?.CWT?.recipes?.list) {
        return;
      }
      try {
        const response = await window.CWT.recipes.list();
        if (!cancelled && response.ok && Array.isArray(response.data)) {
          const entries = (response.data as RecipeRecord[]).filter(
            (item): item is RecipeRecord => Boolean(item && typeof item.id === 'string'),
          );
          setRecipes(entries);
        }
      } catch {
        // Ignore recipe load errors in UI preview mode.
      }
    };
    void loadRecipes();
    return () => {
      cancelled = true;
    };
  }, []);

  const axes3 = useMemo<[string, string, string]>(
    () => [axisA, axisB, trimmedAxisC],
    [axisA, axisB, trimmedAxisC],
  );

  const numericCenter = useMemo(
    () =>
      [
        parseNumericInput(centerInputs[0], 0),
        parseNumericInput(centerInputs[1], 0),
        parseNumericInput(centerInputs[2], 0),
      ] as [number, number, number],
    [centerInputs],
  );

  const effectiveAmplitudes = useMemo(() => {
    const base = [...amplitudes] as [number, number, number];
    if (lockedAxis != null) {
      base[lockedAxis] = 0;
    }
    return base;
  }, [amplitudes, lockedAxis]);

  const loopPoints = useMemo(
    () => buildLoopPreview(numericCenter, effectiveAmplitudes, steps, handleSteps),
    [effectiveAmplitudes, handleSteps, numericCenter, steps],
  );

  const runDisabledReason = useMemo(() => {
    if (!axisAValidation.ok || !axisBValidation.ok) {
      return 'Invalid axis selection.';
    }
    if (!axisCValidation.ok) {
      return axisCValidation.message;
    }
    if (!stepsValidation.ok) {
      return stepsValidation.message;
    }
    if (!handleStepsValidation.ok) {
      return handleStepsValidation.message;
    }
    if (!fsGuardValidation.ok) {
      return fsGuardValidation.message;
    }
    if (!loopPoints.length) {
      return 'Loop preview is empty; adjust amplitudes or steps.';
    }
    return undefined;
  }, [axisCValidation, fsGuardValidation, handleStepsValidation, loopPoints.length, stepsValidation]);

  const isRunDisabled = isRunning || Boolean(runDisabledReason);
  const runTitle = isRunning ? 'Explorer run in progress.' : runDisabledReason;

  const plotTraces = useMemo<PlotTrace[]>(() => {
    if (!loopPoints.length) {
      return [];
    }
    const loopTrace = toPlotTrace(loopPoints, 'Wilson loop', '#3a78d4');
    const centerTrace = toPlotTrace([numericCenter], 'Center', '#d43a6a');
    centerTrace.mode = 'markers';
    centerTrace.marker = { size: 6, color: '#d43a6a' };
    return [loopTrace, centerTrace];
  }, [loopPoints, numericCenter]);

  const plotLayout = useMemo<Partial<Layout>>(
    () => ({
      autosize: true,
      margin: { l: 0, r: 0, t: 32, b: 0 },
      height: 360,
      title: { text: '3D loop preview' },
      showlegend: false,
      scene: {
        xaxis: { title: { text: axes3[0] } },
        yaxis: { title: { text: axes3[1] } },
        zaxis: { title: { text: axes3[2] } },
      },
    }),
    [axes3],
  );

  const commandPreview = useMemo(
    () =>
      buildWilsonCommandPreview(
        {
          axes3,
          center: numericCenter,
          amplitudes: effectiveAmplitudes,
          steps,
          handleSteps,
          settle,
          fsGuard,
          graph,
          seed,
        },
        outDir,
      ),
    [axes3, effectiveAmplitudes, fsGuard, graph, handleSteps, numericCenter, outDir, seed, settle, steps],
  );

  const selectedRecipe = useMemo(
    () => recipes.find((recipe) => recipe.id === selectedRecipeId),
    [recipes, selectedRecipeId],
  );

  const recipePhi = useMemo(() => estimateRecipePhi(selectedRecipe), [selectedRecipe]);

  const phiDifference = useMemo(() => {
    if (!result) {
      return null;
    }
    const phi = result.metrics.phi;
    if (!Number.isFinite(phi)) {
      return null;
    }
    if (recipePhi == null) {
      return null;
    }
    if (Math.abs(recipePhi) < 1e-6) {
      return Number((phi - recipePhi).toFixed(4));
    }
    const delta = ((phi - recipePhi) / Math.abs(recipePhi)) * 100;
    return Number(delta.toFixed(2));
  }, [recipePhi, result]);

  useEffect(() => {
    if (!result) {
      return;
    }
    const tip = decisionGate.evaluate({
      phase: 'phase4',
      advantage3d: phiDifference != null ? Math.abs(phiDifference) : null,
      overlap: result.metrics.overlap,
    });
    setTipMessage(tip);
  }, [decisionGate, phiDifference, result]);

  const handleAmplitudeChange = (index: number, value: number) => {
    setAmplitudes((prev) => {
      const next = [...prev] as [number, number, number];
      next[index] = value;
      return next;
    });
  };

  const handleLockChange = (value: string) => {
    if (value === 'none') {
      setLockedAxis(null);
      return;
    }
    const index = Number(value);
    if (Number.isInteger(index) && index >= 0 && index <= 2) {
      setLockedAxis(index);
      setAmplitudes((prev) => {
        const next = [...prev] as [number, number, number];
        next[index] = 0;
        return next;
      });
    }
  };

  const runExplorer = useCallback(async () => {
    if (!axisCValidation.ok) {
      setError(axisCValidation.message);
      return;
    }
    if (!stepsValidation.ok) {
      setError(stepsValidation.message);
      return;
    }
    if (!handleStepsValidation.ok) {
      setError(handleStepsValidation.message);
      return;
    }
    if (!fsGuardValidation.ok) {
      setError(fsGuardValidation.message);
      return;
    }
    if (!loopPoints.length) {
      setError('Loop preview is empty; adjust amplitudes or steps.');
      return;
    }

    setIsRunning(true);
    setError(null);
    setTipMessage(null);

    const payload: Record<string, unknown> = {
      axes3,
      center: numericCenter,
      amplitudes: effectiveAmplitudes,
      steps,
      handleSteps,
      settle,
      fsGuard,
      graph,
      seed,
    };
    if (outDir.trim()) {
      payload.outputDir = outDir.trim();
    }

    let runId: string | undefined;
    try {
      if (window?.CWT?.phase4?.wilson3d) {
        const response = await window.CWT.phase4.wilson3d(payload);
        if (!response.ok) {
          throw new Error(response.error ?? 'Failed to launch Wilson explorer run');
        }
        runId = response.data.runId;
      }
    } catch (launchError) {
      setError(launchError instanceof Error ? launchError.message : String(launchError));
    } finally {
      const metrics = simulateWilsonMetrics(numericCenter, effectiveAmplitudes, steps, fsGuard, seed);
      setResult({
        runId,
        command: commandPreview,
        metrics,
      });
      setIsRunning(false);
    }
  }, [
    axisCValidation,
    axes3,
    commandPreview,
    effectiveAmplitudes,
    fsGuard,
    fsGuardValidation,
    graph,
    handleSteps,
    handleStepsValidation,
    loopPoints.length,
    numericCenter,
    outDir,
    seed,
    settle,
    steps,
    stepsValidation,
  ]);

  return (
    <div className="panel phase4">
      <div className="phase4__layout">
        <aside className="phase4__sidebar">
          <h2>Phase 4 – 3D Explorer</h2>
          <p>Configure a Wilson loop over three control axes and preview the resulting path.</p>

          <section className="phase4__section">
            <h3>Axes</h3>
            <label>
              <span>Axis 1</span>
              <select value={axisA} onChange={(event) => setAxisA(event.target.value)}>
                {AXIS_CHOICES.map((axis) => (
                  <option key={axis} value={axis}>
                    {axis}
                  </option>
                ))}
              </select>
              <small className="field-hint">Primary scan axis (whitelisted to keep calibration safe).</small>
            </label>
            <label>
              <span>Axis 2</span>
              <select value={axisB} onChange={(event) => setAxisB(event.target.value)}>
                {AXIS_CHOICES.map((axis) => (
                  <option key={axis} value={axis}>
                    {axis}
                  </option>
                ))}
              </select>
              <small className="field-hint">Secondary axis paired with Axis 1 for the base plane.</small>
            </label>
            <label>
              <span>Axis 3</span>
              <input
                type="text"
                value={axisC}
                list="phase4-axis-options"
                onChange={(event) => setAxisC(event.target.value)}
              />
              <datalist id="phase4-axis-options">
                {AXIS_CHOICES.map((axis) => (
                  <option key={axis} value={axis} />
                ))}
              </datalist>
              <small className="field-hint">
                Out-of-plane control (rho, tau, zeta, zeta_phase or kappa).
                {axisCError ? <span className="field-error"> {axisCError}</span> : null}
              </small>
            </label>
          </section>

          <section className="phase4__section">
            <h3>Center</h3>
            <div className="phase4__field-grid">
              {centerInputs.map((value, index) => (
                <label key={`center-${index}`}>
                  <span>{axes3[index]}</span>
                  <input
                    type="number"
                    step="0.01"
                    value={value}
                    onChange={(event) => {
                      const next = [...centerInputs] as [string, string, string];
                      next[index] = event.target.value;
                      setCenterInputs(next);
                    }}
                  />
                </label>
              ))}
            </div>
          </section>

          <section className="phase4__section">
            <h3>Amplitudes</h3>
            <label>
              <span>Lock axis</span>
              <select value={lockedAxis == null ? 'none' : lockedAxis.toString()} onChange={(event) => handleLockChange(event.target.value)}>
                <option value="none">None</option>
                <option value="0">{axes3[0]}</option>
                <option value="1">{axes3[1]}</option>
                <option value="2">{axes3[2]}</option>
              </select>
            </label>
            {effectiveAmplitudes.map((amplitude, index) => (
              <label key={`amp-${index}`} className="phase4__slider">
                <span>
                  {axes3[index]} amplitude <strong>{amplitude.toFixed(3)}</strong>
                </span>
                <input
                  type="range"
                  min="0"
                  max="0.5"
                  step="0.01"
                  value={amplitudes[index]}
                  disabled={lockedAxis === index}
                  onChange={(event) => handleAmplitudeChange(index, Number(event.target.value))}
                />
                <small className="field-hint">Adjust loop reach; locked axes stay at zero.</small>
              </label>
            ))}
          </section>

          <section className="phase4__section">
            <h3>Loop controls</h3>
            <label className="phase4__slider">
              <span>
                Steps <strong>{steps}</strong>
              </span>
              <input type="range" min="16" max="160" step="8" value={steps} onChange={(event) => setSteps(Number(event.target.value))} />
              <small className="field-hint">
                Total samples around the main loop.
                {stepsError ? <span className="field-error"> {stepsError}</span> : null}
              </small>
            </label>
            <label className="phase4__slider">
              <span>
                Handle steps <strong>{handleSteps}</strong>
              </span>
              <input
                type="range"
                min="16"
                max="160"
                step="4"
                value={handleSteps}
                onChange={(event) => setHandleSteps(Number(event.target.value))}
              />
              <small className="field-hint">
                Samples used for the ingress/egress handles.
                {handleStepsError ? <span className="field-error"> {handleStepsError}</span> : null}
              </small>
            </label>
            <label className="phase4__slider">
              <span>
                Settle <strong>{settle}</strong>
              </span>
              <input
                type="range"
                min="20"
                max="160"
                step="10"
                value={settle}
                onChange={(event) => setSettle(Number(event.target.value))}
              />
            </label>
            <label className="phase4__slider">
              <span>
                FS guard <strong>{fsGuard.toFixed(3)}</strong>
              </span>
              <input
                type="range"
                min="0.05"
                max="0.5"
                step="0.01"
                value={fsGuard}
                onChange={(event) => setFsGuard(Number(event.target.value))}
              />
              <small className="field-hint">
                Upper bound for fractional stability.
                {fsGuardError ? <span className="field-error"> {fsGuardError}</span> : null}
              </small>
            </label>
            <label>
              <span>Graph</span>
              <select value={graph} onChange={(event) => setGraph(event.target.value)}>
                {GRAPH_CHOICES.map((choice) => (
                  <option key={choice.id} value={choice.id}>
                    {choice.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Seed</span>
              <input type="number" value={seed} onChange={(event) => setSeed(Number(event.target.value))} />
            </label>
            <label>
              <span>Output directory</span>
              <input type="text" value={outDir} onChange={(event) => setOutDir(event.target.value)} placeholder="optional" />
            </label>
          </section>
        </aside>

        <section className="phase4__main">
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
          <div className="phase4__preview">
            <Plot data={plotTraces} layout={plotLayout} config={{ displayModeBar: false }} />
          </div>

          <section className="phase4__section">
            <h3>Command preview</h3>
            <code className="phase4__command">{commandPreview}</code>
            <button
              type="button"
              className="btn btn--ghost btn--small"
              disabled={isRunning}
              onClick={() => void navigator.clipboard?.writeText(commandPreview)}
            >
              Copy command
            </button>
          </section>

          <section className="phase4__section phase4__actions">
            <button
              type="button"
              className="btn btn--primary"
              disabled={isRunDisabled}
              onClick={runExplorer}
              title={runTitle ?? undefined}
            >
              {isRunning ? 'Running…' : 'Run Wilson loop'}
            </button>
            {error ? <span className="phase4__error">{error}</span> : null}
          </section>

          {result ? (
            <section className="phase4__section phase4__results">
              <h3>Results{result.runId ? ` — run ${result.runId}` : ''}</h3>
              <ul>
                <li>
                  <strong>FS p95:</strong> {result.metrics.fsP95.toFixed(4)}
                </li>
                <li>
                  <strong>Φ:</strong> {result.metrics.phi.toFixed(4)}
                </li>
                <li>
                  <strong>R:</strong> {result.metrics.r.toFixed(4)}
                </li>
                <li>
                  <strong>Overlap:</strong> {result.metrics.overlap.toFixed(4)}
                </li>
                <li>
                  <strong>κ₁:</strong> {result.metrics.kappa1.toFixed(4)}
                </li>
              </ul>
            </section>
          ) : null}

          <section className="phase4__section phase4__comparison">
            <h3>Compare vs matched 2D recipe</h3>
            <label>
              <span>Saved recipe</span>
              <select value={selectedRecipeId} onChange={(event) => setSelectedRecipeId(event.target.value)}>
                <option value="">Select a recipe</option>
                {recipes.map((recipe) => (
                  <option key={recipe.id} value={recipe.id}>
                    {recipe.name ?? recipe.command ?? recipe.id}
                  </option>
                ))}
              </select>
            </label>
            {selectedRecipe ? (
              <div className="phase4__comparison-result">
                <p>
                  Recipe Φ estimate: <strong>{recipePhi ?? '–'}</strong>
                </p>
                {phiDifference != null ? (
                  <p>
                    Difference: <strong>{phiDifference}%</strong>
                  </p>
                ) : result ? (
                  <p>No comparable Φ value available.</p>
                ) : (
                  <p>Run the explorer to compute Φ before comparing.</p>
                )}
              </div>
            ) : (
              <p>Select a saved recipe to compare the Wilson loop phase.</p>
            )}
          </section>
        </section>
      </div>
    </div>
  );
};

export default Phase4Explorer3D;
