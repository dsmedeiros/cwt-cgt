import { promises as fs } from 'node:fs';
import path from 'node:path';
import chokidar from 'chokidar';

export type ArtifactFile = {
  path: string;
  relativePath: string;
  updatedAt: number;
  type: 'file' | 'directory';
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

export const watchArtifacts = (root: string, onChange: (file: ArtifactFile) => void) => {
  const watcher = chokidar.watch(root, { ignoreInitial: true });

  watcher.on('add', async (filePath) => {
    const stat = await fs.stat(toFsPath(filePath));
    onChange({
      path: filePath,
      relativePath: path.relative(root, filePath),
      updatedAt: stat.mtimeMs,
      type: 'file',
    });
  });

  watcher.on('change', async (filePath) => {
    const stat = await fs.stat(toFsPath(filePath));
    onChange({
      path: filePath,
      relativePath: path.relative(root, filePath),
      updatedAt: stat.mtimeMs,
      type: 'file',
    });
  });

  return watcher;
};
