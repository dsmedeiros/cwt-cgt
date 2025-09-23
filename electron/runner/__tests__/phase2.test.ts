import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

import { correlate } from '../phase2';

describe('correlate', () => {
  const csvContent = [
    'omega_abs,spectral_gap,kuramoto_r,grad_r,trace_g',
    '0.2,1.0,0.2,,10.0',
    '1.2,2.0,0.4,0.7,12.0',
    '1.5,2.5,0.5,0.9,13.0',
    '0.8,1.5,0.3,0.4,11.0',
  ].join('\n');
  const tempDirs: string[] = [];

  function createTempMetricsDir(withMetrics = true): string {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'phase2-test-'));
    if (withMetrics) {
      fs.writeFileSync(path.join(tempDir, 'metrics.csv'), csvContent, 'utf8');
    }
    tempDirs.push(tempDir);
    return tempDir;
  }

  afterAll(() => {
    tempDirs.forEach((dir) => {
      try {
        if (fs.existsSync(dir)) {
          fs.rmSync(dir, { recursive: true, force: true });
        }
      } catch (error) {
        // Ignore cleanup errors in tests.
      }
    });
  });

  it('returns empty statistics when no metrics are available', () => {
    const emptyDir = createTempMetricsDir(false);

    const result = correlate({
      metricsDirs: [emptyDir],
      threshold: { mode: 'absolute', value: 1 },
    });

    expect(result.features).toHaveLength(4);
    result.features.forEach((feature) => {
      expect(feature.correlation).toBeNull();
      expect(feature.sampleSize).toBe(0);
      expect(feature.hotCount).toBe(0);
      expect(feature.coldCount).toBe(0);
      expect(feature.meanHot).toBeNull();
      expect(feature.meanCold).toBeNull();
    });
    expect(result.auc).toBeUndefined();
  });

  it('computes point-biserial correlations with an absolute threshold', () => {
    const metricsDir = createTempMetricsDir();

    const result = correlate({
      metricsDirs: [metricsDir],
      threshold: { mode: 'absolute', value: 1.0 },
    });

    const spectral = result.features.find((feature) => feature.name === 'spectral_gap');
    const grad = result.features.find((feature) => feature.name === 'grad_r');

    expect(spectral).toBeDefined();
    expect(spectral?.correlation).not.toBeNull();
    expect(spectral?.correlation ?? 0).toBeCloseTo(0.7745966, 6);
    expect(spectral?.sampleSize).toBe(4);
    expect(spectral?.hotCount).toBe(2);
    expect(spectral?.coldCount).toBe(2);

    expect(grad).toBeDefined();
    expect(grad?.sampleSize).toBe(3);
    expect(grad?.hotCount).toBe(2);
    expect(grad?.coldCount).toBe(1);

    expect(result.auc).toBeDefined();
    expect(result.auc ?? 0).toBeCloseTo(1.0, 6);
  });

  it('supports percentile thresholds and recomputes statistics accordingly', () => {
    const metricsDir = createTempMetricsDir();

    const result = correlate({
      metricsDirs: [metricsDir],
      threshold: { mode: 'percentile', value: 75 },
    });

    const spectral = result.features.find((feature) => feature.name === 'spectral_gap');

    expect(spectral).toBeDefined();
    expect(spectral?.hotCount).toBe(1);
    expect(spectral?.coldCount).toBe(3);
    expect(spectral?.correlation ?? 0).toBeCloseTo(0.6708203, 6);
    expect(result.auc).toBeDefined();
    expect(result.auc ?? 0).toBeCloseTo(1.0, 6);
  });
});
