#!/usr/bin/env python3
"""Render a roundtable transcript (JSON) into the chat-style HTML template.

Usage: python3 -I render_roundtable.py <transcript.json> <out.html> [--live]

--live   The page polls the transcript JSON every few seconds and appends new
         turns as they land (serve it with roundtable_server.py). Re-render
         without --live when the run ends, for a static copy that opens anywhere.

The JSON shape is documented in references/roundtable.md ("Chat page").
"""
import json
import os
import pathlib
import re
import sys

TEMPLATE = pathlib.Path(__file__).resolve().parent.parent / "assets" / "roundtable.html"
BLOCK = re.compile(
    r'(<script type="application/json" id="roundtable-data">)(.*?)(</script>)', re.S
)
KINDS = {"thinker", "self", "user", "moderator", "researcher"}
TYPES = {"round", "turn", "user", "moderator", "evidence", "ai"}


def validate(data):
    errors = []
    ids = set()
    for p in data.get("participants", []):
        if p.get("kind") not in KINDS:
            errors.append(f"participant {p.get('id')!r}: kind must be one of {sorted(KINDS)}")
        ids.add(p.get("id"))
    for i, it in enumerate(data.get("items", [])):
        if it.get("type") not in TYPES:
            errors.append(f"item {i}: type must be one of {sorted(TYPES)}")
        if it.get("type") == "turn" and it.get("who") not in ids:
            errors.append(f"item {i}: turn by unknown participant {it.get('who')!r}")
    return errors


def render(src, out, live=False):
    """Render transcript `src` to page `out`. Returns a one-line summary; raises ValueError if invalid."""
    src, out = pathlib.Path(src), pathlib.Path(out)
    data = json.loads(src.read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        raise ValueError("Invalid transcript:\n  " + "\n  ".join(errors))
    data["transcript"] = src.name  # lets a served copy of a finished chat pick the conversation up again
    if live:
        data["live"] = os.path.relpath(src.resolve(), out.resolve().parent)
    else:
        for key in ("live", "speaking", "drawing", "ask", "note"):
            data.pop(key, None)
    # Escape so the JSON can't close the <script> element early.
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8")
    html, n = BLOCK.subn(lambda m: m.group(1) + payload + m.group(3), html, count=1)
    if n != 1:
        raise ValueError("Template data block not found")
    out.write_text(html, encoding="utf-8")
    turns = sum(1 for it in data.get("items", []) if it.get("type") == "turn")
    mode = " (live: polls " + data["live"] + ")" if live else ""
    return f"Wrote {out} ({turns} turns, {len(data.get('items', []))} items){mode}"


def main():
    args = [a for a in sys.argv[1:] if a != "--live"]
    if len(args) != 2:
        sys.exit(__doc__)
    try:
        print(render(args[0], args[1], "--live" in sys.argv[1:]))
    except ValueError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
