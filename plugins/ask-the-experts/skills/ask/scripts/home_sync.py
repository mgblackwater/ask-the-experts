#!/usr/bin/env python3
"""Keep the Ask the Experts home folder (chats, personas) in git, optionally synced through a
private remote such as a private GitHub repository.

Usage:
  python3 -I home_sync.py status             what's configured, and what's changed
  python3 -I home_sync.py commit [message]   commit changes; on the host with git-sync, also push
  python3 -I home_sync.py pull               on a copy machine: fetch the host's latest (fast-forward only)
  python3 -I home_sync.py init <remote>      on the host: turn the home folder into a synced repo and push
  python3 -I home_sync.py clone <remote> [folder]   on a new machine: clone the home folder from the remote

Settings (in ~/.claude/ask-the-experts/config.json):
  "chat_history": "git" (local history only) | "git-sync" (also push to / pull from "sync_remote")
  "sync_remote":  e.g. "https://github.com/<you>/ask-the-experts-home.git"   (keep it PRIVATE)
  "sync_role":    "host" (the one machine that runs the app and pushes) | "copy" (only pulls)
  "sync_sources": false (default) | true  — also sync persona source documents (persona-sources/).
                  Off by default: those are raw uploads (notes, emails), often work material.

Only the host pushes, so two machines never edit the same chat. Runtime files (the app's
inbox, the moderator's state and log, briefs) and persona source documents stay local.
"""
import json
import pathlib
import subprocess
import sys

CONFIG = pathlib.Path.home() / ".claude" / "ask-the-experts" / "config.json"
IGNORE = [
    "# Ask the Experts home folder. Runtime files and raw persona sources stay on this machine.",
    "chats/.ask-the-experts-inbox.jsonl",
    "chats/.moderator-state.json",
    "chats/.moderator-state.tmp",
    "chats/.moderator.log",
    "chats/.briefs/",
    "persona-sources/",
    "host.py",
    ".DS_Store",
    "Thumbs.db",
]


def load_cfg():
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        sys.exit(f"No settings at {CONFIG}: run the skill's setup first")


def save_cfg(cfg):
    CONFIG.write_text(json.dumps(cfg, indent=1) + "\n", encoding="utf-8")


def home_of(cfg):
    if cfg.get("home_dir"):
        return pathlib.Path(cfg["home_dir"]).expanduser()
    if cfg.get("logs_dir"):
        return pathlib.Path(cfg["logs_dir"]).expanduser().parent
    sys.exit("No home folder in the settings")


def git(home, *args, check=True):
    r = subprocess.run(["git", "-C", str(home), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {(r.stderr or r.stdout).strip()[-400:]}")
    return r.stdout.strip()


def ensure_repo(home, cfg=None):
    if not (home / ".git").exists():
        git(home, "init", "-q", "-b", "main")
    ignore = [line for line in IGNORE if not (line == "persona-sources/" and (cfg or {}).get("sync_sources"))]
    gi = home / ".gitignore"
    have = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
    if (cfg or {}).get("sync_sources"):
        have = [line for line in have if line != "persona-sources/"]
    missing = [line for line in ignore if line not in have]
    if missing or (cfg or {}).get("sync_sources"):
        gi.write_text("\n".join(have + missing).strip() + "\n", encoding="utf-8")
    # Files that were tracked before they were ignored: stop tracking them (they stay on disk).
    for line in ignore[1:]:
        if git(home, "ls-files", "--", line.rstrip("/"), check=False):
            git(home, "rm", "-r", "-q", "--cached", "--", line.rstrip("/"), check=False)


def commit(cfg, message):
    home = home_of(cfg)
    if cfg.get("chat_history") == "git-sync" and cfg.get("sync_role") == "copy":
        sys.exit("This machine is a copy (sync_role: copy): it doesn't commit, so its pulls stay clean. "
                 "Make changes on the host.")
    ensure_repo(home, cfg)
    git(home, "add", "-A")
    if git(home, "status", "--porcelain"):
        git(home, "commit", "-q", "-m", message or "Update")
        print(f"committed: {message or 'Update'}")
    else:
        print("nothing new to commit")
    if cfg.get("chat_history") == "git-sync" and cfg.get("sync_role", "host") == "host":
        if not git(home, "remote", check=False):
            print("no remote yet: run `home_sync.py init <remote>`")
            return
        if git(home, "rev-list", "--count", "@{u}..HEAD", check=False) not in ("", "0") or \
           not git(home, "rev-parse", "--abbrev-ref", "@{u}", check=False):
            git(home, "push", "-q", "-u", "origin", "HEAD:main")
            print("pushed")


def pull(cfg):
    home = home_of(cfg)
    if cfg.get("sync_role", "host") == "host":
        sys.exit("This machine is the host (sync_role: host); it pushes, it doesn't pull.")
    git(home, "pull", "-q", "--ff-only", "origin", "main")
    print("up to date with the host")


def init(cfg, remote):
    home = home_of(cfg)
    ensure_repo(home, cfg)
    if git(home, "remote", check=False):
        git(home, "remote", "set-url", "origin", remote)
    else:
        git(home, "remote", "add", "origin", remote)
    cfg.update({"chat_history": "git-sync", "sync_remote": remote, "sync_role": "host"})
    save_cfg(cfg)
    commit(cfg, "Ask the Experts home: start syncing")


def clone(cfg, remote, folder):
    home = pathlib.Path(folder).expanduser() if folder else home_of(cfg)
    if home.exists() and any(home.iterdir()):
        sys.exit(f"{home} isn't empty. Move it aside first, or pass another folder.")
    home.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["git", "clone", "-q", remote, str(home)], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"clone failed: {r.stderr.strip()}")
    for d in ("chats", "personas", "persona-sources", "avatars"):
        (home / d).mkdir(exist_ok=True)
    cfg.update({"home_dir": str(home), "logs_dir": str(home / "chats"), "private_personas_dir": str(home / "personas"),
                "chat_history": "git-sync", "sync_remote": remote, "sync_role": cfg.get("sync_role", "copy")})
    save_cfg(cfg)
    print(f"cloned into {home} (sync_role: {cfg['sync_role']}). On the host, set sync_role to host.")


def status(cfg):
    home = home_of(cfg)
    print(f"home folder:  {home}")
    print(f"history:      {cfg.get('chat_history', 'none')}   role: {cfg.get('sync_role', '-')}   remote: {cfg.get('sync_remote', '-')}")
    if (home / ".git").exists():
        print(git(home, "status", "-sb", check=False))


def main():
    a = sys.argv[1:]
    if not a or a[0] not in ("status", "commit", "pull", "init", "clone"):
        sys.exit(__doc__)
    cfg = load_cfg()
    try:
        if a[0] == "status":
            status(cfg)
        elif a[0] == "commit":
            commit(cfg, " ".join(a[1:]))
        elif a[0] == "pull":
            pull(cfg)
        elif a[0] == "init":
            if len(a) < 2:
                sys.exit("init needs the remote URL of a PRIVATE repository")
            init(cfg, a[1])
        elif a[0] == "clone":
            if len(a) < 2:
                sys.exit("clone needs the remote URL")
            clone(cfg, a[1], a[2] if len(a) > 2 else None)
    except RuntimeError as e:
        sys.exit(f"sync problem: {e}")


if __name__ == "__main__":
    main()
