import { act, cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest';

import * as NavigationModule from '../../navigation/ExperimentNavigationContext';
import Phase3Loops, { buildGuidedPayload, previewGuidedCli } from '../Phase3Loops';

vi.mock('../ipc', () => ({
  runs: {
    listRecent: vi.fn().mockResolvedValue([]),
  },
}));

let latestViewerProps: any = null;
let viewerOnResult: ((update: any) => void) | null = null;

vi.mock('../AdiabaticBoundaryViewer', () => ({
  __esModule: true,
  default: (props: any) => {
    latestViewerProps = props;
    viewerOnResult = props.onResult ?? null;
    return null;
  },
}));

const originalWindow = (globalThis as { window?: Window }).window;

type NavigationContextValue = ReturnType<typeof NavigationModule.useExperimentNavigation>;

let navigationState: NavigationContextValue;
let navigationSpy: MockInstance<[], NavigationContextValue> | null = null;
let guidedLoopMock: MockInstance<[any], Promise<any>> | null = null;
let runPreviewMock: MockInstance<[any], Promise<any>> | null = null;

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
      undefined,
      64,
      192,
    );

    expect(payload.axes3).toEqual(['kappa', 'rho', 'tau']);
    expect(payload.center).toEqual([kappaCenter, 0.9, 1.15]);
    expect(payload.settle).toBe(64);
    expect(payload.handleSteps).toBe(192);

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
      72,
      144,
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
    expect(summary.settle).toBe(72);
    expect(summary.handleSteps).toBe(144);
    expect(summary.stepsList).toEqual([128, 256]);
    expect(summary.fsGuard).toBe(0.18);
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
      substrates: [
        {
          name: 'ring3 substrate',
          path: 'substrate-1',
          relativePath: 'ring3-substrate',
          type: 'directory',
        },
      ],
      substratesError: null,
      substratesLoading: false,
      selectedSubstratePath: 'substrate-1',
      setSelectedSubstratePath: vi.fn(),
      refreshSubstrates: vi.fn(),
    } as NavigationContextValue;

    navigationSpy = vi
      .spyOn(NavigationModule, 'useExperimentNavigation')
      .mockImplementation(() => navigationState);

    latestViewerProps = null;
    viewerOnResult = null;

    const baseWindow = originalWindow ?? (globalThis as { window?: Window }).window;
    if (!baseWindow) {
      throw new Error('Phase3Loops component tests require a window environment.');
    }

    (globalThis as any).window = baseWindow;
    guidedLoopMock = vi
      .fn<[any], Promise<any>>()
      .mockResolvedValue({ ok: true, data: { runs: [], satisfied: false } });
    runPreviewMock = vi
      .fn<[any], Promise<any>>()
      .mockResolvedValue({ ok: true, data: { cli: 'preview' } });
    Object.assign(baseWindow as unknown as Record<string, unknown>, {
      CWT: {
        artifacts: {
          readFile: readFileMock,
        },
        registry: {
          query: vi.fn(),
        },
        phase3: {
          guidedLoop: guidedLoopMock,
        },
        run: {
          preview: runPreviewMock,
        },
      },
    });
    readFileMock.mockReset();
  });

  afterEach(() => {
    navigationSpy?.mockRestore();
    navigationSpy = null;
    guidedLoopMock = null;
    runPreviewMock = null;
    cleanup();
    vi.clearAllMocks();
    const currentWindow = (globalThis as { window?: Window }).window;
    if (currentWindow && 'CWT' in currentWindow) {
      delete (currentWindow as { CWT?: unknown }).CWT;
    }
    latestViewerProps = null;
    viewerOnResult = null;
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

  it('infers graph identifiers from CLI-compatible summary descriptors', async () => {
    navigationState.substrates = [
      {
        name: 'mystery substrate',
        path: 'substrate-42',
        relativePath: 'enigmatic',
        type: 'directory',
      },
    ] as any;
    navigationState.selectedSubstratePath = 'substrate-42';

    readFileMock.mockResolvedValue({
      ok: true,
      data: {
        contents: JSON.stringify({
          graph_descriptor: {
            identifier: 'random_regular',
            label: 'Random regular graph',
          },
        }),
      },
    });

    render(<Phase3Loops />);

    await waitFor(() => {
      expect(readFileMock).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(latestViewerProps?.graphId).toBe('random_regular');
    });
  });

  it('gates loop controls until the adiabatic sweep succeeds for the hotspot', async () => {
    readFileMock.mockResolvedValue({ ok: false });
    render(<Phase3Loops />);

    const user = userEvent.setup();
    const simpleTab = await screen.findByRole('button', { name: /Simple loop/i });
    await user.click(simpleTab);

    const runButton = await screen.findByRole('button', { name: 'Run' });
    expect(runButton).toBeDisabled();

    const initialGates = await screen.findAllByText(/Run the adiabatic boundary sweep/i);
    expect(initialGates).toHaveLength(1);

    const boundaryResult = {
      runId: 'adiabatic-1',
      outputDir: '/tmp/adiabatic',
      surface: [],
      histograms: [],
      boundary: [],
      recommendation: null,
      fsGuard: { recommended: null, maxObserved: null },
      referenceKappa: null,
    };

    expect(viewerOnResult).toBeDefined();
    const initialHotspotId = latestViewerProps?.hotspot?.id ?? null;
    const initialGraphId = latestViewerProps?.graphId ?? null;

    act(() => {
      viewerOnResult?.({
        status: 'running',
        requestId: 1,
        hotspotId: initialHotspotId,
        graphId: initialGraphId,
      });
    });
    act(() => {
      viewerOnResult?.({
        status: 'success',
        requestId: 1,
        hotspotId: initialHotspotId,
        graphId: initialGraphId,
        result: boundaryResult,
      });
    });

    await waitFor(() => {
      expect(runButton).not.toBeDisabled();
    });
    expect(screen.queryByText(/Run the adiabatic boundary sweep/i)).not.toBeInTheDocument();

    const secondHotspot = await screen.findByRole('radio', { name: /Calm Basin B/i });
    await user.click(secondHotspot);

    await waitFor(() => {
      expect(latestViewerProps?.hotspot?.id).not.toBe(initialHotspotId);
    });

    const refreshedGates = await screen.findAllByText(/Run the adiabatic boundary sweep/i);
    expect(refreshedGates).toHaveLength(1);
    expect(runButton).toBeDisabled();

    const nextHotspotId = latestViewerProps?.hotspot?.id ?? null;
    const nextGraphId = latestViewerProps?.graphId ?? null;

    act(() => {
      viewerOnResult?.({
        status: 'success',
        requestId: 2,
        hotspotId: nextHotspotId,
        graphId: nextGraphId,
        result: boundaryResult,
      });
    });

    await waitFor(() => {
      expect(runButton).not.toBeDisabled();
    });
  });

  it('applies adiabatic recommendations to guided controls', async () => {
    readFileMock.mockResolvedValue({ ok: false });

    render(<Phase3Loops />);

    await waitFor(() => {
      expect(viewerOnResult).toBeInstanceOf(Function);
      expect(latestViewerProps?.hotspot?.id).toBeTruthy();
    });

    const hotspotId = latestViewerProps!.hotspot!.id;
    const graphId = (latestViewerProps?.graphId as string | null) ?? 'ring3';
    const boundaryResult = {
      runId: 'adiabatic-2',
      outputDir: '/tmp/adiabatic',
      surface: [
        { extent: 0.2, steps: 200, flux: 0.012, area: null, kappa1: null, readout: null, fsMean: null, fsP95: 0.07 },
        { extent: 0.25, steps: 260, flux: 0.01, area: null, kappa1: null, readout: null, fsMean: null, fsP95: 0.09 },
        { extent: 0.3, steps: 320, flux: 0.015, area: null, kappa1: null, readout: null, fsMean: null, fsP95: 0.11 },
      ],
      histograms: [],
      boundary: [
        {
          extent: 0.25,
          boundarySteps: 120,
          referenceKappa: 1.0,
          boundaryKappa: 1.08,
          boundaryFsP95: 0.07,
        },
      ],
      recommendation: { extent: 0.24, steps: 240, fsP95: 0.085 },
      fsGuard: { recommended: 0.1, maxObserved: 0.12 },
      referenceKappa: 1.0,
    };

    act(() => {
      viewerOnResult?.({
        status: 'running',
        requestId: 1,
        hotspotId,
        graphId,
      });
    });

    act(() => {
      viewerOnResult?.({
        status: 'success',
        requestId: 1,
        hotspotId,
        graphId,
        result: boundaryResult,
      });
    });

    const tauInput = (await screen.findByRole('spinbutton', { name: 'τ amplitude value' })) as HTMLInputElement;
    const zetaInput = screen.getByRole('spinbutton', { name: 'ζ amplitude value' }) as HTMLInputElement;
    const kappaInput = screen.getByRole('spinbutton', { name: 'κ amplitude value' }) as HTMLInputElement;
    expect(Number(tauInput.value)).toBeCloseTo(0.25, 2);
    expect(Number(zetaInput.value)).toBeCloseTo(0.25, 2);
    expect(Number(kappaInput.value)).toBeCloseTo(0.08, 2);

    const guardInputs = await screen.findAllByLabelText(/FS guard/i, { selector: 'input' });
    guardInputs.forEach((input) => {
      expect((input as HTMLInputElement).value).toBe('0.1');
    });

    const user = userEvent.setup();
    const guidedSettle = (await screen.findByLabelText(/Guided settle steps/i)) as HTMLInputElement;
    const handleInput = (await screen.findByLabelText(/Handle steps/i)) as HTMLInputElement;
    expect(guidedSettle.value).toBe('52');
    expect(handleInput.value).toBe('120');

    const simpleTab = screen.getByRole('button', { name: /Simple loop/i });
    await act(async () => {
      await user.click(simpleTab);
    });
    const simpleSettle = await screen.findByLabelText(/Settle steps/i);
    expect((simpleSettle as HTMLInputElement).value).toBe('52');

    const guidedTab = screen.getByRole('button', { name: /Guided loop/i });
    await act(async () => {
      await user.click(guidedTab);
    });

    const stepInputs = screen.getAllByPlaceholderText('e.g. 320') as HTMLInputElement[];
    const stepValues = stepInputs.map((input) => input.value);
    expect(stepValues).toEqual(['200', '240', '260']);

    const calibrateButton = screen.getByRole('button', { name: /Calibrate & Run/i });
    expect(calibrateButton).not.toBeDisabled();
  });

  it('flags a calm basin and keeps calibration gated', async () => {
    readFileMock.mockResolvedValue({ ok: false });

    render(<Phase3Loops />);

    await waitFor(() => {
      expect(viewerOnResult).toBeInstanceOf(Function);
    });

    const energeticHotspot = await screen.findByRole('radio', { name: /Energetic Ridge/i });
    const user = userEvent.setup();
    await act(async () => {
      await user.click(energeticHotspot);
    });

    await waitFor(() => {
      expect(latestViewerProps?.hotspot?.name).toMatch(/Energetic Ridge/);
    });

    const calmBoundary = {
      runId: 'adiabatic-calm',
      outputDir: '/tmp/adiabatic',
      surface: [
        { extent: 0.12, steps: 160, flux: 0.0008, area: null, kappa1: null, readout: null, fsMean: null, fsP95: 0.004 },
        { extent: 0.14, steps: 200, flux: 0.0012, area: null, kappa1: null, readout: null, fsMean: null, fsP95: 0.006 },
        { extent: 0.16, steps: 220, flux: 0.0018, area: null, kappa1: null, readout: null, fsMean: null, fsP95: 0.008 },
      ],
      histograms: [],
      boundary: [],
      recommendation: { extent: 0.14, steps: 200, fsP95: 0.006 },
      fsGuard: { recommended: 0.05, maxObserved: 0.07 },
      referenceKappa: 1.0,
    };

    const calmHotspotId = latestViewerProps!.hotspot!.id;
    const calmGraphId = (latestViewerProps?.graphId as string | null) ?? 'ring3';

    act(() => {
      viewerOnResult?.({
        status: 'success',
        requestId: 7,
        hotspotId: calmHotspotId,
        graphId: calmGraphId,
        result: calmBoundary,
      });
    });

    const calmMessages = await screen.findAllByText(/adiabatic sweep identified a calm basin/i);
    expect(calmMessages.length).toBeGreaterThan(0);
    const calibrateButton = screen.getByRole('button', { name: /Calibrate & Run/i });
    expect(calibrateButton).toBeDisabled();
    await waitFor(() => {
      expect(latestViewerProps?.hotspot?.calm).toBe(true);
    });
  });

  it('passes tuned settle and handle steps in the guided payload', async () => {
    readFileMock.mockResolvedValue({ ok: false });

    render(<Phase3Loops />);

    await waitFor(() => {
      expect(viewerOnResult).toBeInstanceOf(Function);
      expect(latestViewerProps?.hotspot?.id).toBeTruthy();
    });

    const hotspotId = latestViewerProps!.hotspot!.id;
    const graphId = (latestViewerProps?.graphId as string | null) ?? 'ring3';
    const boundaryResult = {
      runId: 'adiabatic-run',
      outputDir: '/tmp/adiabatic',
      surface: [
        { extent: 0.22, steps: 220, flux: 0.015, area: null, kappa1: null, readout: null, fsMean: null, fsP95: 0.08 },
        { extent: 0.26, steps: 280, flux: 0.017, area: null, kappa1: null, readout: null, fsMean: null, fsP95: 0.09 },
      ],
      histograms: [],
      boundary: [
        {
          extent: 0.24,
          boundarySteps: 140,
          referenceKappa: 1.0,
          boundaryKappa: 1.09,
          boundaryFsP95: 0.08,
        },
      ],
      recommendation: { extent: 0.23, steps: 240, fsP95: 0.085 },
      fsGuard: { recommended: 0.09, maxObserved: 0.1 },
      referenceKappa: 1.0,
    };

    act(() => {
      viewerOnResult?.({
        status: 'success',
        requestId: 11,
        hotspotId,
        graphId,
        result: boundaryResult,
      });
    });

    const user = userEvent.setup();
    const calibrateButton = await screen.findByRole('button', { name: /Calibrate & Run/i });
    await waitFor(() => {
      const stepValues = screen
        .getAllByPlaceholderText('e.g. 320')
        .map((input) => (input as HTMLInputElement).value);
      expect(stepValues).toEqual(['220', '240', '280']);
    });
    await waitFor(() => {
      expect(calibrateButton).not.toBeDisabled();
    });
    await act(async () => {
      await user.click(calibrateButton);
    });

    await waitFor(() => {
      expect(guidedLoopMock).toHaveBeenCalled();
    });

    const firstCall = guidedLoopMock?.mock.calls[0];
    expect(firstCall).toBeDefined();
    const [callArgs] = firstCall!;
    expect(callArgs.settle).toBe(56);
    expect(callArgs.handleSteps).toBe(140);
    expect(callArgs.stepsList).toEqual([220, 240, 280]);
    expect(callArgs.summary?.settle).toBe(56);
    expect(callArgs.summary?.handleSteps).toBe(140);
    expect(callArgs.summary?.stepsList).toEqual([220, 240, 280]);
    expect(callArgs.summary?.fsGuard).toBe(0.09);
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
