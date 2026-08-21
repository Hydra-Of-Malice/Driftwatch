"""SQLite persistence layer.

Deliberately thin: a schema, a per-thread connection, dict rows, JSON columns,
and an append-only audit writer. Swapping to Postgres is a driver change, not a
redesign — the schema is vanilla SQL.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  vertical TEXT NOT NULL,
  url TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  schedule_minutes INTEGER NOT NULL DEFAULT 60,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS contracts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT NOT NULL REFERENCES sources(id),
  version INTEGER NOT NULL,
  spec TEXT NOT NULL,               -- JSON ContractSpec
  created_from TEXT NOT NULL,       -- "seed" | "auto_draft" | "manual"
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scrapers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT NOT NULL REFERENCES sources(id),
  collector_id TEXT NOT NULL,
  active_version INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'active',
  view_url TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT NOT NULL REFERENCES sources(id),
  scraper_version INTEGER NOT NULL DEFAULT 1,
  state TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  credits_spent INTEGER NOT NULL DEFAULT 0,
  confidence REAL,
  error TEXT
);
CREATE TABLE IF NOT EXISTS snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER REFERENCES runs(id),
  source_id TEXT NOT NULL REFERENCES sources(id),
  content_hash TEXT NOT NULL,
  payload TEXT NOT NULL,            -- JSON extraction
  verdict TEXT,                     -- JSON Verdict
  quarantined INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drift_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT NOT NULL REFERENCES sources(id),
  run_id INTEGER REFERENCES runs(id),
  drift_class INTEGER NOT NULL,
  severity TEXT NOT NULL,           -- "info" | "warning" | "critical"
  confidence REAL NOT NULL,
  summary TEXT NOT NULL,
  field_changes TEXT NOT NULL DEFAULT '[]',   -- JSON [FieldChange]
  before_snapshot_id INTEGER,
  after_snapshot_id INTEGER,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS heal_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT NOT NULL REFERENCES sources(id),
  trigger_event_id INTEGER REFERENCES drift_events(id),
  composed_prompt TEXT NOT NULL,
  preview_payload TEXT,             -- JSON preview_result
  verification TEXT,                -- JSON Verdict of the preview
  decision TEXT,                    -- "auto_approved" | "auto_rejected" | "human_approved" | "human_rejected" | NULL (pending review)
  decided_by TEXT,                  -- "machine" | "human"
  version_before INTEGER,
  version_after INTEGER,
  status TEXT NOT NULL,             -- "verifying" | "review" | "approved" | "rejected"
  mttr_seconds REAL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS impact_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  drift_event_id INTEGER NOT NULL REFERENCES drift_events(id),
  affected TEXT NOT NULL,           -- JSON [{file,line,snippet,entity}]
  cost_delta_monthly REAL,
  migration_note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  drift_event_id INTEGER NOT NULL REFERENCES drift_events(id),
  channel TEXT NOT NULL,            -- "in_app" | "slack"
  payload TEXT NOT NULL,
  delivered_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor TEXT NOT NULL,              -- "machine" | "human" | "scheduler"
  action TEXT NOT NULL,
  refs TEXT NOT NULL DEFAULT '{}',
  payload TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);
"""

_local = threading.local()
_db_path: str | None = None
_init_lock = threading.Lock()


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def configure(db_path: str) -> None:
    """Point the module at a database file and ensure the schema exists."""
    global _db_path
    _db_path = db_path
    with _init_lock:
        conn = _connect()
        conn.executescript(SCHEMA)
        conn.commit()


def _connect() -> sqlite3.Connection:
    if _db_path is None:
        raise RuntimeError("db.configure(db_path) must be called before use")
    conn: sqlite3.Connection | None = getattr(_local, "conn", None)
    if conn is None or getattr(_local, "path", None) != _db_path:
        conn = sqlite3.connect(_db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
        _local.path = _db_path
    return conn


def j(value: Any) -> str:
    return json.dumps(value, default=str, ensure_ascii=False)


def uj(value: str | None) -> Any:
    return json.loads(value) if value else None


def insert(table: str, row: dict[str, Any]) -> int:
    conn = _connect()
    cols = ", ".join(row)
    marks = ", ".join("?" for _ in row)
    cur = conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", list(row.values()))
    conn.commit()
    return int(cur.lastrowid or 0)


def update(table: str, row_id: int | str, fields: dict[str, Any], id_col: str = "id") -> None:
    conn = _connect()
    sets = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE {table} SET {sets} WHERE {id_col} = ?", [*fields.values(), row_id])
    conn.commit()


def query(sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    conn = _connect()
    return [dict(r) for r in conn.execute(sql, list(params)).fetchall()]


def query_one(sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def audit(actor: str, action: str, refs: dict[str, Any] | None = None, payload: dict[str, Any] | None = None) -> int:
    """Append-only ledger write. Everything of consequence goes through here."""
    return insert(
        "audit_events",
        {
            "actor": actor,
            "action": action,
            "refs": j(refs or {}),
            "payload": j(payload or {}),
            "created_at": now_iso(),
        },
    )
