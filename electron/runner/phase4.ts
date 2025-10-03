import path from 'path';

export type Wilson3DOptions = {
  axes3: [string, string, string];
  center: [number, number, number];
  amplitudes: [number, number, number];
  steps: number;
  handleSteps?: number;
  settle?: number;
  fsGuard?: number;
  graph?: string;
  seed?: number;
  etaQ?: number;
  zeta?: number;
  omegaScale?: number;
  outDir?: string;
  phase3Summary?: string;
  hotspotIndex?: number;
  extentIndex?: number;
  strategy?: 'module' | 'script';
};

export type TorusPlateauAxisConfig =
  | { axis: string; center: number; extent: number }
  | { axis?: string; center: number; extent: number };

export type TorusPlateauOptions = {
  axes: [string, string];
  gridSize?: number;
  disorderList?: number[];
  centersExtents:
    | TorusPlateauAxisConfig[]
    | Record<string, { center: number; extent: number } | TorusPlateauAxisConfig>;
  outDir?: string;
  strategy?: 'module' | 'script';
};

export type CommandSpec = {
  command: string;
  args: string[];
};

const formatNumber = (value: number) => {
  if (!Number.isFinite(value)) {
    throw new Error(`Invalid numeric value: ${value}`);
  }
  const fixed = Number.parseFloat(value.toFixed(6));
  return Number.isFinite(fixed) ? fixed.toString() : value.toString();
};

const resolveEntrypoint = (strategy: 'module' | 'script' | undefined, moduleName: string, scriptPath: string) => {
  if (strategy === 'script') {
    return [scriptPath];
  }
  return ['-m', moduleName];
};

export const cmdWilson3D = (pythonExe: string, options: Wilson3DOptions): CommandSpec => {
  const { axes3, center, amplitudes, steps } = options;
  if (!pythonExe) {
    throw new Error('pythonExe is required');
  }
  if (!Array.isArray(axes3) || axes3.length !== 3) {
    throw new Error('axes3 must contain exactly three entries');
  }
  if (center.length !== 3) {
    throw new Error('center must contain three numeric entries');
  }
  if (amplitudes.length !== 3) {
    throw new Error('amplitudes must contain three numeric entries');
  }
  if (!Number.isInteger(steps) || steps <= 0) {
    throw new Error('steps must be a positive integer');
  }

  const entrypoint = resolveEntrypoint(
    options.strategy,
    'experiments.wilson_loop_3d.run',
    path.join(__dirname, '..', '..', 'cwt-sim', 'experiments', 'wilson_loop_3d', 'run.py'),
  );

  if (options.strategy && options.strategy !== 'module' && options.strategy !== 'script') {
    throw new Error(`Unsupported strategy: ${options.strategy}`);
  }

  const args: string[] = [
    ...entrypoint,
    '--axes3',
    ...axes3.map((axis) => {
      if (!axis || typeof axis !== 'string' || axis.trim().length === 0) {
        throw new Error('axes3 entries must be non-empty strings');
      }
      return axis.trim();
    }),
    '--center',
    ...center.map(formatNumber),
    '--amplitudes',
    ...amplitudes.map(formatNumber),
    '--steps',
    steps.toString(),
  ];

  if (options.handleSteps != null) {
    if (!Number.isInteger(options.handleSteps) || options.handleSteps <= 0) {
      throw new Error('handleSteps must be a positive integer when provided');
    }
    args.push('--handle-steps', options.handleSteps.toString());
  }
  if (options.settle != null) {
    if (!Number.isInteger(options.settle) || options.settle <= 0) {
      throw new Error('settle must be a positive integer when provided');
    }
    args.push('--settle', options.settle.toString());
  }
  if (options.fsGuard != null) {
    args.push('--fs-guard', formatNumber(options.fsGuard));
  }
  if (options.graph) {
    args.push('--graph', options.graph);
  }
  if (options.seed != null) {
    if (!Number.isInteger(options.seed)) {
      throw new Error('seed must be an integer when provided');
    }
    args.push('--seed', options.seed.toString());
  }
  if (options.etaQ != null) {
    args.push('--eta-q', formatNumber(options.etaQ));
  }
  if (options.zeta != null) {
    args.push('--zeta', formatNumber(options.zeta));
  }
  if (options.omegaScale != null) {
    args.push('--omega-scale', formatNumber(options.omegaScale));
  }
  if (options.outDir) {
    args.push('--output-dir', options.outDir);
  }
  if (options.phase3Summary) {
    args.push('--phase3-summary', options.phase3Summary);
  }
  if (options.hotspotIndex != null) {
    if (!Number.isInteger(options.hotspotIndex) || options.hotspotIndex < 0) {
      throw new Error('hotspotIndex must be a non-negative integer when provided');
    }
    args.push('--hotspot-index', options.hotspotIndex.toString());
  }
  if (options.extentIndex != null) {
    if (!Number.isInteger(options.extentIndex) || options.extentIndex < 0) {
      throw new Error('extentIndex must be a non-negative integer when provided');
    }
    args.push('--extent-index', options.extentIndex.toString());
  }

  return {
    command: pythonExe,
    args,
  };
};

const toAxisConfigMap = (
  input: TorusPlateauOptions['centersExtents'],
): Map<string, { center: number; extent: number }> => {
  const map = new Map<string, { center: number; extent: number }>();
  if (Array.isArray(input)) {
    input.forEach((entry) => {
      const axisName = (entry as { axis?: string }).axis;
      if (axisName) {
        map.set(axisName, { center: entry.center, extent: entry.extent });
      }
    });
  } else {
    for (const [axis, value] of Object.entries(input)) {
      if (value && typeof value === 'object') {
        const { center, extent } = value as { center: number; extent: number };
        map.set(axis, { center, extent });
      }
    }
  }
  return map;
};

const TORUS_DEFAULTS: [
  { center: number; extent: number },
  { center: number; extent: number },
] = [
  { center: 0.28, extent: 0.22 },
  { center: 0.5, extent: 0.5 },
];

export const cmdTorusPlateau = (pythonExe: string, options: TorusPlateauOptions): CommandSpec => {
  if (!pythonExe) {
    throw new Error('pythonExe is required');
  }
  const { axes, gridSize, disorderList, centersExtents, outDir } = options;
  if (!Array.isArray(axes) || axes.length !== 2) {
    throw new Error('axes must contain exactly two entries');
  }

  if (options.strategy && options.strategy !== 'module' && options.strategy !== 'script') {
    throw new Error(`Unsupported strategy: ${options.strategy}`);
  }

  const entrypoint = resolveEntrypoint(
    options.strategy,
    'experiments.torus_plateau.run',
    path.join(__dirname, '..', '..', 'cwt-sim', 'experiments', 'torus_plateau', 'run.py'),
  );

  const axisConfig = toAxisConfigMap(centersExtents);
  const primary = axisConfig.get(axes[0]) ?? TORUS_DEFAULTS[0];
  const secondary = axisConfig.get(axes[1]) ?? TORUS_DEFAULTS[1];

  const args: string[] = [
    ...entrypoint,
    '--axes',
    axes[0],
    axes[1],
  ];

  if (gridSize != null) {
    if (!Number.isInteger(gridSize) || gridSize <= 0) {
      throw new Error('gridSize must be a positive integer when provided');
    }
    args.push('--grid-size', gridSize.toString());
  }

  const disorders = (disorderList && disorderList.length > 0 ? disorderList : [0.0, 0.02, 0.05]).map((value) => {
    if (!Number.isFinite(value)) {
      throw new Error('disorder values must be numeric');
    }
    return formatNumber(value);
  });

  args.push('--disorder', ...disorders);
  args.push('--tau-center', formatNumber(primary.center));
  args.push('--tau-extent', formatNumber(primary.extent));
  args.push('--zeta-center', formatNumber(secondary.center));
  args.push('--zeta-extent', formatNumber(secondary.extent));

  if (outDir) {
    args.push('--output-dir', outDir);
  }

  return {
    command: pythonExe,
    args,
  };
};
