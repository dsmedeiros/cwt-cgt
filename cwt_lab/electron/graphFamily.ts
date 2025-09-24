import { spawn } from 'node:child_process';
import { promises as fs } from 'node:fs';
import path from 'node:path';

import type { GraphFamilyCommandResult } from '../renderer/types/ipc';
import type { PythonStrategy } from './runner/env';

type GraphFamilyCommandParams = {
  families: string[];
  axes: [string, string];
  gridSize: number;
  extents: number;
  seed: number;
  outDir: string;
  strategy: PythonStrategy;
};

type RawFamilyEntry = {
  name: string;
  degree_entropy?: number | null;
  clustering?: number | null;
  modularity?: number | null;
  peak_abs_omega?: number | null;
  kappa_mean?: number | null;
  ridge_auc?: number | null;
  phi_missing?: boolean;
  phi_flux?: number | null;
  phi_flux_missing?: boolean;
  fs_p95?: number | null;
  fs_boundary?: number | null;
  fs_exceeded?: boolean;
  fs_guard_enabled?: boolean;
  median_abs_omega?: number | null;
  runtime_seconds?: number | null;
  thumbnail?: string | null;
};

const repoRoot = path.resolve(__dirname, '..', '..');
const cwtSimRoot = path.join(repoRoot, 'cwt-sim');

const toNumber = (value: unknown): number | null => {
  if (value == null) {
    return null;
  }
  const numeric = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(numeric) || !Number.isFinite(numeric)) {
    return null;
  }
  return numeric;
};

const ensureUniquePath = async (dir: string) => {
  await fs.mkdir(dir, { recursive: true });
};

const buildPythonPath = (strategy: PythonStrategy): string | undefined => {
  const parts = new Set<string>();
  const existing = process.env.PYTHONPATH;
  if (existing) {
    for (const segment of existing.split(path.delimiter)) {
      const trimmed = segment.trim();
      if (trimmed.length > 0) {
        parts.add(trimmed);
      }
    }
  }

  if (strategy === 'py_path') {
    parts.add(cwtSimRoot);
  }

  const values = Array.from(parts);
  if (values.length === 0) {
    return undefined;
  }
  return values.join(path.delimiter);
};

const collectOutput = (buffer: string, chunk: Buffer) => buffer + chunk.toString('utf-8');

const toDataUrl = (buffer: Buffer) => `data:image/png;base64,${buffer.toString('base64')}`;

export const cmdGraphFamily = async (
  pythonExe: string,
  params: GraphFamilyCommandParams,
): Promise<GraphFamilyCommandResult> => {
  await ensureUniquePath(params.outDir);

  const args = [
    '-m',
    'experiments.graph_family.run',
    '--families',
    params.families.join(','),
    '--axes',
    params.axes[0],
    params.axes[1],
    '--grid-size',
    String(params.gridSize),
    '--extents',
    String(params.extents),
    '--seed',
    String(params.seed),
    '--out-dir',
    params.outDir,
  ];

  const pythonPath = buildPythonPath(params.strategy);
  const env: NodeJS.ProcessEnv = {
    ...process.env,
    PYTHONUNBUFFERED: '1',
  };
  if (pythonPath) {
    env.PYTHONPATH = pythonPath;
  }

  let stdout = '';
  let stderr = '';

  await new Promise<void>((resolve, reject) => {
    const child = spawn(pythonExe, args, {
      cwd: cwtSimRoot,
      env,
    });

    child.stdout.on('data', (chunk: Buffer) => {
      stdout = collectOutput(stdout, chunk);
    });

    child.stderr.on('data', (chunk: Buffer) => {
      stderr = collectOutput(stderr, chunk);
    });

    child.on('error', (error) => {
      reject(error);
    });

    child.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        const error = new Error(
          `graph-family command failed with exit code ${code ?? 'unknown'}`,
        );
        (error as Error & { stdout?: string; stderr?: string }).stdout = stdout;
        (error as Error & { stdout?: string; stderr?: string }).stderr = stderr;
        reject(error);
      }
    });
  });

  const summaryPath = path.join(params.outDir, 'summary.json');
  const raw = await fs.readFile(summaryPath, 'utf-8');
  const parsed = JSON.parse(raw) as {
    families?: RawFamilyEntry[];
    axes?: [string, string];
    extent?: number;
    grid_size?: number;
    seed?: number;
    runtime_seconds?: number | null;
  };

  const families: GraphFamilyCommandResult['families'] = [];
  for (const entry of parsed.families ?? []) {
    const name = typeof entry.name === 'string' && entry.name.trim().length > 0
      ? entry.name
      : 'unknown';
    const thumbnailPath = entry.thumbnail ? path.join(params.outDir, entry.thumbnail) : null;
    let thumbnailDataUrl: string | null = null;
    if (thumbnailPath) {
      try {
        const buffer = await fs.readFile(thumbnailPath);
        thumbnailDataUrl = toDataUrl(buffer);
      } catch {
        thumbnailDataUrl = null;
      }
    }

    const phiFlux = toNumber(entry.phi_flux);
    const guardEnabled = Boolean(entry.fs_guard_enabled);
    const fsExceeded = Boolean(entry.fs_exceeded);
    const phiGuardOk = guardEnabled && !fsExceeded && phiFlux != null;

    families.push({
      name,
      degreeEntropy: toNumber(entry.degree_entropy),
      clustering: toNumber(entry.clustering),
      modularity: toNumber(entry.modularity),
      peakAbsOmega: toNumber(entry.peak_abs_omega),
      kappaMean: toNumber(entry.kappa_mean),
      ridgeAuc: toNumber(entry.ridge_auc),
      phiMissing: Boolean(entry.phi_missing),
      phiFlux,
      phiFluxMissing: Boolean(entry.phi_flux_missing),
      phiGuardOk,
      fsP95: toNumber(entry.fs_p95),
      fsBoundary: toNumber(entry.fs_boundary),
      fsExceeded,
      medianAbsOmega: toNumber(entry.median_abs_omega),
      thumbnail: thumbnailPath
        ? { name: path.basename(thumbnailPath), path: thumbnailPath, dataUrl: thumbnailDataUrl }
        : null,
    });
  }

  return {
    outputDir: params.outDir,
    summaryPath,
    stdout,
    stderr,
    axes: Array.isArray(parsed.axes) && parsed.axes.length === 2 ? parsed.axes : params.axes,
    extent: parsed.extent ?? params.extents,
    gridSize: parsed.grid_size ?? params.gridSize,
    seed: parsed.seed ?? params.seed,
    runtimeSeconds: toNumber(parsed.runtime_seconds),
    families,
  } satisfies GraphFamilyCommandResult;
};

export type { GraphFamilyCommandResult };
