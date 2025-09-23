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
const scriptPath = path.join('cwt-sim', 'experiments', 'gateB_ridge_finder', 'run.py');

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
    args.push(scriptPath);
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
