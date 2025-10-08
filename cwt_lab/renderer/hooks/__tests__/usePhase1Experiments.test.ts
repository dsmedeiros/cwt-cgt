import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, afterEach } from 'vitest';

import { usePhase1Experiments } from '../usePhase1Experiments';
import type { ArtifactsWatchEvent } from '../../types/ipc';

const buildExperimentNode = (guid: string) => ({
  name: guid,
  path: `/artifacts/${guid}`,
  relativePath: guid,
  type: 'directory' as const,
  children: [
    {
      name: 'substrate',
      path: `/artifacts/${guid}/substrate`,
      relativePath: `${guid}/substrate`,
      type: 'directory' as const,
      children: [
        {
          name: 'top_omega_tiles.json',
          path: `/artifacts/${guid}/substrate/top_omega_tiles.json`,
          relativePath: `${guid}/substrate/top_omega_tiles.json`,
          type: 'file' as const,
        },
      ],
    },
  ],
});

describe('usePhase1Experiments', () => {
  const guid = '123e4567-e89b-12d3-a456-426614174000';

  afterEach(() => {
    delete (window as typeof window & { CWT?: unknown }).CWT;
  });

  it('refreshes when nested Phase 1 outputs change', async () => {
    const changeListeners: Array<(event: ArtifactsWatchEvent) => void> = [];

    const list = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, data: [] })
      .mockResolvedValueOnce({ ok: true, data: [buildExperimentNode(guid)] });

    const watch = vi.fn().mockResolvedValue({ ok: true, data: { id: 7 } });
    const unwatch = vi.fn().mockResolvedValue({ ok: true });
    const getConfig = vi
      .fn()
      .mockResolvedValue({ ok: true, data: { artifactsRoot: '/artifacts' } });

    const onDidChange = vi.fn((listener: (event: ArtifactsWatchEvent) => void) => {
      changeListeners.push(listener);
      return () => {
        const index = changeListeners.indexOf(listener);
        if (index >= 0) {
          changeListeners.splice(index, 1);
        }
      };
    });

    (window as typeof window & { CWT?: unknown }).CWT = {
      env: { getConfig },
      artifacts: {
        list,
        watch,
        unwatch,
        onDidChange,
      },
    };

    const { result } = renderHook(() => usePhase1Experiments());

    await waitFor(() => expect(getConfig).toHaveBeenCalled());
    await waitFor(() => expect(list).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(watch).toHaveBeenCalledWith({ under: '/artifacts', depth: 2 }));

    expect(result.current.experiments).toEqual([]);

    const event: ArtifactsWatchEvent = {
      id: 7,
      kind: 'add',
      path: `/artifacts/${guid}/substrate/top_omega_tiles.json`,
      relativePath: `${guid}/substrate/top_omega_tiles.json`,
      updatedAt: Date.now(),
      type: 'file',
    };

    act(() => {
      changeListeners.forEach((listener) => listener(event));
    });

    await waitFor(() => expect(list).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(result.current.experiments).toHaveLength(1));
    expect(result.current.experiments[0]?.relativePath).toBe(guid);

    expect(unwatch).not.toHaveBeenCalled();
  });
});
