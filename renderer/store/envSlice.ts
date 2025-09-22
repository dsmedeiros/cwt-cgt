import { create } from 'zustand';

type ImportStatus = 'unknown' | 'checking' | 'ok' | 'error';

export interface PythonCandidate {
  path: string;
  displayName: string;
  version: string | null;
  installed: boolean;
  hasCwtModule: boolean;
  onPythonPath: boolean;
  reason: string | null;
}

interface NormalizedEnvState {
  candidates?: PythonCandidate[];
  selectedPython?: string | null;
  moduleMode?: boolean;
  usePythonPath?: boolean;
  repoRoot?: string | null;
  importStatus?: ImportStatus;
  importMessage?: string | null;
  importError?: string | null;
  lastCheckedAt?: number | null;
}

interface ImportResult {
  status: 'ok' | 'error';
  message: string | null;
}

interface ElectronEnvBridge {
  env?: Record<string, unknown>;
  ipcRenderer?: {
    invoke?: (channel: string, ...args: unknown[]) => Promise<unknown>;
  };
}

declare global {
  interface Window {
    electron?: ElectronEnvBridge;
  }
}

function getElectron(): ElectronEnvBridge | undefined {
  if (typeof window === 'undefined') {
    return undefined;
  }
  return window.electron;
}

function normalizeBoolean(value: unknown): boolean | undefined {
  if (typeof value === 'boolean') {
    return value;
  }
  if (typeof value === 'number') {
    if (Number.isNaN(value)) {
      return undefined;
    }
    return value !== 0;
  }
  if (typeof value === 'string') {
    const lowered = value.trim().toLowerCase();
    if (['1', 'true', 'yes', 'ok', 'y', 't'].includes(lowered)) {
      return true;
    }
    if (['0', 'false', 'no', 'n', 'f'].includes(lowered)) {
      return false;
    }
  }
  return undefined;
}

function normalizeString(value: unknown): string | undefined {
  if (typeof value === 'string') {
    return value;
  }
  if (value == null) {
    return undefined;
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    return String(value);
  }
  return undefined;
}

function normalizeTimestamp(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Date.parse(value);
    if (!Number.isNaN(parsed)) {
      return parsed;
    }
  }
  return undefined;
}

function formatError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'string') {
    return error;
  }
  try {
    return JSON.stringify(error);
  } catch (serializationError) {
    return String(error);
  }
}

async function callEnvBridge(method: string, ...args: unknown[]): Promise<unknown> {
  const electron = getElectron();
  const env = electron?.env;

  const direct = env && typeof env[method] === 'function' ? (env[method] as (...inner: unknown[]) => unknown) : null;
  if (direct) {
    return await Promise.resolve(direct(...args));
  }

  const channel = `env.${method}`;
  const invoke = electron?.ipcRenderer?.invoke;
  if (invoke) {
    return invoke(channel, ...args);
  }

  throw new Error('Env bridge is not available.');
}

function normalizeCandidates(raw: unknown): PythonCandidate[] {
  if (!Array.isArray(raw)) {
    return [];
  }

  const candidates: PythonCandidate[] = [];

  for (const item of raw) {
    if (!item || typeof item !== 'object') {
      continue;
    }

    const source = item as Record<string, unknown>;
    const path = normalizeString(source.path ?? source.exe ?? source.command ?? source.location);
    if (!path) {
      continue;
    }

    const displayName = normalizeString(source.displayName ?? source.name ?? source.label) ?? path;
    const version = normalizeString(source.version ?? source.pyVersion ?? source.pythonVersion ?? source.ver) ?? null;
    const installed = normalizeBoolean(source.installed ?? source.exists ?? true) ?? false;
    const hasCwtModule = normalizeBoolean(
      source.hasCwtModule ?? source.hasModule ?? source.cwtInstalled ?? source.cwt
    ) ?? false;
    const onPythonPath = normalizeBoolean(
      source.onPythonPath ?? source.hasPythonPath ?? source.pythonpath ?? source.onPath
    ) ?? false;
    const reason = normalizeString(source.reason ?? source.note ?? source.message ?? source.hint) ?? null;

    candidates.push({
      path,
      displayName,
      version,
      installed,
      hasCwtModule,
      onPythonPath,
      reason,
    });
  }

  candidates.sort((a, b) => a.displayName.localeCompare(b.displayName));

  return candidates;
}

function normalizeImportResult(raw: unknown): ImportResult {
  if (!raw) {
    return { status: 'ok', message: null };
  }

  if (typeof raw === 'string') {
    const lowered = raw.trim().toLowerCase();
    if (['ok', 'success', 'ready', 'available'].includes(lowered)) {
      return { status: 'ok', message: null };
    }
    if (['error', 'failed', 'fail'].includes(lowered)) {
      return { status: 'error', message: null };
    }
    return { status: 'error', message: raw };
  }

  if (typeof raw === 'boolean') {
    return { status: raw ? 'ok' : 'error', message: null };
  }

  if (typeof raw === 'object') {
    const source = raw as Record<string, unknown>;
    const statusString = normalizeString(source.status ?? source.state ?? source.result)?.toLowerCase();
    const okValue = normalizeBoolean(source.ok ?? source.success ?? source.ready);
    const message = normalizeString(source.message ?? source.error ?? source.reason ?? source.detail ?? source.details) ?? null;

    if (statusString === 'ok' || statusString === 'success' || statusString === 'ready') {
      return { status: 'ok', message };
    }
    if (statusString === 'error' || statusString === 'failed' || statusString === 'fail') {
      return { status: 'error', message };
    }
    if (typeof okValue === 'boolean') {
      return { status: okValue ? 'ok' : 'error', message };
    }

    if (message) {
      return { status: 'error', message };
    }
  }

  return { status: 'ok', message: null };
}

function normalizeEnvState(raw: unknown): NormalizedEnvState {
  if (!raw || typeof raw !== 'object') {
    return {};
  }

  const source = raw as Record<string, unknown>;
  const normalized: NormalizedEnvState = {};

  const hasSelectedPythonKey =
    Object.prototype.hasOwnProperty.call(source, 'selectedPython') ||
    Object.prototype.hasOwnProperty.call(source, 'pythonPath') ||
    Object.prototype.hasOwnProperty.call(source, 'python') ||
    Object.prototype.hasOwnProperty.call(source, 'exe');

  const selectedPython = normalizeString(source.selectedPython ?? source.pythonPath ?? source.python ?? source.exe);
  if (hasSelectedPythonKey) {
    normalized.selectedPython = selectedPython ?? null;
  }

  const moduleMode = normalizeBoolean(source.moduleMode ?? source.module_mode ?? source.useModuleMode);
  if (typeof moduleMode === 'boolean') {
    normalized.moduleMode = moduleMode;
  }

  const usePythonPath = normalizeBoolean(source.usePythonPath ?? source.pythonPathEnabled ?? source.appendPythonPath);
  if (typeof usePythonPath === 'boolean') {
    normalized.usePythonPath = usePythonPath;
  }

  const repoRoot = normalizeString(source.repoRoot ?? source.projectRoot ?? source.root ?? source.workspaceRoot) ?? null;
  if (repoRoot) {
    normalized.repoRoot = repoRoot;
  }

  const candidates = normalizeCandidates(
    source.pythonCandidates ?? source.candidates ?? source.options ?? source.pythons ?? source.items
  );
  if (candidates.length) {
    normalized.candidates = candidates;
  }

  const importStatusSource = source.importStatus ?? source.importResult ?? source.cwtStatus ?? source.status;
  const importNormalized = normalizeImportResult(importStatusSource);
  const importOkValue = normalizeBoolean(source.importOk ?? source.cwtOk ?? source.ok);
  const importError = normalizeString(source.importError ?? source.error ?? source.importMessage ?? source.message) ?? null;
  const importChecked = normalizeTimestamp(source.lastCheckedAt ?? source.checkedAt ?? source.importCheckedAt);

  if (typeof importOkValue === 'boolean') {
    normalized.importStatus = importOkValue ? 'ok' : 'error';
  } else if (importStatusSource !== undefined) {
    normalized.importStatus = importNormalized.status;
  }

  if (normalized.importStatus === 'ok') {
    normalized.importMessage = importNormalized.message ?? importError;
  } else if (normalized.importStatus === 'error') {
    normalized.importError = importError ?? importNormalized.message;
  } else if (importError) {
    normalized.importStatus = 'error';
    normalized.importError = importError;
  }

  if (typeof importChecked !== 'undefined') {
    normalized.lastCheckedAt = importChecked;
  }

  return normalized;
}

export interface EnvSliceState {
  pythonCandidates: PythonCandidate[];
  selectedPython: string | null;
  moduleMode: boolean;
  usePythonPath: boolean;
  repoRoot: string | null;
  importStatus: ImportStatus;
  importMessage: string | null;
  importError: string | null;
  lastCheckedAt: number | null;
  isLoadingCandidates: boolean;
  isCheckingImport: boolean;
  loadEnvState: () => Promise<void>;
  refreshCandidates: () => Promise<PythonCandidate[]>;
  usePython: (pythonPath: string) => Promise<void>;
  setModuleMode: (enabled: boolean) => Promise<void>;
  setUsePythonPath: (enabled: boolean) => Promise<void>;
  checkImport: () => Promise<void>;
}

export const useEnvStore = create<EnvSliceState>((set, get) => ({
  pythonCandidates: [],
  selectedPython: null,
  moduleMode: false,
  usePythonPath: false,
  repoRoot: null,
  importStatus: 'unknown',
  importMessage: null,
  importError: null,
  lastCheckedAt: null,
  isLoadingCandidates: false,
  isCheckingImport: false,
  async loadEnvState() {
    set((state) => ({ ...state, isLoadingCandidates: true }));

    try {
      const rawState = await callEnvBridge('getState');
      const normalized = normalizeEnvState(rawState);

      set((state) => {
        const updates: Partial<EnvSliceState> = { isLoadingCandidates: false };

        if (Object.prototype.hasOwnProperty.call(normalized, 'candidates')) {
          updates.pythonCandidates = normalized.candidates ?? [];
        }
        if (Object.prototype.hasOwnProperty.call(normalized, 'selectedPython')) {
          updates.selectedPython = normalized.selectedPython ?? null;
        }
        if (Object.prototype.hasOwnProperty.call(normalized, 'moduleMode')) {
          updates.moduleMode = normalized.moduleMode ?? false;
        }
        if (Object.prototype.hasOwnProperty.call(normalized, 'usePythonPath')) {
          updates.usePythonPath = normalized.usePythonPath ?? false;
        }
        if (Object.prototype.hasOwnProperty.call(normalized, 'repoRoot')) {
          updates.repoRoot = normalized.repoRoot ?? null;
        }
        if (Object.prototype.hasOwnProperty.call(normalized, 'importStatus')) {
          updates.importStatus = normalized.importStatus ?? 'unknown';
        }
        if (Object.prototype.hasOwnProperty.call(normalized, 'importMessage')) {
          updates.importMessage = normalized.importMessage ?? null;
        }
        if (Object.prototype.hasOwnProperty.call(normalized, 'importError')) {
          updates.importError = normalized.importError ?? null;
        }
        if (Object.prototype.hasOwnProperty.call(normalized, 'lastCheckedAt')) {
          updates.lastCheckedAt = normalized.lastCheckedAt ?? null;
        }

        return { ...state, ...updates };
      });

      if (!normalized.candidates) {
        await get().refreshCandidates();
      }
    } catch (error) {
      set((state) => ({
        ...state,
        isLoadingCandidates: false,
        importStatus: 'error',
        importError: formatError(error),
        importMessage: null,
      }));
    }
  },
  async refreshCandidates() {
    set((state) => ({ ...state, isLoadingCandidates: true }));

    try {
      const rawCandidates = await callEnvBridge('listPythonCandidates');
      const candidates = normalizeCandidates(rawCandidates);

      set((state) => ({
        ...state,
        isLoadingCandidates: false,
        pythonCandidates: candidates,
      }));

      return candidates;
    } catch (error) {
      set((state) => ({
        ...state,
        isLoadingCandidates: false,
        pythonCandidates: [],
        importStatus: 'error',
        importError: formatError(error),
        importMessage: null,
      }));
      throw error;
    }
  },
  async usePython(pythonPath: string) {
    const previous = get().selectedPython;
    set((state) => ({ ...state, selectedPython: pythonPath }));

    try {
      await callEnvBridge('usePython', pythonPath);
      await get().refreshCandidates();
      await get().checkImport();
    } catch (error) {
      set((state) => ({ ...state, selectedPython: previous ?? null }));
      set((state) => ({
        ...state,
        importStatus: 'error',
        importError: formatError(error),
        importMessage: null,
      }));
      throw error;
    }
  },
  async setModuleMode(enabled: boolean) {
    const previous = get().moduleMode;
    set((state) => ({ ...state, moduleMode: enabled }));

    try {
      await callEnvBridge('setModuleMode', enabled);
    } catch (error) {
      set((state) => ({ ...state, moduleMode: previous }));
      throw error;
    }
  },
  async setUsePythonPath(enabled: boolean) {
    const previous = get().usePythonPath;
    set((state) => ({ ...state, usePythonPath: enabled }));

    try {
      await callEnvBridge('setUsePythonPath', enabled);
    } catch (error) {
      set((state) => ({ ...state, usePythonPath: previous }));
      throw error;
    }
  },
  async checkImport() {
    const state = get();
    const { selectedPython, moduleMode, usePythonPath } = state;

    set((current) => ({
      ...current,
      isCheckingImport: true,
      importStatus: 'checking',
      importMessage: null,
      importError: null,
    }));

    try {
      const result = await callEnvBridge('checkImport', {
        pythonPath: selectedPython,
        moduleMode,
        usePythonPath,
      });

      const normalized = normalizeImportResult(result);

      set((current) => ({
        ...current,
        isCheckingImport: false,
        importStatus: normalized.status === 'ok' ? 'ok' : 'error',
        importMessage: normalized.status === 'ok' ? normalized.message ?? 'cwt import succeeded.' : null,
        importError: normalized.status === 'error' ? normalized.message ?? 'Unable to import cwt.' : null,
        lastCheckedAt: Date.now(),
      }));
    } catch (error) {
      set((current) => ({
        ...current,
        isCheckingImport: false,
        importStatus: 'error',
        importMessage: null,
        importError: formatError(error),
        lastCheckedAt: Date.now(),
      }));
    }
  },
}));
