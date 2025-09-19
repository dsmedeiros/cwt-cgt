import { contextBridge, ipcRenderer } from 'electron';

type Api = {
  shutdown: () => Promise<void>;
};

const api: Api = {
  shutdown: () => ipcRenderer.invoke('cwt:shutdown'),
};

contextBridge.exposeInMainWorld('cwtLab', api);

export type PreloadApi = typeof api;
