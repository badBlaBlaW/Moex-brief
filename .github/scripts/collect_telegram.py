#!/usr/bin/env python3
"""Read public Telegram channels and write a digest the brief can use.

Runs on a GitHub runner, which has open internet — neither Claude's container
nor the scheduled session can reach t.me. Public channels expose a web preview
at t.me/s/<name>; private channels have none and are skipped.
"""
import html, pathlib, re, sys, urllib.error, urllib.request
from datetime import datetime, timedelta, timezone

ROOT    = pathlib.Path(__file__).resolve().parents[2]
LIST    = ROOT / "sources" / "channels.txt"
OUT     = ROOT / "sources" / "telegram-digest.md"
HOURS   = 36                      # keep a weekend's worth
MAX_PER = 25
UA      = {"User-Agent": "Mozilla/5.0 (compatible; markwatch/1.0)"}

def channels():
    if not LIST.exists():
        return []
    return [l.strip() for l in LIST.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]

def fetch(name: str) -> str:
    req = urllib.request.Request(f"https://t.me/s/{name}", headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def posts(page: str):
    """(datetime, text) for each post, newest last."""
    out = []
    for block in page.split('class="tgme_widget_message_wrap')[1:]:
        m = re.search(r'<time[^>]+datetime="([^"]+)"', block)
        t = re.search(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
                      block, re.S)
        if not (m and t):
            continue
        body = re.sub(r"<br\s*/?>", "\n", t.group(1))
        body = html.unescape(re.sub(r"<[^>]+>", "", body)).strip()
        body = re.sub(r"\n{3,}", "\n\n", body)
        if len(body) < 30:
            continue
        try:
            when = datetime.fromisoformat(m.group(1))
        except ValueError:
            continue
        out.append((when, body))
    return out

def main() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=HOURS)
    lines = [f"# Telegram digest — generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
             "", f"Public channel posts from the last {HOURS} hours. "
             "Source material, not verified — treat every claim as REPORTED or "
             "RUMOUR until confirmed elsewhere.", ""]
    total = 0
    for name in channels():
        try:
            page = fetch(name)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            lines += [f"## @{name}", f"_could not be read: {e}_", ""]
            print(f"{name}: FAILED {e}")
            continue
        recent = [(w, b) for w, b in posts(page) if w >= cutoff][-MAX_PER:]
        print(f"{name}: {len(recent)} recent post(s)")
        total += len(recent)
        lines.append(f"## @{name}")
        if not recent:
            lines += ["_nothing in the window_", ""]
            continue
        for when, body in recent:
            lines.append(f"**{when:%d %b %H:%M} UTC** — {body}")
            lines.append("")
    lines.append(f"_{total} post(s) across {len(channels())} channel(s)._")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes, {total} posts)")

if __name__ == "__main__":
    main()
