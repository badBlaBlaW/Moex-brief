#!/usr/bin/env python3
"""Refuse to publish a brief that is not a brief.

Claude Code can finish a run without producing what was asked — it can write a
stub, answer in the wrong language, or leave the file untouched. Nothing should
reach Telegram unchecked, so the gate lives here between generation and send.

Reads the path from $BRIEF. Exits non-zero with the reason on any failure.
"""
import json, os, pathlib, re, sys

ROOT     = pathlib.Path(__file__).resolve().parents[2]
MIN_CHAR = 1500
SECTIONS = ("Рынок", "Что важно", "Проверка фактов", "Рекомендации",
            "Мой взгляд", "Сценарии")


def fail(msg: str) -> None:
    sys.exit(f"brief rejected: {msg}")


def main() -> None:
    rel = os.environ.get("BRIEF", "").strip()
    if not rel:
        fail("$BRIEF is not set")
    path = ROOT / rel
    if not path.exists():
        fail(f"{rel} was never written")

    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) < MIN_CHAR:
        fail(f"{rel} is {len(text)} chars, under the {MIN_CHAR} floor\n"
             f"--- what it holds ---\n{text[:600]}")

    if not re.search(r"^# ", text, re.M):
        fail("no '# ' heading — this does not look like the brief")

    try:
        lang = json.loads((ROOT / "config.json").read_text()).get("language", "ru")
    except Exception:
        lang = "ru"

    cyr = len(re.findall(r"[А-Яа-яЁё]", text))
    if lang == "ru":
        if cyr < 400:
            fail(f"language is 'ru' but the brief holds only {cyr} Cyrillic "
                 f"characters — it came back in the wrong language")
        found = [s for s in SECTIONS if s in text]
        if len(found) < 4:
            fail(f"only {len(found)} of the six sections are present: {found}")
    elif cyr > len(text) * 0.3:
        fail("language is 'en' but the brief came back mostly in Russian")

    # A brief written from memory instead of from searches is the failure the
    # gate would otherwise pass: it reads fine and every number is stale. Live
    # sources are the evidence that searching happened.
    links = re.findall(r"https?://[^\s)\]]+", text)
    if len(links) < 3:
        fail(f"only {len(links)} source link(s) — the brief was probably written "
             f"from memory rather than from live searches")

    # A homepage is not a source: it cannot be checked and it does not show
    # where a figure came from. Deep links are the ones that carry evidence.
    deep = [u for u in links if re.search(r"https?://[^/]+/.+", u)]
    if len(deep) < 2:
        print(f"::warning::{len(deep)} of {len(links)} source links point at an "
              f"actual page; the rest are bare homepages")

    dead = re.findall(r"\b[A-Z]{1,3}[+-]?\.ru\b", text)
    if dead:
        print(f"::warning::rating written as a dead link: {sorted(set(dead))}")

    print(f"ok: {rel}, {len(text)} chars, lang={lang}, cyrillic={cyr}")


if __name__ == "__main__":
    main()
