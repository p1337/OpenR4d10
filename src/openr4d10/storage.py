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


SCHEMA_VERSION = 4
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

MIGRATION_2 = """
UPDATE service_state SET enabled = 1, updated_at = CURRENT_TIMESTAMP
WHERE service_id IN ('system', 'webradio', 'local_media', 'recorder', 'rss', 'webcam');
"""

MIGRATION_3 = """
ALTER TABLE service_state ADD COLUMN position INTEGER NOT NULL DEFAULT 0;
ALTER TABLE channels ADD COLUMN position INTEGER NOT NULL DEFAULT 0;
"""

MIGRATION_4 = """
ALTER TABLE media ADD COLUMN artist TEXT;
ALTER TABLE media ADD COLUMN favorite INTEGER NOT NULL DEFAULT 0
    CHECK (favorite IN (0, 1));
ALTER TABLE media ADD COLUMN normalized_key TEXT;
ALTER TABLE media ADD COLUMN fingerprint TEXT;
ALTER TABLE media ADD COLUMN cover_file TEXT;
ALTER TABLE media ADD COLUMN review_required INTEGER NOT NULL DEFAULT 0
    CHECK (review_required IN (0, 1));
ALTER TABLE media ADD COLUMN source_kind TEXT NOT NULL DEFAULT 'local';
CREATE UNIQUE INDEX IF NOT EXISTS media_normalized_track_unique
    ON media(normalized_key) WHERE normalized_key IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS media_fingerprint_unique
    ON media(fingerprint) WHERE fingerprint IS NOT NULL;
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
            current = 1
        if current < 2:
            with self.transaction():
                self.connection.executescript(MIGRATION_2)
                self.connection.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (2, _now()),
                )
                self.connection.execute("PRAGMA user_version = 2")
            current = 2
        if current < 3:
            with self.transaction():
                self.connection.executescript(MIGRATION_3)
                self.connection.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (3, _now()),
                )
                self.connection.execute("PRAGMA user_version = 3")
            current = 3
        if current < 4:
            with self.transaction():
                self.connection.executescript(MIGRATION_4)
                self.connection.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (4, _now()),
                )
                self.connection.execute("PRAGMA user_version = 4")

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

    def ensure_services(
        self, service_ids: tuple[str, ...], default_enabled: set[str] | None = None
    ) -> None:
        now = _now()
        enabled = default_enabled or set()
        with self.transaction():
            existing_rows = self.connection.execute(
                "SELECT service_id, position FROM service_state"
            ).fetchall()
            existing = {str(row["service_id"]) for row in existing_rows}
            reset_positions = bool(existing_rows) and all(
                int(row["position"]) == 0 for row in existing_rows
            )
            next_position = (
                max((int(row["position"]) for row in existing_rows), default=-1) + 1
            )
            inserts = []
            for position, service_id in enumerate(service_ids):
                assigned = position
                if existing_rows and not reset_positions and service_id not in existing:
                    assigned = next_position
                    next_position += 1
                inserts.append((service_id, int(service_id in enabled), now, assigned))
            self.connection.executemany(
                """
                INSERT OR IGNORE INTO service_state(
                    service_id, enabled, config_state, updated_at, position
                ) VALUES (?, ?, 'not_configured', ?, ?)
                """,
                inserts,
            )
            if reset_positions:
                self.connection.executemany(
                    "UPDATE service_state SET position = ? WHERE service_id = ?",
                    ((position, service_id) for position, service_id in enumerate(service_ids)),
                )

    def set_service_enabled(self, service_id: str, enabled: bool) -> None:
        if not service_id or not isinstance(enabled, bool):
            raise ValueError("service_id and boolean enabled state are required")
        with self.transaction():
            cursor = self.connection.execute(
                "UPDATE service_state SET enabled = ?, updated_at = ? WHERE service_id = ?",
                (int(enabled), _now(), service_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("unknown service")

    def service_enabled(self, service_id: str) -> bool:
        with self._lock:
            row = self.connection.execute(
                "SELECT enabled FROM service_state WHERE service_id = ?", (service_id,)
            ).fetchone()
        if row is None:
            raise ValueError("unknown service")
        return bool(row["enabled"])

    def service_states(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT service_id, enabled, config_state, last_error, updated_at, position
                FROM service_state ORDER BY position, service_id
                """
            ).fetchall()
            return {
                str(row["service_id"]): {
                    "enabled": bool(row["enabled"]),
                    "config_state": str(row["config_state"]),
                    "last_error": row["last_error"],
                    "updated_at": str(row["updated_at"]),
                    "position": int(row["position"]),
                }
                for row in rows
            }

    def move_service(self, service_id: str, direction: int) -> bool:
        if direction not in {-1, 1}:
            raise ValueError("service direction must be -1 or 1")
        with self.transaction():
            rows = self.connection.execute(
                "SELECT service_id FROM service_state ORDER BY position, service_id"
            ).fetchall()
            ordered = [str(row["service_id"]) for row in rows]
            if service_id not in ordered:
                return False
            current = ordered.index(service_id)
            target = current + direction
            if target < 0 or target >= len(ordered):
                return False
            ordered[current], ordered[target] = ordered[target], ordered[current]
            self.connection.executemany(
                "UPDATE service_state SET position = ?, updated_at = ? WHERE service_id = ?",
                ((position, _now(), item) for position, item in enumerate(ordered)),
            )
            return True

    def seed_channels_once(
        self,
        service_id: str,
        channels: tuple[tuple[str, str, dict[str, Any]], ...],
        *,
        marker: str,
    ) -> bool:
        """Seed an ordered channel list once and preserve later user changes."""
        if not service_id or not marker or _SECRET_KEY.search(marker):
            raise ValueError("channel seed service and non-secret marker are required")
        with self.transaction():
            seeded = self.connection.execute(
                "SELECT value_json FROM settings WHERE key = ?", (marker,)
            ).fetchone()
            if seeded is not None and json.loads(seeded["value_json"]) is True:
                return False
            existing = self.connection.execute(
                "SELECT id, external_id FROM channels WHERE service_id = ? ORDER BY position, id",
                (service_id,),
            ).fetchall()
            by_external = {
                str(row["external_id"]): int(row["id"]) for row in existing
            }
            ordered_ids: list[int] = []
            for external_id, name, metadata in channels:
                channel_id = by_external.get(external_id)
                if channel_id is None:
                    cursor = self.connection.execute(
                        """
                        INSERT INTO channels(
                            service_id, external_id, name, metadata_json, position
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            service_id,
                            external_id,
                            name,
                            json.dumps(metadata, ensure_ascii=False, separators=(",", ":")),
                            len(ordered_ids),
                        ),
                    )
                    channel_id = int(cursor.lastrowid)
                ordered_ids.append(channel_id)
            ordered_ids.extend(
                int(row["id"])
                for row in existing
                if int(row["id"]) not in ordered_ids
            )
            self.connection.executemany(
                "UPDATE channels SET position = ? WHERE id = ?",
                ((position, channel_id) for position, channel_id in enumerate(ordered_ids)),
            )
            self.connection.execute(
                """
                INSERT INTO settings(key, value_json, updated_at) VALUES (?, 'true', ?)
                ON CONFLICT(key) DO UPDATE SET value_json = 'true', updated_at = excluded.updated_at
                """,
                (marker, _now()),
            )
            return True

    def channels(self, service_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT id, service_id, external_id, name, favorite, metadata_json, position
                FROM channels WHERE service_id = ? ORDER BY position, id LIMIT 500
                """,
                (service_id,),
            ).fetchall()
        return [
            {
                **dict(row),
                "metadata": json.loads(str(row["metadata_json"])),
            }
            for row in rows
        ]

    def channel(self, channel_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self.connection.execute(
                """
                SELECT id, service_id, external_id, name, favorite, metadata_json, position
                FROM channels WHERE id = ?
                """,
                (channel_id,),
            ).fetchone()
        if row is None:
            return None
        return {**dict(row), "metadata": json.loads(str(row["metadata_json"]))}

    def add_channel(
        self,
        service_id: str,
        external_id: str,
        name: str,
        metadata: dict[str, Any],
    ) -> int:
        if not service_id or not external_id or not name.strip() or len(name) > 160:
            raise ValueError("channel service, id and name are required")
        with self.transaction():
            existing = self.connection.execute(
                "SELECT id FROM channels WHERE service_id = ? AND external_id = ?",
                (service_id, external_id),
            ).fetchone()
            if existing is not None:
                return int(existing["id"])
            last = self.connection.execute(
                "SELECT MAX(position) AS position FROM channels WHERE service_id = ?",
                (service_id,),
            ).fetchone()
            position = 0 if last is None or last["position"] is None else int(last["position"]) + 1
            cursor = self.connection.execute(
                """
                INSERT INTO channels(service_id, external_id, name, metadata_json, position)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    service_id,
                    external_id,
                    name.strip(),
                    json.dumps(metadata, ensure_ascii=False, separators=(",", ":")),
                    position,
                ),
            )
            return int(cursor.lastrowid)

    def update_channel(self, channel_id: int, name: str, metadata: dict[str, Any]) -> bool:
        if not name.strip() or len(name) > 160:
            raise ValueError("channel name is required")
        with self.transaction():
            cursor = self.connection.execute(
                "UPDATE channels SET name = ?, metadata_json = ? WHERE id = ?",
                (
                    name.strip(),
                    json.dumps(metadata, ensure_ascii=False, separators=(",", ":")),
                    channel_id,
                ),
            )
            return cursor.rowcount == 1

    def delete_channel(self, channel_id: int) -> bool:
        with self.transaction():
            row = self.connection.execute(
                "SELECT service_id FROM channels WHERE id = ?", (channel_id,)
            ).fetchone()
            if row is None:
                return False
            cursor = self.connection.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
            self._resequence_channels(str(row["service_id"]))
            return cursor.rowcount == 1

    def move_channel(self, channel_id: int, direction: int) -> bool:
        if direction not in {-1, 1}:
            raise ValueError("channel direction must be -1 or 1")
        with self.transaction():
            row = self.connection.execute(
                "SELECT service_id FROM channels WHERE id = ?", (channel_id,)
            ).fetchone()
            if row is None:
                return False
            service_id = str(row["service_id"])
            rows = self.connection.execute(
                "SELECT id FROM channels WHERE service_id = ? ORDER BY position, id",
                (service_id,),
            ).fetchall()
            ordered = [int(item["id"]) for item in rows]
            current = ordered.index(channel_id)
            target = current + direction
            if target < 0 or target >= len(ordered):
                return False
            ordered[current], ordered[target] = ordered[target], ordered[current]
            self.connection.executemany(
                "UPDATE channels SET position = ? WHERE id = ?",
                ((position, item_id) for position, item_id in enumerate(ordered)),
            )
            return True

    def _resequence_channels(self, service_id: str) -> None:
        rows = self.connection.execute(
            "SELECT id FROM channels WHERE service_id = ? ORDER BY position, id",
            (service_id,),
        ).fetchall()
        self.connection.executemany(
            "UPDATE channels SET position = ? WHERE id = ?",
            ((position, int(row["id"])) for position, row in enumerate(rows)),
        )

    def seed_stations_once(
        self,
        service_id: str,
        stations: tuple[tuple[str, str], ...],
        *,
        marker: str,
        append: bool = False,
    ) -> bool:
        """Seed a persistent ordered station list once, never after deletion."""
        if not service_id or not marker or _SECRET_KEY.search(marker):
            raise ValueError("station seed service and non-secret marker are required")
        with self.transaction():
            seeded = self.connection.execute(
                "SELECT value_json FROM settings WHERE key = ?", (marker,)
            ).fetchone()
            if seeded is not None and json.loads(seeded["value_json"]) is True:
                return False

            existing = self.connection.execute(
                """
                SELECT id, stream_url FROM stations
                WHERE service_id = ? ORDER BY position, id
                """,
                (service_id,),
            ).fetchall()
            by_url = {str(row["stream_url"]): int(row["id"]) for row in existing}
            ordered_ids: list[int] = (
                [int(row["id"]) for row in existing] if append else []
            )
            now = _now()
            for name, stream_url in stations:
                station_id = by_url.get(stream_url)
                if station_id is None:
                    cursor = self.connection.execute(
                        """
                        INSERT INTO stations(
                            service_id, name, stream_url, position, created_at
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (service_id, name, stream_url, len(ordered_ids), now),
                    )
                    station_id = int(cursor.lastrowid)
                if station_id not in ordered_ids:
                    ordered_ids.append(station_id)
            ordered_ids.extend(
                int(row["id"])
                for row in existing
                if int(row["id"]) not in ordered_ids
            )
            self.connection.executemany(
                "UPDATE stations SET position = ? WHERE id = ?",
                ((position, station_id) for position, station_id in enumerate(ordered_ids)),
            )
            self.connection.execute(
                """
                INSERT INTO settings(key, value_json, updated_at) VALUES (?, 'true', ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = 'true', updated_at = excluded.updated_at
                """,
                (marker, now),
            )
            return True

    def add_station(self, service_id: str, name: str, stream_url: str) -> int:
        if not service_id or not name.strip() or len(name) > 160:
            raise ValueError("station service and name are required")
        with self.transaction():
            existing = self.connection.execute(
                "SELECT id FROM stations WHERE service_id = ? AND stream_url = ? LIMIT 1",
                (service_id, stream_url),
            ).fetchone()
            if existing is not None:
                return int(existing["id"])
            last = self.connection.execute(
                "SELECT MAX(position) AS position FROM stations WHERE service_id = ?",
                (service_id,),
            ).fetchone()
            position = 0 if last is None or last["position"] is None else int(last["position"]) + 1
            cursor = self.connection.execute(
                """
                INSERT INTO stations(service_id, name, stream_url, position, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (service_id, name.strip(), stream_url, position, _now()),
            )
            return int(cursor.lastrowid)

    def delete_station(self, station_id: int) -> bool:
        with self.transaction():
            row = self.connection.execute(
                "SELECT service_id FROM stations WHERE id = ?", (station_id,)
            ).fetchone()
            if row is None:
                return False
            cursor = self.connection.execute(
                "DELETE FROM stations WHERE id = ?", (station_id,)
            )
            self._resequence_stations(str(row["service_id"]))
            return cursor.rowcount == 1

    def move_station(self, station_id: int, direction: int) -> bool:
        if direction not in {-1, 1}:
            raise ValueError("station direction must be -1 or 1")
        with self.transaction():
            selected = self.connection.execute(
                "SELECT service_id FROM stations WHERE id = ?", (station_id,)
            ).fetchone()
            if selected is None:
                return False
            service_id = str(selected["service_id"])
            rows = self.connection.execute(
                """
                SELECT id FROM stations WHERE service_id = ?
                ORDER BY position, id
                """,
                (service_id,),
            ).fetchall()
            ordered = [int(row["id"]) for row in rows]
            current = ordered.index(station_id)
            target = current + direction
            if target < 0 or target >= len(ordered):
                return False
            ordered[current], ordered[target] = ordered[target], ordered[current]
            self.connection.executemany(
                "UPDATE stations SET position = ? WHERE id = ?",
                ((position, item_id) for position, item_id in enumerate(ordered)),
            )
            return True

    def _resequence_stations(self, service_id: str) -> None:
        rows = self.connection.execute(
            """
            SELECT id FROM stations WHERE service_id = ?
            ORDER BY position, id
            """,
            (service_id,),
        ).fetchall()
        self.connection.executemany(
            "UPDATE stations SET position = ? WHERE id = ?",
            ((position, int(row["id"])) for position, row in enumerate(rows)),
        )

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
                ORDER BY position, id LIMIT 500
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
                SELECT id, service_id, path, artist, title, duration_seconds,
                       size_bytes, checksum, favorite, normalized_key,
                       fingerprint, cover_file, review_required, source_kind
                FROM media WHERE service_id = ?
                ORDER BY COALESCE(artist, '') COLLATE NOCASE,
                         title COLLATE NOCASE LIMIT 2000
                """,
                (service_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def media_item(self, media_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self.connection.execute(
                """
                SELECT id, service_id, path, artist, title, duration_seconds,
                       size_bytes, checksum, favorite, normalized_key,
                       fingerprint, cover_file, review_required, source_kind
                FROM media WHERE id = ?
                """,
                (media_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def media_duplicate(
        self,
        normalized_key: str | None,
        fingerprint: str | None,
        checksum: str | None,
    ) -> dict[str, Any] | None:
        clauses: list[str] = []
        values: list[str] = []
        for column, value in (
            ("normalized_key", normalized_key),
            ("fingerprint", fingerprint),
            ("checksum", checksum),
        ):
            if value:
                clauses.append(f"{column} = ?")
                values.append(value)
        if not clauses:
            return None
        with self._lock:
            row = self.connection.execute(
                "SELECT id, path, artist, title FROM media WHERE "
                + " OR ".join(clauses)
                + " LIMIT 1",
                tuple(values),
            ).fetchone()
        return dict(row) if row is not None else None

    def add_recorded_media(
        self,
        path: Path,
        *,
        artist: str | None,
        title: str,
        size_bytes: int,
        checksum: str,
        normalized_key: str | None,
        fingerprint: str | None,
        review_required: bool,
    ) -> int:
        if not path.is_absolute() or not title:
            raise ValueError("recorded media requires an absolute path and title")
        with self.transaction():
            cursor = self.connection.execute(
                """
                INSERT INTO media(
                    service_id, path, artist, title, size_bytes, checksum,
                    normalized_key, fingerprint, review_required, source_kind,
                    created_at
                ) VALUES ('local_media', ?, ?, ?, ?, ?, ?, ?, ?, 'radio', ?)
                """,
                (
                    str(path),
                    artist,
                    title[:240],
                    size_bytes,
                    checksum,
                    normalized_key,
                    fingerprint,
                    int(review_required),
                    _now(),
                ),
            )
            return int(cursor.lastrowid)

    def set_media_favorite(self, media_id: int, favorite: bool) -> bool:
        if isinstance(media_id, bool) or not isinstance(media_id, int):
            raise ValueError("media id must be an integer")
        if not isinstance(favorite, bool):
            raise ValueError("favorite state must be boolean")
        with self.transaction():
            cursor = self.connection.execute(
                "UPDATE media SET favorite = ? WHERE id = ?",
                (int(favorite), media_id),
            )
        return cursor.rowcount == 1

    def set_media_cover(self, media_id: int, cover_file: str | None) -> bool:
        if cover_file is not None and not re.fullmatch(r"track-\d+\.jpg", cover_file):
            raise ValueError("invalid local cover filename")
        with self.transaction():
            cursor = self.connection.execute(
                "UPDATE media SET cover_file = ? WHERE id = ?",
                (cover_file, media_id),
            )
        return cursor.rowcount == 1

    def delete_media(self, media_id: int) -> dict[str, Any] | None:
        if isinstance(media_id, bool) or not isinstance(media_id, int):
            raise ValueError("media id must be an integer")
        with self.transaction():
            row = self.connection.execute(
                "SELECT id, path, cover_file FROM media WHERE id = ?", (media_id,)
            ).fetchone()
            if row is None:
                return None
            self.connection.execute("DELETE FROM media WHERE id = ?", (media_id,))
        return dict(row)

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
