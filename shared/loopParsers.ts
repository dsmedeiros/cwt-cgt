export interface LoopStdoutMetrics {
  /**
   * Generic calibration score emitted by legacy runners.
   * Maintained for compatibility with the calibrator state machine.
   */
  value?: number;
  fsP95?: number;
  phi?: number;
  R?: number;
  overlapMin?: number;
  kappaChange?: number;
  guardExceeded?: boolean;
  phiFlipError?: number;
  rFlipError?: number;
}

const DECIMAL_SEPARATOR = /,/g;

const FS_P95_REGEX = /FS p95=([0-9.,]+)\s+rad/;
const PHI_REGEX = /Φ=([+-]?[0-9.,]+)/;
const R_REGEX = /R=([+-]?[0-9.,]+)/;
const KAPPA_CHANGE_REGEX = /κ₁ scale change:\s*([0-9.,]+)%/;
const GUARD_EXCEEDED_REGEX = /guard_exceeded=(True|False)/;
const FLIP_ERROR_REGEX = /flip error: area=([0-9.,]+)%\s+phi=([0-9.,]+)%/;
const OVERLAP_MIN_REGEX = /overlap.*?([0-9.,]+)/;

function parseLocaleNumber(value: string | undefined): number | undefined {
  if (value == null) {
    return undefined;
  }
  const normalized = value.replace(DECIMAL_SEPARATOR, '.');
  const parsed = Number.parseFloat(normalized);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function extractNumber(regex: RegExp, text: string): number | undefined {
  const match = regex.exec(text);
  return match ? parseLocaleNumber(match[1]) : undefined;
}

export function parseLoopStdout(txt: string): LoopStdoutMetrics {
  const metrics: LoopStdoutMetrics = {};

  metrics.fsP95 = extractNumber(FS_P95_REGEX, txt);
  metrics.phi = extractNumber(PHI_REGEX, txt);
  metrics.R = extractNumber(R_REGEX, txt);
  metrics.kappaChange = extractNumber(KAPPA_CHANGE_REGEX, txt);
  metrics.overlapMin = extractNumber(OVERLAP_MIN_REGEX, txt);

  const guardMatch = GUARD_EXCEEDED_REGEX.exec(txt);
  if (guardMatch) {
    metrics.guardExceeded = guardMatch[1] === 'True';
  }

  const flipMatch = FLIP_ERROR_REGEX.exec(txt);
  if (flipMatch) {
    metrics.rFlipError = parseLocaleNumber(flipMatch[1]);
    metrics.phiFlipError = parseLocaleNumber(flipMatch[2]);
  }

  return metrics;
}
