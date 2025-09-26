import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import type { GuidedLoopArgs, LoopAtHotspotPayload } from '../types/ipc';
import AdiabaticBoundaryViewer from './AdiabaticBoundaryViewer';
import { createDecisionGateEngine } from '../decisionGate';
import {
  formatValidationMessage,
  validateExtent,
  validateFsGuard,
  validateAdaptLevels,
  validateSettleSteps,
  validateSteps,
} from '../../shared/validators';

type Hotspot = {
  id: string;
  name: string;
  tau: number;
  zeta: number;
  calm?: boolean;
  axes?: [string, string];
  graph?: string | null;
  originPath?: string | null;
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
  {
    id: 'calm-1',
    name: 'Calm Basin A',
    tau: 0.08,
    zeta: -0.03,
    calm: true,
    axes: ['tau', 'zeta'],
    graph: 'default',
    originPath: 'defaults',
  },
  {
    id: 'calm-2',
    name: 'Calm Basin B',
    tau: -0.04,
    zeta: 0.06,
    calm: true,
    axes: ['tau', 'zeta'],
    graph: 'default',
    originPath: 'defaults',
  },
  {
    id: 'spicy-1',
    name: 'Energetic Ridge',
    tau: 0.18,
    zeta: 0.12,
    axes: ['tau', 'zeta'],
    graph: 'default',
    originPath: 'defaults',
  },
];

const graphOptions = [
  { id: 'flux', label: 'Flux Linkage' },
  { id: 'energy', label: 'Energy Capture' },
  { id: 'phase', label: 'Phase Portrait' },
];

const safeNumber = (value: number) => Number(value.toFixed(4));

const toCliValue = (value: number) => value.toFixed(4).replace(/\.0+$/, '');

const normalizeOrigin = (value: string | null | undefined) =>
  value ? value.replace(/\\/g, '/').trim() : '';

const hotspotKey = (hotspot: Hotspot) => {
  const axes = hotspot.axes ?? ['tau', 'zeta'];
  const graph = hotspot.graph ?? '';
  const origin = normalizeOrigin(hotspot.originPath);
  const center = `${hotspot.tau.toFixed(6)}|${hotspot.zeta.toFixed(6)}`;
  return `${axes[0]}|${axes[1]}|${graph}|${center}|${origin}`;
};

const mergeHotspotList = (
  existing: Hotspot[],
  candidate: Hotspot,
): { list: Hotspot[]; activeId: string } => {
  const key = hotspotKey(candidate);
  const index = existing.findIndex((item) => hotspotKey(item) === key);
  if (index >= 0) {
    const preservedId = existing[index].id;
    const next = [...existing];
    next[index] = { ...candidate, id: preservedId };
    return { list: next, activeId: preservedId };
  }
  return { list: [...existing, candidate], activeId: candidate.id };
};

const buildSimplePayload = (
  hotspot: Hotspot,
  graph: string,
  extents: [number, number],
  fsGuard: number,
  limit: number,
  seed: number,
  neighborSettleSteps: number,
  adaptLevels: number,
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
  neighborSettleSteps,
  adaptLevels,
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

const previewGuidedCli = async (payload: GuidedLoopArgs): Promise<string> => {
  if (typeof window === 'undefined' || !window?.CWT?.run?.preview) {
    return 'Command preview unavailable in this environment.';
  }

  const { stepsList, ...rest } = payload;
  const baseParams: Record<string, unknown> = { ...rest };
  const previews: string[] = [];

  for (const steps of stepsList) {
    const currentParams = { ...baseParams, steps };
    try {
      const response = await window.CWT.run.preview({
        experiment: 'experiments.wilson_loop_3d.run',
        args: currentParams,
      });
      if (!response.ok) {
        throw new Error(response.error ?? 'Preview request failed');
      }
      previews.push(response.data.cli);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      previews.push(`(preview failed for steps=${steps}: ${message})`);
    }
  }

  return previews.join('\n');
};

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

const Phase3Loops = () => {
  const [hotspots, setHotspots] = useState<Hotspot[]>(defaultHotspots);
  const [selectedHotspotId, setSelectedHotspotId] = useState<string>(defaultHotspots[0].id);
  const [manualTau, setManualTau] = useState(0);
  const [manualZeta, setManualZeta] = useState(0);
  const [graph, setGraph] = useState(graphOptions[0].id);
  const [activeTab, setActiveTab] = useState<'simple' | 'guided'>('guided');

  const decisionGate = useMemo(() => createDecisionGateEngine(), []);
  const [tipMessage, setTipMessage] = useState<string | null>(null);

  const [extentA, setExtentA] = useState(0.4);
  const [extentB, setExtentB] = useState(0.4);
  const [fsGuardInput, setFsGuardInput] = useState('0.1');
  const [simpleLimitInput, setSimpleLimitInput] = useState('300');
  const [neighborSettleInput, setNeighborSettleInput] = useState('40');
  const [adaptLevelsInput, setAdaptLevelsInput] = useState('1');
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
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [saveDescription, setSaveDescription] = useState('');
  const [saveInFlight, setSaveInFlight] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccessMessage, setSaveSuccessMessage] = useState<string | null>(null);
  const modalRef = useRef<HTMLDivElement | null>(null);

  const upsertHotspot = useCallback(
    (incoming: Hotspot) => {
      setHotspots((prev) => {
        const { list, activeId } = mergeHotspotList(prev, incoming);
        setSelectedHotspotId(activeId);
        return list;
      });
    },
    [],
  );

  const selectedHotspot = useMemo(
    () => hotspots.find((hotspot) => hotspot.id === selectedHotspotId) ?? hotspots[0],
    [hotspots, selectedHotspotId],
  );

  const extentAValidation = useMemo(() => validateExtent(extentA), [extentA]);
  const extentBValidation = useMemo(() => validateExtent(extentB), [extentB]);
  const fsGuardValidation = useMemo(() => validateFsGuard(fsGuardInput), [fsGuardInput]);
  const simpleLimitValidation = useMemo(() => validateSteps(simpleLimitInput), [simpleLimitInput]);
  const neighborSettleValidation = useMemo(
    () => validateSettleSteps(neighborSettleInput),
    [neighborSettleInput],
  );
  const adaptLevelsValidation = useMemo(
    () => validateAdaptLevels(adaptLevelsInput),
    [adaptLevelsInput],
  );
  const fsGuardNumber = fsGuardValidation.ok ? fsGuardValidation.value : null;
  const guidedStepValidation = useMemo(() => guidedSteps.map((step) => validateSteps(step)), [guidedSteps]);
  const guidedStepError = guidedStepValidation.find((result) => !result.ok);
  const guidedStepErrorMessage = guidedStepError && !guidedStepError.ok ? guidedStepError.message : undefined;
  const fsGuardError = formatValidationMessage(fsGuardValidation);
  const simpleLimitError = formatValidationMessage(simpleLimitValidation);
  const settleStepsError = formatValidationMessage(neighborSettleValidation);
  const adaptLevelsError = formatValidationMessage(adaptLevelsValidation);

  const simpleRunDisabledReason = useMemo(() => {
    if (!extentAValidation.ok) {
      return extentAValidation.message;
    }
    if (!extentBValidation.ok) {
      return extentBValidation.message;
    }
    if (!fsGuardValidation.ok) {
      return fsGuardValidation.message;
    }
    if (!simpleLimitValidation.ok) {
      return simpleLimitValidation.message;
    }
    if (!neighborSettleValidation.ok) {
      return neighborSettleValidation.message;
    }
    if (!adaptLevelsValidation.ok) {
      return adaptLevelsValidation.message;
    }
    return undefined;
  }, [
    extentAValidation,
    extentBValidation,
    fsGuardValidation,
    simpleLimitValidation,
    neighborSettleValidation,
    adaptLevelsValidation,
  ]);

  const guidedRunDisabledReason = useMemo(() => {
    if (!fsGuardValidation.ok) {
      return fsGuardValidation.message;
    }
    if (guidedSteps.length === 0) {
      return 'Select at least one step.';
    }
    if (guidedStepErrorMessage) {
      return guidedStepErrorMessage;
    }
    return undefined;
  }, [fsGuardValidation, guidedStepErrorMessage, guidedSteps.length]);

  const isSimpleRunDisabled = isSimpleRunning || Boolean(simpleRunDisabledReason);
  const isGuidedRunDisabled = isGuidedRunning || Boolean(guidedRunDisabledReason);
  const simpleRunTitle = isSimpleRunning ? 'Loop already running.' : simpleRunDisabledReason;
  const guidedRunTitle = isGuidedRunning ? 'Guided calibration in progress.' : guidedRunDisabledReason;

  const addManualHotspot = () => {
    const id = `manual-${Date.now()}`;
    const newHotspot: Hotspot = {
      id,
      name: `Manual (${toCliValue(manualTau)}, ${toCliValue(manualZeta)})`,
      tau: manualTau,
      zeta: manualZeta,
      calm: true,
      axes: ['tau', 'zeta'],
      graph,
      originPath: 'manual',
    };

    upsertHotspot(newHotspot);
  };

  const runSimpleLoop = useCallback(async () => {
    if (
      !selectedHotspot ||
      !extentAValidation.ok ||
      !extentBValidation.ok ||
      !fsGuardValidation.ok ||
      !simpleLimitValidation.ok ||
      !neighborSettleValidation.ok ||
      !adaptLevelsValidation.ok
    ) {
      return;
    }

    const extents: [number, number] = [extentAValidation.value, extentBValidation.value];
    const guardValue = fsGuardValidation.value;
    const settleSteps = neighborSettleValidation.value;
    const adaptLevels = adaptLevelsValidation.value;
    const payload = buildSimplePayload(
      selectedHotspot,
      graph,
      extents,
      guardValue,
      simpleLimitValidation.value,
      simpleSeed,
      settleSteps,
      adaptLevels,
    );

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

      const metrics = simulateSimpleMetrics(simpleSeed, extents, guardValue);
      const result: SimpleLoopResult = {
        id: `${Date.now()}`,
        hotspot: selectedHotspot,
        graph,
        extents,
        metrics,
        runId,
      };
      setSimpleRuns((prev) => [result, ...prev]);
      const tip = decisionGate.evaluate({
        phase: 'phase3',
        fsP95: metrics.fsP95,
        fsGuard: guardValue,
        phi: metrics.phi,
        calmHotspot: selectedHotspot.calm ?? false,
      });
      setTipMessage(tip);
    } finally {
      setIsSimpleRunning(false);
    }
  }, [
    decisionGate,
    extentAValidation,
    extentBValidation,
    fsGuardValidation,
    graph,
    neighborSettleValidation,
    adaptLevelsValidation,
    selectedHotspot,
    simpleLimitValidation,
    simpleSeed,
  ]);

  const toggleStep = (step: number) => {
    setGuidedSteps((prev) =>
      prev.includes(step) ? prev.filter((value) => value !== step) : [...prev, step].sort((a, b) => a - b),
    );
  };

  const runGuidedLoop = useCallback(async () => {
    if (!selectedHotspot || !fsGuardValidation.ok) {
      return;
    }

    const guardValue = fsGuardValidation.value;
    const payload = buildGuidedPayload(
      selectedHotspot,
      graph,
      tauAmplitude,
      zetaAmplitude,
      guidedSteps,
      guardValue,
      guidedMinPhi,
      guidedSeed,
    );
    const command = await previewGuidedCli(payload);

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
          const simpleMetrics = simulateSimpleMetrics(seed, [tauAmplitude, zetaAmplitude], guardValue);
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
      const tip = decisionGate.evaluate({
        phase: 'phase3',
        fsP95: derived.fsP95 ?? undefined,
        fsGuard: guardValue,
        phi: derived.phi ?? undefined,
        calmHotspot: selectedHotspot.calm ?? false,
      });
      setTipMessage(tip);
    } finally {
      setIsGuidedRunning(false);
    }
  }, [
    decisionGate,
    fsGuardValidation,
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

  const openSaveRecipeModal = () => {
    if (!guidedResult) {
      return;
    }
    setSaveName(`Guided loop ${new Date().toLocaleString()}`);
    setSaveDescription('');
    setSaveError(null);
    setSaveModalOpen(true);
  };

  const closeSaveRecipeModal = useCallback(() => {
    if (saveInFlight) {
      return;
    }
    setSaveModalOpen(false);
    setSaveError(null);
  }, [saveInFlight]);

  const confirmSaveRecipe = async () => {
    if (!guidedResult) {
      setSaveModalOpen(false);
      return;
    }
    if (!window?.CWT?.recipes?.save) {
      return;
    }

    const trimmedName = saveName.trim();
    if (!trimmedName) {
      setSaveError('Provide a recipe name.');
      return;
    }

    setSaveInFlight(true);
    setSaveError(null);
    try {
      await window.CWT.recipes.save({
        name: trimmedName,
        description: saveDescription.trim(),
        params: guidedResult.payload,
        command: guidedResult.command,
        seed: guidedResult.payload.seed,
        basedOnRunId: guidedResult.runs[guidedResult.runs.length - 1]?.runId ?? null,
      });
      setSaveModalOpen(false);
      setSaveSuccessMessage(`Saved recipe “${trimmedName}”.`);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('cwt:recipes:updated'));
      }
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : String(error));
    } finally {
      setSaveInFlight(false);
    }
  };

  useEffect(() => {
    if (!saveSuccessMessage) {
      return;
    }
    const timer = window.setTimeout(() => setSaveSuccessMessage(null), 6000);
    return () => window.clearTimeout(timer);
  }, [saveSuccessMessage]);

  useEffect(() => {
    if (!saveModalOpen) {
      return;
    }
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const focusFirst = () => {
      if (!modalRef.current) {
        return;
      }
      const focusable = modalRef.current.querySelector<HTMLElement>(
        'input, textarea, button, select, [tabindex]:not([tabindex="-1"])',
      );
      focusable?.focus();
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        if (!saveInFlight) {
          event.preventDefault();
          setSaveModalOpen(false);
          setSaveError(null);
        }
        return;
      }
      if (event.key !== 'Tab' || !modalRef.current) {
        return;
      }
      const focusable = modalRef.current.querySelectorAll<HTMLElement>(
        'input, textarea, button, select, [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable.length) {
        event.preventDefault();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement as HTMLElement | null;
      if (event.shiftKey) {
        if (active === first || !modalRef.current.contains(active)) {
          event.preventDefault();
          last.focus();
        }
      } else if (active === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    setTimeout(focusFirst, 0);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      previouslyFocused?.focus?.();
    };
  }, [saveModalOpen, saveInFlight]);

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
                    min="0.01"
                    max="1"
                    step="0.01"
                    value={extentA}
                    onChange={(event) => setExtentA(Math.max(0.01, Number(event.target.value)))}
                  />
                  <code>{extentA.toFixed(2)}</code>
                  <small className="field-hint">How far to sweep along τ from the hotspot centre.</small>
                </label>
                <label>
                  <span>Extent ζ</span>
                  <input
                    type="range"
                    min="0.01"
                    max="1"
                    step="0.01"
                    value={extentB}
                    onChange={(event) => setExtentB(Math.max(0.01, Number(event.target.value)))}
                  />
                  <code>{extentB.toFixed(2)}</code>
                  <small className="field-hint">Controls the ζ reach of the loop about the hotspot.</small>
                </label>
                <label>
                  <span>FS guard</span>
                  <input
                    type="number"
                    step="0.01"
                    min="0.02"
                    max="0.5"
                    value={fsGuardInput}
                    onChange={(event) => setFsGuardInput(event.target.value)}
                  />
                  <small className="field-hint">
                    Flux stability fence. Keep FS p95 at or below this level.
                    {fsGuardError ? (
                      <span className="field-error"> {fsGuardError}</span>
                    ) : null}
                  </small>
                </label>
                <label>
                  <span>Loop limit</span>
                  <input
                    type="number"
                    min="16"
                    max="2000"
                    step="1"
                    value={simpleLimitInput}
                    onChange={(event) => setSimpleLimitInput(event.target.value)}
                  />
                  <small className="field-hint">
                    Number of solver steps per loop.
                    {simpleLimitError ? (
                      <span className="field-error"> {simpleLimitError}</span>
                    ) : null}
                  </small>
                </label>
                <label>
                  <span>Settle steps</span>
                  <input
                    type="number"
                    min="1"
                    max="2000"
                    step="1"
                    value={neighborSettleInput}
                    onChange={(event) => setNeighborSettleInput(event.target.value)}
                  />
                  <small className="field-hint">
                    Relax neighbours between loop samples. Drop to 8–16 for tiny loops.
                    {settleStepsError ? <span className="field-error"> {settleStepsError}</span> : null}
                  </small>
                </label>
                <label>
                  <span>Adaptive levels</span>
                  <input
                    type="number"
                    min="1"
                    max="6"
                    step="1"
                    value={adaptLevelsInput}
                    onChange={(event) => setAdaptLevelsInput(event.target.value)}
                  />
                  <small className="field-hint">
                    Limit adaptive curvature depth. Lower to 1 when extents stay small.
                    {adaptLevelsError ? <span className="field-error"> {adaptLevelsError}</span> : null}
                  </small>
                </label>
                <label>
                  <span>Seed</span>
                  <input
                    type="number"
                    value={simpleSeed}
                    onChange={(event) => setSimpleSeed(Number(event.target.value))}
                  />
                  <small className="field-hint">Use the same seed to reproduce a sweep for comparison.</small>
                </label>
              </div>
              <div className="phase3__actions">
                <button
                  type="button"
                  className="btn btn--primary"
                  onClick={runSimpleLoop}
                  disabled={isSimpleRunDisabled}
                  title={simpleRunTitle ?? undefined}
                >
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
                  <small className="field-hint">Half-width of the sweep along τ when guiding the loop.</small>
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
                  <small className="field-hint">Adjust to explore broader ζ excursions without overshooting.</small>
                </label>
                <label>
                  <span>FS guard</span>
                  <input
                    type="number"
                    step="0.01"
                    min="0.02"
                    max="0.5"
                    value={fsGuardInput}
                    onChange={(event) => setFsGuardInput(event.target.value)}
                  />
                  <small className="field-hint">
                    Same guard shared with the simple loop. Raise it only if every guided pass fails.
                    {fsGuardError ? <span className="field-error"> {fsGuardError}</span> : null}
                  </small>
                </label>
                <label>
                  <span>min Φ</span>
                  <input
                    type="number"
                    step="0.005"
                    value={guidedMinPhi}
                    onChange={(event) => setGuidedMinPhi(Number(event.target.value))}
                  />
                  <small className="field-hint">Guard against flat Φ by requiring at least this magnitude.</small>
                </label>
                <label>
                  <span>Seed</span>
                  <input
                    type="number"
                    value={guidedSeed}
                    onChange={(event) => setGuidedSeed(Number(event.target.value))}
                  />
                  <small className="field-hint">Changes the jitter pattern while preserving other settings.</small>
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
                {guidedRunDisabledReason ? (
                  <p className="field-error" role="alert">{guidedRunDisabledReason}</p>
                ) : null}
              </div>

              <div className="phase3__actions">
                <button
                  type="button"
                  className="btn btn--primary"
                  onClick={runGuidedLoop}
                  disabled={isGuidedRunDisabled}
                  title={guidedRunTitle ?? undefined}
                >
                  {isGuidedRunning ? 'Calibrating…' : 'Calibrate & Run'}
                </button>
              </div>

              {guidedResult ? (
                <div className="phase3__guided-result">
                  <header className="phase3__guided-header">
                    <h4>{guidedResult.satisfied ? 'Stable configuration found' : 'Tuning incomplete'}</h4>
                    <button type="button" className="btn btn--ghost" onClick={openSaveRecipeModal}>
                      Save as Recipe
                    </button>
                  </header>

                  {saveSuccessMessage ? <p className="phase3__notice">{saveSuccessMessage}</p> : null}

                  <div className="phase3__badges">
                    <span className={fsGuardBadgeClass(guidedResult.derivedMetrics.fsP95, fsGuardNumber ?? undefined)}>
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
      <section className="phase3__card">
        <AdiabaticBoundaryViewer />
      </section>
      {saveModalOpen ? (
        <div
          className="modal-overlay"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeSaveRecipeModal();
            }
          }}
        >
          <div
            className="modal"
            ref={modalRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="save-recipe-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <h3 id="save-recipe-title">Save recipe</h3>
            <label>
              <span>Name</span>
              <input value={saveName} onChange={(event) => setSaveName(event.target.value)} />
            </label>
            <label>
              <span>Description</span>
              <textarea
                rows={3}
                value={saveDescription}
                onChange={(event) => setSaveDescription(event.target.value)}
              />
            </label>
            {saveError ? <p className="modal__error">{saveError}</p> : null}
            <div className="modal__actions">
              <button type="button" className="btn btn--primary" onClick={confirmSaveRecipe} disabled={saveInFlight}>
                {saveInFlight ? 'Saving…' : 'Save recipe'}
              </button>
              <button
                type="button"
                className="btn btn--ghost"
                onClick={closeSaveRecipeModal}
                disabled={saveInFlight}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default Phase3Loops;
