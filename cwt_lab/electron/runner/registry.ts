import BetterSqlite3 from 'better-sqlite3';
import type { Database as BetterSqlite3Database } from 'better-sqlite3';

export type RunStatus = 'pending' | 'running' | 'complete' | 'failed' | 'aborted';

export type RunRecord = {
  id: string;
  createdAt: number;
  updatedAt: number;
  status: RunStatus;
  command: string;
  args: string[];
  cwd: string;
  phase: string | null;
  experiment: string | null;
  label: string | null;
  artifactsDir: string;
  metrics: Record<string, number | null> | null;
};

export type RunQuery = {
  id?: string;
  phase?: string;
  experiment?: string;
  limit?: number;
};

const ensureColumns = (db: BetterSqlite3Database) => {
  const columns = db.prepare("PRAGMA table_info(runs)").all() as Array<{ name: string }>;
  const columnNames = new Set(columns.map((column) => column.name));
  const addColumn = (definition: string) => {
    db.exec(`ALTER TABLE runs ADD COLUMN ${definition}`);
  };

  if (!columnNames.has('updated_at')) {
    addColumn('updated_at INTEGER NOT NULL DEFAULT 0');
  }
  if (!columnNames.has('command')) {
    addColumn("command TEXT NOT NULL DEFAULT ''");
  }
  if (!columnNames.has('args')) {
    addColumn("args TEXT NOT NULL DEFAULT '[]'");
  }
  if (!columnNames.has('cwd')) {
    addColumn("cwd TEXT NOT NULL DEFAULT ''");
  }
  if (!columnNames.has('phase')) {
    addColumn('phase TEXT');
  }
  if (!columnNames.has('experiment')) {
    addColumn('experiment TEXT');
  }
  if (!columnNames.has('label')) {
    addColumn('label TEXT');
  }
  if (!columnNames.has('artifacts_dir')) {
    addColumn("artifacts_dir TEXT NOT NULL DEFAULT ''");
  }
  if (!columnNames.has('metrics_json')) {
    addColumn('metrics_json TEXT');
  }
};

export const openRegistry = (dbPath: string): BetterSqlite3Database => {
  const db = new BetterSqlite3(dbPath);
  db.pragma('journal_mode = WAL');
  db.exec(`
    CREATE TABLE IF NOT EXISTS runs (
      id TEXT PRIMARY KEY,
      created_at INTEGER NOT NULL,
      updated_at INTEGER NOT NULL,
      status TEXT NOT NULL,
      command TEXT NOT NULL,
      args TEXT NOT NULL,
      cwd TEXT NOT NULL,
      phase TEXT,
      experiment TEXT,
      label TEXT,
      artifacts_dir TEXT NOT NULL,
      metrics_json TEXT
    );
  `);
  ensureColumns(db);
  return db;
};

export const upsertRun = (db: BetterSqlite3Database, run: RunRecord) => {
  const stmt = db.prepare(
    `INSERT INTO runs (id, created_at, updated_at, status, command, args, cwd, phase, experiment, label, artifacts_dir, metrics_json)
     VALUES (@id, @createdAt, @updatedAt, @status, @command, @args, @cwd, @phase, @experiment, @label, @artifactsDir, @metrics)
     ON CONFLICT(id) DO UPDATE SET
       updated_at=excluded.updated_at,
       status=excluded.status,
       command=excluded.command,
       args=excluded.args,
       cwd=excluded.cwd,
       phase=excluded.phase,
       experiment=excluded.experiment,
       label=excluded.label,
       artifacts_dir=excluded.artifacts_dir,
       metrics_json=excluded.metrics_json`,
  );
  stmt.run({
    id: run.id,
    createdAt: run.createdAt,
    updatedAt: run.updatedAt,
    status: run.status,
    command: run.command,
    args: JSON.stringify(run.args ?? []),
    cwd: run.cwd,
    phase: run.phase,
    experiment: run.experiment,
    label: run.label,
    artifactsDir: run.artifactsDir,
    metrics: run.metrics ? JSON.stringify(run.metrics) : null,
  });
};

export const fetchRuns = (db: BetterSqlite3Database, query: RunQuery): RunRecord[] => {
  const clauses: string[] = [];
  const params: Record<string, unknown> = {};

  if (query.id) {
    clauses.push('id = @id');
    params.id = query.id;
  }
  if (query.phase) {
    clauses.push('phase = @phase');
    params.phase = query.phase;
  }
  if (query.experiment) {
    clauses.push('experiment = @experiment');
    params.experiment = query.experiment;
  }

  let sql =
    'SELECT id, created_at as createdAt, updated_at as updatedAt, status, command, args, cwd, phase, experiment, label, artifacts_dir as artifactsDir, metrics_json as metricsJson FROM runs';

  if (clauses.length > 0) {
    sql += ` WHERE ${clauses.join(' AND ')}`;
  }

  sql += ' ORDER BY updated_at DESC, created_at DESC';

  if (query.limit && Number.isFinite(query.limit)) {
    sql += ' LIMIT @limit';
    params.limit = query.limit;
  }

  const stmt = db.prepare(sql);
  const rows = stmt.all(params) as Array<{
    id: string;
    createdAt: number;
    updatedAt: number;
    status: RunStatus;
    command: string;
    args: string;
    cwd: string;
    phase: string | null;
    experiment: string | null;
    label: string | null;
    artifactsDir: string;
    metricsJson: string | null;
  }>;

  return rows.map((row) => {
    let parsedArgs: string[] = [];
    try {
      parsedArgs = row.args ? (JSON.parse(row.args) as string[]) : [];
    } catch {
      parsedArgs = [];
    }

    let parsedMetrics: Record<string, number | null> | null = null;
    try {
      parsedMetrics = row.metricsJson
        ? (JSON.parse(row.metricsJson) as Record<string, number | null>)
        : null;
    } catch {
      parsedMetrics = null;
    }

    return {
      id: row.id,
      createdAt: row.createdAt,
      updatedAt: row.updatedAt,
      status: row.status,
      command: row.command,
      args: parsedArgs,
      cwd: row.cwd,
      phase: row.phase,
      experiment: row.experiment,
      label: row.label,
      artifactsDir: row.artifactsDir,
      metrics: parsedMetrics,
    } satisfies RunRecord;
  });
};

export const deleteRunRecord = (db: BetterSqlite3Database, runId: string) => {
  const stmt = db.prepare('DELETE FROM runs WHERE id = @id');
  stmt.run({ id: runId });
};
