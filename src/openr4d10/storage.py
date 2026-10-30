"""Versioned local SQLite state without credential storage."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import sqlite3
from typing import Any


SCHEMA_VERSION = 1
_SECRET_KEY = re.compile(
    r"(^|[._-])(password|passwd|token|secret|api[_-]?key|private[_-]?key)($|[._-])",
    re.IGNORECASE,
)

MIGRATION_1 = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS service_state (
    service_id TEXT PRIMARY KEY,
    enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
    config_state TEXT NOT NULL DEFAULT 'not_configured'
        CHECK (config_state IN ('not_configured', 'ready', 'error')),
    last_error TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stations (
    id INTEGER PRIMARY KEY,
    service_id TEXT NOT NULL,
    name TEXT NOT NULL,
    stream_url TEXT NOT NULL,
    favorite INTEGER NOT NULL DEFAULT 0 CHECK (favorite IN (0, 1)),
    position INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY,
    service_id TEXT NOT NULL,
    external_id TEXT NOT NULL,
    name TEXT NOT NULL,
    favorite INTEGER NOT NULL DEFAULT 0 CHECK (favorite IN (0, 1)),
    metadata_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(service_id, external_id)
);

CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY,
    service_id TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    title TEXT,
    duration_seconds REAL,
    size_bytes INTEGER,
    checksum TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recordings (
    id INTEGER PRIMARY KEY,
    service_id TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    source_label TEXT,
    started_at TEXT NOT NULL,
    duration_seconds REAL,
    codec TEXT,
    size_bytes INTEGER,
    checksum TEXT
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class StateStore:
    """Own the non-secret application database and its schema migrations."""

    def __init__(self, path: Path) -> None:
        if not path.is_absolute():
            raise ValueError("state database path must be absolute")
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
        self.connection = sqlite3.connect(path, timeout=5, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        try:
            path.chmod(0o600)
        except OSError:
            pass
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self._migrate()

    def _migrate(self) -> None:
        current = int(self.connection.execute("PRAGMA user_version").fetchone()[0])
        if current > SCHEMA_VERSION:
            raise RuntimeError(
                f"state database schema {current} is newer than supported {SCHEMA_VERSION}"
            )
        if current < 1:
            with self.transaction():
                self.connection.executescript(MIGRATION_1)
                self.connection.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (1, _now()),
                )
                self.connection.execute("PRAGMA user_version = 1")

    @contextmanager
    def transaction(self) -> Iterator[None]:
        try:
            yield
        except Exception:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    def set_setting(self, key: str, value: Any) -> None:
        if not key or _SECRET_KEY.search(key):
            raise ValueError("secret-like settings are forbidden in the application database")
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        with self.transaction():
            self.connection.execute(
                """
                INSERT INTO settings(key, value_json, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (key, encoded, _now()),
            )

    def get_setting(self, key: str, default: Any = None) -> Any:
        row = self.connection.execute(
            "SELECT value_json FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return default if row is None else json.loads(row["value_json"])

    def ensure_services(self, service_ids: tuple[str, ...]) -> None:
        now = _now()
        with self.transaction():
            self.connection.executemany(
                """
                INSERT OR IGNORE INTO service_state(
                    service_id, enabled, config_state, updated_at
                ) VALUES (?, 0, 'not_configured', ?)
                """,
                ((service_id, now) for service_id in service_ids),
            )

    def service_states(self) -> dict[str, dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT service_id, enabled, config_state, last_error, updated_at
            FROM service_state ORDER BY service_id
            """
        )
        return {
            str(row["service_id"]): {
                "enabled": bool(row["enabled"]),
                "config_state": str(row["config_state"]),
                "last_error": row["last_error"],
                "updated_at": str(row["updated_at"]),
            }
            for row in rows
        }

    def close(self) -> None:
        self.connection.close()
