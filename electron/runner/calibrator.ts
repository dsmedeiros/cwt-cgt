import fs from 'fs';
import path from 'path';
import { spawnSync, SpawnSyncReturns } from 'child_process';
import { cmdWilson3D, Wilson3DOptions } from './commands';
import { LoopStdoutMetrics, parseLoopStdout } from './parsers';

export interface GuidedLoopOptions {
  pythonExe: string;
  axes3?: Wilson3DOptions['axes3'];
  center?: Wilson3DOptions['center'];
  baseAmps: [number, number, number];
  fsGuard?: number;
  stepsSeq?: number[];
  minPhi?: number;
  handleSteps?: number;
  settle?: number;
  graph?: string;
  seed?: number;
  outDir: string;
  strategy?: Wilson3DOptions['strategy'];
}

export interface GuidedLoopOutputPaths {
  dir: string;
  stdout: string;
  stderr: string;
}

export interface GuidedLoopSuccess {
  ok: true;
  amps: [number, number, number];
  steps: number;
  metrics: LoopStdoutMetrics;
  out: GuidedLoopOutputPaths;
}

export interface GuidedLoopFailure {
  ok: false;
  out: GuidedLoopOutputPaths;
}

export type GuidedLoopResult = GuidedLoopSuccess | GuidedLoopFailure;

const DEFAULT_STEPS_SEQ = [160, 320, 480, 800];
const MAX_SHRINK_ATTEMPTS = 4;

function formatAttemptDirName(index: number): string {
  const padded = String(index + 1).padStart(2, '0');
  return `attempt-${padded}`;
}

function writeAttemptLogs(
  attemptDir: string,
  stdout: string,
  stderr: string
): GuidedLoopOutputPaths {
  fs.mkdirSync(attemptDir, { recursive: true });
  const stdoutPath = path.join(attemptDir, 'stdout.txt');
  const stderrPath = path.join(attemptDir, 'stderr.txt');
  fs.writeFileSync(stdoutPath, stdout, 'utf8');
  fs.writeFileSync(stderrPath, stderr, 'utf8');
  return { dir: attemptDir, stdout: stdoutPath, stderr: stderrPath };
}

function runWilson3D(
  pythonExe: string,
  options: Wilson3DOptions
): SpawnSyncReturns<string> {
  const { cmd, args, cwd } = cmdWilson3D(pythonExe, options);
  return spawnSync(cmd, args, { cwd, encoding: 'utf8' });
}

function shouldAcceptAttempt(
  metrics: LoopStdoutMetrics,
  fsGuard: number,
  minPhi: number
): boolean {
  if (typeof metrics.fsP95 !== 'number') {
    return false;
  }
  if (typeof metrics.phi !== 'number') {
    return false;
  }
  if (metrics.fsP95 > fsGuard) {
    return false;
  }
  return Math.abs(metrics.phi) >= minPhi;
}

export function guidedLoop({
  pythonExe,
  axes3,
  center,
  baseAmps,
  fsGuard = 0.1,
  stepsSeq = DEFAULT_STEPS_SEQ,
  minPhi = 0.01,
  handleSteps = 0,
  settle = 40,
  graph,
  seed,
  outDir,
  strategy,
}: GuidedLoopOptions): GuidedLoopResult {
  if (!Array.isArray(baseAmps) || baseAmps.length !== 3) {
    throw new Error('baseAmps must be a tuple of three values');
  }
  if (!stepsSeq.length) {
    throw new Error('stepsSeq must contain at least one entry');
  }
  if (!outDir) {
    throw new Error('outDir must be provided');
  }

  fs.mkdirSync(outDir, { recursive: true });

  let currentAmps: [number, number, number] = [
    baseAmps[0],
    baseAmps[1],
    baseAmps[2],
  ];
  let attemptIndex = 0;
  let lastOutput: GuidedLoopOutputPaths | null = null;

  for (let shrink = 0; shrink <= MAX_SHRINK_ATTEMPTS; shrink += 1) {
    for (const steps of stepsSeq) {
      const attemptDir = path.join(outDir, formatAttemptDirName(attemptIndex));
      attemptIndex += 1;
      const result = runWilson3D(pythonExe, {
        axes3,
        center,
        amplitudes: currentAmps,
        steps,
        handleSteps,
        settle,
        fsGuard,
        graph,
        seed,
        outDir: attemptDir,
        strategy,
      });

      const stdoutText = result.stdout ?? '';
      const stderrText = result.stderr ?? '';
      lastOutput = writeAttemptLogs(attemptDir, stdoutText, stderrText);

      if (result.status === 0 && stdoutText.length > 0) {
        const metrics = parseLoopStdout(stdoutText);
        if (shouldAcceptAttempt(metrics, fsGuard, minPhi)) {
          const acceptedAmps: [number, number, number] = [
            currentAmps[0],
            currentAmps[1],
            currentAmps[2],
          ];
          return {
            ok: true,
            amps: acceptedAmps,
            steps,
            metrics,
            out: lastOutput,
          };
        }
      }
    }

    if (shrink === MAX_SHRINK_ATTEMPTS) {
      break;
    }

    currentAmps = [
      currentAmps[0] / 2,
      currentAmps[1] / 2,
      currentAmps[2],
    ];
  }

  if (!lastOutput) {
    throw new Error('guidedLoop executed zero attempts');
  }

  return { ok: false, out: lastOutput };
}
