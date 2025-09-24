import { spawn } from 'node:child_process';
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { parse as parseYaml, stringify as stringifyYaml } from 'yaml';

import type { PythonStrategy } from './runner/env';

export type CouplingVariantRequest = {
  configPath: string;
  betas: number[];
  etaQ?: number | number[];
  outDir: string;
  strategy: PythonStrategy;
};

export type CouplingVariantSummary = {
  beta: number;
  etaQ: number | null;
  phi: number | null;
  phiMissing: boolean;
  rValue: number | null;
  fsP95: number | null;
  fsBoundary: number | null;
  guardExceeded: boolean;
  runId: string;
  variantConfig: string;
  runDir: string;
};

export type CouplingTunerResult = {
  outputDir: string;
  baselineConfig: string;
  variants: CouplingVariantSummary[];
  bestIndex: number | null;
};

const repoRoot = path.resolve(__dirname, '..', '..');
const cwtSimRoot = path.join(repoRoot, 'cwt-sim');

const ensureDir = async (dir: string) => {
  await fs.mkdir(dir, { recursive: true });
};

const buildPythonPath = (strategy: PythonStrategy): string | undefined => {
  const entries = new Set<string>();
  const current = process.env.PYTHONPATH ?? '';
  if (current) {
    for (const part of current.split(path.delimiter)) {
      const trimmed = part.trim();
      if (trimmed.length > 0) {
        entries.add(trimmed);
      }
    }
  }

  if (strategy === 'py_path') {
    entries.add(cwtSimRoot);
  }

  const values = Array.from(entries);
  if (values.length === 0) {
    return undefined;
  }
  return values.join(path.delimiter);
};

const normalizeEtaQ = (etaQ: number | number[] | undefined, index: number): number | null => {
  if (etaQ == null) {
    return null;
  }
  if (Array.isArray(etaQ)) {
    if (etaQ.length === 0) {
      return null;
    }
    const clamped = etaQ[Math.min(index, etaQ.length - 1)];
    return Number.isFinite(clamped) ? Number(clamped) : null;
  }
  return Number.isFinite(etaQ) ? Number(etaQ) : null;
};

const mutateConfig = (
  base: Record<string, unknown>,
  beta: number,
  etaQ: number | null,
): Record<string, unknown> => {
  const clone = JSON.parse(JSON.stringify(base)) as Record<string, unknown>;
  const coupling =
    typeof clone.geometric_coupling === 'object' && clone.geometric_coupling !== null
      ? (clone.geometric_coupling as Record<string, unknown>)
      : {};
  coupling.beta = beta;
  clone.geometric_coupling = coupling;

  if (etaQ != null) {
    const dynamics =
      typeof clone.dynamics === 'object' && clone.dynamics !== null
        ? (clone.dynamics as Record<string, unknown>)
        : {};
    dynamics.eta_q = etaQ;
    clone.dynamics = dynamics;
  }

  return clone;
};

const readMeta = async (runDir: string) => {
  const metaPath = path.join(runDir, 'meta.json');
  const raw = await fs.readFile(metaPath, 'utf-8');
  return JSON.parse(raw) as Record<string, unknown>;
};

const computePhi = (meta: Record<string, unknown>): { value: number | null; missing: boolean } => {
  const omegaTiles = Array.isArray(meta.omega_tiles) ? (meta.omega_tiles as Record<string, unknown>[]) : [];
  let phi = 0;
  let seen = false;
  for (const tile of omegaTiles) {
    const omega = Number(tile.omega);
    const area = Number(tile.tile_area);
    if (Number.isFinite(omega) && Number.isFinite(area)) {
      seen = true;
      phi += omega * area;
    }
  }
  const missing = !seen;
  return { value: seen ? phi : null, missing };
};

const lastFinite = (values: number[]): number | null => {
  for (let index = values.length - 1; index >= 0; index -= 1) {
    const value = values[index];
    if (Number.isFinite(value)) {
      return value;
    }
  }
  return null;
};

const computeRValue = (meta: Record<string, unknown>): number | null => {
  const overlaps = Array.isArray(meta.overlaps_min)
    ? (meta.overlaps_min as unknown[]).map((entry) => Number(entry)).filter((entry) => Number.isFinite(entry))
    : [];
  return overlaps.length > 0 ? lastFinite(overlaps) : null;
};

const computeFs = (meta: Record<string, unknown>) => {
  const guard =
    typeof meta.meta === 'object' && meta.meta !== null
      ? (meta.meta as Record<string, unknown>).fs_step_guard
      : undefined;
  if (!guard || typeof guard !== 'object') {
    return { boundary: null, p95: null, exceeded: false };
  }
  const boundary = Number((guard as Record<string, unknown>).boundary);
  const p95 = Number((guard as Record<string, unknown>).p95);
  const exceeded = Boolean((guard as Record<string, unknown>).boundary_exceeded);
  return {
    boundary: Number.isFinite(boundary) ? boundary : null,
    p95: Number.isFinite(p95) ? p95 : null,
    exceeded,
  };
};

export const runCouplingTuner = async (
  pythonExe: string,
  options: CouplingVariantRequest,
): Promise<CouplingTunerResult> => {
  if (!pythonExe) {
    throw new Error('pythonExe is required');
  }
  if (!options.configPath) {
    throw new Error('configPath is required');
  }
  if (!Array.isArray(options.betas) || options.betas.length === 0) {
    throw new Error('betas must contain at least one numeric value');
  }

  const baselinePath = path.resolve(options.configPath);
  const baselineRaw = await fs.readFile(baselinePath, 'utf-8');
  const baselineConfig = parseYaml(baselineRaw) as Record<string, unknown>;

  await ensureDir(options.outDir);
  const baselineCopy = path.join(options.outDir, path.basename(baselinePath));
  await fs.writeFile(baselineCopy, baselineRaw, 'utf-8');

  const pythonPath = buildPythonPath(options.strategy);
  const env: NodeJS.ProcessEnv = {
    ...process.env,
    PYTHONUNBUFFERED: '1',
  };
  if (pythonPath) {
    env.PYTHONPATH = pythonPath;
  }

  const variants: CouplingVariantSummary[] = [];

  for (let index = 0; index < options.betas.length; index += 1) {
    const beta = Number(options.betas[index]);
    if (!Number.isFinite(beta)) {
      throw new Error('betas must contain only numeric entries');
    }
    const etaQ = normalizeEtaQ(options.etaQ, index);
    const mutated = mutateConfig(baselineConfig, beta, etaQ);
    const variantName = `beta_${beta.toFixed(3)}${etaQ != null ? `_eta_${etaQ.toFixed(3)}` : ''}`;
    const variantPath = path.join(options.outDir, `${variantName}.yaml`);
    await fs.writeFile(variantPath, stringifyYaml(mutated), 'utf-8');

    const args = ['-m', 'scripts.run_loop', '--config', variantPath, '--out', options.outDir];
    const result = await new Promise<{ runId: string; runDir: string }>((resolve, reject) => {
      let stdout = '';
      let stderr = '';
      const child = spawn(pythonExe, args, { cwd: cwtSimRoot, env });
      child.stdout.on('data', (chunk: Buffer) => {
        stdout += chunk.toString('utf-8');
      });
      child.stderr.on('data', (chunk: Buffer) => {
        stderr += chunk.toString('utf-8');
      });
      child.on('error', (error) => reject(error));
      child.on('close', (code) => {
        if (code !== 0) {
          const err = new Error(`run_loop failed with exit code ${code ?? 'unknown'}`);
          (err as Error & { stdout?: string }).stdout = stdout;
          (err as Error & { stderr?: string }).stderr = stderr;
          reject(err);
          return;
        }
        const lines = stdout.trim().split(/\r?\n/);
        const payloadRaw = lines[lines.length - 1];
        try {
          const payload = JSON.parse(payloadRaw) as { run_id: string; out_dir: string };
          resolve({ runId: payload.run_id, runDir: payload.out_dir });
        } catch (error) {
          reject(new Error(`Unable to parse run_loop output: ${payloadRaw}`));
        }
      });
    });

    const meta = await readMeta(result.runDir);
    const phi = computePhi(meta);
    const fsMetrics = computeFs(meta);
    const rValue = computeRValue(meta);

    variants.push({
      beta,
      etaQ,
      phi: phi.value,
      phiMissing: phi.missing,
      rValue,
      fsP95: fsMetrics.p95,
      fsBoundary: fsMetrics.boundary,
      guardExceeded: fsMetrics.exceeded,
      runId: result.runId,
      variantConfig: variantPath,
      runDir: result.runDir,
    });
  }

  let bestIndex: number | null = null;
  for (let index = 0; index < variants.length; index += 1) {
    const entry = variants[index];
    if (entry.guardExceeded || entry.phi == null) {
      continue;
    }
    if (bestIndex == null) {
      bestIndex = index;
      continue;
    }
    const currentBest = variants[bestIndex];
    if ((entry.phi ?? Number.NEGATIVE_INFINITY) > (currentBest.phi ?? Number.NEGATIVE_INFINITY)) {
      bestIndex = index;
    }
  }

  return {
    outputDir: options.outDir,
    baselineConfig: baselineCopy,
    variants,
    bestIndex,
  };
};

export default runCouplingTuner;
