#!/usr/bin/env python3
"""Flag a roundtable turn that reads like writing rather than talk, or that recites the dossier.

Usage:
  python3 -I speech_check.py [<dossier.md>] < turn.txt

Prints one line per problem and exits 1 if there are any; prints nothing and exits 0 if the
turn passes. With a dossier, also flags runs of seven or more words copied from it (its
Verified quotes section excepted: a speaker may work those into speech).

The checks are deliberately blunt. They catch the habits that made test runs sound staged:
colons and semicolons mid-speech, neat lists of three, "X, not Y" slogan endings, quotation
marks, overlong turns, and stock openers such as "Fair point" or "X is right".
"""
import pathlib
import re
import sys

MAX_WORDS = 60
MAX_SENTENCES = 4
COPY_RUN = 7

OPENERS = re.compile(
    r"^\s*(?:(?:[A-Z][a-z]+|Sir [A-Z][a-z]+|Mr [A-Z][a-z]+)[,’'s]*\s+)?"
    r"(?:fair point|good point|you'?re right|is right|'s right|’s right|is half right|'s half right|i concede|i agree)\b",
    re.IGNORECASE)
SLOGAN = re.compile(r",\s+not\s+(?:a |an |the )?[\w’'-]+[.!?]?\s*$|\bnot\s+[\w’' -]{1,25},\s+but\b", re.IGNORECASE)
# "A, B, and C" (two commas) or "A, B and C" with a short middle item. A lone name followed by a
# comma ("So Sam, pull the minutes and see") is a way of talking, not a list.
TRIPLE = re.compile(r"\b[\w’'-]+(?: [\w’'-]+){0,3}, (?:[\w’'-]+(?: [\w’'-]+){0,3}, (?:and|or)|[\w’'-]+(?: [\w’'-]+)?,? (?:and|or)) [\w’'-]+", re.IGNORECASE)
QUOTES = re.compile(r"[\"“”]")


def words(text):
    return re.findall(r"[a-z0-9’']+", text.lower().replace("’", "'"))


def dossier_text(path):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    # Drop the Verified quotes section and the source list: quoting a verified line is allowed,
    # and source titles are not something a speaker would say anyway.
    text = re.sub(r"(?ms)^## Verified quotes.*?(?=^## )", "", text)
    text = re.sub(r"(?ms)^## Sources.*", "", text)
    return text


def copied_runs(turn, source):
    src = words(source)
    grams = {tuple(src[i:i + COPY_RUN]) for i in range(len(src) - COPY_RUN + 1)}
    tw = words(turn)
    hits, i = [], 0
    while i <= len(tw) - COPY_RUN:
        if tuple(tw[i:i + COPY_RUN]) in grams:
            j = i + COPY_RUN
            while j < len(tw) and tuple(tw[j - COPY_RUN + 1:j + 1]) in grams:
                j += 1
            hits.append(" ".join(tw[i:j]))
            i = j
        else:
            i += 1
    return hits


def check(turn, dossier=None):
    flags = []
    body = turn.strip()
    n = len(words(body))
    if n > MAX_WORDS:
        flags.append(f"too long: {n} words (keep it under about 50)")
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", body) if s.strip()]
    if len(sentences) > MAX_SENTENCES:
        flags.append(f"too many sentences: {len(sentences)} (three at most)")
    if re.search(r"[:;]", body):
        flags.append("colon or semicolon: people don't speak in them; split it or say it plainly")
    if QUOTES.search(body):
        flags.append("quotation marks: work the line into speech instead of quoting it")
    for para in body.split("\n"):
        for s in re.split(r"(?<=[.!?])\s+", para):
            if SLOGAN.search(s):
                flags.append(f"slogan ending ('X, not Y' or 'not X, but Y'): {s.strip()}")
            m = TRIPLE.search(s)
            if m:
                flags.append(f"neat list: {m.group(0)}")
    if OPENERS.search(body):
        flags.append("stock opener (\"fair point\", \"X is right\", \"I concede\"): react the way this person really would")
    if dossier:
        for run in copied_runs(body, dossier_text(dossier)):
            flags.append(f"copied from the dossier: \"{run}\"; say it in your own words, or drop it")
    return flags


def main():
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        sys.exit(__doc__)
    # UTF-8 both ways: on Windows the console streams default to the ANSI code page (cp1252).
    sys.stdout.reconfigure(encoding="utf-8")
    flags = check(sys.stdin.buffer.read().decode("utf-8-sig"), args[0] if args else None)
    for f in flags:
        print("- " + f)
    sys.exit(1 if flags else 0)


if __name__ == "__main__":
    main()
