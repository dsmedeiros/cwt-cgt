import type {
  IpcEnvelope,
  Phase2CorrelatePayload,
  Phase2CorrelateResult,
  RegistryRunRecord,
  RunDiagnosticsBundle,
} from './types/ipc';

const unwrap = async <T>(
  promise: Promise<IpcEnvelope<T>> | undefined,
  unavailableMessage: string,
): Promise<T> => {
  if (!promise) {
    throw new Error(unavailableMessage);
  }
  const response = await promise;
  if (!response.ok) {
    throw new Error(response.error ?? 'IPC call failed');
  }
  return response.data;
};

export const phase2 = {
  async correlate(payload: Phase2CorrelatePayload): Promise<Phase2CorrelateResult> {
    return unwrap(
      window?.CWT?.phase2?.correlate?.(payload),
      'Phase-2 correlation IPC is unavailable',
    );
  },
  async saveSnapshot(payload: unknown): Promise<{ path: string }> {
    return unwrap(
      window?.CWT?.phase2?.saveSnapshot?.(payload),
      'Phase-2 snapshot IPC is unavailable',
    );
  },
};

export const runs = {
  async listRecent(limit = 20): Promise<RegistryRunRecord[]> {
    return unwrap(
      window?.CWT?.registry?.query?.({ limit }),
      'Run registry IPC is unavailable',
    );
  },
  async collectDiagnostics(runId: string): Promise<RunDiagnosticsBundle> {
    return unwrap(
      window?.CWT?.run?.collectDiagnostics?.({ runId }),
      'Diagnostics IPC is unavailable',
    );
  },
};

export type { Phase2CorrelatePayload, Phase2CorrelateResult } from './types/ipc';
