#!/usr/bin/env python3
"""TEMPORARY BRIDGE. Answers the bot until the Cloudflare Worker is live.

Mirrors worker/worker.js. GitHub's scheduler is unreliable at short intervals,
so this is mostly useful run by hand from the Actions tab. Once the Worker's
webhook is set, Telegram stops serving getUpdates and this retires itself.
Delete listen.py, bridge_text.py and listen.yml at that point.
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import bridge_text as B, tg

def latest_brief():
    briefs = sorted(p for p in pathlib.Path("briefs").glob("*.md")
                    if p.stat().st_size and p.name.lower() != "readme.md")
    return briefs[-1] if briefs else None

def send_brief(lang):
    path = latest_brief()
    if not path:
        tg.send(B.NO_BRIEF[lang].format(w=B.next_brief(lang)), markup=B.kb_menu(lang)); return
    tg.send(B.SENDING[lang])
    parts = tg.chunk(tg.md_to_html(path.read_text(encoding="utf-8").strip()))
    for i, part in enumerate(parts, 1):
        tag = (f"\n\n<i>({i}{' из ' if lang=='ru' else '/'}{len(parts)})</i>"
               if len(parts) > 1 else "")
        tg.send(part + tag, markup=B.kb_menu(lang) if i == len(parts) else None)

def main() -> None:
    cfg = tg.load_config(); before = dict(cfg)
    try:
        resp = tg.call("getUpdates", {"offset": cfg["last_update_id"] + 1,
                                      "timeout": 0, "allowed_updates": ["message"]})
    except RuntimeError as e:
        if "409" in str(e) or "webhook is active" in str(e).lower():
            print("A webhook is active — the Worker has taken over. "
                  "Delete listen.py, bridge_text.py and listen.yml.")
            return
        raise

    for u in resp.get("result", []):
        cfg["last_update_id"] = max(cfg["last_update_id"], u["update_id"])
        msg = u.get("message") or {}
        raw = (msg.get("text") or "").strip()
        cmd = raw.lower().split("@")[0]
        if str((msg.get("chat") or {}).get("id", "")) != tg.chat():
            continue                                   # owner only
        lang = cfg["language"] if cfg["language"] in ("ru", "en") else "en"

        if cmd == "/start":
            tg.send(B.ASK_LANGUAGE, markup=B.kb_language())
            cfg["stage"] = "awaiting_language"
        elif raw == B.LANG_BTN["ru"] or cmd == "/ru" or raw == B.LANG_BTN["en"] or cmd == "/en":
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

    if cfg != before:
        tg.save_config(cfg); print("saved:", cfg)
    else:
        print("no change")

if __name__ == "__main__":
    main()
