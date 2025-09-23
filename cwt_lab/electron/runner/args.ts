export const buildArgsFromParams = (params: Record<string, unknown> | undefined): string[] => {
  if (!params) {
    return [];
  }

  const args: string[] = [];
  const toKebab = (key: string) =>
    key
      .replace(/([a-z0-9])([A-Z])/g, '$1-$2')
      .replace(/_/g, '-')
      .toLowerCase();

  for (const [rawKey, value] of Object.entries(params)) {
    if (value === undefined || value === null) {
      continue;
    }

    const flag = `--${toKebab(rawKey)}`;
    if (Array.isArray(value)) {
      const serialized = value.map((item) =>
        typeof item === 'object' && item !== null ? JSON.stringify(item) : String(item),
      );
      args.push(flag, ...serialized);
    } else if (typeof value === 'boolean') {
      const isNegatedFlag = /^no[A-Z_]/i.test(rawKey);
      if (isNegatedFlag) {
        if (value) {
          args.push(flag);
        }
      } else {
        args.push(flag, value ? 'true' : 'false');
      }
    } else if (typeof value === 'object') {
      args.push(flag, JSON.stringify(value));
    } else {
      args.push(flag, String(value));
    }
  }

  return args;
};
