import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'node',
    environmentMatchGlobs: [
      ['renderer/**/*.test.{ts,tsx}', 'jsdom'],
    ],
    globals: true,
    setupFiles: './vitest.setup.ts',
    include: [
      'electron/**/*.test.ts',
      'shared/**/*.test.ts',
      'renderer/**/*.test.{ts,tsx}',
    ],
    restoreMocks: true,
    clearMocks: true,
  },
});
