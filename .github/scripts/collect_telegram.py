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
HOURS     = 36                    # keep a weekend's worth
MAX_PER   = 20                    # posts per channel
MAX_IMGS  = 24                    # charts are often the whole point of a post
IMG_DIR   = ROOT / "sources" / "telegram-images"
IMG_MAX_B = 3_000_000
PRUNE_DAYS = 3
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

def pick_images(block: str):
    """Photo URLs in a post. Telegram puts them in a CSS background-image."""
    return re.findall(r"background-image:url\('([^']+)'\)", block)

def save_image(url: str, stem: str):
    """Download one photo. Charts carry content that the caption does not."""
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read(IMG_MAX_B + 1)
        if not data or len(data) > IMG_MAX_B:
            return None
        IMG_DIR.mkdir(parents=True, exist_ok=True)
        path = IMG_DIR / f"{stem}.jpg"
        path.write_bytes(data)
        return path.relative_to(ROOT)
    except Exception as e:
        print(f"  image skipped: {e}")
        return None

def prune_images():
    """Keep the folder small — old charts are worthless and bloat the repo."""
    if not IMG_DIR.exists():
        return
    cutoff = datetime.now(timezone.utc).timestamp() - PRUNE_DAYS * 86400
    for f in IMG_DIR.glob("*.jpg"):
        if f.stat().st_mtime < cutoff:
            f.unlink()

def posts(page: str):
    """(datetime, text, [image urls]) for each post, newest last."""
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
        out.append((when, body, pick_images(block)))
    return out

def main() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=HOURS)
    lines = [f"# Telegram digest — generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
             "", f"Public channel posts from the last {HOURS} hours. "
             "Source material, not verified — treat every claim as REPORTED or "
             "RUMOUR until confirmed elsewhere.", ""]
    total = 0
    saved = [0]
    prune_images()
    for name in channels():
        try:
            page = fetch(name)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            lines += [f"## @{name}", f"_could not be read: {e}_", ""]
            print(f"{name}: FAILED {e}")
            continue
        recent = [p for p in posts(page) if p[0] >= cutoff][-MAX_PER:]
        print(f"{name}: {len(recent)} recent post(s)")
        total += len(recent)
        lines.append(f"## @{name}")
        if not recent:
            lines += ["_nothing in the window_", ""]
            continue
        for when, body, imgs in recent:
            lines.append(f"**{when:%d %b %H:%M} UTC** — {body}")
            for i, u in enumerate(imgs):
                if saved[0] >= MAX_IMGS:
                    break
                stem = f"{name}-{when:%m%d-%H%M}-{i}"
                rel = save_image(u, stem)
                if rel:
                    saved[0] += 1
                    lines.append(f"  [IMAGE — read this file: {rel}]")
            lines.append("")
    lines.append(f"_{total} post(s) across {len(channels())} channel(s); "
                 f"{saved[0]} image(s) saved._")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes, {total} posts)")

if __name__ == "__main__":
    main()
