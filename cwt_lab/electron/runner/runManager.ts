import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { promises as fs, existsSync } from 'node:fs';
import path from 'node:path';

import os from 'node:os';
import { setTimeout as delay } from 'node:timers/promises';

import JSZip from 'jszip';

import type { Database as BetterSqlite3Database } from 'better-sqlite3';

import { scanArtifacts } from './files';
import type { PythonEnvironment } from './env';
import { planModuleInvocation, formatCli } from './pythonInvoker';
import { openRegistry, upsertRun, fetchRuns, type RunRecord, type RunQuery } from './registry';

export type RunStatus = 'pending' | 'running' | 'complete' | 'failed' | 'aborted';

export type RunTailChunk = {
  output: string;
  nextFromByte: number;
  startFromByte: number;
  totalBytes: number;
  hasMoreBefore: boolean;
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
  requestedCommand: string;
  requestedArgs: string[];
  requestedCwd: string;
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
  timeoutHandle: NodeJS.Timeout | null;
  timeoutMs: number | null;
  diagnosticsPath: string;
  diagnostics: RunDiagnostics;
  timeoutTriggered: boolean;
};

type ManagerConfig = {
  repoRoot: string;
  artifactsRoot: string;
  registryPath: string;
  pythonPathEntries: string[];
};

export type RunOptions = {
  timeoutMs?: number;
};

type RunDiagnostics = {
  runId: string;
  command: string;
  args: string[];
  cwd: string;
  createdAtUtc: string;
  updatedAtUtc: string;
  status: RunStatus;
  timeoutMs: number | null;
  exitCode: number | null;
  signal: NodeJS.Signals | null;
  error: string | null;
  platform: NodeJS.Platform;
  env: Record<string, string>;
};

const LONG_PATH_THRESHOLD = 240;

const toFsPath = (value: string) => {
  if (process.platform !== 'win32') {
    return value;
  }

  const absolute = path.resolve(value);
  if (absolute.startsWith('\\\\?\\')) {
    return absolute;
  }

  if (absolute.length < LONG_PATH_THRESHOLD) {
    return absolute;
  }

  if (absolute.startsWith('\\\\')) {
    return `\\\\?\\UNC\\${absolute.slice(2)}`;
  }

  return `\\\\?\\${absolute}`;
};

const ensureDir = async (dir: string) => {
  await fs.mkdir(toFsPath(dir), { recursive: true });
};

const writeLog = async (logPath: string, contents: Buffer) => {
  await ensureDir(path.dirname(logPath));
  await fs.writeFile(toFsPath(logPath), contents);
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
    options: RunOptions = {},
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

    const timeoutMs = Number.isFinite(options.timeoutMs) ? Number(options.timeoutMs) : null;
    const diagnosticsPath = path.join(runArtifactsDir, 'diagnostics.json');

    const pythonPathValue = this.buildPythonPath();
    const envSnapshotSource: NodeJS.ProcessEnv = {
      ...process.env,
      CWT_OUTPUT_DIR: runArtifactsDir,
    };
    if (pythonPathValue) {
      envSnapshotSource.PYTHONPATH = pythonPathValue;
    }

    const diagnostics: RunDiagnostics = {
      runId,
      command,
      args,
      cwd: runCwd,
      createdAtUtc: new Date().toISOString(),
      updatedAtUtc: new Date().toISOString(),
      status: 'pending',
      timeoutMs,
      exitCode: null,
      signal: null,
      error: null,
      platform: process.platform,
      env: this.snapshotEnv(envSnapshotSource),
    };

    const context: RunContext = {
      id: runId,
      requestedCommand: command,
      requestedArgs: [...args],
      requestedCwd: runCwd,
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
      timeoutHandle: null,
      timeoutMs,
      diagnosticsPath,
      diagnostics,
      timeoutTriggered: false,
    };

    this.runs.set(runId, context);
    await this.writeDiagnostics(context);
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

  previewCommand(
    command: string,
    args: string[],
    cwd?: string,
  ): { command: string; args: string[]; cwd: string; env: Record<string, string>; cli: string } {
    if (!this.pythonEnv) {
      throw new Error('Python environment not configured. Call env.detect() first.');
    }

    const runCwd = cwd ? path.resolve(cwd) : this.config.repoRoot;
    const invocation = this.resolveInvocation(command, args, runCwd);
    const pythonPathValue = invocation.pythonPath ?? this.buildPythonPath();

    const env: Record<string, string> = {};
    if (pythonPathValue) {
      env.PYTHONPATH = pythonPathValue;
    }

    const cli = formatCli({
      command: invocation.command,
      args: invocation.args,
      cwd: invocation.cwd,
      pythonPath: pythonPathValue ?? null,
    });

    return {
      command: invocation.command,
      args: [...invocation.args],
      cwd: invocation.cwd,
      env,
      cli,
    };
  }

  private spawnProcess(context: RunContext) {
    const invocation = this.resolveInvocation(
      context.requestedCommand,
      context.requestedArgs,
      context.requestedCwd,
    );

    context.command = invocation.command;
    context.args = [...invocation.args];
    context.cwd = invocation.cwd;

    const pythonPathValue = invocation.pythonPath ?? this.buildPythonPath();
    const env: NodeJS.ProcessEnv = {
      ...process.env,
      CWT_OUTPUT_DIR: context.artifactsDir,
      PYTHONIOENCODING: 'utf-8',
    };
    if (pythonPathValue) {
      env.PYTHONPATH = pythonPathValue;
    }

    context.diagnostics.command = invocation.command;
    context.diagnostics.args = [...invocation.args];
    context.diagnostics.cwd = invocation.cwd;
    context.diagnostics.env = this.snapshotEnv(env);

    const child = spawn(invocation.command, invocation.args, {
      cwd: invocation.cwd,
      env,
      detached: process.platform !== 'win32',
      windowsHide: true,
    });

    context.process = child;
    context.status = 'running';
    context.diagnostics.status = 'running';
    context.diagnostics.updatedAtUtc = new Date().toISOString();
    void this.writeDiagnostics(context);

    if (context.timeoutMs && context.timeoutMs > 0) {
      context.timeoutHandle = setTimeout(() => {
        void this.handleTimeout(context);
      }, context.timeoutMs).unref();
    }
    child.stdout.on('data', (chunk: Buffer) => {
      context.buffer = Buffer.concat([context.buffer, chunk]);
    });
    child.stderr.on('data', (chunk: Buffer) => {
      context.buffer = Buffer.concat([context.buffer, chunk]);
    });

    child.on('exit', async (code, signal) => {
      if (context.timeoutHandle) {
        clearTimeout(context.timeoutHandle);
        context.timeoutHandle = null;
      }

      if (context.timeoutTriggered) {
        context.status = 'failed';
      } else if (signal === 'SIGTERM') {
        context.status = 'aborted';
      } else if (code === 0) {
        context.status = 'complete';
      } else {
        context.status = 'failed';
      }

      context.updatedAt = Date.now();
      await writeLog(context.logPath, context.buffer);

      context.diagnostics.status = context.status;
      context.diagnostics.exitCode = code ?? null;
      context.diagnostics.signal = signal ?? null;
      if (context.timeoutTriggered) {
        context.diagnostics.error = 'timeout';
      }
      context.diagnostics.updatedAtUtc = new Date().toISOString();
      await this.writeDiagnostics(context);

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
        error: context.timeoutTriggered ? 'timeout' : undefined,
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
      context.diagnostics.status = 'failed';
      context.diagnostics.exitCode = null;
      context.diagnostics.signal = null;
      context.diagnostics.error = error.message;
      context.diagnostics.updatedAtUtc = new Date().toISOString();
      await this.writeDiagnostics(context);

      context.resolveCompletion({
        runId: context.id,
        status: 'failed',
        exitCode: null,
        signal: null,
        error: error.message,
      });
    });
  }

  private async handleTimeout(context: RunContext) {
    if (!context.process) {
      return;
    }

    context.timeoutTriggered = true;
    context.diagnostics.error = 'timeout';
    context.diagnostics.updatedAtUtc = new Date().toISOString();
    await this.writeDiagnostics(context);

    await this.terminateProcessTree(context, 'SIGTERM');
  }

  private isModuleName(command: string): boolean {
    if (!command) {
      return false;
    }

    if (command.includes('/') || command.includes('\\')) {
      return false;
    }

    if (command.endsWith('.py')) {
      return false;
    }

    if (this.pythonEnv && command === this.pythonEnv.executable) {
      return false;
    }

    return command.split('.').every((segment) => segment.length > 0 && !segment.includes('-'));
  }

  private buildPythonPath(): string | null {
    if (this.pythonEnv?.strategy !== 'py_path') {
      return null;
    }

    const entries = this.config.pythonPathEntries.filter((entry) => entry && entry.length > 0);
    if (entries.length === 0) {
      return path.join(this.config.repoRoot, 'cwt-sim');
    }
    return entries.join(path.delimiter);
  }

  private resolveInvocation(
    command: string,
    args: string[],
    cwd: string,
  ): {
    command: string;
    args: string[];
    cwd: string;
    pythonPath: string | null;
  } {
    if (!this.pythonEnv) {
      throw new Error('Python environment not configured');
    }

    const requestedCommand = command;
    const requestedArgs = [...args];
    const requestedCwd = cwd;

    if (!this.isModuleName(requestedCommand)) {
      return {
        command: requestedCommand,
        args: requestedArgs,
        cwd: requestedCwd,
        pythonPath: null,
      };
    }

    const plan = planModuleInvocation({
      pythonExe: this.pythonEnv.executable,
      strategy: this.pythonEnv.strategy,
      repoRoot: this.config.repoRoot,
      moduleName: requestedCommand,
      args: requestedArgs,
      pythonPathEntries: this.config.pythonPathEntries,
    });

    return plan;
  }

  async tail(runId: string, fromByte = 0, maxBytes?: number): Promise<RunTailChunk> {
    const context = this.runs.get(runId);
    if (!context) {
      throw new Error(`Run ${runId} not found`);
    }

    const totalBytes = context.buffer.byteLength;
    let start = Math.trunc(fromByte);
    if (!Number.isFinite(start)) {
      start = 0;
    }
    if (maxBytes && start < 0) {
      start = Math.max(totalBytes - maxBytes, 0);
    } else if (start < 0) {
      start = Math.max(totalBytes + start, 0);
    }
    if (start > totalBytes) {
      start = totalBytes;
    }

    const effectiveMax = maxBytes && maxBytes > 0 ? Math.min(maxBytes, totalBytes) : null;
    const end = effectiveMax ? Math.min(start + effectiveMax, totalBytes) : totalBytes;
    const slice = context.buffer.subarray(start, end);
    return {
      output: slice.toString('utf-8'),
      nextFromByte: start + slice.byteLength,
      startFromByte: start,
      totalBytes,
      hasMoreBefore: start > 0,
      status: context.status,
    };
  }

  async abort(runId: string) {
    const context = this.runs.get(runId);
    if (!context?.process) {
      throw new Error(`Run ${runId} not running`);
    }

    await this.terminateProcessTree(context, 'SIGTERM');
  }

  async listArtifacts(runId: string) {
    const context = this.runs.get(runId);
    if (!context) {
      throw new Error(`Run ${runId} not found`);
    }

    return scanArtifacts(context.artifactsDir);
  }

  async readArtifact(runId: string, relativePath: string) {
    const context = this.runs.get(runId);
    if (!context) {
      throw new Error(`Run ${runId} not found`);
    }

    const safeRelative = relativePath.replace(/\\/g, '/');
    const resolved = path.resolve(context.artifactsDir, safeRelative);
    if (!resolved.startsWith(context.artifactsDir)) {
      throw new Error('Invalid artifact path');
    }

    const contents = await fs.readFile(toFsPath(resolved), 'utf-8');
    return { path: resolved, contents };
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

  async shutdown(gracePeriodMs = 2_000) {
    const active = Array.from(this.runs.values()).filter((context) => context.process);
    await Promise.all(
      active.map(async (context) => {
        if (!context.process) {
          return;
        }

        await this.terminateProcessTree(context, 'SIGTERM');
        const outcome = await Promise.race([
          context.completion,
          delay(gracePeriodMs).then(() => null),
        ]);

        if (!outcome && context.process) {
          await this.terminateProcessTree(context, 'SIGKILL');
        }
      }),
    );
  }

  async collectRunMetrics(runId: string): Promise<Record<string, number | null> | null> {
    const artifactsDir = await this.resolveArtifactsDir(runId);

    const summaryPath = path.join(artifactsDir, 'summary.json');
    if (!existsSync(toFsPath(summaryPath))) {
      return null;
    }

    try {
      const raw = await fs.readFile(toFsPath(summaryPath), 'utf-8');
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

  async collectDiagnosticsBundle(runId: string): Promise<{ zipPath: string; files: string[] }> {
    const artifactsDir = await this.resolveArtifactsDir(runId);
    const attachments: string[] = [];
    const zip = new JSZip();

    const addFile = async (filename: string) => {
      const absolute = path.join(artifactsDir, filename);
      if (!existsSync(toFsPath(absolute))) {
        return;
      }
      const data = await fs.readFile(toFsPath(absolute));
      zip.file(filename, data);
      attachments.push(absolute);
    };

    await addFile('stdout.log');
    await addFile('diagnostics.json');

    const envInfo = {
      platform: process.platform,
      release: os.release(),
      python: this.pythonEnv,
      timestampUtc: new Date().toISOString(),
    } satisfies Record<string, unknown>;
    zip.file('environment.json', JSON.stringify(envInfo, null, 2));

    const zipBuffer = await zip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE' });
    const zipPath = path.join(artifactsDir, `diagnostics-${Date.now()}.zip`);
    await fs.writeFile(toFsPath(zipPath), zipBuffer);

    return { zipPath, files: attachments };
  }

  private snapshotEnv(env: NodeJS.ProcessEnv): Record<string, string> {
    const preferredKeys = new Set([
      'PATH',
      'PYTHONPATH',
      'VIRTUAL_ENV',
      'CONDA_PREFIX',
      'CONDA_DEFAULT_ENV',
      'CWT_OUTPUT_DIR',
    ]);

    const entries: [string, string][] = [];
    for (const key of preferredKeys) {
      const value = env[key];
      if (typeof value === 'string') {
        entries.push([key, value]);
      }
    }

    const extraKeys = Object.keys(env)
      .filter((key) =>
        key.startsWith('PYTHON') || key.startsWith('CWT_') || key.startsWith('VIRTUAL')
          ? true
          : false,
      )
      .slice(0, 5);

    for (const key of extraKeys) {
      if (entries.find(([existing]) => existing === key)) {
        continue;
      }
      const value = env[key];
      if (typeof value === 'string') {
        entries.push([key, value]);
      }
    }

    const snapshot: Record<string, string> = {};
    for (const [key, value] of entries) {
      snapshot[key] = value;
    }
    return snapshot;
  }

  private async writeDiagnostics(context: RunContext) {
    try {
      const payload = {
        ...context.diagnostics,
        hostname: os.hostname(),
        pid: context.process?.pid ?? null,
      } satisfies RunDiagnostics & { hostname: string; pid: number | null };
      await ensureDir(path.dirname(context.diagnosticsPath));
      await fs.writeFile(toFsPath(context.diagnosticsPath), JSON.stringify(payload, null, 2), 'utf-8');
    } catch (error) {
      console.warn(`Failed to write diagnostics for run ${context.id}:`, error);
    }
  }

  private async terminateProcessTree(context: RunContext, signal: NodeJS.Signals | 'SIGKILL') {
    const child = context.process;
    if (!child || !child.pid) {
      return;
    }

    try {
      if (process.platform === 'win32') {
        await new Promise<void>((resolve) => {
          const taskkill = spawn('taskkill', ['/PID', String(child.pid), '/T', '/F']);
          taskkill.on('exit', () => resolve());
          taskkill.on('error', () => resolve());
        });
      } else {
        try {
          process.kill(-child.pid, signal);
        } catch {
          try {
            child.kill(signal);
          } catch {
            // ignore
          }
        }
      }
    } catch (error) {
      console.warn(`Failed to terminate run ${context.id}:`, error);
    }
  }

  private async resolveArtifactsDir(runId: string): Promise<string> {
    const context = this.runs.get(runId);
    if (context) {
      return context.artifactsDir;
    }

    const [record] = fetchRuns(this.registry, { id: runId, limit: 1 });
    if (!record) {
      throw new Error(`Run ${runId} not found`);
    }
    return record.artifactsDir;
  }
}

