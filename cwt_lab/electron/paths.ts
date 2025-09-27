import { existsSync } from 'node:fs';
import path from 'node:path';

const MAX_ASCENT_STEPS = 10;
const SIM_DIRECTORY = 'cwt-sim';

const findRepoRoot = (): string => {
  let current = path.resolve(__dirname);

  for (let step = 0; step < MAX_ASCENT_STEPS; step += 1) {
    if (existsSync(path.join(current, SIM_DIRECTORY))) {
      return current;
    }

    const parent = path.dirname(current);
    if (parent === current) {
      break;
    }
    current = parent;
  }

  // Fall back to the historical behaviour so that we never throw during
  // module evaluation – this will still surface obvious errors when the
  // paths are actually used.
  return path.resolve(__dirname, '..', '..');
};

const repoRoot = findRepoRoot();
const cwtSimRoot = path.join(repoRoot, SIM_DIRECTORY);
const artifactsRoot = path.join(repoRoot, 'artifacts');

export { artifactsRoot, cwtSimRoot, repoRoot };
