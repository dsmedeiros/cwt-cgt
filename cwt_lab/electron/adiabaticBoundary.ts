import { promises as fs } from 'node:fs';
import path from 'node:path';

import { v4 as uuidv4 } from 'uuid';

import type { AdiabaticBoundaryResult, AdiabaticBoundaryPoint, AdiabaticHistogram, AdiabaticSurfaceSample } from '../shared/adiabatic';
import type { RunManager } from './runner/runManager';
import { buildArgsFromParams } from './runner/args';

const GENERIC_FAILURE_MESSAGE_PATTERN =
  /^(run failed for an unknown reason\.|process exited with code \d+(?: after signal .*?)?\.)$/i;
export const MISSING_GRAPH_PARAMETER_HINT_PATTERN = /missing required graph parameters/i;

const isGenericFailureMessage = (message: string | null | undefined): boolean =>
  typeof message === 'string' && GENERIC_FAILURE_MESSAGE_PATTERN.test(message.trim());

const parseMaybeNumber = (value: string): number | null => {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }

  const lowered = trimmed.toLowerCase();
  if (lowered === 'nan' || lowered === 'none' || lowered === 'null') {
    return null;
  }

  const parsed = Number(trimmed);
  if (!Number.isFinite(parsed)) {
    return null;
  }

  return parsed;
};

const parseSurfaceCsv = async (filePath: string): Promise<AdiabaticSurfaceSample[]> => {
  const content = await fs.readFile(filePath, 'utf-8');
  const lines = content.split(/\r?\n/).map((line) => line.trim());
  const rows = lines.filter((line) => line.length > 0);
  if (rows.length <= 1) {
    return [];
  }

  const data: AdiabaticSurfaceSample[] = [];
  for (const row of rows.slice(1)) {
    const cols = row.split(',');
    if (cols.length < 8) {
      continue;
    }

    const extent = parseMaybeNumber(cols[0]);
    const steps = parseMaybeNumber(cols[1]);
    if (extent == null || steps == null) {
      continue;
    }

    data.push({
      extent,
      steps: Math.round(steps),
      flux: parseMaybeNumber(cols[2]),
      area: parseMaybeNumber(cols[3]),
      kappa1: parseMaybeNumber(cols[4]),
      readout: parseMaybeNumber(cols[5]),
      fsMean: parseMaybeNumber(cols[6]),
      fsP95: parseMaybeNumber(cols[7]),
    });
  }

  return data.sort((a, b) => (a.extent !== b.extent ? a.extent - b.extent : a.steps - b.steps));
};

const parseBoundaryCsv = async (filePath: string): Promise<AdiabaticBoundaryPoint[]> => {
  const content = await fs.readFile(filePath, 'utf-8');
  const lines = content.split(/\r?\n/).map((line) => line.trim());
  const rows = lines.filter((line) => line.length > 0);
  if (rows.length <= 1) {
    return [];
  }

  const points: AdiabaticBoundaryPoint[] = [];
  for (const row of rows.slice(1)) {
    const cols = row.split(',');
    if (cols.length < 5) {
      continue;
    }

    const extent = parseMaybeNumber(cols[0]);
    if (extent == null) {
      continue;
    }

    const boundarySteps = parseMaybeNumber(cols[1]);
    points.push({
      extent,
      boundarySteps: boundarySteps != null ? Math.round(boundarySteps) : null,
      referenceKappa: parseMaybeNumber(cols[2]),
      boundaryKappa: parseMaybeNumber(cols[3]),
      boundaryFsP95: parseMaybeNumber(cols[4]),
    });
  }

  return points.sort((a, b) => a.extent - b.extent);
};

const parseHistograms = async (filePath: string): Promise<AdiabaticHistogram[]> => {
  const content = await fs.readFile(filePath, 'utf-8');
  if (!content.trim()) {
    return [];
  }

  const parsed = JSON.parse(content) as Record<string, unknown>;
  const histograms: AdiabaticHistogram[] = [];
  for (const [key, value] of Object.entries(parsed)) {
    if (!Array.isArray(value)) {
      continue;
    }

    const match = /extent=([^|]+)\|steps=([^|]+)/.exec(key);
    if (!match) {
      continue;
    }

    const extent = parseMaybeNumber(match[1] ?? '');
    const steps = parseMaybeNumber(match[2] ?? '');
    if (extent == null || steps == null) {
      continue;
    }

    const bins = value
      .map((entry) => (typeof entry === 'number' ? entry : Number(entry)))
      .filter((entry) => Number.isFinite(entry)) as number[];

    histograms.push({ extent, steps: Math.round(steps), bins });
  }

  return histograms.sort((a, b) => (a.extent !== b.extent ? a.extent - b.extent : a.steps - b.steps));
};

const pickRecommendation = (
  boundary: AdiabaticBoundaryPoint[],
): { extent: number; steps: number; fsP95: number | null } | null => {
  const candidates = boundary.filter((point) => point.boundarySteps != null);
  if (candidates.length === 0) {
    return null;
  }

  const sorted = [...candidates].sort((a, b) => {
    if (a.extent !== b.extent) {
      return b.extent - a.extent;
    }
    return (a.boundarySteps ?? 0) - (b.boundarySteps ?? 0);
  });
  const choice = sorted[0];
  return {
    extent: choice.extent,
    steps: choice.boundarySteps ?? 0,
    fsP95: choice.boundaryFsP95 ?? null,
  };
};

const summarizeFsGuard = (boundary: AdiabaticBoundaryPoint[], recommendationFs: number | null) => {
  const fsValues = boundary
    .map((point) => point.boundaryFsP95)
    .filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
  const maxObserved = fsValues.length > 0 ? Math.max(...fsValues) : null;
  return {
    recommended: recommendationFs ?? (fsValues.length > 0 ? Math.min(...fsValues) : null),
    maxObserved,
  };
};

const NON_CLI_PARAM_KEYS = new Set([
  'hotspotId',
  'graphId',
  'graphParams',
  'graphOverride',
]);

const deriveGraphOverrideCliParams = (
  params: Record<string, unknown> | undefined,
): Record<string, unknown> => {
  if (!params) {
    return {};
  }

  const cliParams: Record<string, unknown> = {};

  const setGraphId = (value: unknown) => {
    if (cliParams['graphId'] !== undefined) {
      return;
    }
    if (typeof value !== 'string') {
      return;
    }

    const trimmed = value.trim();
    if (trimmed.length === 0) {
      return;
    }

    cliParams['graphId'] = trimmed;
  };

  const setGraphParams = (value: unknown) => {
    if (cliParams['graphParams'] !== undefined) {
      return;
    }

    if (value == null) {
      return;
    }

    if (typeof value === 'string') {
      const trimmed = value.trim();
      if (trimmed.length > 0) {
        cliParams['graphParams'] = trimmed;
      }
      return;
    }

    if (Array.isArray(value)) {
      cliParams['graphParams'] = value.map((entry) => entry);
      return;
    }

    if (typeof value === 'object') {
      cliParams['graphParams'] = { ...(value as Record<string, unknown>) };
    }
  };

  if ('graphId' in params) {
    setGraphId(params['graphId']);
  }

  if ('graphParams' in params) {
    setGraphParams(params['graphParams']);
  }

  const rawOverride = params['graphOverride'];
  if (rawOverride && typeof rawOverride === 'object') {
    const overrideRecord = rawOverride as Record<string, unknown>;

    const identifierCandidates = [
      overrideRecord['identifier'],
      overrideRecord['graphId'],
      overrideRecord['id'],
    ];
    for (const candidate of identifierCandidates) {
      if (candidate !== undefined) {
        setGraphId(candidate);
      }
    }

    const paramsCandidates = [
      overrideRecord['params'],
      overrideRecord['kwargs'],
      overrideRecord['arguments'],
      overrideRecord['graphParams'],
      overrideRecord['values'],
      overrideRecord['options'],
    ];
    for (const candidate of paramsCandidates) {
      if (candidate !== undefined) {
        setGraphParams(candidate);
      }
    }
  }

  return cliParams;
};

type RunManagerClient = Pick<RunManager, 'createRun' | 'waitForCompletion' | 'tail'>;

export const runAdiabaticBoundary = async (
  runManager: RunManagerClient,
  cwtSimRoot: string,
  artifactsRoot: string,
  params: Record<string, unknown> | undefined,
  options: { experimentDir?: string | null } = {},
): Promise<AdiabaticBoundaryResult> => {
  const resolvedExperimentDir =
    typeof options.experimentDir === 'string' && options.experimentDir.length > 0
      ? options.experimentDir
      : null;

  const root = resolvedExperimentDir ?? artifactsRoot;
  const segments = resolvedExperimentDir
    ? ['phase3', 'adiabatic_boundary', uuidv4()]
    : ['adiabatic_boundary', uuidv4()];
  const outputDir = path.join(root, ...segments);
  await fs.mkdir(outputDir, { recursive: true });

  const cliParams = Object.fromEntries(
    Object.entries(params ?? {}).filter(([key]) => !NON_CLI_PARAM_KEYS.has(key)),
  );

  const args = buildArgsFromParams({ ...cliParams, ...deriveGraphOverrideCliParams(params), outputDir });
  const { runId } = await runManager.createRun(
    'experiments.adiabatic_boundary.run',
    args,
    cwtSimRoot,
    {
      phase: 'phase3',
      experiment: 'adiabatic_boundary',
      label: 'Adiabatic boundary sweep',
    },
    { artifactsDir: resolvedExperimentDir ?? undefined },
  );

  const completion = await runManager.waitForCompletion(runId);
  if (completion.status !== 'complete' || completion.exitCode !== 0) {
    let failureReason: string | null =
      typeof completion.error === 'string' ? completion.error.trim() : null;
    if (failureReason === '') {
      failureReason = null;
    }
    let tailSnippet: string | null = null;
    let friendlyTailHint: string | null = null;
    let tailError: string | null = null;

    try {
      const tailChunk = await runManager.tail(runId, -8_192, 8_192);
      if (tailChunk.failureDetails) {
        const trimmedFailureDetails = tailChunk.failureDetails.trim();
        failureReason = trimmedFailureDetails.length > 0 ? trimmedFailureDetails : failureReason;
      }

      const trimmedOutput = tailChunk.output.trim();
      if (trimmedOutput) {
        const recentLines = trimmedOutput.split(/\r?\n/).slice(-20);
        tailSnippet = recentLines.join('\n');
        const hintLine = recentLines.find((line) =>
          MISSING_GRAPH_PARAMETER_HINT_PATTERN.test(line),
        );
        if (hintLine) {
          friendlyTailHint = hintLine.trim();
        }
      }
    } catch (error) {
      tailError = error instanceof Error ? error.message : String(error);
    }

    const failureReasonLooksGeneric = isGenericFailureMessage(failureReason);

    if (friendlyTailHint && (!failureReason || failureReasonLooksGeneric)) {
      failureReason = friendlyTailHint;
    }

    if (!failureReason) {
      const exitCode = Number.isFinite(completion.exitCode)
        ? completion.exitCode
        : null;
      failureReason = exitCode != null ? `exit code ${exitCode}` : 'unknown error';
    }

    const messageParts = [`adiabatic boundary sweep failed: ${failureReason}`];
    if (tailSnippet) {
      messageParts.push(`Recent output:\n${tailSnippet}`);
    }
    if (tailError) {
      messageParts.push(`Additionally, failed to read run logs: ${tailError}`);
    }

    throw new Error(messageParts.join('\n\n'));
  }

  const surfacePath = path.join(outputDir, 'kappa_surface.csv');
  const histPath = path.join(outputDir, 'fs_histograms.json');
  const boundaryPath = path.join(outputDir, 'boundary.csv');

  const [surface, histograms, boundary] = await Promise.all([
    parseSurfaceCsv(surfacePath),
    parseHistograms(histPath),
    parseBoundaryCsv(boundaryPath),
  ]);

  const recommendation = pickRecommendation(boundary);
  const fsGuard = summarizeFsGuard(boundary, recommendation?.fsP95 ?? null);
  const referenceKappa = boundary.find((point) => point.referenceKappa != null)?.referenceKappa ?? null;

  return {
    runId,
    outputDir,
    surface,
    histograms,
    boundary,
    recommendation,
    fsGuard,
    referenceKappa,
  };
};
