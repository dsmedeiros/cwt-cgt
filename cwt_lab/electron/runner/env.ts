import {
  spawnSync,
  type SpawnSyncOptions,
  type SpawnSyncOptionsWithStringEncoding,
  type SpawnSyncReturns,
} from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';

export type PythonStrategy = 'module' | 'py_path' | 'installed';

export type PythonCandidate = {
  path: string;
  version: string | null;
  ok: boolean;
  strategy: PythonStrategy | null;
  error?: string;
};

export type PythonEnvironment = {
  executable: string;
  version: string | null;
  strategy: PythonStrategy;
};

export type DetectPythonResult = {
  candidates: PythonCandidate[];
  selected: PythonCandidate | null;
  environment: PythonEnvironment | null;
  error?: string;
};

export type EnvironmentConfig = {
  repoRoot: string;
  artifactsRoot: string;
  pythonPath: string | null;
  strategy: PythonStrategy | null;
};

type StoredConfig = {
  pythonPath: string | null;
  strategy: PythonStrategy | null;
};

type CandidateSpec = {
  label: string;
  command: string;
  args: string[];
};

type CandidateEvaluation = {
  candidate: PythonCandidate;
  environment: PythonEnvironment | null;
};

const repoRoot = path.resolve(__dirname, '..', '..', '..');
const artifactsRoot = path.join(repoRoot, 'artifacts');
const cwtSimRoot = path.join(repoRoot, 'cwt-sim');
const configPath = path.join(repoRoot, 'cwt_lab', 'config.json');

const BUNDLED_PACKAGES = ['networkx'];

let currentEnvironment: PythonEnvironment | null = null;

const defaultConfig: StoredConfig = {
  pythonPath: null,
  strategy: null,
};

const candidatePythonRoots = (): string[] => [
  path.join(repoRoot, 'python_deps'),
  path.join(repoRoot, 'python_deps', 'site-packages'),
  path.join(repoRoot, 'vendor'),
  path.join(repoRoot, 'vendor', 'python'),
  path.join(cwtSimRoot, 'vendor'),
  path.join(cwtSimRoot, 'vendor', 'python'),
];

const resolveBundledPythonPaths = (): string[] => {
  const entries = new Set<string>();
  candidatePythonRoots().forEach((root) => {
    if (!existsSync(root)) {
      return;
    }
    if (BUNDLED_PACKAGES.some((pkg) => existsSync(path.join(root, pkg)))) {
      entries.add(root);
    }
  });
  return Array.from(entries);
};

const buildPythonPathSegments = (): string[] => {
  const segments = new Set<string>();
  segments.add(cwtSimRoot);
  resolveBundledPythonPaths().forEach((entry) => segments.add(entry));

  const existing = process.env.PYTHONPATH;
  if (existing) {
    existing
      .split(path.delimiter)
      .map((segment) => segment.trim())
      .filter((segment) => segment.length > 0)
      .forEach((segment) => segments.add(segment));
  }

  return Array.from(segments);
};

export const getBundledPythonPathEntries = (): string[] => resolveBundledPythonPaths();

const ensureConfigDir = () => {
  const dir = path.dirname(configPath);
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
};

const readConfig = (): StoredConfig => {
  try {
    const raw = readFileSync(configPath, 'utf-8');
    const parsed = JSON.parse(raw) as StoredConfig;
    return {
      pythonPath: parsed.pythonPath ?? null,
      strategy: parsed.strategy ?? null,
    };
  } catch {
    return { ...defaultConfig };
  }
};

const writeConfig = (config: StoredConfig) => {
  ensureConfigDir();
  writeFileSync(configPath, JSON.stringify(config, null, 2), 'utf-8');
};

const buildCandidateSpecs = (): CandidateSpec[] => {
  if (process.platform === 'win32') {
    const venvPath = path.join(repoRoot, '.venv', 'Scripts', 'python.exe');
    return [
      { label: venvPath, command: venvPath, args: [] },
      { label: 'python', command: 'python', args: [] },
      { label: 'py -3', command: 'py', args: ['-3'] },
    ];
  }

  const venvPath = path.join(repoRoot, '.venv', 'bin', 'python');
  return [
    { label: venvPath, command: venvPath, args: [] },
    { label: 'python3', command: 'python3', args: [] },
    { label: 'python', command: 'python', args: [] },
  ];
};

const runPythonCommand = (
  spec: CandidateSpec,
  extraArgs: string[],
  options: SpawnSyncOptions = {},
): SpawnSyncReturns<string> => {
  const args = [...spec.args, ...extraArgs];
  const merged: SpawnSyncOptionsWithStringEncoding = {
    encoding: 'utf-8',
    ...options,
  } as SpawnSyncOptionsWithStringEncoding;
  return spawnSync(spec.command, args, merged);
};

const describeFailure = (stage: string, result: SpawnSyncReturns<string>) => {
  if (result.error) {
    return `${stage}: ${result.error.message}`;
  }

  const stderr = result.stderr?.toString().trim();
  const stdout = result.stdout?.toString().trim();
  const message = stderr || stdout;
  return `${stage}: ${message && message.length > 0 ? message : 'no output'}`;
};

const normalizePathForComparison = (value: string) =>
  process.platform === 'win32' ? value.toLowerCase() : value;

const evaluateCandidate = (spec: CandidateSpec): CandidateEvaluation => {
  if (path.isAbsolute(spec.command) && spec.args.length === 0 && !existsSync(spec.command)) {
    return {
      candidate: {
        path: spec.command,
        version: null,
        ok: false,
        strategy: null,
        error: `Interpreter not found at ${spec.command}`,
      },
      environment: null,
    };
  }

  const failures: string[] = [];

  const versionResult = runPythonCommand(spec, ['-V']);
  if (versionResult.error || versionResult.status !== 0) {
    failures.push(describeFailure('version check', versionResult));
    return {
      candidate: {
        path: spec.command,
        version: null,
        ok: false,
        strategy: null,
        error: failures.join(' | '),
      },
      environment: null,
    };
  }

  const versionOutput = (versionResult.stdout || versionResult.stderr || '').toString().trim();
  const version = versionOutput.length > 0 ? versionOutput : null;

  const execResult = runPythonCommand(spec, ['-c', 'import sys; print(sys.executable)'], {
    cwd: repoRoot,
  });
  if (execResult.error || execResult.status !== 0) {
    failures.push(describeFailure('interpreter probe', execResult));
    return {
      candidate: {
        path: spec.command,
        version,
        ok: false,
        strategy: null,
        error: failures.join(' | '),
      },
      environment: null,
    };
  }

  const resolvedPath = execResult.stdout?.toString().trim() || execResult.stderr?.toString().trim();
  const interpreterPath = resolvedPath && resolvedPath.length > 0 ? resolvedPath : spec.command;

  const installedResult = runPythonCommand(spec, ['-c', "import cwt; print('ok')"], {
    cwd: repoRoot,
  });
  if (!installedResult.error && installedResult.status === 0) {
    const environment: PythonEnvironment = {
      executable: interpreterPath,
      version,
      strategy: 'installed',
    };
    return {
      candidate: {
        path: interpreterPath,
        version,
        ok: true,
        strategy: 'installed',
      },
      environment,
    };
  }
  failures.push(describeFailure('import cwt', installedResult));

  const moduleResult = runPythonCommand(
    spec,
    ['-c', "import importlib; importlib.import_module('experiments')"],
    {
      cwd: cwtSimRoot,
    },
  );
  if (!moduleResult.error && moduleResult.status === 0) {
    const environment: PythonEnvironment = {
      executable: interpreterPath,
      version,
      strategy: 'module',
    };
    return {
      candidate: {
        path: interpreterPath,
        version,
        ok: true,
        strategy: 'module',
      },
      environment,
    };
  }
  failures.push(describeFailure('module run', moduleResult));

  const pythonSegments = buildPythonPathSegments();
  const pythonPath = pythonSegments.join(path.delimiter);
  const pyPathResult = runPythonCommand(spec, ['-c', "import cwt; print('ok')"], {
    cwd: repoRoot,
    env: {
      ...process.env,
      PYTHONPATH: pythonPath,
    },
  });
  if (!pyPathResult.error && pyPathResult.status === 0) {
    const environment: PythonEnvironment = {
      executable: interpreterPath,
      version,
      strategy: 'py_path',
    };
    return {
      candidate: {
        path: interpreterPath,
        version,
        ok: true,
        strategy: 'py_path',
      },
      environment,
    };
  }
  failures.push(describeFailure('PYTHONPATH injection', pyPathResult));

  return {
    candidate: {
      path: interpreterPath,
      version,
      ok: false,
      strategy: null,
      error: failures.join(' | '),
    },
    environment: null,
  };
};

const selectCandidate = (
  evaluations: CandidateEvaluation[],
  preferred: StoredConfig,
): { selected: CandidateEvaluation | null; updatedConfig: StoredConfig | null } => {
  const okCandidates = evaluations.filter((evaluation) => evaluation.candidate.ok && evaluation.environment);

  if (okCandidates.length === 0) {
    return { selected: null, updatedConfig: null };
  }

  const desiredPath = preferred.pythonPath;
  if (desiredPath) {
    const match = okCandidates.find(
      (evaluation) =>
        normalizePathForComparison(evaluation.candidate.path) ===
        normalizePathForComparison(desiredPath),
    );
    if (match) {
      return {
        selected: match,
        updatedConfig:
          match.candidate.strategy !== preferred.strategy ||
          normalizePathForComparison(match.candidate.path) !== normalizePathForComparison(desiredPath)
            ? {
                pythonPath: match.candidate.path,
                strategy: match.candidate.strategy,
              }
            : null,
      };
    }
  }

  const priority: PythonStrategy[] = ['module', 'py_path', 'installed'];
  const match = okCandidates.sort((a, b) => {
    const aIndex = priority.indexOf(a.candidate.strategy as PythonStrategy);
    const bIndex = priority.indexOf(b.candidate.strategy as PythonStrategy);
    return aIndex - bIndex;
  })[0];

  return {
    selected: match,
    updatedConfig: {
      pythonPath: match.candidate.path,
      strategy: match.candidate.strategy,
    },
  };
};

export const detectPython = (): DetectPythonResult => {
  const stored = readConfig();
  const evaluations = buildCandidateSpecs().map(evaluateCandidate);
  const candidates = evaluations.map(({ candidate }) => candidate);
  const { selected, updatedConfig } = selectCandidate(evaluations, stored);

  if (updatedConfig) {
    writeConfig(updatedConfig);
  }

  currentEnvironment = selected?.environment ?? null;

  const errorMessage = selected?.environment
    ? undefined
    : (() => {
        const failures = evaluations
          .map(({ candidate }) =>
            candidate.ok ? null : `${candidate.path}: ${candidate.error ?? 'unknown failure'}`,
          )
          .filter((value): value is string => Boolean(value))
          .join(' | ');
        return failures.length > 0
          ? `No usable Python interpreter found. ${failures}`
          : 'No usable Python interpreter found.';
      })();

  return {
    candidates,
    selected: selected?.candidate ?? null,
    environment: selected?.environment ?? null,
    error: errorMessage,
  };
};

export const setPythonPath = (pythonPath: string): { candidate: PythonCandidate; environment: PythonEnvironment } => {
  const trimmed = pythonPath?.trim();
  if (!trimmed) {
    throw new Error('Python path is required');
  }

  const evaluation = evaluateCandidate({ label: trimmed, command: trimmed, args: [] });
  if (!evaluation.environment || !evaluation.candidate.ok) {
    throw new Error(
      evaluation.candidate.error || `Interpreter at ${trimmed} is not a valid CWT environment`,
    );
  }

  const stored: StoredConfig = {
    pythonPath: evaluation.candidate.path,
    strategy: evaluation.candidate.strategy,
  };
  writeConfig(stored);
  currentEnvironment = evaluation.environment;

  return {
    candidate: evaluation.candidate,
    environment: evaluation.environment,
  };
};

export const getEnvironmentConfig = (): EnvironmentConfig => {
  const stored = readConfig();
  return {
    repoRoot,
    artifactsRoot,
    pythonPath: stored.pythonPath,
    strategy: stored.strategy,
  };
};

export const getCurrentEnvironment = (): PythonEnvironment | null => currentEnvironment;
