import { describe, expect, it } from 'vitest';

import { sanitizeStoredConfig } from '../env';

type StoredConfig = Parameters<typeof sanitizeStoredConfig>[0];

describe('sanitizeStoredConfig', () => {
  it('clears stored Windows paths when running on non-Windows platforms', () => {
    const config: StoredConfig = {
      pythonPath: 'D:\\repos\\cwt-cgt\\.venv\\Scripts\\python.exe',
      strategy: 'module',
      phase2MetricsRoot: null,
    };
    const sanitized = sanitizeStoredConfig(config, 'linux');
    expect(sanitized).toEqual({ pythonPath: null, strategy: null, phase2MetricsRoot: null });
  });

  it('retains non-Windows paths on non-Windows platforms', () => {
    const config: StoredConfig = {
      pythonPath: '/opt/cwt/.venv/bin/python',
      strategy: 'module',
      phase2MetricsRoot: null,
    };
    const sanitized = sanitizeStoredConfig(config, 'linux');
    expect(sanitized).toEqual({
      pythonPath: '/opt/cwt/.venv/bin/python',
      strategy: 'module',
      phase2MetricsRoot: null,
    });
  });

  it('clears stored POSIX-style paths when running on Windows', () => {
    const config: StoredConfig = {
      pythonPath: '/opt/cwt/.venv/bin/python',
      strategy: 'module',
      phase2MetricsRoot: null,
    };
    const sanitized = sanitizeStoredConfig(config, 'win32');
    expect(sanitized).toEqual({ pythonPath: null, strategy: null, phase2MetricsRoot: null });
  });

  it('retains Windows paths on Windows platforms', () => {
    const config: StoredConfig = {
      pythonPath: 'C:\\cwt\\.venv\\Scripts\\python.exe',
      strategy: 'module',
      phase2MetricsRoot: null,
    };
    const sanitized = sanitizeStoredConfig(config, 'win32');
    expect(sanitized).toEqual({
      pythonPath: 'C:\\cwt\\.venv\\Scripts\\python.exe',
      strategy: 'module',
      phase2MetricsRoot: null,
    });
  });

  it('trims whitespace around stored paths', () => {
    const config: StoredConfig = {
      pythonPath: '  /opt/cwt/.venv/bin/python  ',
      strategy: 'module',
      phase2MetricsRoot: null,
    };
    const sanitized = sanitizeStoredConfig(config, 'linux');
    expect(sanitized).toEqual({
      pythonPath: '/opt/cwt/.venv/bin/python',
      strategy: 'module',
      phase2MetricsRoot: null,
    });
  });

  it('converts quoted Windows paths when running on Windows', () => {
    const config: StoredConfig = {
      pythonPath: '"C:\\cwt\\.venv\\Scripts\\python.exe"',
      strategy: 'module',
      phase2MetricsRoot: null,
    };
    const sanitized = sanitizeStoredConfig(config, 'win32');
    expect(sanitized).toEqual({
      pythonPath: 'C:\\cwt\\.venv\\Scripts\\python.exe',
      strategy: 'module',
      phase2MetricsRoot: null,
    });
  });

  it('accepts Windows paths that use forward slashes', () => {
    const config: StoredConfig = {
      pythonPath: 'C:/cwt/.venv/Scripts/python.exe',
      strategy: 'module',
      phase2MetricsRoot: null,
    };
    const sanitized = sanitizeStoredConfig(config, 'win32');
    expect(sanitized).toEqual({
      pythonPath: 'C:\\cwt\\.venv\\Scripts\\python.exe',
      strategy: 'module',
      phase2MetricsRoot: null,
    });
  });
});
