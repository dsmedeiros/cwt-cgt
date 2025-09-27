import { useCallback, useEffect, useMemo, useState } from 'react';

import { runs as defaultRunsApi } from '../ipc';
import type { RegistryRunRecord, RunDiagnosticsBundle, RunTailChunk } from '../types/ipc';
import { useCommandRegistration } from '../commandCenter';

export type RunsApi = {
  listRecent: (limit?: number) => Promise<RegistryRunRecord[]>;
  collectDiagnostics: (runId: string) => Promise<RunDiagnosticsBundle>;
  tail: (payload: { runId: string; fromByte?: number; maxBytes?: number }) => Promise<RunTailChunk>;
  deleteRun: (runId: string) => Promise<{ runId: string } | void>;
};

type RunBoardProps = {
  api?: RunsApi;
};

type NoticeState =
  | { kind: 'success'; message: string }
  | { kind: 'error'; message: string }
  | null;

export const LOG_CHUNK_BYTES = 64 * 1024;

type LogChunkEntry = { start: number; text: string };

type LogState = {
  runId: string | null;
  chunks: LogChunkEntry[];
  status: string | null;
  loading: boolean;
  error: string | null;
  failureDetails: string | null;
  hasMoreBefore: boolean;
  startByte: number | null;
  nextByte: number | null;
  totalBytes: number | null;
};

const makeEmptyLogState = (): LogState => ({
  runId: null,
  chunks: [],
  status: null,
  loading: false,
  error: null,
  failureDetails: null,
  hasMoreBefore: false,
  startByte: null,
  nextByte: null,
  totalBytes: null,
});

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
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [logState, setLogState] = useState<LogState>(() => makeEmptyLogState());
  const [logAbortable, setLogAbortable] = useState(false);

  const resetLogState = useCallback(() => {
    setLogState(makeEmptyLogState());
    setLogAbortable(false);
  }, []);

  const applyLogChunk = useCallback(
    (runId: string, chunk: RunTailChunk) => {
      setLogState((prev) => {
        if (prev.runId !== runId) {
          return prev;
        }

        const earliestStart =
          prev.startByte == null ? chunk.startFromByte : Math.min(prev.startByte, chunk.startFromByte);
        const hasMoreBefore =
          earliestStart > 0
            ? chunk.startFromByte <= (prev.startByte ?? chunk.startFromByte)
              ? chunk.hasMoreBefore
              : prev.hasMoreBefore
            : false;
        const nextByte =
          prev.nextByte == null ? chunk.nextFromByte : Math.max(prev.nextByte, chunk.nextFromByte);

        const chunks = chunk.output.length
          ? [...prev.chunks.filter((entry) => entry.start !== chunk.startFromByte),
            { start: chunk.startFromByte, text: chunk.output }].sort((a, b) => a.start - b.start)
          : prev.chunks;

        const nextState = {
          ...prev,
          chunks,
          status: chunk.status,
          loading: false,
          error: null,
          failureDetails: chunk.failureDetails ?? null,
          hasMoreBefore,
          startByte: earliestStart,
          nextByte,
          totalBytes: chunk.totalBytes,
        };
        setLogAbortable(false);
        return nextState;
      });
    },
    [],
  );

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

  const fetchLogChunk = useCallback(
    async (runId: string, mode: 'latest' | 'older' | 'refresh') => {
      setLogState((prev) => {
        if (prev.runId === runId) {
          return { ...prev, loading: true, error: null };
        }
        return { ...makeEmptyLogState(), runId, loading: true };
      });
      setLogAbortable(true);

      try {
        let fromByte: number | undefined;
        let maxBytes = LOG_CHUNK_BYTES;

        if (mode === 'latest') {
          fromByte = -LOG_CHUNK_BYTES;
        } else if (mode === 'older') {
          const startByte = logState.startByte ?? 0;
          const canLoadMore = logState.hasMoreBefore && startByte > 0;
          if (!canLoadMore) {
            setLogState((prev) =>
              prev.runId === runId ? { ...prev, loading: false } : prev,
            );
            setLogAbortable(false);
            return;
          }
          const targetStart = Math.max(0, startByte - LOG_CHUNK_BYTES);
          maxBytes = Math.max(1, startByte - targetStart || LOG_CHUNK_BYTES);
          fromByte = targetStart;
        } else {
          const nextByte = logState.nextByte ?? 0;
          fromByte = nextByte > 0 ? nextByte : -LOG_CHUNK_BYTES;
        }

        const chunk = await api.tail({ runId, fromByte, maxBytes });
        applyLogChunk(runId, chunk);
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        setLogState((prev) =>
          prev.runId === runId ? { ...prev, loading: false, error: message } : prev,
        );
        setLogAbortable(false);
      }
    },
    [api, applyLogChunk, logState.hasMoreBefore, logState.nextByte, logState.startByte],
  );

  const handleViewLog = useCallback(
    (runId: string) => {
      if (logState.runId === runId) {
        resetLogState();
        return;
      }

      setLogState({ ...makeEmptyLogState(), runId, loading: true });
      void fetchLogChunk(runId, 'latest');
    },
    [fetchLogChunk, logState.runId, resetLogState],
  );

  const handleLoadMore = useCallback(() => {
    if (!logState.runId) {
      return;
    }
    void fetchLogChunk(logState.runId, 'older');
  }, [fetchLogChunk, logState.runId]);

  const handleRefresh = useCallback(() => {
    if (!logState.runId) {
      return;
    }
    void fetchLogChunk(logState.runId, 'refresh');
  }, [fetchLogChunk, logState.runId]);

  useEffect(() => {
    void fetchRuns();
  }, [fetchRuns]);

  const runCommand = useMemo(
    () => ({ handler: () => void fetchRuns(), description: 'Refresh run board' }),
    [fetchRuns],
  );

  const abortCommand = useMemo(
    () => (logAbortable ? { handler: resetLogState, description: 'Stop log tail request' } : null),
    [logAbortable, resetLogState],
  );

  useCommandRegistration({ run: runCommand, abort: abortCommand });

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

  const handleDeleteRun = useCallback(
    async (runId: string) => {
      if (!window.confirm(`Delete run ${runId}? This will remove all artifacts.`)) {
        return;
      }

      setDeletingId(runId);
      setNotice(null);
      try {
        await api.deleteRun(runId);
        if (logState.runId === runId) {
          resetLogState();
        }
        await fetchRuns();
        setNotice({ kind: 'success', message: `Run ${runId} deleted.` });
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        setNotice({ kind: 'error', message });
      } finally {
        setDeletingId(null);
      }
    },
    [api, fetchRuns, logState.runId, resetLogState],
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
                      onClick={() => handleViewLog(run.id)}
                      disabled={logState.loading && logState.runId === run.id}
                    >
                      {logState.runId === run.id
                        ? logState.loading
                          ? 'Loading log…'
                          : 'Hide log'
                        : 'View log'}
                    </button>
                    <button
                      type="button"
                      className="run-board__button"
                      onClick={() => handleCollectDiagnostics(run.id)}
                      disabled={collectingId === run.id}
                    >
                      {collectingId === run.id ? 'Collecting…' : 'Collect diagnostics'}
                    </button>
                    <button
                      type="button"
                      className="run-board__button run-board__delete-button"
                      onClick={() => handleDeleteRun(run.id)}
                      disabled={deletingId === run.id}
                      aria-label={`Delete run ${run.id}`}
                    >
                      <span aria-hidden="true" role="img">
                        🗑️
                      </span>
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {logState.runId ? (
        <section className="run-board__log" aria-live="polite">
          <header className="run-board__log-header">
            <h3>Run log</h3>
            <div className="run-board__log-meta-row">
              <code className="run-board__mono">{logState.runId}</code>
              {logState.status ? (
                <span className={`run-board__status run-board__status--${logState.status}`}>
                  {statusLabels[logState.status as RegistryRunRecord['status']] ?? logState.status}
                </span>
              ) : null}
            </div>
            {logState.status === 'failed' && logState.failureDetails ? (
              <p className="run-board__log-failure" role="status">
                Failure details: {logState.failureDetails}
              </p>
            ) : null}
          </header>
          {logState.error ? (
            <div className="run-board__notice run-board__notice--error" role="alert">
              {logState.error}
            </div>
          ) : null}
          <pre className="run-board__log-output">
            {logState.chunks.length > 0
              ? logState.chunks.map((chunk) => chunk.text).join('')
              : '(no output yet)'}
          </pre>
          <div className="run-board__log-actions">
            <button
              type="button"
              className="run-board__button"
              onClick={handleLoadMore}
              disabled={!logState.hasMoreBefore || logState.loading}
            >
              {logState.loading && logState.hasMoreBefore ? 'Loading…' : 'Load more'}
            </button>
            <button
              type="button"
              className="run-board__button"
              onClick={handleRefresh}
              disabled={logState.loading}
            >
              {logState.loading && !logState.hasMoreBefore ? 'Refreshing…' : 'Refresh'}
            </button>
            {logAbortable ? (
              <button
                type="button"
                className="run-board__button"
                onClick={resetLogState}
              >
                Cancel request
              </button>
            ) : null}
          </div>
          {logState.totalBytes != null ? (
            <p className="run-board__log-meta">
              Showing bytes {logState.startByte ?? 0}–
              {Math.max((logState.nextByte ?? 1) - 1, 0)} of {logState.totalBytes}.
            </p>
          ) : null}
        </section>
      ) : null}
    </div>
  );
};

export default RunBoard;
