import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import EnvDoctor from '../EnvDoctor';
import type { EnvCandidate, EnvConfig, EnvDetectResult, RendererIpc } from '../../types/ipc';

type EnvEnvelope<T> = { ok: true; data: T } | { ok: false; error: string; data?: T };

const assignEnvApi = (overrides: Partial<RendererIpc['env']>) => {
  const env: RendererIpc['env'] = {
    detect: vi.fn(),
    setPythonPath: vi.fn(),
    getConfig: vi.fn(),
    ...overrides,
  } as RendererIpc['env'];
  (window as typeof window & { CWT: RendererIpc }).CWT = {
    env,
  } as unknown as RendererIpc;
  return env;
};

describe('EnvDoctor', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    Reflect.deleteProperty(window as typeof window & { CWT?: RendererIpc }, 'CWT');
  });

  it('renders detection results and highlights the active interpreter', async () => {
    const candidates: EnvCandidate[] = [
      { path: '/tmp/.venv/bin/python', version: 'Python 3.11.4', ok: true, strategy: 'installed' },
      {
        path: '/usr/bin/python3',
        version: 'Python 3.10.8',
        ok: false,
        strategy: null,
        error: 'module run: ImportError: No module named cwt',
      },
    ];

    const detect = vi
      .fn()
      .mockResolvedValue({ ok: true, data: { candidates, selected: candidates[0] } satisfies EnvDetectResult });
    const getConfig = vi.fn().mockResolvedValue({
      ok: true,
      data: {
        repoRoot: '/repo',
        artifactsRoot: '/repo/artifacts',
        pythonPath: candidates[0].path,
        strategy: 'installed',
      } satisfies EnvConfig,
    } satisfies EnvEnvelope<EnvConfig>);

    assignEnvApi({ detect, getConfig });

    render(<EnvDoctor />);

    await waitFor(() => expect(detect).toHaveBeenCalled());

    const activeHeading = await screen.findByRole('heading', { name: /Active interpreter/i });
    const activeSection = activeHeading.closest('.env-doctor__active');
    expect(activeSection).not.toBeNull();
    if (!(activeSection instanceof HTMLElement)) {
      throw new Error('Active interpreter section missing');
    }
    expect(within(activeSection).getByText(candidates[0].path)).toBeInTheDocument();
    expect(within(activeSection).getByText(/Python 3.11.4/)).toBeInTheDocument();
    expect(await screen.findByText(/module run/i)).toBeInTheDocument();
  });

  it('surfaces detection errors from the backend', async () => {
    const detect = vi.fn().mockResolvedValue({
      ok: false as const,
      error: 'No usable Python interpreter found.',
      data: { candidates: [], selected: null },
    } satisfies EnvEnvelope<EnvDetectResult>);
    const getConfig = vi.fn().mockResolvedValue({
      ok: true,
      data: {
        repoRoot: '/repo',
        artifactsRoot: '/repo/artifacts',
        pythonPath: null,
        strategy: null,
      } satisfies EnvConfig,
    } satisfies EnvEnvelope<EnvConfig>);

    assignEnvApi({ detect, getConfig });

    render(<EnvDoctor />);

    await waitFor(() => expect(detect).toHaveBeenCalled());

    expect(await screen.findByRole('alert')).toHaveTextContent('No usable Python interpreter found.');
  });

  it('allows manually configuring the python path and refreshes the scan', async () => {
    const initialCandidates: EnvCandidate[] = [
      { path: '/tmp/.venv/bin/python', version: 'Python 3.11.4', ok: true, strategy: 'installed' },
    ];
    const updatedCandidate: EnvCandidate = {
      path: '/opt/python',
      version: 'Python 3.11.6',
      ok: true,
      strategy: 'installed',
    };

    const detect = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        data: { candidates: initialCandidates, selected: initialCandidates[0] },
      } satisfies EnvEnvelope<EnvDetectResult>)
      .mockResolvedValueOnce({
        ok: true,
        data: { candidates: [updatedCandidate], selected: updatedCandidate },
      } satisfies EnvEnvelope<EnvDetectResult>);

    const getConfig = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        data: {
          repoRoot: '/repo',
          artifactsRoot: '/repo/artifacts',
          pythonPath: initialCandidates[0].path,
          strategy: 'installed',
        } satisfies EnvConfig,
      } satisfies EnvEnvelope<EnvConfig>)
      .mockResolvedValueOnce({
        ok: true,
        data: {
          repoRoot: '/repo',
          artifactsRoot: '/repo/artifacts',
          pythonPath: updatedCandidate.path,
          strategy: 'installed',
        } satisfies EnvConfig,
      } satisfies EnvEnvelope<EnvConfig>);

    const setPythonPath = vi.fn().mockResolvedValue({ ok: true, data: updatedCandidate } satisfies EnvEnvelope<EnvCandidate>);

    assignEnvApi({ detect, getConfig, setPythonPath });

    render(<EnvDoctor />);

    await waitFor(() => expect(detect).toHaveBeenCalledTimes(1));

    const input = await screen.findByLabelText<HTMLInputElement>(/Python executable/i);
    fireEvent.change(input, { target: { value: updatedCandidate.path } });
    const submit = screen.getByRole<HTMLButtonElement>('button', { name: /Set Python Path/i });
    fireEvent.click(submit);

    await waitFor(() => expect(setPythonPath).toHaveBeenCalledWith(updatedCandidate.path));
    await waitFor(() => expect(detect).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(getConfig).toHaveBeenCalledTimes(2));

    expect(await screen.findByText(`Interpreter set to ${updatedCandidate.path}.`)).toBeInTheDocument();
  });
});
