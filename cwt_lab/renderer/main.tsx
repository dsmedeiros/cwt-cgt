import React from 'react';
import { createRoot } from 'react-dom/client';

import App from './App';
import { ThemeProvider } from './theme';
import { I18nProvider } from './i18n';
import './styles.css';

const container = document.getElementById('root');

if (!container) {
  throw new Error('Unable to find root element for renderer');
}

const root = createRoot(container);
root.render(
  <React.StrictMode>
    <I18nProvider>
      <ThemeProvider>
        <App />
      </ThemeProvider>
    </I18nProvider>
  </React.StrictMode>,
);
