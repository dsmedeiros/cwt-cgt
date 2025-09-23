import path from 'path';

type RangeTuple = [number, number];

export interface GateBRidgeFinderRanges {
  rho?: RangeTuple;
  tau?: RangeTuple;
  zeta?: RangeTuple;
  zetaPhase?: RangeTuple;
}

export interface GateBRidgeFinderOptions {
  axes: [string, string];
  gridSize?: number;
  ranges?: GateBRidgeFinderRanges;
  graphs?: string[] | string;
  bootstrap?: number;
  topK?: number;
  seed?: number;
  outDir?: string;
  strategy?: 'module' | 'script';
}

export interface CommandSpec {
  cmd: string;
  args: string[];
  cwd: string;
}

const repoRoot = path.resolve(__dirname, '..', '..');
const simRoot = path.join(repoRoot, 'cwt-sim');
const gateBRidgeFinderScriptPath = path.join(
  'cwt-sim',
  'experiments',
  'gateB_ridge_finder',
  'run.py'
);
const loopAtHotspotScriptPath = path.join(
  'cwt-sim',
  'experiments',
  'loop_at_hotspot',
  'run.py'
);
const wilson3DScriptPath = path.join(
  'cwt-sim',
  'experiments',
  'wilson_loop_3d',
  'run.py'
);
const adiabaticBoundaryScriptPath = path.join(
  'cwt-sim',
  'experiments',
  'adiabatic_boundary',
  'run.py'
);

export interface LoopAtHotspotOptions {
  hotspots: string;
  axes?: [string, string];
  extents: Array<number | string>;
  fsGuard?: number;
  graph?: string;
  limit?: number;
  seed?: number;
  strategy?: 'module' | 'script';
}

export interface Wilson3DOptions {
  axes3?: [string, string, string];
  center?: Array<number | string>;
  amplitudes?: Array<number | string>;
  steps?: number;
  handleSteps?: number;
  settle?: number;
  fsGuard?: number;
  graph?: string;
  seed?: number;
  outDir?: string;
  strategy?: 'module' | 'script';
}

export interface AdiabaticBoundaryOptions {
  outDir?: string;
  strategy?: 'module' | 'script';
}

export function cmdGateBRidgeFinder(
  pythonExe: string,
  { axes, gridSize, ranges, graphs, bootstrap, topK, seed, outDir, strategy }: GateBRidgeFinderOptions
): CommandSpec {
  if (!Array.isArray(axes) || axes.length !== 2) {
    throw new Error('axes must be a tuple of two axis names');
  }

  const args: string[] = [];

  if (strategy === 'module') {
    args.push('-m', 'experiments.gateB_ridge_finder.run');
  } else {
    args.push(gateBRidgeFinderScriptPath);
  }

  args.push('--axes', axes[0], axes[1]);

  if (typeof gridSize === 'number') {
    args.push('--grid-size', String(gridSize));
  }

  const rangeFlags: Array<[keyof GateBRidgeFinderRanges, string]> = [
    ['rho', '--rho-range'],
    ['tau', '--tau-range'],
    ['zeta', '--zeta-range'],
    ['zetaPhase', '--zeta-phase-range'],
  ];

  if (ranges) {
    for (const [key, flag] of rangeFlags) {
      const value = ranges[key];
      if (value) {
        const [start, end] = value;
        args.push(flag, String(start), String(end));
      }
    }
  }

  if (typeof graphs !== 'undefined') {
    const graphsValue = Array.isArray(graphs) ? graphs.join(',') : graphs;
    args.push('--graphs', graphsValue);
  }

  if (typeof bootstrap === 'number') {
    args.push('--bootstrap', String(bootstrap));
  }

  if (typeof topK === 'number') {
    args.push('--top-k', String(topK));
  }

  if (typeof seed === 'number') {
    args.push('--seed', String(seed));
  }

  if (typeof outDir === 'string') {
    args.push('--output-dir', outDir);
  }

  return {
    cmd: pythonExe,
    args,
    cwd: strategy === 'module' ? simRoot : repoRoot,
  };
}

export function cmdLoopAtHotspot(
  pythonExe: string,
  { hotspots, axes, extents, fsGuard, graph, limit, seed, strategy }: LoopAtHotspotOptions
): CommandSpec {
  if (typeof hotspots !== 'string' || hotspots.length === 0) {
    throw new Error('hotspots must be a non-empty string path');
  }

  if (!Array.isArray(extents) || extents.length === 0) {
    throw new Error('extents must be a non-empty array of values');
  }

  if (axes && (!Array.isArray(axes) || axes.length !== 2)) {
    throw new Error('axes must be a tuple of two axis names');
  }

  const args: string[] = [];

  if (strategy === 'module') {
    args.push('-m', 'experiments.loop_at_hotspot.run');
  } else {
    args.push(loopAtHotspotScriptPath);
  }

  args.push('--hotspots', hotspots);
  args.push('--extents', ...extents.map((value) => String(value)));

  if (axes) {
    args.push('--axes', axes[0], axes[1]);
  }

  if (typeof graph === 'string') {
    args.push('--graph', graph);
  }

  if (typeof fsGuard === 'number') {
    args.push('--fs-guard', String(fsGuard));
  }

  if (typeof limit === 'number') {
    args.push('--limit', String(limit));
  }

  if (typeof seed === 'number') {
    args.push('--seed', String(seed));
  }

  return {
    cmd: pythonExe,
    args,
    cwd: strategy === 'module' ? simRoot : repoRoot,
  };
}

export function cmdWilson3D(
  pythonExe: string,
  {
    axes3,
    center,
    amplitudes,
    steps,
    handleSteps,
    settle,
    fsGuard,
    graph,
    seed,
    outDir,
    strategy,
  }: Wilson3DOptions
): CommandSpec {
  if (axes3 && (!Array.isArray(axes3) || axes3.length !== 3)) {
    throw new Error('axes3 must be a tuple of three axis names');
  }

  if (center && center.length !== 3) {
    throw new Error('center must contain three coordinate values');
  }

  if (amplitudes && amplitudes.length !== 3) {
    throw new Error('amplitudes must contain three values');
  }

  const args: string[] = [];

  if (strategy === 'module') {
    args.push('-m', 'experiments.wilson_loop_3d.run');
  } else {
    args.push(wilson3DScriptPath);
  }

  if (axes3) {
    args.push('--axes3', ...axes3.map((axis) => String(axis)));
  }

  if (center) {
    args.push('--center', ...center.map((value) => String(value)));
  }

  if (amplitudes) {
    args.push('--amplitudes', ...amplitudes.map((value) => String(value)));
  }

  if (typeof steps === 'number') {
    args.push('--steps', String(steps));
  }

  if (typeof handleSteps === 'number') {
    args.push('--handle-steps', String(handleSteps));
  }

  if (typeof settle === 'number') {
    args.push('--settle', String(settle));
  }

  if (typeof graph === 'string') {
    args.push('--graph', graph);
  }

  if (typeof seed === 'number') {
    args.push('--seed', String(seed));
  }

  if (typeof fsGuard === 'number') {
    args.push('--fs-guard', String(fsGuard));
  }

  if (typeof outDir === 'string') {
    args.push('--output-dir', outDir);
  }

  return {
    cmd: pythonExe,
    args,
    cwd: strategy === 'module' ? simRoot : repoRoot,
  };
}

export function cmdAdiabaticBoundary(
  pythonExe: string,
  { outDir, strategy }: AdiabaticBoundaryOptions
): CommandSpec {
  const args: string[] = [];

  if (strategy === 'module') {
    args.push('-m', 'experiments.adiabatic_boundary.run');
  } else {
    args.push(adiabaticBoundaryScriptPath);
  }

  if (typeof outDir === 'string') {
    args.push('--output-dir', outDir);
  }

  return {
    cmd: pythonExe,
    args,
    cwd: strategy === 'module' ? simRoot : repoRoot,
  };
}
