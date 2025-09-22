import fs from 'fs';
import path from 'path';

import { parseLoopStdout } from '../parsers';

describe('parseLoopStdout', () => {
  it('extracts metrics from hotspot stdout sample', () => {
    const fixturePath = path.join(__dirname, '..', '__fixtures__', 'stdout_hotspot_example.txt');
    const sample = fs.readFileSync(fixturePath, 'utf8');

    const metrics = parseLoopStdout(sample);

    expect(metrics).toEqual(
      expect.objectContaining({
        fsP95: 0.245,
        phi: 0.5123,
        R: 0.7321,
        kappaChange: 3.21,
        overlapMin: 0.654,
        guardExceeded: false,
        rFlipError: 1.23,
        phiFlipError: 4.56,
      })
    );
  });

  it('parses locale-style decimals by normalizing separators', () => {
    const sample = 'FS p95=1,5 rad  Φ=-0,75  R=+0,25  κ₁ scale change: 12,5%  guard_exceeded=True  flip error: area=3,4%  phi=5,6%';

    const metrics = parseLoopStdout(sample);

    expect(metrics.fsP95).toBeCloseTo(1.5);
    expect(metrics.phi).toBeCloseTo(-0.75);
    expect(metrics.R).toBeCloseTo(0.25);
    expect(metrics.kappaChange).toBeCloseTo(12.5);
    expect(metrics.guardExceeded).toBe(true);
    expect(metrics.rFlipError).toBeCloseTo(3.4);
    expect(metrics.phiFlipError).toBeCloseTo(5.6);
  });
});
