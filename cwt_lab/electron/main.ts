import { app, BrowserWindow, ipcMain } from 'electron';
import { join } from 'node:path';

import './ipc';

const createWindow = async () => {
  const webPreferences: Electron.BrowserWindowConstructorOptions['webPreferences'] & {
    enableRemoteModule?: boolean;
  } = {
    preload: join(__dirname, '../preload/index.js'),
    contextIsolation: true,
    nodeIntegration: false,
    enableRemoteModule: false,
  };

  const mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    title: 'CWT Lab',
    webPreferences,
  });

  const contentSecurityPolicy = [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "frame-ancestors 'none'",
  ].join('; ');

  mainWindow.webContents.session.webRequest.onHeadersReceived((details, callback) => {
    const responseHeaders = {
      ...details.responseHeaders,
      'Content-Security-Policy': [contentSecurityPolicy],
    } satisfies Record<string, string | string[]>;

    callback({
      responseHeaders,
    });
  });

  mainWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));

  if (process.env['ELECTRON_RENDERER_URL']) {
    await mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL']);
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    await mainWindow.loadFile(join(__dirname, '../renderer/index.html'));
  }
};

app.whenReady().then(async () => {
  await createWindow();

  app.on('activate', async () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      await createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Placeholder shutdown wiring until runner orchestrations are implemented.
ipcMain.handle('cwt:shutdown', async () => {
  app.quit();
});
