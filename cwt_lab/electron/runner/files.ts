import { promises as fs } from 'node:fs';
import path from 'node:path';
import chokidar from 'chokidar';

export type ArtifactFile = {
  path: string;
  updatedAt: number;
};

export const scanArtifacts = async (root: string): Promise<ArtifactFile[]> => {
  const entries = await fs.readdir(root, { withFileTypes: true });
  const files: ArtifactFile[] = [];

  for (const entry of entries) {
    if (!entry.isFile()) {
      continue;
    }

    const filePath = path.join(root, entry.name);
    const stat = await fs.stat(filePath);
    files.push({ path: filePath, updatedAt: stat.mtimeMs });
  }

  return files;
};

export const watchArtifacts = (root: string, onChange: (file: ArtifactFile) => void) => {
  const watcher = chokidar.watch(root, { ignoreInitial: true });

  watcher.on('add', async (filePath) => {
    const stat = await fs.stat(filePath);
    onChange({ path: filePath, updatedAt: stat.mtimeMs });
  });

  watcher.on('change', async (filePath) => {
    const stat = await fs.stat(filePath);
    onChange({ path: filePath, updatedAt: stat.mtimeMs });
  });

  return watcher;
};
