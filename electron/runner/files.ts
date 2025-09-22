import fs from 'fs';
import path from 'path';
import chokidar from 'chokidar';

const ARTIFACTS_ROOT = path.join(process.cwd(), 'artifacts');
const IGNORE_SEGMENT = '_logs';
const UPDATE_EVENT = 'artifacts.updated';
const DEBOUNCE_MS = 500;

export type ArtifactType = 'file' | 'directory';

export interface ArtifactNode {
  path: string;
  type: ArtifactType;
  size: number;
  mtime: number;
  children?: ArtifactNode[];
}

let watcher: chokidar.FSWatcher | null = null;
let pendingPaths: Set<string> | null = null;
let debounceHandle: NodeJS.Timeout | null = null;
interface BrowserWindowLike {
  isDestroyed(): boolean;
  webContents: {
    send(channel: string, ...args: unknown[]): void;
  };
}

interface ElectronLike {
  BrowserWindow?: {
    getAllWindows(): BrowserWindowLike[];
  };
}

let electronModule: ElectronLike | null | undefined;

function normalizeRelativePath(fullPath: string): string | null {
  const relative = path.relative(ARTIFACTS_ROOT, fullPath);
  if (relative === '') {
    return '';
  }
  if (relative.startsWith('..') || path.isAbsolute(relative)) {
    return null;
  }
  return relative.split(path.sep).join('/');
}

function shouldIgnore(fullPath: string): boolean {
  const relative = normalizeRelativePath(fullPath);
  if (relative === null) {
    return true;
  }
  if (relative === '') {
    return false;
  }
  return relative === IGNORE_SEGMENT || relative.startsWith(`${IGNORE_SEGMENT}/`);
}

function getBrowserWindows(): BrowserWindowLike[] {
  if (electronModule === undefined) {
    try {
      electronModule = require('electron') as ElectronLike;
    } catch (error) {
      electronModule = null;
    }
  }

  if (!electronModule || !electronModule.BrowserWindow) {
    return [];
  }

  return electronModule.BrowserWindow.getAllWindows();
}

function emitArtifactUpdate(paths: string[]): void {
  if (!paths.length) {
    return;
  }

  const windows = getBrowserWindows();
  for (const window of windows) {
    if (!window.isDestroyed()) {
      window.webContents.send(UPDATE_EVENT, paths);
    }
  }
}

function flushPendingPaths(): void {
  if (!pendingPaths) {
    return;
  }

  const paths = Array.from(pendingPaths).sort();
  pendingPaths.clear();
  pendingPaths = null;
  debounceHandle = null;
  emitArtifactUpdate(paths);
}

function scheduleEmit(relativePath: string): void {
  if (!pendingPaths) {
    pendingPaths = new Set();
  }
  pendingPaths.add(relativePath);

  if (debounceHandle) {
    clearTimeout(debounceHandle);
  }

  debounceHandle = setTimeout(() => {
    flushPendingPaths();
  }, DEBOUNCE_MS);
}

function handleWatcherEvent(fullPath: string): void {
  const relative = normalizeRelativePath(fullPath);
  if (!relative) {
    return;
  }

  if (relative === '' || relative.startsWith(`${IGNORE_SEGMENT}/`) || relative === IGNORE_SEGMENT) {
    return;
  }

  scheduleEmit(relative);
}

function startWatcher(): void {
  if (watcher || process.env.NODE_ENV === 'test') {
    return;
  }

  watcher = chokidar.watch(ARTIFACTS_ROOT, {
    ignoreInitial: true,
    ignored: (watchPath) => shouldIgnore(watchPath),
  });

  const changeEvents = ['add', 'change', 'unlink', 'addDir', 'unlinkDir'] as const;

  for (const event of changeEvents) {
    watcher.on(event, (changedPath: string) => {
      handleWatcherEvent(changedPath);
    });
  }

  watcher.on('error', () => {
    // Ignore watcher errors. They will be retried automatically by chokidar.
  });
}

startWatcher();

async function buildArtifactNode(fullPath: string): Promise<ArtifactNode | null> {
  const relative = normalizeRelativePath(fullPath);
  if (!relative) {
    return null;
  }

  if (relative === IGNORE_SEGMENT || relative.startsWith(`${IGNORE_SEGMENT}/`)) {
    return null;
  }

  const stats = await fs.promises.stat(fullPath);

  if (stats.isDirectory()) {
    const children = await readDirectory(fullPath);
    return {
      path: relative,
      type: 'directory',
      size: stats.size,
      mtime: stats.mtimeMs,
      children,
    };
  }

  if (stats.isFile()) {
    return {
      path: relative,
      type: 'file',
      size: stats.size,
      mtime: stats.mtimeMs,
    };
  }

  return null;
}

async function readDirectory(dirPath: string): Promise<ArtifactNode[]> {
  let dirents: fs.Dirent[];
  try {
    dirents = await fs.promises.readdir(dirPath, { withFileTypes: true });
  } catch (error) {
    return [];
  }

  const nodes: ArtifactNode[] = [];

  for (const dirent of dirents) {
    const fullPath = path.join(dirPath, dirent.name);
    const node = await buildArtifactNode(fullPath);
    if (node) {
      nodes.push(node);
    }
  }

  nodes.sort((a, b) => a.path.localeCompare(b.path));
  return nodes;
}

function resolveTarget(under?: string): string {
  if (!under) {
    return ARTIFACTS_ROOT;
  }

  const target = path.resolve(ARTIFACTS_ROOT, under);
  const relative = path.relative(ARTIFACTS_ROOT, target);
  if (relative.startsWith('..') || path.isAbsolute(relative)) {
    throw new Error('Requested path is outside the artifacts directory.');
  }

  return target;
}

export async function listArtifacts(under?: string): Promise<ArtifactNode[]> {
  const target = resolveTarget(under);

  if (!fs.existsSync(target)) {
    return [];
  }

  const stats = await fs.promises.stat(target);

  if (stats.isDirectory()) {
    if (shouldIgnore(target)) {
      return [];
    }
    const relative = normalizeRelativePath(target);
    if (!relative) {
      return readDirectory(target);
    }
    const node = await buildArtifactNode(target);
    return node ? [node] : [];
  }

  const node = await buildArtifactNode(target);
  return node ? [node] : [];
}

export function ensureArtifactsWatcher(): void {
  startWatcher();
}

