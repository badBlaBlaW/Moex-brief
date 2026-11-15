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
    briefs = sorted(p for p in pathlib.Path("briefs").glob("*.md") if p.stat().st_size)
    if not briefs:
        sys.exit("no briefs/*.md found")
    return briefs[-1]                 # filenames are YYYY-MM-DD, so last = newest

def main() -> None:
    lang = tg.load_config()["language"]
    path = pick_file()
    parts = tg.chunk(tg.md_to_html(path.read_text(encoding="utf-8").strip()))
    print(f"Sending {path} as {len(parts)} message(s), language={lang}")
    for i, part in enumerate(parts, 1):
        last = i == len(parts)
        tag = "\n\n<i>" + strings.PART[lang].format(i=i, n=len(parts)) + "</i>" \
              if len(parts) > 1 else ""
        # Keyboard rides on the final message so it is what stays on screen.
        tg.send(part + tag, markup=strings.keyboard(lang) if last else None)
    print("done")

if __name__ == "__main__":
    main()
