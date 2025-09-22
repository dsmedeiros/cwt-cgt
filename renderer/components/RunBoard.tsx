import React, { useCallback, useEffect, useMemo } from 'react';
import { RunMetrics, RunSummary, useRunsStore } from '../store/runsSlice';

interface IpcRendererLike {
  on?: (channel: string, listener: (...args: unknown[]) => void) => void;
  off?: (channel: string, listener: (...args: unknown[]) => void) => void;
  removeListener?: (channel: string, listener: (...args: unknown[]) => void) => void;
  invoke?: (channel: string, ...args: unknown[]) => Promise<unknown>;
}

interface ElectronRenderer {
  ipcRenderer?: IpcRendererLike;
  registry?: {
    onDidChange?: (listener: () => void) => () => void;
    onChange?: (listener: () => void) => () => void;
  };
  runs?: Record<string, (...args: unknown[]) => unknown>;
  logs?: Record<string, (...args: unknown[]) => unknown>;
  artifacts?: Record<string, (...args: unknown[]) => unknown>;
  params?: Record<string, (...args: unknown[]) => unknown>;
}

declare global {
  interface Window {
    electron?: ElectronRenderer;
  }
}

function getElectron(): ElectronRenderer | undefined {
  if (typeof window === 'undefined') {
    return undefined;
  }
  return window.electron;
}

function subscribeToIpc(channel: string, handler: () => void): () => void {
  const electron = getElectron();
  const ipc = electron?.ipcRenderer;
  if (!ipc?.on) {
    return () => undefined;
  }

  const listener = () => {
    handler();
  };

  ipc.on(channel, listener);

  return () => {
    if (ipc.off) {
      ipc.off(channel, listener);
    } else if (ipc.removeListener) {
      ipc.removeListener(channel, listener);
    }
  };
}

function subscribeToRegistry(handler: () => void): () => void {
  const electron = getElectron();
  const cleanups: Array<() => void> = [];

  const registry = electron?.registry;
  if (registry?.onDidChange) {
    cleanups.push(registry.onDidChange(handler));
  } else if (registry?.onChange) {
    cleanups.push(registry.onChange(handler));
  }

  const registryChannels = ['registry.updated', 'registry.changed', 'runs.registryChanged'];
  for (const channel of registryChannels) {
    const unsubscribe = subscribeToIpc(channel, handler);
    cleanups.push(unsubscribe);
  }

  if (cleanups.length === 0) {
    return () => undefined;
  }

  return () => {
    for (const cleanup of cleanups) {
      try {
        cleanup();
      } catch (error) {
        // Ignore listener cleanup errors.
      }
    }
  };
}

async function callElectronAction(paths: string[][], ipcChannel: string, ...args: unknown[]): Promise<void> {
  const electron = getElectron();
  if (electron) {
    for (const segments of paths) {
      let target: unknown = electron;
      for (const segment of segments) {
        if (!target || typeof target !== 'object') {
          target = undefined;
          break;
        }
        target = (target as Record<string, unknown>)[segment];
      }
      if (typeof target === 'function') {
        await (target as (...innerArgs: unknown[]) => unknown)(...args);
        return;
      }
    }
  }

  const ipc = electron?.ipcRenderer;
  if (ipc?.invoke) {
    await ipc.invoke(ipcChannel, ...args);
  }
}

function formatTimestamp(value: string): string {
  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
  } catch (error) {
    return value;
  }
}

interface MetricBadge {
  label: string;
  value: string;
  tone?: 'default' | 'warning';
}

function buildMetricBadges(metrics: RunMetrics | null): MetricBadge[] {
  if (!metrics) {
    return [];
  }
  const badges: MetricBadge[] = [];

  if (typeof metrics.fsP95 === 'number') {
    badges.push({ label: 'FS', value: metrics.fsP95.toFixed(2) });
  }
  if (typeof metrics.phi === 'number') {
    badges.push({ label: 'Φ', value: metrics.phi.toFixed(2) });
  }
  if (typeof metrics.R === 'number') {
    badges.push({ label: 'R', value: metrics.R.toFixed(2) });
  }
  if (metrics.guardExceeded) {
    badges.push({ label: 'Guard', value: 'Exceeded', tone: 'warning' });
  }

  return badges;
}

function MetricsCell({ metrics }: { metrics: RunMetrics | null }): JSX.Element {
  const badges = useMemo(() => buildMetricBadges(metrics), [metrics]);

  if (!badges.length) {
    return <span className="metric-badge muted">—</span>;
  }

  return (
    <div className="metric-badges">
      {badges.map((badge) => (
        <span
          key={`${badge.label}-${badge.value}`}
          className={`metric-badge ${badge.tone === 'warning' ? 'warning' : ''}`.trim()}
        >
          <strong>{badge.label}</strong>
          <span className="metric-value">{badge.value}</span>
        </span>
      ))}
    </div>
  );
}

function ActionsCell({ run, onRefresh }: { run: RunSummary; onRefresh: () => void }): JSX.Element {
  const handleViewLog = useCallback(async () => {
    await callElectronAction(
      [
        ['runs', 'viewLog'],
        ['logs', 'viewRunLog'],
        ['logs', 'openLog'],
      ],
      'runs.viewLog',
      { runId: run.id, path: run.stdoutPath }
    );
  }, [run.id, run.stdoutPath]);

  const handleOpenArtifacts = useCallback(async () => {
    await callElectronAction(
      [
        ['runs', 'openArtifacts'],
        ['artifacts', 'open'],
      ],
      'runs.openArtifacts',
      { runId: run.id, artifactsPath: run.artifactsPath }
    );
  }, [run.id, run.artifactsPath]);

  const handleCloneParams = useCallback(async () => {
    await callElectronAction(
      [
        ['runs', 'cloneParams'],
        ['params', 'clone'],
      ],
      'runs.cloneParams',
      { runId: run.id, params: run.paramsJson }
    );
  }, [run.id, run.paramsJson]);

  const handleAbort = useCallback(async () => {
    await callElectronAction(
      [['runs', 'abort']],
      'runs.abort',
      { runId: run.id }
    );
    onRefresh();
  }, [onRefresh, run.id]);

  return (
    <div className="run-actions">
      <button type="button" onClick={handleViewLog}>
        View Log
      </button>
      <button type="button" onClick={handleOpenArtifacts} disabled={!run.artifactsPath}>
        Open Artifacts
      </button>
      <button type="button" onClick={handleCloneParams}>
        Clone Params
      </button>
      <button type="button" onClick={handleAbort} disabled={run.status === 'aborted' || run.status === 'done'}>
        Abort
      </button>
    </div>
  );
}

export default function RunBoard(): JSX.Element {
  const runs = useRunsStore((state) => state.runs);
  const selectedRunId = useRunsStore((state) => state.selectedRunId);
  const selectRun = useRunsStore((state) => state.selectRun);
  const refreshRuns = useRunsStore((state) => state.refreshRuns);

  useEffect(() => {
    const refresh = () => {
      void refreshRuns();
    };

    refresh();

    const unsubscribeArtifacts = subscribeToIpc('artifacts.updated', refresh);
    const unsubscribeRegistry = subscribeToRegistry(refresh);

    return () => {
      unsubscribeArtifacts();
      unsubscribeRegistry();
    };
  }, [refreshRuns]);

  return (
    <div className="run-board">
      <table className="run-table">
        <thead>
          <tr>
            <th>Created</th>
            <th>Phase / Experiment</th>
            <th>Status</th>
            <th>Metrics</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr
              key={run.id}
              className={run.id === selectedRunId ? 'selected' : ''}
              onClick={() => selectRun(run.id)}
            >
              <td className="created-at">{formatTimestamp(run.createdAt)}</td>
              <td>
                <div className="phase">{run.phase ?? '—'}</div>
                <div className="experiment">{run.experiment ?? '—'}</div>
              </td>
              <td className={`status status-${run.status ?? 'unknown'}`}>{run.status ?? 'unknown'}</td>
              <td>
                <MetricsCell metrics={run.metrics} />
              </td>
              <td>
                <ActionsCell run={run} onRefresh={() => void refreshRuns()} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
