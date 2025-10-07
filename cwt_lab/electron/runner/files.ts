import { promises as fs } from 'node:fs';
import path from 'node:path';
import chokidar, { type WatchOptions } from 'chokidar';

export type ArtifactFile = {
  path: string;
  relativePath: string;
  updatedAt: number;
  type: 'file' | 'directory';
};

export type ArtifactChangeEvent = ArtifactFile & {
  kind: 'add' | 'change' | 'unlink' | 'addDir' | 'unlinkDir';
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

const scanRecursive = async (root: string, base: string): Promise<ArtifactFile[]> => {
  const entries = await fs.readdir(toFsPath(root), { withFileTypes: true });
  entries.sort((a, b) => a.name.localeCompare(b.name));
  const nodes: ArtifactFile[] = [];

  for (const entry of entries) {
    const entryPath = path.join(root, entry.name);
    const relativePath = path.relative(base, entryPath);
    const stat = await fs.stat(toFsPath(entryPath));

    if (entry.isDirectory()) {
      nodes.push({
        path: entryPath,
        relativePath,
        updatedAt: stat.mtimeMs,
        type: 'directory',
      });
      nodes.push(...(await scanRecursive(entryPath, base)));
    } else if (entry.isFile()) {
      nodes.push({
        path: entryPath,
        relativePath,
        updatedAt: stat.mtimeMs,
        type: 'file',
      });
    }
  }

  return nodes;
};

export const scanArtifacts = async (root: string): Promise<ArtifactFile[]> => scanRecursive(root, root);

const makeChangeEvent = (
  root: string,
  kind: ArtifactChangeEvent['kind'],
  filePath: string,
  type: ArtifactFile['type'],
  updatedAt?: number,
): ArtifactChangeEvent => ({
  path: filePath,
  relativePath: path.relative(root, filePath),
  updatedAt: updatedAt ?? Date.now(),
  type,
  kind,
});

export const watchArtifacts = (
  root: string,
  onChange: (event: ArtifactChangeEvent) => void,
  options: WatchOptions = {},
) => {
  const watcher = chokidar.watch(root, { ignoreInitial: true, ...options });

  const emitWithStat = async (
    kind: ArtifactChangeEvent['kind'],
    filePath: string,
    type: ArtifactFile['type'],
  ) => {
    try {
      const stat = await fs.stat(toFsPath(filePath));
      onChange(makeChangeEvent(root, kind, filePath, type, stat.mtimeMs));
    } catch (error) {
      if ((error as NodeJS.ErrnoException)?.code !== 'ENOENT') {
        console.warn('Failed to stat artifact change:', error);
      }
    }
  };

  watcher.on('add', (filePath) => {
    void emitWithStat('add', filePath, 'file');
  });

  watcher.on('change', (filePath) => {
    void emitWithStat('change', filePath, 'file');
  });

  watcher.on('unlink', (filePath) => {
    onChange(makeChangeEvent(root, 'unlink', filePath, 'file'));
  });

  watcher.on('addDir', (filePath) => {
    void emitWithStat('addDir', filePath, 'directory');
  });

  watcher.on('unlinkDir', (filePath) => {
    onChange(makeChangeEvent(root, 'unlinkDir', filePath, 'directory'));
  });

  return watcher;
};
