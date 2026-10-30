"""Versioned local SQLite state without credential storage."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import sqlite3
import threading
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
        self._lock = threading.RLock()
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
        with self._lock:
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
        with self._lock:
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
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT service_id, enabled, config_state, last_error, updated_at
                FROM service_state ORDER BY service_id
                """
            ).fetchall()
            return {
                str(row["service_id"]): {
                    "enabled": bool(row["enabled"]),
                    "config_state": str(row["config_state"]),
                    "last_error": row["last_error"],
                    "updated_at": str(row["updated_at"]),
                }
                for row in rows
            }

    def add_station(self, service_id: str, name: str, stream_url: str) -> int:
        if not service_id or not name.strip() or len(name) > 160:
            raise ValueError("station service and name are required")
        with self.transaction():
            cursor = self.connection.execute(
                """
                INSERT INTO stations(service_id, name, stream_url, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (service_id, name.strip(), stream_url, _now()),
            )
            return int(cursor.lastrowid)

    def delete_station(self, station_id: int) -> bool:
        with self.transaction():
            cursor = self.connection.execute(
                "DELETE FROM stations WHERE id = ?", (station_id,)
            )
            return cursor.rowcount == 1

    def station(self, station_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self.connection.execute(
                "SELECT id, service_id, name, stream_url, favorite, position FROM stations WHERE id = ?",
                (station_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def stations(self, service_id: str = "webradio") -> list[dict[str, Any]]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT id, service_id, name, stream_url, favorite, position
                FROM stations WHERE service_id = ?
                ORDER BY favorite DESC, position, name COLLATE NOCASE LIMIT 500
                """,
                (service_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def upsert_media(self, service_id: str, path: Path, size_bytes: int) -> None:
        with self.transaction():
            self.connection.execute(
                """
                INSERT INTO media(service_id, path, title, size_bytes, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    service_id = excluded.service_id,
                    title = excluded.title,
                    size_bytes = excluded.size_bytes
                """,
                (service_id, str(path), path.stem[:240], size_bytes, _now()),
            )

    def media_items(self, service_id: str = "local_media") -> list[dict[str, Any]]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT id, service_id, path, title, duration_seconds, size_bytes
                FROM media WHERE service_id = ?
                ORDER BY title COLLATE NOCASE LIMIT 2000
                """,
                (service_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def media_item(self, media_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self.connection.execute(
                """
                SELECT id, service_id, path, title, duration_seconds, size_bytes
                FROM media WHERE id = ?
                """,
                (media_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def remove_missing_media(self, service_id: str, present_paths: set[str]) -> int:
        """Remove stale library rows without constructing a dynamic SQL query."""
        removed = 0
        with self.transaction():
            rows = self.connection.execute(
                "SELECT id, path FROM media WHERE service_id = ?", (service_id,)
            ).fetchall()
            for row in rows:
                if str(row["path"]) not in present_paths:
                    cursor = self.connection.execute(
                        "DELETE FROM media WHERE id = ?", (row["id"],)
                    )
                    removed += cursor.rowcount
        return removed

    def close(self) -> None:
        with self._lock:
            self.connection.close()
