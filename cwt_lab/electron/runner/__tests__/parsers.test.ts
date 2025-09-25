import { readFileSync } from 'node:fs';
import path from 'node:path';

import { describe, expect, it } from 'vitest';

import { parseLoopStdout } from '../parsers';

const loadFixture = (name: string) =>
  readFileSync(path.join(__dirname, '..', '__fixtures__', name), 'utf-8');

describe('parseLoopStdout', () => {
  it('extracts key metrics from loop stdout fixtures', () => {
    const fixture = loadFixture('loop_sample.log');

    const metrics = parseLoopStdout(fixture);

    expect(metrics).toEqual(
      expect.objectContaining({
        fsP95: 0.245,
        phi: 0.5123,
        R: 0.7321,
        overlapMin: 0.654,
        kappaChange: 3.21,
        guardExceeded: false,
        rFlipError: 1.23,
        phiFlipError: 4.56,
      }),
    );
  });

  it('tolerates logs that do not contain metrics', () => {
    const metrics = parseLoopStdout('no metrics on this line');
    expect(metrics).toEqual({});
  });
});
