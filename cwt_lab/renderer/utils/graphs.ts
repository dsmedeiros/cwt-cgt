import type { GraphFactoryDescriptor } from '../types/ipc';

export const GRAPH_ID_ALIASES: Record<string, readonly string[]> = {
  ring3: ['ring-3', 'ring_3', 'ring3_hetero', 'ring3-hetero', 'ring3-h'],
  random_regular: [
    'random-regular',
    'randomregular',
    'random_regular_digraph',
    'random-regular-digraph',
  ],
  small_world: ['small-world', 'smallworld', 'small world'],
  scale_free: ['scale-free', 'scalefree', 'scale free'],
  watts_strogatz_p001: [
    'watts-strogatz-p001',
    'watts strogatz p001',
    'wattsstrogatzp001',
  ],
  watts_strogatz_p010: [
    'watts-strogatz-p010',
    'watts strogatz p010',
    'wattsstrogatzp010',
  ],
  watts_strogatz_p0: [
    'watts-strogatz-p0',
    'watts strogatz p0',
    'wattsstrogatzp0',
  ],
  periodic_lattice: ['periodic-lattice', 'periodiclattice', 'periodic lattice'],
  erdos_renyi: ['erdos-renyi', 'erdosrenyi', 'erdos renyi'],
  barabasi_albert: ['barabasi-albert', 'barabasialbert', 'barabasi albert'],
};

type GraphDescriptorLike =
  | string
  | GraphFactoryDescriptor
  | { id?: unknown; graph?: unknown; label?: unknown; name?: unknown }
  | null
  | undefined;

const matchesGraphAlias = (value: string, alias: string) => {
  const normalizedValue = value.toLowerCase();
  const normalizedAlias = alias.toLowerCase();
  if (!normalizedAlias) {
    return false;
  }

  const sanitizedValue = normalizedValue.replace(/[^a-z0-9]/g, '');
  const sanitizedAlias = normalizedAlias.replace(/[^a-z0-9]/g, '');

  if (
    sanitizedAlias &&
    (sanitizedValue === sanitizedAlias ||
      sanitizedValue.startsWith(sanitizedAlias) ||
      sanitizedValue.endsWith(sanitizedAlias) ||
      (sanitizedAlias.length >= 4 && sanitizedValue.includes(sanitizedAlias)))
  ) {
    return true;
  }

  const valueTokens = normalizedValue.split(/[^a-z0-9]+/).filter(Boolean);
  const aliasTokens = normalizedAlias.split(/[^a-z0-9]+/).filter(Boolean);
  if (aliasTokens.length === 0) {
    return false;
  }

  let startIndex = 0;
  for (const token of aliasTokens) {
    const index = valueTokens.indexOf(token, startIndex);
    if (index === -1) {
      return false;
    }
    startIndex = index + 1;
  }

  return true;
};

const candidateStringsFromGraph = (value: GraphDescriptorLike): string[] => {
  if (typeof value === 'string') {
    return [value];
  }

  if (!value || typeof value !== 'object') {
    return [];
  }

  const descriptor = value as GraphFactoryDescriptor & {
    id?: unknown;
    graph?: unknown;
    label?: unknown;
    name?: unknown;
  };

  const candidates: string[] = [];
  const register = (entry: unknown) => {
    if (typeof entry === 'string') {
      const trimmed = entry.trim();
      if (trimmed.length > 0) {
        candidates.push(trimmed);
      }
    }
  };

  register(descriptor.identifier);
  register(descriptor.id);
  register(descriptor.graph);
  register(descriptor.label);
  register(descriptor.name);

  return candidates;
};

export const canonicalGraphId = (value: GraphDescriptorLike): string | null => {
  const candidates = candidateStringsFromGraph(value);

  for (const candidate of candidates) {
    const trimmed = candidate.trim();
    if (!trimmed) {
      continue;
    }

    for (const [graphId, aliases] of Object.entries(GRAPH_ID_ALIASES)) {
      const aliasList = [graphId, ...aliases];
      if (aliasList.some((alias) => matchesGraphAlias(trimmed, alias))) {
        return graphId;
      }
    }
  }

  return null;
};
