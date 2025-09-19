import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { promises as fs, existsSync } from 'node:fs';
import path from 'node:path';

import type { ChildProcessWithoutNullStreams } from 'node:child_process';

import type { Database as BetterSqlite3Database } from 'better-sqlite3';

import { scanArtifacts } from './files';
import type { PythonEnvironment } from './env';
import { openRegistry, upsertRun, fetchRuns, type RunRecord, type RunQuery } from './registry';

export type RunStatus = 'pending' | 'running' | 'complete' | 'failed' | 'aborted';

export type RunTailChunk = {
  output: string;
  nextFromByte: number;
  status: RunStatus;
};

export type RunCreateResult = {
  runId: string;
};

export type RunMetadata = {
  phase?: string | null;
  experiment?: string | null;
  label?: string | null;
};

type RunCompletion = {
  runId: string;
  status: RunStatus;
  exitCode: number | null;
  signal: NodeJS.Signals | null;
  error?: string | null;
};

type RunContext = {
  id: string;
  command: string;
  args: string[];
  cwd: string;
  createdAt: number;
  status: RunStatus;
  buffer: Buffer;
  process: ChildProcessWithoutNullStreams | null;
  artifactsDir: string;
  logPath: string;
  metadata: Required<RunMetadata>;
  updatedAt: number;
  completion: Promise<RunCompletion>;
  resolveCompletion: (result: RunCompletion) => void;
};

type ManagerConfig = {
  repoRoot: string;
  artifactsRoot: string;
  registryPath: string;
  pythonPathEntries: string[];
};

const ensureDir = async (dir: string) => {
  await fs.mkdir(dir, { recursive: true });
};

const writeLog = async (logPath: string, contents: Buffer) => {
  await ensureDir(path.dirname(logPath));
  await fs.writeFile(logPath, contents);
};

export class RunManager {
  private readonly config: ManagerConfig;
  private pythonEnv: PythonEnvironment | null = null;
  private readonly runs = new Map<string, RunContext>();
  private readonly registry: BetterSqlite3Database;

  constructor(config: ManagerConfig) {
    this.config = config;
    this.registry = openRegistry(config.registryPath);
  }

  setPythonEnv(env: PythonEnvironment | null) {
    this.pythonEnv = env;
  }

  getPythonEnv(): PythonEnvironment | null {
    return this.pythonEnv;
  }

  async createRun(
    command: string,
    args: string[],
    cwd?: string,
    metadata: RunMetadata = {},
  ): Promise<RunCreateResult> {
    if (!this.pythonEnv) {
      throw new Error('Python environment not configured. Call env.detect() first.');
    }

    const runId = randomUUID();
    const runCwd = cwd ? path.resolve(cwd) : this.config.repoRoot;
    const runArtifactsDir = path.join(this.config.artifactsRoot, runId);
    await ensureDir(runArtifactsDir);

    let resolveCompletion: (result: RunCompletion) => void = () => undefined;
    const completion = new Promise<RunCompletion>((resolve) => {
      resolveCompletion = resolve;
    });

    const context: RunContext = {
      id: runId,
      command,
      args,
      cwd: runCwd,
      createdAt: Date.now(),
      status: 'pending',
      buffer: Buffer.alloc(0),
      process: null,
      artifactsDir: runArtifactsDir,
      logPath: path.join(runArtifactsDir, 'stdout.log'),
      metadata: {
        phase: metadata.phase ?? null,
        experiment: metadata.experiment ?? null,
        label: metadata.label ?? null,
      },
      updatedAt: Date.now(),
      completion,
      resolveCompletion,
    };

    this.runs.set(runId, context);
    this.spawnProcess(context);
    upsertRun(this.registry, {
      id: context.id,
      createdAt: context.createdAt,
      updatedAt: context.createdAt,
      status: 'running',
      command: context.command,
      args: context.args,
      cwd: context.cwd,
      phase: context.metadata.phase,
      experiment: context.metadata.experiment,
      label: context.metadata.label,
      artifactsDir: context.artifactsDir,
      metrics: null,
    });
    return { runId };
  }

  private spawnProcess(context: RunContext) {
    const [cmd, ...argv] = this.buildPythonCommand(context);
    const child = spawn(cmd, argv, {
      cwd: context.cwd,
      env: {
        ...process.env,
        PYTHONPATH: this.buildPythonPath(),
      },
    });

    context.process = child;
    context.status = 'running';
    child.stdout.on('data', (chunk: Buffer) => {
      context.buffer = Buffer.concat([context.buffer, chunk]);
    });
    child.stderr.on('data', (chunk: Buffer) => {
      context.buffer = Buffer.concat([context.buffer, chunk]);
    });

    child.on('exit', async (code, signal) => {
      if (signal === 'SIGTERM') {
        context.status = 'aborted';
      } else if (code === 0) {
        context.status = 'complete';
      } else {
        context.status = 'failed';
      }

      context.updatedAt = Date.now();
      await writeLog(context.logPath, context.buffer);

      const metrics = await this.collectRunMetrics(context.id);
      upsertRun(this.registry, {
        id: context.id,
        createdAt: context.createdAt,
        updatedAt: context.updatedAt,
        status: context.status,
        command: context.command,
        args: context.args,
        cwd: context.cwd,
        phase: context.metadata.phase,
        experiment: context.metadata.experiment,
        label: context.metadata.label,
        artifactsDir: context.artifactsDir,
        metrics,
      });

      context.resolveCompletion({
        runId: context.id,
        status: context.status,
        exitCode: code,
        signal,
      });
    });

    child.on('error', async (error: Error) => {
      context.status = 'failed';
      context.updatedAt = Date.now();
      await writeLog(context.logPath, context.buffer);
      upsertRun(this.registry, {
        id: context.id,
        createdAt: context.createdAt,
        updatedAt: context.updatedAt,
        status: 'failed',
        command: context.command,
        args: context.args,
        cwd: context.cwd,
        phase: context.metadata.phase,
        experiment: context.metadata.experiment,
        label: context.metadata.label,
        artifactsDir: context.artifactsDir,
        metrics: null,
      });
      context.resolveCompletion({
        runId: context.id,
        status: 'failed',
        exitCode: null,
        signal: null,
        error: error.message,
      });
    });
  }

  private buildPythonCommand(context: RunContext): [string, ...string[]] {
    if (!this.pythonEnv) {
      throw new Error('Python environment not configured');
    }

    const python = this.pythonEnv.executable;
    if (context.command === python) {
      return [context.command, ...context.args];
    }

    return [python, '-m', context.command, ...context.args];
  }

  private buildPythonPath(): string {
    const entries = new Set<string>();

    if (process.env.PYTHONPATH) {
      for (const part of process.env.PYTHONPATH.split(path.delimiter)) {
        if (part.trim().length > 0) {
          entries.add(part.trim());
        }
      }
    }

    for (const entry of this.config.pythonPathEntries) {
      entries.add(entry);
    }

    return Array.from(entries).join(path.delimiter);
  }

  async tail(runId: string, fromByte = 0): Promise<RunTailChunk> {
    const context = this.runs.get(runId);
    if (!context) {
      throw new Error(`Run ${runId} not found`);
    }

    const start = Math.max(0, fromByte);
    const slice = context.buffer.subarray(start);
    return {
      output: slice.toString('utf-8'),
      nextFromByte: start + slice.byteLength,
      status: context.status,
    };
  }

  async abort(runId: string) {
    const context = this.runs.get(runId);
    if (!context?.process) {
      throw new Error(`Run ${runId} not running`);
    }

    context.process.kill('SIGTERM');
  }

  async listArtifacts(runId: string) {
    const context = this.runs.get(runId);
    if (!context) {
      throw new Error(`Run ${runId} not found`);
    }

    return scanArtifacts(context.artifactsDir);
  }

  async fetchRegistry(query: RunQuery = {}): Promise<RunRecord[]> {
    return fetchRuns(this.registry, query);
  }

  async waitForCompletion(runId: string): Promise<RunCompletion> {
    const context = this.runs.get(runId);
    if (!context) {
      throw new Error(`Run ${runId} not found`);
    }
    return context.completion;
  }

  async collectRunMetrics(runId: string): Promise<Record<string, number | null> | null> {
    const context = this.runs.get(runId);
    if (!context) {
      throw new Error(`Run ${runId} not found`);
    }

    const summaryPath = path.join(context.artifactsDir, 'summary.json');
    if (!existsSync(summaryPath)) {
      return null;
    }

    try {
      const raw = await fs.readFile(summaryPath, 'utf-8');
      const parsed = JSON.parse(raw) as Record<string, unknown>;
      const metrics: Record<string, number | null> = {};
      for (const [key, value] of Object.entries(parsed)) {
        if (typeof value === 'number') {
          metrics[key] = Number.isFinite(value) ? value : null;
        } else if (typeof value === 'boolean') {
          metrics[key] = value ? 1 : 0;
        }
      }
      return Object.keys(metrics).length > 0 ? metrics : null;
    } catch (error) {
      console.warn(`Failed to parse summary metrics for run ${runId}:`, error);
      return null;
    }
  }
}

