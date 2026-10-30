"""Command-line interface."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

from .adapters import build_adapters
from .app import OpenR4d10App
from .config import ConfigError, load_app_config, load_hardware_config
from .doctor import exit_code, run_checks


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

    display, power, receiver = build_adapters(hardware_config)
    application = OpenR4d10App(
        app_config,
        display=display,
        power=power,
        receiver=receiver,
        hardware=hardware_config,
    )
    if args.command == "render-once":
        application.render_once()
        return 0
    application.run()
    return 0
