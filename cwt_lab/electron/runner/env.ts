import { spawnSync } from 'node:child_process';
import path from 'node:path';

export type PythonEnvironment = {
  executable: string;
  venvRoot?: string;
};

export const detectPython = (): PythonEnvironment | null => {
  const { status, stdout } = spawnSync('python3', ['-c', 'import sys; print(sys.executable)'], {
    encoding: 'utf-8',
  });

  if (status !== 0) {
    return null;
  }

  const executable = stdout.trim();
  const venvRoot = process.env.VIRTUAL_ENV
    ? path.resolve(process.env.VIRTUAL_ENV)
    : undefined;

  return { executable, venvRoot };
};

export const resolveVenvBin = (env: PythonEnvironment | null): string | null => {
  if (!env?.venvRoot) {
    return null;
  }

  return process.platform === 'win32'
    ? path.join(env.venvRoot, 'Scripts')
    : path.join(env.venvRoot, 'bin');
};

export const canImportCwt = (env: PythonEnvironment | null): boolean => {
  if (!env) {
    return false;
  }

  const result = spawnSync(env.executable, ['-c', 'import cwt'], {
    encoding: 'utf-8',
  });

  return result.status === 0;
};

export const normalizePythonEnv = (
  env: PythonEnvironment | null,
): { executable: string | null; venvRoot: string | null } => ({
  executable: env?.executable ?? null,
  venvRoot: env?.venvRoot ?? null,
});
