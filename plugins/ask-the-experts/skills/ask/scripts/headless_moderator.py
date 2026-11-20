#!/usr/bin/env python3
"""Always-on moderator for an Ask the Experts host (an always-on PC, a home server).

Watches the app's inbox and, for each batch of events about one chat, hands them to Claude Code
in headless mode (`claude -p`) with the ask-the-experts instructions. Claude handles the events
and carries the chat on until it needs the user. One turn at a time.

Each chat keeps one Claude process open between messages (stream-json input), so a follow-up
starts at once instead of reloading Claude Code. A chat idle for IDLE_CLOSE, or beyond MAX_WARM
open chats, is closed; its session is kept and resumed (--resume) on the next message.
Claude starts lean: only this plugin, no other plugins, MCP servers, hooks or user CLAUDE.md
(set "moderator_lean": false in the settings to load everything). The model is the settings'
"moderator_model", else the "model" in ~/.claude/settings.json.

Usage:
  python3 -I headless_moderator.py [--once] [--dry-run]

Reads ~/.claude/ask-the-experts/config.json for the logs folder. Keeps its place in
<logs>/.moderator-state.json and writes <logs>/.moderator.log.

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
import queue
import shutil
import subprocess
import sys
import threading
import time

CONFIG = pathlib.Path.home() / ".claude" / "ask-the-experts" / "config.json"
USER_SETTINGS = pathlib.Path.home() / ".claude" / "settings.json"
IDLE_CLOSE = 30 * 60        # close a chat's Claude process after this long without a message
MAX_WARM = 4                # at most this many chats keep a Claude process open
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
- Be quick: the user is waiting in a chat. Post each turn with one roundtable_log.py call
  (--claim, --turn <id>, --check <dossier>, --speaking <next|none>, the text on stdin). Don't render the
  page (the app redraws it), and don't re-read the skill or a dossier you already read in this session.
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


class ClaudeSession:
    """One Claude Code process for one chat, kept open between messages (stream-json in and out)."""

    def __init__(self, cmd, cwd):
        self.proc = subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
        self.lines = queue.Queue()
        self.stderr = []
        self.last_used = time.time()
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def _read_stdout(self):
        for line in self.proc.stdout:
            self.lines.put(line)
        self.lines.put(None)            # end of output: the process has ended

    def _read_stderr(self):
        for line in self.proc.stderr:
            self.stderr = (self.stderr + [line])[-20:]

    def alive(self):
        return self.proc.poll() is None

    def turn(self, prompt, timeout):
        """Send one message; return Claude's result for it (a dict), or None on timeout."""
        self.last_used = time.time()
        msg = {"type": "user", "message": {"role": "user", "content": prompt}}
        try:
            self.proc.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
            self.proc.stdin.flush()
        except OSError:
            return {"is_error": True, "result": "the Claude process had ended: " + "".join(self.stderr)[-300:]}
        deadline = time.time() + timeout
        while True:
            try:
                line = self.lines.get(timeout=max(0.1, deadline - time.time()))
            except queue.Empty:
                return None
            if line is None:            # the process ended without a result
                self.proc.wait()
                return {"is_error": True, "result": f"Claude exited (code {self.proc.returncode}): "
                                                    + "".join(self.stderr)[-300:]}
            try:
                m = json.loads(line)
            except ValueError:
                continue
            if m.get("type") == "result":
                self.last_used = time.time()
                return m

    def close(self, wait=10):
        try:
            self.proc.stdin.close()     # ends the conversation; Claude exits on its own
            self.proc.wait(timeout=wait)
        except (OSError, subprocess.TimeoutExpired):
            self.proc.kill()


WARM = {}   # chat key -> ClaudeSession


def close_idle(logs_dir, keep=None):
    """Close chats idle too long, and the least recently used beyond MAX_WARM."""
    for key, s in list(WARM.items()):
        if not s.alive() or time.time() - s.last_used > IDLE_CLOSE:
            WARM.pop(key).close()
            log(logs_dir, f"closed {key} (idle)")
    while len(WARM) > MAX_WARM:
        key = min((k for k in WARM if k != keep), key=lambda k: WARM[k].last_used)
        WARM.pop(key).close()
        log(logs_dir, f"closed {key} (too many open chats)")


def claude_cmd(claude, skill, logs_dir, session):
    cfg = load_json(CONFIG, {})
    cmd = [claude, "-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
           "--append-system-prompt", SYSTEM, "--permission-mode", "acceptEdits",
           "--add-dir", str(skill), "--add-dir", str(logs_dir), "--allowedTools", *ALLOWED_TOOLS]
    if cfg.get("moderator_lean", True):
        # Only this plugin: skip the user's other plugins, MCP servers, hooks and CLAUDE.md. Much faster to
        # start and to answer, and nothing else in the user's setup steers the moderator.
        cmd += ["--setting-sources", "project,local", "--strict-mcp-config", "--plugin-dir", str(skill.parent.parent)]
    model = cfg.get("moderator_model") or load_json(USER_SETTINGS, {}).get("model")
    if model:
        cmd += ["--model", model]
    if session:
        cmd += ["--resume", session]
    return cmd


def run_claude(logs_dir, state, key, events, dry_run):
    """Hand one chat's events to Claude. Returns True if it worked, False to retry later."""
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
    one_off = key == "_persona"          # persona builds get a fresh session each
    warm = WARM.get(key)
    if warm and not warm.alive():
        WARM.pop(key, None)
        warm = None
    how = "warm" if warm else ("resumed" if session and not one_off else "new")
    if dry_run:
        log(logs_dir, f"DRY RUN for {key}: {len(events)} event(s), session {how}")
        return True
    log(logs_dir, f"run for {key}: {len(events)} event(s) ({', '.join(e.get('kind', '?') for e in events)}), "
                  f"session {how}")
    if not warm:
        warm = ClaudeSession(claude_cmd(claude, skill, logs_dir, None if one_off else session), str(logs_dir))
        if not one_off:
            WARM[key] = warm
            close_idle(logs_dir, keep=key)
    started = time.time()
    result = warm.turn(prompt, RUN_TIMEOUT)
    if one_off:
        warm.close()
    if result is None:
        log(logs_dir, f"TIMEOUT after {RUN_TIMEOUT // 60} min for {key}")
        WARM.pop(key, None)
        warm.close(wait=0)
        return True                     # it did work for 45 minutes; don't replay the same events
    text = str(result.get("result", "")).strip()
    if result.get("is_error"):
        log(logs_dir, f"ERROR for {key}: {text[:300]}")
        if WARM.get(key) is warm:
            WARM.pop(key).close(wait=0)  # start clean next time
        if session and "session" in text.lower() and "not found" in text.lower():
            state["sessions"].pop(key, None)   # a stale session id: start fresh next time
        return False
    if result.get("session_id") and not one_off:
        state["sessions"][key] = result["session_id"]   # resume this chat's session after a restart
    log(logs_dir, f"done {key} in {time.time() - started:.0f}s: {text[:200]}")
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
    try:
        watch(args, logs_dir, state, state_path)
    finally:
        for s in WARM.values():
            s.close()


def watch(args, logs_dir, state, state_path):
    pending, last_event = {}, 0.0
    retry = {}                          # key -> (attempts so far, earliest time to try again)
    while True:
        close_idle(logs_dir)
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
