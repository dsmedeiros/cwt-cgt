import React, {
  CSSProperties,
  ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import path from 'path';
import { useEnvStore } from '../store/envSlice';

type ArtifactType = 'file' | 'directory';

interface ArtifactNode {
  path: string;
  type: ArtifactType;
  size: number;
  mtime: number;
  children?: ArtifactNode[];
}

interface StatusMessage {
  message: string;
  tone: 'info' | 'error';
}

interface ElectronBridge {
  artifacts?: Record<string, unknown>;
  files?: Record<string, unknown>;
  shell?: { showItemInFolder?: (target: string) => void };
  clipboard?: { writeText?: (value: string) => void };
  ipcRenderer?: {
    invoke?: (channel: string, ...args: unknown[]) => Promise<unknown>;
    on?: (channel: string, listener: (...args: unknown[]) => void) => void;
    off?: (channel: string, listener: (...args: unknown[]) => void) => void;
    removeListener?: (channel: string, listener: (...args: unknown[]) => void) => void;
  };
}

declare global {
  interface Window {
    electron?: ElectronBridge;
    require?: (module: string) => unknown;
  }
}

function getElectron(): ElectronBridge | undefined {
  if (typeof window === 'undefined') {
    return undefined;
  }
  return window.electron;
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

function subscribeToIpc(channel: string, handler: () => void): () => void {
  const electron = getElectron();
  const ipc = electron?.ipcRenderer;
  if (!ipc?.on) {
    return () => undefined;
  }

  const listener = () => {
    handler();
  };

  ipc.on(channel, listener);

  return () => {
    if (ipc.off) {
      ipc.off(channel, listener);
    } else if (ipc.removeListener) {
      ipc.removeListener(channel, listener);
    }
  };
}

async function callBridgeFunction(paths: string[][], channel: string, ...args: unknown[]): Promise<unknown> {
  const electron = getElectron();

  if (electron) {
    for (const segments of paths) {
      let target: unknown = electron;
      for (const segment of segments) {
        if (!target || typeof target !== 'object') {
          target = undefined;
          break;
        }
        target = (target as Record<string, unknown>)[segment];
      }
      if (typeof target === 'function') {
        return await Promise.resolve((target as (...inner: unknown[]) => unknown)(...args));
      }
    }
  }

  const ipc = electron?.ipcRenderer;
  if (ipc?.invoke) {
    return ipc.invoke(channel, ...args);
  }

  throw new Error('Electron bridge is not available.');
}

let fsModulePromise: Promise<typeof import('fs')> | null = null;

async function getFsModule(): Promise<typeof import('fs') | null> {
  if (!fsModulePromise) {
    try {
      fsModulePromise = import('fs');
    } catch (error) {
      fsModulePromise = Promise.resolve(null as unknown as typeof import('fs'));
    }
  }

  try {
    const module = await fsModulePromise;
    return module;
  } catch (error) {
    return null;
  }
}

async function readTextFile(filePath: string): Promise<string | null> {
  const fsModule = await getFsModule();
  if (fsModule?.promises?.readFile) {
    try {
      return await fsModule.promises.readFile(filePath, 'utf8');
    } catch (error) {
      // Continue to IPC fallback.
    }
  }

  try {
    const result = await callBridgeFunction([
      ['files', 'readText'],
      ['files', 'readFile'],
    ], 'files.readText', filePath);

    if (typeof result === 'string') {
      return result;
    }

    if (result instanceof Uint8Array) {
      try {
        return new TextDecoder().decode(result);
      } catch (error) {
        return null;
      }
    }
  } catch (error) {
    return null;
  }

  return null;
}

async function readBinaryFile(filePath: string): Promise<Uint8Array | null> {
  const fsModule = await getFsModule();
  if (fsModule?.promises?.readFile) {
    try {
      const buffer = await fsModule.promises.readFile(filePath);
      return buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
    } catch (error) {
      // Continue to IPC fallback.
    }
  }

  try {
    const result = await callBridgeFunction([
      ['files', 'readBinary'],
      ['files', 'readBuffer'],
      ['files', 'readFile'],
    ], 'files.readBinary', filePath);

    if (result instanceof Uint8Array) {
      return result;
    }

    if (typeof Buffer !== 'undefined' && typeof Buffer.from === 'function' && typeof result === 'string') {
      return new Uint8Array(Buffer.from(result, 'base64'));
    }
  } catch (error) {
    return null;
  }

  return null;
}

function normalizeArtifactNode(raw: unknown): ArtifactNode | null {
  if (!raw || typeof raw !== 'object') {
    return null;
  }

  const source = raw as Record<string, unknown>;
  const pathValue = typeof source.path === 'string' ? source.path : '';
  const typeValue = source.type === 'directory' ? 'directory' : source.type === 'file' ? 'file' : null;
  if (!typeValue) {
    return null;
  }

  const sizeValue = typeof source.size === 'number' && Number.isFinite(source.size) ? source.size : 0;
  const mtimeValue = typeof source.mtime === 'number' && Number.isFinite(source.mtime) ? source.mtime : 0;

  let children: ArtifactNode[] | undefined;
  if (Array.isArray(source.children)) {
    const normalizedChildren: ArtifactNode[] = [];
    for (const child of source.children) {
      const normalizedChild = normalizeArtifactNode(child);
      if (normalizedChild) {
        normalizedChildren.push(normalizedChild);
      }
    }
    if (normalizedChildren.length) {
      children = normalizedChildren;
    }
  }

  return {
    path: pathValue,
    type: typeValue,
    size: sizeValue,
    mtime: mtimeValue,
    ...(children ? { children } : {}),
  };
}

function normalizeArtifactList(raw: unknown): ArtifactNode[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  const nodes: ArtifactNode[] = [];
  for (const item of raw) {
    const node = normalizeArtifactNode(item);
    if (node) {
      nodes.push(node);
    }
  }
  return nodes;
}

async function listArtifacts(under?: string): Promise<ArtifactNode[]> {
  const response = await callBridgeFunction([
    ['artifacts', 'list'],
  ], 'artifacts.list', under);

  if (!Array.isArray(response)) {
    throw new Error('Artifacts bridge returned unexpected data.');
  }

  return normalizeArtifactList(response);
}

function findNodeByPath(nodes: ArtifactNode[], targetPath: string): ArtifactNode | null {
  for (const node of nodes) {
    if (node.path === targetPath) {
      return node;
    }
    if (node.children) {
      const match = findNodeByPath(node.children, targetPath);
      if (match) {
        return match;
      }
    }
  }
  return null;
}

function resolveArtifactPath(relativePath: string, repoRoot: string | null): string | null {
  const base = repoRoot ?? (typeof process !== 'undefined' && typeof process.cwd === 'function' ? process.cwd() : null);
  if (!base) {
    return null;
  }
  if (!relativePath) {
    return path.join(base, 'artifacts');
  }
  return path.join(base, 'artifacts', relativePath);
}

function bufferToBase64(data: Uint8Array): string {
  if (typeof Buffer !== 'undefined') {
    return Buffer.from(data).toString('base64');
  }
  let binary = '';
  for (const byte of data) {
    binary += String.fromCharCode(byte);
  }
  return typeof btoa === 'function' ? btoa(binary) : binary;
}

const CSV_PREVIEW_ROW_LIMIT = 200;
const CSV_PAGE_SIZE = 25;

interface CsvPreviewResult {
  header: string[];
  rows: string[][];
  truncated: boolean;
}

function parseCsvPreview(text: string, maxRows: number): CsvPreviewResult {
  const rows: string[][] = [];
  let currentField = '';
  let currentRow: string[] = [];
  let inQuotes = false;
  let truncated = false;

  const commitField = () => {
    currentRow.push(currentField);
    currentField = '';
  };

  const commitRow = () => {
    commitField();
    rows.push(currentRow);
    currentRow = [];
  };

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];

    if (char === '"') {
      if (inQuotes && text[index + 1] === '"') {
        currentField += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (!inQuotes && (char === '\n' || char === '\r')) {
      if (char === '\r' && text[index + 1] === '\n') {
        index += 1;
      }
      commitRow();
      if (rows.length >= maxRows + 1) {
        truncated = true;
        break;
      }
      continue;
    }

    if (!inQuotes && char === ',') {
      commitField();
      continue;
    }

    currentField += char;
  }

  if (currentField.length > 0 || currentRow.length > 0) {
    commitRow();
  }

  while (rows.length > 0) {
    const last = rows[rows.length - 1];
    if (last.every((value) => value === '')) {
      rows.pop();
    } else {
      break;
    }
  }

  const header = rows.length ? rows[0] : [];
  const dataRows = rows.length > 1 ? rows.slice(1) : [];
  const limitedRows = dataRows.slice(0, maxRows);
  if (!truncated && dataRows.length > maxRows) {
    truncated = true;
  }

  return {
    header,
    rows: limitedRows,
    truncated,
  };
}

function formatFileSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) {
    return '—';
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const units = ['KB', 'MB', 'GB', 'TB'];
  let size = bytes / 1024;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`;
}

function formatTimestampMs(timestamp: number): string {
  if (!Number.isFinite(timestamp) || timestamp <= 0) {
    return '—';
  }
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return '—';
  }
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
}

function getNodeDisplayName(node: ArtifactNode): string {
  if (!node.path) {
    return 'artifacts';
  }
  const segments = node.path.split('/');
  const name = segments[segments.length - 1];
  return name || node.path;
}

type PreviewState =
  | { status: 'idle' }
  | { status: 'loading'; path: string }
  | { status: 'error'; path: string; message: string }
  | { status: 'image'; path: string; src: string }
  | { status: 'json'; path: string; pretty: string }
  | { status: 'csv'; path: string; header: string[]; rows: string[][]; truncated: boolean }
  | { status: 'unsupported'; path: string };

const containerStyle: CSSProperties = {
  display: 'flex',
  gap: '1rem',
  alignItems: 'stretch',
  width: '100%',
  minHeight: '400px',
};

const treePaneStyle: CSSProperties = {
  flex: '0 0 320px',
  border: '1px solid var(--panel-border, #ccc)',
  borderRadius: '6px',
  padding: '0.75rem',
  overflowY: 'auto',
  background: 'var(--panel-background, #fff)',
};

const previewPaneStyle: CSSProperties = {
  flex: '1 1 auto',
  border: '1px solid var(--panel-border, #ccc)',
  borderRadius: '6px',
  padding: '0.75rem',
  overflow: 'auto',
  background: 'var(--panel-background, #fff)',
};

function ArtifactTreeNode({
  node,
  depth,
  expanded,
  onToggle,
  onSelect,
  selectedPath,
}: {
  node: ArtifactNode;
  depth: number;
  expanded: Set<string>;
  onToggle: (path: string) => void;
  onSelect: (target: ArtifactNode) => void;
  selectedPath: string | null;
}): JSX.Element {
  const isDirectory = node.type === 'directory';
  const isExpanded = isDirectory ? expanded.has(node.path) : false;
  const isSelected = selectedPath === node.path;
  const displayName = getNodeDisplayName(node);

  const handleSelect = useCallback(() => {
    onSelect(node);
  }, [node, onSelect]);

  const toggleButton = isDirectory ? (
    <button
      type="button"
      className="artifact-tree-toggle"
      onClick={() => onToggle(node.path)}
      aria-label={isExpanded ? 'Collapse directory' : 'Expand directory'}
    >
      {isExpanded ? '▾' : '▸'}
    </button>
  ) : (
    <span className="artifact-tree-spacer">•</span>
  );

  return (
    <div className="artifact-tree-node" key={node.path}>
      <div
        className={`artifact-tree-row${isSelected ? ' selected' : ''}`}
        style={{ paddingLeft: `${depth * 1.25}rem` }}
      >
        {toggleButton}
        <button
          type="button"
          className={`artifact-tree-label ${isDirectory ? 'directory' : 'file'}`}
          onClick={handleSelect}
        >
          {displayName || (isDirectory ? 'Directory' : 'File')}
        </button>
      </div>
      {isDirectory && isExpanded && node.children && node.children.length ? (
        <div className="artifact-tree-children">
          {node.children.map((child) => (
            <ArtifactTreeNode
              key={child.path}
              node={child}
              depth={depth + 1}
              expanded={expanded}
              onToggle={onToggle}
              onSelect={onSelect}
              selectedPath={selectedPath}
            />
          ))}
        </div>
      ) : null}
      {isDirectory && isExpanded && (!node.children || node.children.length === 0) ? (
        <div className="artifact-tree-empty" style={{ paddingLeft: `${(depth + 1) * 1.25}rem` }}>
          <em>Empty</em>
        </div>
      ) : null}
    </div>
  );
}

function ArtifactTree({
  nodes,
  expanded,
  onToggle,
  onSelect,
  selectedPath,
}: {
  nodes: ArtifactNode[];
  expanded: Set<string>;
  onToggle: (path: string) => void;
  onSelect: (target: ArtifactNode) => void;
  selectedPath: string | null;
}): JSX.Element {
  if (!nodes.length) {
    return <p className="artifact-tree-empty-state">No artifacts yet.</p>;
  }

  return (
    <div className="artifact-tree">
      {nodes.map((node) => (
        <ArtifactTreeNode
          key={node.path}
          node={node}
          depth={0}
          expanded={expanded}
          onToggle={onToggle}
          onSelect={onSelect}
          selectedPath={selectedPath}
        />
      ))}
    </div>
  );
}

function CsvPreview({
  header,
  rows,
  truncated,
  page,
  onPageChange,
}: {
  header: string[];
  rows: string[][];
  truncated: boolean;
  page: number;
  onPageChange: (page: number) => void;
}): JSX.Element {
  const totalRows = rows.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / CSV_PAGE_SIZE));
  const currentPage = Math.min(Math.max(page, 0), totalPages - 1);
  const startIndex = currentPage * CSV_PAGE_SIZE;
  const pageRows = rows.slice(startIndex, startIndex + CSV_PAGE_SIZE);

  return (
    <div className="artifact-preview-csv">
      <div className="artifact-preview-table-container">
        <table className="artifact-preview-table">
          <thead>
            <tr>
              {header.map((cell, index) => (
                <th key={`header-${index}`}>{cell}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageRows.length ? (
              pageRows.map((row, rowIndex) => (
                <tr key={`row-${startIndex + rowIndex}`}>
                  {row.map((cell, cellIndex) => (
                    <td key={`cell-${startIndex + rowIndex}-${cellIndex}`}>{cell}</td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={header.length || 1} className="artifact-preview-empty">
                  No rows to display.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="artifact-preview-pagination">
        <button
          type="button"
          onClick={() => onPageChange(Math.max(currentPage - 1, 0))}
          disabled={currentPage === 0}
        >
          Previous
        </button>
        <span>
          Page {currentPage + 1} of {totalPages}
        </span>
        <button
          type="button"
          onClick={() => onPageChange(Math.min(currentPage + 1, totalPages - 1))}
          disabled={currentPage + 1 >= totalPages}
        >
          Next
        </button>
      </div>
      {truncated ? (
        <p className="artifact-preview-note">
          Showing the first {CSV_PREVIEW_ROW_LIMIT} rows. Download the file to view the remainder.
        </p>
      ) : null}
    </div>
  );
}

function ArtifactPreview({
  preview,
  csvPage,
  setCsvPage,
}: {
  preview: PreviewState;
  csvPage: number;
  setCsvPage: (page: number) => void;
}): JSX.Element {
  if (preview.status === 'idle') {
    return <p>Select a file to preview.</p>;
  }
  if (preview.status === 'loading') {
    return <p>Loading preview…</p>;
  }
  if (preview.status === 'error') {
    return <p className="artifact-preview-error">Failed to load preview: {preview.message}</p>;
  }
  if (preview.status === 'image') {
    return <img src={preview.src} alt={preview.path} className="artifact-preview-image" />;
  }
  if (preview.status === 'json') {
    return (
      <pre className="artifact-preview-json">
        <code>{preview.pretty}</code>
      </pre>
    );
  }
  if (preview.status === 'csv') {
    return <CsvPreview header={preview.header} rows={preview.rows} truncated={preview.truncated} page={csvPage} onPageChange={setCsvPage} />;
  }
  if (preview.status === 'unsupported') {
    return <p>No preview available for this file type.</p>;
  }
  return <p>Preview unavailable.</p>;
}

function ArtifactDetails({
  node,
}: {
  node: ArtifactNode | null;
}): JSX.Element {
  if (!node) {
    return <p>Select an artifact to view its details.</p>;
  }

  const isDirectory = node.type === 'directory';

  return (
    <div className="artifact-details">
      <h3>{node.path || 'artifacts'}</h3>
      <dl>
        <div>
          <dt>Type</dt>
          <dd>{isDirectory ? 'Directory' : 'File'}</dd>
        </div>
        <div>
          <dt>Size</dt>
          <dd>{isDirectory ? '—' : formatFileSize(node.size)}</dd>
        </div>
        <div>
          <dt>Last Modified</dt>
          <dd>{formatTimestampMs(node.mtime)}</dd>
        </div>
      </dl>
    </div>
  );
}

const ArtifactBrowser = (): JSX.Element => {
  const repoRoot = useEnvStore((state) => state.repoRoot ?? null);
  const [nodes, setNodes] = useState<ArtifactNode[]>([]);
  const [isLoadingTree, setIsLoadingTree] = useState<boolean>(false);
  const [treeError, setTreeError] = useState<string | null>(null);
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(() => new Set());
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [previewState, setPreviewState] = useState<PreviewState>({ status: 'idle' });
  const [csvPage, setCsvPage] = useState(0);
  const [statusMessage, setStatusMessage] = useState<StatusMessage | null>(null);
  const mountedRef = useRef(true);
  const selectedPathRef = useRef<string | null>(null);

  useEffect(() => {
    selectedPathRef.current = selectedPath;
  }, [selectedPath]);

  useEffect(() => {
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const refreshArtifacts = useCallback(async () => {
    setIsLoadingTree(true);
    setTreeError(null);
    try {
      const list = await listArtifacts();
      if (!mountedRef.current) {
        return;
      }
      setNodes(list);
      const currentSelection = selectedPathRef.current;
      if (currentSelection) {
        const existing = findNodeByPath(list, currentSelection);
        if (!existing) {
          setSelectedPath(null);
          setPreviewState({ status: 'idle' });
        }
      }
    } catch (error) {
      if (!mountedRef.current) {
        return;
      }
      setNodes([]);
      setTreeError(formatError(error));
    } finally {
      if (mountedRef.current) {
        setIsLoadingTree(false);
      }
    }
  }, []);

  useEffect(() => {
    refreshArtifacts();
    const unsubscribe = subscribeToIpc('artifacts.updated', () => {
      refreshArtifacts();
    });
    return () => {
      unsubscribe();
    };
  }, [refreshArtifacts]);

  const artifactMap = useMemo(() => {
    const map = new Map<string, ArtifactNode>();
    const stack = [...nodes];
    while (stack.length) {
      const node = stack.pop();
      if (!node) {
        continue;
      }
      map.set(node.path, node);
      if (node.children) {
        for (const child of node.children) {
          stack.push(child);
        }
      }
    }
    return map;
  }, [nodes]);

  const selectedNode = selectedPath ? artifactMap.get(selectedPath) ?? null : null;

  useEffect(() => {
    if (!selectedNode || selectedNode.type !== 'file') {
      setPreviewState({ status: 'idle' });
      setCsvPage(0);
      return;
    }

    let cancelled = false;
    const loadPreview = async () => {
      setPreviewState({ status: 'loading', path: selectedNode.path });
      setCsvPage(0);

      const absolutePath = resolveArtifactPath(selectedNode.path, repoRoot);
      if (!absolutePath) {
        if (!cancelled) {
          setPreviewState({
            status: 'error',
            path: selectedNode.path,
            message: 'Unable to resolve artifact path.',
          });
        }
        return;
      }

      try {
        const lowered = selectedNode.path.toLowerCase();
        if (lowered.endsWith('.png')) {
          const binary = await readBinaryFile(absolutePath);
          if (!binary) {
            throw new Error('Unable to read image file.');
          }
          const base64 = bufferToBase64(binary);
          if (!cancelled) {
            setPreviewState({ status: 'image', path: selectedNode.path, src: `data:image/png;base64,${base64}` });
          }
          return;
        }

        if (lowered.endsWith('.json')) {
          const text = await readTextFile(absolutePath);
          if (!text) {
            throw new Error('Unable to read JSON file.');
          }
          let pretty: string;
          try {
            const parsed = JSON.parse(text);
            pretty = JSON.stringify(parsed, null, 2);
          } catch (parseError) {
            pretty = text;
          }
          if (!cancelled) {
            setPreviewState({ status: 'json', path: selectedNode.path, pretty });
          }
          return;
        }

        if (lowered.endsWith('.csv')) {
          const text = await readTextFile(absolutePath);
          if (!text) {
            throw new Error('Unable to read CSV file.');
          }
          const preview = parseCsvPreview(text, CSV_PREVIEW_ROW_LIMIT);
          if (!cancelled) {
            setPreviewState({
              status: 'csv',
              path: selectedNode.path,
              header: preview.header,
              rows: preview.rows,
              truncated: preview.truncated,
            });
          }
          return;
        }

        if (!cancelled) {
          setPreviewState({ status: 'unsupported', path: selectedNode.path });
        }
      } catch (error) {
        if (!cancelled) {
          setPreviewState({
            status: 'error',
            path: selectedNode.path,
            message: formatError(error),
          });
        }
      }
    };

    loadPreview();

    return () => {
      cancelled = true;
    };
  }, [selectedNode, repoRoot]);

  useEffect(() => {
    if (!statusMessage) {
      return;
    }
    const handle = setTimeout(() => {
      setStatusMessage(null);
    }, 3000);
    return () => {
      clearTimeout(handle);
    };
  }, [statusMessage]);

  const handleToggle = useCallback((targetPath: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(targetPath)) {
        next.delete(targetPath);
      } else {
        next.add(targetPath);
      }
      return next;
    });
  }, []);

  const handleSelect = useCallback((node: ArtifactNode) => {
    setSelectedPath(node.path);
    if (node.type === 'directory') {
      setPreviewState({ status: 'idle' });
    }
    if (node.path) {
      const segments = node.path.split('/');
      if (segments.length > 1) {
        setExpandedPaths((prev) => {
          const next = new Set(prev);
          for (let index = 1; index < segments.length; index += 1) {
            const prefix = segments.slice(0, index).join('/');
            next.add(prefix);
          }
          return next;
        });
      }
    }
  }, []);

  const handleReveal = useCallback(async () => {
    const node = selectedPath ? artifactMap.get(selectedPath) ?? null : null;
    if (!node) {
      return;
    }
    const absolutePath = resolveArtifactPath(node.path, repoRoot);
    if (!absolutePath) {
      setStatusMessage({ message: 'Unable to determine artifact path.', tone: 'error' });
      return;
    }
    try {
      await callBridgeFunction([
        ['shell', 'showItemInFolder'],
      ], 'shell.showItemInFolder', absolutePath);
    } catch (error) {
      setStatusMessage({ message: `Failed to reveal artifact: ${formatError(error)}`, tone: 'error' });
    }
  }, [artifactMap, repoRoot, selectedPath]);

  const handleCopyPath = useCallback(async () => {
    const node = selectedPath ? artifactMap.get(selectedPath) ?? null : null;
    if (!node) {
      return;
    }
    const absolutePath = resolveArtifactPath(node.path, repoRoot);
    const target = absolutePath ?? node.path;
    if (!target) {
      setStatusMessage({ message: 'Nothing to copy.', tone: 'error' });
      return;
    }

    try {
      if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(target);
        setStatusMessage({ message: 'Copied path to clipboard.', tone: 'info' });
        return;
      }
      const electron = getElectron();
      if (electron?.clipboard?.writeText) {
        electron.clipboard.writeText(target);
        setStatusMessage({ message: 'Copied path to clipboard.', tone: 'info' });
        return;
      }
      await callBridgeFunction([
        ['clipboard', 'writeText'],
      ], 'clipboard.writeText', target);
      setStatusMessage({ message: 'Copied path to clipboard.', tone: 'info' });
    } catch (error) {
      setStatusMessage({ message: `Failed to copy path: ${formatError(error)}`, tone: 'error' });
    }
  }, [artifactMap, repoRoot, selectedPath]);

  const controls: ReactNode = (
    <div className="artifact-preview-actions">
      <button type="button" onClick={handleReveal} disabled={!selectedNode}>
        Reveal in File Browser
      </button>
      <button type="button" onClick={handleCopyPath} disabled={!selectedNode}>
        Copy Path
      </button>
      <button type="button" onClick={refreshArtifacts} disabled={isLoadingTree}>
        Refresh
      </button>
    </div>
  );

  return (
    <div className="artifact-browser" style={containerStyle}>
      <div className="artifact-browser-tree" style={treePaneStyle}>
        <h2>Artifacts</h2>
        {isLoadingTree ? <p>Loading artifacts…</p> : null}
        {treeError ? <p className="artifact-tree-error">Failed to load artifacts: {treeError}</p> : null}
        {!isLoadingTree ? (
          <ArtifactTree
            nodes={nodes}
            expanded={expandedPaths}
            onToggle={handleToggle}
            onSelect={handleSelect}
            selectedPath={selectedPath}
          />
        ) : null}
      </div>
      <div className="artifact-browser-preview" style={previewPaneStyle}>
        <ArtifactDetails node={selectedNode} />
        {controls}
        {statusMessage ? (
          <p className={`artifact-status ${statusMessage.tone === 'error' ? 'error' : 'info'}`}>
            {statusMessage.message}
          </p>
        ) : null}
        <ArtifactPreview preview={previewState} csvPage={csvPage} setCsvPage={setCsvPage} />
      </div>
    </div>
  );
};

export default ArtifactBrowser;
