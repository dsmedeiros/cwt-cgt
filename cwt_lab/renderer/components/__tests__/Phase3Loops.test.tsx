import { afterEach, describe, expect, it, vi } from 'vitest';

import { buildGuidedPayload, previewGuidedCli } from '../Phase3Loops';

vi.mock('../AdiabaticBoundaryViewer', () => ({
  __esModule: true,
  default: () => null,
}));

describe('Phase3 guided helpers', () => {
  afterEach(() => {
    delete (globalThis as any).window;
  });

  it('builds the guided payload and previews CLI with plane amplitudes', async () => {
    const hotspot = {
      id: 'hotspot-123',
      name: 'Test Hotspot',
      axes: ['rho', 'tau'] as const,
      coordinates: {
        rho: 0.9,
        tau: 1.15,
      },
    };

    const rhoAmplitude = 0.32;
    const tauAmplitude = 0.48;
    const kappaAmplitude = 0.27;
    const kappaCenter = 1.0;
    const amplitudeMap: Record<string, number> = {
      rho: rhoAmplitude,
      tau: tauAmplitude,
      kappa: kappaAmplitude,
    };

    const payload = buildGuidedPayload(
      hotspot as any,
      'ring3',
      (axis) => amplitudeMap[axis] ?? 0,
      kappaAmplitude,
      kappaCenter,
      [256],
      0.2,
      0.05,
      7,
    );

    expect(payload.axes3).toEqual(['kappa', 'rho', 'tau']);
    expect(payload.center).toEqual([kappaCenter, 0.9, 1.15]);

    const previewMock = vi.fn().mockImplementation(async (request: any) => {
      const planeAmplitudes = request.args.amplitudes.slice(1).join(', ');
      return { ok: true, data: { cli: `plane amplitudes: ${planeAmplitudes}` } };
    });

    (globalThis as any).window = {
      CWT: {
        run: {
          preview: previewMock,
        },
      },
    };

    const cliPreview = await previewGuidedCli(payload);

    expect(previewMock).toHaveBeenCalledTimes(1);
    const previewArgs = previewMock.mock.calls[0][0].args;
    expect(previewArgs.amplitudes).toEqual([kappaAmplitude, rhoAmplitude, tauAmplitude]);
    expect(cliPreview).toContain(`${rhoAmplitude}`);
    expect(cliPreview).toContain(`${tauAmplitude}`);
  });

  it('includes plane axes and extents in the summary payload', () => {
    const hotspot = {
      id: 'hotspot-sum',
      name: 'Summary Hotspot',
      axes: ['rho', 'tau'] as const,
      coordinates: {
        rho: 0.9,
        tau: 1.15,
      },
    };

    const rhoAmplitude = 0.33;
    const tauAmplitude = 0.41;
    const kappaAmplitude = 0.25;
    const kappaCenter = 1.0;
    const amplitudeMap: Record<string, number> = {
      rho: rhoAmplitude,
      tau: tauAmplitude,
      kappa: kappaAmplitude,
    };

    const payload = buildGuidedPayload(
      hotspot as any,
      'random_regular',
      (axis) => amplitudeMap[axis] ?? 0,
      kappaAmplitude,
      kappaCenter,
      [128, 256],
      0.18,
      0.04,
      17,
      '/tmp/summary.json',
    );

    expect(payload.summary).toBeDefined();
    const summary = payload.summary!;
    expect(summary.axes).toEqual(['rho', 'tau']);
    expect(summary.extents).toEqual([rhoAmplitude, tauAmplitude]);
    expect(summary.center.kappa).toBe(kappaCenter);
    expect(summary.center.rho).toBe(0.9);
    expect(summary.center.tau).toBe(1.15);
    expect(summary.centerVector).toEqual([kappaCenter, 0.9, 1.15]);
    expect(summary.amplitudes).toEqual([kappaAmplitude, rhoAmplitude, tauAmplitude]);
  });
});
