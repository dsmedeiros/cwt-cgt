import { ChangeEvent, useCallback, useEffect, useMemo, useState } from 'react';

import ArtifactBrowser from './components/ArtifactBrowser';
import HelpDrawer from './components/HelpDrawer';
import EnvDoctor from './components/EnvDoctor';
import Phase1Mapping from './components/Phase1Mapping';
import Phase2Features from './components/Phase2Features';
import Phase3Loops from './components/Phase3Loops';
import Phase4Explorer3D from './components/Phase4Explorer3D';
import Phase5Optimize from './components/Phase5Optimize';
import TorusPlateauViewer from './components/TorusPlateauViewer';
import RunBoard, { type RunsApi } from './components/RunBoard';
import RecipeComparison from './components/RecipeComparison';
import { CommandProvider, useCommandCenter, useCommandCombos } from './commandCenter';
import { DemoModeProvider, useDemoMode, type DemoRun } from './demo/DemoModeContext';
import { useTranslation } from './i18n';
import { useExperimentNavigation } from './navigation/ExperimentNavigationContext';
import { useThemeMode } from './theme';

const DEFAULT_LOG_CHUNK = 8_192;

const TABS_WITHOUT_ARTIFACT_SELECTORS = new Set([
  'runs',
  'phase1',
  'comparison',
  'artifacts',
  'env',
]);

const createDemoRunsApi = (runs: DemoRun[]): RunsApi => {
  const byId = new Map(runs.map((entry) => [entry.record.id, entry]));

  const sliceLog = (log: string, fromByte?: number, maxBytes = DEFAULT_LOG_CHUNK) => {
    const total = log.length;
    if (total === 0) {
      return {
        output: '',
        startFromByte: 0,
        nextFromByte: 0,
        totalBytes: 0,
        hasMoreBefore: false,
      };
    }
    let start = 0;
    if (typeof fromByte === 'number') {
      if (fromByte < 0) {
        start = Math.max(total + fromByte, 0);
      } else {
        start = Math.min(fromByte, total);
      }
    } else {
      start = Math.max(0, total - maxBytes);
    }
    const end = Math.min(total, start + maxBytes);
    const output = log.slice(start, end);
    return {
      output,
      startFromByte: start,
      nextFromByte: end,
      totalBytes: total,
      hasMoreBefore: start > 0,
    };
  };

  return {
    async listRecent() {
      await new Promise((resolve) => setTimeout(resolve, 120));
      return runs.map((entry) => entry.record);
    },
    async collectDiagnostics(runId) {
      await new Promise((resolve) => setTimeout(resolve, 80));
      const entry = byId.get(runId);
      if (!entry) {
        throw new Error(`Run ${runId} not found in demo catalog.`);
      }
      return entry.diagnostics;
    },
    async tail({ runId, fromByte, maxBytes }) {
      await new Promise((resolve) => setTimeout(resolve, 60));
      const entry = byId.get(runId);
      if (!entry) {
        throw new Error(`Run ${runId} not found in demo catalog.`);
      }
      const slice = sliceLog(entry.log, fromByte, maxBytes);
      return {
        ...slice,
        status: entry.record.status,
        failureDetails:
          entry.record.status === 'failed'
            ? 'Demo mode does not include failure diagnostics.'
            : null,
      };
    },
    async deleteRun(runId) {
      await new Promise((resolve) => setTimeout(resolve, 60));
      const index = runs.findIndex((entry) => entry.record.id === runId);
      if (index === -1) {
        throw new Error(`Run ${runId} not found in demo catalog.`);
      }
      const [removed] = runs.splice(index, 1);
      byId.delete(runId);
      return { runId: removed.record.id };
    },
  };
};

type AppContentProps = {
  mode: 'light' | 'dark';
  onToggleTheme: () => void;
  demoEnabled: boolean;
  onToggleDemo: () => void;
};

const AppContent = ({ mode, onToggleTheme, demoEnabled, onToggleDemo }: AppContentProps) => {
  const [active, setActive] = useState('runs');
  const [helpOpen, setHelpOpen] = useState(false);
  const { runDescription, abortDescription, status } = useCommandCenter();
  const combos = useCommandCombos();
  const { runs: demoRuns } = useDemoMode();
  const { t } = useTranslation();
  const {
    experiments,
    experimentsError,
    experimentsLoading,
    selectedExperimentPath,
    setSelectedExperimentPath,
    substrates,
    substratesError,
    substratesLoading,
    selectedSubstratePath,
    setSelectedSubstratePath,
  } = useExperimentNavigation();

  const demoRunsApi = useMemo<RunsApi | undefined>(
    () => (demoEnabled ? createDemoRunsApi(demoRuns) : undefined),
    [demoEnabled, demoRuns],
  );

  const tabs = useMemo(
    () => [
      { id: 'runs', label: 'Run Board', element: <RunBoard api={demoRunsApi} /> },
      { id: 'phase1', label: 'Phase 1', element: <Phase1Mapping /> },
      { id: 'phase2', label: 'Phase 2', element: <Phase2Features /> },
      { id: 'phase3', label: 'Phase 3', element: <Phase3Loops /> },
      { id: 'phase4', label: 'Phase 4', element: <Phase4Explorer3D /> },
      { id: 'torus', label: 'Torus Plateau', element: <TorusPlateauViewer /> },
      { id: 'phase5', label: 'Phase 5', element: <Phase5Optimize /> },
      { id: 'comparison', label: 'Comparison', element: <RecipeComparison /> },
      { id: 'artifacts', label: 'Artifacts', element: <ArtifactBrowser /> },
      { id: 'env', label: 'Env Doctor', element: <EnvDoctor /> },
    ],
    [demoRunsApi],
  );

  const activeHelp = useMemo(() => {
    const baseBullets = [
      'Treat the phase map like a compass: north-east motion nudges the system hotter, south-west cools it.',
      'Keep an eye on the stability guard – it is your avalanche warning flag.',
      'Φ near zero means the ridge is flat; wide swings signal steep terrain.',
      'R close to one tells you the flock is moving together; near zero means chaos.',
    ];
    const config: Record<string, { title: string; analogy: string; bullets: string[] }> = {
      runs: {
        title: 'Run Board overview',
        analogy: 'Think of this board as the expedition logbook – every climb, every stumble recorded in order.',
        bullets: [
          'New runs appear at the top with their timestamps so you can gauge tempo.',
          'Statuses move from pending → running → complete; failed runs are flagged in red.',
          'Use the logbook to spot sequences that cluster – they often share parameter DNA.',
          'Hover over a row for more detail when available; the logbook keeps context handy.',
        ],
      },
      phase1: {
        title: 'Phase 1 – Mapping',
        analogy: 'The phase-1 grid is your mountain scout, a compass overlay that highlights where the slope tilts.',
        bullets: [
          'Warm colours mark steep Ω gradients – that is where sw/sf asymmetry pays off.',
          'If every tile looks flat, widen extents or rotate axes to expose structure.',
          'Percentile thresholds clip the noisiest 1–99% edges to emphasise signal.',
          'Swap between allowed axes to chase the ridge without breaking calibration.',
        ],
      },
      phase2: {
        title: 'Phase 2 – Feature scans',
        analogy: 'Phase-2 metrics behave like weather fronts: gradients warn of turbulence ahead of the climb.',
        bullets: [
          'Correlation bars show which features lift hot tiles; negative values point to stabilisers.',
          'ROC curves balance detection vs false alarms – hug the top-left for confident triggers.',
          'Switch the scatter feature to inspect how individual points line up against the classifier.',
          'Snapshot status summarises whether the latest stats improved or regressed.',
        ],
      },
      phase3: {
        title: 'Phase 3 – Loops',
        analogy: 'Guided loops are like tracing contour lines with a compass, checking how the ridge wraps around the peak.',
        bullets: [
          ...baseBullets,
          'Step counts control how finely you trace the ridge; higher counts resolve detail but cost time.',
          'Guided mode mixes axes like switching to crampons – it stabilises the climb when basic loops slip.',
        ],
      },
      phase4: {
        title: 'Phase 4 – 3D explorer',
        analogy: 'The 3D explorer is a drone flight over the mountain, revealing overhangs that 2D maps hide.',
        bullets: [
          ...baseBullets,
          'Handle steps govern how smooth the climb-in/out handles are drawn – avoid kinks that destabilise.',
          'Compare against a 2D recipe: if Φ barely changes, the drone found no new ridge to exploit.',
        ],
      },
      phase5: {
        title: 'Phase 5 – Optimisation',
        analogy: 'Optimisation is your summit push – every parameter tweak is a deliberate step along the ridge.',
        bullets: [
          'Watch convergence metrics; they tell you if the summit is approaching or if you are circling.',
          'Use recipe provenance to understand which earlier climbs feed the current attempt.',
          'Export results when gradients stabilise; lingering too long can invite drift.',
          'Switch axes if the optimiser stalls – a new bearing can unlock the next move.',
        ],
      },
      torus: {
        title: 'Torus Plateau viewer',
        analogy: 'The torus plot shows the mountain plateau rolled into a doughnut – height wraps seamlessly around.',
        bullets: [
          'Hot bands circling the torus point to resonant lanes worth seeding later phases with.',
          'Gaps or cold troughs imply stable basins – useful for anchoring feedback loops.',
          'Rotate the torus to inspect hidden saddles on the underside.',
          'Use the colour legend as slope steepness: brighter is sharper tilt.',
        ],
      },
      artifacts: {
        title: 'Artifact browser',
        analogy: 'Artifacts are summit souvenirs – organised shelves that help retrace what worked.',
        bullets: [
          'Filter by phase or tag to narrow the wall of data quickly.',
          'Preview thumbnails hint at structure so you can open the right artifact first.',
          'Star favourites to build a short-list when presenting findings.',
          'Download bundles to share with collaborators without digging through directories.',
        ],
      },
      comparison: {
        title: 'Recipe comparison',
        analogy: 'Think of comparison mode as laying two route maps side-by-side to pick the safest ascent.',
        bullets: [
          'Select any two saved protocols to contrast Φ flux, guard margins, and persistence.',
          'Use the evolution plots to see which climb converged faster or held the guard margin longer.',
          'Differences column highlights percentage gaps so you can justify your chosen baseline.',
          'Export snapshots after aligning your preferred pair to share the decision trail.',
        ],
      },
      env: {
        title: 'Environment doctor',
        analogy: 'The environment doctor is base camp – it checks that your ropes, crampons, and radio are intact.',
        bullets: [
          'Candidates list each detected Python environment with quick health status.',
          'Configure the active interpreter before launching runs to avoid broken toolchains.',
          'Logs explain why a candidate failed so you can patch missing dependencies.',
          'The doctor stores your selection locally – no need to re-enter each session.',
        ],
      },
    };
    return config[active] ?? null;
  }, [active]);

  useEffect(() => {
    setHelpOpen(false);
  }, [active]);

  const onExperimentChange = useCallback(
    (event: ChangeEvent<HTMLSelectElement>) => {
      const next = event.target.value;
      setSelectedExperimentPath(next ? next : null);
    },
    [setSelectedExperimentPath],
  );

  const onSubstrateChange = useCallback(
    (event: ChangeEvent<HTMLSelectElement>) => {
      const next = event.target.value;
      setSelectedSubstratePath(next ? next : null);
    },
    [setSelectedSubstratePath],
  );

  const hideArtifactSelectors = TABS_WITHOUT_ARTIFACT_SELECTORS.has(active);
  const experimentSelectDisabled = experimentsLoading || experiments.length === 0;
  const substrateSelectDisabled =
    substratesLoading ||
    !selectedExperimentPath ||
    substrates.length === 0 ||
    !!experimentsError;

  return (
    <div className="app">
      <header className="app__header">
        <h1>{t('app.title', 'CWT Lab')}</h1>
        <div className="app__controls" role="group" aria-label="View controls">
          <button
            type="button"
            className="app__theme-toggle"
            onClick={onToggleTheme}
            aria-label={`Switch to ${mode === 'light' ? 'dark' : 'light'} theme`}
          >
            {mode === 'light' ? '🌙 Dark' : '☀️ Light'}
          </button>
          <button
            type="button"
            className={demoEnabled ? 'app__demo-toggle app__demo-toggle--active' : 'app__demo-toggle'}
            onClick={onToggleDemo}
            aria-pressed={demoEnabled}
            title={t('app.demo.hint', 'Toggle demo mode')}
          >
            {demoEnabled ? t('app.demo.on', 'Demo: On') : t('app.demo.off', 'Demo: Off')}
          </button>
          {activeHelp ? (
            <button
              type="button"
              className="app__help-button"
              onClick={() => setHelpOpen(true)}
              aria-label="Explain this panel"
            >
              ?
            </button>
          ) : null}
        </div>
        <div className="app__shortcut-hints" role="note" aria-label="Keyboard shortcuts">
          <span>
            {combos.run}
            {` – ${runDescription ?? t('app.shortcuts.run', 'Run action')}`}
          </span>
          <span>
            {combos.abort}
            {` – ${abortDescription ?? t('app.shortcuts.abort', 'Abort action')}`}
          </span>
          <span>{`${combos.theme} – ${t('app.shortcuts.theme', 'Toggle theme')}`}</span>
        </div>
        <nav className="app__tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={tab.id === active ? 'app__tab app__tab--active' : 'app__tab'}
              onClick={() => setActive(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
        {hideArtifactSelectors ? null : (
          <div className="app__selectors" role="group" aria-label="Artifact navigation">
            <div className="app__selector">
              <label className="app__selector-label" htmlFor="app-experiment-select">
                Experiment
              </label>
              <select
                id="app-experiment-select"
                value={selectedExperimentPath ?? ''}
                onChange={onExperimentChange}
                disabled={experimentSelectDisabled}
              >
                <option value="">Select an experiment</option>
                {experiments.map((experiment) => (
                  <option key={experiment.path} value={experiment.path}>
                    {experiment.relativePath}
                  </option>
                ))}
              </select>
              {experimentsLoading ? (
                <small className="app__selector-message">Loading experiments…</small>
              ) : experimentsError ? (
                <small className="app__selector-message app__selector-message--error">
                  {experimentsError}
                </small>
              ) : null}
            </div>
            <div className="app__selector">
              <label className="app__selector-label" htmlFor="app-substrate-select">
                Substrate
              </label>
              <select
                id="app-substrate-select"
                value={selectedSubstratePath ?? ''}
                onChange={onSubstrateChange}
                disabled={substrateSelectDisabled}
              >
                <option value="">Select a substrate</option>
                {substrates.map((substrate) => (
                  <option key={substrate.path} value={substrate.path}>
                    {substrate.name ?? substrate.relativePath}
                  </option>
                ))}
              </select>
              {substratesLoading ? (
                <small className="app__selector-message">Loading substrates…</small>
              ) : substratesError ? (
                <small className="app__selector-message app__selector-message--error">
                  {substratesError}
                </small>
              ) : null}
            </div>
          </div>
        )}
      </header>
      <div className="app__body">
        <main className="app__content">
          {tabs.map((tab) =>
            tab.id === active ? (
              <section key={tab.id} className="app__panel">
                {tab.element}
              </section>
            ) : null,
          )}
        </main>
      </div>
      {activeHelp ? (
        <HelpDrawer
          open={helpOpen}
          onClose={() => setHelpOpen(false)}
          title={activeHelp.title}
          analogy={activeHelp.analogy}
          bullets={activeHelp.bullets}
        />
      ) : null}
      {status ? (
        <div className="app__command-status" role="status">
          {status}
        </div>
      ) : null}
    </div>
  );
};

const App = () => {
  const { mode, toggleMode } = useThemeMode();
  const [demoEnabled, setDemoEnabled] = useState(false);

  const toggleDemo = useCallback(() => {
    setDemoEnabled((prev) => !prev);
  }, []);

  return (
    <DemoModeProvider enabled={demoEnabled} onToggle={toggleDemo}>
      <CommandProvider onToggleTheme={toggleMode}>
        <AppContent
          mode={mode}
          onToggleTheme={toggleMode}
          demoEnabled={demoEnabled}
          onToggleDemo={toggleDemo}
        />
      </CommandProvider>
    </DemoModeProvider>
  );
};

export default App;
