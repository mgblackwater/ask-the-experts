#!/usr/bin/env python3
"""Always-on moderator for an Ask the Experts host (an always-on PC, a home server).

Watches the app's inbox and, for each batch of events about one chat, runs Claude Code in
headless mode (`claude -p`) with the ask-the-experts instructions. Claude handles the events
and carries the chat on until it needs the user, then exits. One run at a time.

Usage:
  python3 -I headless_moderator.py [--once] [--dry-run]

Reads ~/.claude/ask-the-experts/config.json for the logs folder. Keeps its place in
<logs>/.moderator-state.json and writes <logs>/.moderator.log. Each chat keeps its own Claude
session (resumed with --resume), so the moderator remembers the conversation between events.

--once      handle whatever is waiting, then exit (for testing)
--dry-run   print the command it would run instead of running Claude
--logs-dir  watch another chats folder (testing)
"""
import argparse
import datetime
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import time

CONFIG = pathlib.Path.home() / ".claude" / "ask-the-experts" / "config.json"
INBOX = ".ask-the-experts-inbox.jsonl"
STATE = ".moderator-state.json"
LOG = ".moderator.log"
POLL_SECONDS = 2
SETTLE_SECONDS = 3          # wait this long after the last event before starting a run (batches quick clicks)
RUN_TIMEOUT = 45 * 60       # a long roundtable round can take a while
RETRY_DELAYS = [60, 300, 900]  # seconds before each retry of a failed run (e.g. sign-in or network trouble)
MODERATOR_ID = "host-" + (platform.node() or "pc").split(".")[0].lower()

# Tools the headless moderator may use without asking. It briefs thinkers (Agent), runs the
# plugin's scripts (python), reads dossiers and attachments, writes brief files, and looks
# things up for @Claude questions. It never needs to push, delete or change settings.
ALLOWED_TOOLS = [
    "Agent", "Read", "Write", "Edit", "Glob", "Grep", "WebSearch", "WebFetch", "Skill",
    "Bash(python3:*)", "Bash(python:*)", "Bash(py:*)", "Bash(git add:*)", "Bash(git commit:*)",
    "Bash(git -C:*)", "Bash(mkdir:*)", "Bash(ls:*)", "Bash(cat:*)",
]

SYSTEM = """You are the always-on moderator of the Ask the Experts app on this computer, running headless:
nobody is watching a terminal, and the user is in the app (often on a phone).
Follow the ask-the-experts skill (SKILL.md and references/roundtable.md) for everything: claiming tables,
briefs, speech checks, guardrails, @Claude answers, archetypes, direct chats, attachments, personas.
Headless rules:
- Handle the events you are given. Then keep the chat moving on your own judgement until it needs the user:
  a checkpoint card, a question to them, a finished chat, or simply their next message. Then stop.
- Never wait, poll, start a Monitor, open a browser or ask questions in this terminal. Anything for the user goes on the page.
- Use the moderator id you are given for every roundtable_log.py --claim.
- Keep your final reply to one line saying what you did."""


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def log(logs_dir, msg):
    line = f"{now()} {msg}"
    print(line, flush=True)
    with open(logs_dir / LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save_json(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def plugin_dir():
    """The newest installed ask-the-experts plugin version (survives plugin updates)."""
    base = pathlib.Path.home() / ".claude" / "plugins" / "cache"  # <marketplace>/ask-the-experts/<version>
    here = pathlib.Path(__file__).resolve().parents[1]
    versions = sorted((d for d in base.glob("*/ask-the-experts/*") if (d / "skills" / "ask" / "SKILL.md").is_file()),
                      key=lambda d: [int(x) if x.isdigit() else x for x in d.name.split(".")]) if base.is_dir() else []
    return versions[-1] / "skills" / "ask" if versions else here


def read_new_events(logs_dir, state):
    inbox = logs_dir / INBOX
    if not inbox.exists():
        return []
    size = inbox.stat().st_size
    pos = state.get("offset", size if "offset" not in state else 0)
    if "offset" not in state:          # first start: don't replay history
        state["offset"] = size
        return []
    if size < pos:                     # the inbox was replaced or emptied
        pos = 0
    events = []
    with open(inbox, "r", encoding="utf-8") as f:
        f.seek(pos)
        for line in f:
            if not line.endswith("\n"):
                break                  # a half-written line: read it next time
            pos += len(line.encode("utf-8"))
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except ValueError:
                    pass
    state["offset"] = pos
    return events


def run_claude(logs_dir, state, key, events, dry_run):
    """Run Claude for one chat's events. Returns True if it worked, False to retry later."""
    skill = plugin_dir()
    claude = shutil.which("claude")
    if not claude:
        log(logs_dir, "ERROR: the claude command isn't on PATH")
        return False
    session = state.setdefault("sessions", {}).get(key)
    prompt = (f"Moderator id: {MODERATOR_ID}\n"
              f"Skill folder: {skill}\n"
              f"Logs folder (chats): {logs_dir}\n"
              f"New app events (oldest first), as JSON:\n{json.dumps(events, ensure_ascii=False, indent=1)}\n\n"
              "Handle them now, following the ask-the-experts skill.")
    cmd = [claude, "-p", prompt, "--output-format", "json", "--append-system-prompt", SYSTEM,
           "--permission-mode", "acceptEdits", "--add-dir", str(skill), "--add-dir", str(logs_dir),
           "--allowedTools", *ALLOWED_TOOLS]
    if session:
        cmd += ["--resume", session]
    if dry_run:
        log(logs_dir, f"DRY RUN for {key}: {len(events)} event(s), resume={session or 'new'}")
        return True
    log(logs_dir, f"run for {key}: {len(events)} event(s) ({', '.join(e.get('kind', '?') for e in events)}), "
                  f"session {'resumed' if session else 'new'}")
    try:
        out = subprocess.run(cmd, cwd=str(logs_dir), capture_output=True, text=True, timeout=RUN_TIMEOUT,
                             encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        log(logs_dir, f"TIMEOUT after {RUN_TIMEOUT // 60} min for {key}")
        return True                     # it did work for 45 minutes; don't replay the same events
    try:
        result = json.loads(out.stdout)
    except ValueError:
        result = {"is_error": True, "result": (out.stderr or out.stdout)[-400:]}
    text = str(result.get("result", "")).strip()
    if result.get("is_error") or out.returncode != 0:
        log(logs_dir, f"ERROR for {key} (code {out.returncode}): {text[:300]}")
        if session and "session" in text.lower() and "not found" in text.lower():
            state["sessions"].pop(key, None)   # a stale session id: start fresh next time
        return False
    if result.get("session_id") and key != "_persona":
        state["sessions"][key] = result["session_id"]   # resume this chat's session next time
    log(logs_dir, f"done {key}: {text[:200]}")
    return True


def sync_home(logs_dir, key, events):
    """Commit (and, with git-sync on the host, push) the home folder after a run."""
    cfg = load_json(CONFIG, {})
    if cfg.get("chat_history") not in ("git", "git-sync") or cfg.get("sync_role", "host") != "host":
        return
    kinds = sorted({e.get("kind", "?") for e in events})
    msg = f"{'Persona' if key == '_persona' else key.replace('.json', '')}: {', '.join(kinds)}"
    script = pathlib.Path(__file__).resolve().parent / "home_sync.py"
    r = subprocess.run([sys.executable, "-I", str(script), "commit", msg], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    log(logs_dir, f"sync: {(r.stdout or r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr).strip() else 'ok'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--logs-dir", help="watch this chats folder instead of the config's (for testing)")
    args = ap.parse_args()
    cfg = load_json(CONFIG, {})
    if not (args.logs_dir or cfg.get("logs_dir")):
        sys.exit(f"No logs folder in {CONFIG}: run the skill's setup first")
    logs_dir = pathlib.Path(args.logs_dir or cfg["logs_dir"]).expanduser()
    state_path = logs_dir / STATE
    state = load_json(state_path, {})
    if args.once and "offset" not in state:
        state["offset"] = 0
    log(logs_dir, f"moderator {MODERATOR_ID} watching {logs_dir / INBOX} (plugin {plugin_dir().parent.parent.name})")
    pending, last_event = {}, 0.0
    retry = {}                          # key -> (attempts so far, earliest time to try again)
    while True:
        for e in read_new_events(logs_dir, state):
            key = e.get("transcript") or ("_persona" if e.get("kind") == "persona" else "_other")
            pending.setdefault(key, []).append(e)
            last_event = time.time()
        save_json(state_path, state)
        ready = [k for k in pending if time.time() >= retry.get(k, (0, 0))[1]]
        if ready and time.time() - last_event >= SETTLE_SECONDS:
            key = ready[0]
            events = pending.pop(key)
            if run_claude(logs_dir, state, key, events, args.dry_run):
                retry.pop(key, None)
                if not args.dry_run:
                    sync_home(logs_dir, key, events)
            else:
                attempts = retry.get(key, (0, 0))[0]
                if attempts < len(RETRY_DELAYS):
                    retry[key] = (attempts + 1, time.time() + RETRY_DELAYS[attempts])
                    pending[key] = events + pending.get(key, [])
                    log(logs_dir, f"will retry {key} in {RETRY_DELAYS[attempts] // 60} min")
                else:
                    retry.pop(key, None)
                    log(logs_dir, f"GAVE UP on {key} after {attempts + 1} tries; its events are in the log above")
            save_json(state_path, state)
            if args.once and key in pending:
                return                  # in a one-off test, report the failure instead of waiting
            continue                    # pick up anything that arrived during the run
        if args.once and not pending:
            return
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
