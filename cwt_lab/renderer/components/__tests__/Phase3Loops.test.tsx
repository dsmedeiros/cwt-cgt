import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

type NavigationStub = {
  artifactsRoot: string | null;
  experiments: Array<{ path: string; relativePath: string; name?: string }>;
  experimentsError: string | null;
  experimentsLoading: boolean;
  selectedExperimentPath: string | null;
  setSelectedExperimentPath: (path: string | null) => void;
  refreshExperiments: () => void;
  hasArtifactsApi: boolean;
  substrates: Array<{ path: string; name: string; relativePath: string }>;
  substratesError: string | null;
  substratesLoading: boolean;
  selectedSubstratePath: string | null;
  setSelectedSubstratePath: (path: string | null) => void;
  refreshSubstrates: () => void;
};

let navigationStub: NavigationStub;
const runsListRecentMock = vi.fn(async () => [] as unknown[]);

let Phase3Loops: typeof import('../Phase3Loops').default;
let buildGuidedPayload: typeof import('../Phase3Loops').buildGuidedPayload;
let previewGuidedCli: typeof import('../Phase3Loops').previewGuidedCli;

beforeAll(async () => {
  navigationStub = {
    artifactsRoot: '/artifacts',
    experiments: [{ path: '/experiments/demo', relativePath: 'demo' }],
    experimentsError: null,
    experimentsLoading: false,
    selectedExperimentPath: '/experiments/demo',
    setSelectedExperimentPath: vi.fn(),
    refreshExperiments: vi.fn(),
    hasArtifactsApi: true,
    substrates: [{ path: '/experiments/demo/sub', name: 'sub', relativePath: 'sub' }],
    substratesError: null,
    substratesLoading: false,
    selectedSubstratePath: '/experiments/demo/sub',
    setSelectedSubstratePath: vi.fn(),
    refreshSubstrates: vi.fn(),
  } satisfies NavigationStub;

  const navigationModule = await import('../../navigation/ExperimentNavigationContext');
  Object.defineProperty(navigationModule, 'useExperimentNavigation', {
    configurable: true,
    value: () => navigationStub,
  });
  Object.defineProperty(navigationModule, 'ExperimentNavigationProvider', {
    configurable: true,
    value: ({ children }: { children: any }) => children,
  });

  const module = await import('../Phase3Loops');
  Phase3Loops = module.default;
  buildGuidedPayload = module.buildGuidedPayload;
  previewGuidedCli = module.previewGuidedCli;
});

vi.mock('../AdiabaticBoundaryViewer', () => ({
  __esModule: true,
  default: () => null,
}));

vi.mock('../../ipc', () => ({
  runs: {
    listRecent: (...args: unknown[]) => runsListRecentMock(...args),
  },
}));


beforeEach(() => {
  runsListRecentMock.mockReset();
  runsListRecentMock.mockResolvedValue([]);
  navigationStub = {
    artifactsRoot: '/artifacts',
    experiments: [{ path: '/experiments/demo', relativePath: 'demo' }],
    experimentsError: null,
    experimentsLoading: false,
    selectedExperimentPath: '/experiments/demo',
    setSelectedExperimentPath: vi.fn(),
    refreshExperiments: vi.fn(),
    hasArtifactsApi: true,
    substrates: [{ path: '/experiments/demo/sub', name: 'sub', relativePath: 'sub' }],
    substratesError: null,
    substratesLoading: false,
    selectedSubstratePath: '/experiments/demo/sub',
    setSelectedSubstratePath: vi.fn(),
    refreshSubstrates: vi.fn(),
  } satisfies NavigationStub;
  const win = (globalThis as any).window ?? ((globalThis as any).window = {});
  win.CWT = {
    ...(win.CWT ?? {}),
    registry: {
      query: vi.fn().mockResolvedValue({ ok: true, data: [] }),
    },
  };
});

afterEach(() => {
  if (typeof window !== 'undefined') {
    delete (window as any).CWT;
  }
});

describe('Phase3 guided helpers', () => {
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

    const win = (globalThis as any).window ?? ((globalThis as any).window = {});
    win.CWT = {
      ...(win.CWT ?? {}),
      run: {
        preview: previewMock,
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

describe('Phase3Loops component', () => {
  it('allows amplitudes beyond the initial slider cap via direct entry', async () => {
    const win = (globalThis as any).window ?? ((globalThis as any).window = {});
    win.CWT = {
      ...(win.CWT ?? {}),
      artifacts: {
        list: vi.fn(),
        readFile: vi.fn(),
      },
    };

    render(<Phase3Loops />);

    const rhoLabel = screen.getByText('ρ amplitude', { selector: 'span' }).closest('label');
    expect(rhoLabel).not.toBeNull();
    const rhoSlider = within(rhoLabel!).getByRole('slider') as HTMLInputElement;
    const rhoInput = within(rhoLabel!).getByRole('spinbutton') as HTMLInputElement;

    const initialMax = parseFloat(rhoSlider.max);
    expect(initialMax).toBeGreaterThanOrEqual(0.4);

    const manualValue = Number((initialMax + 0.25).toFixed(2));

    await act(async () => {
      fireEvent.change(rhoInput, { target: { value: manualValue.toString() } });
    });

    await waitFor(() => expect(parseFloat(rhoSlider.value)).toBeCloseTo(manualValue, 2));
    await waitFor(() => expect(parseFloat(rhoSlider.max)).toBeGreaterThanOrEqual(manualValue));
  });

  it('expands amplitude range when summary amplitudes exceed defaults', async () => {
    const hotspotJson = JSON.stringify({
      axes: ['rho', 'tau'],
      top_tiles: [
        {
          coordinates: { rho: 0.12, tau: -0.08 },
          omega_abs: 0.2,
        },
      ],
    });
    const summaryJson = JSON.stringify({
      hotspots: [
        {
          extents: [
            {
              axes: ['rho', 'tau'],
              values: [2.4, 2.2],
            },
          ],
        },
      ],
    });

    const listMock = vi.fn().mockResolvedValue({
      ok: true,
      data: [
        {
          name: 'top_omega_tiles.json',
          path: '/experiments/demo/sub/top_omega_tiles.json',
          type: 'file',
          relativePath: 'top_omega_tiles.json',
        },
        {
          name: 'phase3_loop_summary.json',
          path: '/experiments/demo/sub/phase3_loop_summary.json',
          type: 'file',
          relativePath: 'phase3_loop_summary.json',
        },
      ],
    });
    const readFileMock = vi.fn().mockImplementation(({ path }: { path: string }) => {
      if (path.endsWith('top_omega_tiles.json')) {
        return Promise.resolve({ ok: true, data: { contents: hotspotJson } });
      }
      if (path.endsWith('phase3_loop_summary.json')) {
        return Promise.resolve({ ok: true, data: { contents: summaryJson } });
      }
      return Promise.resolve({ ok: false, error: 'not found' });
    });

    const win = (globalThis as any).window ?? ((globalThis as any).window = {});
    win.CWT = {
      ...(win.CWT ?? {}),
      artifacts: {
        list: listMock,
        readFile: readFileMock,
      },
    };

    render(<Phase3Loops />);

    const initialLabel = screen.getByText('ρ amplitude', { selector: 'span' }).closest('label');
    expect(initialLabel).not.toBeNull();
    const initialSlider = within(initialLabel!).getByRole('slider') as HTMLInputElement;
    const initialMax = parseFloat(initialSlider.max);

    const loadButton = await screen.findByRole('button', { name: /Load hotspots/i });

    await act(async () => {
      fireEvent.click(loadButton);
    });

    await waitFor(() => expect(listMock).toHaveBeenCalled());
    await waitFor(() =>
      expect(readFileMock).toHaveBeenCalledWith({
        path: '/experiments/demo/sub/phase3_loop_summary.json',
      }),
    );

    const rhoLabel = screen.getByText('ρ amplitude', { selector: 'span' }).closest('label');
    expect(rhoLabel).not.toBeNull();
    const rhoSlider = within(rhoLabel!).getByRole('slider') as HTMLInputElement;
    await waitFor(() =>
      expect(parseFloat(rhoSlider.max)).toBeGreaterThan(Math.max(initialMax, 2.4)),
    );
  });
});
