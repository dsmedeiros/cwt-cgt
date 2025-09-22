import { spawn, SpawnOptions, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import fs from 'fs';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';

export type RunStatus = 'queued' | 'running' | 'done' | 'error' | 'aborted';

export interface CreateRunOptions {
  label?: string;
  phase?: string;
  experiment?: string;
  cmd: string;
  args?: string[];
  cwd?: string;
  env?: NodeJS.ProcessEnv;
  seed?: number;
  paramsJson?: unknown;
}

export interface TailResult {
  stdout: string;
  stderr: string;
  stdoutNextByte: number;
  stderrNextByte: number;
}

interface RunState {
  id: string;
  status: RunStatus;
  child?: ChildProcess;
  stdoutPath: string;
  stderrPath: string;
  aborted: boolean;
}

interface LifecycleEvent {
  runId: string;
  status: RunStatus;
}

const LOG_ROOT = path.join(process.cwd(), 'artifacts', '_logs');

const lifecycleEmitter = new EventEmitter();
const runs = new Map<string, RunState>();

function ensureLogDir(runId: string): { stdoutPath: string; stderrPath: string } {
  const runDir = path.join(LOG_ROOT, runId);
  fs.mkdirSync(runDir, { recursive: true });
  const stdoutPath = path.join(runDir, 'stdout.txt');
  const stderrPath = path.join(runDir, 'stderr.txt');
  if (!fs.existsSync(stdoutPath)) {
    fs.writeFileSync(stdoutPath, '');
  }
  if (!fs.existsSync(stderrPath)) {
    fs.writeFileSync(stderrPath, '');
  }
  return { stdoutPath, stderrPath };
}

function emitLifecycle(event: LifecycleEvent): void {
  lifecycleEmitter.emit('status', event);
}

function appendStream(stream: NodeJS.ReadableStream | null, filePath: string): void {
  if (!stream) return;
  const writeStream = fs.createWriteStream(filePath, { flags: 'a', encoding: 'utf8' });
  stream.setEncoding('utf8');
  const closeStream = () => {
    if (!writeStream.closed) {
      writeStream.end();
    }
  };
  stream.on('data', (chunk) => {
    writeStream.write(chunk);
  });
  stream.on('end', closeStream);
  stream.on('close', closeStream);
  stream.on('error', closeStream);
}

function buildSpawnOptions(options: CreateRunOptions): SpawnOptions {
  const spawnOptions: SpawnOptions = {
    cwd: options.cwd ?? process.cwd(),
    env: options.env ? { ...process.env, ...options.env } : process.env,
    windowsHide: true,
  };

  if (process.platform !== 'win32') {
    spawnOptions.detached = true;
  }

  return spawnOptions;
}

function handleProcessLifecycle(runId: string, child: ChildProcess, state: RunState): void {
  child.once('spawn', () => {
    state.status = 'running';
    emitLifecycle({ runId, status: 'running' });
  });

  child.once('error', () => {
    state.status = state.aborted ? 'aborted' : 'error';
    emitLifecycle({ runId, status: state.status });
    runs.delete(runId);
  });

  child.once('exit', (code, signal) => {
    if (state.aborted) {
      state.status = 'aborted';
    } else if (code === 0) {
      state.status = 'done';
    } else {
      state.status = 'error';
    }
    emitLifecycle({ runId, status: state.status });
    runs.delete(runId);
  });
}

export function createRun(options: CreateRunOptions): string {
  const runId = uuidv4();
  emitLifecycle({ runId, status: 'queued' });

  const { stdoutPath, stderrPath } = ensureLogDir(runId);
  const spawnOptions = buildSpawnOptions(options);

  const child = spawn(options.cmd, options.args ?? [], spawnOptions);

  const state: RunState = {
    id: runId,
    status: 'queued',
    child,
    stdoutPath,
    stderrPath,
    aborted: false,
  };

  runs.set(runId, state);

  appendStream(child.stdout, stdoutPath);
  appendStream(child.stderr, stderrPath);

  handleProcessLifecycle(runId, child, state);

  return runId;
}

export function abort(runId: string): boolean {
  const state = runs.get(runId);
  if (!state || !state.child) {
    return false;
  }

  const child = state.child;
  state.aborted = true;

  if (process.platform === 'win32') {
    if (child.pid) {
      spawn('taskkill', ['/PID', String(child.pid), '/T', '/F']);
    }
  } else if (child.pid) {
    try {
      process.kill(-child.pid, 'SIGTERM');
    } catch (err) {
      try {
        process.kill(child.pid, 'SIGTERM');
      } catch (innerErr) {
        // ignore if the process is already terminated
      }
    }
  }

  return true;
}

function readSlice(filePath: string, fromByte: number): { content: string; nextByte: number } {
  if (!fs.existsSync(filePath)) {
    return { content: '', nextByte: fromByte };
  }

  const stats = fs.statSync(filePath);
  const endByte = stats.size;
  if (fromByte >= endByte) {
    return { content: '', nextByte: endByte };
  }

  const fd = fs.openSync(filePath, 'r');
  try {
    const length = endByte - fromByte;
    const buffer = Buffer.alloc(length);
    fs.readSync(fd, buffer, 0, length, fromByte);
    return { content: buffer.toString('utf8'), nextByte: endByte };
  } finally {
    fs.closeSync(fd);
  }
}

export function tail(runId: string, fromByte = 0): TailResult {
  const state = runs.get(runId);
  const stdoutPath = state?.stdoutPath ?? path.join(LOG_ROOT, runId, 'stdout.txt');
  const stderrPath = state?.stderrPath ?? path.join(LOG_ROOT, runId, 'stderr.txt');

  const stdoutSlice = readSlice(stdoutPath, fromByte);
  const stderrSlice = readSlice(stderrPath, fromByte);

  return {
    stdout: stdoutSlice.content,
    stderr: stderrSlice.content,
    stdoutNextByte: stdoutSlice.nextByte,
    stderrNextByte: stderrSlice.nextByte,
  };
}

export function onLifecycle(listener: (event: LifecycleEvent) => void): () => void {
  lifecycleEmitter.on('status', listener);
  return () => lifecycleEmitter.off('status', listener);
}
