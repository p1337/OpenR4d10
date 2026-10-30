from pathlib import Path
import unittest


class InstallerContractTests(unittest.TestCase):
    def test_main_installer_owns_whisplay_audio_installation(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        installer = (repository / "install.sh").read_text(encoding="utf-8")

        self.assertIn("vendor/pisugar-whisplay/audio/scripts/install.sh", installer)
        self.assertIn("WHISPLAY_PLATFORM=raspberry_pi", installer)
        self.assertIn('"linux-headers-$kernel_release"', installer)
        self.assertIn("scripts/basic/fixdep", installer)
        self.assertNotIn("raspberrypi-kernel-headers", installer)
        self.assertIn("AUTO_REBOOT=true", installer)
        self.assertIn("--no-reboot", installer)
        self.assertIn("systemctl reboot --no-block", installer)
        self.assertIn("REBOOT REQUIRED: sudo reboot", installer)
        self.assertNotIn("git clone", installer)
        self.assertIn("bin/openr4d10-update", installer)
        self.assertIn("systemd/openr4d10-update.path", installer)
        self.assertIn("systemctl enable --now openr4d10-update.path", installer)
        self.assertIn("Backing up persistent OpenR4d10 state before the update", installer)
        self.assertIn("from openr4d10.backup import create_backup", installer)
        self.assertLess(
            installer.index("Backing up persistent OpenR4d10 state before the update"),
            installer.index("apt-get update"),
        )

    def test_web_updater_has_a_fixed_privilege_boundary(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        helper = (repository / "bin" / "openr4d10-update").read_text(
            encoding="utf-8"
        )
        path_unit = (repository / "systemd" / "openr4d10-update.path").read_text(
            encoding="utf-8"
        )
        service = (
            repository / "systemd" / "openr4d10-update.service"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "https://raw.githubusercontent.com/p1337/OpenR4d10/main/bootstrap.sh",
            helper,
        )
        self.assertIn("bash \"$bootstrap\"", helper)
        self.assertIn("[[ $# -eq 0 ]]", helper)
        self.assertNotIn("$@", helper)
        self.assertNotIn("sudo", helper)
        self.assertIn("PathExists=/run/openr4d10/update.request", path_unit)
        self.assertIn("User=root", service)
        self.assertIn("ExecStart=/usr/local/sbin/openr4d10-update", service)

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
