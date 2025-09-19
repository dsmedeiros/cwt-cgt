import { ipcMain } from 'electron';

// Placeholder IPC wiring until real orchestration is implemented.
ipcMain.handle('cwt:get-version', async () => ({
  version: '0.1.0',
}));

ipcMain.handle('cwt:ping', async (_event, payload: string) => ({
  pong: payload,
}));
