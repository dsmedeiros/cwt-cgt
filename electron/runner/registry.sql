CREATE TABLE IF NOT EXISTS runs(
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  phase TEXT,
  experiment TEXT,
  status TEXT,
  command TEXT,
  workdir TEXT,
  seed INTEGER,
  params_json TEXT,
  axes TEXT,
  graph TEXT,
  center_json TEXT,
  metrics_json TEXT,
  stdout_path TEXT,
  stderr_path TEXT,
  artifacts_path TEXT,
  python_exe TEXT,
  git_sha TEXT,
  pip_freeze_path TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at DESC);
