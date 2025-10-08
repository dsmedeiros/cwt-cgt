import type {
  IpcEnvelope,
  Phase2BrowseResult,
  Phase2CorrelatePayload,
  Phase2CorrelateResult,
  Phase3BrowseHotspotsResult,
  ArtifactFile,
  RegistryRunRecord,
  RunCreateResult,
  RunDiagnosticsBundle,
  RunTailChunk,
  RunTailPayload,
  RunReadArtifactPayload,
  RunReadArtifactResult,
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
  async browseMetricsDirs(): Promise<Phase2BrowseResult> {
    return unwrap(
      window?.CWT?.phase2?.browseMetricsDirs?.(),
      'Phase-2 directory browser IPC is unavailable',
    );
  },
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

export const phase1 = {
  async map(params: Record<string, unknown>): Promise<RunCreateResult> {
    return unwrap(
      window?.CWT?.phase1?.map?.(params),
      'Phase-1 mapping IPC is unavailable',
    );
  },
};

export const phase3 = {
  async browseHotspots(): Promise<Phase3BrowseHotspotsResult> {
    return unwrap(
      window?.CWT?.phase3?.browseHotspots?.(),
      'Phase-3 hotspot browser IPC is unavailable',
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
  async openArtifacts(runId: string): Promise<ArtifactFile[]> {
    return unwrap(
      window?.CWT?.run?.openArtifacts?.({ runId }),
      'Run artifacts IPC is unavailable',
    );
  },
  async readArtifact(payload: RunReadArtifactPayload): Promise<RunReadArtifactResult> {
    return unwrap(
      window?.CWT?.run?.readArtifact?.(payload),
      'Run artifact reader IPC is unavailable',
    );
  },
  async collectDiagnostics(runId: string): Promise<RunDiagnosticsBundle> {
    return unwrap(
      window?.CWT?.run?.collectDiagnostics?.({ runId }),
      'Diagnostics IPC is unavailable',
    );
  },
  async tail(payload: RunTailPayload): Promise<RunTailChunk> {
    return unwrap(window?.CWT?.run?.tail?.(payload), 'Run tail IPC is unavailable');
  },
  async deleteRun(runId: string): Promise<{ runId: string }> {
    return unwrap(window?.CWT?.run?.delete?.({ runId }), 'Run delete IPC is unavailable');
  },
};

export type { Phase2CorrelatePayload, Phase2CorrelateResult } from './types/ipc';
