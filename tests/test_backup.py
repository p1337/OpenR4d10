from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from openr4d10.backup import BackupError, create_backup, restore_backup
from openr4d10.storage import StateStore


class BackupTests(unittest.TestCase):
    def test_backup_and_explicit_offline_restore_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            database = root / "state" / "openr4d10.sqlite3"
            archive = root / "backup.openr4d10.zip"
            runtime = root / "run"
            store = StateStore(database)
            store.ensure_services(("system", "webradio"), {"system", "webradio"})
            store.set_setting("ui.accent", "cyan")
            store.close()

            manifest = create_backup(database, archive)
            self.assertTrue(archive.is_file())
            self.assertEqual(manifest["format"], "openr4d10-backup")
            self.assertIn("credentials", manifest["excludes"])

            changed = StateStore(database)
            changed.set_setting("ui.accent", "orange")
            changed.close()
            restore_backup(archive, database, runtime, replace=True)
            restored = StateStore(database)
            try:
                self.assertEqual(restored.get_setting("ui.accent"), "cyan")
            finally:
                restored.close()

    def test_restore_requires_stopped_service_and_explicit_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            database = root / "openr4d10.sqlite3"
            archive = root / "backup.zip"
            runtime = root / "run"
            store = StateStore(database)
            store.ensure_services(("system",), {"system"})
            store.close()
            create_backup(database, archive)
            with self.assertRaisesRegex(BackupError, "--replace"):
                restore_backup(archive, database, runtime)
            runtime.mkdir()
            with self.assertRaisesRegex(BackupError, "stop the service"):
                restore_backup(archive, database, runtime, replace=True)


if __name__ == "__main__":
    unittest.main()
