import { promises as fs } from 'node:fs';
import path from 'node:path';

import JSZip from 'jszip';

import type {
  BaselineAlignmentProgressEvent,
  BaselineAlignmentResult,
  BaselineModel,
  BaselineRunPayload,
  BaselineRunResult,
} from '../../renderer/types/ipc';
import type { PythonEnvironment } from '../runner/env';
import { baselineRunPayloadSchema, executeBaselineRun } from './runService';

const DEFAULT_AXIS_MAP_PATH = 'cwt-sim/baselines/axis_map.yml';
const GRID_SIZE = 15;

const formatTimestamp = (value: number): string => {
  const date = new Date(value);
  const pad = (input: number) => input.toString().padStart(2, '0');
  const year = date.getUTCFullYear();
  const month = pad(date.getUTCMonth() + 1);
  const day = pad(date.getUTCDate());
  const hours = pad(date.getUTCHours());
  const minutes = pad(date.getUTCMinutes());
  const seconds = pad(date.getUTCSeconds());
  return `${year}${month}${day}T${hours}${minutes}${seconds}Z`;
};

type AlignmentRunPlan = {
  model: BaselineModel;
  label: string;
  seed: number;
  args: string[];
};

const ALIGNMENT_RUNS: AlignmentRunPlan[] = [
  {
    model: 'ising',
    label: 'Ising lattice sweep',
    seed: 1101,
    args: [
      '--grid-size',
      String(GRID_SIZE),
      String(GRID_SIZE),
      '--lattice-size',
      String(GRID_SIZE),
      String(GRID_SIZE),
    ],
  },
  {
    model: 'kuramoto',
    label: 'Kuramoto synchrony sweep',
    seed: 2202,
    args: ['--grid-size', String(GRID_SIZE), String(GRID_SIZE)],
  },
  {
    model: 'percolation',
    label: 'Percolation threshold sweep',
    seed: 3303,
    args: [
      '--grid-size',
      String(GRID_SIZE),
      String(GRID_SIZE),
      '--lattice-size',
      String(GRID_SIZE),
      String(GRID_SIZE),
    ],
  },
  {
    model: 'sis',
    label: 'SIS contagion sweep',
    seed: 4404,
    args: ['--grid-size', String(GRID_SIZE), String(GRID_SIZE)],
  },
];

const toPosixPath = (value: string) => value.replace(/\\/g, '/');

const collectFiles = async (
  folder: JSZip,
  directory: string,
  base = directory,
): Promise<void> => {
  const entries = await fs.readdir(directory, { withFileTypes: true });
  for (const entry of entries) {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      await collectFiles(folder, entryPath, base);
      continue;
    }
    if (!entry.isFile()) {
      continue;
    }
    const relative = toPosixPath(path.relative(base, entryPath));
    const data = await fs.readFile(entryPath);
    folder.file(relative, data);
  }
};

type RunBaselineFn = (
  payload: BaselineRunPayload,
  options: Parameters<typeof executeBaselineRun>[1],
) => Promise<BaselineRunResult>;

type AlignmentOptions = {
  env: PythonEnvironment;
  artifactsRoot: string;
  onProgress?: (event: BaselineAlignmentProgressEvent) => void;
  timestampFn?: () => number;
  zipFactory?: () => JSZip;
  runBaseline?: RunBaselineFn;
};

const emit = (
  listener: AlignmentOptions['onProgress'],
  event: BaselineAlignmentProgressEvent,
) => {
  if (!listener) {
    return;
  }
  listener(event);
};

const buildReadme = (runs: BaselineAlignmentResult['runs']): string => {
  const header = `# Theory alignment baselines\n\n`;
  const intro =
    'This archive bundles four deterministic baseline sweeps used to demonstrate how the lab aligns coarse Wilson theory predictions with classical reference models. '
    + 'Each run scans a 15×15 grid with loop analysis disabled to emphasise direct observable comparisons.\n\n';
  const tableHeader = '| # | Model | Seed | Relative path |\n| --- | --- | --- | --- |\n';
  const rows = runs
    .map(
      (run, index) =>
        `| ${index + 1} | ${run.model} | ${run.seed} | ${run.relativePath} |`,
    )
    .join('\n');
  const footer =
    '\n\nAll four sweeps disable loop reconstruction so the exported heatmaps and metrics can be compared directly to analytic baselines. '
    + 'Re-run the theory alignment demo from the Baselines pane to regenerate this bundle with fresh timestamps.';
  return `${header}${intro}${tableHeader}${rows}\n${footer}\n`;
};

export const runBaselineAlignment = async (
  options: AlignmentOptions,
): Promise<BaselineAlignmentResult> => {
  const { env, artifactsRoot } = options;
  const runBaseline = options.runBaseline ?? executeBaselineRun;
  const now = options.timestampFn ?? Date.now;
  const createZip = options.zipFactory ?? (() => new JSZip());
  const exportsRoot = path.join(artifactsRoot, '_exports');

  await fs.mkdir(exportsRoot, { recursive: true });

  emit(options.onProgress, { kind: 'start', totalRuns: ALIGNMENT_RUNS.length });

  const startedAt = now();
  const runSummaries: BaselineAlignmentResult['runs'] = [];

  for (let index = 0; index < ALIGNMENT_RUNS.length; index += 1) {
    const plan = ALIGNMENT_RUNS[index];
    emit(options.onProgress, {
      kind: 'run-start',
      index,
      totalRuns: ALIGNMENT_RUNS.length,
      model: plan.model,
      label: plan.label,
      seed: plan.seed,
    });

    const payload = baselineRunPayloadSchema.parse({
      model: plan.model,
      axisMap: DEFAULT_AXIS_MAP_PATH,
      mapToCwt: true,
      seed: String(plan.seed),
      args: plan.args,
    });

    let result: BaselineRunResult;
    try {
      result = await runBaseline(payload, { env, artifactsRoot });
    } catch (error) {
      emit(options.onProgress, {
        kind: 'run-error',
        index,
        totalRuns: ALIGNMENT_RUNS.length,
        model: plan.model,
        label: plan.label,
        message: (error as Error).message ?? 'Baseline run failed',
      });
      throw error;
    }

    const artifactsDir = result.outputDir ?? result.artifactsDir;
    emit(options.onProgress, {
      kind: 'run-complete',
      index,
      totalRuns: ALIGNMENT_RUNS.length,
      model: plan.model,
      label: plan.label,
      runId: result.runId,
      artifactsDir,
    });

    runSummaries.push({
      index,
      model: plan.model,
      label: plan.label,
      runId: result.runId,
      artifactsDir,
      relativePath: `${plan.model}/${path.basename(artifactsDir)}`,
      seed: plan.seed,
      args: plan.args.slice(),
    });
  }

  emit(options.onProgress, { kind: 'packing', totalRuns: ALIGNMENT_RUNS.length });

  const completedAt = now();
  const exportId = `baselines_alignment_${formatTimestamp(startedAt)}`;
  const zip = createZip();
  const root = zip.folder(exportId);
  if (!root) {
    throw new Error('Failed to create export root in zip archive.');
  }

  root.file('README.md', buildReadme(runSummaries));

  for (const summary of runSummaries) {
    const folder = root.folder(summary.relativePath);
    if (!folder) {
      throw new Error(`Failed to create zip folder for ${summary.relativePath}`);
    }
    await collectFiles(folder, summary.artifactsDir);
  }

  const zipBuffer = await zip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE' });
  const zipPath = path.join(exportsRoot, `${exportId}.zip`);
  await fs.writeFile(zipPath, zipBuffer);

  emit(options.onProgress, { kind: 'complete', totalRuns: ALIGNMENT_RUNS.length, zipPath, exportId });

  return {
    exportId,
    zipPath,
    startedAt,
    completedAt,
    runs: runSummaries,
    readmePath: path.join(exportId, 'README.md'),
  };
};

export type { BaselineAlignmentProgressEvent } from '../../renderer/types/ipc';
