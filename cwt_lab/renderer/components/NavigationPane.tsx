import { useMemo } from 'react';

import { useExperimentNavigation } from '../navigation/ExperimentNavigationContext';

const NavigationPane = () => {
  const {
    artifactsRoot,
    experiments,
    experimentsError,
    experimentsLoading,
    selectedExperimentPath,
    setSelectedExperimentPath,
    refreshExperiments,
    substrates,
    substratesError,
    substratesLoading,
    selectedSubstratePath,
    setSelectedSubstratePath,
    refreshSubstrates,
  } = useExperimentNavigation();

  const experimentDisabled = experimentsLoading || experiments.length === 0;
  const substrateDisabled =
    substratesLoading || substrates.length === 0 || !selectedExperimentPath;

  const experimentLabel = useMemo(() => {
    if (experimentsError) {
      return 'Experiments unavailable';
    }
    if (!selectedExperimentPath) {
      return 'Select an experiment';
    }
    return 'Experiment';
  }, [experimentsError, selectedExperimentPath]);

  const substrateLabel = useMemo(() => {
    if (!selectedExperimentPath) {
      return 'Select an experiment first';
    }
    if (substratesError) {
      return 'Substrates unavailable';
    }
    return 'Substrate';
  }, [selectedExperimentPath, substratesError]);

  return (
    <aside className="navigation-pane" aria-label="Experiment and substrate selection">
      <div className="navigation-pane__section">
        <div className="navigation-pane__section-header">
          <h2>Artifacts</h2>
          <button
            type="button"
            className="navigation-pane__refresh"
            onClick={refreshExperiments}
            disabled={experimentsLoading}
            title="Reload experiment list"
          >
            ↻
          </button>
        </div>
        <p className="navigation-pane__hint">
          Base directory: <code>{artifactsRoot ?? 'Not configured'}</code>
        </p>
        <label className="navigation-pane__field" htmlFor="navigation-pane-experiment">
          <span>{experimentLabel}</span>
          <select
            id="navigation-pane-experiment"
            value={selectedExperimentPath ?? ''}
            onChange={(event) => setSelectedExperimentPath(event.target.value || null)}
            disabled={experimentDisabled}
          >
            {experiments.map((experiment) => (
              <option key={experiment.path} value={experiment.path}>
                {experiment.relativePath}
              </option>
            ))}
          </select>
        </label>
        {experimentsLoading ? (
          <p className="navigation-pane__hint" role="status">
            Loading experiments…
          </p>
        ) : experimentsError ? (
          <p className="navigation-pane__error" role="alert">
            {experimentsError}
          </p>
        ) : experiments.length === 0 ? (
          <p className="navigation-pane__hint">
            Run Phase 1 mapping to populate experiments.
          </p>
        ) : null}
      </div>

      <div className="navigation-pane__section">
        <div className="navigation-pane__section-header">
          <h3>Substrate</h3>
          <button
            type="button"
            className="navigation-pane__refresh"
            onClick={refreshSubstrates}
            disabled={substratesLoading || !selectedExperimentPath}
            title="Reload substrates for the selected experiment"
          >
            ↻
          </button>
        </div>
        <label className="navigation-pane__field" htmlFor="navigation-pane-substrate">
          <span>{substrateLabel}</span>
          <select
            id="navigation-pane-substrate"
            value={selectedSubstratePath ?? ''}
            onChange={(event) => setSelectedSubstratePath(event.target.value || null)}
            disabled={substrateDisabled}
          >
            {substrates.map((substrate) => (
              <option key={substrate.path} value={substrate.path}>
                {substrate.name ?? substrate.relativePath}
              </option>
            ))}
          </select>
        </label>
        {substratesLoading ? (
          <p className="navigation-pane__hint" role="status">
            Loading substrates…
          </p>
        ) : substratesError ? (
          <p className="navigation-pane__error" role="alert">
            {substratesError}
          </p>
        ) : substrates.length === 0 && selectedExperimentPath ? (
          <p className="navigation-pane__hint">
            No substrate directories found under this experiment.
          </p>
        ) : null}
      </div>
    </aside>
  );
};

export default NavigationPane;
