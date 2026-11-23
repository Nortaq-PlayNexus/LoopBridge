"""CLI entry point: python -m loopbridge [options]"""

from __future__ import annotations

import argparse
import sys

from .config.profiles import DEFAULT_PROFILE, Profile
from .core.errors import LoopError

DEFAULT_PROFILE_PATH = "loopbridge-profile.json"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="loopbridge",
        description="Relay loop between ChatGPT (Brave) and OpenCode (PowerShell window).",
    )
    parser.add_argument("--profile", default=DEFAULT_PROFILE_PATH,
                        help=f"JSON profile path (default: {DEFAULT_PROFILE_PATH})")
    parser.add_argument("--count", type=int, default=None,
                        help="Run exactly N loop iterations, then stop.")
    parser.add_argument("--simulate", action="store_true",
                        help="Run with mock drivers (no real windows).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Act but do not actually send to OpenCode / ChatGPT.")
    parser.add_argument("--gui", action="store_true",
                        help="Launch the desktop UI (needs PySide6 on Windows).")
    return parser.parse_args(argv)


def load_profile(path: str) -> Profile:
    from pathlib import Path

    p = Path(path)
    if p.exists():
        return Profile.load(p)
    return DEFAULT_PROFILE


def main(argv=None) -> int:
    args = parse_args(argv)
    profile = load_profile(args.profile)
    if args.dry_run:
        profile.debug.dry_run = True

    if args.gui:
        from .app import launch_gui

        launch_gui(args.profile)
        return 0

    from .app import run_console

    try:
        stats = run_console(profile, simulate=args.simulate, count=args.count)
    except LoopError as exc:
        print(f"[x] {exc}")
        return 1
    print(f"Finished: {stats.loops_completed} iterations, "
          f"{stats.errors} errors, {stats.retries} retries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
