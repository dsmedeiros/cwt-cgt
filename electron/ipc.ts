import fs from 'fs';
import path from 'path';
import {
  cmdLoopAtHotspot,
  LoopAtHotspotOptions,
  cmdAdiabaticBoundary,
  AdiabaticBoundaryOptions,
} from './runner/commands';
import { createRun } from './runner/runner';
import { guidedLoop as executeGuidedLoop, GuidedLoopOptions, GuidedLoopResult } from './runner/calibrator';

type LoopAxes = [string, string];

type LoopExtent = number;

const ARTIFACTS_ROOT = path.join(process.cwd(), 'artifacts');
const PHASE3_ROOT = path.join(ARTIFACTS_ROOT, 'phase3');
const LOOP_AT_HOTSPOT_ROOT = path.join(PHASE3_ROOT, 'loop_at_hotspot');
const GUIDED_LOOP_ROOT = path.join(PHASE3_ROOT, 'guided_loop');
const ADIABATIC_BOUNDARY_ROOT = path.join(PHASE3_ROOT, 'adiabatic_boundary');

function ensureDirectory(dirPath: string): void {
  fs.mkdirSync(dirPath, { recursive: true });
}

function createTimestampedDir(baseDir: string, prefix: string): string {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  let candidate = path.join(baseDir, `${prefix}-${timestamp}`);
  let attempt = 1;
  while (fs.existsSync(candidate)) {
    attempt += 1;
    candidate = path.join(baseDir, `${prefix}-${timestamp}-${attempt}`);
  }
  ensureDirectory(candidate);
  return candidate;
}

function normalizeAxes(value: unknown): LoopAxes {
  if (!Array.isArray(value) || value.length !== 2) {
    throw new Error('axes must be a tuple containing exactly two axis names.');
  }
  const [first, second] = value;
  if (typeof first !== 'string' || typeof second !== 'string') {
    throw new Error('axes entries must be strings.');
  }
  if (!first.trim() || !second.trim()) {
    throw new Error('axes entries must be non-empty strings.');
  }
  return [first, second];
}

function normalizeExtents(extents: unknown): LoopExtent[] {
  if (!Array.isArray(extents) || extents.length === 0) {
    throw new Error('extents must contain at least one value.');
  }
  const normalized: LoopExtent[] = [];
  for (const value of extents) {
    const numberValue = typeof value === 'string' ? Number.parseFloat(value) : value;
    if (typeof numberValue !== 'number' || !Number.isFinite(numberValue)) {
      throw new Error('extents must contain finite numeric values.');
    }
    normalized.push(numberValue);
  }
  return normalized;
}

function resolveOutDir(requested: string | undefined, baseDir: string, prefix: string): string {
  if (requested) {
    if (typeof requested !== 'string' || !requested.trim()) {
      throw new Error('outDir must be a non-empty string when provided.');
    }
    const resolved = path.resolve(requested);
    ensureDirectory(resolved);
    return resolved;
  }
  ensureDirectory(baseDir);
  return createTimestampedDir(baseDir, prefix);
}

function writeHotspotsFile(dir: string, payload: unknown, sourceText: string): string {
  const hotspotsPath = path.join(dir, 'hotspots.json');
  let serialized = sourceText;
  try {
    serialized = JSON.stringify(payload, null, 2);
  } catch (error) {
    // Fallback to original text if serialization fails.
    serialized = sourceText;
  }
  fs.writeFileSync(hotspotsPath, `${serialized}\n`, 'utf8');
  return hotspotsPath;
}

function parseHotspotsJson(hotspotsJson: unknown): unknown {
  if (typeof hotspotsJson !== 'string' || !hotspotsJson.trim()) {
    throw new Error('hotspotsJson must be a non-empty JSON string.');
  }
  try {
    return JSON.parse(hotspotsJson);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`Unable to parse hotspotsJson: ${message}`);
  }
}

function assertPythonExe(pythonExe: unknown): asserts pythonExe is string {
  if (typeof pythonExe !== 'string' || !pythonExe.trim()) {
    throw new Error('A pythonExe string must be provided.');
  }
}

function normalizeOptionalNumber(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number.parseFloat(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return undefined;
}

export interface LoopAtHotspotPayload {
  pythonExe: string;
  hotspotsJson: string;
  axes: LoopAxes;
  extents: Array<number | string>;
  fsGuard?: number | string;
  graph?: string;
  limit?: number | string;
  seed?: number | string;
  strategy?: LoopAtHotspotOptions['strategy'];
  outDir?: string;
}

export interface LoopAtHotspotResult {
  runId: string;
  workdir: string;
  hotspotsPath: string;
}

export async function loopAtHotspot(payload: LoopAtHotspotPayload): Promise<LoopAtHotspotResult> {
  assertPythonExe(payload.pythonExe);
  const axes = normalizeAxes(payload.axes);
  const extents = normalizeExtents(payload.extents);
  const hotspotsParsed = parseHotspotsJson(payload.hotspotsJson);
  const workdir = resolveOutDir(payload.outDir, LOOP_AT_HOTSPOT_ROOT, 'loop-at-hotspot');
  const hotspotsPath = writeHotspotsFile(workdir, hotspotsParsed, payload.hotspotsJson);

  const fsGuard = normalizeOptionalNumber(payload.fsGuard);
  const limit = normalizeOptionalNumber(payload.limit);
  const seed = normalizeOptionalNumber(payload.seed);

  const command = cmdLoopAtHotspot(payload.pythonExe, {
    hotspots: hotspotsPath,
    axes,
    extents,
    fsGuard,
    graph: payload.graph,
    limit,
    seed,
    strategy: payload.strategy,
  });

  const paramsJson = {
    axes,
    extents,
    fsGuard: typeof fsGuard === 'number' ? fsGuard : null,
    graph: payload.graph ?? null,
    limit: typeof limit === 'number' ? limit : null,
    seed: typeof seed === 'number' ? seed : null,
    hotspotsPath,
  };

  const runId = createRun({
    phase: 'phase3',
    experiment: 'loop_at_hotspot',
    cmd: command.cmd,
    args: command.args,
    cwd: command.cwd,
    seed: typeof seed === 'number' ? seed : undefined,
    paramsJson,
  });

  return { runId, workdir, hotspotsPath };
}

export interface GuidedLoopArgs extends Omit<GuidedLoopOptions, 'outDir'> {
  outDir?: string;
}

export function guidedLoop(payload: GuidedLoopArgs): GuidedLoopResult {
  assertPythonExe(payload.pythonExe);
  const outDir = resolveOutDir(payload.outDir, GUIDED_LOOP_ROOT, 'guided-loop');
  const { outDir: _ignored, ...rest } = payload;
  const options: GuidedLoopOptions = { ...rest, outDir };
  return executeGuidedLoop(options);
}

export interface AdiabaticBoundaryPayload extends Pick<LoopAtHotspotPayload, 'pythonExe' | 'outDir'> {
  strategy?: AdiabaticBoundaryOptions['strategy'];
}

export interface AdiabaticBoundaryResult {
  runId: string;
  workdir: string;
}

export async function adiabaticBoundary(payload: AdiabaticBoundaryPayload): Promise<AdiabaticBoundaryResult> {
  assertPythonExe(payload.pythonExe);
  const workdir = resolveOutDir(payload.outDir, ADIABATIC_BOUNDARY_ROOT, 'adiabatic-boundary');

  const command = cmdAdiabaticBoundary(payload.pythonExe, {
    outDir: workdir,
    strategy: payload.strategy,
  });

  const runId = createRun({
    phase: 'phase3',
    experiment: 'adiabatic_boundary',
    cmd: command.cmd,
    args: command.args,
    cwd: command.cwd,
    paramsJson: {
      outDir: workdir,
    },
  });

  return { runId, workdir };
}
