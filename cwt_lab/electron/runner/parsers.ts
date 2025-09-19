export type MetricParseResult = {
  metric: string;
  value: number;
  source: string;
};

const METRIC_PATTERNS: Record<string, RegExp> = {
  fs_p95: /fs_p95\s*[:=]\s*(?<value>\d+(?:\.\d+)?)/i,
  phi: /phi\s*[:=]\s*(?<value>\d+(?:\.\d+)?)/i,
  r_value: /r\s*[:=]\s*(?<value>\d+(?:\.\d+)?)/i,
  overlap: /overlap\s*[:=]\s*(?<value>\d+(?:\.\d+)?)/i,
  kappa1: /kappa[_\s]*1\s*[:=]\s*(?<value>\d+(?:\.\d+)?)/i,
};

export const parseMetricsFromLine = (line: string): MetricParseResult[] => {
  const matches: MetricParseResult[] = [];

  for (const [metric, pattern] of Object.entries(METRIC_PATTERNS)) {
    const match = pattern.exec(line);
    if (match?.groups?.value) {
      matches.push({
        metric,
        value: Number.parseFloat(match.groups.value),
        source: line,
      });
    }
  }

  return matches;
};
