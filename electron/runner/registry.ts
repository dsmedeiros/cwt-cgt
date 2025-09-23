import fs from 'fs';
import path from 'path';
import Database from 'better-sqlite3';
import { z } from 'zod';

const ARTIFACTS_DIR = path.join(process.cwd(), 'artifacts');
const DB_PATH = path.join(ARTIFACTS_DIR, 'registry.db');
const SCHEMA_PATH = path.join(__dirname, 'registry.sql');

const JsonValueSchema: z.ZodType<unknown> = z.lazy(() =>
  z.union([z.string(), z.number(), z.boolean(), z.null(), z.array(JsonValueSchema), z.record(JsonValueSchema)])
);

const InsertRunSchema = z.object({
  id: z.string().uuid(),
  createdAt: z.string(),
  phase: z.string().optional().nullable(),
  experiment: z.string().optional().nullable(),
  status: z.string().optional().nullable(),
  command: z.string().optional().nullable(),
  workdir: z.string().optional().nullable(),
  seed: z.number().int().optional().nullable(),
  paramsJson: JsonValueSchema.optional(),
  axes: JsonValueSchema.optional(),
  graph: JsonValueSchema.optional(),
  centerJson: JsonValueSchema.optional(),
  metricsJson: JsonValueSchema.optional(),
  stdoutPath: z.string().optional().nullable(),
  stderrPath: z.string().optional().nullable(),
  artifactsPath: z.string().optional().nullable(),
  pythonExe: z.string().optional().nullable(),
  gitSha: z.string().optional().nullable(),
  pipFreezePath: z.string().optional().nullable(),
});

const UpdateStatusSchema = z.object({
  id: z.string().uuid(),
  status: z.string(),
});

const AttachMetricsSchema = z.object({
  id: z.string().uuid(),
  metricsJson: JsonValueSchema,
});

const QueryRunsSchema = z
  .object({
    phase: z.string().optional(),
    experiment: z.string().optional(),
    limit: z.number().int().positive().optional(),
  })
  .optional();

type InsertRunInput = z.infer<typeof InsertRunSchema>;

let database: Database.Database | null = null;

function ensureArtifactsDir(): void {
  fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });
}

function getDb(): Database.Database {
  if (database) {
    return database;
  }

  ensureArtifactsDir();

  const db = new Database(DB_PATH);
  const schema = fs.readFileSync(SCHEMA_PATH, 'utf8');
  db.exec(schema);
  database = db;
  return db;
}

function serializeJson(value: unknown): string | null {
  if (typeof value === 'undefined' || value === null) {
    return null;
  }
  return JSON.stringify(value);
}

function deserializeJson<T = unknown>(value: unknown): T | null {
  if (typeof value !== 'string' || value.length === 0) {
    return null;
  }
  try {
    return JSON.parse(value) as T;
  } catch (error) {
    return null;
  }
}

function mapInsertToRow(meta: InsertRunInput): Record<string, unknown> {
  return {
    id: meta.id,
    created_at: meta.createdAt,
    phase: meta.phase ?? null,
    experiment: meta.experiment ?? null,
    status: meta.status ?? null,
    command: meta.command ?? null,
    workdir: meta.workdir ?? null,
    seed: meta.seed ?? null,
    params_json: serializeJson(meta.paramsJson),
    axes: serializeJson(meta.axes),
    graph: serializeJson(meta.graph),
    center_json: serializeJson(meta.centerJson),
    metrics_json: serializeJson(meta.metricsJson),
    stdout_path: meta.stdoutPath ?? null,
    stderr_path: meta.stderrPath ?? null,
    artifacts_path: meta.artifactsPath ?? null,
    python_exe: meta.pythonExe ?? null,
    git_sha: meta.gitSha ?? null,
    pip_freeze_path: meta.pipFreezePath ?? null,
  };
}

export function insertRun(meta: InsertRunInput): void {
  const parsed = InsertRunSchema.parse(meta);
  const db = getDb();
  const row = mapInsertToRow(parsed);

  const columns = Object.keys(row);
  const placeholders = columns.map((col) => `@${col}`).join(', ');
  const statement = db.prepare(`INSERT INTO runs(${columns.join(', ')}) VALUES(${placeholders})`);
  statement.run(row);
}

export function updateRunStatus(id: string, status: string): void {
  const parsed = UpdateStatusSchema.parse({ id, status });
  const db = getDb();
  const statement = db.prepare('UPDATE runs SET status = @status WHERE id = @id');
  statement.run(parsed);
}

export function attachMetrics(id: string, metricsJson: unknown): void {
  const parsed = AttachMetricsSchema.parse({ id, metricsJson });
  const db = getDb();
  const serialized = serializeJson(parsed.metricsJson);
  const statement = db.prepare('UPDATE runs SET metrics_json = @metrics_json WHERE id = @id');
  statement.run({ id: parsed.id, metrics_json: serialized });
}

export interface QueryRunsOptions {
  phase?: string;
  experiment?: string;
  limit?: number;
}

export interface RunRecord {
  id: string;
  createdAt: string;
  phase: string | null;
  experiment: string | null;
  status: string | null;
  command: string | null;
  workdir: string | null;
  seed: number | null;
  paramsJson: unknown;
  axes: unknown;
  graph: unknown;
  centerJson: unknown;
  metricsJson: unknown;
  stdoutPath: string | null;
  stderrPath: string | null;
  artifactsPath: string | null;
  pythonExe: string | null;
  gitSha: string | null;
  pipFreezePath: string | null;
}

export function queryRuns(options?: QueryRunsOptions): RunRecord[] {
  const parsed = QueryRunsSchema.parse(options);
  const db = getDb();

  const conditions: string[] = [];
  const params: Record<string, unknown> = {};

  if (parsed?.phase) {
    conditions.push('phase = @phase');
    params.phase = parsed.phase;
  }

  if (parsed?.experiment) {
    conditions.push('experiment = @experiment');
    params.experiment = parsed.experiment;
  }

  let query = 'SELECT * FROM runs';
  if (conditions.length > 0) {
    query += ` WHERE ${conditions.join(' AND ')}`;
  }
  query += ' ORDER BY created_at DESC';

  if (parsed?.limit) {
    query += ' LIMIT @limit';
    params.limit = parsed.limit;
  }

  const statement = db.prepare(query);
  const rows = statement.all(params);

  return rows.map((row) => ({
    id: row.id as string,
    createdAt: row.created_at as string,
    phase: (row.phase as string) ?? null,
    experiment: (row.experiment as string) ?? null,
    status: (row.status as string) ?? null,
    command: (row.command as string) ?? null,
    workdir: (row.workdir as string) ?? null,
    seed: (row.seed as number) ?? null,
    paramsJson: deserializeJson(row.params_json),
    axes: deserializeJson(row.axes),
    graph: deserializeJson(row.graph),
    centerJson: deserializeJson(row.center_json),
    metricsJson: deserializeJson(row.metrics_json),
    stdoutPath: (row.stdout_path as string) ?? null,
    stderrPath: (row.stderr_path as string) ?? null,
    artifactsPath: (row.artifacts_path as string) ?? null,
    pythonExe: (row.python_exe as string) ?? null,
    gitSha: (row.git_sha as string) ?? null,
    pipFreezePath: (row.pip_freeze_path as string) ?? null,
  }));
}
