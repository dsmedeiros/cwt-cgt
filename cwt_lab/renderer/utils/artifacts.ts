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
