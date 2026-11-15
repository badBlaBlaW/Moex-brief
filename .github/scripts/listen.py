#!/usr/bin/env python3
"""Mark's listener — long polling, so replies are immediate.

Telegram holds each getUpdates request open until a message arrives (or the
timeout lapses), so this answers the moment you press a button rather than on
a schedule. One run listens for just under six hours, then asks GitHub to
start the next one, so the chain is continuous.

  --once   drain whatever is waiting and exit (used for a quick manual check)
"""
import os, pathlib, subprocess, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import bridge_text as B, tg

POLL_SECONDS = 50                 # how long Telegram holds the connection
RUN_SECONDS  = 5 * 3600 + 40 * 60  # stop before the 6h job limit

def git(*args, check=True):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=check)


def refresh():
    """Pull before reading briefs.

    A shift lasts six hours; the checkout is made once at the start. Without
    this, a brief published mid-shift is invisible and /brief keeps returning
    yesterday's.
    """
    r = git("pull", "--rebase", "--autostash", check=False)
    if r.returncode:
        print(f"::warning::could not refresh briefs: {r.stderr.strip()[:200]}")

def latest_brief():
    briefs = sorted(p for p in pathlib.Path("briefs").glob("*.md")
                    if p.stat().st_size and p.name.lower() != "readme.md")
    return briefs[-1] if briefs else None

def send_brief(lang):
    refresh()
    path = latest_brief()
    if not path:
        tg.send(B.NO_BRIEF[lang].format(w=B.next_brief(lang)), markup=B.kb_menu(lang)); return
    tg.send(B.SENDING[lang])
    parts = tg.chunk(tg.md_to_html(path.read_text(encoding="utf-8").strip()))
    for i, part in enumerate(parts, 1):
        tag = (f"\n\n<i>({i}{' из ' if lang=='ru' else '/'}{len(parts)})</i>"
               if len(parts) > 1 else "")
        tg.send(part + tag, markup=B.kb_menu(lang) if i == len(parts) else None)

def persist(cfg):
    """Commit the language/stage change. Rebase first — a brief may have landed."""
    tg.save_config(cfg)
    if not git("status", "--porcelain", "config.json").stdout.strip():
        return
    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email",
        "41898282+github-actions[bot]@users.noreply.github.com")
    git("add", "config.json")
    git("commit", "-m", "bot: update settings")
    for attempt in range(2):
        if git("push", check=False).returncode == 0:
            return
        git("pull", "--rebase", "--autostash", check=False)
    print("::warning::could not push config change")

def handle(msg, cfg) -> None:
    raw = (msg.get("text") or "").strip()
    cmd = raw.lower().split("@")[0]
    if str((msg.get("chat") or {}).get("id", "")) != tg.chat():
        return                                              # owner only
    lang = cfg["language"] if cfg.get("language") in ("ru", "en") else "en"

    if cmd == "/start":
        tg.send(B.ASK_LANGUAGE, markup=B.kb_language())
        cfg["stage"] = "awaiting_language"
    elif raw in (B.LANG_BTN["ru"], B.LANG_BTN["en"]) or cmd in ("/ru", "/en"):
        L = "ru" if (raw == B.LANG_BTN["ru"] or cmd == "/ru") else "en"
        tg.send(B.CONFIRMED[L].format(w=B.next_brief(L)))
        tg.send(B.OFFER[L], markup=B.kb_offer(L))
        cfg.update(language=L, stage="awaiting_offer", onboarded=True)
        try: tg.call("setMyCommands", {"commands": B.COMMANDS[L]})
        except RuntimeError: pass
    elif raw in (B.OFFER_BTN["ru"]["yes"], B.OFFER_BTN["en"]["yes"]):
        send_brief(lang); cfg["stage"] = "idle"
    elif raw in (B.OFFER_BTN["ru"]["no"], B.OFFER_BTN["en"]["no"]):
        tg.send(B.DECLINED[lang].format(w=B.next_brief(lang)) + "\n\n" + B.DISCLAIMER[lang],
                markup=B.kb_menu(lang))
        cfg["stage"] = "idle"
    elif cmd == "/brief" or raw in (B.MENU_BTN["ru"]["brief"], B.MENU_BTN["en"]["brief"]):
        send_brief(lang)
    else:
        tg.send(B.HELP[lang], markup=B.kb_menu(lang))

MIN_CYCLE = 2.0                   # floor, so a fast-returning API can't busy-loop

def drain(cfg, wait: int):
    """One getUpdates round. Returns (config_changed, updates_seen)."""
    before = dict(cfg)
    try:
        resp = tg.call("getUpdates",
                       {"offset": cfg["last_update_id"] + 1, "timeout": wait,
                        "allowed_updates": ["message"]},
                       http_timeout=wait + 20)
    except RuntimeError as e:
        if "409" in str(e) or "webhook is active" in str(e).lower():
            print("A webhook is active — something else is answering. Stopping.")
            raise SystemExit(0)
        print(f"::warning::{e}")
        time.sleep(5)
        return False, 0
    updates = resp.get("result", [])
    for u in updates:
        cfg["last_update_id"] = max(cfg["last_update_id"], u["update_id"])
        if u.get("message"):
            handle(u["message"], cfg)
    return cfg != before, len(updates)

def main() -> None:
    once = "--once" in sys.argv
    cfg = tg.load_config()
    if once:
        changed, _ = drain(cfg, 0)
        if changed:
            persist(cfg)
        print("drained"); return

    deadline = time.time() + RUN_SECONDS
    print(f"listening for {RUN_SECONDS // 60} minutes")
    rounds = 0
    while time.time() < deadline:
        started = time.time()
        changed, seen = drain(cfg, POLL_SECONDS)
        if changed:
            persist(cfg)
        rounds += 1
        # If the API returned at once with nothing, pause before asking again.
        idle = time.time() - started
        if not seen and idle < MIN_CYCLE:
            time.sleep(MIN_CYCLE - idle)
    print(f"shift over after {rounds} polls — handing to the next run")

if __name__ == "__main__":
    main()
