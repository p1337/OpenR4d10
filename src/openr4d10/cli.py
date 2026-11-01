"""Command-line interface."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

from .adapters import build_adapters
from .app import OpenR4d10App
from .backup import BackupError, create_backup, restore_backup
from .config import ConfigError, load_app_config, load_hardware_config
from .device_ui import DeviceUiState, render_device_ui
from .doctor import exit_code, run_checks
from .services import ServiceCatalog


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="openr4d10")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("/etc/openr4d10/openr4d10.toml"),
        help="application TOML file",
    )
    parser.add_argument(
        "--hardware-config",
        type=Path,
        default=Path("/etc/openr4d10/hardware.toml"),
        help="hardware adapter TOML file",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run", help="run the service loop")
    commands.add_parser("render-once", help="render one dashboard frame")
    backup = commands.add_parser("backup", help="create a secret-free state backup")
    backup.add_argument("--output", type=Path, required=True, help="absolute backup archive path")
    restore = commands.add_parser("restore", help="restore a validated state backup")
    restore.add_argument("--input", type=Path, required=True, help="absolute backup archive path")
    restore.add_argument("--replace", action="store_true", help="explicitly replace an existing state database")
    preview = commands.add_parser("preview-ui", help="write a 240x280 UI preview PNG")
    preview.add_argument("--output", type=Path, required=True, help="PNG output path")
    doctor = commands.add_parser("doctor", help="check platform and configuration")
    doctor.add_argument(
        "--allow-unsupported-platform",
        action="store_true",
        help="report but do not fail for non-Pi development hosts",
    )
    doctor.add_argument(
        "--allow-unconfigured",
        action="store_true",
        help="report but do not fail for placeholder hardware adapters",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "preview-ui":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        render_device_ui(DeviceUiState()).save(args.output, format="PNG")
        print(args.output)
        return 0

    try:
        app_config = load_app_config(args.config)
        hardware_config = load_hardware_config(args.hardware_config)
    except ConfigError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    logging.basicConfig(
        level=getattr(logging, app_config.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    database_path = app_config.state_directory / "openr4d10.sqlite3"
    if args.command == "backup":
        try:
            manifest = create_backup(database_path, args.output)
        except (BackupError, ValueError) as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 1
        print(f"Backup created: {args.output} ({manifest['database_sha256']})")
        return 0
    if args.command == "restore":
        try:
            manifest = restore_backup(
                args.input,
                database_path,
                app_config.runtime_directory,
                replace=args.replace,
            )
        except (BackupError, ValueError) as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 1
        print(f"Backup restored: schema {manifest['schema_version']}")
        return 0

    if args.command == "doctor":
        checks = run_checks(
            app_config,
            hardware_config,
            allow_unsupported_platform=args.allow_unsupported_platform,
        )
        for check in checks:
            print(f"[{check.level}] {check.message}")
        code = exit_code(checks, allow_unconfigured=args.allow_unconfigured)
        if code == 2:
            print("[WARN] HARDWARE CONFIGURATION REQUIRED")
        return code

    display, power, receiver = build_adapters(
        hardware_config,
        app_config.state_directory,
    )
    services = (
        ServiceCatalog(
            app_config.state_directory,
            runtime_directory=app_config.runtime_directory,
            adapter_directory=app_config.service_adapter_directory,
        )
        if args.command == "run"
        else None
    )
    if services is not None:
        services.prefetch_ambient_audio()
        services.prefetch_brandmeister_catalog()
        # Saved BrandMeister talkgroups are configuration, never permission to
        # start network audio after a boot.  Playback always requires an
        # explicit PLAY/ENTER action from the user.
    application = OpenR4d10App(
        app_config,
        display=display,
        power=power,
        receiver=receiver,
        hardware=hardware_config,
        services=services,
    )
    if args.command == "render-once":
        try:
            application.render_once()
        finally:
            application.close()
        return 0
    application.run()
    return 0
