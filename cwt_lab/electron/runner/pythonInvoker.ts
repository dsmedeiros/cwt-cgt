import path from 'node:path';

import type { PythonStrategy } from './env';

type InvocationPlan = {
  command: string;
  args: string[];
  cwd: string;
  pythonPath: string | null;
  cli: string;
};

const SIM_DIRECTORY = 'cwt-sim';

const quoteShellArg = (value: string): string => {
  if (value.length === 0) {
    return process.platform === 'win32' ? '""' : "''";
  }

  if (process.platform === 'win32') {
    const escaped = value.replace(/"/g, '""');
    return `"${escaped}"`;
  }

  if (!/[\s"'\\]/.test(value)) {
    return value;
  }

  const escaped = value.replace(/(["\\$`])/g, '\\$1');
  return `"${escaped}"`;
};

const formatCli = (plan: { command: string; args: string[]; cwd: string; pythonPath: string | null }): string => {
  const { command, args, cwd, pythonPath } = plan;
  const envPrefix = pythonPath ? `PYTHONPATH=${quoteShellArg(pythonPath)} ` : '';
  const commandLine = [command, ...args].map(quoteShellArg).join(' ');
  if (cwd) {
    return `cd ${quoteShellArg(cwd)} && ${envPrefix}${commandLine}`.trim();
  }
  return `${envPrefix}${commandLine}`.trim();
};

const resolveScriptPath = (repoRoot: string, moduleName: string): string => {
  const segments = moduleName.split('.');
  const scriptPath = path.join(repoRoot, SIM_DIRECTORY, ...segments);
  return scriptPath.endsWith('.py') ? scriptPath : `${scriptPath}.py`;
};

export const planModuleInvocation = (options: {
  pythonExe: string;
  strategy: PythonStrategy;
  repoRoot: string;
  moduleName: string;
  args: string[];
  pythonPathEntries?: string[];
}): InvocationPlan => {
  const { pythonExe, strategy, repoRoot, moduleName } = options;
  const args = [...options.args];
  const pythonPathEntries = options.pythonPathEntries?.filter((entry) => entry && entry.length > 0) ?? [];
  const simRoot = path.join(repoRoot, SIM_DIRECTORY);

  if (strategy === 'py_path') {
    const scriptPath = resolveScriptPath(repoRoot, moduleName);
    const invocationArgs = [scriptPath, ...args];
    const pythonPath = pythonPathEntries.length > 0 ? pythonPathEntries.join(path.delimiter) : simRoot;
    return {
      command: pythonExe,
      args: invocationArgs,
      cwd: repoRoot,
      pythonPath,
      cli: formatCli({ command: pythonExe, args: invocationArgs, cwd: repoRoot, pythonPath }),
    } satisfies InvocationPlan;
  }

  const invocationArgs = ['-m', moduleName, ...args];
  return {
    command: pythonExe,
    args: invocationArgs,
    cwd: simRoot,
    pythonPath: null,
    cli: formatCli({ command: pythonExe, args: invocationArgs, cwd: simRoot, pythonPath: null }),
  } satisfies InvocationPlan;
};

export { formatCli, quoteShellArg };
export type { InvocationPlan };
