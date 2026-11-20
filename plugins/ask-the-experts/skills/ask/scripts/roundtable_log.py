#!/usr/bin/env python3
"""Update a live roundtable transcript: add turns, post questions, add people, say who's speaking.

Usage:
  python3 -I roundtable_log.py <transcript.json> [--claim MODERATOR [--take-over]] [--speaking ID | --speaking none]
                              [--clear-ask] [--finish] < items.json
  python3 -I roundtable_log.py <transcript.json> --claim MODERATOR --turn WHO [--check [DOSSIER]]
                              [--sketch SKETCH.svg] [--speaking NEXT | --speaking none] < turn.txt

One call per turn: --turn WHO reads the turn as plain text (no JSON), --check runs the speech check
first, and --speaking sets who's next. If the check flags anything, nothing is written: the flags
are printed and the script exits with status 1, so the turn can be sent back and rewritten.
There's no need to render the page after a turn: the app redraws it from the transcript.

stdin holds one object or a list of objects (may be empty). Each object is either
  - a transcript item: {"type": "turn" | "user" | "moderator" | "evidence" | "round" | "ai", ...}
    ("ai" is an answer from AI research to someone who tagged @AI: {"type": "ai", "text", "sources": [{text, url, src}],
    "replyTo": <index of the message it answers>}). Items get a "time" stamp if they have none.
  - {"type": "ask", "id": "cp1", "title": "...", "questions": [{"id", "q", "header", "multi", "options": [{"label", "desc"}]}]}
    shows a question card on the page (replaces any open one); the answer arrives in the inbox
  - {"type": "participant", "id": "...", "name": "...", "kind": "thinker" | "self", "lens": "...", "avatar": "<slug>"}
    adds someone to the table
  - {"type": "meta", "topic": "...", "title": "...", "aim": "debate|decide|truth|explore"} updates the header or the aim
--speaking ID   shows a "typing" bubble for that participant on the page ("claude": the host itself)
--drawing       with --speaking ID: show "<name> is drawing…" instead (cleared when their turn is posted)
--clear-ask     removes the open question card
--finish        marks the run finished (the page stops polling and shows "Finished")
--claim ID      only one Claude session may moderate a roundtable. Claims it for ID (your moderator id) if
                nobody holds it, you already hold it, or the holder has been silent for over an hour, and
                refreshes your heartbeat. If another session holds it, nothing is written and the script
                exits with status 3: leave that roundtable alone. Pass --claim on every call.
--take-over     with --claim: take the roundtable even from an active holder. Only when the user asks.
--turn WHO      stdin is the text of one turn by participant WHO (instead of JSON items).
--check [DOSSIER]  speech-check every turn being posted (with DOSSIER: also copied runs from it);
                post nothing and exit 1 if anything is flagged.
--sketch FILE   with --turn: attach a whiteboard sketch (an SVG file) to the turn. Only plain drawing is
                allowed (shapes, text, a roughening filter, markers): no scripts, event handlers,
                external links, images or embedded HTML, at most 40 KB. A sketch that breaks the rules
                is refused (exit 1, nothing written) with the reason.

Locks the transcript, because roundtable_server.py writes the user's messages to it too.
"""
import datetime
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # -I leaves the script's folder off sys.path
from filelock import lock as lock_file, unlock as unlock_file  # noqa: E402

STALE = datetime.timedelta(hours=1)  # a holder silent this long has gone away (a card can wait a while)
CLAIMED = 3                          # exit status: another session moderates this roundtable
FLAGGED = 1                          # exit status: --check flagged a turn; nothing was written

SKETCH_MAX = 40_000                  # bytes: a whiteboard sketch, not an illustration
SKETCH_TAGS = {"svg", "g", "title", "desc", "defs", "filter", "feTurbulence", "feDisplacementMap",
               "marker", "path", "line", "polyline", "polygon", "rect", "circle", "ellipse", "text", "tspan", "use"}


def check_sketch(svg):
    """Return a reason if the SVG isn't a plain drawing, else None. The page also shows sketches as
    images (which can't run scripts or load anything), so this is a second, stricter line."""
    if len(svg.encode("utf-8")) > SKETCH_MAX:
        return f"too big ({len(svg.encode('utf-8')) // 1000} KB, max {SKETCH_MAX // 1000}): draw fewer, simpler shapes"
    if re.search(r"<!(DOCTYPE|ENTITY)", svg, re.I):
        return "no DOCTYPE or ENTITY declarations"
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as e:
        return f"not well-formed SVG: {e}"
    for node in root.iter():
        tag = node.tag.split("}")[-1]
        if node is root and tag != "svg":
            return "the sketch must be one <svg> element"
        if tag not in SKETCH_TAGS:
            return f"<{tag}> isn't allowed: use shapes, text and the roughening filter only"
        for name, value in node.attrib.items():
            attr = name.split("}")[-1].lower()
            if attr.startswith("on"):
                return f"event handler {attr} isn't allowed"
            if attr == "href" and not value.startswith("#"):
                return "links may only point inside the sketch (#id)"
            if "url(" in value.replace(" ", "") and not re.fullmatch(r"\s*url\(\s*#[\w-]+\s*\)\s*", value):
                return f"{attr}: url() may only point inside the sketch (#id)"
            if re.search(r"javascript:|data:|@import|expression\(", value, re.I):
                return f"{attr} has a value that isn't allowed"
    if not any(child.tag.split("}")[-1] == "title" and (child.text or "").strip() for child in root):
        return "add a <title> saying what the sketch shows (it's the picture's description)"
    return None


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
    # Read bytes and decode as UTF-8: on Windows sys.stdin uses the ANSI code page (cp1252).
    raw = sys.stdin.buffer.read().decode("utf-8-sig").strip() if not sys.stdin.isatty() else ""
    if "--turn" in argv:
        if not raw:
            sys.exit("--turn needs the turn's text on stdin")
        new = [{"type": "turn", "who": argv[argv.index("--turn") + 1], "text": raw}]
        if "--sketch" in argv:
            svg = pathlib.Path(argv[argv.index("--sketch") + 1]).read_text(encoding="utf-8-sig").strip()
            reason = check_sketch(svg)
            if reason:
                print(f"Not posted. The sketch was refused: {reason}")
                sys.exit(FLAGGED)
            new[0]["sketch"] = svg
    else:
        new = json.loads(raw) if raw else []
        new = new if isinstance(new, list) else [new]
    if "--check" in argv:
        from speech_check import check   # noqa: E402  (same folder)
        i = argv.index("--check") + 1
        dossier = argv[i] if i < len(argv) and not argv[i].startswith("--") else None
        flags = [f for obj in new if obj.get("type") == "turn" for f in check(obj.get("text", ""), dossier)]
        if flags:
            print("Not posted. The speech check flagged:\n" + "\n".join("- " + f for f in flags))
            sys.exit(FLAGGED)
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
                    data.pop("drawing", None)
        if "--speaking" in argv:
            who = argv[argv.index("--speaking") + 1]
            data.pop("speaking", None) if who == "none" else data.__setitem__("speaking", who)
            if "--drawing" in argv and who != "none":
                data["drawing"] = True   # the page says "<name> is drawing…" instead of typing
            else:
                data.pop("drawing", None)
        if "--clear-ask" in argv:
            data.pop("ask", None)
        if "--finish" in argv:
            data["live"] = False
            for k in ("speaking", "drawing", "ask", "paused"):
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
