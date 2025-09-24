import { z } from 'zod';

export const extentSchema = z
  .number({ invalid_type_error: 'Extent must be a number.' })
  .refine((value) => value > 0 && value <= 1, {
    message: 'Extent must be greater than 0 and no more than 1.',
  });

export const fsGuardSchema = z
  .number({ invalid_type_error: 'FS guard must be a number.' })
  .refine((value) => value > 0.01 && value <= 0.5, {
    message: 'FS guard must be between 0.01 and 0.5.',
  });

export const stepsSchema = z
  .number({ invalid_type_error: 'Steps must be a number.' })
  .int('Steps must be a whole number.')
  .min(16, { message: 'Steps must be at least 16.' })
  .max(2000, { message: 'Steps cannot exceed 2000.' });

export const percentileSchema = z
  .number({ invalid_type_error: 'Percentile must be a number.' })
  .int('Percentile must be a whole number.')
  .min(1, { message: 'Percentile must be at least 1.' })
  .max(99, { message: 'Percentile must be no more than 99.' });

const AXES_PHASE1 = ['rho', 'tau', 'zeta', 'sigma', 'omega'] as const;
const AXES_PHASE3 = ['tau', 'zeta', 'rho', 'sigma', 'kappa'] as const;
const AXES_PHASE4 = ['rho', 'tau', 'zeta', 'zeta_phase', 'kappa'] as const;

export type Phase = 'phase1' | 'phase3' | 'phase4';

type AxisScope = {
  phase: Phase;
  axes: readonly string[];
};

const AXIS_SCOPES: AxisScope[] = [
  { phase: 'phase1', axes: AXES_PHASE1 },
  { phase: 'phase3', axes: AXES_PHASE3 },
  { phase: 'phase4', axes: AXES_PHASE4 },
];

export const axisSchema = (phase: Phase) => {
  const scope = AXIS_SCOPES.find((candidate) => candidate.phase === phase);
  const whitelist = scope?.axes ?? [];
  return z
    .string({ invalid_type_error: 'Axis name must be text.' })
    .min(1, { message: 'Axis name is required.' })
    .refine((value) => whitelist.includes(value), {
      message: `Axis name must be one of: ${whitelist.join(', ')}.`,
    });
};

export type ValidationResult<T> =
  | { ok: true; value: T }
  | { ok: false; message: string };

type Coerceable = string | number | undefined | null;

const coerceNumber = (value: Coerceable): number | null => {
  if (value === '' || value === null || value === undefined) {
    return null;
  }
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const extractIssueMessage = (issues: z.ZodIssue[]): string => {
  if (!issues.length) {
    return 'Invalid value.';
  }
  const [first] = issues;
  return first.message || 'Invalid value.';
};

const wrapNumberValidation = (schema: z.ZodType<number, z.ZodTypeDef, number>) =>
  (value: Coerceable): ValidationResult<number> => {
    const numeric = coerceNumber(value);
    if (numeric === null) {
      return { ok: false, message: 'Enter a numeric value.' };
    }
    const result = schema.safeParse(numeric);
    if (result.success) {
      return { ok: true, value: result.data };
    }
    return { ok: false, message: extractIssueMessage(result.error.issues) };
  };

export const validateExtent = wrapNumberValidation(extentSchema);
export const validateFsGuard = wrapNumberValidation(fsGuardSchema);
export const validateSteps = wrapNumberValidation(stepsSchema);
export const validatePercentile = wrapNumberValidation(percentileSchema);

export const validateAxis = (phase: Phase, value: string): ValidationResult<string> => {
  const schema = axisSchema(phase);
  const result = schema.safeParse(value);
  if (result.success) {
    return { ok: true, value: result.data };
  }
  return { ok: false, message: extractIssueMessage(result.error.issues) };
};

export const formatValidationMessage = (result: ValidationResult<unknown>): string | undefined =>
  result.ok ? undefined : result.message;
