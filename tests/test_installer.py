from pathlib import Path
import unittest


class InstallerContractTests(unittest.TestCase):
    def test_main_installer_owns_whisplay_audio_installation(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        installer = (repository / "install.sh").read_text(encoding="utf-8")
        application_service = (
            repository / "systemd" / "openr4d10.service"
        ).read_text(encoding="utf-8")

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
        self.assertIn("bin/openr4d10-update-recover", installer)
        self.assertIn("systemd/openr4d10-update-recover.service", installer)
        self.assertIn("bin/openr4d10-wifi-repair", installer)
        self.assertIn("systemd/openr4d10-wifi-repair.path", installer)
        self.assertIn("network-manager", installer)
        self.assertIn("dnsmasq-base", installer)
        self.assertIn("bin/openr4d10-hotspot", installer)
        self.assertIn("systemd/openr4d10-hotspot.timer", installer)
        self.assertIn("systemctl enable --now openr4d10-hotspot.timer", installer)
        self.assertIn("Backing up persistent OpenR4d10 state before the update", installer)
        self.assertIn("from openr4d10.backup import create_backup", installer)
        self.assertLess(
            installer.index("Backing up persistent OpenR4d10 state before the update"),
            installer.index("apt-get update"),
        )
        self.assertIn("WorkingDirectory=/run/openr4d10", application_service)
        self.assertIn("ProtectSystem=strict", application_service)
        self.assertIn(
            "ReadWritePaths=/run/openr4d10 /var/lib/openr4d10",
            application_service,
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
        self.assertIn('bash "$bootstrap" --no-reboot', helper)
        self.assertLess(
            helper.index("write_status rebooting"),
            helper.index("systemctl reboot --no-block"),
        )
        self.assertIn("sync", helper)
        self.assertIn("[[ $# -eq 0 ]]", helper)
        self.assertNotIn("$@", helper)
        self.assertNotIn("sudo", helper)
        self.assertIn("PathExists=/run/openr4d10/update.request", path_unit)
        self.assertIn("User=root", service)
        self.assertIn("ExecStart=/usr/local/sbin/openr4d10-update", service)

    def test_reboot_recovery_and_wifi_repair_have_fixed_privilege_boundaries(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        recover = (repository / "bin" / "openr4d10-update-recover").read_text(encoding="utf-8")
        recover_unit = (repository / "systemd" / "openr4d10-update-recover.service").read_text(encoding="utf-8")
        wifi = (repository / "bin" / "openr4d10-wifi-repair").read_text(encoding="utf-8")
        wifi_path = (repository / "systemd" / "openr4d10-wifi-repair.path").read_text(encoding="utf-8")
        wifi_service = (repository / "systemd" / "openr4d10-wifi-repair.service").read_text(encoding="utf-8")

        self.assertIn('{"queued", "running", "rebooting"}', recover)
        self.assertIn('new_state = "completed"', recover)
        self.assertIn('new_state = "failed"', recover)
        self.assertIn("Before=openr4d10.service", recover_unit)
        self.assertIn("ExecStart=/usr/local/sbin/openr4d10-update-recover", recover_unit)
        self.assertIn("INTERFACE=wlan0", wifi)
        self.assertIn("/etc/NetworkManager/system-connections", wifi)
        self.assertIn("os.O_EXCL, 0o600", wifi)
        self.assertNotIn('psk "$passphrase"', wifi)
        self.assertLess(
            wifi.index('connection up uuid "$candidate_uuid"'),
            wifi.index('connection delete uuid "$existing_uuid"'),
        )
        self.assertIn("PathExists=/run/openr4d10/wifi-repair.request", wifi_path)
        self.assertIn("User=root", wifi_service)
        self.assertIn("ExecStart=/usr/local/sbin/openr4d10-wifi-repair", wifi_service)

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

    def test_fallback_hotspot_uses_only_the_existing_networkmanager_owner(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        helper = (repository / "bin" / "openr4d10-hotspot").read_text(encoding="utf-8")
        service = (repository / "systemd" / "openr4d10-hotspot.service").read_text(encoding="utf-8")
        timer = (repository / "systemd" / "openr4d10-hotspot.timer").read_text(encoding="utf-8")

        self.assertIn("INTERFACE=wlan0", helper)
        self.assertIn('CONNECTION_ID="OpenR4d10 Setup"', helper)
        self.assertIn("GRACE_SECONDS=60", helper)
        self.assertIn("mode=ap", helper)
        self.assertIn("key-mgmt=wpa-psk", helper)
        self.assertIn("method=shared", helper)
        self.assertIn("autoconnect=false", helper)
        self.assertIn("chmod 0600 \"$SECRET_FILE\"", helper)
        self.assertIn("[[ $# -eq 0 ]]", helper)
        self.assertNotIn("hostapd", helper)
        self.assertNotIn("wpa_supplicant", helper)
        self.assertIn("User=root", service)
        self.assertIn("ExecStart=/usr/local/sbin/openr4d10-hotspot", service)
        self.assertIn("OnBootSec=30s", timer)
        self.assertIn("OnUnitActiveSec=30s", timer)


if __name__ == "__main__":
    unittest.main()
