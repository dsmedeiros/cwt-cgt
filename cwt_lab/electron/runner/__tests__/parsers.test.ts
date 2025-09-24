import { readFileSync } from 'node:fs';
import path from 'node:path';

import { describe, expect, it } from 'vitest';

import { parseMetricsFromLine } from '../parsers';

const loadFixture = (name: string) =>
  readFileSync(path.join(__dirname, '..', '__fixtures__', name), 'utf-8');

describe('parseMetricsFromLine', () => {
  it('extracts key metrics from loop stdout fixtures', () => {
    const fixture = loadFixture('loop_sample.log');
    const [firstLine] = fixture.split('\n');

    const metrics = parseMetricsFromLine(firstLine);

    expect(metrics).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ metric: 'fs_p95', value: 0.245 }),
        expect.objectContaining({ metric: 'phi', value: 0.512 }),
        expect.objectContaining({ metric: 'r_value', value: 0.732 }),
        expect.objectContaining({ metric: 'overlap', value: 0.654 }),
        expect.objectContaining({ metric: 'kappa1', value: 3.21 }),
      ]),
    );
  });

  it('returns an empty array when a line does not contain metrics', () => {
    const metrics = parseMetricsFromLine('no metrics on this line');
    expect(metrics).toEqual([]);
  });
});
