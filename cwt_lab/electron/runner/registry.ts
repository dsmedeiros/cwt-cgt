import Database from 'better-sqlite3';

export type RunRecord = {
  id: string;
  createdAt: number;
  status: 'pending' | 'running' | 'complete' | 'failed';
};

export const openRegistry = (dbPath: string): Database => {
  const db = new Database(dbPath);
  db.pragma('journal_mode = WAL');
  db.exec(`
    CREATE TABLE IF NOT EXISTS runs (
      id TEXT PRIMARY KEY,
      created_at INTEGER NOT NULL,
      status TEXT NOT NULL
    );
  `);
  return db;
};

export const upsertRun = (db: Database, run: RunRecord) => {
  const stmt = db.prepare(
    'INSERT INTO runs (id, created_at, status) VALUES (@id, @createdAt, @status) ' +
      'ON CONFLICT(id) DO UPDATE SET status=excluded.status',
  );
  stmt.run({
    id: run.id,
    createdAt: run.createdAt,
    status: run.status,
  });
};

export const fetchRuns = (db: Database): RunRecord[] => {
  const stmt = db.prepare('SELECT id, created_at as createdAt, status FROM runs ORDER BY created_at DESC');
  return stmt.all() as RunRecord[];
};
