import { contextBridge, ipcRenderer } from 'electron';

import type { IpcEnvelope, RendererIpc } from '../renderer/types/ipc';

const invoke = <T>(channel: string, payload?: unknown) =>
  ipcRenderer.invoke(channel, payload) as Promise<IpcEnvelope<T>>;

const api = {
  shutdown: () => ipcRenderer.invoke('cwt:shutdown') as Promise<void>,
  env: {
    detect: () => invoke('cwt:env:detect'),
    setPythonPath: (path: string) => invoke('cwt:env:set-python-path', path),
    getConfig: () => invoke('cwt:env:get-config'),
    browsePythonExecutable: () => invoke('cwt:env:browse-python'),
  },
  run: {
    create: (payload) => invoke('cwt:run:create', payload),
    preview: (payload) => invoke('cwt:run:preview', payload),
    abort: (payload) => invoke('cwt:run:abort', payload),
    tail: (payload) => invoke('cwt:run:tail', payload),
    openArtifacts: (payload) => invoke('cwt:run:open-artifacts', payload),
    collectDiagnostics: (payload) => invoke('cwt:run:collect-diagnostics', payload),
    delete: (payload) => invoke('cwt:run:delete', payload),
    readArtifact: (payload) => invoke('cwt:run:read-artifact', payload),
  },
  phase1: {
    map: (params) => invoke('cwt:phase1:map', params),
  },
  phase2: {
    browseMetricsDirs: () => invoke('cwt:phase2:browse-metrics-dirs'),
    correlate: (payload) => invoke('cwt:phase2:correlate', payload),
    saveSnapshot: (payload) => invoke('cwt:phase2:save-snapshot', payload),
  },
  phase3: {
    loopAtHotspot: (params) => invoke('cwt:phase3:loop-at-hotspot', params),
    guidedLoop: (params) => invoke('cwt:phase3:guided-loop', params),
    adiabaticBoundary: (params) => invoke('cwt:phase3:adiabatic-boundary', params),
    cmdAdiabaticBoundary: (params) => invoke('cwt:phase3:adiabatic-boundary:analyze', params),
  },
  phase4: {
    wilson3d: (params) => invoke('cwt:phase4:wilson3d', params),
    torusPlateau: (params) => invoke('cwt:phase4:torus-plateau', params),
  },
  phase5: {
    graphFamily: (params) => invoke('cwt:phase5:graph-family', params),
    cmdGraphFamily: (params) => invoke('cwt:phase5:graph-family:analyze', params),
    inverseDesign: (params) => invoke('cwt:phase5:inverse-design', params),
    cmdInverseDesign: (params) => invoke('cwt:phase5:inverse-design:command', params),
    noiseRobust: (params) => invoke('cwt:phase5:noise-robust', params),
    cmdNoiseRobust: (params) => invoke('cwt:phase5:noise-robust:command', params),
    betaSweep: (params) => invoke('cwt:phase5:beta-sweep', params),
    couplingTuner: (params) => invoke('cwt:phase5:coupling-tuner', params),
  },
  artifacts: {
    list: (payload) => invoke('cwt:artifacts:list', payload),
  },
  registry: {
    query: (payload) => invoke('cwt:registry:query', payload),
  },
  recipes: {
    list: () => invoke('cwt:recipes:list'),
    save: (payload) => invoke('cwt:recipes:save', payload),
    run: (payload) => invoke('cwt:recipes:run', payload),
    export: (payload) => invoke('cwt:recipes:export', payload),
  },
  ping: (payload: string) => invoke('cwt:ping', payload),
  version: () => invoke('cwt:get-version'),
} satisfies RendererIpc;

contextBridge.exposeInMainWorld('CWT', Object.freeze(api));

export type { RendererIpc as PreloadApi } from '../renderer/types/ipc';
