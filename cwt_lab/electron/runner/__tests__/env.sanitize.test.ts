import { describe, expect, it } from 'vitest';

import { sanitizeStoredConfig } from '../env';

describe('sanitizeStoredConfig', () => {
  it('clears stored Windows paths when running on non-Windows platforms', () => {
    const config = { pythonPath: 'D:\\\\repos\\\\cwt-cgt\\\\.venv\\\\Scripts\\\\python.exe', strategy: 'module' };
    const sanitized = sanitizeStoredConfig(config, 'linux');
    expect(sanitized).toEqual({ pythonPath: null, strategy: null });
  });

  it('retains non-Windows paths on non-Windows platforms', () => {
    const config = { pythonPath: '/opt/cwt/.venv/bin/python', strategy: 'module' };
    const sanitized = sanitizeStoredConfig(config, 'linux');
    expect(sanitized).toEqual({ pythonPath: '/opt/cwt/.venv/bin/python', strategy: 'module' });
  });

  it('clears stored POSIX-style paths when running on Windows', () => {
    const config = { pythonPath: '/opt/cwt/.venv/bin/python', strategy: 'module' };
    const sanitized = sanitizeStoredConfig(config, 'win32');
    expect(sanitized).toEqual({ pythonPath: null, strategy: null });
  });

  it('retains Windows paths on Windows platforms', () => {
    const config = { pythonPath: 'C:\\\\cwt\\\\.venv\\\\Scripts\\\\python.exe', strategy: 'module' };
    const sanitized = sanitizeStoredConfig(config, 'win32');
    expect(sanitized).toEqual({ pythonPath: 'C:\\\\cwt\\\\.venv\\\\Scripts\\\\python.exe', strategy: 'module' });
  });

  it('trims whitespace around stored paths', () => {
    const config = { pythonPath: '  /opt/cwt/.venv/bin/python  ', strategy: 'module' };
    const sanitized = sanitizeStoredConfig(config, 'linux');
    expect(sanitized).toEqual({ pythonPath: '/opt/cwt/.venv/bin/python', strategy: 'module' });
  });
});
