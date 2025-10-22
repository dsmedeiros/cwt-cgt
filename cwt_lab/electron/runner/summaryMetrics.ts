/**
 * Flattens nested summary metrics into dot-separated keys so downstream consumers
 * can access per-graph descriptors like "graphs.my_graph.diameter".
 *
 * Only plain-object values are traversed recursively. Numbers are preserved when
 * finite, booleans are converted to 0/1, and other types are ignored.
 */
export const flattenSummaryMetrics = (
  payload: Record<string, unknown>,
  prefix = '',
): Record<string, number | null> => {
  const metrics: Record<string, number | null> = {};
  const basePrefix = prefix ? `${prefix}.` : '';

  for (const [key, value] of Object.entries(payload)) {
    if (!key) {
      continue;
    }

    const qualifiedKey = `${basePrefix}${key}`;
    if (typeof value === 'number') {
      metrics[qualifiedKey] = Number.isFinite(value) ? value : null;
      continue;
    }

    if (typeof value === 'boolean') {
      metrics[qualifiedKey] = value ? 1 : 0;
      continue;
    }

    if (value && typeof value === 'object' && !Array.isArray(value)) {
      const nested = flattenSummaryMetrics(value as Record<string, unknown>, qualifiedKey);
      Object.assign(metrics, nested);
    }
  }

  return metrics;
};
