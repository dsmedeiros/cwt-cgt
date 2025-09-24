import { useCallback, useEffect, useMemo, useState } from 'react';

import { runs as defaultRunsApi } from '../ipc';
import type { RegistryRunRecord, RunDiagnosticsBundle } from '../types/ipc';

type RunsApi = {
  listRecent: (limit?: number) => Promise<RegistryRunRecord[]>;
  collectDiagnostics: (runId: string) => Promise<RunDiagnosticsBundle>;
};

type RunBoardProps = {
  api?: RunsApi;
};

type NoticeState =
  | { kind: 'success'; message: string }
  | { kind: 'error'; message: string }
  | null;

const statusLabels: Record<RegistryRunRecord['status'], string> = {
  pending: 'Pending',
  running: 'Running',
  complete: 'Complete',
  failed: 'Failed',
  aborted: 'Aborted',
};

const formatTimestamp = (value: number) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'Unknown';
  }
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date);
};

const formatMetrics = (metrics: Record<string, number | null> | null) => {
  if (!metrics) {
    return '—';
  }

  const entries = Object.entries(metrics)
    .filter(([, value]) => value !== null)
    .slice(0, 3)
    .map(([key, value]) => `${key}: ${value?.toFixed(3)}`);

  return entries.length > 0 ? entries.join(', ') : '—';
};

const RunBoard = ({ api = defaultRunsApi }: RunBoardProps) => {
  const [runs, setRuns] = useState<RegistryRunRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<NoticeState>(null);
  const [collectingId, setCollectingId] = useState<string | null>(null);

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listRecent(25);
      setRuns(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    void fetchRuns();
  }, [fetchRuns]);

  const sortedRuns = useMemo(
    () =>
      [...runs].sort((a, b) => {
        if (a.updatedAt === b.updatedAt) {
          return b.createdAt - a.createdAt;
        }
        return b.updatedAt - a.updatedAt;
      }),
    [runs],
  );

  const handleCollectDiagnostics = useCallback(
    async (runId: string) => {
      setCollectingId(runId);
      setNotice(null);
      try {
        const bundle = await api.collectDiagnostics(runId);
        setNotice({
          kind: 'success',
          message: `Diagnostics saved to ${bundle.zipPath}`,
        });
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        setNotice({ kind: 'error', message });
      } finally {
        setCollectingId(null);
      }
    },
    [api],
  );

  return (
    <div className="panel run-board">
      <div className="run-board__header">
        <div>
          <h2>Run Board</h2>
          <p className="run-board__subtitle">
            Track recent calibration runs, inspect their metrics, and collect diagnostics bundles for support.
          </p>
        </div>
        <button
          type="button"
          className="run-board__button"
          onClick={() => fetchRuns()}
          disabled={loading}
        >
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>
      {notice ? (
        <div
          className={
            notice.kind === 'success'
              ? 'run-board__notice run-board__notice--success'
              : 'run-board__notice run-board__notice--error'
          }
          role="status"
        >
          {notice.message}
        </div>
      ) : null}
      {error ? (
        <div className="run-board__notice run-board__notice--error" role="alert">
          {error}
        </div>
      ) : null}
      <div className="run-board__table-wrapper" role="region" aria-live="polite">
        <table className="run-board__table">
          <thead>
            <tr>
              <th scope="col">Run ID</th>
              <th scope="col">Status</th>
              <th scope="col">Phase</th>
              <th scope="col">Experiment</th>
              <th scope="col">Last update</th>
              <th scope="col">Metrics</th>
              <th scope="col" className="run-board__actions-col">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedRuns.length === 0 ? (
              <tr>
                <td colSpan={7} className="run-board__empty">
                  No runs recorded yet. Launch an experiment to populate the board.
                </td>
              </tr>
            ) : (
              sortedRuns.map((run) => (
                <tr key={run.id}>
                  <td>
                    <code className="run-board__mono">{run.id}</code>
                  </td>
                  <td>
                    <span className={`run-board__status run-board__status--${run.status}`}>
                      {statusLabels[run.status] ?? run.status}
                    </span>
                  </td>
                  <td>{run.phase ?? '—'}</td>
                  <td>{run.experiment ?? '—'}</td>
                  <td>{formatTimestamp(run.updatedAt)}</td>
                  <td>{formatMetrics(run.metrics)}</td>
                  <td className="run-board__actions">
                    <button
                      type="button"
                      className="run-board__button"
                      onClick={() => handleCollectDiagnostics(run.id)}
                      disabled={collectingId === run.id}
                    >
                      {collectingId === run.id ? 'Collecting…' : 'Collect diagnostics'}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default RunBoard;
