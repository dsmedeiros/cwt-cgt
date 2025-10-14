import { act, cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import Baselines from '../Baselines';

type StreamHandler = (event: { runId: string; chunk: string; stream: 'stdout' | 'stderr' }) => void;
type ExitHandler = (event: { runId: string; code: number | null; signal: NodeJS.Signals | null }) => void;
type ErrorHandler = (event: { runId: string; message: string }) => void;
type ArtifactNode = { type: string; name: string; path: string; children?: ArtifactNode[] };

declare global {
  interface Window {
    CWT?: {
      artifacts?: {
        readFile?: (request: { path: string }) => Promise<{ contents: string }>;
        list?: (request: { under: string }) => Promise<Array<{ type: string; name: string; path: string; children?: unknown[] }>>;
      };
    };
  }
}

const runMock = vi.fn();
let outputHandlers: StreamHandler[] = [];
let exitHandlers: ExitHandler[] = [];
let errorHandlers: ErrorHandler[] = [];

vi.mock('../../ipc', () => ({
  baselines: {
    run: (...args: unknown[]) => runMock(...args),
    onOutput: (handler: StreamHandler) => {
      outputHandlers.push(handler);
      return () => {
        outputHandlers = outputHandlers.filter((entry) => entry !== handler);
      };
    },
    onExit: (handler: ExitHandler) => {
      exitHandlers.push(handler);
      return () => {
        exitHandlers = exitHandlers.filter((entry) => entry !== handler);
      };
    },
    onError: (handler: ErrorHandler) => {
      errorHandlers.push(handler);
      return () => {
        errorHandlers = errorHandlers.filter((entry) => entry !== handler);
      };
    },
  },
}));

const AXIS_MAP_PATH = 'cwt-sim/baselines/axis_map.yml';

describe('Baselines component', () => {
  const readFileMock = vi.fn<Promise<{ contents: string }>, [{ path: string }]>();
  const listMock = vi.fn<Promise<ArtifactNode[]>, [{ under: string }]>();

  beforeEach(() => {
    runMock.mockReset();
    outputHandlers = [];
    exitHandlers = [];
    errorHandlers = [];
    readFileMock.mockReset();
    listMock.mockReset();

    window.CWT = {
      artifacts: {
        readFile: readFileMock,
        list: listMock,
      },
    };
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    delete window.CWT;
  });

  it('submits the baseline payload and renders artifacts', async () => {
    const topTiles = {
      axes: [{ name: 'T' }, { name: 'h' }],
      top_tiles: [
        {
          indices: [0, 1],
          coordinates: { T: 2, h: 0.1 },
          omega_abs: 0.42,
        },
      ],
    };
    const metricsCsv = 'T_index,h_index,omega_abs,M_mean\n0,1,0.42,0.11\n';
    const loopReport = {
      indices: [0, 1],
      loop: { omega_abs: 0.36, area: 1.25 },
      center: { T: 2, h: 0.1, omega: 0.5, M_mean: 0.2 },
      phi_abs: 0.35,
    };

    runMock.mockResolvedValueOnce({
      runId: 'run-1',
      model: 'ising',
      outputDir: '/tmp/baselines/run-1',
      artifactsDir: '/tmp/baselines/run-1',
      command: 'python',
      args: ['--graph-kind', 'lattice_2d'],
      cli: 'baseline --model ising',
      cwd: '/workspace',
      status: 'complete',
      startedAt: 1,
      completedAt: 2,
      loopMetrics: null,
    });

    listMock.mockResolvedValue([
      { type: 'file', name: 'loop-1.json', path: '/tmp/baselines/run-1/loops/loop-1.json' },
    ]);

    readFileMock.mockImplementation(async ({ path }) => {
      if (path.endsWith('top_omega_tiles.json')) {
        return { contents: JSON.stringify(topTiles) };
      }
      if (path.endsWith('metrics.csv')) {
        return { contents: metricsCsv };
      }
      return { contents: JSON.stringify(loopReport) };
    });

    const user = userEvent.setup();
    const { container } = render(<Baselines />);

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /run baseline/i }));
    });

    expect(runMock).toHaveBeenCalledTimes(1);
    const payload = runMock.mock.calls[0][0] as Record<string, unknown>;
    expect(payload.model).toBe('ising');
    expect(payload.axisMap).toBe(AXIS_MAP_PATH);
    expect(payload.steps).toBe('200');
    expect(payload.seed).toBe('42');
    expect(Array.isArray(payload.args)).toBe(true);

    // Simulate process exit so the UI unlocks
    act(() => {
      exitHandlers.forEach((handler) => handler({ runId: 'run-1', code: 0, signal: null }));
    });

    await waitFor(() => expect(readFileMock).toHaveBeenCalled());

    expect(await screen.findByAltText('Baseline heatmap')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 4, name: /top 1 tiles/i })).toBeInTheDocument();
    const topkTable = screen.getByRole('table');
    expect(within(topkTable).getByText(/T=2, h=0.1/)).toBeInTheDocument();
    expect(screen.getByText(/Aligned with theory/)).toBeInTheDocument();

    expect(container).toMatchSnapshot();
  });

  it('streams logs and reports completion status', async () => {
    runMock.mockResolvedValueOnce({
      runId: 'run-stream',
      model: 'ising',
      outputDir: '/tmp/stream',
      artifactsDir: '/tmp/stream',
      command: 'python',
      args: [],
      cli: 'baseline',
      cwd: '/workspace',
      status: 'complete',
      startedAt: 1,
      completedAt: 2,
      loopMetrics: null,
    });

    listMock.mockResolvedValue([]);
    readFileMock.mockResolvedValue({ contents: JSON.stringify({ axes: [], top_tiles: [] }) });

    const user = userEvent.setup();
    render(<Baselines />);

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /run baseline/i }));
    });

    expect(runMock).toHaveBeenCalledTimes(1);

    act(() => {
      outputHandlers.forEach((handler) =>
        handler({ runId: 'run-stream', stream: 'stdout', chunk: 'progress: 10%\n' }),
      );
    });

    await waitFor(() => expect(screen.getByText(/progress: 10%/)).toBeInTheDocument());

    act(() => {
      exitHandlers.forEach((handler) => handler({ runId: 'run-stream', code: 0, signal: null }));
    });

    await waitFor(() =>
      expect(screen.getByText(/Baseline run completed successfully/)).toBeInTheDocument(),
    );
  });

  it('persists per-model form state between selections', async () => {
    const user = userEvent.setup();
    render(<Baselines />);

    let graphKindInput = screen.getByLabelText('Graph kind') as HTMLInputElement;
    expect(graphKindInput.value).toBe('lattice_2d');

    await act(async () => {
      await user.clear(graphKindInput);
      await user.type(graphKindInput, 'custom_ising');
    });
    expect(graphKindInput.value).toBe('custom_ising');

    const modelSelect = screen.getByLabelText('Model') as HTMLSelectElement;
    await act(async () => {
      await user.selectOptions(modelSelect, 'kuramoto');
    });

    await waitFor(() => {
      graphKindInput = screen.getByLabelText('Graph kind') as HTMLInputElement;
      expect(graphKindInput.value).toBe('ring3');
    });

    await act(async () => {
      await user.clear(graphKindInput);
      await user.type(graphKindInput, 'custom_kuramoto');
    });

    await act(async () => {
      await user.selectOptions(modelSelect, 'ising');
    });
    await waitFor(() => {
      const restoredGraphKind = screen.getByLabelText('Graph kind') as HTMLInputElement;
      expect(restoredGraphKind.value).toBe('custom_ising');
    });
  });
});
