import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import * as NavigationModule from '../../navigation/ExperimentNavigationContext';
import Phase3Loops, { buildGuidedPayload, previewGuidedCli } from '../Phase3Loops';

vi.mock('../ipc', () => ({
  runs: {
    listRecent: vi.fn().mockResolvedValue([]),
  },
}));

vi.mock('../AdiabaticBoundaryViewer', () => ({
  __esModule: true,
  default: () => null,
}));

const originalWindow = (globalThis as { window?: Window }).window;

type NavigationContextValue = ReturnType<typeof NavigationModule.useExperimentNavigation>;

let navigationState: NavigationContextValue;
let navigationSpy: ReturnType<typeof vi.spyOn<typeof NavigationModule, 'useExperimentNavigation'>> | null = null;

describe('Phase3 guided helpers', () => {
  afterEach(() => {
    if (originalWindow) {
      (globalThis as any).window = originalWindow;
    } else {
      delete (globalThis as any).window;
    }
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

describe('Phase3Loops component amplitude controls', () => {
  const readFileMock = vi.fn();

  beforeEach(() => {
    navigationState = {
      artifactsRoot: '/tmp',
      experiments: [],
      experimentsError: null,
      experimentsLoading: false,
      selectedExperimentPath: 'exp-1',
      setSelectedExperimentPath: vi.fn(),
      refreshExperiments: vi.fn(),
      hasArtifactsApi: true,
      substrates: [],
      substratesError: null,
      substratesLoading: false,
      selectedSubstratePath: 'substrate-1',
      setSelectedSubstratePath: vi.fn(),
      refreshSubstrates: vi.fn(),
    } as NavigationContextValue;

    navigationSpy = vi
      .spyOn(NavigationModule, 'useExperimentNavigation')
      .mockImplementation(() => navigationState);

    const baseWindow = originalWindow ?? (globalThis as { window?: Window }).window;
    if (!baseWindow) {
      throw new Error('Phase3Loops component tests require a window environment.');
    }

    (globalThis as any).window = baseWindow;
    Object.assign(baseWindow as unknown as Record<string, unknown>, {
      CWT: {
        artifacts: {
          readFile: readFileMock,
        },
        registry: {
          query: vi.fn(),
        },
      },
    });
    readFileMock.mockReset();
  });

  afterEach(() => {
    navigationSpy?.mockRestore();
    navigationSpy = null;
    cleanup();
    vi.clearAllMocks();
    const currentWindow = (globalThis as { window?: Window }).window;
    if (currentWindow && 'CWT' in currentWindow) {
      delete (currentWindow as Record<string, unknown>).CWT;
    }
  });

  it('extends the amplitude slider max using summary amplitudes', async () => {
    readFileMock.mockResolvedValue({
      ok: true,
      data: {
        contents: JSON.stringify({
          amplitudes: [0.75, 0.52, 0.61],
          graph: 'ring3',
        }),
      },
    });

    render(<Phase3Loops />);

    const rhoSlider = (await screen.findByRole('slider', { name: /ρ amplitude/i })) as HTMLInputElement;

    await waitFor(() => {
      expect(readFileMock).toHaveBeenCalled();
    });

    await waitFor(() => {
      const max = Number((rhoSlider as HTMLInputElement).max);
      expect(max).toBeGreaterThan(0.75);
    });
  });

  it('allows manual amplitude entries beyond the default range', async () => {
    readFileMock.mockResolvedValue({ ok: false });
    navigationState = {
      ...navigationState,
      selectedSubstratePath: null,
    } as NavigationContextValue;

    render(<Phase3Loops />);

    const user = userEvent.setup();
    const tauSlider = (await screen.findByRole('slider', { name: /τ amplitude/i })) as HTMLInputElement;
    const tauInput = screen.getByRole('spinbutton', { name: 'τ amplitude value' });

    await user.clear(tauInput);
    await user.type(tauInput, '0.85');

    await waitFor(() => {
      expect(Number(tauSlider.value)).toBeCloseTo(0.85, 2);
    });

    const sliderMax = Number(tauSlider.max);
    expect(sliderMax).toBeGreaterThan(0.85);
  });
});
