import {
  type ChangeEvent,
  type FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import type { EnvCandidate, EnvConfig, EnvDetectResult, PythonStrategy } from '../types/ipc';

type ManualPathUpdateOptions = { fromUser?: boolean; force?: boolean };

type CandidateState = {
  loading: boolean;
  candidates: EnvCandidate[];
  selected: EnvCandidate | null;
  error: string | null;
};

type PathNotice =
  | { kind: 'success'; message: string }
  | { kind: 'error'; message: string }
  | null;

const strategyLabels: Record<PythonStrategy, string> = {
  installed: 'installed',
  module: 'module',
  py_path: 'py_path',
};

const strategyDescriptions: Record<PythonStrategy, string> = {
  installed: 'Imports the cwt package directly from site-packages.',
  module: 'Loads the experiments module from cwt-sim as a package.',
  py_path: 'Injects cwt onto PYTHONPATH before launching commands.',
};

const detectionProgressMessages = [
  'Starting interpreter scan…',
  'Checking interpreter locations…',
  'Attempting imports from detected interpreters…',
  'Wrapping up interpreter scan…',
] as const;

const formatTimestampedSummary = (detail: string) =>
  `Last scan at ${new Date().toLocaleTimeString()}: ${detail}`;

const idleStatusMessage =
  'No interpreter scan has been run yet — click "Start interpreter scan" to begin.';

const buildScanSummary = (result: EnvDetectResult | null, error?: string) => {
  if (!result) {
    return formatTimestampedSummary(
      error ? `scan failed — ${error}` : 'scan completed but returned no data.',
    );
  }

  const total = result.candidates.length;
  const interpreterLabel = `${total} interpreter${total === 1 ? '' : 's'}`;

  if (error) {
    if (total === 0) {
      return formatTimestampedSummary(`no interpreters were detected — ${error}`);
    }
    return formatTimestampedSummary(`detected ${interpreterLabel}, but none usable — ${error}`);
  }

  if (result.selected) {
    return formatTimestampedSummary(
      `detected ${interpreterLabel}; active environment ${result.selected.path}.`,
    );
  }

  if (total === 0) {
    return formatTimestampedSummary(
      'no interpreters were detected. Configure a Python path and rerun the scan.',
    );
  }

  return formatTimestampedSummary(
    `detected ${interpreterLabel}, but none passed validation. Review the errors below.`,
  );
};

const parseCandidateErrors = (error?: string): string[] => {
  if (!error) {
    return [];
  }
  return error
    .split('|')
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0);
};

const formatStrategy = (strategy: PythonStrategy | null) => {
  if (!strategy) {
    return '—';
  }
  return strategyLabels[strategy];
};

const isWindowsEnvironment = (): boolean => {
  const globalProcess = (globalThis as { process?: { platform?: string } }).process;
  if (typeof globalProcess?.platform === 'string') {
    return globalProcess.platform === 'win32';
  }

  if (typeof navigator !== 'undefined') {
    const platform =
      (navigator as { userAgentData?: { platform?: string } }).userAgentData?.platform ??
      navigator.platform ??
      '';
    return platform.toLowerCase().includes('win');
  }

  return false;
};

const getPythonPathPlaceholder = (): string =>
  isWindowsEnvironment()
    ? 'C:\\\\path\\\\to\\\\.venv\\\\Scripts\\\\python.exe'
    : '/path/to/.venv/bin/python';

const EnvDoctor = () => {
  const [ipcAvailable, setIpcAvailable] = useState(
    () => typeof window !== 'undefined' && Boolean(window?.CWT?.env?.detect),
  );
  const [candidateState, setCandidateState] = useState<CandidateState>(() => ({
    loading: false,
    candidates: [],
    selected: null,
    error: null,
  }));
  const [config, setConfig] = useState<EnvConfig | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);
  const [pathNotice, setPathNotice] = useState<PathNotice>(null);
  const [pathBusy, setPathBusy] = useState(false);
  const [browseBusy, setBrowseBusy] = useState(false);
  const [manualPath, setManualPath] = useState('');
  const [phase2RootInput, setPhase2RootInput] = useState('');
  const [phase2RootNotice, setPhase2RootNotice] = useState<PathNotice>(null);
  const [phase2RootBusy, setPhase2RootBusy] = useState(false);
  const [progressIndex, setProgressIndex] = useState(0);
  const [lastScanSummary, setLastScanSummary] = useState<string | null>(null);
  const [timeoutWarning, setTimeoutWarning] = useState<string | null>(null);
  const manualPathTouched = useRef(false);
  const isMounted = useRef(true);
  const detectionTimeoutRef = useRef<number | null>(null);
  const detectionInFlightRef = useRef(false);

  useEffect(
    () => () => {
      isMounted.current = false;
      if (typeof window !== 'undefined' && detectionTimeoutRef.current !== null) {
        window.clearTimeout(detectionTimeoutRef.current);
      }
    },
    [],
  );

  const updateManualPath = useCallback(
    (value: string, options: ManualPathUpdateOptions = {}) => {
      console.debug('[EnvDoctor] Updating manual Python path.', {
        value,
        fromUser: Boolean(options.fromUser),
        force: Boolean(options.force),
      });
      if (options.fromUser) {
        manualPathTouched.current = true;
        setManualPath(value);
        return;
      }
      if (!manualPathTouched.current || options.force) {
        setManualPath(value);
      }
    },
    [],
  );

  const refreshConfig = useCallback(
    async (options: ManualPathUpdateOptions = {}) => {
      const api = typeof window !== 'undefined' ? window?.CWT?.env : undefined;
      if (!api?.getConfig) {
        return;
      }
      try {
        console.info('[EnvDoctor] Requesting environment configuration.');
        const response = await api.getConfig();
        if (!isMounted.current) {
          return;
        }
        if (response.ok) {
          console.info('[EnvDoctor] Environment configuration loaded.');
          setConfig(response.data);
          setConfigError(null);
          const value = response.data.pythonPath ?? '';
          if (value || options.force) {
            updateManualPath(value, options);
          }
          setPhase2RootInput(
            response.data.phase2MetricsRoot ?? response.data.artifactsRoot ?? '',
          );
        } else {
          console.warn('[EnvDoctor] Failed to load environment configuration.', {
            error: response.error,
          });
          setConfigError(response.error ?? 'Failed to load environment configuration.');
        }
      } catch (error) {
        if (!isMounted.current) {
          return;
        }
        const message = error instanceof Error ? error.message : String(error);
        console.error('[EnvDoctor] Unexpected error while loading configuration.', error);
        setConfigError(message);
      }
    },
    [updateManualPath],
  );

  const runDetection = useCallback(async () => {
    const api = typeof window !== 'undefined' ? window?.CWT?.env : undefined;
    if (!api?.detect) {
      console.warn('[EnvDoctor] Detection API unavailable.');
      if (isMounted.current) {
        setIpcAvailable(false);
        setCandidateState((prev) => ({ ...prev, loading: false }));
        setLastScanSummary(
          formatTimestampedSummary(
            'interpreter scan unavailable — launch the laboratory Electron app to run diagnostics.',
          ),
        );
      }
      return;
    }

    if (detectionInFlightRef.current) {
      console.info('[EnvDoctor] Detection request ignored because a scan is already running.');
      return;
    }

    detectionInFlightRef.current = true;

    if (isMounted.current) {
      console.info('[EnvDoctor] Starting interpreter detection run.');
      setIpcAvailable(true);
      setTimeoutWarning(null);
      setProgressIndex(0);
      setCandidateState((prev) => ({ ...prev, loading: true, error: null }));
      if (typeof window !== 'undefined') {
        if (detectionTimeoutRef.current !== null) {
          window.clearTimeout(detectionTimeoutRef.current);
        }
        detectionTimeoutRef.current = window.setTimeout(() => {
          if (!isMounted.current) {
            return;
          }
          console.warn('[EnvDoctor] Detection is taking longer than expected.');
          setTimeoutWarning(
            'Interpreter scanning is taking longer than expected. Ensure the laboratory Electron app remains open and check the developer tools console for detailed logs.',
          );
        }, 30000);
      }
    }

    try {
      const response = await api.detect();
      if (!isMounted.current) {
        return;
      }
      if (response.ok) {
        console.info('[EnvDoctor] Detection run completed successfully.', {
          candidateCount: response.data.candidates.length,
          selected: response.data.selected?.path ?? null,
        });
        setCandidateState({
          loading: false,
          candidates: response.data.candidates,
          selected: response.data.selected,
          error: null,
        });
        setLastScanSummary(buildScanSummary(response.data));
        if (response.data.selected?.path) {
          updateManualPath(response.data.selected.path);
        }
      } else {
        console.warn('[EnvDoctor] Detection run completed with reported errors.', {
          error: response.error,
        });
        setCandidateState({
          loading: false,
          candidates: response.data?.candidates ?? [],
          selected: response.data?.selected ?? null,
          error: response.error ?? 'Failed to detect Python interpreters.',
        });
        setLastScanSummary(buildScanSummary(response.data ?? null, response.error));
      }
    } catch (error) {
      if (!isMounted.current) {
        return;
      }
      const message = error instanceof Error ? error.message : String(error);
      console.error('[EnvDoctor] Detection run failed due to an unexpected error.', error);
      setCandidateState((prev) => ({ ...prev, loading: false, error: message }));
      setLastScanSummary(buildScanSummary(null, message));
    } finally {
      detectionInFlightRef.current = false;
      if (typeof window !== 'undefined' && detectionTimeoutRef.current !== null) {
        window.clearTimeout(detectionTimeoutRef.current);
        detectionTimeoutRef.current = null;
      }
    }
  }, [updateManualPath]);

  useEffect(() => {
    if (!candidateState.loading) {
      return;
    }
    setProgressIndex(0);
    if (typeof window === 'undefined') {
      return;
    }
    const intervalId = window.setInterval(() => {
      setProgressIndex((prev) => (prev + 1) % detectionProgressMessages.length);
    }, 5000);
    return () => {
      window.clearInterval(intervalId);
    };
  }, [candidateState.loading]);

  useEffect(() => {
    void refreshConfig();
  }, [refreshConfig]);

  const activeCandidate = useMemo(() => {
    if (!candidateState.selected) {
      return null;
    }
    return (
      candidateState.candidates.find(
        (candidate) => candidate.path === candidateState.selected?.path,
      ) ?? candidateState.selected
    );
  }, [candidateState.candidates, candidateState.selected]);

  const statusMessage = useMemo(() => {
    if (candidateState.loading) {
      return detectionProgressMessages[progressIndex];
    }
    return lastScanSummary ?? idleStatusMessage;
  }, [candidateState.loading, lastScanSummary, progressIndex]);

  const statusClassName = useMemo(
    () =>
      candidateState.loading
        ? 'env-doctor__status env-doctor__status--running'
        : 'env-doctor__status env-doctor__status--idle',
    [candidateState.loading],
  );

  const handleRefresh = useCallback(() => {
    console.info('[EnvDoctor] Interpreter scan requested via UI.');
    void runDetection();
  }, [runDetection]);

  const handleManualPathChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      console.debug('[EnvDoctor] Manual Python path input changed.', {
        value: event.target.value,
      });
      updateManualPath(event.target.value, { fromUser: true });
    },
    [updateManualPath],
  );

  const handleBrowseForInterpreter = useCallback(async () => {
    console.info('[EnvDoctor] Browse for Python executable requested.');
    const api = typeof window !== 'undefined' ? window?.CWT?.env : undefined;
    if (!api?.browsePythonExecutable) {
      console.warn('[EnvDoctor] Browse API unavailable in this build.');
      setPathNotice({
        kind: 'error',
        message: 'Python path browsing is unavailable in this build.',
      });
      return;
    }
    if (browseBusy) {
      return;
    }

    setPathNotice(null);
    setBrowseBusy(true);
    try {
      const response = await api.browsePythonExecutable();
      const browseError = response.ok ? null : response.error ?? null;
      console.debug('[EnvDoctor] Browse result received.', {
        ok: response.ok,
        canceled: response.data?.canceled ?? null,
        path: response.data?.path ?? null,
        error: browseError,
      });
      if (!isMounted.current) {
        return;
      }
      if (response.ok) {
        if (!response.data.canceled && response.data.path) {
          manualPathTouched.current = true;
          updateManualPath(response.data.path, { force: true });
        }
      } else {
        setPathNotice({
          kind: 'error',
          message: response.error ?? 'Failed to open file picker.',
        });
      }
    } catch (error) {
      if (!isMounted.current) {
        return;
      }
      const message = error instanceof Error ? error.message : String(error);
      setPathNotice({ kind: 'error', message });
    } finally {
      if (isMounted.current) {
        setBrowseBusy(false);
      }
    }
  }, [browseBusy, updateManualPath]);

  const handleSetPythonPath = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setPathNotice(null);

      const api = typeof window !== 'undefined' ? window?.CWT?.env : undefined;
      if (!api?.setPythonPath) {
        console.warn('[EnvDoctor] Set Python path API unavailable in this build.');
        setPathNotice({
          kind: 'error',
          message: 'Python path configuration is unavailable in this build.',
        });
        return;
      }

      const trimmed = manualPath.trim();
      console.info('[EnvDoctor] Attempting to set Python path.', { trimmed });
      if (!trimmed) {
        setPathNotice({ kind: 'error', message: 'Provide the path to a Python executable.' });
        return;
      }

      setPathBusy(true);
      try {
        const response = await api.setPythonPath(trimmed);
        const responseError = response.ok ? null : response.error ?? null;
        console.debug('[EnvDoctor] Set Python path response received.', {
          ok: response.ok,
          candidate: response.data ?? null,
          error: responseError,
        });
        if (!isMounted.current) {
          return;
        }
        if (response.ok) {
          const candidate = response.data;
          console.info('[EnvDoctor] Python path updated successfully.', {
            path: candidate.path ?? trimmed,
          });
          updateManualPath(candidate.path ?? trimmed, { force: true });
          setPathNotice({ kind: 'success', message: `Interpreter set to ${candidate.path}.` });
          await runDetection();
          await refreshConfig({ force: true });
        } else {
          console.warn('[EnvDoctor] Failed to set Python path.', {
            error: response.error,
          });
          setPathNotice({
            kind: 'error',
            message: response.error ?? 'Failed to set Python path.',
          });
        }
      } catch (error) {
        if (!isMounted.current) {
          return;
        }
        const message = error instanceof Error ? error.message : String(error);
        console.error('[EnvDoctor] Unexpected error while setting Python path.', error);
        setPathNotice({ kind: 'error', message });
      } finally {
        if (isMounted.current) {
          setPathBusy(false);
        }
      }
    },
    [manualPath, refreshConfig, runDetection, updateManualPath],
  );

  const pythonPathPlaceholder = useMemo(() => getPythonPathPlaceholder(), []);

  const handlePhase2RootChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    setPhase2RootInput(event.target.value);
  }, []);

  const handleResetPhase2Root = useCallback(() => {
    setPhase2RootInput('');
    setPhase2RootNotice(null);
  }, []);

  const handleSetPhase2Root = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const api = typeof window !== 'undefined' ? window?.CWT?.env : undefined;
      if (!api?.setPhase2MetricsRoot) {
        setPhase2RootNotice({
          kind: 'error',
          message:
            'Updating the Phase-2 artifacts root is unavailable in this build. Launch the Electron app for full configuration.',
        });
        return;
      }
      if (phase2RootBusy) {
        return;
      }
      setPhase2RootBusy(true);
      setPhase2RootNotice(null);
      try {
        const trimmed = phase2RootInput.trim();
        const response = await api.setPhase2MetricsRoot({ path: trimmed.length > 0 ? trimmed : null });
        if (!isMounted.current) {
          return;
        }
        if (response.ok) {
          const effective = response.data.path;
          setPhase2RootNotice({
            kind: 'success',
            message: effective
              ? `Phase-2 artifacts root set to ${effective}.`
              : 'Phase-2 artifacts root cleared. Using the default artifacts folder.',
          });
          await refreshConfig();
        } else {
          setPhase2RootNotice({
            kind: 'error',
            message: response.error ?? 'Failed to update Phase-2 artifacts root.',
          });
        }
      } catch (error) {
        if (!isMounted.current) {
          return;
        }
        const message = error instanceof Error ? error.message : String(error);
        setPhase2RootNotice({ kind: 'error', message });
      } finally {
        if (isMounted.current) {
          setPhase2RootBusy(false);
        }
      }
    },
    [phase2RootBusy, phase2RootInput, refreshConfig],
  );

  return (
    <div className="panel env-doctor">
      <div className="env-doctor__header">
        <h2>Environment Doctor</h2>
        <p>
          Diagnose Python installations and virtual environment configuration before launching
          experiments.
        </p>
      </div>

      <p className="env-doctor__intro">
        Environment Doctor inspects available Python interpreters, verifies that{' '}
        <code>cwt</code> loads correctly, and highlights fixes when something goes wrong.
      </p>
      <ul className="env-doctor__list">
        <li>Discovers interpreters from PATH, virtual environments, and configured locations.</li>
        <li>
          Runs import checks against <code>cwt</code> to confirm required dependencies.
        </li>
        <li>Captures detailed failure messages so you know how to repair your setup.</li>
      </ul>

      {!ipcAvailable && (
        <div className="env-doctor__notice env-doctor__notice--info">
          Desktop IPC bridge unavailable. Launch the laboratory Electron app to run interpreter diagnostics.
        </div>
      )}

      <div className="env-doctor__actions">
        <button
          type="button"
          className={
            candidateState.loading
              ? 'env-doctor__button env-doctor__button--busy'
              : 'env-doctor__button'
          }
          onClick={handleRefresh}
          disabled={!ipcAvailable || candidateState.loading}
          aria-busy={candidateState.loading}
        >
          {candidateState.loading ? 'Scanning interpreters…' : 'Start interpreter scan'}
        </button>
        <span
          role="status"
          className={statusClassName}
          aria-live="polite"
          aria-atomic="true"
        >
          {statusMessage}
        </span>
      </div>

      {timeoutWarning && (
        <div role="alert" className="env-doctor__notice env-doctor__notice--info">
          {timeoutWarning}
        </div>
      )}

      <form className="env-doctor__form" onSubmit={handleSetPythonPath}>
        <label className="env-doctor__label" htmlFor="env-doctor-python-path">
          Python executable
        </label>
        <div className="env-doctor__form-row">
          <input
            id="env-doctor-python-path"
            type="text"
            className="env-doctor__input"
            placeholder={pythonPathPlaceholder}
            value={manualPath}
            onChange={handleManualPathChange}
            disabled={!ipcAvailable || pathBusy}
          />
          <button
            type="button"
            className={
              browseBusy ? 'env-doctor__button env-doctor__button--busy' : 'env-doctor__button'
            }
            onClick={handleBrowseForInterpreter}
            disabled={!ipcAvailable || pathBusy || browseBusy}
            aria-busy={browseBusy}
          >
            Browse…
          </button>
          <button
            type="submit"
            className={
              pathBusy ? 'env-doctor__button env-doctor__button--busy' : 'env-doctor__button'
            }
            disabled={!ipcAvailable || pathBusy || manualPath.trim().length === 0}
            aria-busy={pathBusy}
          >
            Set Python Path
          </button>
        </div>
        <p className="env-doctor__hint">
          Point to the Python executable inside the virtual environment prepared with
          <code> pip install -r requirements.txt</code> and
          <code> pip install -r requirements.test.txt</code>.
        </p>
      </form>

      {pathNotice && (
        <div
          role={pathNotice.kind === 'success' ? 'status' : 'alert'}
          className={`env-doctor__notice env-doctor__notice--${pathNotice.kind}`}
        >
          {pathNotice.message}
        </div>
      )}

      {candidateState.error && (
        <div role="alert" className="env-doctor__notice env-doctor__notice--error">
          {candidateState.error}
        </div>
      )}

      {configError && (
        <div role="alert" className="env-doctor__notice env-doctor__notice--error">
          {configError}
        </div>
      )}

      {activeCandidate && (
        <div className="env-doctor__active">
          <h3>Active interpreter</h3>
          <code className="env-doctor__mono">{activeCandidate.path}</code>
          <dl className="env-doctor__meta">
            <div>
              <dt>Version</dt>
              <dd>{activeCandidate.version ?? 'Unknown'}</dd>
            </div>
            <div>
              <dt>Strategy</dt>
              <dd>{formatStrategy(activeCandidate.strategy)}</dd>
            </div>
          </dl>
        </div>
      )}

      <div className="env-doctor__candidates">
        {candidateState.candidates.map((candidate) => {
          const ok = candidate.ok;
          const selected = candidateState.selected?.path === candidate.path;
          const errors = parseCandidateErrors(candidate.error);
          return (
            <div
              key={`${candidate.path}-${candidate.version ?? 'unknown'}`}
              className={`env-doctor__candidate env-doctor__candidate--${ok ? 'ok' : 'bad'}${
                selected ? ' env-doctor__candidate--selected' : ''
              }`}
            >
              <div className="env-doctor__candidate-header">
                <span className={`env-doctor__badge env-doctor__badge--${ok ? 'ok' : 'bad'}`}>
                  {ok ? 'Healthy' : 'Needs attention'}
                </span>
                {selected && <span className="env-doctor__badge env-doctor__badge--active">Active</span>}
              </div>
              <code className="env-doctor__candidate-path">{candidate.path}</code>
              <dl className="env-doctor__meta">
                <div>
                  <dt>Version</dt>
                  <dd>{candidate.version ?? 'Unknown'}</dd>
                </div>
                <div>
                  <dt>Strategy</dt>
                  <dd>{formatStrategy(candidate.strategy)}</dd>
                </div>
              </dl>
              {ok && candidate.strategy ? (
                <p className="env-doctor__candidate-message">{strategyDescriptions[candidate.strategy]}</p>
              ) : null}
              {!ok && errors.length > 0 ? (
                <ul className="env-doctor__candidate-errors">
                  {errors.map((entry, index) => (
                    <li key={`${candidate.path}-error-${index}`}>{entry}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          );
        })}
      </div>

      {candidateState.candidates.length === 0 && !candidateState.loading && (
        <p className="env-doctor__empty">
          No interpreters recorded yet. Run detection or set the Python path manually to bootstrap the toolchain.
        </p>
      )}

      {config && (
        <div className="env-doctor__config">
          <h3>Environment context</h3>
          <dl>
            <div>
              <dt>Repository root</dt>
              <dd className="env-doctor__mono">{config.repoRoot}</dd>
            </div>
            <div>
              <dt>Artifacts root</dt>
              <dd className="env-doctor__mono">{config.artifactsRoot}</dd>
            </div>
            <div>
              <dt>Phase-2 artifacts root</dt>
              <dd className="env-doctor__mono">
                {config.phase2MetricsRoot ?? config.artifactsRoot}
                {!config.phase2MetricsRoot ? ' (default)' : ''}
              </dd>
            </div>
            <div>
              <dt>Preferred strategy</dt>
              <dd>{config.strategy ? strategyLabels[config.strategy] : 'Not set'}</dd>
            </div>
          </dl>
          <form className="env-doctor__form" onSubmit={handleSetPhase2Root}>
            <label className="env-doctor__label" htmlFor="env-doctor-phase2-root">
              Phase-2 artifacts root
            </label>
            <div className="env-doctor__form-row">
              <input
                id="env-doctor-phase2-root"
                type="text"
                className="env-doctor__input"
                value={phase2RootInput}
                onChange={handlePhase2RootChange}
                disabled={!ipcAvailable || phase2RootBusy}
              />
              <button
                type="button"
                className="env-doctor__button"
                onClick={handleResetPhase2Root}
                disabled={!ipcAvailable || phase2RootBusy || phase2RootInput.trim().length === 0}
              >
                Reset
              </button>
              <button
                type="submit"
                className={
                  phase2RootBusy
                    ? 'env-doctor__button env-doctor__button--busy'
                    : 'env-doctor__button'
                }
                disabled={!ipcAvailable || phase2RootBusy}
                aria-busy={phase2RootBusy}
              >
                Save Phase-2 root
              </button>
            </div>
            <p className="env-doctor__hint">
              Configure the base directory Phase 2 uses when listing Phase-1 outputs. Leave this blank to
              fall back to the default artifacts folder.
            </p>
          </form>
          {phase2RootNotice && (
            <div
              role={phase2RootNotice.kind === 'success' ? 'status' : 'alert'}
              className={`env-doctor__notice env-doctor__notice--${phase2RootNotice.kind}`}
            >
              {phase2RootNotice.message}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default EnvDoctor;
