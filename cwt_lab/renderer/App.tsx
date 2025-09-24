import { useState } from 'react';

import ArtifactBrowser from './components/ArtifactBrowser';
import EnvDoctor from './components/EnvDoctor';
import Phase1Mapping from './components/Phase1Mapping';
import Phase2Features from './components/Phase2Features';
import Phase3Loops from './components/Phase3Loops';
import Phase4Explorer3D from './components/Phase4Explorer3D';
import Phase5Optimize from './components/Phase5Optimize';
import TorusPlateauViewer from './components/TorusPlateauViewer';
import RunBoard from './components/RunBoard';

const tabs = [
  { id: 'runs', label: 'Run Board', element: <RunBoard /> },
  { id: 'phase1', label: 'Phase 1', element: <Phase1Mapping /> },
  { id: 'phase2', label: 'Phase 2', element: <Phase2Features /> },
  { id: 'phase3', label: 'Phase 3', element: <Phase3Loops /> },
  { id: 'phase4', label: 'Phase 4', element: <Phase4Explorer3D /> },
  { id: 'torus', label: 'Torus Plateau', element: <TorusPlateauViewer /> },
  { id: 'phase5', label: 'Phase 5', element: <Phase5Optimize /> },
  { id: 'artifacts', label: 'Artifacts', element: <ArtifactBrowser /> },
  { id: 'env', label: 'Env Doctor', element: <EnvDoctor /> },
];

const App = () => {
  const [active, setActive] = useState('runs');

  return (
    <div className="app">
      <header className="app__header">
        <h1>CWT Lab</h1>
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
      </header>
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
  );
};

export default App;
