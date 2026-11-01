from pathlib import Path
import re
import tomllib
import unittest


class InstallerContractTests(unittest.TestCase):
    def test_release_version_is_consistent_across_installer_and_python_metadata(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        release = repository.joinpath("VERSION").read_text(encoding="ascii").strip()
        project = tomllib.loads(repository.joinpath("pyproject.toml").read_text(encoding="utf-8"))
        package = repository.joinpath("src", "openr4d10", "__init__.py").read_text(encoding="utf-8")
        match = re.search(r'^__version__ = "([^"]+)"$', package, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(release, project["project"]["version"])
        self.assertEqual(release, match.group(1))

    def test_radio_capture_fingerprint_tool_is_installed(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        installer = (repository / "install.sh").read_text(encoding="utf-8")
        self.assertIn("libchromaprint-tools", installer)

    def test_application_media_boundaries_belong_to_the_service_user(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        installer = (repository / "install.sh").read_text(encoding="utf-8")
        self.assertIn(
            'install -d -m 0750 -o openr4d10 -g openr4d10 "$STATE_ROOT"',
            installer,
        )
        for relative in ("media", "media/ambient", "recordings", "cache"):
            self.assertIn(f'"$STATE_ROOT/{relative}"', installer)
        self.assertNotIn('chown -R openr4d10', installer)
        self.assertIn('"$state_database-wal" "$state_database-shm"', installer)
        self.assertIn('! -L "$sqlite_file"', installer)
        self.assertIn('for _attempt in {1..60}', installer)
        self.assertIn("python3-websockets", installer)
        self.assertIn("python3-msgpack", installer)

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
        self.assertIn("bin/openr4d10-audio-max", installer)
        self.assertIn("systemd/openr4d10-audio-max.service", installer)
        audio_helper = (repository / "bin" / "openr4d10-audio-max").read_text(
            encoding="utf-8"
        )
        audio_service = (
            repository / "systemd" / "openr4d10-audio-max.service"
        ).read_text(encoding="utf-8")
        self.assertIn("cset name=speaker 100", audio_helper)
        self.assertNotIn("cset name=speaker 101", audio_helper)
        self.assertIn("After=sound.target whisplay-soundcard-warmup.service", audio_service)
        self.assertIn("Before=openr4d10.service", audio_service)
        self.assertIn("ExecStart=/usr/local/sbin/openr4d10-audio-max", audio_service)
        self.assertIn("User=root", audio_service)
        self.assertIn("After=openr4d10-audio-max.service", application_service)
        vendor_audio_installer = (
            repository
            / "vendor"
            / "pisugar-whisplay"
            / "audio"
            / "scripts"
            / "install.sh"
        ).read_text(encoding="utf-8")
        warmup_unit = vendor_audio_installer.split(
            "cat >/etc/systemd/system/whisplay-soundcard-warmup.service <<'EOF'",
            1,
        )[1].split("\nEOF", 1)[0]
        self.assertIn("After=sound.target alsa-restore.service", warmup_unit)
        self.assertNotIn("multi-user.target", warmup_unit.split("[Service]", 1)[0])
        self.assertIn("boot/openr4d10-backlight", installer)
        self.assertIn("Backing up persistent OpenR4d10 state before the update", installer)
        self.assertIn("from openr4d10.backup import create_backup", installer)
        self.assertLess(
            installer.index("Backing up persistent OpenR4d10 state before the update"),
            installer.index("apt-get update"),
        )
        self.assertIn("WorkingDirectory=/run/openr4d10", application_service)
        self.assertIn("ProtectSystem=strict", application_service)
        self.assertIn("SupplementaryGroups=gpio spi audio i2c", application_service)
        self.assertIn("DeviceAllow=/dev/i2c-1 rw", application_service)
        self.assertIn("modprobe i2c-dev", installer)
        self.assertIn('backend = "pisugar3"', (repository / "config" / "hardware.toml").read_text(encoding="utf-8"))
        self.assertIn(
            "ReadWritePaths=/run/openr4d10 /run/openr4d10-backlight /var/lib/openr4d10",
            application_service,
        )

    def test_whisplay_backlight_uses_fixed_kernel_pwm_boundary(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        boot_installer = (repository / "boot" / "install.sh").read_text(encoding="utf-8")
        helper = (repository / "boot" / "openr4d10-backlight").read_text(encoding="utf-8")
        path_unit = (repository / "boot" / "openr4d10-backlight.path").read_text(encoding="utf-8")
        service = (repository / "boot" / "openr4d10-backlight.service").read_text(encoding="utf-8")
        boot_source = (repository / "boot" / "native" / "openr4d10_boot.c").read_text(encoding="utf-8")

        self.assertIn("dtoverlay=pwm-gpio,gpio=22", boot_installer)
        self.assertIn("openr4d10-backlight-init.service", boot_installer)
        self.assertIn('"$node" == pwm_gpio@16', helper)
        self.assertIn("pwm_gpio@22", helper)
        self.assertIn(
            "ReadWritePaths=/run/openr4d10-backlight",
            (repository / "boot" / "openr4d10-boot.service").read_text(encoding="utf-8"),
        )
        self.assertIn("PERIOD_NS=1000000", helper)
        self.assertIn("PathExists=/run/openr4d10-backlight/brightness.request", path_unit)
        self.assertIn("User=root", service)
        self.assertNotIn("req.offsets[2]=22", boot_source)
        self.assertIn("queue_backlight(100)", boot_source)

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
        self.assertIn('active_state="$(\n', helper)
        self.assertIn('"$active_state" == 100', helper)
        self.assertIn('nmcli --wait 10 device disconnect "$INTERFACE"', helper)
        self.assertIn("for attempt in 1 2 3", helper)
        self.assertIn('write_status failed "Setup hotspot could not start;', helper)
        self.assertIn("[[ $# -eq 0 ]]", helper)
        self.assertNotIn("hostapd", helper)
        self.assertNotIn("wpa_supplicant", helper)
        self.assertIn("User=root", service)
        self.assertIn("RuntimeDirectory=openr4d10", service)
        self.assertIn("RuntimeDirectoryPreserve=yes", service)
        self.assertIn("-/run/openr4d10", service)
        self.assertIn("ExecStart=/usr/local/sbin/openr4d10-hotspot", service)
        self.assertIn("OnBootSec=30s", timer)
        self.assertIn("OnUnitActiveSec=30s", timer)


if __name__ == "__main__":
    unittest.main()
