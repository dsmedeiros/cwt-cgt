import * as fs from 'fs';
import * as path from 'path';

export type FeatureName = 'spectral_gap' | 'kuramoto_r' | 'grad_r' | 'trace_g';

export interface FeatureStat {
  name: FeatureName;
  correlation: number | null;
  sampleSize: number;
  hotCount: number;
  coldCount: number;
  meanHot: number | null;
  meanCold: number | null;
}

export interface CorrelateOptions {
  metricsDirs: string[];
  threshold: { mode: 'absolute' | 'percentile'; value: number };
}

export interface Phase2Sample {
  omegaAbs: number | null;
  features: Partial<Record<FeatureName, number | null>>;
}

export interface RocPoint {
  threshold: number;
  tpr: number;
  fpr: number;
}

export interface CorrelateResult {
  features: FeatureStat[];
  auc?: number;
  roc?: { feature: FeatureName; points: RocPoint[] };
  threshold: number | null;
  samples: Phase2Sample[];
}

interface MetricsRow {
  omega_abs: number;
  spectral_gap?: number;
  kuramoto_r?: number;
  grad_r?: number;
  trace_g?: number;
}

interface FeatureAccumulator {
  values: number[];
  labels: number[];
}

const FEATURE_NAMES: FeatureName[] = [
  'spectral_gap',
  'kuramoto_r',
  'grad_r',
  'trace_g',
];

const METRICS_FILENAME = 'metrics.csv';
const MAX_DIRECTORY_DEPTH = 4;

const isMetricsFile = (filePath: string): boolean =>
  path.basename(filePath).toLowerCase() === METRICS_FILENAME;

function discoverMetricsFiles(root: string, maxDepth = MAX_DIRECTORY_DEPTH): string[] {
  const matches = new Set<string>();
  const resolvedRoot = path.resolve(root);

  if (!fs.existsSync(resolvedRoot)) {
    return [];
  }

  try {
    const stat = fs.statSync(resolvedRoot);
    if (stat.isFile()) {
      return isMetricsFile(resolvedRoot) ? [resolvedRoot] : [];
    }
    if (!stat.isDirectory()) {
      return [];
    }
  } catch {
    return [];
  }

  const stack: Array<{ dir: string; depth: number }> = [{ dir: resolvedRoot, depth: 0 }];

  while (stack.length > 0) {
    const current = stack.pop();
    if (!current) {
      continue;
    }

    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(current.dir, { withFileTypes: true });
    } catch {
      continue;
    }

    for (const entry of entries) {
      const entryPath = path.join(current.dir, entry.name);
      if (entry.isFile()) {
        if (isMetricsFile(entryPath)) {
          matches.add(path.resolve(entryPath));
        }
      } else if (entry.isDirectory() && current.depth < maxDepth) {
        stack.push({ dir: entryPath, depth: current.depth + 1 });
      }
    }
  }

  return [...matches];
}

export function correlate({ metricsDirs, threshold }: CorrelateOptions): CorrelateResult {
  const { rows, sources } = loadMetrics(metricsDirs);

  if (sources.length === 0) {
    throw new Error(
      'No metrics.csv files were found under the selected directories. ' +
        'Confirm the Phase-1 run completed and select the graph-level output folders.',
    );
  }

  if (rows.length === 0) {
    return {
      features: FEATURE_NAMES.map((name) => ({
        name,
        correlation: null,
        sampleSize: 0,
        hotCount: 0,
        coldCount: 0,
        meanHot: null,
        meanCold: null,
      })),
      samples: [],
      threshold: null,
    } satisfies CorrelateResult;
  }

  const omegaValues = rows
    .map((row) => row.omega_abs)
    .filter((value) => Number.isFinite(value)) as number[];

  const theta = computeThreshold(omegaValues, threshold);

  const featureData: Record<FeatureName, FeatureAccumulator> = {
    spectral_gap: { values: [], labels: [] },
    kuramoto_r: { values: [], labels: [] },
    grad_r: { values: [], labels: [] },
    trace_g: { values: [], labels: [] },
  };

  const samples = rows.map((row) => {
    const features: Partial<Record<FeatureName, number | null>> = {};
    FEATURE_NAMES.forEach((feature) => {
      const value = row[feature];
      features[feature] = Number.isFinite(value as number) ? (value as number) : null;
    });
    return {
      omegaAbs: Number.isFinite(row.omega_abs) ? row.omega_abs : null,
      features,
    } satisfies Phase2Sample;
  });

  if (!Number.isFinite(theta)) {
    return {
      features: FEATURE_NAMES.map((name) => ({
        name,
        correlation: null,
        sampleSize: 0,
        hotCount: 0,
        coldCount: 0,
        meanHot: null,
        meanCold: null,
      })),
      samples,
      threshold: null,
    } satisfies CorrelateResult;
  }

  rows.forEach((row) => {
    if (!Number.isFinite(row.omega_abs)) {
      return;
    }

    const label = row.omega_abs >= (theta as number) ? 1 : 0;

    FEATURE_NAMES.forEach((feature) => {
      const rawValue = row[feature];
      if (rawValue !== undefined && Number.isFinite(rawValue)) {
        featureData[feature].values.push(rawValue as number);
        featureData[feature].labels.push(label);
      }
    });
  });

  const features = FEATURE_NAMES.map((name) => {
    const data = featureData[name];
    const stats = computePointBiserial(data.values, data.labels);

    return {
      name,
      correlation: stats.correlation,
      sampleSize: data.values.length,
      hotCount: stats.hotCount,
      coldCount: stats.coldCount,
      meanHot: stats.meanHot,
      meanCold: stats.meanCold,
    } satisfies FeatureStat;
  });

  const { auc, bestFeature } = computeBestFeatureAuc(featureData, features);

  const roc =
    bestFeature && auc !== null
      ? {
          feature: bestFeature,
          points: computeRoc(featureData[bestFeature].values, featureData[bestFeature].labels),
        }
      : undefined;

  return {
    features,
    ...(auc === null ? {} : { auc }),
    ...(roc && roc.points.length > 0 ? { roc } : {}),
    threshold: Number.isFinite(theta) ? (theta as number) : null,
    samples,
  } satisfies CorrelateResult;
}

function loadMetrics(metricsDirs: string[]): { rows: MetricsRow[]; sources: string[] } {
  const rows: MetricsRow[] = [];
  const sources = new Set<string>();

  metricsDirs.forEach((dir) => {
    const metricsFiles = discoverMetricsFiles(dir);

    metricsFiles.forEach((metricsPath) => {
      if (sources.has(metricsPath)) {
        return;
      }
      sources.add(metricsPath);

      try {
        const content = fs.readFileSync(metricsPath, 'utf8');
        rows.push(...parseMetricsCsv(content));
      } catch {
        // Skip unreadable files but continue processing other directories.
      }
    });
  });

  return { rows, sources: Array.from(sources) };
}

function parseMetricsCsv(content: string): MetricsRow[] {
  const lines = content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  if (lines.length === 0) {
    return [];
  }

  const header = lines[0].split(',').map((cell) => cell.trim());
  const rows: MetricsRow[] = [];

  for (let i = 1; i < lines.length; i += 1) {
    const cells = lines[i].split(',');

    if (cells.every((cell) => cell.trim().length === 0)) {
      continue;
    }

    const record: MetricsRow = {
      omega_abs: NaN,
    };

    header.forEach((column, index) => {
      const rawValue = (cells[index] ?? '').trim();
      const numericValue = rawValue.length > 0 ? Number(rawValue) : NaN;

      if (column === 'omega_abs') {
        record.omega_abs = numericValue;
      } else if (isFeatureName(column)) {
        record[column] = numericValue;
      }
    });

    rows.push(record);
  }

  return rows;
}

function isFeatureName(value: string): value is FeatureName {
  return (FEATURE_NAMES as string[]).includes(value);
}

function computeThreshold(
  omegaValues: number[],
  threshold: { mode: 'absolute' | 'percentile'; value: number },
): number | null {
  if (threshold.mode === 'absolute') {
    return threshold.value;
  }

  if (omegaValues.length === 0) {
    return null;
  }

  const sorted = [...omegaValues].sort((a, b) => a - b);
  const percentile = Math.min(Math.max(threshold.value, 0), 100);
  const rank = (percentile / 100) * (sorted.length - 1);
  const lowerIndex = Math.floor(rank);
  const upperIndex = Math.ceil(rank);

  if (lowerIndex === upperIndex) {
    return sorted[lowerIndex];
  }

  const weight = rank - lowerIndex;
  return sorted[lowerIndex] * (1 - weight) + sorted[upperIndex] * weight;
}

interface PointBiserialResult {
  correlation: number | null;
  hotCount: number;
  coldCount: number;
  meanHot: number | null;
  meanCold: number | null;
}

function computePointBiserial(values: number[], labels: number[]): PointBiserialResult {
  const n = values.length;

  if (n === 0 || labels.length !== n) {
    return {
      correlation: null,
      hotCount: 0,
      coldCount: 0,
      meanHot: null,
      meanCold: null,
    };
  }

  const hotValues: number[] = [];
  const coldValues: number[] = [];

  for (let i = 0; i < n; i += 1) {
    if (labels[i] === 1) {
      hotValues.push(values[i]);
    } else if (labels[i] === 0) {
      coldValues.push(values[i]);
    } else {
      return {
        correlation: null,
        hotCount: 0,
        coldCount: 0,
        meanHot: null,
        meanCold: null,
      };
    }
  }

  const hotCount = hotValues.length;
  const coldCount = coldValues.length;

  if (hotCount === 0 || coldCount === 0) {
    return {
      correlation: null,
      hotCount,
      coldCount,
      meanHot: hotCount > 0 ? mean(hotValues) : null,
      meanCold: coldCount > 0 ? mean(coldValues) : null,
    };
  }

  const hotMean = mean(hotValues);
  const coldMean = mean(coldValues);
  const overallMean = mean(values);

  const variance = sampleVariance(values, overallMean);
  if (!Number.isFinite(variance) || variance <= 0) {
    return {
      correlation: 0,
      hotCount,
      coldCount,
      meanHot: hotMean,
      meanCold: coldMean,
    };
  }

  const p = hotCount / n;
  const q = coldCount / n;

  const correlation = ((hotMean - coldMean) * Math.sqrt(p * q)) / Math.sqrt(variance);

  return {
    correlation,
    hotCount,
    coldCount,
    meanHot: hotMean,
    meanCold: coldMean,
  };
}

function mean(values: number[]): number {
  if (values.length === 0) {
    return NaN;
  }

  const total = values.reduce((sum, value) => sum + value, 0);
  return total / values.length;
}

function sampleVariance(values: number[], meanValue: number): number {
  if (values.length < 2) {
    return 0;
  }

  const sumOfSquares = values.reduce((sum, value) => {
    const diff = value - meanValue;
    return sum + diff * diff;
  }, 0);

  return sumOfSquares / (values.length - 1);
}

function computeBestFeatureAuc(
  featureData: Record<FeatureName, FeatureAccumulator>,
  features: FeatureStat[],
): { auc: number | null; bestFeature: FeatureName | null } {
  let bestFeature: FeatureName | null = null;
  let bestScore = -Infinity;

  features.forEach((feature) => {
    if (feature.correlation === null) {
      return;
    }

    const score = Math.abs(feature.correlation);
    if (score > bestScore) {
      bestScore = score;
      bestFeature = feature.name;
    }
  });

  if (!bestFeature) {
    return { auc: null, bestFeature: null };
  }

  const selectedFeature: FeatureName = bestFeature;
  const data: FeatureAccumulator = featureData[selectedFeature];

  const auc = computeAuc(data.values, data.labels);
  return { auc, bestFeature };
}

function computeAuc(values: number[], labels: number[]): number | null {
  const n = values.length;
  if (n === 0 || labels.length !== n) {
    return null;
  }

  const pairs = values.map((value, index) => ({
    value,
    label: labels[index],
  }));

  const positives = pairs.filter((pair) => pair.label === 1).length;
  const negatives = pairs.filter((pair) => pair.label === 0).length;

  if (positives === 0 || negatives === 0) {
    return null;
  }

  pairs.sort((a, b) => a.value - b.value);

  let rankSum = 0;
  let index = 0;
  while (index < pairs.length) {
    let j = index + 1;
    while (j < pairs.length && pairs[j].value === pairs[index].value) {
      j += 1;
    }

    const rank = (index + 1 + j) / 2;
    for (let k = index; k < j; k += 1) {
      if (pairs[k].label === 1) {
        rankSum += rank;
      }
    }

    index = j;
  }

  const auc =
    (rankSum - (positives * (positives + 1)) / 2) / (positives * negatives);

  return auc;
}

function computeRoc(values: number[], labels: number[]): RocPoint[] {
  const n = values.length;
  if (n === 0 || labels.length !== n) {
    return [];
  }

  const pairs = values.map((value, index) => ({ value, label: labels[index] }));
  const positives = pairs.filter((pair) => pair.label === 1).length;
  const negatives = pairs.filter((pair) => pair.label === 0).length;

  if (positives === 0 || negatives === 0) {
    return [];
  }

  pairs.sort((a, b) => b.value - a.value);

  const points: RocPoint[] = [{ threshold: Number.POSITIVE_INFINITY, tpr: 0, fpr: 0 }];
  let tp = 0;
  let fp = 0;
  let index = 0;

  while (index < pairs.length) {
    const value = pairs[index].value;
    let j = index;
    while (j < pairs.length && pairs[j].value === value) {
      if (pairs[j].label === 1) {
        tp += 1;
      } else {
        fp += 1;
      }
      j += 1;
    }
    points.push({ threshold: value, tpr: tp / positives, fpr: fp / negatives });
    index = j;
  }

  points.push({ threshold: Number.NEGATIVE_INFINITY, tpr: 1, fpr: 1 });

  return points;
}
