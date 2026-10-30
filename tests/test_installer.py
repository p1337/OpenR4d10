from pathlib import Path
import unittest


class InstallerContractTests(unittest.TestCase):
    def test_main_installer_owns_whisplay_audio_installation(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        installer = (repository / "install.sh").read_text(encoding="utf-8")

        self.assertIn("vendor/pisugar-whisplay/audio/scripts/install.sh", installer)
        self.assertIn("WHISPLAY_PLATFORM=raspberry_pi", installer)
        self.assertIn("raspberrypi-kernel-headers", installer)
        self.assertIn("REBOOT REQUIRED: sudo reboot", installer)
        self.assertNotIn("git clone", installer)

    def test_pinned_vendor_provenance_is_present(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        provenance = (
            repository / "vendor" / "pisugar-whisplay" / "UPSTREAM.md"
        ).read_text(encoding="utf-8")

        self.assertIn("736975188ebbe146d319e450aad19c218a310611", provenance)
        self.assertIn(
            "1fac1045fb763de52eed5aa23704d7752ff5e024c9ce64692cf9832261cfb88a",
            provenance,
        )
        self.assertTrue(
            (repository / "vendor" / "pisugar-whisplay" / "LICENSE").is_file()
        )


if __name__ == "__main__":
    unittest.main()
