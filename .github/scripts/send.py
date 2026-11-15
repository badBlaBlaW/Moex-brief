#!/usr/bin/env python3
"""Post the newest brief in briefs/ to Telegram, with the command buttons attached."""
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import strings, tg

def pick_file() -> pathlib.Path:
    named = os.environ.get("BRIEF_FILE", "").strip()
    if named:
        p = pathlib.Path(named)
        if not p.is_file():
            sys.exit(f"{named} not found")
        return p
    briefs = sorted(p for p in pathlib.Path("briefs").glob("*.md")
                    if p.stat().st_size and p.name.lower() != "readme.md")
    if not briefs:
        print("No brief to send yet — nothing to do.")
        sys.exit(0)                   # not an error: the repo simply has no brief
    return briefs[-1]                 # filenames are YYYY-MM-DD, so last = newest

def main() -> None:
    path = pick_file()                # may exit cleanly if there is nothing to send
    cfg = tg.load_config()
    lang = cfg["language"]
    parts = tg.chunk(tg.md_to_html(path.read_text(encoding="utf-8").strip()))
    recipients = tg.owners(cfg)
    print(f"Sending {path} as {len(parts)} message(s), language={lang}, "
          f"to {len(recipients)} device(s)")
    for i, part in enumerate(parts, 1):
        last = i == len(parts)
        tag = "\n\n<i>" + strings.PART[lang].format(i=i, n=len(parts)) + "</i>" \
              if len(parts) > 1 else ""
        # Keyboard rides on the final message so it is what stays on screen.
        tg.broadcast(cfg, part + tag, markup=strings.keyboard(lang) if last else None)
    print("done")

if __name__ == "__main__":
    main()
