import React, { ChangeEvent, useEffect, useMemo } from 'react';
import { PythonCandidate, useEnvStore } from '../store/envSlice';

function formatLastChecked(timestamp: number | null): string | null {
  if (timestamp == null) {
    return null;
  }
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
}

function pythonPathTarget(repoRoot: string | null): string {
  if (!repoRoot) {
    return '<repo>/cwt-sim';
  }
  return `${repoRoot}${repoRoot.endsWith('/') || repoRoot.endsWith('\\') ? '' : '/'}cwt-sim`;
}

function StatusBadge({ label, ok, description }: { label: string; ok: boolean; description?: string }): JSX.Element {
  const toneClass = ok ? 'ok' : 'error';
  return (
    <span className={`env-badge ${toneClass}`} title={description ?? undefined}>
      <strong>{label}</strong>
      <span className="badge-state">{ok ? 'Yes' : 'No'}</span>
    </span>
  );
}

function CandidateCard({ candidate, isSelected, onSelect }: {
  candidate: PythonCandidate;
  isSelected: boolean;
  onSelect: (pythonPath: string) => void;
}): JSX.Element {
  return (
    <div className={`env-candidate ${isSelected ? 'selected' : ''}`}>
      <div className="env-candidate-header">
        <div className="env-candidate-meta">
          <div className="env-candidate-name">{candidate.displayName}</div>
          <div className="env-candidate-path">{candidate.path}</div>
          {candidate.version ? <div className="env-candidate-version">Version: {candidate.version}</div> : null}
        </div>
        <div className="env-candidate-actions">
          <button
            type="button"
            onClick={() => onSelect(candidate.path)}
            disabled={isSelected}
            className="use-python-button"
          >
            {isSelected ? 'In Use' : 'Use this Python'}
          </button>
        </div>
      </div>
      <div className="env-candidate-statuses">
        <StatusBadge label="Installed" ok={candidate.installed} description="Python executable availability" />
        <StatusBadge label="cwt module" ok={candidate.hasCwtModule} description="cwt package importability" />
        <StatusBadge label="PYTHONPATH" ok={candidate.onPythonPath} description="cwt-sim available on PYTHONPATH" />
      </div>
      {candidate.reason ? <div className="env-candidate-note">{candidate.reason}</div> : null}
    </div>
  );
}

export default function EnvDoctor(): JSX.Element {
  const pythonCandidates = useEnvStore((state) => state.pythonCandidates);
  const selectedPython = useEnvStore((state) => state.selectedPython);
  const moduleMode = useEnvStore((state) => state.moduleMode);
  const usePythonPath = useEnvStore((state) => state.usePythonPath);
  const repoRoot = useEnvStore((state) => state.repoRoot);
  const importStatus = useEnvStore((state) => state.importStatus);
  const importMessage = useEnvStore((state) => state.importMessage);
  const importError = useEnvStore((state) => state.importError);
  const lastCheckedAt = useEnvStore((state) => state.lastCheckedAt);
  const isLoadingCandidates = useEnvStore((state) => state.isLoadingCandidates);
  const isCheckingImport = useEnvStore((state) => state.isCheckingImport);
  const loadEnvState = useEnvStore((state) => state.loadEnvState);
  const usePython = useEnvStore((state) => state.usePython);
  const setModuleMode = useEnvStore((state) => state.setModuleMode);
  const setUsePythonPath = useEnvStore((state) => state.setUsePythonPath);
  const checkImport = useEnvStore((state) => state.checkImport);

  useEffect(() => {
    const initialize = async () => {
      try {
        await loadEnvState();
      } catch (error) {
        // Errors are captured within the store state.
      }

      const state = useEnvStore.getState();
      if (state.importStatus === 'unknown' && state.selectedPython) {
        void state.checkImport().catch(() => undefined);
      }
      if (!state.pythonCandidates.length) {
        void state.refreshCandidates().catch(() => undefined);
      }
    };

    void initialize();
  }, [loadEnvState]);

  const handleSelectPython = (pythonPath: string) => {
    void usePython(pythonPath).catch(() => undefined);
  };

  const handleModuleModeChange = (event: ChangeEvent<HTMLInputElement>) => {
    const enabled = event.target.checked;
    void setModuleMode(enabled)
      .then(() => {
        void checkImport();
      })
      .catch(() => undefined);
  };

  const handlePythonPathChange = (event: ChangeEvent<HTMLInputElement>) => {
    const enabled = event.target.checked;
    void setUsePythonPath(enabled)
      .then(() => {
        void checkImport();
      })
      .catch(() => undefined);
  };

  const pythonPathTargetValue = useMemo(() => pythonPathTarget(repoRoot), [repoRoot]);
  const lastCheckedLabel = useMemo(() => formatLastChecked(lastCheckedAt), [lastCheckedAt]);

  let statusClass = 'unknown';
  let statusText = 'Run a check to verify cwt importability.';

  if (importStatus === 'checking') {
    statusClass = 'checking';
    statusText = 'Checking cwt importability…';
  } else if (importStatus === 'ok') {
    statusClass = 'ok';
    statusText = importMessage ?? 'cwt import succeeded.';
  } else if (importStatus === 'error') {
    statusClass = 'error';
    statusText = importError ?? 'Unable to import cwt.';
  }

  return (
    <div className="env-doctor">
      <section className="python-section">
        <div className="section-header">
          <h2>Python interpreters</h2>
          {isLoadingCandidates ? <span className="section-status">Scanning…</span> : null}
        </div>
        {pythonCandidates.length === 0 && !isLoadingCandidates ? (
          <p className="empty-state">No Python interpreters detected yet.</p>
        ) : (
          <div className="env-candidate-grid">
            {pythonCandidates.map((candidate) => (
              <CandidateCard
                key={candidate.path}
                candidate={candidate}
                isSelected={candidate.path === selectedPython}
                onSelect={handleSelectPython}
              />
            ))}
          </div>
        )}
      </section>

      <section className="import-section">
        <div className="section-header">
          <h2>cwt import status</h2>
          {lastCheckedLabel ? <span className="section-status">Last checked: {lastCheckedLabel}</span> : null}
        </div>
        <div className={`import-status status-${statusClass}`}>{statusText}</div>
        <div className="import-actions">
          <button
            type="button"
            onClick={() => {
              void checkImport().catch(() => undefined);
            }}
            disabled={isCheckingImport}
          >
            {isCheckingImport ? 'Checking…' : 'Re-check'}
          </button>
        </div>
        {importStatus === 'error' ? (
          <div className="import-guidance">
            <h3>Auto-fix tips</h3>
            <label className="guidance-toggle">
              <input type="checkbox" checked={moduleMode} onChange={handleModuleModeChange} />
              <span>Run in module mode (set cwd to cwt-sim and use -m invocations)</span>
            </label>
            <label className="guidance-toggle">
              <input type="checkbox" checked={usePythonPath} onChange={handlePythonPathChange} />
              <span>Temporarily set PYTHONPATH = {pythonPathTargetValue}</span>
            </label>
          </div>
        ) : null}
      </section>
    </div>
  );
}
