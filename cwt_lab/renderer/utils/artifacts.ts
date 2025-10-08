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
  graph: string;
  files: Partial<Record<Phase1HeatmapKind, string>>;
};

const normalizeRelativePath = (value: string) => value.replace(/\\/g, '/');

const HEATMAP_PATTERN = /\/(heatmaps\.png|omega_heatmap\.png)$/;

const HEATMAP_KINDS: readonly Phase1HeatmapKind[] = ['heatmaps', 'omega_heatmap'];

export const phase1HeatmapKinds = HEATMAP_KINDS;

export const findPhase1HeatmapGroups = (artifacts: ArtifactFile[]): Phase1HeatmapGroup[] => {
  const groups = new Map<string, Phase1HeatmapGroup>();

  for (const artifact of artifacts) {
    if (artifact.type !== 'file') {
      continue;
    }
    const normalized = normalizeRelativePath(artifact.relativePath);
    if (!HEATMAP_PATTERN.test(normalized)) {
      continue;
    }

    const segments = normalized.split('/');
    if (segments.length < 2) {
      continue;
    }

    const fileName = segments[segments.length - 1] ?? '';
    const graph = segments[segments.length - 2];
    if (!graph) {
      continue;
    }

    const group = groups.get(graph) ?? { graph, files: {} };

    if (fileName === 'heatmaps.png') {
      group.files.heatmaps = artifact.relativePath;
    } else if (fileName === 'omega_heatmap.png') {
      group.files.omega_heatmap = artifact.relativePath;
    }

    groups.set(graph, group);
  }

  return Array.from(groups.values()).sort((a, b) => a.graph.localeCompare(b.graph));
};

export const formatPhase1GraphLabel = (graph: string): string => {
  const sanitized = graph.replace(/[_\-]+/g, ' ').replace(/\s+/g, ' ').trim();
  return sanitized.length > 0 ? sanitized : 'Unnamed graph';
};
