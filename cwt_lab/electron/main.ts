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

  const cspDirectives: Record<string, Set<string>> = {
    'default-src': new Set(["'self'"]),
    'script-src': new Set(["'self'", "'unsafe-inline'"]),
    'style-src': new Set(["'self'", "'unsafe-inline'"]),
    'img-src': new Set(["'self'", 'data:']),
    'font-src': new Set(["'self'"]),
    'connect-src': new Set(["'self'"]),
    'object-src': new Set(["'none'"]),
    'base-uri': new Set(["'self'"]),
    'frame-ancestors': new Set(["'none'"]),
  };

  if (process.env['ELECTRON_RENDERER_URL']) {
    cspDirectives['script-src'].add("'unsafe-inline'");
    cspDirectives['connect-src'].add('ws://localhost:*');
  }

  const contentSecurityPolicy = Object.entries(cspDirectives)
    .map(([key, value]) => `${key} ${Array.from(value).join(' ')}`)
    .join('; ');

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
