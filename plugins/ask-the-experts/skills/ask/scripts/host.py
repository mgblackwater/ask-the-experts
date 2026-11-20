#!/usr/bin/env python3
"""Start the Ask the Experts app or its always-on moderator from the newest installed plugin.

The Windows setup copies this file into your home folder, and the start-at-logon tasks run it, so
plugin updates never leave a task pointing at an old version folder.

Usage:
  python -I host.py server       the app (roundtable_server.py)
  python -I host.py moderator    the always-on moderator (headless_moderator.py)
"""
import pathlib
import subprocess
import sys

BASE = pathlib.Path.home() / ".claude" / "plugins" / "cache"  # <marketplace>/ask-the-experts/<version>
SCRIPTS = {"server": "roundtable_server.py", "moderator": "headless_moderator.py"}


def newest_scripts():
    def key(d):
        return [int(x) if x.isdigit() else 0 for x in d.name.split(".")]
    versions = [d for d in BASE.glob("*/ask-the-experts/*") if (d / "skills" / "ask" / "scripts").is_dir()] if BASE.is_dir() else []
    if not versions:
        sys.exit(f"Ask the Experts isn't installed under {BASE}. Install it in Claude Code (/plugin).")
    return max(versions, key=key) / "skills" / "ask" / "scripts"


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in SCRIPTS:
        sys.exit(__doc__)
    script = newest_scripts() / SCRIPTS[sys.argv[1]]
    sys.exit(subprocess.call([sys.executable, "-I", str(script)]))


if __name__ == "__main__":
    main()
