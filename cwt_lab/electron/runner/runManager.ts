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
import {
  openRegistry,
  upsertRun,
  fetchRuns,
  deleteRunRecord,
  type RunRecord,
  type RunQuery,
} from './registry';

export type RunStatus = 'pending' | 'running' | 'complete' | 'failed' | 'aborted';

export type RunTailChunk = {
  output: string;
  nextFromByte: number;
  startFromByte: number;
  totalBytes: number;
  hasMoreBefore: boolean;
  status: RunStatus;
  failureDetails: string | null;
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
  workspaceDir: string;
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
  artifactsDir?: string | null;
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

type StoredDiagnostics = Partial<RunDiagnostics> & { timeoutMs?: unknown };

const LONG_PATH_THRESHOLD = 240;

const RUN_WORKSPACE_ROOT = '_runs';
const RUN_LOG_FILENAME = 'stdout.log';
const RUN_DIAGNOSTICS_FILENAME = 'diagnostics.json';

const resolveWorkspaceDir = (artifactsDir: string, runId: string) =>
  path.join(artifactsDir, RUN_WORKSPACE_ROOT, runId);

const resolveLogPath = (artifactsDir: string, runId: string) =>
  path.join(resolveWorkspaceDir(artifactsDir, runId), RUN_LOG_FILENAME);

const resolveDiagnosticsPath = (artifactsDir: string, runId: string) =>
  path.join(resolveWorkspaceDir(artifactsDir, runId), RUN_DIAGNOSTICS_FILENAME);

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
    const overrideArtifactsDir =
      typeof options.artifactsDir === 'string' && options.artifactsDir.length > 0
        ? path.resolve(options.artifactsDir)
        : null;
    const runArtifactsDir = overrideArtifactsDir ?? path.join(this.config.artifactsRoot, runId);
    await ensureDir(runArtifactsDir);
    const runWorkspaceDir = resolveWorkspaceDir(runArtifactsDir, runId);
    await ensureDir(runWorkspaceDir);

    const argsSummary = JSON.stringify(args);
    console.info(
      '[RunManager] Received run request %s: command=%s args=%s cwd=%s',
      runId,
      command,
      argsSummary,
      runCwd,
    );

    let resolveCompletion: (result: RunCompletion) => void = () => undefined;
    const completion = new Promise<RunCompletion>((resolve) => {
      resolveCompletion = resolve;
    });

    const timeoutMs = Number.isFinite(options.timeoutMs) ? Number(options.timeoutMs) : null;
    const diagnosticsPath = resolveDiagnosticsPath(runArtifactsDir, runId);

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
      workspaceDir: runWorkspaceDir,
      logPath: resolveLogPath(runArtifactsDir, runId),
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

    const cliForLog = formatCli({
      command: invocation.command,
      args: invocation.args,
      cwd: invocation.cwd,
      pythonPath: pythonPathValue ?? null,
    });
    console.info(`[RunManager] Launching run ${context.id}: ${cliForLog}`);

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

      const exitDescriptor = `code=${code ?? 'null'} signal=${signal ?? 'null'}`;
      console.info(
        `[RunManager] Run ${context.id} exited with status ${context.status} (${exitDescriptor}).`,
      );

      context.diagnostics.status = context.status;
      context.diagnostics.exitCode = code ?? null;
      context.diagnostics.signal = signal ?? null;
      if (context.timeoutTriggered) {
        context.diagnostics.error = 'timeout';
      }
      context.diagnostics.updatedAtUtc = new Date().toISOString();
      await this.writeDiagnostics(context);

      context.process = null;
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

      const failureMessage = this.describeFailureDetails({
        status: context.status,
        timeoutMs: context.timeoutMs,
        timeoutTriggered: context.timeoutTriggered,
        diagnostics: context.diagnostics,
      });
      if (failureMessage) {
        console.error(`[RunManager] ${context.id}: ${failureMessage}`);
      }

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
      console.error(`[RunManager] Failed to start run ${context.id}:`, error);
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

      context.process = null;
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

    if (!context.timeoutTriggered) {
      console.warn(
        `[RunManager] Run ${context.id} exceeded timeout of ${context.timeoutMs ?? 0} ms. Sending SIGTERM.`,
      );
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

    const pythonExe = this.pythonEnv.executable;

    if (path.isAbsolute(pythonExe) && !existsSync(pythonExe)) {
      this.pythonEnv = null;
      throw new Error(
        `Configured Python interpreter not found at ${pythonExe}. ` +
          'Re-run environment detection to select a valid interpreter.',
      );
    }

    const plan = planModuleInvocation({
      pythonExe,
      strategy: this.pythonEnv.strategy,
      repoRoot: this.config.repoRoot,
      moduleName: requestedCommand,
      args: requestedArgs,
      pythonPathEntries: this.config.pythonPathEntries,
    });

    return plan;
  }

  private describeFailureDetails({
    status,
    timeoutMs,
    timeoutTriggered,
    diagnostics,
  }: {
    status: RunStatus;
    timeoutMs: number | null;
    timeoutTriggered: boolean;
    diagnostics: Partial<RunDiagnostics> | null;
  }): string | null {
    if (status !== 'failed') {
      return null;
    }

    const diagnosticsError =
      typeof diagnostics?.error === 'string' ? diagnostics.error : null;

    const effectiveTimeoutMs = (() => {
      if (Number.isFinite(timeoutMs)) {
        return timeoutMs;
      }
      const candidate = (diagnostics as { timeoutMs?: unknown } | null)?.timeoutMs;
      const numeric = typeof candidate === 'number' ? candidate : Number(candidate);
      return Number.isFinite(numeric) ? numeric : null;
    })();

    if (timeoutTriggered || diagnosticsError === 'timeout') {
      if (effectiveTimeoutMs && effectiveTimeoutMs > 0) {
        return `Run timed out after ${effectiveTimeoutMs} ms.`;
      }
      return 'Run timed out.';
    }

    if (diagnosticsError) {
      return diagnosticsError;
    }

    const exitCodeRaw = diagnostics?.exitCode;
    const exitCode = Number.isFinite(exitCodeRaw as number) ? (exitCodeRaw as number) : null;
    const signal = typeof diagnostics?.signal === 'string' ? diagnostics.signal : null;

    if (exitCode !== null && signal) {
      return `Process exited with code ${exitCode} after signal ${signal}.`;
    }
    if (exitCode !== null) {
      return `Process exited with code ${exitCode}.`;
    }
    if (signal) {
      return `Process terminated by signal ${signal}.`;
    }

    return 'Run failed for an unknown reason.';
  }

  async tail(runId: string, fromByte = 0, maxBytes?: number): Promise<RunTailChunk> {
    const context = this.runs.get(runId);
    if (context) {
      return this.formatTailChunk({
        buffer: context.buffer,
        fromByte,
        maxBytes,
        status: context.status,
        failureDetails: this.describeFailureDetails({
          status: context.status,
          timeoutMs: context.timeoutMs,
          timeoutTriggered: context.timeoutTriggered,
          diagnostics: context.diagnostics,
        }),
      });
    }

    const record = this.resolveRunRecord(runId);
    const artifactsDir = record.artifactsDir;
    const preferredLogPath = resolveLogPath(artifactsDir, runId);
    const legacyLogPath = path.join(artifactsDir, 'stdout.log');
    let buffer = Buffer.alloc(0);

    const candidateLogs = [preferredLogPath, legacyLogPath];
    for (const candidate of candidateLogs) {
      if (!existsSync(toFsPath(candidate))) {
        continue;
      }
      try {
        buffer = await fs.readFile(toFsPath(candidate));
        break;
      } catch (error) {
        console.warn(`Failed to read stdout for run ${runId}:`, error);
      }
    }

    const diagnostics = await this.loadStoredDiagnostics(runId, artifactsDir);
    const timeoutMs = diagnostics
      ? this.extractTimeoutMs(diagnostics.timeoutMs)
      : null;
    const failureDetails = this.describeFailureDetails({
      status: record.status,
      timeoutMs,
      timeoutTriggered: diagnostics?.error === 'timeout',
      diagnostics,
    });

    return this.formatTailChunk({
      buffer,
      fromByte,
      maxBytes,
      status: record.status,
      failureDetails,
    });
  }

  async abort(runId: string) {
    const context = this.runs.get(runId);
    if (!context?.process) {
      throw new Error(`Run ${runId} not running`);
    }

    await this.terminateProcessTree(context, 'SIGTERM');
  }

  async listArtifacts(runId: string) {
    const artifactsDir = await this.resolveArtifactsDir(runId);
    if (!existsSync(toFsPath(artifactsDir))) {
      throw new Error(`Artifacts for run ${runId} not found`);
    }

    try {
      return await scanArtifacts(artifactsDir);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to scan artifacts for run ${runId}: ${message}`);
    }
  }

  async readArtifact(
    runId: string,
    relativePath: string,
    encoding: 'utf-8' | 'base64' = 'utf-8',
  ) {
    const artifactsDir = await this.resolveArtifactsDir(runId);
    const safeRelative = relativePath.replace(/\\/g, '/');
    const resolved = path.resolve(artifactsDir, safeRelative);
    if (!resolved.startsWith(artifactsDir)) {
      throw new Error('Invalid artifact path');
    }

    if (encoding !== 'utf-8' && encoding !== 'base64') {
      throw new Error(`Unsupported encoding requested: ${encoding}`);
    }

    if (encoding === 'base64') {
      const buffer = await fs.readFile(toFsPath(resolved));
      return { path: resolved, contents: buffer.toString('base64'), encoding };
    }

    const contents = await fs.readFile(toFsPath(resolved), 'utf-8');
    return { path: resolved, contents, encoding };
  }

  async fetchRegistry(query: RunQuery = {}): Promise<RunRecord[]> {
    const records = fetchRuns(this.registry, query);
    const enriched = await Promise.all(
      records.map(async (record) => {
        if (record.metrics && Object.keys(record.metrics).length > 0) {
          return record;
        }

        try {
          const metrics = await this.collectRunMetrics(record.id);
          if (metrics && Object.keys(metrics).length > 0) {
            const updated: RunRecord = { ...record, metrics };
            upsertRun(this.registry, updated);
            return updated;
          }
        } catch (error) {
          console.warn(`Failed to collect metrics for run ${record.id}:`, error);
        }

        return record;
      }),
    );

    return enriched;
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

    const summaryMetrics = await this.collectSummaryMetrics(runId, artifactsDir);
    if (summaryMetrics && Object.keys(summaryMetrics).length > 0) {
      return summaryMetrics;
    }

    const csvMetrics = await this.collectMetricsFromCsv(runId, artifactsDir);
    return csvMetrics && Object.keys(csvMetrics).length > 0 ? csvMetrics : null;
  }

  async collectDiagnosticsBundle(runId: string): Promise<{ zipPath: string; files: string[] }> {
    const artifactsDir = await this.resolveArtifactsDir(runId);
    const attachments: string[] = [];
    const zip = new JSZip();

    const addFile = async (absolute: string) => {
      if (!existsSync(toFsPath(absolute))) {
        return false;
      }
      const data = await fs.readFile(toFsPath(absolute));
      const relative = path.relative(artifactsDir, absolute) || path.basename(absolute);
      zip.file(relative.replace(/\\/g, '/'), data);
      attachments.push(absolute);
      return true;
    };

    const logPaths = [resolveLogPath(artifactsDir, runId), path.join(artifactsDir, 'stdout.log')];
    for (const candidate of logPaths) {
      if (await addFile(candidate)) {
        break;
      }
    }

    const diagnosticsPaths = [
      resolveDiagnosticsPath(artifactsDir, runId),
      path.join(artifactsDir, 'diagnostics.json'),
    ];
    for (const candidate of diagnosticsPaths) {
      if (await addFile(candidate)) {
        break;
      }
    }

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

  async deleteRun(runId: string): Promise<{ runId: string }> {
    const context = this.runs.get(runId);
    if (context && (context.status === 'running' || context.status === 'pending')) {
      throw new Error('Cannot delete a run while it is in progress. Abort it first.');
    }

    let artifactsDir: string;
    try {
      artifactsDir = await this.resolveArtifactsDir(runId);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      throw new Error(`Unable to locate run ${runId}: ${message}`);
    }

    const workspaceDir = resolveWorkspaceDir(artifactsDir, runId);
    try {
      await fs.rm(toFsPath(workspaceDir), { recursive: true, force: true });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      console.warn(`Failed to remove workspace for run ${runId}:`, message);
    }

    const related = fetchRuns(this.registry, { artifactsDir });
    const remaining = related.filter((run) => run.id !== runId);

    if (remaining.length === 0) {
      try {
        await fs.rm(toFsPath(artifactsDir), { recursive: true, force: true });
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        throw new Error(`Failed to delete run directory ${artifactsDir}: ${message}`);
      }
    }

    deleteRunRecord(this.registry, runId);
    if (context) {
      this.runs.delete(runId);
    }

    return { runId };
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
    const record = this.resolveRunRecord(runId);
    return record.artifactsDir;
  }

  private extractTimeoutMs(value: unknown): number | null {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === 'string') {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : null;
    }
    return null;
  }

  private async loadStoredDiagnostics(
    runId: string,
    artifactsDir: string,
  ): Promise<StoredDiagnostics | null> {
    const diagnosticsPaths = [
      resolveDiagnosticsPath(artifactsDir, runId),
      path.join(artifactsDir, 'diagnostics.json'),
    ];

    for (const candidate of diagnosticsPaths) {
      if (!existsSync(toFsPath(candidate))) {
        continue;
      }

      try {
        const raw = await fs.readFile(toFsPath(candidate), 'utf-8');
        const parsed = JSON.parse(raw);
        if (!parsed || typeof parsed !== 'object') {
          continue;
        }
        return parsed as StoredDiagnostics;
      } catch (error) {
        console.warn(`Failed to read diagnostics for run ${runId}:`, error);
      }
    }

    return null;
  }

  private formatTailChunk({
    buffer,
    fromByte,
    maxBytes,
    status,
    failureDetails,
  }: {
    buffer: Buffer;
    fromByte: number;
    maxBytes?: number;
    status: RunStatus;
    failureDetails: string | null;
  }): RunTailChunk {
    const totalBytes = buffer.byteLength;
    let start = Math.trunc(fromByte);
    if (!Number.isFinite(start)) {
      start = 0;
    }
    if (maxBytes && maxBytes > 0 && start < 0) {
      start = Math.max(totalBytes - maxBytes, 0);
    } else if (start < 0) {
      start = Math.max(totalBytes + start, 0);
    }
    if (start > totalBytes) {
      start = totalBytes;
    }

    const effectiveMax = maxBytes && maxBytes > 0 ? Math.min(maxBytes, totalBytes) : null;
    const end = effectiveMax ? Math.min(start + effectiveMax, totalBytes) : totalBytes;
    const slice = buffer.subarray(start, end);

    return {
      output: slice.toString('utf-8'),
      nextFromByte: start + slice.byteLength,
      startFromByte: start,
      totalBytes,
      hasMoreBefore: start > 0,
      status,
      failureDetails,
    } satisfies RunTailChunk;
  }

  private async collectSummaryMetrics(
    runId: string,
    artifactsDir: string,
  ): Promise<Record<string, number | null> | null> {
    const summaryPath = path.join(artifactsDir, 'summary.json');
    if (!existsSync(toFsPath(summaryPath))) {
      return null;
    }

    let raw: string | null = null;
    try {
      raw = await fs.readFile(toFsPath(summaryPath), 'utf-8');
      const parsed = JSON.parse(raw) as Record<string, unknown>;
      const metrics = this.extractNumericMetrics(parsed);
      return Object.keys(metrics).length > 0 ? metrics : null;
    } catch (error) {
      if (raw) {
        const matches = Array.from(raw.matchAll(/"([^"\\]+)"\s*:\s*(NaN|Infinity|-Infinity)/g));
        if (matches.length > 0) {
          matches.forEach((match) => {
            const field = match[1];
            const value = match[2];
            console.warn(
              `Summary metrics for run ${runId} contain non-finite value ${value} in field ${field}.`,
            );
          });
        } else {
          const fallback = raw.match(/\b(NaN|Infinity|-Infinity)\b/);
          if (fallback) {
            console.warn(
              `Summary metrics for run ${runId} contain non-finite value ${fallback[1]} in an array or nested structure.`,
            );
          }
        }
      }
      console.warn(`Failed to parse summary metrics for run ${runId}:`, error);
      return null;
    }
  }

  private async collectMetricsFromCsv(
    runId: string,
    artifactsDir: string,
  ): Promise<Record<string, number | null> | null> {
    let entries: Awaited<ReturnType<typeof scanArtifacts>>;
    try {
      entries = await scanArtifacts(artifactsDir);
    } catch (error) {
      console.warn(`Failed to enumerate artifacts for run ${runId}:`, error);
      return null;
    }

    const csvFiles = entries.filter(
      (entry) => entry.type === 'file' && entry.relativePath.toLowerCase().endsWith('metrics.csv'),
    );
    if (csvFiles.length === 0) {
      return null;
    }

    const aggregates = new Map<string, { sum: number; count: number }>();
    for (const file of csvFiles) {
      try {
        const content = await fs.readFile(toFsPath(file.path), 'utf-8');
        this.accumulateCsvMetrics(content, aggregates);
      } catch (error) {
        console.warn(`Failed to parse metrics file ${file.path} for run ${runId}:`, error);
      }
    }

    const metrics: Record<string, number | null> = {};
    for (const [key, aggregate] of aggregates.entries()) {
      if (aggregate.count === 0) {
        continue;
      }
      metrics[key] = aggregate.sum / aggregate.count;
    }

    return Object.keys(metrics).length > 0 ? metrics : null;
  }

  private parseCsvLine(line: string): string[] {
    const cells: string[] = [];
    let current = '';
    let inQuotes = false;

    for (let index = 0; index < line.length; index += 1) {
      const char = line[index];
      if (char === '"') {
        if (inQuotes && line[index + 1] === '"') {
          current += '"';
          index += 1;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (char === ',' && !inQuotes) {
        cells.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }

    cells.push(current.trim());
    return cells;
  }

  private accumulateCsvMetrics(
    content: string,
    aggregates: Map<string, { sum: number; count: number }>,
  ) {
    const lines = content
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line.length > 0);

    if (lines.length < 2) {
      return;
    }

    const header = this.parseCsvLine(lines[0]);

    for (let i = 1; i < lines.length; i += 1) {
      const cells = this.parseCsvLine(lines[i]);

      header.forEach((column, index) => {
        const key = column.trim();
        if (!key) {
          return;
        }

        const rawValue = (cells[index] ?? '').trim();
        if (!rawValue) {
          return;
        }

        const numeric = Number(rawValue);
        if (!Number.isFinite(numeric)) {
          return;
        }

        const entry = aggregates.get(key) ?? { sum: 0, count: 0 };
        entry.sum += numeric;
        entry.count += 1;
        aggregates.set(key, entry);
      });
    }
  }

  private extractNumericMetrics(payload: Record<string, unknown>): Record<string, number | null> {
    const metrics: Record<string, number | null> = {};
    for (const [key, value] of Object.entries(payload)) {
      if (typeof value === 'number') {
        metrics[key] = Number.isFinite(value) ? value : null;
      } else if (typeof value === 'boolean') {
        metrics[key] = value ? 1 : 0;
      }
    }
    return metrics;
  }

  private resolveRunRecord(runId: string): RunRecord {
    const [record] = fetchRuns(this.registry, { id: runId, limit: 1 });
    if (record) {
      return record;
    }

    const context = this.runs.get(runId);
    if (!context) {
      throw new Error(`Run ${runId} not found`);
    }

    return {
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
      metrics: null,
    } satisfies RunRecord;
  }
}

