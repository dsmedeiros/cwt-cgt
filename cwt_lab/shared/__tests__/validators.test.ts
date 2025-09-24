import { describe, expect, it } from 'vitest';

import {
  formatValidationMessage,
  validateAxis,
  validateExtent,
  validateFsGuard,
  validatePercentile,
  validateSteps,
} from '../validators';

describe('validators', () => {
  it('validates numeric ranges for extent and FS guard', () => {
    expect(validateExtent(0.5)).toEqual({ ok: true, value: 0.5 });
    expect(validateExtent(0)).toEqual({ ok: false, message: 'Extent must be greater than 0 and no more than 1.' });

    expect(validateFsGuard(0.1)).toEqual({ ok: true, value: 0.1 });
    expect(validateFsGuard('bad')).toEqual({ ok: false, message: 'Enter a numeric value.' });
  });

  it('requires integer ranges for steps and percentile', () => {
    expect(validateSteps(128)).toEqual({ ok: true, value: 128 });
    expect(validateSteps(4.5)).toEqual({ ok: false, message: 'Steps must be a whole number.' });

    expect(validatePercentile(25)).toEqual({ ok: true, value: 25 });
    expect(validatePercentile(120)).toEqual({ ok: false, message: 'Percentile must be no more than 99.' });
  });

  it('validates allowed axes per phase', () => {
    expect(validateAxis('phase1', 'rho')).toEqual({ ok: true, value: 'rho' });
    expect(validateAxis('phase3', 'omega')).toEqual({ ok: false, message: 'Axis name must be one of: tau, zeta, rho, sigma, kappa.' });
  });

  it('formats validation messages for UI consumption', () => {
    expect(formatValidationMessage({ ok: true, value: 1 })).toBeUndefined();
    expect(formatValidationMessage({ ok: false, message: 'Nope' })).toBe('Nope');
  });
});
