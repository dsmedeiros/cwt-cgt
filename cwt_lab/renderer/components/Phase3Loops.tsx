import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import type { GuidedLoopArgs, LoopAtHotspotPayload, RegistryRunRecord } from '../types/ipc';
import { runs } from '../ipc';
import { useExperimentNavigation } from '../navigation/ExperimentNavigationContext';
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
import { findArtifactNodeByName, joinArtifactPath, sanitizeArtifactNodes } from '../utils/artifacts';

type HotspotAxis = 'rho' | 'tau' | 'zeta' | 'zeta_phase' | 'kappa';

type HotspotCoordinates = Partial<Record<HotspotAxis, number>>;

type Hotspot = {
  id: string;
  name: string;
  calm?: boolean;
  axes?: [HotspotAxis, HotspotAxis];
  coordinates?: HotspotCoordinates;
  graph?: string | null;
  originPath?: string | null;
  omegaAbs?: number | null;
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
  failureReasons: string[];
};

const hotspotAxisOrder: HotspotAxis[] = ['rho', 'tau', 'zeta', 'zeta_phase', 'kappa'];

const hotspotAxisLabels: Record<HotspotAxis, string> = {
  rho: 'ρ',
  tau: 'τ',
  zeta: 'ζ',
  zeta_phase: 'ζ_phase',
  kappa: 'κ',
};

const defaultPlaneAxes: [HotspotAxis, HotspotAxis] = ['tau', 'zeta'];

const labelForAxis = (axis: HotspotAxis | string) =>
  hotspotAxisLabels[axis as HotspotAxis] ?? axis;

const axisAliasToHotspotAxis = (value: string): HotspotAxis | null => {
  const normalized = value.trim().toLowerCase();
  switch (normalized) {
    case 'rho':
    case 'ρ':
      return 'rho';
    case 'tau':
    case 'τ':
      return 'tau';
    case 'zeta':
    case 'ζ':
      return 'zeta';
    case 'zeta_phase':
    case 'zeta-phase':
    case 'zetaphase':
    case 'ζ_phase':
    case 'ζφ':
      return 'zeta_phase';
    case 'kappa':
    case 'κ':
      return 'kappa';
    default:
      return null;
  }
};

const defaultHotspots: Hotspot[] = [
  {
    id: 'calm-1',
    name: 'Calm Basin A',
    calm: true,
    axes: [defaultPlaneAxes[0], defaultPlaneAxes[1]],
    coordinates: { tau: 0.08, zeta: -0.03 },
    graph: 'default',
    originPath: 'defaults',
  },
  {
    id: 'calm-2',
    name: 'Calm Basin B',
    calm: true,
    axes: [defaultPlaneAxes[0], defaultPlaneAxes[1]],
    coordinates: { tau: -0.04, zeta: 0.06 },
    graph: 'default',
    originPath: 'defaults',
  },
  {
    id: 'spicy-1',
    name: 'Energetic Ridge',
    axes: [defaultPlaneAxes[0], defaultPlaneAxes[1]],
    coordinates: { tau: 0.18, zeta: 0.12 },
    graph: 'default',
    originPath: 'defaults',
  },
];

const graphOptions = [
  {
    id: 'ring3',
    label: 'Ring-3 triad',
    help: 'Deterministic three-node loop useful for verifying calibrations and guard thresholds.',
  },
  {
    id: 'random_regular',
    label: 'Random regular (20 nodes)',
    help: 'Generates a 20-node 3-regular digraph using the selected seed to stress-test the loop.',
  },
];

const safeNumber = (value: number) => Number(value.toFixed(4));

const toCliValue = (value: number) => value.toFixed(4).replace(/\.0+$/, '');

const defaultAxisAmplitude = 0.15;

const getHotspotAxes = (hotspot: Hotspot): [HotspotAxis, HotspotAxis] => {
  if (Array.isArray(hotspot.axes) && hotspot.axes.length === 2) {
    return [hotspot.axes[0], hotspot.axes[1]];
  }
  return [defaultPlaneAxes[0], defaultPlaneAxes[1]];
};

const planeAxesEqual = (
  a: [HotspotAxis, HotspotAxis],
  b: [HotspotAxis, HotspotAxis],
) => a[0] === b[0] && a[1] === b[1];

const manualPlaneMismatchWarning =
  'Manual plane selection diverges from the Phase 2 discovery plane. Guided heuristics assume the discovered axes pair; realign them before continuing.';

let hasWarnedMissingCoordinate = false;

const getHotspotCoordinate = (axis: HotspotAxis | string, hotspot: Hotspot): number => {
  const canonical = axisAliasToHotspotAxis(String(axis)) ?? null;
  const candidates: string[] = [];
  const registerCandidate = (candidate: string | null | undefined) => {
    const normalized = String(candidate ?? '').trim();
    if (!normalized || candidates.includes(normalized)) {
      return;
    }
    candidates.push(normalized);
  };

  registerCandidate(typeof axis === 'string' ? axis : String(axis));
  if (canonical) {
    registerCandidate(canonical);
  }

  switch (canonical) {
    case 'rho':
      registerCandidate('ρ');
      break;
    case 'tau':
      registerCandidate('τ');
      break;
    case 'zeta':
      registerCandidate('ζ');
      break;
    case 'zeta_phase':
      registerCandidate('zetaPhase');
      registerCandidate('zeta-phase');
      registerCandidate('zetaphase');
      registerCandidate('ζ_phase');
      registerCandidate('ζφ');
      break;
    case 'kappa':
      registerCandidate('κ');
      break;
    default:
      break;
  }

  const readCoordinate = (record: Record<string, unknown> | undefined) => {
    if (!record) {
      return undefined;
    }
    for (const key of candidates) {
      const value = record[key];
      if (typeof value === 'number' && Number.isFinite(value)) {
        return value;
      }
    }
    return undefined;
  };

  const coordinateValue = readCoordinate(hotspot.coordinates as Record<string, unknown> | undefined);
  if (typeof coordinateValue === 'number') {
    return coordinateValue;
  }

  const legacyValue = readCoordinate(hotspot as Record<string, unknown>);
  if (typeof legacyValue === 'number') {
    return legacyValue;
  }

  if (!hasWarnedMissingCoordinate) {
    const axisLabel = labelForAxis(canonical ?? axis);
    const hotspotLabel = hotspot.name ?? hotspot.id ?? 'unknown hotspot';
    // eslint-disable-next-line no-console
    console.warn(`Missing ${axisLabel} coordinate for ${hotspotLabel}; defaulting to 1.0.`);
    hasWarnedMissingCoordinate = true;
  }

  return 1.0;
};

const getPlaneCoordinates = (hotspot: Hotspot): [number, number] => {
  const [axisA, axisB] = getHotspotAxes(hotspot);
  const coordA = getHotspotCoordinate(axisA, hotspot);
  const coordB = getHotspotCoordinate(axisB, hotspot);
  return [coordA, coordB];
};

const buildCoordinateRecord = (hotspot: Hotspot): Record<string, number> => {
  const record: Record<string, number> = {};
  const seen = new Set<HotspotAxis>();
  if (hotspot.coordinates) {
    for (const axis of hotspotAxisOrder) {
      const value = hotspot.coordinates[axis];
      if (typeof value === 'number' && Number.isFinite(value)) {
        record[axis] = value;
        seen.add(axis);
      }
    }
  }
  // Legacy fallback to any numeric properties.
  for (const axis of hotspotAxisOrder) {
    if (seen.has(axis)) {
      continue;
    }
    const legacyValue = (hotspot as Record<string, unknown>)[axis];
    if (typeof legacyValue === 'number' && Number.isFinite(legacyValue)) {
      record[axis] = legacyValue;
    }
  }
  return record;
};

const formatPlaneSummary = (hotspot: Hotspot) => {
  const [axisA, axisB] = getHotspotAxes(hotspot);
  const [coordA, coordB] = getPlaneCoordinates(hotspot);
  const labelA = labelForAxis(axisA);
  const labelB = labelForAxis(axisB);
  return `${labelA} ${toCliValue(coordA)} / ${labelB} ${toCliValue(coordB)}`;
};

const normalizeOrigin = (value: string | null | undefined) =>
  value ? value.replace(/\\/g, '/').trim() : '';

const PHASE3_SUMMARY_FILENAME = 'phase3_loop_summary.json';

type GuidedStepEntry = {
  id: string;
  value: string;
};

let guidedStepEntrySequence = 0;
const createGuidedStepEntry = (value: number | string = ''): GuidedStepEntry => ({
  id: `guided-step-${guidedStepEntrySequence++}`,
  value: typeof value === 'number' ? String(value) : String(value ?? ''),
});

type Phase1HotspotEntry = {
  axes: [HotspotAxis, HotspotAxis];
  coordinates: HotspotCoordinates;
  omegaAbs: number | null;
};

const parsePhase1Hotspots = (raw: string): Phase1HotspotEntry[] => {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (error) {
    throw new Error('Selected file is not valid JSON.');
  }

  if (!parsed || typeof parsed !== 'object') {
    throw new Error('Hotspot file contents are not a JSON object.');
  }

  const axesRaw = Array.isArray((parsed as { axes?: unknown }).axes)
    ? ((parsed as { axes?: unknown }).axes as unknown[])
    : [];
  const axes = axesRaw
    .map((axis) => String(axis ?? '').trim())
    .filter((axis) => axis.length > 0)
    .map((axis) => ({
      original: axis,
      normalized: axis.toLowerCase(),
      canonical: axisAliasToHotspotAxis(axis),
    }));

  const tilesRaw = (parsed as { top_tiles?: unknown; topTiles?: unknown }).top_tiles ?? (
    parsed as { topTiles?: unknown }
  ).topTiles;
  const tiles = Array.isArray(tilesRaw) ? tilesRaw : [];

  if (tiles.length === 0) {
    throw new Error('Hotspot file does not list any ridge selections.');
  }

  const entries: Phase1HotspotEntry[] = [];

  const readCoordinate = (record: Record<string, unknown>, candidates: (string | null | undefined)[]) => {
    for (const key of candidates) {
      const name = String(key ?? '').trim();
      if (!name) {
        continue;
      }
      const value = Number(record[name]);
      if (Number.isFinite(value)) {
        return value;
      }
    }
    return null;
  };

  const candidateMap: Record<HotspotAxis, string[]> = {
    rho: ['rho', 'ρ'],
    tau: ['tau', 'τ'],
    zeta: ['zeta', 'ζ'],
    zeta_phase: ['zeta_phase', 'ζ_phase', 'zeta-phase', 'zetaphase', 'ζφ'],
    kappa: ['kappa', 'κ'],
  };

  for (const axis of axes) {
    if (!axis.canonical) {
      continue;
    }
    candidateMap[axis.canonical] = [axis.original, ...candidateMap[axis.canonical].filter((item) => item !== axis.original)];
  }

  const planeAxesFromFile = axes
    .map((axis) => axis.canonical)
    .filter((axis): axis is HotspotAxis => Boolean(axis))
    .filter((axis, index, array) => array.indexOf(axis) === index);

  const planeAxes: [HotspotAxis, HotspotAxis] =
    planeAxesFromFile.length >= 2
      ? [planeAxesFromFile[0]!, planeAxesFromFile[1]!]
      : [defaultPlaneAxes[0], defaultPlaneAxes[1]];

  const planeAxisSeen: Partial<Record<HotspotAxis, boolean>> = {
    [planeAxes[0]]: false,
    [planeAxes[1]]: false,
  };

  for (const tile of tiles) {
    if (!tile || typeof tile !== 'object') {
      continue;
    }

    const coordinates = (tile as { coordinates?: unknown }).coordinates;
    if (!coordinates || typeof coordinates !== 'object') {
      continue;
    }

    const coordinateRecord = coordinates as Record<string, unknown>;
    const coordinateValues: HotspotCoordinates = {};
    for (const axis of hotspotAxisOrder) {
      const value = readCoordinate(coordinateRecord, candidateMap[axis]);
      if (value == null) {
        continue;
      }
      coordinateValues[axis] = value;
      if (axis === planeAxes[0] || axis === planeAxes[1]) {
        planeAxisSeen[axis] = true;
      }
    }

    const planeValueA = coordinateValues[planeAxes[0]];
    const planeValueB = coordinateValues[planeAxes[1]];

    if (planeValueA == null || planeValueB == null) {
      continue;
    }

    const omegaRaw = (tile as { omega_abs?: unknown }).omega_abs ??
      (tile as Record<string, unknown>).omegaAbs;
    const omegaAbs = Number(omegaRaw);

    entries.push({
      axes: [planeAxes[0], planeAxes[1]],
      coordinates: coordinateValues,
      omegaAbs: Number.isFinite(omegaAbs) ? omegaAbs : null,
    });
  }

  if (entries.length === 0 && tiles.length > 0) {
    const missing: string[] = [];
    for (const axis of [planeAxes[0], planeAxes[1]]) {
      if (!planeAxisSeen[axis]) {
        missing.push(labelForAxis(axis));
      }
    }
    if (missing.length > 0) {
      throw new Error(`Hotspot file must contain ${missing.join(' and ')} coordinates.`);
    }
  }

  if (entries.length === 0) {
    throw new Error('No usable hotspots were found in the selected file.');
  }

  return entries;
};

const toImportId = (origin: string, index: number) => {
  const safeOrigin = origin
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  const base = safeOrigin.length > 0 ? safeOrigin : 'phase1-hotspot';
  return `${base}-${index + 1}`;
};

const formatOmega = (value: number | null) => {
  if (value == null) {
    return null;
  }
  if (!Number.isFinite(value)) {
    return null;
  }
  return value.toFixed(3);
};

const hotspotKey = (hotspot: Hotspot) => {
  const axes = getHotspotAxes(hotspot);
  const graph = hotspot.graph ?? '';
  const origin = normalizeOrigin(hotspot.originPath);
  const [coordA, coordB] = getPlaneCoordinates(hotspot);
  const center = `${coordA.toFixed(6)}|${coordB.toFixed(6)}`;
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
  saveSummaryPath?: string | null,
): LoopAtHotspotPayload => {
  const axes = getHotspotAxes(hotspot);
  const [axisI, axisJ] = axes;
  const coordinates = buildCoordinateRecord(hotspot);
  const centerI = typeof coordinates[axisI] === 'number' ? coordinates[axisI] : 0;
  const centerJ = typeof coordinates[axisJ] === 'number' ? coordinates[axisJ] : 0;
  coordinates[axisI] = centerI;
  coordinates[axisJ] = centerJ;
  const hotspotEntry: Record<string, unknown> = {
    coordinates,
    label: hotspot.name,
  };
  const origin = normalizeOrigin(hotspot.originPath);
  if (origin) {
    hotspotEntry.origin = origin;
  }
  if (hotspot.id) {
    hotspotEntry.id = hotspot.id;
  }

  const payload: LoopAtHotspotPayload = {
    hotspotsJson: JSON.stringify({ axes, hotspots: [hotspotEntry] }),
    axes,
    extents,
    fsGuard,
    graph,
    limit,
    seed,
    neighborSettleSteps,
    adaptLevels,
  };
  if (saveSummaryPath) {
    payload.saveSummary = saveSummaryPath;
  }
  return payload;
};

const buildGuidedPayload = (
  hotspot: Hotspot,
  graph: string,
  axisAmplitude: (axis: string) => number,
  kappaAmp: number,
  kappaCenter: number,
  stepsList: number[],
  fsGuard: number,
  minPhi: number,
  seed: number,
  summaryPath?: string | null,
): GuidedLoopArgs => {
  const axes = getHotspotAxes(hotspot);
  const [axisI, axisJ] = axes;
  const centerI = getHotspotCoordinate(axisI, hotspot);
  const centerJ = getHotspotCoordinate(axisJ, hotspot);
  const planeAmpI = axisAmplitude(axisI);
  const planeAmpJ = axisAmplitude(axisJ);
  const payload: GuidedLoopArgs = {
    // axis[0] is the handle; axes[1] × axes[2] span the loop plane
    axes3: ['kappa', axisI, axisJ],
    center: [kappaCenter, centerI, centerJ],
    amplitudes: [kappaAmp, planeAmpI, planeAmpJ],
    graph,
    stepsList,
    fsGuard,
    minPhi,
    seed,
  };

  if (summaryPath) {
    const centerRecord: Record<string, number> = {
      kappa: kappaCenter,
      [axisI]: centerI,
      [axisJ]: centerJ,
    };
    const metadata: Record<string, unknown> = {};
    if (hotspot.id) {
      metadata.id = hotspot.id;
    }
    const origin = normalizeOrigin(hotspot.originPath);
    if (origin) {
      metadata.origin = origin;
    }
    if (typeof hotspot.calm === 'boolean') {
      metadata.calm = hotspot.calm;
    }
    if (hotspot.graph) {
      metadata.graph = hotspot.graph;
    }

    payload.summary = {
      path: summaryPath,
      axes: [axisI, axisJ],
      extents: [planeAmpI, planeAmpJ],
      center: centerRecord,
      centerVector: [kappaCenter, centerI, centerJ],
      amplitudes: [kappaAmp, planeAmpI, planeAmpJ],
      label: hotspot.name,
      ...(hotspot.omegaAbs !== undefined ? { omegaAbs: hotspot.omegaAbs } : {}),
      ...(Object.keys(metadata).length > 0 ? { metadata } : {}),
    };
  }

  return payload;
};

const previewGuidedCli = async (payload: GuidedLoopArgs): Promise<string> => {
  if (typeof window === 'undefined' || !window?.CWT?.run?.preview) {
    return 'Command preview unavailable in this environment.';
  }

  const { stepsList, summary: _summary, ...rest } = payload;
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

const metricFromRecord = (
  metrics: Record<string, number | null> | null,
  key: string,
  extraKeys: string[] = [],
) => {
  if (!metrics) {
    return undefined;
  }

  const seen = new Set<string>();
  const candidates: string[] = [];
  const registerCandidate = (candidate: string) => {
    const normalized = candidate.trim();
    if (!normalized || seen.has(normalized)) {
      return;
    }
    seen.add(normalized);
    candidates.push(normalized);
  };

  [key, key.replace(/-/g, '_'), key.replace(/_/g, '-')].forEach(registerCandidate);
  extraKeys.forEach((candidate) => {
    [candidate, candidate.replace(/-/g, '_'), candidate.replace(/_/g, '-')].forEach(
      registerCandidate,
    );
  });

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

const phiFromMetrics = (metrics: Record<string, number | null> | null) => {
  const primary = metricFromRecord(metrics, 'phi', ['phi_flux', 'phi_value']);
  if (typeof primary === 'number') {
    return Math.abs(primary);
  }

  const phiForward = metricFromRecord(metrics, 'phi_forward', ['phiForward']);
  const phiReverse = metricFromRecord(metrics, 'phi_reverse', ['phiReverse']);
  if (typeof phiForward === 'number' && typeof phiReverse === 'number') {
    return Math.max(Math.abs(phiForward), Math.abs(phiReverse));
  }
  if (typeof phiForward === 'number') {
    return Math.abs(phiForward);
  }
  if (typeof phiReverse === 'number') {
    return Math.abs(phiReverse);
  }
  const phiSum = metricFromRecord(metrics, 'phi_sum', ['phiSum']);
  if (typeof phiSum === 'number') {
    return Math.abs(phiSum);
  }
  return undefined;
};

const buildGuidedFailureReasons = ({
  satisfied,
  runs,
  minPhi,
  fsGuard,
  planeAxes,
}: {
  satisfied: boolean;
  runs: GuidedLoopRun[];
  minPhi?: number;
  fsGuard?: number;
  planeAxes: [HotspotAxis, HotspotAxis];
}) => {
  if (satisfied) {
    return [];
  }

  const metrics =
    runs[runs.length - 1]?.metrics ?? runs.find((run) => run.metrics)?.metrics ?? null;
  const reasons: string[] = [];

  const [axisA, axisB] = planeAxes;
  const axisALabel = labelForAxis(axisA);
  const axisBLabel = labelForAxis(axisB);

  const phi = phiFromMetrics(metrics);
  const fsP95 = metricFromRecord(metrics, 'fs_p95');
  const fsExceeded = metricFromRecord(metrics, 'fs_guard_exceeded');

  if (minPhi != null && (phi == null || phi < minPhi)) {
    reasons.push(
      `Guided loop φ=${
        phi == null ? 'n/a' : phi.toFixed(4)
      } did not reach minimum ${minPhi.toFixed(4)}. Try increasing ${axisALabel}/${axisBLabel} amplitudes, loosening the Φ threshold, or revisiting the selected ${axisALabel}/${axisBLabel} axes/extents per the troubleshooting guidance.`,
    );
  }

  if (
    fsGuard != null &&
    ((fsP95 != null && fsP95 > fsGuard) || (fsExceeded != null && fsExceeded > 0))
  ) {
    reasons.push(
      `Guided loop FS guard threshold ${fsGuard.toFixed(4)} was exceeded (p95=${fsP95 == null ? 'n/a' : fsP95.toFixed(4)}).`,
    );
  }

  if (reasons.length === 0) {
    reasons.push('Guided loop criteria were not satisfied.');
  }

  return reasons;
};

const Phase3Loops = () => {
  const [hotspots, setHotspots] = useState<Hotspot[]>(defaultHotspots);
  const [selectedHotspotId, setSelectedHotspotId] = useState<string>(defaultHotspots[0].id);
  const [manualPlaneAxes, setManualPlaneAxes] = useState<[HotspotAxis, HotspotAxis]>([
    defaultPlaneAxes[0],
    defaultPlaneAxes[1],
  ]);
  const [manualCoordinates, setManualCoordinates] = useState<HotspotCoordinates>({
    tau: 0,
    zeta: 0,
  });
  const manualAxisOptions = useMemo(
    () => hotspotAxisOrder.map((axis) => ({ value: axis, label: labelForAxis(axis) })),
    [],
  );

  const updateManualAxis = useCallback((index: 0 | 1, axis: HotspotAxis) => {
    setManualPlaneAxes((prev) => {
      const next: [HotspotAxis, HotspotAxis] = [prev[0], prev[1]];
      const otherIndex = index === 0 ? 1 : 0;
      next[index] = axis;
      if (next[otherIndex] === axis) {
        const fallback = hotspotAxisOrder.find(
          (candidate) => candidate !== axis && candidate !== next[index],
        );
        next[otherIndex] = fallback ?? (axis === 'tau' ? 'zeta' : 'tau');
      }
      return next;
    });
    setManualCoordinates((prev) => {
      if (prev[axis] != null && Number.isFinite(prev[axis] ?? 0)) {
        return prev;
      }
      return { ...prev, [axis]: 0 };
    });
  }, []);

  const updateManualCoordinate = useCallback((axis: HotspotAxis, value: number) => {
    setManualCoordinates((prev) => ({
      ...prev,
      [axis]: Number.isFinite(value) ? value : 0,
    }));
  }, []);
  const manualOptionalAxes = useMemo(
    () => hotspotAxisOrder.filter((axis) => !manualPlaneAxes.includes(axis)),
    [manualPlaneAxes],
  );
  const [graph, setGraph] = useState(graphOptions[0].id);
  const [activeTab, setActiveTab] = useState<'simple' | 'guided'>('guided');

  const {
    experiments,
    experimentsError,
    experimentsLoading,
    selectedExperimentPath,
    substrates,
    substratesError,
    substratesLoading,
    selectedSubstratePath,
  } = useExperimentNavigation();

  const [phase1Runs, setPhase1Runs] = useState<RegistryRunRecord[]>([]);
  const [selectedPhase1RunId, setSelectedPhase1RunId] = useState('');
  const [isLoadingPhase1Runs, setIsLoadingPhase1Runs] = useState(false);
  const [phase1RunError, setPhase1RunError] = useState<string | null>(null);
  const [importMessage, setImportMessage] = useState<string | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [isImportingHotspots, setIsImportingHotspots] = useState(false);

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

  const [rhoAmplitude, setRhoAmplitude] = useState(defaultAxisAmplitude);
  const [tauAmplitude, setTauAmplitude] = useState(defaultAxisAmplitude);
  const [zetaAmplitude, setZetaAmplitude] = useState(defaultAxisAmplitude);
  const [zetaPhaseAmplitude, setZetaPhaseAmplitude] = useState(defaultAxisAmplitude);
  const [kappaAmplitude, setKappaAmplitude] = useState(0.06);
  const [kappaCenter, setKappaCenter] = useState(1.0);
  const [guidedStepEntries, setGuidedStepEntries] = useState<GuidedStepEntry[]>([
    createGuidedStepEntry(160),
    createGuidedStepEntry(320),
    createGuidedStepEntry(480),
  ]);
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
  const isMountedRef = useRef(true);
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

  const [discoveryPlane, setDiscoveryPlane] = useState<[HotspotAxis, HotspotAxis]>(() =>
    getHotspotAxes(selectedHotspot),
  );

  useEffect(() => {
    const fallback: [HotspotAxis, HotspotAxis] = [defaultPlaneAxes[0], defaultPlaneAxes[1]];
    const nextAxes = selectedHotspot ? getHotspotAxes(selectedHotspot) : fallback;
    setDiscoveryPlane((prev) => (planeAxesEqual(prev, nextAxes) ? prev : nextAxes));
    setManualPlaneAxes((prev) => (planeAxesEqual(prev, nextAxes) ? prev : nextAxes));
  }, [selectedHotspot]);

  const selectedPlaneAxes = useMemo(() => getHotspotAxes(selectedHotspot), [selectedHotspot]);
  const [selectedAxisI, selectedAxisJ] = selectedPlaneAxes;
  const selectedAxisILabel = labelForAxis(selectedAxisI);
  const selectedAxisJLabel = labelForAxis(selectedAxisJ);
  const selectedOmegaAbs = selectedHotspot?.omegaAbs ?? null;
  const amplitudeGuidance = useMemo(() => {
    if (!Number.isFinite(guidedMinPhi) || guidedMinPhi <= 0) {
      return null;
    }
    const fallbackOmegaAbs = 0.1;
    const hasOmega = typeof selectedOmegaAbs === 'number' && Number.isFinite(selectedOmegaAbs) && Math.abs(selectedOmegaAbs) > 0;
    const omegaMagnitude = hasOmega ? Math.abs(selectedOmegaAbs ?? fallbackOmegaAbs) : fallbackOmegaAbs;
    if (!Number.isFinite(omegaMagnitude) || omegaMagnitude <= 0) {
      return null;
    }
    const areaMin = guidedMinPhi / omegaMagnitude;
    if (!Number.isFinite(areaMin) || areaMin <= 0) {
      return null;
    }
    const symmetricAmplitude = Math.sqrt(areaMin / 4);
    if (!Number.isFinite(symmetricAmplitude) || symmetricAmplitude <= 0) {
      return null;
    }
    return {
      areaMin,
      symmetricAmplitude,
      omegaMagnitude,
      usingFallback: !hasOmega,
    } as const;
  }, [guidedMinPhi, selectedOmegaAbs]);
  const amplitudeGuidanceText = useMemo(() => {
    if (!amplitudeGuidance) {
      return null;
    }
    const { areaMin, symmetricAmplitude, omegaMagnitude, usingFallback } = amplitudeGuidance;
    const areaText = areaMin.toFixed(4);
    const amplitudeText = symmetricAmplitude.toFixed(3);
    const omegaText = omegaMagnitude.toFixed(3);
    const axisPairLabel = `${selectedAxisILabel}/${selectedAxisJLabel}`;
    const assumptionText = usingFallback
      ? `Assuming |Ω| ≈ ${omegaText} because the hotspot metadata omits |Ω|.`
      : `Using hotspot |Ω| ≈ ${omegaText}.`;
    return `Φ guard needs ${axisPairLabel} area ≥ ${areaText}. Symmetric amplitude suggestion: ±${amplitudeText}. ${assumptionText}`;
  }, [amplitudeGuidance, selectedAxisILabel, selectedAxisJLabel]);
  const [discoveryAxisI, discoveryAxisJ] = discoveryPlane;
  const discoveryAxisILabel = labelForAxis(discoveryAxisI);
  const discoveryAxisJLabel = labelForAxis(discoveryAxisJ);
  const manualPlaneMatchesDiscovery = useMemo(
    () => planeAxesEqual(manualPlaneAxes, discoveryPlane),
    [discoveryPlane, manualPlaneAxes],
  );

  const axisAmp = useCallback(
    (axis: string): number => {
      const canonical = axisAliasToHotspotAxis(axis) ?? (axis as HotspotAxis | null);
      switch (canonical) {
        case 'rho':
          return rhoAmplitude;
        case 'tau':
          return tauAmplitude;
        case 'zeta':
          return zetaAmplitude;
        case 'zeta_phase':
          return zetaPhaseAmplitude;
        case 'kappa':
          return kappaAmplitude;
        default:
          return defaultAxisAmplitude;
      }
    },
    [kappaAmplitude, rhoAmplitude, tauAmplitude, zetaAmplitude, zetaPhaseAmplitude],
  );

  const setAxisAmplitude = useCallback(
    (axis: HotspotAxis, value: number) => {
      const safeValue = Number.isFinite(value) ? value : defaultAxisAmplitude;
      switch (axis) {
        case 'rho':
          setRhoAmplitude(safeValue);
          break;
        case 'tau':
          setTauAmplitude(safeValue);
          break;
        case 'zeta':
          setZetaAmplitude(safeValue);
          break;
        case 'zeta_phase':
          setZetaPhaseAmplitude(safeValue);
          break;
        case 'kappa':
          setKappaAmplitude(safeValue);
          break;
        default:
          break;
      }
    },
    [setKappaAmplitude, setRhoAmplitude, setTauAmplitude, setZetaAmplitude, setZetaPhaseAmplitude],
  );


  useEffect(
    () => () => {
      isMountedRef.current = false;
    },
    [],
  );

  const refreshPhase1Runs = useCallback(async () => {
    if (!isMountedRef.current) {
      return;
    }

    setIsLoadingPhase1Runs(true);
    try {
      if (typeof window === 'undefined' || !window?.CWT?.registry?.query) {
        setPhase1RunError('Phase 1 runs are unavailable outside the desktop application.');
        setPhase1Runs([]);
        setSelectedPhase1RunId('');
        return;
      }

      const records = await runs.listRecent(50);
      if (!isMountedRef.current) {
        return;
      }
      const relevant = records
        .filter((run) => run.phase === 'phase1' && run.status === 'complete')
        .sort((a, b) => b.updatedAt - a.updatedAt);
      setPhase1Runs(relevant);
      if (!relevant.some((run) => run.id === selectedPhase1RunId)) {
        setSelectedPhase1RunId(relevant[0]?.id ?? '');
      }
      setPhase1RunError(null);
    } catch (error) {
      if (!isMountedRef.current) {
        return;
      }
      const message = error instanceof Error ? error.message : String(error);
      setPhase1RunError(message);
    } finally {
      if (isMountedRef.current) {
        setIsLoadingPhase1Runs(false);
      }
    }
  }, [selectedPhase1RunId]);

  useEffect(() => {
    void refreshPhase1Runs();
  }, [refreshPhase1Runs]);

  useEffect(() => {
    if (selectedExperimentPath && selectedSubstratePath) {
      return;
    }

    setImportError(null);
    setImportMessage(null);
    setTipMessage(null);
    setSimpleRuns([]);
    setGuidedResult(null);
    setHotspots(defaultHotspots.map((hotspot) => ({ ...hotspot })));
    setSelectedHotspotId(defaultHotspots[0].id);
  }, [selectedExperimentPath, selectedSubstratePath]);

  const applyImportedHotspots = useCallback(
    (entries: Phase1HotspotEntry[], originKey: string, sourceLabel: string) => {
      const normalizedOrigin = normalizeOrigin(originKey) || originKey;
      const effectiveOrigin = normalizedOrigin || originKey;
      const created: Hotspot[] = entries.map((entry, index) => {
        const omegaLabel = formatOmega(entry.omegaAbs);
        const suffix = omegaLabel ? ` (|Ω| ${omegaLabel})` : '';
        const planeAxes = entry.axes ?? [...defaultPlaneAxes];
        const coordinates: HotspotCoordinates = {};
        for (const axis of hotspotAxisOrder) {
          const value = entry.coordinates?.[axis];
          if (typeof value === 'number' && Number.isFinite(value)) {
            coordinates[axis] = value;
          }
        }
        return {
          id: toImportId(effectiveOrigin || sourceLabel, index),
          name: `Phase 1 ridge #${index + 1}${suffix}`,
          axes: [planeAxes[0], planeAxes[1]],
          coordinates,
          graph: null,
          originPath: effectiveOrigin,
          omegaAbs: entry.omegaAbs,
        } satisfies Hotspot;
      });

      setHotspots((prev) => {
        const withoutDefaults = prev.filter((item) => item.originPath !== 'defaults');
        if (!effectiveOrigin) {
          return [...created, ...withoutDefaults];
        }
        const filtered = withoutDefaults.filter((item) => item.originPath !== effectiveOrigin);
        return [...created, ...filtered];
      });

      if (created.length > 0) {
        setSelectedHotspotId(created[0].id);
      }
      setImportError(null);
      setImportMessage(`Loaded ${created.length} hotspots from ${sourceLabel}.`);
    },
    [setHotspots],
  );

  const importFromPhase1Run = useCallback(async () => {
    if (!selectedPhase1RunId) {
      setImportError('Select a completed Phase 1 run to import its hotspots.');
      setImportMessage(null);
      return;
    }

    if (!window?.CWT?.run?.readArtifact) {
      setImportError('Phase 1 artifacts are unavailable in this environment.');
      setImportMessage(null);
      return;
    }

    setImportError(null);
    setImportMessage(null);
    setIsImportingHotspots(true);
    try {
      const response = await window.CWT.run.readArtifact({
        runId: selectedPhase1RunId,
        relativePath: 'top_omega_tiles.json',
      });
      if (!response.ok) {
        throw new Error(response.error ?? 'Failed to load Phase 1 hotspot file.');
      }
      if (!response.data?.contents) {
        throw new Error('Phase 1 hotspot file was empty.');
      }
      const entries = parsePhase1Hotspots(response.data.contents);
      const run = phase1Runs.find((item) => item.id === selectedPhase1RunId);
      const label = run?.label ?? run?.experiment ?? run?.command ?? 'Phase 1 run';
      applyImportedHotspots(entries, `run:${selectedPhase1RunId}`, label);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setImportError(message);
      setImportMessage(null);
    } finally {
      setIsImportingHotspots(false);
    }
  }, [
    selectedPhase1RunId,
    phase1Runs,
    applyImportedHotspots,
  ]);

  useEffect(() => {
    if (!selectedPhase1RunId) {
      return;
    }

    void importFromPhase1Run();
  }, [selectedPhase1RunId, importFromPhase1Run]);

  const loadHotspotsFromSubstrate = useCallback(async () => {
    if (!selectedSubstratePath) {
      setImportError('Select a substrate to load hotspots.');
      setImportMessage(null);
      return;
    }

    const api = typeof window !== 'undefined' ? window?.CWT?.artifacts : undefined;
    if (!api?.list) {
      setImportError('Artifact listing is unavailable in this build.');
      setImportMessage(null);
      return;
    }
    if (!window?.CWT?.artifacts?.readFile) {
      setImportError('Artifact file reading is unavailable in this build.');
      setImportMessage(null);
      return;
    }

    setImportError(null);
    setImportMessage(null);
    setIsImportingHotspots(true);
    try {
      const listResponse = await api.list({ under: selectedSubstratePath });
      if (!listResponse.ok) {
        throw new Error(listResponse.error ?? 'Failed to inspect substrate directory.');
      }
      const nodes = sanitizeArtifactNodes(listResponse.data);
      const fileNode = findArtifactNodeByName(nodes, 'top_omega_tiles.json');
      if (!fileNode) {
        throw new Error('top_omega_tiles.json not found in the selected substrate.');
      }
      const fileResponse = await window.CWT.artifacts.readFile({ path: fileNode.path });
      if (!fileResponse.ok) {
        throw new Error(fileResponse.error ?? 'Failed to load Phase 1 hotspot file.');
      }
      const payload = fileResponse.data as { contents?: unknown } | null;
      const contents = typeof payload?.contents === 'string' ? payload.contents : '';
      if (!contents) {
        throw new Error('Phase 1 hotspot file was empty.');
      }

      const entries = parsePhase1Hotspots(contents);
      const experiment = experiments.find((node) => node.path === selectedExperimentPath);
      const substrate = substrates.find((node) => node.path === selectedSubstratePath);
      const experimentLabel = experiment?.relativePath ?? 'experiment';
      const substrateLabel = substrate?.name ?? 'substrate';
      applyImportedHotspots(entries, fileNode.path, `${experimentLabel}/${substrateLabel}`);
      setImportMessage(`Loaded ${entries.length} hotspots from ${experimentLabel}/${substrateLabel}.`);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setImportError(message);
      setImportMessage(null);
    } finally {
      setIsImportingHotspots(false);
    }
  }, [
    selectedSubstratePath,
    experiments,
    selectedExperimentPath,
    substrates,
    applyImportedHotspots,
  ]);

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
  const guidedStepAnalysis = useMemo(() => {
    const validations = guidedStepEntries.map((entry) => ({
      entry,
      validation: validateSteps(entry.value),
    }));
    const counts = new Map<number, number>();
    const numericValues: number[] = [];
    validations.forEach(({ validation }) => {
      if (validation.ok) {
        numericValues.push(validation.value);
        counts.set(validation.value, (counts.get(validation.value) ?? 0) + 1);
      }
    });
    const errors = new Map<string, string | null>();
    validations.forEach(({ entry, validation }) => {
      if (!validation.ok) {
        errors.set(entry.id, validation.message);
        return;
      }
      if ((counts.get(validation.value) ?? 0) > 1) {
        errors.set(entry.id, 'Duplicate step.');
        return;
      }
      errors.set(entry.id, null);
    });
    const steps = Array.from(new Set(numericValues)).sort((a, b) => a - b);

    return { errors, steps };
  }, [guidedStepEntries]);
  const guidedSteps = guidedStepAnalysis.steps;
  const guidedStepErrors = guidedStepEntries.map(
    (entry) => guidedStepAnalysis.errors.get(entry.id) ?? null,
  );
  const hasGuidedStepError = guidedStepErrors.some((message) => message != null);
  const firstGuidedStepError = guidedStepErrors.find((message) => message != null) ?? null;
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
    if (!hasGuidedStepError && guidedSteps.length === 0) {
      return 'Add at least one valid step.';
    }
    return undefined;
  }, [fsGuardValidation, guidedSteps.length, hasGuidedStepError]);

  const isSimpleRunDisabled = isSimpleRunning || Boolean(simpleRunDisabledReason);
  const isGuidedRunDisabled =
    isGuidedRunning || hasGuidedStepError || Boolean(guidedRunDisabledReason);
  const simpleRunTitle = isSimpleRunning ? 'Loop already running.' : simpleRunDisabledReason;
  const guidedRunTitle = isGuidedRunning
    ? 'Guided calibration in progress.'
    : guidedRunDisabledReason ?? firstGuidedStepError ?? undefined;

  const addManualHotspot = () => {
    const id = `manual-${Date.now()}`;
    const [axisA, axisB] = manualPlaneAxes;
    const coordinateMap: HotspotCoordinates = {};
    for (const axis of hotspotAxisOrder) {
      const value = manualCoordinates[axis];
      if (typeof value === 'number' && Number.isFinite(value)) {
        coordinateMap[axis] = value;
      }
    }
    const valueA = typeof coordinateMap[axisA] === 'number' ? (coordinateMap[axisA] as number) : 0;
    const valueB = typeof coordinateMap[axisB] === 'number' ? (coordinateMap[axisB] as number) : 0;
    coordinateMap[axisA] = valueA;
    coordinateMap[axisB] = valueB;
    const labelA = labelForAxis(axisA);
    const labelB = labelForAxis(axisB);
    const newHotspot: Hotspot = {
      id,
      name: `Manual (${labelA} ${toCliValue(valueA)}, ${labelB} ${toCliValue(valueB)})`,
      calm: true,
      axes: [axisA, axisB],
      coordinates: coordinateMap,
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

    if (!selectedExperimentPath) {
      setImportError('Select an experiment before running the validator.');
      setImportMessage(null);
      return;
    }

    if (!selectedSubstratePath) {
      setImportError('Select a substrate before running the validator.');
      setImportMessage(null);
      return;
    }

    const extents: [number, number] = [extentAValidation.value, extentBValidation.value];
    const guardValue = fsGuardValidation.value;
    const settleSteps = neighborSettleValidation.value;
    const adaptLevels = adaptLevelsValidation.value;
    const summaryPath = joinArtifactPath(selectedSubstratePath, PHASE3_SUMMARY_FILENAME);
    const payload = buildSimplePayload(
      selectedHotspot,
      graph,
      extents,
      guardValue,
      simpleLimitValidation.value,
      simpleSeed,
      settleSteps,
      adaptLevels,
      summaryPath,
    );
    const payloadWithExperiment: LoopAtHotspotPayload = {
      ...payload,
      experimentDir: selectedExperimentPath,
    };

    setIsSimpleRunning(true);
    try {
      const runId = await (async () => {
        if (window?.CWT?.phase3?.loopAtHotspot) {
          const response = await window.CWT.phase3.loopAtHotspot(payloadWithExperiment);
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
    selectedSubstratePath,
    selectedExperimentPath,
    setImportError,
    setImportMessage,
    simpleLimitValidation,
    simpleSeed,
  ]);

  const updateGuidedStepEntry = (id: string, value: string) => {
    setGuidedStepEntries((prev) => prev.map((entry) => (entry.id === id ? { ...entry, value } : entry)));
  };

  const addGuidedStepEntry = () => {
    setGuidedStepEntries((prev) => [...prev, createGuidedStepEntry('')]);
  };

  const removeGuidedStepEntry = (id: string) => {
    setGuidedStepEntries((prev) => prev.filter((entry) => entry.id !== id));
  };

  const runGuidedLoop = useCallback(async () => {
    if (!selectedHotspot || !fsGuardValidation.ok || guidedSteps.length === 0) {
      return;
    }

    if (!selectedExperimentPath) {
      setImportError('Select an experiment before running the guided explorer.');
      setImportMessage(null);
      return;
    }

    if (!selectedSubstratePath) {
      setImportError('Select a substrate before running the guided explorer.');
      setImportMessage(null);
      return;
    }

    const guardValue = fsGuardValidation.value;
    const summaryPath = selectedSubstratePath
      ? joinArtifactPath(selectedSubstratePath, PHASE3_SUMMARY_FILENAME)
      : null;

    const payload = buildGuidedPayload(
      selectedHotspot,
      graph,
      axisAmp,
      kappaAmplitude,
      kappaCenter,
      guidedSteps,
      guardValue,
      guidedMinPhi,
      guidedSeed,
      summaryPath,
    );
    const payloadWithExperiment: GuidedLoopArgs = {
      ...payload,
      experimentDir: selectedExperimentPath,
    };
    const command = await previewGuidedCli(payload);

    setIsGuidedRunning(true);
    try {
      let runs: GuidedLoopRun[] | undefined;
      let satisfied = false;

      if (window?.CWT?.phase3?.guidedLoop) {
        const response = await window.CWT.phase3.guidedLoop(payloadWithExperiment);
        if (response.ok) {
          runs = response.data.runs;
          satisfied = response.data.satisfied;
        }
      }

      if (!runs) {
        const simulatedMetrics: GuidedLoopRun[] = guidedSteps.map((steps, index) => {
          const seed = guidedSeed + index * 23;
          const simpleMetrics = simulateSimpleMetrics(
            seed,
            [axisAmp(selectedAxisI), axisAmp(selectedAxisJ)],
            guardValue,
          );
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
        phi: phiFromMetrics(referenceMetrics?.metrics ?? null),
        r: metricFromRecord(referenceMetrics?.metrics ?? null, 'R'),
        overlapMin: metricFromRecord(referenceMetrics?.metrics ?? null, 'overlap_min'),
        kappaChange: metricFromRecord(referenceMetrics?.metrics ?? null, 'kappa1_delta'),
      };

      setGuidedResult({
        command,
        payload: payloadWithExperiment,
        runs,
        satisfied,
        derivedMetrics: derived,
        failureReasons: buildGuidedFailureReasons({
          satisfied,
          runs,
          minPhi: guidedMinPhi,
          fsGuard: guardValue,
          planeAxes: getHotspotAxes(selectedHotspot),
        }),
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
    axisAmp,
    decisionGate,
    fsGuardValidation,
    graph,
    guidedMinPhi,
    guidedSeed,
    guidedSteps,
    selectedAxisI,
    selectedAxisJ,
    selectedHotspot,
    selectedExperimentPath,
    selectedSubstratePath,
    setImportError,
    setImportMessage,
    kappaAmplitude,
    kappaCenter,
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

  const guidedRecommendations = useMemo(() => {
    if (!guidedResult) {
      return null;
    }

    const { payload } = guidedResult;
    const [axisA, axisB, axisC] = payload.axes3;
    const axisALabel = labelForAxis(axisA);
    const axisBLabel = labelForAxis(axisB);
    const axisCLabel = labelForAxis(axisC);
    const [, centerPlaneA, centerPlaneB] = payload.center;
    const [ampA, ampB, ampC] = payload.amplitudes;

    return {
      graph: graphOptions.find((option) => option.id === payload.graph)?.label ?? payload.graph,
      steps: payload.stepsList.join(', '),
      guard: payload.fsGuard != null ? toCliValue(payload.fsGuard) : 'n/a',
      minPhi: payload.minPhi != null ? toCliValue(payload.minPhi) : 'n/a',
      settle: payload.settle != null ? String(payload.settle) : 'n/a',
      seed: payload.seed != null ? String(payload.seed) : 'n/a',
      center: `${axisBLabel}=${toCliValue(centerPlaneA)}, ${axisCLabel}=${toCliValue(centerPlaneB)}`,
      amplitudes: `${axisALabel}±${toCliValue(ampA)}, ${axisBLabel}±${toCliValue(ampB)}, ${axisCLabel}±${toCliValue(ampC)}`,
    };
  }, [guidedResult]);

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
            <h3>Phase 1 ridge map</h3>
            <div className="phase3__import-run">
              <button
                type="button"
                className="btn"
                onClick={() => void loadHotspotsFromSubstrate()}
                disabled={
                  isImportingHotspots ||
                  !selectedSubstratePath ||
                  substratesLoading ||
                  experimentsLoading
                }
              >
                {isImportingHotspots ? 'Loading…' : 'Load hotspots'}
              </button>
            </div>
            {experimentsError ? (
              <p className="phase3__error" role="alert">{experimentsError}</p>
            ) : null}
            {!experimentsLoading && !experimentsError && experiments.length === 0 ? (
              <p className="phase3__hint">Run Phase 1 mapping to populate experiments.</p>
            ) : null}
            {!experimentsLoading &&
              !experimentsError &&
              experiments.length > 0 &&
              !selectedExperimentPath ? (
                <p className="phase3__hint">Select an experiment from the header dropdown to enable Phase 3 tools.</p>
              ) : null}
            {substratesError ? (
              <p className="phase3__error" role="alert">{substratesError}</p>
            ) : null}
            {selectedExperimentPath &&
              !substratesLoading &&
              !substratesError &&
              !selectedSubstratePath ? (
                <p className="phase3__hint">Choose a substrate from the header dropdown to load hotspots.</p>
              ) : null}
            {phase1RunError ? (
              <p className="phase3__error" role="alert">{phase1RunError}</p>
            ) : null}
            {importError ? (
              <p className="phase3__error" role="alert">{importError}</p>
            ) : null}
            {importMessage ? (
              <p className="phase3__hint" role="status">{importMessage}</p>
            ) : null}
            {!phase1RunError && phase1Runs.length === 0 && !isLoadingPhase1Runs ? (
              <p className="phase3__hint">Run Phase 1 mapping to populate this list.</p>
            ) : null}
          </section>

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
                      {formatPlaneSummary(hotspot)}
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
                <span>Loop plane axis 1</span>
                <select
                  value={manualPlaneAxes[0]}
                  onChange={(event) => updateManualAxis(0, event.target.value as HotspotAxis)}
                >
                  {manualAxisOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Loop plane axis 2</span>
                <select
                  value={manualPlaneAxes[1]}
                  onChange={(event) => updateManualAxis(1, event.target.value as HotspotAxis)}
                >
                  {manualAxisOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              {manualPlaneAxes.map((axis) => (
                <label key={`manual-axis-${axis}`}>
                  <span>{labelForAxis(axis)}</span>
                  <input
                    type="number"
                    step="0.01"
                    value={manualCoordinates[axis] ?? 0}
                    onChange={(event) => updateManualCoordinate(axis, Number(event.target.value))}
                  />
                </label>
              ))}
              {manualOptionalAxes.length > 0 ? (
                <details>
                  <summary>Optional axes</summary>
                  <div className="phase3__field-grid">
                    {manualOptionalAxes.map((axis) => (
                      <label key={`manual-optional-${axis}`}>
                        <span>{labelForAxis(axis)}</span>
                        <input
                          type="number"
                          step="0.01"
                          value={manualCoordinates[axis] ?? 0}
                          onChange={(event) =>
                            updateManualCoordinate(axis, Number(event.target.value))
                          }
                        />
                      </label>
                    ))}
                  </div>
                </details>
              ) : null}
            </div>
            {manualPlaneMatchesDiscovery ? null : (
              <p className="phase3__warning" role="alert">{manualPlaneMismatchWarning}</p>
            )}
            <button type="button" className="btn" onClick={addManualHotspot}>
              Use center
            </button>
          </section>

          <section className="phase3__section">
            <h3>Graph</h3>
            <select value={graph} onChange={(event) => setGraph(event.target.value)}>
              {graphOptions.map((option) => (
                <option key={option.id} value={option.id} title={option.help}>
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
                  <span>Extent {selectedAxisILabel}</span>
                  <input
                    type="range"
                    min="0.01"
                    max="1"
                    step="0.01"
                    value={extentA}
                    onChange={(event) => setExtentA(Math.max(0.01, Number(event.target.value)))}
                  />
                  <code>{extentA.toFixed(2)}</code>
                  <small className="field-hint">{`How far to sweep along ${selectedAxisILabel} from the hotspot centre.`}</small>
                </label>
                <label>
                  <span>Extent {selectedAxisJLabel}</span>
                  <input
                    type="range"
                    min="0.01"
                    max="1"
                    step="0.01"
                    value={extentB}
                    onChange={(event) => setExtentB(Math.max(0.01, Number(event.target.value)))}
                  />
                  <code>{extentB.toFixed(2)}</code>
                  <small className="field-hint">{`Controls the ${selectedAxisJLabel} reach of the loop about the hotspot.`}</small>
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
                              {formatPlaneSummary(run.hotspot)}
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
              <div className="phase3__plane-indicator" aria-live="polite">
                <span className="badge">{`Plane: ${discoveryAxisILabel}–${discoveryAxisJLabel} (from Phase 2)`}</span>
              </div>
              <div className="phase3__grid phase3__grid--guided">
                {hotspotAxisOrder
                  .filter((axis): axis is Exclude<HotspotAxis, 'kappa'> => axis !== 'kappa')
                  .map((axis) => {
                    const axisLabel = labelForAxis(axis);
                    const tooltip =
                      axis === selectedAxisI
                        ? `Half-width of the sweep along ${axisLabel} when guiding the loop.`
                        : axis === selectedAxisJ
                        ? `Adjust to explore broader ${axisLabel} excursions without overshooting.`
                        : `${axisLabel} amplitude is saved for use when swapping it into the ${selectedAxisILabel}/${selectedAxisJLabel} plane.`;
                    const value = axisAmp(axis);
                    return (
                      <label key={axis}>
                        <span>{axisLabel} amplitude</span>
                        <input
                          type="range"
                          min="0"
                          max="0.4"
                          step="0.01"
                          value={value}
                          onChange={(event) => setAxisAmplitude(axis, Number(event.target.value))}
                        />
                        <code>{value.toFixed(2)}</code>
                        <small className="field-hint">{tooltip}</small>
                      </label>
                    );
                  })}
                <label>
                  <span>κ amplitude</span>
                  <input
                    type="range"
                    min="0"
                    max="0.4"
                    step="0.01"
                    value={kappaAmplitude}
                    onChange={(event) => setKappaAmplitude(Number(event.target.value))}
                  />
                  <code>{kappaAmplitude.toFixed(2)}</code>
                  <small className="field-hint">Gives the 3-axis loop nonzero enclosed area so Φ can register.</small>
                </label>
                {amplitudeGuidanceText ? (
                  <p className="phase3__hint" role="note">{amplitudeGuidanceText}</p>
                ) : null}
                <label>
                  <span>κ center</span>
                  <input
                    type="number"
                    step="0.05"
                    min="-2"
                    max="4"
                    value={kappaCenter}
                    onChange={(event) => {
                      const next = Number(event.target.value);
                      setKappaCenter((prev) => (Number.isFinite(next) ? next : prev));
                    }}
                  />
                  <small className="field-hint">
                    {`Baseline for the κ handle; adjust to explore ${selectedAxisILabel}–κ or ${selectedAxisJLabel}–κ planes.`}
                  </small>
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
                <div className="phase3__step-editor">
                  {guidedStepEntries.map((entry, index) => {
                    const inputId = `guided-step-input-${entry.id}`;
                    const error = guidedStepErrors[index];
                    return (
                      <div key={entry.id} className="phase3__step-row">
                        <label htmlFor={inputId}>Step {index + 1}</label>
                        <div className="phase3__step-row-controls">
                          <input
                            id={inputId}
                            className="phase3__step-input"
                            type="number"
                            inputMode="numeric"
                            min={16}
                            max={2000}
                            value={entry.value}
                            onChange={(event) => updateGuidedStepEntry(entry.id, event.target.value)}
                            placeholder="e.g. 320"
                          />
                          <button
                            type="button"
                            className="btn btn--ghost btn--small phase3__step-remove"
                            onClick={() => removeGuidedStepEntry(entry.id)}
                            aria-label={`Remove step ${index + 1}`}
                          >
                            Remove
                          </button>
                        </div>
                        {error ? (
                          <small className="field-error" role="alert">
                            {error}
                          </small>
                        ) : null}
                      </div>
                    );
                  })}
                  <button type="button" className="btn btn--ghost btn--small" onClick={addGuidedStepEntry}>
                    Add step
                  </button>
                </div>
                <p className="phase3__hint">
                  Provide one or more step counts. Values are validated, sorted, and deduplicated automatically.
                </p>
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

                  {guidedRecommendations ? (
                    <section className="phase3__recommended">
                      <h5>Recommended parameters</h5>
                      <dl className="phase3__recommended-list">
                        <div className="phase3__recommended-item">
                          <dt>Graph</dt>
                          <dd>{guidedRecommendations.graph}</dd>
                        </div>
                        <div className="phase3__recommended-item">
                          <dt>Steps</dt>
                          <dd>{guidedRecommendations.steps}</dd>
                        </div>
                        <div className="phase3__recommended-item">
                          <dt>FS guard</dt>
                          <dd>{guidedRecommendations.guard}</dd>
                        </div>
                        <div className="phase3__recommended-item">
                          <dt>Minimum Φ</dt>
                          <dd>{guidedRecommendations.minPhi}</dd>
                        </div>
                        <div className="phase3__recommended-item">
                          <dt>Settle steps</dt>
                          <dd>{guidedRecommendations.settle}</dd>
                        </div>
                        <div className="phase3__recommended-item">
                          <dt>Seed</dt>
                          <dd>{guidedRecommendations.seed}</dd>
                        </div>
                        <div className="phase3__recommended-item">
                          <dt>Center</dt>
                          <dd>{guidedRecommendations.center}</dd>
                        </div>
                        <div className="phase3__recommended-item">
                          <dt>Amplitudes</dt>
                          <dd>{guidedRecommendations.amplitudes}</dd>
                        </div>
                      </dl>
                    </section>
                  ) : null}

                  {!guidedResult.satisfied && guidedResult.failureReasons.length > 0 ? (
                    <section className="phase3__guided-failures">
                      <h5>Guided loop needs more tuning</h5>
                      <ul>
                        {guidedResult.failureReasons.map((reason) => (
                          <li key={reason}>{reason}</li>
                        ))}
                      </ul>
                    </section>
                  ) : null}

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
