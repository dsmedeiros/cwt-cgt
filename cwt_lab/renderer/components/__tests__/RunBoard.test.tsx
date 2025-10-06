import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import RunBoard, { LOG_CHUNK_BYTES } from '../RunBoard';
import type { RegistryRunRecord } from '../../types/ipc';

const buildRun = (overrides: Partial<RegistryRunRecord> = {}): RegistryRunRecord => ({
  id: 'run-' + Math.random().toString(36).slice(2, 6),
  status: 'complete',
  command: 'python',
  args: ['-m', 'demo'],
  cwd: '/tmp/demo',
  phase: 'phase5',
  experiment: 'demo',
  label: 'demo run',
  createdAt: Date.now() - 1_000,
  updatedAt: Date.now(),
  artifactsDir: '/tmp/demo/artifacts',
  metrics: { fs_p95: 0.123, phi: 0.456, R: 0.789 },
  ...overrides,
});

describe('RunBoard', () => {
  it('renders recent runs and triggers diagnostics collection', async () => {
    const runs = [
      buildRun({ id: 'run-2', status: 'complete', updatedAt: Date.now() - 500 }),
      buildRun({ id: 'run-1', status: 'running', updatedAt: Date.now() }),
    ];
    const api = {
      listRecent: vi.fn().mockResolvedValue(runs),
      collectDiagnostics: vi
        .fn()
        .mockResolvedValue({ zipPath: '/tmp/demo.zip', files: ['/tmp/demo/stdout.log'] }),
      tail: vi.fn(),
      deleteRun: vi.fn(),
    };

    render(<RunBoard api={api} />);

    await waitFor(() => expect(api.listRecent).toHaveBeenCalled());

    expect(screen.getByRole('columnheader', { name: /item/i })).toBeInTheDocument();
    expect(screen.getByText('run-1')).toBeInTheDocument();
    expect(screen.getByText('run-2')).toBeInTheDocument();
    const actionButtons = screen.getAllByRole('button', { name: /Collect diagnostics/i });
    expect(actionButtons).toHaveLength(2);

    fireEvent.click(actionButtons[0]);

    await waitFor(() => expect(api.collectDiagnostics).toHaveBeenCalledWith('run-1'));
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('/tmp/demo.zip'));
  });

  it('surfaces IPC errors to the operator', async () => {
    const api = {
      listRecent: vi.fn().mockRejectedValue(new Error('IPC unavailable')),
      collectDiagnostics: vi.fn(),
      tail: vi.fn(),
      deleteRun: vi.fn(),
    };

    render(<RunBoard api={api} />);

    await waitFor(() => expect(api.listRecent).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('IPC unavailable'));
  });

  it('tails logs with pagination controls', async () => {
    const runs = [buildRun({ id: 'run-1', status: 'running' })];
  const tail = vi
    .fn()
    .mockResolvedValueOnce({
      output: 'tail chunk',
      startFromByte: 7,
      nextFromByte: 12,
      totalBytes: 12,
      hasMoreBefore: true,
      status: 'running',
      failureDetails: null,
    })
    .mockResolvedValueOnce({
      output: 'older ',
      startFromByte: 0,
      nextFromByte: 7,
      totalBytes: 12,
      hasMoreBefore: false,
      status: 'running',
      failureDetails: null,
    });
    const api = {
      listRecent: vi.fn().mockResolvedValue(runs),
      collectDiagnostics: vi.fn(),
      tail,
      deleteRun: vi.fn(),
    };

    render(<RunBoard api={api} />);

    await waitFor(() => expect(api.listRecent).toHaveBeenCalled());
    const viewButtons = screen.getAllByRole('button', { name: /View log/i });
    fireEvent.click(viewButtons[0]);

    await waitFor(() =>
      expect(tail).toHaveBeenCalledWith({
        runId: 'run-1',
        fromByte: -LOG_CHUNK_BYTES,
        maxBytes: LOG_CHUNK_BYTES,
      }),
    );
    await waitFor(() => expect(screen.getByText(/tail chunk/)).toBeInTheDocument());

    const loadMore = screen.getByRole('button', { name: /Load more/i });
    fireEvent.click(loadMore);

    await waitFor(() =>
      expect(tail).toHaveBeenLastCalledWith({
        runId: 'run-1',
        fromByte: 0,
        maxBytes: expect.any(Number),
      }),
    );
    await waitFor(() =>
      expect(screen.getByText(/older tail chunk/)).toBeInTheDocument(),
    );
  });

  it('surfaces failure details when available', async () => {
    const runs = [buildRun({ id: 'run-1', status: 'failed' })];
    const api = {
      listRecent: vi.fn().mockResolvedValue(runs),
      collectDiagnostics: vi.fn(),
      tail: vi.fn().mockResolvedValue({
        output: '',
        startFromByte: 0,
        nextFromByte: 0,
        totalBytes: 0,
        hasMoreBefore: false,
        status: 'failed',
        failureDetails: 'Process exited with code 2.',
      }),
      deleteRun: vi.fn(),
    };

    render(<RunBoard api={api} />);

    await waitFor(() => expect(api.listRecent).toHaveBeenCalled());

    const viewButtons = screen.getAllByRole('button', { name: /View log/i });
    fireEvent.click(viewButtons[0]);

    await waitFor(() =>
      expect(api.tail).toHaveBeenCalledWith({
        runId: 'run-1',
        fromByte: -LOG_CHUNK_BYTES,
        maxBytes: LOG_CHUNK_BYTES,
      }),
    );

    await waitFor(() =>
      expect(screen.getByText(/Failure details: Process exited with code 2\./i)).toBeInTheDocument(),
    );
  });

  it('deletes runs after confirmation', async () => {
    const run1 = buildRun({ id: 'run-1', updatedAt: Date.now() });
    const run2 = buildRun({ id: 'run-2', updatedAt: Date.now() - 10 });
    const listRecent = vi
      .fn<[], Promise<RegistryRunRecord[]>>()
      .mockResolvedValueOnce([run1, run2])
      .mockResolvedValueOnce([run2]);
    const api = {
      listRecent,
      collectDiagnostics: vi.fn(),
      tail: vi.fn(),
      deleteRun: vi.fn().mockResolvedValue({ runId: 'run-1' }),
    };
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

    render(<RunBoard api={api} />);

    await waitFor(() => expect(listRecent).toHaveBeenCalledTimes(1));

    const deleteButton = screen.getByRole('button', { name: /delete run run-1/i });
    fireEvent.click(deleteButton);

    await waitFor(() => expect(api.deleteRun).toHaveBeenCalledWith('run-1'));
    await waitFor(() => expect(listRecent).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.queryByText('run-1')).not.toBeInTheDocument());

    confirmSpy.mockRestore();
  });
});
