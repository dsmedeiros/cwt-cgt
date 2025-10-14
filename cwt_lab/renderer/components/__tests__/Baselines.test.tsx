import { readFileSync } from 'node:fs';
import path from 'node:path';

import { act, cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import Baselines from '../Baselines';
import type {
  ArtifactsReadFilePayload,
  IpcEnvelope,
  RendererIpc,
} from '../../types/ipc';

type StreamHandler = (event: { runId: string; chunk: string; stream: 'stdout' | 'stderr' }) => void;
type ExitHandler = (event: { runId: string; code: number | null; signal: NodeJS.Signals | null }) => void;
type ErrorHandler = (event: { runId: string; message: string }) => void;
const globalWindow = window as typeof window & { CWT?: RendererIpc };

const okEnvelope = <T,>(data: T): IpcEnvelope<T> => ({ ok: true, data });

const runMock = vi.fn();
let outputHandlers: StreamHandler[] = [];
let exitHandlers: ExitHandler[] = [];
let errorHandlers: ErrorHandler[] = [];

const FIXTURES_ROOT = path.resolve(process.cwd(), '..', 'cwt-sim/baselines/__fixtures__');

const parseFixtureCsv = (filename: string): Array<Record<string, string>> => {
  const raw = readFileSync(path.join(FIXTURES_ROOT, filename), 'utf8');
  const lines = raw.trim().split(/\r?\n/);
  if (lines.length === 0) {
    return [];
  }
  const headers = lines[0].split(',').map((header) => header.trim());
  return lines.slice(1).map((line) => {
    const cells = line.split(',');
    return headers.reduce<Record<string, string>>((record, header, index) => {
      record[header] = cells[index]?.trim() ?? '';
      return record;
    }, {});
  });
};

const formatNumber = (value: number, digits = 3): string => {
  if (!Number.isFinite(value)) {
    return '—';
  }
  if (Math.abs(value) >= 1000 || Math.abs(value) < 0.001) {
    return value.toExponential(2);
  }
  const fixed = value.toFixed(digits);
  return fixed.replace(/\.0+$/, '').replace(/(\.\d*?)0+$/, '$1');
};

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
  const readFileMock = vi.fn();
  const listMock = vi.fn();

  beforeEach(() => {
    runMock.mockReset();
    outputHandlers = [];
    exitHandlers = [];
    errorHandlers = [];
    readFileMock.mockReset();
    listMock.mockReset();

    globalWindow.CWT = {
      artifacts: {
        readFile: readFileMock as unknown as RendererIpc['artifacts']['readFile'],
        list: listMock as unknown as RendererIpc['artifacts']['list'],
      },
    } as RendererIpc;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    delete (globalWindow as { CWT?: RendererIpc }).CWT;
  });

  it('submits the baseline payload and renders artifacts', async () => {
    const metricsRows = parseFixtureCsv('tiny_grid_ising.csv');
    expect(metricsRows.length).toBeGreaterThan(0);
    const peak = metricsRows.reduce((best, current) =>
      Number.parseFloat(current.omega_abs) > Number.parseFloat(best.omega_abs) ? current : best,
    );
    const peakIndices = [Number.parseInt(peak.T_index, 10), Number.parseInt(peak.h_index, 10)];
    const peakCoordinates = { T: Number.parseFloat(peak.T), h: Number.parseFloat(peak.h) };
    const topTiles = {
      axes: [{ name: 'T' }, { name: 'h' }],
      top_tiles: [
        {
          indices: peakIndices,
          coordinates: peakCoordinates,
          omega_abs: Number.parseFloat(peak.omega_abs),
          omega_abs_proxy: Number.parseFloat(peak.omega_abs_proxy ?? '0'),
        },
      ],
    };
    const metricsCsv = readFileSync(
      path.join(FIXTURES_ROOT, 'tiny_grid_ising.csv'),
      'utf8',
    );
    const loopReport = {
      indices: peakIndices,
      loop: { omega_abs: 0.5, area: 1.25 },
      center: {
        T: peakCoordinates.T,
        h: peakCoordinates.h,
        omega: Number.parseFloat(peak.omega_abs),
        M_mean: Number.parseFloat(peak.M_mean),
      },
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

    listMock.mockResolvedValue(
      okEnvelope([
        { type: 'file', name: 'loop-1.json', path: '/tmp/baselines/run-1/loops/loop-1.json' },
      ]) as IpcEnvelope<unknown>,
    );

    readFileMock.mockImplementation(async ({ path }: ArtifactsReadFilePayload) => {
      if (path.endsWith('top_omega_tiles.json')) {
        return okEnvelope({ path, contents: JSON.stringify(topTiles) });
      }
      if (path.endsWith('metrics.csv')) {
        return okEnvelope({ path, contents: metricsCsv });
      }
      return okEnvelope({ path, contents: JSON.stringify(loopReport) });
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
    expect(payload.mapToCwt).toBe(true);
    expect(payload.steps).toBe('200');
    expect(payload.seed).toBe('42');
    expect(Array.isArray(payload.args)).toBe(true);

    // Simulate process exit so the UI unlocks
    act(() => {
      exitHandlers.forEach((handler) => handler({ runId: 'run-1', code: 0, signal: null }));
    });

    await waitFor(() => expect(readFileMock).toHaveBeenCalled());

    expect(await screen.findByAltText('|Ω| heatmap')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /proxy/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 4, name: /top 1 tiles/i })).toBeInTheDocument();
    const topkTable = screen.getByRole('table');
    const expectedCoords = `T=${formatNumber(peakCoordinates.T)}, h=${formatNumber(
      peakCoordinates.h,
    )}`;
    expect(within(topkTable).getByText(expectedCoords)).toBeInTheDocument();
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

    listMock.mockResolvedValue(okEnvelope([]) as IpcEnvelope<unknown>);
    readFileMock.mockResolvedValue(
      okEnvelope({ path: '/tmp/stream/top_omega_tiles.json', contents: JSON.stringify({ axes: [], top_tiles: [] }) }),
    );

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
