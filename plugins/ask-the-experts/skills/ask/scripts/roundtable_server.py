#!/usr/bin/env python3
"""The Ask the Experts app: a local server for the start screen and chat pages.

Usage: python3 -I roundtable_server.py [--dir <logs folder>] [--port 8766] [--public-only]

Reads ~/.claude/ask-the-experts/config.json (written by the skill's setup) for the logs
folder, the private personas folder and the port. Listens on 127.0.0.1 only.

One server serves every Claude session. If something already answers /api/ping on the port, this
script says so and exits 0 instead of starting a second one; it never stops a running server.

  GET  /                      start screen (assets/lobby.html)
  GET  /avatars/<slug>.svg    drawn avatars (private folder first, then the plugin's)
  GET  /<file>                chat pages and transcripts in the logs folder
  GET  /api/ping              {"ok": true, "user", "version", "pid"}
  GET  /api/roster            every persona: slug, name, lens, good_for, group, self, avatar
  GET  /api/roundtables       every chat in the logs folder, newest first, with its last message
  POST /api/new               start a chat: {topic, people:[slug], context, claudePicks, aim}. One person and no
                              Claude picks makes a direct chat (mode "direct"), where topic is your first message;
                              otherwise a group roundtable (mode "group")
  POST /api/persona           ask Claude to build a persona: {name, kind: "public" | "custom", description, files:[{name, data}]}.
                              public = research a well-known figure's public record; custom = from your material only
  POST /api/archive           {transcript, archived: true | false}; archived chats leave the main list
  POST /api/add               add people to a chat: {transcript, people:[slug]}; a direct chat becomes a group
  POST /api/say               {transcript, text, replyTo, to:[participant id | "ai"], files:[{name, data (base64)}]}  (to = the people tagged with @).
                              Writing in a finished chat picks it up again (the event has "reopened": true)
  POST /api/edit              {transcript, index, text}  (self-persona turns only)
  POST /api/answer            {transcript, askId, answers:[{qid, choices:[label], other}]}
  POST /api/control           {transcript, action: "pause" | "resume" | "wrap"}

Everything the user does is appended, one JSON line per event, to
<logs folder>/.ask-the-experts-inbox.jsonl. The moderator (Claude) watches that file.
"""
import argparse
import base64
import datetime
import functools
import http.server
import json
import os
import pathlib
import re
import sys
import urllib.request

SKILL = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))
from filelock import lock as lock_file, unlock as unlock_file  # noqa: E402
from render_roundtable import TEMPLATE, render  # noqa: E402

CONFIG = pathlib.Path.home() / ".claude" / "ask-the-experts" / "config.json"
INBOX = ".ask-the-experts-inbox.jsonl"
NAME = re.compile(r"^[A-Za-z0-9._-]+\.json$")
SLUG = re.compile(r"^[a-z0-9-]+$")
MAX_TEXT = 4000
# Attachments: images and documents sent with a message, saved next to the chat in <logs>/attachments/.
ATTACH_TYPES = {"png", "jpg", "jpeg", "gif", "webp", "pdf", "txt", "md", "csv", "json", "docx", "xlsx", "pptx"}
MAX_FILE = 10 * 1024 * 1024
MAX_FILES = 5
MAX_UPLOAD_BODY = 72 * 1024 * 1024  # five files of 10 MB each, base64-encoded, plus the message


def host_name(cfg):
    """What the moderator is called in the chat: config "host_name", default "Claude"."""
    return str(cfg.get("host_name") or "Claude")[:40]


def person_entry(p):
    return {"id": p["slug"], "name": p["name"], "kind": "self" if p["self"] else "thinker",
            "lens": p["lens"][:90], "avatar": p["slug"] if p["avatar"] else None}


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def plugin_version():
    try:
        meta = pathlib.Path(__file__).resolve().parents[3] / ".claude-plugin" / "plugin.json"
        return json.loads(meta.read_text(encoding="utf-8")).get("version", "")
    except (OSError, ValueError, IndexError):
        return ""


VERSION = plugin_version()


def running(port):
    """The ping answer of a server already on this port, or None."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ping", timeout=2) as r:
            return json.loads(r.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
# What the discussion is for; it changes how the moderator steers and ends it (see references/roundtable.md).
AIMS = {
    "debate": ("Debate", "sharpen the disagreements; nobody has to agree."),
    "decide": ("Reach a decision", "converge on one answer and the first step."),
    "truth": ("Find the hidden truth", "test each explanation against evidence and drop the ones that are just stories."),
    "explore": ("Explore", "open up angles nobody has raised yet."),
}
GROUPS = {
    "Product & strategy": "product strategy design platform branding".split(),
    "Engineering & learning": "engineering cost speed operations debugging learning explaining".split(),
    "People & leadership": "leadership teams hiring culture management".split(),
    "Decisions, risk & money": "decisions forecasting risk investing money negotiation persuasion".split(),
}


PUBLIC_ONLY = False  # --public-only: ignore the user's private personas and name (for demos and screenshots)


def load_config():
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    if PUBLIC_ONLY:
        cfg = {k: v for k, v in cfg.items() if k not in ("private_personas_dir", "user_name")}
        cfg["private_personas_dir"] = "/nonexistent"
    return cfg


def frontmatter(path):
    """Parse the simple `key: value` / `key: [a, b]` frontmatter of a persona dossier."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    block = text.split("---", 2)[1]
    out = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            val = [v.strip().strip('"') for v in val[1:-1].split(",") if v.strip()]
        out[key.strip()] = val
    return out


def group_of(tags):
    scores = {g: sum(t in words for t in tags) for g, words in GROUPS.items()}
    first = next((g for t in tags for g, words in GROUPS.items() if t in words), None)
    best = max(GROUPS, key=lambda g: (scores[g], g == first))
    return best


def roster(cfg):
    dirs = [SKILL / "personas"]
    if cfg.get("private_personas_dir"):
        dirs.append(pathlib.Path(cfg["private_personas_dir"]).expanduser())
    people = {}  # slug -> person; the private folder comes last, so its newer copies win
    for d in dirs:
        for f in sorted(d.glob("*.md")) if d.is_dir() else []:
            fm = frontmatter(f)
            slug = fm.get("slug") or f.stem
            if not SLUG.match(slug):
                continue
            tags = fm.get("good_for") or []
            is_self = "self-persona" in str(fm.get("status", ""))
            is_custom = "custom persona" in str(fm.get("status", ""))
            is_archetype = str(fm.get("status", "")).startswith("archetype")
            people[slug] = {
                "slug": slug, "name": fm.get("name", slug), "lens": fm.get("lens", ""),
                "good_for": tags, "group": "Your people" if is_custom else "Roles" if is_archetype else group_of(tags),
                "self": is_self, "custom": is_custom, "archetype": is_archetype,
                "status": fm.get("status", ""), "researched": fm.get("researched", ""),
                "avatar": avatar_path(cfg, slug) is not None,
            }
    return sorted(people.values(), key=lambda p: p["name"])


def avatar_path(cfg, slug):
    for d in (pathlib.Path(cfg.get("private_personas_dir", "~/.claude/ask-the-experts/personas")).expanduser().parent / "avatars",
              SKILL / "assets" / "avatars"):
        for ext in ("svg", "png", "jpg"):
            p = d / f"{slug}.{ext}"
            if p.is_file():
                return p
    return None


def locked_update(path, fn):
    """Read-modify-write a transcript under an exclusive lock (roundtable_log.py uses the same lock)."""
    with open(path, "r+", encoding="utf-8") as f:
        lock_file(f)
        try:
            data = json.load(f)
            result = fn(data)
            f.seek(0)
            f.truncate()
            json.dump(data, f, ensure_ascii=False, indent=1)
            return result
        finally:
            f.flush()  # data must be on disk before anyone else gets the lock
            unlock_file(f)


def slugify(text, root):
    words = re.findall(r"[a-z0-9]+", text.lower())[:6] or ["roundtable"]
    base = "roundtable-" + "-".join(words)
    name, n = base, 2
    while (root / f"{name}.json").exists():
        name, n = f"{base}-{n}", n + 1
    return name


class App(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    # -- helpers -------------------------------------------------------------
    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path, ctype):
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read(self):
        n = int(self.headers.get("Content-Length", "0"))
        limit = MAX_UPLOAD_BODY if self.path.split("?")[0] in ("/api/say", "/api/persona") else 40000
        if n <= 0 or n > limit:
            raise ValueError("too large" if n > limit else "bad length")
        return json.loads(self.rfile.read(n))

    def _transcript(self, req):
        name = str(req.get("transcript", ""))
        if not NAME.match(name):
            raise ValueError("bad transcript name")
        path = self.server.root / name
        if not path.is_file():
            raise ValueError("unknown transcript")
        return name, path

    def _event(self, event):
        event["time"] = datetime.datetime.now().isoformat(timespec="seconds")
        with open(self.server.root / INBOX, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def end_headers(self):
        if self.path.split("?")[0].endswith((".json", ".html")):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    # -- GET -----------------------------------------------------------------
    def do_GET(self):
        route = self.path.split("?")[0]
        cfg = load_config()
        if route in ("/", "/index.html"):
            return self._file(SKILL / "assets" / "lobby.html", "text/html; charset=utf-8")
        if route in ("/manifest.webmanifest", "/app-icon-180.png", "/app-icon-512.png"):
            ctype = "application/manifest+json" if route.endswith(".webmanifest") else "image/png"
            return self._file(SKILL / "assets" / route[1:], ctype)
        if route.startswith("/avatars/"):
            slug = route[len("/avatars/"):].rsplit(".", 1)[0]
            p = avatar_path(cfg, slug) if SLUG.match(slug) else None
            if not p:
                return self._json(404, {"error": "no avatar"})
            ctype = {"svg": "image/svg+xml", "png": "image/png", "jpg": "image/jpeg"}[p.suffix[1:]]
            return self._file(p, ctype)
        if route == "/api/ping":
            return self._json(200, {"ok": True, "user": cfg.get("user_name", ""), "version": VERSION, "pid": os.getpid()})
        if route == "/api/roster":
            return self._json(200, {"people": roster(cfg), "groups": list(GROUPS)})
        if route == "/api/roundtables":
            out = []
            for f in self.server.root.glob("*.json"):
                try:
                    d = json.loads(f.read_text(encoding="utf-8"))
                except ValueError:
                    continue
                if "items" not in d:
                    continue
                seated = {p.get("id"): p.get("name") for p in d.get("participants", [])}
                last = next((i for i in reversed(d["items"]) if i.get("type") in ("turn", "user", "ai")), None)
                last_out = None
                if last:
                    who = ("You" if last["type"] == "user" else "AI research" if last["type"] == "ai"
                           else seated.get(last.get("who"), ""))
                    last_out = {"who": who, "text": str(last.get("text", ""))[:140], "time": last.get("time", "")}
                out.append({
                    "transcript": f.name, "page": f.with_suffix(".html").name, "mode": d.get("mode", "group"),
                    "last": last_out, "slugs": [p.get("id") for p in d.get("participants", [])
                                                if p.get("kind") in ("thinker", "self")],
                    "title": d.get("title", f.stem), "topic": d.get("topic", ""), "date": d.get("date", ""),
                    "live": bool(d.get("live")), "archived": bool(d.get("archived")),
                    "turns": sum(1 for i in d["items"] if i.get("type") == "turn"),
                    "people": [p.get("name") for p in d.get("participants", []) if p.get("kind") in ("thinker", "self")],
                    "avatars": [p.get("avatar") if p.get("avatar") and avatar_path(cfg, p["avatar"]) else None
                                for p in d.get("participants", []) if p.get("kind") in ("thinker", "self")],
                    "mtime": f.stat().st_mtime,
                })
            out.sort(key=lambda r: r["mtime"], reverse=True)
            return self._json(200, {"roundtables": out})
        if any(part.startswith(".") for part in route.split("/")):
            return self._json(404, {"error": "not found"})
        self._refresh_page(route)
        return super().do_GET()

    def _refresh_page(self, route):
        """Render a chat page from its transcript when the page is missing, older than its transcript or
        than the page template (a plugin update), or predates the "transcript" field that lets a finished
        chat be picked up again."""
        name = route.rsplit("/", 1)[-1]
        if not (name.startswith("roundtable-") and name.endswith(".html")) or not NAME.match(name[:-5] + ".json"):
            return
        page, src = self.server.root / name, self.server.root / (name[:-5] + ".json")
        if not src.is_file():
            return
        try:
            stale = (not page.is_file() or max(src.stat().st_mtime, TEMPLATE.stat().st_mtime) > page.stat().st_mtime
                     or '"transcript"' not in page.read_text(encoding="utf-8"))
            if stale:
                live = bool(json.loads(src.read_text(encoding="utf-8")).get("live"))
                render(src, page, live=live)
        except (OSError, ValueError):
            pass

    # -- POST ----------------------------------------------------------------
    def do_POST(self):
        route = self.path.split("?")[0]
        handlers = {"/api/new": self.post_new, "/api/add": self.post_add, "/api/persona": self.post_persona,
                    "/api/archive": self.post_archive, "/api/say": self.post_say, "/api/edit": self.post_edit,
                    "/api/answer": self.post_answer, "/api/control": self.post_control}
        if route not in handlers:
            return self._json(404, {"error": "not found"})
        try:
            return handlers[route](self._read())
        except (ValueError, TypeError, KeyError) as e:
            return self._json(400, {"error": str(e)})

    def post_new(self, req):
        cfg = load_config()
        topic = str(req.get("topic", "")).strip()
        context = str(req.get("context", "")).strip()
        picks = [str(s) for s in (req.get("people") or [])]
        claude_picks = bool(req.get("claudePicks"))
        aim = str(req.get("aim") or "debate")
        if aim not in AIMS:
            raise ValueError("unknown aim")
        if not topic or len(topic) > 600 or len(context) > MAX_TEXT:
            raise ValueError("a topic (up to 600 characters) is required")
        people = {p["slug"]: p for p in roster(cfg)}
        if any(s not in people for s in picks) or len(picks) > 8:
            raise ValueError("unknown or too many people")
        if not picks and not claude_picks:
            raise ValueError("pick at least one thinker, or let Claude pick")
        mode = "direct" if len(picks) == 1 and not claude_picks else "group"
        user_name = cfg.get("user_name") or "You"
        parts = [person_entry(people[s]) for s in picks]
        parts.append({"id": "you", "name": f"{user_name} (you)" if user_name != "You" else "You", "kind": "user"})
        names = [p["name"] for p in parts if p["kind"] != "user"]
        root = self.server.root
        if mode == "direct":
            items = []
            if context:
                items.append({"type": "user", "label": "What's going on", "text": context, "time": now_iso()})
            items.append({"type": "user", "label": "You", "text": topic, "from": "page", "time": now_iso()})
            name = slugify("chat " + names[0] + " " + topic, root)
            data = {"title": names[0], "topic": "Direct chat", "mode": "direct", "host": host_name(cfg),
                    "date": datetime.date.today().isoformat(), "participants": parts, "items": items,
                    "live": True, "speaking": None,
                    "note": f"Claude is reading {names[0]}'s dossier. The reply will appear here shortly."}
        else:
            items = [{"type": "moderator", "label": "The question", "text": topic},
                     {"type": "moderator", "label": "Aim", "text": f"{AIMS[aim][0]}: {AIMS[aim][1]}"}]
            if context:
                items.append({"type": "user", "label": "What you told the table", "text": context})
            name = slugify(topic, root)
            data = {"title": topic if len(topic) <= 90 else topic[:87] + "…",
                    "topic": "Roundtable with " + (", ".join(names) if names else "thinkers Claude will pick"),
                    "mode": "group", "host": host_name(cfg), "date": datetime.date.today().isoformat(), "participants": parts, "items": items,
                    "live": True, "speaking": None, "aim": aim,
                    "note": "Claude is reading the dossiers and briefing the table. The first speaker will appear here shortly."}
        (root / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        render(root / f"{name}.json", root / f"{name}.html", live=True)
        self._event({"kind": "new", "transcript": f"{name}.json", "mode": mode, "topic": topic, "context": context,
                     "people": picks, "claudePicks": claude_picks, "aim": aim if mode == "group" else None})
        return self._json(200, {"ok": True, "transcript": f"{name}.json", "page": f"{name}.html"})

    def post_archive(self, req):
        name, path = self._transcript(req)
        archived = bool(req.get("archived", True))

        def mark(data):
            if archived:
                data["archived"] = True
            else:
                data.pop("archived", None)
            return None

        locked_update(path, mark)
        return self._json(200, {"ok": True, "archived": archived})

    def post_persona(self, req):
        """Ask the moderator to build a custom persona from a description and/or documents.
        Sources are kept in the private folder (next to personas/), never in the logs folder."""
        cfg = load_config()
        name = re.sub(r"\s+", " ", str(req.get("name", ""))).strip()
        description = str(req.get("description", "")).strip()
        kind = str(req.get("kind") or "custom")
        if kind not in ("public", "custom"):
            raise ValueError("kind must be public or custom")
        if not name or len(name) > 60:
            raise ValueError("give the persona a name" + ("" if kind == "public" else " (a nickname or role name is best)"))
        if len(description) > 8000:
            raise ValueError("the description is too long (8,000 characters at most)")
        if kind == "custom" and not description and not req.get("files"):
            raise ValueError("add a description, documents, or both")
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "persona"
        private = pathlib.Path(cfg.get("private_personas_dir", "~/.claude/ask-the-experts/personas")).expanduser()
        files = []
        if req.get("files"):
            files = self._save_files("", req.get("files"), folder=private.parent / "persona-sources" / slug)
        self._event({"kind": "persona", "persona_kind": kind, "name": name, "slug": slug, "description": description,
                     "files": [{k: f[k] for k in ("name", "path", "type", "size")} for f in files]})
        return self._json(200, {"ok": True, "slug": slug})

    def post_add(self, req):
        name, path = self._transcript(req)
        cfg = load_config()
        people = {p["slug"]: p for p in roster(cfg)}
        picks = [str(s) for s in (req.get("people") or [])]
        if not picks or len(picks) > 6 or any(s not in people for s in picks):
            raise ValueError("pick one to six people from the roster")
        user_name = cfg.get("user_name") or "You"
        result = {}

        def add(data):
            if not data.get("live"):  # adding people to a finished chat picks it up again
                data["live"] = True
                result["reopened"] = True
            parts = data.setdefault("participants", [])
            have = {p.get("id") for p in parts}
            new = [s for s in picks if s not in have]
            if not new:
                raise ValueError("they're already in this chat")
            for s in new:
                parts.insert(max(0, len(parts) - 1), person_entry(people[s]))  # keep the user last
            added = [people[s]["name"] for s in new]
            seated = [p.get("name") for p in parts if p.get("kind") in ("thinker", "self")]
            was = data.get("mode", "group")
            if was == "direct":
                data["mode"] = "group"
                data["topic"] = "Group chat with " + ", ".join(seated)
                data["title"] = ", ".join(n.split()[-1] for n in seated)
            data.setdefault("items", []).append({"type": "moderator", "label": "Added",
                                                 "text": f"{user_name} added {', '.join(added)}.", "time": now_iso()})
            result.update(added=new, was=was)
            return None

        locked_update(path, add)
        self._event({"kind": "add", "transcript": name, "people": result["added"], "was": result["was"],
                     "reopened": bool(result.get("reopened"))})
        return self._json(200, {"ok": True, "added": result["added"]})

    def _save_files(self, transcript_name, files, folder=None):
        """Decode and save attachments; returns [{name, url, path, type, size}]."""
        if not isinstance(files, list) or len(files) > MAX_FILES:
            raise ValueError(f"up to {MAX_FILES} files at a time")
        out, folder = [], folder or (self.server.root / "attachments" / transcript_name[:-5])
        for f in files:
            raw_name = pathlib.Path(str(f.get("name", "file"))).name
            ext = raw_name.rsplit(".", 1)[-1].lower() if "." in raw_name else ""
            if ext not in ATTACH_TYPES:
                raise ValueError(f"{raw_name}: only images, PDFs, text, Office files and CSV/JSON can be attached")
            try:
                blob = base64.b64decode(str(f.get("data", "")), validate=True)
            except ValueError:
                raise ValueError(f"{raw_name}: could not read the file")
            if not blob or len(blob) > MAX_FILE:
                raise ValueError(f"{raw_name}: files must be under 10 MB")
            stem = re.sub(r"[^A-Za-z0-9._-]+", "-", raw_name.rsplit(".", 1)[0]).strip("-.")[:60] or "file"
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / f"{datetime.datetime.now().strftime('%H%M%S')}-{stem}.{ext}"
            n = 1
            while target.exists():
                target = folder / f"{datetime.datetime.now().strftime('%H%M%S')}-{stem}-{n}.{ext}"; n += 1
            target.write_bytes(blob)
            try:
                url = target.relative_to(self.server.root).as_posix()
            except ValueError:
                url = None  # saved outside the logs folder (persona sources): not served
            out.append({"name": raw_name, "url": url,
                        "path": str(target), "type": ext, "size": len(blob)})
        return out

    def post_say(self, req):
        name, path = self._transcript(req)
        text = str(req.get("text", "")).strip()
        files = self._save_files(name, req.get("files") or []) if req.get("files") else []
        if (not text and not files) or len(text) > MAX_TEXT:
            raise ValueError("empty or too long")
        reply_to = req.get("replyTo")
        to_req = req.get("to") or []
        if not isinstance(to_req, list) or len(to_req) > 10:
            raise ValueError("to must be a short list")
        tagged = {"to": []}

        def add(data):
            items = data.setdefault("items", [])
            names = {p.get("id"): p.get("name") for p in data.get("participants", [])
                     if p.get("kind") in ("thinker", "self")}
            names["ai"] = data.get("host") or "Claude"
            to = [t for t in dict.fromkeys(str(x) for x in to_req) if t in names]
            tagged["to"] = to
            data.pop("archived", None)  # writing in an archived chat brings it back to the list
            if not data.get("live"):  # a finished chat picks up again when the user writes in it
                data["live"] = True
                tagged["reopened"] = True
                items.append({"type": "moderator", "label": "Picked up again",
                              "text": "The chat continues after its earlier ending.", "time": now_iso()})
            label = "You"
            item = {"type": "user", "label": label, "text": text, "from": "page", "time": now_iso()}
            if files:
                item["files"] = [{k: f[k] for k in ("name", "url", "type", "size")} for f in files]
            if isinstance(reply_to, int) and 0 <= reply_to < len(items):
                item["replyTo"] = reply_to
                who = names.get(items[reply_to].get("who"))
                if who:
                    label = f"You, replying to {who}"
            if to:
                item["to"] = to
                label = "You → " + ", ".join(names[t] for t in to)
            item["label"] = label
            items.append(item)
            return len(items) - 1, label

        index, label = locked_update(path, add)
        self._event({"kind": "say", "transcript": name, "index": index, "label": label, "text": text,
                     "to": tagged["to"], "replyTo": reply_to if isinstance(reply_to, int) else None,
                     "reopened": bool(tagged.get("reopened")),
                     "files": [{k: f[k] for k in ("name", "path", "type", "size")} for f in files]})
        return self._json(200, {"ok": True, "index": index})

    def post_edit(self, req):
        name, path = self._transcript(req)
        text = str(req.get("text", "")).strip()
        index = req.get("index")
        if not text or len(text) > MAX_TEXT:
            raise ValueError("empty or too long")

        def edit(data):
            items = data.get("items", [])
            if not isinstance(index, int) or not 0 <= index < len(items):
                raise ValueError("bad index")
            it = items[index]
            selfs = {p.get("id") for p in data.get("participants", []) if p.get("kind") == "self"}
            if it.get("type") != "turn" or it.get("who") not in selfs:
                raise ValueError("only your own persona's turns can be edited")
            old, it["text"], it["edited"] = it.get("text", ""), text, True
            return old

        old = locked_update(path, edit)
        self._event({"kind": "edit", "transcript": name, "index": index, "text": text, "was": old})
        return self._json(200, {"ok": True, "index": index})

    def post_answer(self, req):
        name, path = self._transcript(req)
        ask_id = req.get("askId")
        answers = req.get("answers") or []

        def answer(data):
            ask = data.get("ask")
            if not ask or ask.get("id") != ask_id:
                raise ValueError("that question is no longer open")
            qs = {q.get("id"): q for q in ask.get("questions", [])}
            given = []
            for a in answers:
                q = qs.get(a.get("qid"))
                if not q:
                    continue
                valid = {o.get("label") for o in q.get("options", [])}
                choices = [c for c in (a.get("choices") or []) if c in valid]
                other = str(a.get("other") or "").strip()[:MAX_TEXT]
                text = "; ".join(choices + ([other] if other else []))
                if not text:
                    continue
                label = "You chose" if q.get("header") == "Next" else q.get("q", "You answered")
                data["items"].append({"type": "user", "label": label, "text": text, "from": "page", "time": now_iso()})
                given.append({"qid": q.get("id"), "question": q.get("q"), "choices": choices, "other": other})
            if not given:
                raise ValueError("pick an option or type an answer")
            data.pop("ask", None)
            return given

        given = locked_update(path, answer)
        self._event({"kind": "answer", "transcript": name, "askId": ask_id, "answers": given})
        return self._json(200, {"ok": True})

    def post_control(self, req):
        name, path = self._transcript(req)
        action = req.get("action")
        words = {"pause": "Pause here, please.", "resume": "Carry on.", "wrap": "Let's wrap up now."}
        if action not in words:
            raise ValueError("unknown action")

        def control(data):
            data["paused"] = action == "pause"
            data["items"].append({"type": "user", "label": "You", "text": words[action], "from": "page"})

        locked_update(path, control)
        self._event({"kind": "control", "transcript": name, "action": action})
        return self._json(200, {"ok": True})


def main():
    cfg = load_config()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=cfg.get("logs_dir"))
    ap.add_argument("--port", type=int, default=int(cfg.get("port", 8766)))
    ap.add_argument("--public-only", action="store_true", help="show only the plugin's own experts (for demos)")
    args = ap.parse_args()
    global PUBLIC_ONLY
    PUBLIC_ONLY = args.public_only
    if not args.dir:
        sys.exit("No logs folder: run the skill's setup first, or pass --dir")
    root = pathlib.Path(args.dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / INBOX).touch()
    other = running(args.port)
    if other:
        print(f"Ask the Experts is already running on http://127.0.0.1:{args.port}/ "
              f"(version {other.get('version') or 'unknown'}, pid {other.get('pid', '?')}). Reusing it.", flush=True)
        return
    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), functools.partial(App, directory=str(root)))
    server.root = root
    print(f"Ask the Experts on http://127.0.0.1:{args.port}/  (logs: {root})", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
