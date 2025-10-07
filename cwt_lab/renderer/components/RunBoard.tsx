import { Fragment, useCallback, useEffect, useMemo, useState } from 'react';

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

const experimentIdFromPath = (artifactsDir: string) => {
  const trimmed = artifactsDir.replace(/[\\/]+$/, '');
  if (!trimmed) {
    return artifactsDir;
  }
  const segments = trimmed.split(/[\\/]/).filter(Boolean);
  return segments.length > 0 ? segments[segments.length - 1] : trimmed;
};

const RunBoard = ({ api = defaultRunsApi }: RunBoardProps) => {
  const [runs, setRuns] = useState<RegistryRunRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<NoticeState>(null);
  const [collectingId, setCollectingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [logState, setLogState] = useState<LogState>(() => makeEmptyLogState());
  const [logAbortable, setLogAbortable] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});

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

  const toggleGroup = useCallback((artifactsDir: string) => {
    setExpandedGroups((prev) => ({
      ...prev,
      [artifactsDir]: !(prev[artifactsDir] ?? true),
    }));
  }, []);

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

  const groupedExperiments = useMemo(() => {
    if (runs.length === 0) {
      return [] as Array<{
        artifactsDir: string;
        runs: RegistryRunRecord[];
        label: string;
        experimentId: string;
        lastUpdated: number;
        status: RegistryRunRecord['status'];
        primaryPhase: string | null;
        metrics: Record<string, number | null> | null;
      }>;
    }

    const buckets = new Map<string, RegistryRunRecord[]>();
    for (const run of runs) {
      const key = run.artifactsDir && run.artifactsDir.length > 0 ? run.artifactsDir : `run:${run.id}`;
      const list = buckets.get(key);
      if (list) {
        list.push(run);
      } else {
        buckets.set(key, [run]);
      }
    }

    const groups = Array.from(buckets.entries()).map(([artifactsDir, bucketRuns]) => {
      const sorted = [...bucketRuns].sort((a, b) => {
        if (a.updatedAt === b.updatedAt) {
          return b.createdAt - a.createdAt;
        }
        return b.updatedAt - a.updatedAt;
      });

      const latest = sorted[0];
      const phase1 = sorted.find((run) => run.phase === 'phase1') ?? null;
      const labelCandidate =
        phase1?.label ||
        phase1?.experiment ||
        latest.label ||
        latest.experiment ||
        experimentIdFromPath(artifactsDir);

      const selectMetrics = (record: RegistryRunRecord | null) => {
        if (!record?.metrics) {
          return null;
        }
        return Object.keys(record.metrics).length > 0 ? record.metrics : null;
      };

      const metrics = selectMetrics(phase1) ?? selectMetrics(latest);
      const lastUpdated = sorted.reduce((acc, run) => Math.max(acc, run.updatedAt), 0);

      return {
        artifactsDir,
        runs: sorted,
        label: labelCandidate,
        experimentId: experimentIdFromPath(artifactsDir),
        lastUpdated,
        status: latest.status,
        primaryPhase: phase1?.phase ?? latest.phase ?? null,
        metrics,
      };
    });

    groups.sort((a, b) => b.lastUpdated - a.lastUpdated);
    return groups;
  }, [runs]);

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

  const cancelDeletePrompt = useCallback(() => {
    setConfirmingId(null);
  }, []);

  const requestDeleteRun = useCallback((runId: string) => {
    setConfirmingId(runId);
  }, []);

  const handleDeleteRun = useCallback(
    async (runId: string) => {
      setConfirmingId(null);
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
          className="btn btn--ghost run-board__button run-board__button--refresh"
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
              <th scope="col">Item</th>
              <th scope="col">Status</th>
              <th scope="col">Phase</th>
              <th scope="col">Label / Path</th>
              <th scope="col">Last update</th>
              <th scope="col">Metrics</th>
              <th scope="col" className="run-board__actions-col">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {groupedExperiments.length === 0 ? (
              <tr>
                <td colSpan={7} className="run-board__empty">
                  No runs recorded yet. Launch an experiment to populate the board.
                </td>
              </tr>
            ) : (
              groupedExperiments.map((group) => {
                const isExpanded = expandedGroups[group.artifactsDir] ?? true;
                const statusLabel = statusLabels[group.status] ?? group.status;
                const metricsText = formatMetrics(group.metrics);
                const runCountLabel =
                  group.runs.length === 1 ? '1 phase run' : `${group.runs.length} phase runs`;
                return (
                  <Fragment key={group.artifactsDir}>
                    <tr className="run-board__experiment-row">
                      <td>
                        <button
                          type="button"
                          className="run-board__experiment-toggle"
                          onClick={() => toggleGroup(group.artifactsDir)}
                          aria-expanded={isExpanded}
                        >
                          <span aria-hidden="true" className="run-board__experiment-caret">
                            {isExpanded ? '▾' : '▸'}
                          </span>
                          <span>{group.label}</span>
                        </button>
                        <div className="run-board__experiment-meta">
                          <code className="run-board__mono">{group.experimentId}</code>
                          <span className="run-board__experiment-path">{group.artifactsDir}</span>
                          <span className="run-board__experiment-count">{runCountLabel}</span>
                        </div>
                      </td>
                      <td>
                        <span className={`run-board__status run-board__status--${group.status}`}>
                          {statusLabel}
                        </span>
                      </td>
                      <td>{group.primaryPhase ?? '—'}</td>
                      <td>
                        <code className="run-board__mono">{group.artifactsDir}</code>
                      </td>
                      <td>{formatTimestamp(group.lastUpdated)}</td>
                      <td>{metricsText}</td>
                      <td className="run-board__actions run-board__actions--placeholder">—</td>
                    </tr>
                    {isExpanded
                      ? group.runs.map((run) => (
                          <tr key={run.id} className="run-board__run-row">
                            <td>
                              <div className="run-board__run-label">
                                <span aria-hidden="true" className="run-board__run-bullet">
                                  •
                                </span>
                                <code className="run-board__mono">{run.id}</code>
                              </div>
                            </td>
                            <td>
                              <span className={`run-board__status run-board__status--${run.status}`}>
                                {statusLabels[run.status] ?? run.status}
                              </span>
                            </td>
                            <td>{run.phase ?? '—'}</td>
                            <td>{run.label ?? run.command ?? '—'}</td>
                            <td>{formatTimestamp(run.updatedAt)}</td>
                            <td>{formatMetrics(run.metrics)}</td>
                            <td className="run-board__actions">
                              <button
                                type="button"
                                className="btn btn--ghost btn--small run-board__button"
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
                                className="btn btn--primary btn--small run-board__button"
                                onClick={() => handleCollectDiagnostics(run.id)}
                                disabled={collectingId === run.id}
                              >
                                {collectingId === run.id
                                  ? 'Collecting…'
                                  : 'Collect diagnostics'}
                              </button>
                              {confirmingId === run.id ? (
                                <div
                                  className="run-board__delete-confirm"
                                  role="group"
                                  aria-label={`Confirm deletion of run ${run.id}`}
                                >
                                  <p className="run-board__delete-confirm-message">Are you sure?</p>
                                  <div className="run-board__delete-confirm-actions">
                                    <button
                                      type="button"
                                      className="btn btn--primary btn--small run-board__button run-board__delete-confirm-button"
                                      onClick={() => handleDeleteRun(run.id)}
                                      disabled={deletingId === run.id}
                                    >
                                      <span className="run-board__button-content">
                                        <span aria-hidden="true" role="img">
                                          ✅
                                        </span>
                                        <span>{deletingId === run.id ? 'Deleting…' : 'Yes'}</span>
                                      </span>
                                    </button>
                                    <button
                                      type="button"
                                      className="btn btn--ghost btn--small run-board__button run-board__delete-confirm-button"
                                      onClick={cancelDeletePrompt}
                                      disabled={deletingId === run.id}
                                    >
                                      <span className="run-board__button-content">
                                        <span aria-hidden="true" role="img">
                                          ❌
                                        </span>
                                        <span>No</span>
                                      </span>
                                    </button>
                                  </div>
                                </div>
                              ) : (
                                <button
                                  type="button"
                                  className="btn btn--ghost btn--small run-board__button run-board__delete-button"
                                  onClick={() => requestDeleteRun(run.id)}
                                  disabled={deletingId === run.id}
                                  aria-label={`Delete run ${run.id}`}
                                >
                                  <span aria-hidden="true" role="img">
                                    🗑️
                                  </span>
                                </button>
                              )}
                            </td>
                          </tr>
                        ))
                      : null}
                  </Fragment>
                );
              })
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
              className="btn btn--ghost btn--small run-board__button"
              onClick={handleLoadMore}
              disabled={!logState.hasMoreBefore || logState.loading}
            >
              {logState.loading && logState.hasMoreBefore ? 'Loading…' : 'Load more'}
            </button>
            <button
              type="button"
              className="btn btn--ghost btn--small run-board__button"
              onClick={handleRefresh}
              disabled={logState.loading}
            >
              {logState.loading && !logState.hasMoreBefore ? 'Refreshing…' : 'Refresh'}
            </button>
            {logAbortable ? (
              <button
                type="button"
                className="btn btn--ghost btn--small run-board__button"
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
