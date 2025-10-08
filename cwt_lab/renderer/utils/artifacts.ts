import type { ArtifactFile } from '../types/ipc';

export type ArtifactNode = {
  name: string;
  path: string;
  type: 'file' | 'directory';
  relativePath: string;
  children?: ArtifactNode[];
};

export const sanitizeArtifactNodes = (value: unknown): ArtifactNode[] => {
  if (!Array.isArray(value)) {
    return [];
  }

  const result: ArtifactNode[] = [];

  for (const entry of value) {
    if (!entry || typeof entry !== 'object') {
      continue;
    }

    const node = entry as Partial<ArtifactNode>;
    if (
      typeof node.name !== 'string' ||
      typeof node.path !== 'string' ||
      typeof node.relativePath !== 'string' ||
      (node.type !== 'file' && node.type !== 'directory')
    ) {
      continue;
    }

    const children =
      node.type === 'directory' ? sanitizeArtifactNodes(node.children) : undefined;

    result.push({
      name: node.name,
      path: node.path,
      type: node.type,
      relativePath: node.relativePath,
      ...(children ? { children } : {}),
    });
  }

  return result;
};

const GUID_PATTERN =
  /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;

export const isGuidLike = (value: string) => GUID_PATTERN.test(value.trim());

export const findArtifactNodeByName = (
  nodes: ArtifactNode[],
  name: string,
): ArtifactNode | null => {
  for (const node of nodes) {
    if (node.name === name) {
      return node;
    }
    if (node.type === 'directory' && node.children?.length) {
      const match = findArtifactNodeByName(node.children, name);
      if (match) {
        return match;
      }
    }
  }
  return null;
};

export const joinArtifactPath = (base: string, leaf: string): string => {
  if (!base) {
    return leaf;
  }
  const trimmed = base.replace(/[\\/]+$/, '');
  if (/^\\\\/.test(trimmed) || (trimmed.includes('\\') && !trimmed.includes('/'))) {
    return `${trimmed}\\${leaf}`;
  }
  if (trimmed === '') {
    return `/${leaf}`;
  }
  return `${trimmed}/${leaf}`;
};

export type Phase1HeatmapKind = 'heatmaps' | 'omega_heatmap';

export type Phase1HeatmapGroup = {
  substrate: string;
  graph: string;
  files: Partial<Record<Phase1HeatmapKind, string>>;
};

const normalizeRelativePath = (value: string) => value.replace(/\\/g, '/');

const HEATMAP_PATTERN = /\/(heatmaps\.png|omega_heatmap\.png)$/;

const SUBSTRATE_MARKERS = new Set(['substrate', 'substrates']);

const formatPhase1Label = (value: string, fallback: string): string => {
  const sanitized = value.replace(/[_\-]+/g, ' ').replace(/\s+/g, ' ').trim();
  return sanitized.length > 0 ? sanitized : fallback;
};

const HEATMAP_KINDS: readonly Phase1HeatmapKind[] = ['heatmaps', 'omega_heatmap'];

export const phase1HeatmapKinds = HEATMAP_KINDS;

const resolveHeatmapMetadata = (
  relativePath: string,
): { normalizedPath: string; graph: string; substrate: string; kind: Phase1HeatmapKind } | null => {
  const normalizedPath = normalizeRelativePath(relativePath);
  if (!HEATMAP_PATTERN.test(normalizedPath)) {
    return null;
  }

  const segments = normalizedPath.split('/').filter(Boolean);
  if (segments.length < 2) {
    return null;
  }

  const fileName = segments[segments.length - 1];
  const graph = segments[segments.length - 2] ?? '';
  if (!graph) {
    return null;
  }

  let kind: Phase1HeatmapKind | null = null;
  if (fileName === 'heatmaps.png') {
    kind = 'heatmaps';
  } else if (fileName === 'omega_heatmap.png') {
    kind = 'omega_heatmap';
  }
  if (!kind) {
    return null;
  }

  let substrate = graph;
  for (let index = segments.length - 3; index >= 0; index -= 1) {
    const segment = segments[index];
    if (!segment) {
      continue;
    }
    if (SUBSTRATE_MARKERS.has(segment)) {
      const candidate = segments[index + 1];
      if (candidate) {
        substrate = candidate;
      }
      break;
    }
  }

  return { normalizedPath, graph, substrate, kind };
};

export const findPhase1HeatmapGroups = (artifacts: ArtifactFile[]): Phase1HeatmapGroup[] => {
  const groups = new Map<string, Phase1HeatmapGroup>();

  for (const artifact of artifacts) {
    if (artifact.type !== 'file') {
      continue;
    }

    const metadata = resolveHeatmapMetadata(artifact.relativePath);
    if (!metadata) {
      continue;
    }

    const key = `${metadata.substrate}::${metadata.graph}`;
    const group = groups.get(key) ?? {
      substrate: metadata.substrate,
      graph: metadata.graph,
      files: {},
    };

    group.files[metadata.kind] = metadata.normalizedPath;
    groups.set(key, group);
  }

  return Array.from(groups.values()).sort((a, b) => {
    const substrateDiff = a.substrate.localeCompare(b.substrate);
    if (substrateDiff !== 0) {
      return substrateDiff;
    }
    return a.graph.localeCompare(b.graph);
  });
};

export const formatPhase1GraphLabel = (graph: string): string =>
  formatPhase1Label(graph, 'Unnamed graph');

export const formatPhase1SubstrateLabel = (substrate: string): string =>
  formatPhase1Label(substrate, 'Unnamed substrate');
