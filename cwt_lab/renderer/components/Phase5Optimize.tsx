import { useCallback, useEffect, useMemo, useState } from 'react';

import type {
  GraphFamilyCommandPayload,
  GraphFamilyCommandResult,
  GraphFamilySummary,
  InverseDesignCommandPayload,
  InverseDesignCommandResult,
  NoiseRobustCommandResult,
  NoiseRobustGraph,
  NoiseRobustCommandPayload,
  CouplingTunerResult,
  CouplingVariantSummary,
  CouplingTunerPayload,
  BetaSweepRunRecord,
  RecipeRecord,
} from '../types/ipc';
import { useExperimentNavigation } from '../navigation/ExperimentNavigationContext';

type FamilyOption = {
  id: string;
  label: string;
  description: string;
};

type Phase5Tab = 'graph' | 'inverse' | 'noise' | 'tuner' | 'recipes';

type ValidationResult<T> = { payload: T | null; error: string | null };

const familyOptions: FamilyOption[] = [
  { id: 'ring', label: 'Ring', description: 'Directed ring with heterogeneous delays.' },
  { id: 'rr', label: 'Random regular', description: '3-regular digraph ensemble.' },
  { id: 'sw', label: 'Small-world', description: 'Watts–Strogatz perturbation of a ring lattice.' },
  { id: 'sf', label: 'Scale-free', description: 'Barabási–Albert style heavy-tailed hub distribution.' },
  { id: 'mod', label: 'Modular', description: 'Two-community digraph with dense intra-links.' },
];

const defaultAxes: [string, string] = ['tau', 'zeta'];

const tabs: Array<{ id: Phase5Tab; label: string }> = [
  { id: 'graph', label: 'Graph families' },
  { id: 'inverse', label: 'Inverse design' },
  { id: 'noise', label: 'Noise robustness' },
  { id: 'tuner', label: 'Coupling tuner' },
  { id: 'recipes', label: 'Recipes' },
];

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

const formatPercent = (value: number | null | undefined) => {
  if (value == null || Number.isNaN(value) || !Number.isFinite(value)) {
    return '—';
  }
  return `${(value * 100).toFixed(1)}%`;
};

const formatTimestamp = (value: string | null | undefined) => {
  if (!value) {
    return '—';
  }
  const time = Date.parse(value);
  if (Number.isNaN(time)) {
    return value;
  }
  return new Date(time).toLocaleString();
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

const copyToClipboard = async (value: string) => {
  try {
    await navigator.clipboard?.writeText(value);
  } catch {
    /* noop */
  }
};

const buildNoiseList = (value: number, includeZero = true) => {
  if (!Number.isFinite(value) || value <= 0) {
    return includeZero ? [0] : [];
  }
  const rounded = Number.parseFloat(value.toFixed(3));
  return includeZero ? [0, rounded] : [rounded];
};

const badgeClassForPersistence = (value: number | null | undefined) => {
  if (value == null || !Number.isFinite(value)) {
    return 'badge badge--warning';
  }
  if (value >= 0.9) {
    return 'badge badge--success';
  }
  if (value >= 0.75) {
    return 'badge badge--warning';
  }
  return 'badge badge--danger';
};

const statusBadgeClass = (status: string) => {
  switch (status) {
    case 'complete':
      return 'badge badge--success';
    case 'failed':
      return 'badge badge--danger';
    case 'aborted':
      return 'badge badge--warning';
    default:
      return 'badge badge--warning';
  }
};

const guardBadgeClass = (entry: CouplingVariantSummary) => {
  if (entry.guardExceeded || (entry.fsP95 != null && entry.fsBoundary != null && entry.fsP95 > entry.fsBoundary)) {
    return 'badge badge--danger';
  }
  return 'badge badge--success';
};

const asRecord = (value: unknown): Record<string, unknown> | null => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
};

const coerceBoolean = (value: unknown): boolean | null => {
  if (typeof value === 'boolean') {
    return value;
  }
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) {
      return null;
    }
    if (value > 0) {
      return true;
    }
    if (value === 0) {
      return false;
    }
  }
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase();
    if (!normalized) {
      return null;
    }
    if (['true', 'yes', 'ok', 'okay', 'pass', 'passed', 'compliant', 'satisfied', '1'].includes(normalized)) {
      return true;
    }
    if (['false', 'no', 'fail', 'failed', 'exceeded', 'violation', 'warn', 'warning', '0'].includes(normalized)) {
      return false;
    }
  }
  return null;
};

const coerceNumber = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number.parseFloat(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return null;
};

const pickFromSources = (
  sources: Array<Record<string, unknown> | null>,
  keys: string[],
): unknown => {
  for (const source of sources) {
    if (!source) {
      continue;
    }
    for (const key of keys) {
      if (key in source && source[key] != null) {
        return source[key];
      }
    }
  }
  return undefined;
};

const isRecipeGuardCompliant = (recipe: RecipeRecord): boolean => {
  const paramsRecord = asRecord(recipe.params);
  const metricsRecord = paramsRecord ? asRecord(paramsRecord['metrics']) : null;
  const derivedRecord = paramsRecord ? asRecord(paramsRecord['derivedMetrics']) : null;
  const metaRecord = paramsRecord ? asRecord(paramsRecord['meta']) : null;

  const sources = [paramsRecord, metricsRecord, derivedRecord, metaRecord];

  const guardExceededValue = pickFromSources(sources, [
    'guardExceeded',
    'guard_exceeded',
    'fsGuardExceeded',
    'fs_guard_exceeded',
    'guardBreached',
    'guard_breached',
  ]);
  const guardExceeded = coerceBoolean(guardExceededValue);
  if (guardExceeded === true) {
    return false;
  }

  const guardSatisfiedValue = pickFromSources(sources, [
    'guardSatisfied',
    'guard_satisfied',
    'fsGuardSatisfied',
    'fs_guard_satisfied',
    'guardOk',
    'guard_ok',
    'guardOK',
  ]);
  const guardSatisfied = coerceBoolean(guardSatisfiedValue);
  if (guardSatisfied != null) {
    return guardSatisfied;
  }

  if (guardExceeded === false) {
    return true;
  }

  const fractionValue = pickFromSources(sources, [
    'guardFraction',
    'guard_fraction',
    'fsGuardFraction',
    'fs_guard_fraction',
    'guardPercent',
    'guard_percent',
    'fsGuardRate',
    'fs_guard_rate',
  ]);
  const fraction = coerceNumber(fractionValue);
  if (fraction != null) {
    const boundaryValue = pickFromSources(sources, [
      'fsGuard',
      'fs_guard',
      'guardThreshold',
      'guard_threshold',
      'guardLimit',
      'guard_limit',
      'boundary',
      'fsBoundary',
      'fs_boundary',
      'threshold',
    ]);
    const boundary = coerceNumber(boundaryValue);
    if (boundary != null) {
      return fraction <= boundary;
    }
    return fraction <= 0.25;
  }

  return true;
};

const deriveBestRecipe = (recipes: RecipeRecord[]): RecipeRecord | null => {
  if (!recipes.length) {
    return null;
  }
  const guardCompliant = recipes.find((recipe) => isRecipeGuardCompliant(recipe));
  return guardCompliant ?? recipes[0] ?? null;
};

const Phase5Optimize = () => {
  const [activeTab, setActiveTab] = useState<Phase5Tab>('graph');

  const [selectedFamilies, setSelectedFamilies] = useState<Set<string>>(
    () => new Set(familyOptions.map((option) => option.id)),
  );
  const [axisA, setAxisA] = useState(defaultAxes[0]);
  const [axisB, setAxisB] = useState(defaultAxes[1]);
  const [gridSizeInput, setGridSizeInput] = useState('21');
  const [extentInput, setExtentInput] = useState('0.02');
  const [seedInput, setSeedInput] = useState('123');
  const [graphResult, setGraphResult] = useState<GraphFamilyCommandResult | null>(null);
  const [graphIsRunning, setGraphIsRunning] = useState(false);
  const [graphError, setGraphError] = useState<string | null>(null);

  const [invAxisA, setInvAxisA] = useState(defaultAxes[0]);
  const [invAxisB, setInvAxisB] = useState(defaultAxes[1]);
  const [invCenterTau, setInvCenterTau] = useState('0.24');
  const [invCenterZeta, setInvCenterZeta] = useState('0.0');
  const [invExtentTau, setInvExtentTau] = useState('0.05');
  const [invExtentZeta, setInvExtentZeta] = useState('0.04');
  const [invBudgetSteps, setInvBudgetSteps] = useState('200');
  const [invMaxFs, setInvMaxFs] = useState('0.1');
  const [invTargetIndex, setInvTargetIndex] = useState('0');
  const [invResult, setInvResult] = useState<InverseDesignCommandResult | null>(null);
  const [invRunning, setInvRunning] = useState(false);
  const [invError, setInvError] = useState<string | null>(null);

  const [noisePhase, setNoisePhase] = useState(0.1);
  const [noiseAmp, setNoiseAmp] = useState(0.2);
  const [noiseDelay, setNoiseDelay] = useState(0.1);
  const [noiseTrials, setNoiseTrials] = useState('6');
  const [noiseSteps, setNoiseSteps] = useState('200');
  const [noiseGrid, setNoiseGrid] = useState('8');
  const [noiseAxesA, setNoiseAxesA] = useState('rho');
  const [noiseAxesB, setNoiseAxesB] = useState('tau');
  const [noiseResult, setNoiseResult] = useState<NoiseRobustCommandResult | null>(null);
  const [noiseRunning, setNoiseRunning] = useState(false);
  const [noiseError, setNoiseError] = useState<string | null>(null);
  const [selectedNoiseGraph, setSelectedNoiseGraph] = useState<string>('');

  const [configPathInput, setConfigPathInput] = useState('cwt-sim/configs/loop_tau_zeta.yaml');
  const [betaInput, setBetaInput] = useState('0.8, 1.0, 1.2');
  const [etaInput, setEtaInput] = useState('');
  const [tunerResult, setTunerResult] = useState<CouplingTunerResult | null>(null);
  const [tunerRunning, setTunerRunning] = useState(false);
  const [tunerError, setTunerError] = useState<string | null>(null);
  const [betaSweepRuns, setBetaSweepRuns] = useState<BetaSweepRunRecord[]>([]);
  const [betaSweepDir, setBetaSweepDir] = useState<string | null>(null);
  const [betaSweepRunning, setBetaSweepRunning] = useState(false);
  const [betaSweepError, setBetaSweepError] = useState<string | null>(null);
  const [recipes, setRecipes] = useState<RecipeRecord[]>([]);
  const [recipesLoading, setRecipesLoading] = useState(false);
  const [recipesLoaded, setRecipesLoaded] = useState(false);
  const [recipesStale, setRecipesStale] = useState(true);
  const [recipesError, setRecipesError] = useState<string | null>(null);
  const [exportMessage, setExportMessage] = useState<
    | {
        tone: 'info' | 'success' | 'error';
        text: string;
      }
    | null
  >(null);
  const [bestRecipe, setBestRecipe] = useState<RecipeRecord | null>(null);
  const [exportingRecipeId, setExportingRecipeId] = useState<string | null>(null);

  const {
    artifactsRoot,
    experiments,
    experimentsError,
    experimentsLoading,
    selectedExperimentPath,
  } = useExperimentNavigation();

  const [graphPreview, setGraphPreview] = useState('');
  const [graphPreviewError, setGraphPreviewError] = useState<string | null>(null);
  const [invPreview, setInvPreview] = useState('');
  const [invPreviewError, setInvPreviewError] = useState<string | null>(null);
  const [noisePreview, setNoisePreview] = useState('');
  const [noisePreviewError, setNoisePreviewError] = useState<string | null>(null);
  const [tunerPreview, setTunerPreview] = useState<string[]>([]);
  const [tunerPreviewError, setTunerPreviewError] = useState<string | null>(null);

  const buildPreviewPath = useCallback(
    (category: string, leaf = '<preview>'): string | null => {
      const base = selectedExperimentPath
        ? selectedExperimentPath.replace(/[\\/]+$/, '')
        : artifactsRoot
        ? artifactsRoot.replace(/[\\/]+$/, '')
        : null;
      if (!base) {
        return null;
      }
      const trimmedCategory = category.replace(/^[\\/]+/, '').replace(/[\\/]+$/, '');
      const segments = [base];
      if (selectedExperimentPath) {
        segments.push('phase5');
      }
      if (trimmedCategory) {
        segments.push(trimmedCategory);
      }
      if (leaf) {
        segments.push(leaf);
      }
      return segments.filter(Boolean).join('/');
    },
    [artifactsRoot, selectedExperimentPath],
  );

  const buildGraphCommand = useCallback((): ValidationResult<GraphFamilyCommandPayload> => {
    const trimmedAxisA = axisA.trim();
    const trimmedAxisB = axisB.trim();
    if (!trimmedAxisA || !trimmedAxisB) {
      return { payload: null, error: 'Provide names for both loop axes.' };
    }
    if (trimmedAxisA.toLowerCase() === trimmedAxisB.toLowerCase()) {
      return { payload: null, error: 'Axes must be distinct.' };
    }

    const families = new Set(
      Array.from(selectedFamilies)
        .map((item) => item.trim())
        .filter((item): item is string => item.length > 0),
    );
    if (families.size === 0) {
      return { payload: null, error: 'Select at least one graph family.' };
    }

    const gridSize = Number.parseInt(gridSizeInput, 10);
    if (!Number.isFinite(gridSize) || gridSize <= 0) {
      return { payload: null, error: 'Grid size must be a positive integer.' };
    }

    const extent = Number.parseFloat(extentInput);
    if (!Number.isFinite(extent) || extent <= 0) {
      return { payload: null, error: 'Extent must be a positive number.' };
    }

    const seed = Number.parseInt(seedInput, 10);
    if (!Number.isFinite(seed)) {
      return { payload: null, error: 'Seed must be numeric.' };
    }

    return {
      payload: buildPayload(families, trimmedAxisA, trimmedAxisB, gridSize, extent, seed),
      error: null,
    };
  }, [axisA, axisB, extentInput, gridSizeInput, seedInput, selectedFamilies]);

  const buildInverseCommand = useCallback((): ValidationResult<InverseDesignCommandPayload> => {
    const axesA = invAxisA.trim();
    const axesB = invAxisB.trim();
    if (!axesA || !axesB) {
      return { payload: null, error: 'Provide names for both axes.' };
    }
    if (axesA.toLowerCase() === axesB.toLowerCase()) {
      return { payload: null, error: 'Axes must be distinct.' };
    }

    const centerTau = Number.parseFloat(invCenterTau);
    const centerZeta = Number.parseFloat(invCenterZeta);
    if (!Number.isFinite(centerTau) || !Number.isFinite(centerZeta)) {
      return { payload: null, error: 'Center coordinates must be numeric.' };
    }

    const extentTau = Number.parseFloat(invExtentTau);
    const extentZeta = Number.parseFloat(invExtentZeta);
    if (!Number.isFinite(extentTau) || !Number.isFinite(extentZeta)) {
      return { payload: null, error: 'Extents must be numeric.' };
    }

    const budget = Number.parseInt(invBudgetSteps, 10);
    if (!Number.isInteger(budget) || budget <= 0) {
      return { payload: null, error: 'Step budget must be a positive integer.' };
    }

    const maxFs = Number.parseFloat(invMaxFs);
    if (!Number.isFinite(maxFs) || maxFs <= 0) {
      return { payload: null, error: 'FS max must be a positive number.' };
    }

    const target = Number.parseInt(invTargetIndex, 10);
    if (!Number.isInteger(target) || target < 0) {
      return { payload: null, error: 'Target index must be a non-negative integer.' };
    }

    return {
      payload: {
        axes: [axesA, axesB],
        center: [centerTau, centerZeta],
        extentPair: [extentTau, extentZeta],
        budgetSteps: budget,
        maxFs,
        targetIndex: target,
      },
      error: null,
    };
  }, [invAxisA, invAxisB, invBudgetSteps, invCenterTau, invCenterZeta, invExtentTau, invExtentZeta, invMaxFs, invTargetIndex]);

  const buildNoiseCommand = useCallback((): ValidationResult<NoiseRobustCommandPayload> => {
    const trials = Number.parseInt(noiseTrials, 10);
    if (!Number.isInteger(trials) || trials <= 0) {
      return { payload: null, error: 'Trials must be a positive integer.' };
    }

    const steps = Number.parseInt(noiseSteps, 10);
    if (!Number.isInteger(steps) || steps <= 0) {
      return { payload: null, error: 'Loop steps must be a positive integer.' };
    }

    const gridSize = Number.parseInt(noiseGrid, 10);
    if (!Number.isInteger(gridSize) || gridSize <= 0) {
      return { payload: null, error: 'Grid size must be a positive integer.' };
    }

    const axesA = noiseAxesA.trim();
    const axesB = noiseAxesB.trim();
    if (!axesA || !axesB) {
      return { payload: null, error: 'Provide names for both axes.' };
    }

    return {
      payload: {
        phaseStd: buildNoiseList(noisePhase),
        ampStd: buildNoiseList(noiseAmp),
        delayStd: buildNoiseList(noiseDelay, false),
        numTrials: trials,
        loopSteps: steps,
        gridSize,
        axes: [axesA, axesB],
      },
      error: null,
    };
  }, [noiseAmp, noiseAxesA, noiseAxesB, noiseDelay, noiseGrid, noisePhase, noiseSteps, noiseTrials]);

  const buildTunerCommand = useCallback((): ValidationResult<CouplingTunerPayload> => {
    const trimmedPath = configPathInput.trim();
    if (!trimmedPath) {
      return { payload: null, error: 'Provide a baseline YAML path.' };
    }

    const betaValues = betaInput
      .split(',')
      .map((value) => Number.parseFloat(value.trim()))
      .filter((value) => Number.isFinite(value));
    if (betaValues.length === 0) {
      return { payload: null, error: 'Provide at least one β value (comma-separated).' };
    }

    const etaValues = etaInput
      .split(',')
      .map((value) => Number.parseFloat(value.trim()))
      .filter((value) => Number.isFinite(value));

    return {
      payload: {
        configPath: trimmedPath,
        betas: betaValues,
        etaQ: etaValues.length > 0 ? etaValues : undefined,
      },
      error: null,
    };
  }, [betaInput, configPathInput, etaInput]);

  const buildBetaSweepPayload = useCallback(
    (): ValidationResult<{ configPath: string; betas: number[] }> => {
      const trimmedPath = configPathInput.trim();
      if (!trimmedPath) {
        return { payload: null, error: 'Provide a baseline YAML path.' };
      }

      const betaValues = betaInput
        .split(',')
        .map((value) => Number.parseFloat(value.trim()))
        .filter((value) => Number.isFinite(value));
      if (betaValues.length === 0) {
        return { payload: null, error: 'Provide at least one β value (comma-separated).' };
      }

      return {
        payload: {
          configPath: trimmedPath,
          betas: betaValues,
        },
        error: null,
      };
    },
    [betaInput, configPathInput],
  );

  useEffect(() => {
    let cancelled = false;

    const updatePreview = async () => {
      if (typeof window === 'undefined' || !window?.CWT?.run?.preview) {
        setGraphPreview('');
        setGraphPreviewError('Command preview unavailable in this environment.');
        return;
      }

      const { payload, error } = buildGraphCommand();
      if (!payload) {
        setGraphPreview('');
        setGraphPreviewError(error);
        return;
      }

      const previewOutDir = buildPreviewPath('graph_family') ?? 'artifacts/graph_family/<preview>';
      const args: Record<string, unknown> = {
        families: payload.families.join(','),
        axes: payload.axes,
        gridSize: payload.gridSize,
        extents: payload.extents,
        seed: payload.seed,
        outDir: previewOutDir,
      };

      try {
        const response = await window.CWT.run.preview({
          experiment: 'experiments.graph_family.run',
          args,
        });
        if (cancelled) {
          return;
        }
        if (response.ok) {
          setGraphPreview(response.data.cli);
          setGraphPreviewError(null);
        } else {
          setGraphPreview('');
          setGraphPreviewError(response.error ?? 'Unable to preview command.');
        }
      } catch (previewError) {
        if (cancelled) {
          return;
        }
        setGraphPreview('');
        setGraphPreviewError(
          previewError instanceof Error ? previewError.message : String(previewError),
        );
      }
    };

    void updatePreview();

    return () => {
      cancelled = true;
    };
  }, [buildGraphCommand, buildPreviewPath]);

  useEffect(() => {
    let cancelled = false;

    const updatePreview = async () => {
      if (typeof window === 'undefined' || !window?.CWT?.run?.preview) {
        setInvPreview('');
        setInvPreviewError('Command preview unavailable in this environment.');
        return;
      }

      const { payload, error } = buildInverseCommand();
      if (!payload) {
        setInvPreview('');
        setInvPreviewError(error);
        return;
      }

      const args: Record<string, unknown> = {
        axes: payload.axes,
        center: payload.center,
        extent: payload.extentPair.map((value) => Math.abs(value)),
      };
      if (payload.budgetSteps != null) {
        args.budgetSteps = payload.budgetSteps;
      }
      if (payload.maxFs != null) {
        args.maxFs = payload.maxFs;
      }
      if (payload.targetIndex != null) {
        args.targetIndex = payload.targetIndex;
      }

      try {
        const response = await window.CWT.run.preview({
          experiment: 'experiments.inverse_design.run',
          args,
        });
        if (cancelled) {
          return;
        }
        if (response.ok) {
          setInvPreview(response.data.cli);
          setInvPreviewError(null);
        } else {
          setInvPreview('');
          setInvPreviewError(response.error ?? 'Unable to preview command.');
        }
      } catch (previewError) {
        if (cancelled) {
          return;
        }
        setInvPreview('');
        setInvPreviewError(
          previewError instanceof Error ? previewError.message : String(previewError),
        );
      }
    };

    void updatePreview();

    return () => {
      cancelled = true;
    };
  }, [buildInverseCommand]);

  useEffect(() => {
    let cancelled = false;

    const updatePreview = async () => {
      if (typeof window === 'undefined' || !window?.CWT?.run?.preview) {
        setNoisePreview('');
        setNoisePreviewError('Command preview unavailable in this environment.');
        return;
      }

      const { payload, error } = buildNoiseCommand();
      if (!payload) {
        setNoisePreview('');
        setNoisePreviewError(error);
        return;
      }

      const previewOutDir = buildPreviewPath('noise_robust') ?? 'artifacts/noise_robust/<preview>';
      const args: Record<string, unknown> = {
        phaseStd: payload.phaseStd,
        ampStd: payload.ampStd,
        delayStd: payload.delayStd,
        numTrials: payload.numTrials,
        loopSteps: payload.loopSteps,
        gridSize: payload.gridSize,
        axes: payload.axes,
        outputDir: previewOutDir,
      };

      try {
        const response = await window.CWT.run.preview({
          experiment: 'experiments.gateC_topology_robust.run',
          args,
        });
        if (cancelled) {
          return;
        }
        if (response.ok) {
          setNoisePreview(response.data.cli);
          setNoisePreviewError(null);
        } else {
          setNoisePreview('');
          setNoisePreviewError(response.error ?? 'Unable to preview command.');
        }
      } catch (previewError) {
        if (cancelled) {
          return;
        }
        setNoisePreview('');
        setNoisePreviewError(
          previewError instanceof Error ? previewError.message : String(previewError),
        );
      }
    };

    void updatePreview();

    return () => {
      cancelled = true;
    };
  }, [buildNoiseCommand, buildPreviewPath]);

  useEffect(() => {
    let cancelled = false;

    const updatePreview = async () => {
      if (typeof window === 'undefined' || !window?.CWT?.run?.preview) {
        setTunerPreview([]);
        setTunerPreviewError('Command preview unavailable in this environment.');
        return;
      }

      const { payload, error } = buildTunerCommand();
      if (!payload) {
        setTunerPreview([]);
        setTunerPreviewError(error);
        return;
      }

      const previewOutDir = buildPreviewPath('coupling_tuner') ?? 'artifacts/coupling_tuner/<preview>';
      const ensureDir = (value: string) => value.replace(/[\\/]+$/, '');
      const joinPath = (base: string, segment: string) => `${ensureDir(base)}/${segment.replace(/^[\\/]+/, '')}`;
      const resolveEta = (value: number | number[] | undefined, index: number): number | null => {
        if (value == null) {
          return null;
        }
        if (Array.isArray(value)) {
          if (value.length === 0) {
            return null;
          }
          const candidate = value[Math.min(index, value.length - 1)];
          return Number.isFinite(candidate) ? Number(candidate) : null;
        }
        return Number.isFinite(value) ? Number(value) : null;
      };

      const previews: string[] = [];
      try {
        for (let index = 0; index < payload.betas.length; index += 1) {
          const beta = payload.betas[index];
          const etaValue = resolveEta(payload.etaQ, index);
          const variantName = `beta_${beta.toFixed(3)}${
            etaValue != null ? `_eta_${etaValue.toFixed(3)}` : ''
          }`;
          const args: Record<string, unknown> = {
            config: joinPath(previewOutDir, `${variantName}.yaml`),
            out: ensureDir(previewOutDir),
          };
          const response = await window.CWT.run.preview({
            experiment: 'scripts.run_loop',
            args,
          });
          if (!response.ok) {
            throw new Error(response.error ?? `Unable to preview command for β=${beta}`);
          }
          previews.push(response.data.cli);
        }
        if (cancelled) {
          return;
        }
        setTunerPreview(previews);
        setTunerPreviewError(null);
      } catch (previewError) {
        if (cancelled) {
          return;
        }
        setTunerPreview([]);
        setTunerPreviewError(
          previewError instanceof Error ? previewError.message : String(previewError),
        );
      }
    };

    void updatePreview();

    return () => {
      cancelled = true;
    };
  }, [buildPreviewPath, buildTunerCommand]);

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
    if (!graphResult) {
      return [];
    }
    const entries = [...graphResult.families];
    entries.sort((a, b) => {
      if (a.phiGuardOk !== b.phiGuardOk) {
        return a.phiGuardOk ? -1 : 1;
      }
      const aPhi = a.phiFlux ?? Number.NEGATIVE_INFINITY;
      const bPhi = b.phiFlux ?? Number.NEGATIVE_INFINITY;
      return Number(bPhi) - Number(aPhi);
    });
    return entries;
  }, [graphResult]);

  const activeNoiseGraph: NoiseRobustGraph | null = useMemo(() => {
    if (!noiseResult || !noiseResult.graphs.length) {
      return null;
    }
    if (!selectedNoiseGraph) {
      return noiseResult.graphs[0];
    }
    return noiseResult.graphs.find((graph) => graph.name === selectedNoiseGraph) ?? noiseResult.graphs[0];
  }, [noiseResult, selectedNoiseGraph]);

  const bestVariantIndex = tunerResult?.bestIndex ?? null;

  const loadRecipes = useCallback(async () => {
    if (!window?.CWT?.recipes?.list) {
      setRecipesError('Recipe listing is unavailable in this build.');
      setRecipes([]);
      setRecipesLoaded(true);
      setRecipesStale(false);
      return;
    }

    setRecipesLoading(true);
    setRecipesError(null);
    try {
      const response = await window.CWT.recipes.list();
      if (!response.ok) {
        throw new Error(response.error ?? 'Failed to load recipes');
      }
      const entries = Array.isArray(response.data) ? response.data : [];
      setRecipes(entries);
    } catch (error) {
      setRecipesError(error instanceof Error ? error.message : String(error));
    } finally {
      setRecipesLoading(false);
      setRecipesLoaded(true);
      setRecipesStale(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab !== 'recipes') {
      return;
    }
    if (!recipesLoaded || recipesStale) {
      void loadRecipes();
    }
  }, [activeTab, recipesLoaded, recipesStale, loadRecipes]);

  useEffect(() => {
    const handleRecipesUpdated = () => setRecipesStale(true);
    window.addEventListener('cwt:recipes:updated', handleRecipesUpdated);
    return () => {
      window.removeEventListener('cwt:recipes:updated', handleRecipesUpdated);
    };
  }, []);

  useEffect(() => {
    if (!exportMessage) {
      return;
    }
    const timer = window.setTimeout(() => setExportMessage(null), 6000);
    return () => window.clearTimeout(timer);
  }, [exportMessage]);

  const sortedRecipes = useMemo(() => {
    if (!recipes.length) {
      return [];
    }
    const entries = [...recipes];
    entries.sort((a, b) => {
      const aTime = Date.parse(a.createdAt ?? '');
      const bTime = Date.parse(b.createdAt ?? '');
      if (Number.isNaN(aTime) && Number.isNaN(bTime)) {
        return a.name.localeCompare(b.name);
      }
      if (Number.isNaN(aTime)) {
        return 1;
      }
      if (Number.isNaN(bTime)) {
        return -1;
      }
      return bTime - aTime;
    });
    return entries;
  }, [recipes]);

  useEffect(() => {
    setBestRecipe(deriveBestRecipe(sortedRecipes));
  }, [sortedRecipes]);

  const bestRecipeId = bestRecipe?.id ?? null;

  const runGraphAnalysis = async () => {
    if (!window?.CWT?.phase5?.cmdGraphFamily) {
      setGraphError('Graph family command is unavailable in this build.');
      return;
    }

    const { payload, error } = buildGraphCommand();
    if (!payload) {
      setGraphError(error ?? 'Provide valid graph parameters.');
      return;
    }

    if (!selectedExperimentPath) {
      setGraphError('Select an experiment before running graph analysis.');
      return;
    }

    setGraphIsRunning(true);
    setGraphError(null);
    setGraphResult(null);

    try {
      const response = await window.CWT.phase5.cmdGraphFamily({
        ...payload,
        experimentDir: selectedExperimentPath,
      });
      if (!response.ok) {
        throw new Error(response.error ?? 'Graph family analysis failed');
      }
      setGraphResult(response.data);
    } catch (analysisError) {
      setGraphError(analysisError instanceof Error ? analysisError.message : String(analysisError));
    } finally {
      setGraphIsRunning(false);
    }
  };

  const runInverseDesign = async () => {
    if (!window?.CWT?.phase5?.cmdInverseDesign) {
      setInvError('Inverse-design command is unavailable.');
      return;
    }

    const { payload, error } = buildInverseCommand();
    if (!payload) {
      setInvError(error ?? 'Provide valid inverse-design parameters.');
      return;
    }

    if (!selectedExperimentPath) {
      setInvError('Select an experiment before running inverse design.');
      return;
    }

    setInvRunning(true);
    setInvError(null);
    setInvResult(null);

    try {
      const response = await window.CWT.phase5.cmdInverseDesign({
        ...payload,
        experimentDir: selectedExperimentPath,
      });
      if (!response.ok) {
        throw new Error(response.error ?? 'Inverse design failed');
      }
      setInvResult(response.data);
    } catch (error) {
      setInvError(error instanceof Error ? error.message : String(error));
    } finally {
      setInvRunning(false);
    }
  };

  const runNoiseSweep = async () => {
    if (!window?.CWT?.phase5?.cmdNoiseRobust) {
      setNoiseError('Noise robustness command is unavailable.');
      return;
    }

    const { payload, error } = buildNoiseCommand();
    if (!payload) {
      setNoiseError(error ?? 'Provide valid noise robustness parameters.');
      return;
    }

    if (!selectedExperimentPath) {
      setNoiseError('Select an experiment before running the noise sweep.');
      return;
    }

    setNoiseRunning(true);
    setNoiseError(null);
    setNoiseResult(null);

    try {
      const response = await window.CWT.phase5.cmdNoiseRobust({
        ...payload,
        experimentDir: selectedExperimentPath,
      });
      if (!response.ok) {
        throw new Error(response.error ?? 'Noise sweep failed');
      }
      setNoiseResult(response.data);
      if (response.data.graphs.length > 0) {
        setSelectedNoiseGraph(response.data.graphs[0].name);
      }
    } catch (error) {
      setNoiseError(error instanceof Error ? error.message : String(error));
    } finally {
      setNoiseRunning(false);
    }
  };

  const runBetaSweep = async () => {
    if (!window?.CWT?.phase5?.betaSweep) {
      setBetaSweepError('β sweep command is unavailable.');
      return;
    }

    const { payload, error } = buildBetaSweepPayload();
    if (!payload) {
      setBetaSweepError(error ?? 'Provide valid β sweep parameters.');
      return;
    }

    if (!selectedExperimentPath) {
      setBetaSweepError('Select an experiment before launching the β sweep.');
      return;
    }

    setBetaSweepRunning(true);
    setBetaSweepError(null);
    setBetaSweepRuns([]);
    setBetaSweepDir(null);

    try {
      const response = await window.CWT.phase5.betaSweep({
        ...payload,
        experimentDir: selectedExperimentPath,
      });
      if (!response.ok) {
        throw new Error(response.error ?? 'β sweep failed');
      }
      setBetaSweepRuns(Array.isArray(response.data.runs) ? response.data.runs : []);
      setBetaSweepDir(response.data.stagingDir ?? response.data.tempDir ?? null);
    } catch (error) {
      setBetaSweepError(error instanceof Error ? error.message : String(error));
    } finally {
      setBetaSweepRunning(false);
    }
  };

  const runCouplingTuner = async () => {
    if (!window?.CWT?.phase5?.couplingTuner) {
      setTunerError('Coupling tuner command is unavailable.');
      return;
    }

    const { payload, error } = buildTunerCommand();
    if (!payload) {
      setTunerError(error ?? 'Provide valid coupling tuner parameters.');
      return;
    }

    if (!selectedExperimentPath) {
      setTunerError('Select an experiment before running the coupling tuner.');
      return;
    }

    setTunerRunning(true);
    setTunerError(null);
    setTunerResult(null);

    try {
      const response = await window.CWT.phase5.couplingTuner({
        ...payload,
        experimentDir: selectedExperimentPath,
      });
      if (!response.ok) {
        throw new Error(response.error ?? 'Coupling tuner failed');
      }
      setTunerResult(response.data);
    } catch (error) {
      setTunerError(error instanceof Error ? error.message : String(error));
    } finally {
      setTunerRunning(false);
    }
  };

  const handleRunRecipe = async (id: string) => {
    if (!window?.CWT?.recipes?.run) {
      setExportMessage({ tone: 'error', text: 'Recipe run is unavailable in this build.' });
      return;
    }
    if (!selectedExperimentPath) {
      setExportMessage({ tone: 'error', text: 'Select an experiment before running a recipe.' });
      return;
    }
    try {
      await window.CWT.recipes.run({ id, experimentDir: selectedExperimentPath });
      setExportMessage({ tone: 'success', text: `Run launched for recipe ${id}.` });
    } catch (error) {
      setExportMessage({
        tone: 'error',
        text: error instanceof Error ? error.message : String(error),
      });
    }
  };

  const handleExportRecipe = async (id: string) => {
    if (exportingRecipeId) {
      return;
    }
    if (!window?.CWT?.recipes?.export) {
      setExportMessage({ tone: 'error', text: 'Recipe export is unavailable in this build.' });
      return;
    }
    setExportingRecipeId(id);
    setExportMessage({ tone: 'info', text: 'Exporting…' });
    try {
      const response = await window.CWT.recipes.export({ id });
      if (!response.ok) {
        throw new Error(response.error ?? 'Recipe export failed');
      }
      const zipPath = response.data?.zipPath ?? 'unknown';
      setExportMessage({ tone: 'success', text: `Exported to ${zipPath}` });
      if (zipPath && zipPath !== 'unknown') {
        void copyToClipboard(zipPath);
      }
    } catch (error) {
      setExportMessage({
        tone: 'error',
        text: error instanceof Error ? error.message : String(error),
      });
    }
    setExportingRecipeId(null);
  };

  const handleExportBestRecipe = () => {
    if (!bestRecipeId) {
      setExportMessage({ tone: 'info', text: 'No guard-compliant recipe available yet.' });
      return;
    }
    void handleExportRecipe(bestRecipeId);
  };

  const renderRecipesTab = () => {
    const messageClass = exportMessage ? `phase5__message phase5__message--${exportMessage.tone}` : '';
    return (
      <div className="phase5__recipes">
        <header className="phase5__recipes-header">
          <div>
            <h3>Saved recipes</h3>
            <p>Replay calibrated protocols or export a research pack for sharing.</p>
          </div>
          <div className="phase5__recipes-actions">
            <button
              type="button"
              className="btn btn--primary"
              onClick={handleExportBestRecipe}
              disabled={!bestRecipe || Boolean(exportingRecipeId)}
            >
              {bestRecipe && exportingRecipeId === bestRecipe.id ? 'Exporting…' : 'Export Best Recipe'}
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => {
                setRecipesStale(true);
                void loadRecipes();
              }}
              disabled={recipesLoading || Boolean(exportingRecipeId)}
            >
              {recipesLoading ? 'Refreshing…' : 'Refresh'}
            </button>
          </div>
        </header>

        <div className="phase5__experiment-notice">
          {experimentsLoading ? (
            <small className="field-hint">Loading experiments…</small>
          ) : experimentsError ? (
            <small className="field-error">{experimentsError}</small>
          ) : experiments.length === 0 ? (
            <small className="field-hint">Run Phase 1 to populate experiment folders.</small>
          ) : selectedExperimentPath ? (
            <small className="field-hint">
              Results will be stored in <code>{selectedExperimentPath}</code>.
            </small>
          ) : (
            <small className="field-hint">
              Choose an experiment from the navigation pane to store Phase 5 outputs.
            </small>
          )}
        </div>

        {exportMessage ? <p className={messageClass}>{exportMessage.text}</p> : null}
        {recipesError ? <p className="phase5__error">{recipesError}</p> : null}

        {recipesLoading && !recipesLoaded ? (
          <p className="phase5__placeholder">Loading recipes…</p>
        ) : sortedRecipes.length ? (
          <table className="phase5__table phase5__recipes-table">
            <thead>
              <tr>
                <th scope="col">Recipe</th>
                <th scope="col">Created</th>
                <th scope="col">Command</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedRecipes.map((recipe) => (
                <tr key={recipe.id} className={bestRecipeId === recipe.id ? 'phase5__recipes-best' : undefined}>
                  <td>
                    <div className="phase5__recipe-meta">
                      <strong>{recipe.name}</strong>
                      {recipe.description ? <p>{recipe.description}</p> : null}
                    </div>
                  </td>
                  <td>{formatTimestamp(recipe.createdAt)}</td>
                  <td>
                    <code className="phase5__code-snippet">{recipe.command}</code>
                    <button
                      type="button"
                      className="link-button"
                      onClick={() => copyToClipboard(recipe.command)}
                    >
                      Copy
                    </button>
                  </td>
                  <td>
                    <div className="phase5__recipe-actions">
                      <button
                        type="button"
                        className="btn btn--primary"
                        onClick={() => handleRunRecipe(recipe.id)}
                        disabled={!selectedExperimentPath}
                        title={
                          !selectedExperimentPath
                            ? 'Select an experiment to store recipe outputs.'
                            : undefined
                        }
                      >
                        Run
                      </button>
                      <button
                        type="button"
                        className="btn btn--ghost"
                        onClick={() => handleExportRecipe(recipe.id)}
                        disabled={Boolean(exportingRecipeId)}
                      >
                        {exportingRecipeId === recipe.id ? 'Exporting…' : 'Export'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : recipesLoaded ? (
          <p className="phase5__placeholder">No recipes saved yet. Save one from a guided loop run to begin.</p>
        ) : null}
      </div>
    );
  };

  const renderGraphTab = () => (
    <div className="phase5__layout">
      <section className="phase5__controls">
        <h3>Topology sweep</h3>
        <p>Select candidate ensembles and sampling parameters, then launch an in-process sweep.</p>

        <div className="phase5__families">
          {familyOptions.map((family) => {
            const checked = selectedFamilies.has(family.id);
            return (
              <label key={family.id} className="phase5__family-option">
                <input type="checkbox" checked={checked} onChange={() => toggleFamily(family.id)} />
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
            <input value={gridSizeInput} onChange={(event) => setGridSizeInput(event.target.value)} />
          </label>
          <label>
            Extent
            <input value={extentInput} onChange={(event) => setExtentInput(event.target.value)} />
          </label>
          <label>
            Seed
            <input value={seedInput} onChange={(event) => setSeedInput(event.target.value)} />
          </label>
        </div>

        <div className="phase5__preview">
          <h4>Command preview</h4>
          <pre className="phase5__preview-code">{graphPreview || 'Preview unavailable'}</pre>
          {graphPreviewError ? <p className="phase5__error">{graphPreviewError}</p> : null}
          <div className="phase5__preview-actions">
            <button
              type="button"
              className="btn btn--ghost btn--small"
              disabled={!graphPreview}
              onClick={() => copyToClipboard(graphPreview)}
            >
              Copy command
            </button>
          </div>
        </div>

        <button
          className="phase5__run"
          onClick={runGraphAnalysis}
          disabled={graphIsRunning || !selectedExperimentPath}
        >
          {graphIsRunning ? 'Running…' : 'Run topology sweep'}
        </button>

        {graphError ? <p className="phase5__error">{graphError}</p> : null}
      </section>

      <section className="phase5__results">
        <div className="phase5__results-header">
          <h3>Leaderboard</h3>
          {graphResult ? (
            <div className="phase5__run-meta">
              <span>
                Axes:&nbsp;
                <code>
                  {graphResult.axes[0]} × {graphResult.axes[1]}
                </code>
              </span>
              <span>
                Grid:&nbsp;
                <code>{graphResult.gridSize}</code> pts, extent <code>{formatFloat(graphResult.extent)}</code>
              </span>
              <span>
                Seed:&nbsp;<code>{graphResult.seed}</code>
              </span>
              {graphResult.runtimeSeconds != null ? (
                <span>
                  Runtime:&nbsp;
                  <code>{formatFloat(graphResult.runtimeSeconds, 2)} s</code>
                </span>
              ) : null}
              {graphResult.cli ? (
                <span className="phase5__cli">
                  CLI:&nbsp;
                  <code className="phase5__code-snippet">{graphResult.cli}</code>
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
                    <span className={phiBadgeClass}>Φ {family.phiGuardOk ? '' : '(warn)'} {phiValue}</span>
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

        {graphResult ? (
          <details className="phase5__logs">
            <summary>Execution log</summary>
            <pre>{graphResult.stdout.trim() || '(no stdout)'}</pre>
            {graphResult.stderr.trim() ? <pre className="phase5__stderr">{graphResult.stderr}</pre> : null}
            <p>
              Artifacts:&nbsp;
              <code>{graphResult.outputDir}</code>{' '}
              <button type="button" className="link-button" onClick={() => copyToClipboard(graphResult.outputDir)}>
                Copy path
              </button>
            </p>
          </details>
        ) : null}
      </section>
    </div>
  );

  const renderInverseTab = () => (
    <div className="phase5__sectioned">
      <section className="phase5__controls">
        <h3>Inverse design runner</h3>
        <p>Optimise a control polygon for improved Φ without violating the FS guard.</p>

        <div className="phase5__input-grid phase5__input-grid--compact">
          <label>
            Axis 1
            <input value={invAxisA} onChange={(event) => setInvAxisA(event.target.value)} />
          </label>
          <label>
            Axis 2
            <input value={invAxisB} onChange={(event) => setInvAxisB(event.target.value)} />
          </label>
          <label>
            τ center
            <input value={invCenterTau} onChange={(event) => setInvCenterTau(event.target.value)} />
          </label>
          <label>
            ζ center
            <input value={invCenterZeta} onChange={(event) => setInvCenterZeta(event.target.value)} />
          </label>
          <label>
            τ extent
            <input value={invExtentTau} onChange={(event) => setInvExtentTau(event.target.value)} />
          </label>
          <label>
            ζ extent
            <input value={invExtentZeta} onChange={(event) => setInvExtentZeta(event.target.value)} />
          </label>
          <label>
            Step budget
            <input value={invBudgetSteps} onChange={(event) => setInvBudgetSteps(event.target.value)} />
          </label>
          <label>
            FS guard
            <input value={invMaxFs} onChange={(event) => setInvMaxFs(event.target.value)} />
          </label>
          <label>
            Target index
            <input value={invTargetIndex} onChange={(event) => setInvTargetIndex(event.target.value)} />
          </label>
        </div>

        <div className="phase5__preview">
          <h4>Command preview</h4>
          <pre className="phase5__preview-code">{invPreview || 'Preview unavailable'}</pre>
          {invPreviewError ? <p className="phase5__error">{invPreviewError}</p> : null}
          <div className="phase5__preview-actions">
            <button
              type="button"
              className="btn btn--ghost btn--small"
              disabled={!invPreview}
              onClick={() => copyToClipboard(invPreview)}
            >
              Copy command
            </button>
          </div>
        </div>

        <button
          className="phase5__run"
          onClick={runInverseDesign}
          disabled={invRunning || !selectedExperimentPath}
        >
          {invRunning ? 'Running…' : 'Run inverse design'}
        </button>

        {invError ? <p className="phase5__error">{invError}</p> : null}
      </section>

      <section className="phase5__inverse-results">
        {invResult ? (
          <>
            <header className="phase5__inverse-header">
              <h3>Before / After comparison</h3>
              {invResult.acceptance ? <span>{invResult.acceptance}</span> : null}
            </header>
            {invResult.cli ? (
              <p className="phase5__command">
                CLI:&nbsp;<code className="phase5__code-snippet">{invResult.cli}</code>
              </p>
            ) : null}
            <div className="phase5__inverse-grid">
              <article className="phase5__inverse-card">
                <h4>Baseline rectangle</h4>
                <dl>
                  <div>
                    <dt>|Φ|</dt>
                    <dd>{formatFloat(invResult.baseline?.magnitude, 6)}</dd>
                  </div>
                  <div>
                    <dt>Guard fraction</dt>
                    <dd>{formatFloat(invResult.baseline?.guardFraction, 3)}</dd>
                  </div>
                  <div>
                    <dt>Loop length</dt>
                    <dd>{formatFloat(invResult.baseline?.length, 4)}</dd>
                  </div>
                  <div>
                    <dt>Curvature tiles</dt>
                    <dd>{invResult.baseline?.phiMissing ? 'missing' : 'complete'}</dd>
                  </div>
                </dl>
              </article>
              <article className="phase5__inverse-card">
                <h4>Optimised polygon</h4>
                <dl>
                  <div>
                    <dt>|Φ|</dt>
                    <dd>{formatFloat(invResult.optimised?.magnitude, 6)}</dd>
                  </div>
                  <div>
                    <dt>Guard fraction</dt>
                    <dd>{formatFloat(invResult.optimised?.guardFraction, 3)}</dd>
                  </div>
                  <div>
                    <dt>Loop length</dt>
                    <dd>{formatFloat(invResult.optimised?.length, 4)}</dd>
                  </div>
                  <div>
                    <dt>Improvement</dt>
                    <dd>{invResult.optimised?.improvement ? `${formatFloat(invResult.optimised?.improvement, 3)}×` : '—'}</dd>
                  </div>
                </dl>
                {invResult.optimised?.controlPoints.length ? (
                  <table className="phase5__inverse-table">
                    <thead>
                      <tr>
                        <th>Vertex</th>
                        <th>Δ{invAxisA}</th>
                        <th>Δ{invAxisB}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {invResult.optimised.controlPoints.map((point) => (
                        <tr key={point.index}>
                          <td>v{point.index}</td>
                          <td>{formatFloat(point.axisA, 4)}</td>
                          <td>{formatFloat(point.axisB, 4)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : null}
              </article>
            </div>
            <details className="phase5__logs">
              <summary>Execution log</summary>
              <pre>{invResult.stdout.trim() || '(no stdout)'}</pre>
              {invResult.stderr.trim() ? <pre className="phase5__stderr">{invResult.stderr}</pre> : null}
              <p>
                Artifacts:&nbsp;
                <code>{invResult.outputDir}</code>{' '}
                <button type="button" className="link-button" onClick={() => copyToClipboard(invResult.outputDir)}>
                  Copy path
                </button>
              </p>
            </details>
          </>
        ) : (
          <p className="phase5__placeholder">Configure parameters and run the inverse-design routine.</p>
        )}
      </section>
    </div>
  );

  const renderNoiseTab = () => (
    <div className="phase5__sectioned">
      <section className="phase5__controls">
        <h3>Noise robustness</h3>
        <p>Probe loop stability under stochastic phase, amplitude and delay perturbations.</p>

        <div className="phase5__slider-group">
          <label>
            Phase σ
            <input
              type="range"
              min={0}
              max={0.3}
              step={0.01}
              value={noisePhase}
              onChange={(event) => setNoisePhase(Number(event.target.value))}
            />
            <span>{noisePhase.toFixed(2)}</span>
          </label>
          <label>
            Amplitude σ
            <input
              type="range"
              min={0}
              max={0.3}
              step={0.01}
              value={noiseAmp}
              onChange={(event) => setNoiseAmp(Number(event.target.value))}
            />
            <span>{noiseAmp.toFixed(2)}</span>
          </label>
          <label>
            Delay σ
            <input
              type="range"
              min={0}
              max={0.3}
              step={0.01}
              value={noiseDelay}
              onChange={(event) => setNoiseDelay(Number(event.target.value))}
            />
            <span>{noiseDelay.toFixed(2)}</span>
          </label>
        </div>

        <div className="phase5__input-grid phase5__input-grid--compact">
          <label>
            Trials
            <input value={noiseTrials} onChange={(event) => setNoiseTrials(event.target.value)} />
          </label>
          <label>
            Loop steps
            <input value={noiseSteps} onChange={(event) => setNoiseSteps(event.target.value)} />
          </label>
          <label>
            Grid size
            <input value={noiseGrid} onChange={(event) => setNoiseGrid(event.target.value)} />
          </label>
          <label>
            Axis 1
            <input value={noiseAxesA} onChange={(event) => setNoiseAxesA(event.target.value)} />
          </label>
          <label>
            Axis 2
            <input value={noiseAxesB} onChange={(event) => setNoiseAxesB(event.target.value)} />
          </label>
        </div>

        <div className="phase5__preview">
          <h4>Command preview</h4>
          <pre className="phase5__preview-code">{noisePreview || 'Preview unavailable'}</pre>
          {noisePreviewError ? <p className="phase5__error">{noisePreviewError}</p> : null}
          <div className="phase5__preview-actions">
            <button
              type="button"
              className="btn btn--ghost btn--small"
              disabled={!noisePreview}
              onClick={() => copyToClipboard(noisePreview)}
            >
              Copy command
            </button>
          </div>
        </div>

        <button
          className="phase5__run"
          onClick={runNoiseSweep}
          disabled={noiseRunning || !selectedExperimentPath}
        >
          {noiseRunning ? 'Running…' : 'Run noise sweep'}
        </button>

        {noiseError ? <p className="phase5__error">{noiseError}</p> : null}
      </section>

      <section className="phase5__noise-results">
        {noiseResult ? (
          <>
            <header className="phase5__noise-header">
              <div>
                <label>
                  Graph
                  <select
                    value={activeNoiseGraph?.name ?? ''}
                    onChange={(event) => setSelectedNoiseGraph(event.target.value)}
                  >
                    {noiseResult.graphs.map((graph) => (
                      <option key={graph.name} value={graph.name}>
                        {graph.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="phase5__noise-meta">
                <span>Trials: {noiseResult.numTrials ?? '—'}</span>
                <span>Loop steps: {noiseResult.loopSteps ?? '—'}</span>
              </div>
            </header>
            {noiseResult.cli ? (
              <p className="phase5__command">
                CLI:&nbsp;<code className="phase5__code-snippet">{noiseResult.cli}</code>
              </p>
            ) : null}
            {activeNoiseGraph ? (
              <table className="phase5__table">
                <thead>
                  <tr>
                    <th>Phase σ</th>
                    <th>Amp σ</th>
                    <th>Delay σ</th>
                    <th>Sign persistence</th>
                    <th>Mean overlap</th>
                    <th>FS p95</th>
                    <th>FS max</th>
                  </tr>
                </thead>
                <tbody>
                  {activeNoiseGraph.points.map((point) => (
                    <tr key={`${point.phaseStd}-${point.ampStd}-${point.delayStd}`}>
                      <td>{formatFloat(point.phaseStd, 3)}</td>
                      <td>{formatFloat(point.ampStd, 3)}</td>
                      <td>{formatFloat(point.delayStd, 3)}</td>
                      <td>
                        <span className={badgeClassForPersistence(point.signPersistence)}>
                          {formatPercent(point.signPersistence)}
                        </span>
                      </td>
                      <td>{formatFloat(point.overlapMean, 3)}</td>
                      <td>{formatFloat(point.fsP95, 3)}</td>
                      <td>{formatFloat(point.fsMax, 3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : null}
            <details className="phase5__logs">
              <summary>Artifacts</summary>
              <p>
                Report:&nbsp;
                <code>{noiseResult.reportPath ?? 'n/a'}</code>
              </p>
              <p>
                Output directory:&nbsp;
                <code>{noiseResult.outputDir}</code>{' '}
                <button type="button" className="link-button" onClick={() => copyToClipboard(noiseResult.outputDir)}>
                  Copy path
                </button>
              </p>
            </details>
          </>
        ) : (
          <p className="phase5__placeholder">Select noise parameters and launch the robustness sweep.</p>
        )}
      </section>
    </div>
  );

  const renderTunerTab = () => (
    <div className="phase5__sectioned">
      <section className="phase5__controls">
        <h3>Coupling tuner (β, ηq)</h3>
        <p>Generate YAML variants, evaluate Φ/R/FS metrics, and highlight the best guard-compliant loop.</p>

        <div className="phase5__input-grid phase5__input-grid--compact">
          <label className="phase5__input-wide">
            Baseline YAML
            <input value={configPathInput} onChange={(event) => setConfigPathInput(event.target.value)} />
          </label>
          <label className="phase5__input-wide">
            β values
            <input
              value={betaInput}
              onChange={(event) => setBetaInput(event.target.value)}
              placeholder="Comma-separated"
            />
          </label>
          <label className="phase5__input-wide">
            ηq overrides (optional)
            <input
              value={etaInput}
              onChange={(event) => setEtaInput(event.target.value)}
              placeholder="Comma-separated"
            />
          </label>
        </div>

        <div className="phase5__preview">
          <h4>Command preview</h4>
          {tunerPreview.length > 0 ? (
            <pre className="phase5__preview-code">{tunerPreview.join('\n')}</pre>
          ) : (
            <pre className="phase5__preview-code">Preview unavailable</pre>
          )}
          {tunerPreviewError ? <p className="phase5__error">{tunerPreviewError}</p> : null}
          <div className="phase5__preview-actions">
            <button
              type="button"
              className="btn btn--ghost btn--small"
              disabled={tunerPreview.length === 0}
              onClick={() => copyToClipboard(tunerPreview.join('\n'))}
            >
              Copy commands
            </button>
          </div>
        </div>

        <button
          className="phase5__run"
          onClick={runCouplingTuner}
          disabled={tunerRunning || !selectedExperimentPath}
        >
          {tunerRunning ? 'Running…' : 'Run coupling tuner'}
        </button>

        {tunerError ? <p className="phase5__error">{tunerError}</p> : null}

        <div className="phase5__beta-sweep">
          <h4>Launch β sweep runs</h4>
          <p>
            Spawn <code>run_loop</code> jobs for each β value to capture full simulation artifacts for
            offline analysis.
          </p>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={runBetaSweep}
            disabled={betaSweepRunning || !selectedExperimentPath}
            title={
              !selectedExperimentPath
                ? 'Select an experiment to store β sweep outputs.'
                : undefined
            }
          >
            {betaSweepRunning ? 'Launching…' : 'Launch β sweep runs'}
          </button>
          {betaSweepError ? <p className="phase5__error">{betaSweepError}</p> : null}
        </div>
      </section>

      <section className="phase5__tuner-results">
        {tunerResult ? (
          <>
            <header className="phase5__tuner-header">
              <h3>Variant comparison</h3>
              <p>
                Baseline copy:&nbsp;
                <code>{tunerResult.baselineConfig}</code>{' '}
                <button type="button" className="link-button" onClick={() => copyToClipboard(tunerResult.baselineConfig)}>
                  Copy path
                </button>
              </p>
            </header>
            {tunerResult.commands.length ? (
              <details className="phase5__cli-list">
                <summary>Show CLI commands</summary>
                <pre>{tunerResult.commands.join('\n')}</pre>
              </details>
            ) : null}
            <table className="phase5__table">
              <thead>
                <tr>
                  <th>β</th>
                  <th>ηq</th>
                  <th>Φ</th>
                  <th>R</th>
                  <th>FS p95 / bound</th>
                  <th>Guard</th>
                  <th>Artifacts</th>
                </tr>
              </thead>
              <tbody>
                {tunerResult.variants.map((variant, index) => {
                  const isBest = bestVariantIndex === index;
                  const fsSummary =
                    variant.fsP95 != null && variant.fsBoundary != null
                      ? `${formatFloat(variant.fsP95, 3)} / ${formatFloat(variant.fsBoundary, 3)}`
                      : '—';
                  return (
                    <tr key={`${variant.beta}-${variant.etaQ ?? 'none'}`} className={isBest ? 'phase5__tuner-best' : undefined}>
                      <td>{formatFloat(variant.beta, 3)}</td>
                      <td>{variant.etaQ == null ? '—' : formatFloat(variant.etaQ, 3)}</td>
                      <td>{formatFloat(variant.phi, 4)}</td>
                      <td>{formatFloat(variant.rValue, 4)}</td>
                      <td>{fsSummary}</td>
                      <td>
                        <span className={guardBadgeClass(variant)}>
                          {variant.guardExceeded ? 'Exceeded' : 'OK'}
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="link-button"
                          onClick={() => copyToClipboard(variant.runDir)}
                        >
                          Copy run dir
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="phase5__tuner-summary">
              Output directory:&nbsp;
              <code>{tunerResult.outputDir}</code>{' '}
              <button type="button" className="link-button" onClick={() => copyToClipboard(tunerResult.outputDir)}>
                Copy path
              </button>
            </p>
          </>
        ) : (
          <p className="phase5__placeholder">Configure β / ηq values and generate evaluation variants.</p>
        )}
        {betaSweepRunning && betaSweepRuns.length === 0 ? (
          <p className="phase5__placeholder">Launching β sweep runs…</p>
        ) : null}
        {betaSweepRuns.length ? (
          <article className="phase5__beta-results">
            <header>
              <h3>β sweep run summary</h3>
            </header>
            <table className="phase5__table">
              <thead>
                <tr>
                  <th>β</th>
                  <th>Run ID</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {betaSweepRuns.map((entry) => (
                  <tr key={`${entry.runId}-${entry.beta}`}>
                    <td>{formatFloat(entry.beta, 3)}</td>
                    <td>
                      <code className="phase5__code-snippet">{entry.runId}</code>{' '}
                      <button type="button" className="link-button" onClick={() => copyToClipboard(entry.runId)}>
                        Copy
                      </button>
                    </td>
                    <td>
                      <span className={statusBadgeClass(entry.status)}>{entry.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {betaSweepDir ? (
              <p className="phase5__beta-path">
                Config staging:&nbsp;
                <code>{betaSweepDir}</code>{' '}
                <button type="button" className="link-button" onClick={() => copyToClipboard(betaSweepDir)}>
                  Copy path
                </button>
              </p>
            ) : null}
          </article>
        ) : null}
      </section>
    </div>
  );

  return (
    <div className="panel phase5">
      <h2>Phase 5 – Optimization</h2>
      <p className="phase5__lede">
        Survey curated graph families, optimise loop controls, and stress-test candidate protocols under noise.
      </p>

      <div className="phase5__tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`phase5__tab ${activeTab === tab.id ? 'phase5__tab--active' : ''}`}
            type="button"
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="phase5__tab-body">
        {activeTab === 'graph' ? renderGraphTab() : null}
        {activeTab === 'inverse' ? renderInverseTab() : null}
        {activeTab === 'noise' ? renderNoiseTab() : null}
        {activeTab === 'tuner' ? renderTunerTab() : null}
        {activeTab === 'recipes' ? renderRecipesTab() : null}
      </div>
    </div>
  );
};

export default Phase5Optimize;
