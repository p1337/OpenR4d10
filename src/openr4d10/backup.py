"""Portable, secret-free SQLite backup and guarded restore."""

from __future__ import annotations

from contextlib import closing
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import zipfile

from . import __version__
from .storage import SCHEMA_VERSION


FORMAT_VERSION = 1
DATABASE_NAME = "state.sqlite3"
MANIFEST_NAME = "manifest.json"
MAX_DATABASE_BYTES = 256 * 1024 * 1024
MAX_MANIFEST_BYTES = 256 * 1024


class BackupError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _database_info(path: Path) -> tuple[int, list[dict[str, object]]]:
    try:
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        check = connection.execute("PRAGMA quick_check").fetchone()
        if check is None or check[0] != "ok":
            raise BackupError("SQLite integrity check failed")
        schema_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        rows = connection.execute(
            "SELECT service_id, enabled FROM service_state ORDER BY service_id LIMIT 500"
        ).fetchall()
    except sqlite3.Error as exc:
        raise BackupError(f"cannot inspect state database: {exc}") from exc
    finally:
        if "connection" in locals():
            connection.close()
    services = [
        {"service_id": str(row["service_id"])[:64], "enabled": bool(row["enabled"])}
        for row in rows
    ]
    return schema_version, services


def create_backup(database: Path, output: Path) -> dict[str, object]:
    if not database.is_absolute() or not output.is_absolute():
        raise ValueError("backup database and output paths must be absolute")
    if not database.is_file():
        raise BackupError(f"state database does not exist: {database}")
    if database.resolve() == output.resolve():
        raise BackupError("backup output must not replace the live state database")
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
    archive_temp: Path | None = None
    with tempfile.TemporaryDirectory(prefix="openr4d10-backup-") as raw:
        snapshot = Path(raw) / DATABASE_NAME
        try:
            with closing(sqlite3.connect(database)) as source, closing(
                sqlite3.connect(snapshot)
            ) as destination:
                source.backup(destination)
        except sqlite3.Error as exc:
            raise BackupError(f"cannot create consistent SQLite backup: {exc}") from exc
        if snapshot.stat().st_size > MAX_DATABASE_BYTES:
            raise BackupError("state database exceeds the portable backup size limit")
        schema_version, services = _database_info(snapshot)
        if schema_version > SCHEMA_VERSION:
            raise BackupError("state database schema is newer than this OpenR4d10 release")
        manifest: dict[str, object] = {
            "format": "openr4d10-backup",
            "format_version": FORMAT_VERSION,
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "openr4d10_version": __version__,
            "schema_version": schema_version,
            "database_sha256": _sha256(snapshot),
            "services": services,
            "includes": ["non-secret SQLite state", "service activation plan"],
            "excludes": ["credentials", "media", "recordings", "WLAN", "SSH keys"],
        }
        handle = tempfile.NamedTemporaryFile(
            prefix=f".{output.name}.", suffix=".tmp", dir=output.parent, delete=False
        )
        archive_temp = Path(handle.name)
        handle.close()
        try:
            with zipfile.ZipFile(
                archive_temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
            ) as archive:
                archive.write(snapshot, DATABASE_NAME)
                archive.writestr(
                    MANIFEST_NAME,
                    json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2)
                    + "\n",
                )
            os.chmod(archive_temp, 0o600)
            os.replace(archive_temp, output)
            archive_temp = None
        finally:
            if archive_temp is not None:
                archive_temp.unlink(missing_ok=True)
    return manifest


def _read_archive(archive_path: Path, destination: Path) -> dict[str, object]:
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            names = archive.namelist()
            if set(names) != {DATABASE_NAME, MANIFEST_NAME} or len(names) != 2:
                raise BackupError("backup archive contains unexpected files")
            database_info = archive.getinfo(DATABASE_NAME)
            manifest_info = archive.getinfo(MANIFEST_NAME)
            if database_info.file_size > MAX_DATABASE_BYTES:
                raise BackupError("backup database exceeds the restore size limit")
            if manifest_info.file_size > MAX_MANIFEST_BYTES:
                raise BackupError("backup manifest exceeds the restore size limit")
            manifest_value = json.loads(archive.read(MANIFEST_NAME))
            if not isinstance(manifest_value, dict):
                raise BackupError("backup manifest must be a JSON object")
            with archive.open(DATABASE_NAME, "r") as source, destination.open("wb") as target:
                while block := source.read(1024 * 1024):
                    target.write(block)
    except (OSError, zipfile.BadZipFile, KeyError, json.JSONDecodeError) as exc:
        raise BackupError(f"cannot read backup archive: {exc}") from exc
    return manifest_value


def restore_backup(
    archive: Path,
    database: Path,
    runtime_directory: Path,
    *,
    replace: bool = False,
) -> dict[str, object]:
    if not all(path.is_absolute() for path in (archive, database, runtime_directory)):
        raise ValueError("restore paths must be absolute")
    if runtime_directory.exists():
        raise BackupError(
            f"OpenR4d10 runtime directory exists; stop the service first: {runtime_directory}"
        )
    if database.exists() and not replace:
        raise BackupError("state database exists; pass --replace for an explicit restore")
    if archive.resolve() == database.resolve():
        raise BackupError("backup archive and state database must be different files")
    if not archive.is_file():
        raise BackupError(f"backup archive does not exist: {archive}")
    database.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
    handle = tempfile.NamedTemporaryFile(
        prefix=f".{database.name}.", suffix=".restore", dir=database.parent, delete=False
    )
    temporary = Path(handle.name)
    handle.close()
    try:
        manifest = _read_archive(archive, temporary)
        if manifest.get("format") != "openr4d10-backup" or manifest.get("format_version") != FORMAT_VERSION:
            raise BackupError("unsupported backup format")
        expected = manifest.get("database_sha256")
        if not isinstance(expected, str) or _sha256(temporary) != expected:
            raise BackupError("backup database checksum does not match the manifest")
        schema_version, _services = _database_info(temporary)
        if schema_version != manifest.get("schema_version"):
            raise BackupError("backup schema does not match the manifest")
        if schema_version > SCHEMA_VERSION:
            raise BackupError("backup schema is newer than this OpenR4d10 release")
        os.chmod(temporary, 0o600)
        for suffix in ("-wal", "-shm"):
            Path(f"{database}{suffix}").unlink(missing_ok=True)
        os.replace(temporary, database)
    finally:
        temporary.unlink(missing_ok=True)
    return manifest
