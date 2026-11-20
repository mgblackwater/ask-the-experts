#!/usr/bin/env python3
"""Update a live roundtable transcript: add turns, post questions, add people, say who's speaking.

Usage:
  python3 -I roundtable_log.py <transcript.json> [--claim MODERATOR [--take-over]] [--speaking ID | --speaking none]
                              [--clear-ask] [--finish] < items.json

stdin holds one object or a list of objects (may be empty). Each object is either
  - a transcript item: {"type": "turn" | "user" | "moderator" | "evidence" | "round" | "ai", ...}
    ("ai" is an answer from AI research to someone who tagged @AI: {"type": "ai", "text", "sources": [{text, url, src}],
    "replyTo": <index of the message it answers>}). Items get a "time" stamp if they have none.
  - {"type": "ask", "id": "cp1", "title": "...", "questions": [{"id", "q", "header", "multi", "options": [{"label", "desc"}]}]}
    shows a question card on the page (replaces any open one); the answer arrives in the inbox
  - {"type": "participant", "id": "...", "name": "...", "kind": "thinker" | "self", "lens": "...", "avatar": "<slug>"}
    adds someone to the table
  - {"type": "meta", "topic": "...", "title": "...", "aim": "debate|decide|truth|explore"} updates the header or the aim
--speaking ID   shows a "typing" bubble for that participant on the page
--clear-ask     removes the open question card
--finish        marks the run finished (the page stops polling and shows "Finished")
--claim ID      only one Claude session may moderate a roundtable. Claims it for ID (your moderator id) if
                nobody holds it, you already hold it, or the holder has been silent for over an hour, and
                refreshes your heartbeat. If another session holds it, nothing is written and the script
                exits with status 3: leave that roundtable alone. Pass --claim on every call.
--take-over     with --claim: take the roundtable even from an active holder. Only when the user asks.

Locks the transcript, because roundtable_server.py writes the user's messages to it too.
"""
import datetime
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # -I leaves the script's folder off sys.path
from filelock import lock as lock_file, unlock as unlock_file  # noqa: E402

STALE = datetime.timedelta(hours=1)  # a holder silent this long has gone away (a card can wait a while)
CLAIMED = 3                          # exit status: another session moderates this roundtable


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def claim(data, me, take_over):
    """Return None if `me` may moderate (and record the claim), or a message naming the holder."""
    mod = data.get("moderator") or {}
    holder = mod.get("session")
    if holder and holder != me and not take_over:
        try:
            idle = now() - datetime.datetime.fromisoformat(mod.get("heartbeat", ""))
        except ValueError:
            idle = STALE
        if idle < STALE:
            mins = int(idle.total_seconds() // 60)
            return f"moderated by {holder} (active {mins} min ago); leave it alone, or ask the user before --take-over"
    data["moderator"] = {"session": me, "heartbeat": now().isoformat(timespec="seconds")}
    if holder and holder != me:
        print(f"took over from {holder}", file=sys.stderr)
    return None


def main():
    argv = sys.argv[1:]
    if not argv:
        sys.exit(__doc__)
    path = pathlib.Path(argv[0])
    raw = sys.stdin.read().strip() if not sys.stdin.isatty() else ""
    new = json.loads(raw) if raw else []
    new = new if isinstance(new, list) else [new]
    with open(path, "r+", encoding="utf-8") as f:
        lock_file(f)
        data = json.load(f)
        if "--claim" in argv:
            refusal = claim(data, argv[argv.index("--claim") + 1], "--take-over" in argv)
            if refusal:
                print(f"{path.name}: {refusal}", file=sys.stderr)
                sys.exit(CLAIMED)
        parts = data.setdefault("participants", [])
        for obj in new:
            kind = obj.get("type")
            if kind == "ask":
                data["ask"] = {k: v for k, v in obj.items() if k != "type"}
            elif kind == "participant":
                p = {k: v for k, v in obj.items() if k != "type"}
                if not any(x.get("id") == p.get("id") for x in parts):
                    parts.insert(max(0, len(parts) - 1), p)  # keep the user last
            elif kind == "meta":
                for k in ("topic", "title", "aim"):
                    if obj.get(k):
                        data[k] = obj[k]
            else:
                if kind == "turn" and obj.get("who") not in {x.get("id") for x in parts}:
                    sys.exit(f"Unknown participant {obj.get('who')!r}; add them first")
                obj.setdefault("time", now().isoformat(timespec="seconds"))
                data.setdefault("items", []).append(obj)
                if kind == "turn":
                    data.pop("note", None)  # the "getting ready" notice ends when someone speaks
        if "--speaking" in argv:
            who = argv[argv.index("--speaking") + 1]
            data.pop("speaking", None) if who == "none" else data.__setitem__("speaking", who)
        if "--clear-ask" in argv:
            data.pop("ask", None)
        if "--finish" in argv:
            data["live"] = False
            for k in ("speaking", "ask", "paused"):
                data.pop(k, None)
        else:
            data.setdefault("live", True)
        f.seek(0)
        f.truncate()
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.flush()  # data must be on disk before anyone else gets the lock
        unlock_file(f)
    print(f"{path.name}: {len(data.get('items', []))} items, speaking={data.get('speaking')}, "
          f"ask={'open' if data.get('ask') else 'none'}, live={data.get('live')}, "
          f"moderator={(data.get('moderator') or {}).get('session')}")


if __name__ == "__main__":
    main()
