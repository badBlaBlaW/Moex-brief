#!/usr/bin/env python3
"""Read any commands/button presses sent to the bot and act on them.

Runs once per weekday, just before the brief is composed — not a polling loop.
Can also be run by hand from the Actions tab during setup.
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import strings, tg

def greet(lang: str) -> None:
    tg.send(f"{strings.GREETING[lang]}\n\n{strings.DISCLAIMER[lang]}",
            markup=strings.keyboard(lang))
    try:                                   # native "/" menu; cosmetic, never fatal
        tg.call("setMyCommands", {"commands": strings.COMMANDS[lang]})
    except RuntimeError as e:
        print(f"::warning::could not set command menu — {e}")

def main() -> None:
    cfg = tg.load_config()
    before = dict(cfg)

    resp = tg.call("getUpdates", {"offset": cfg["last_update_id"] + 1,
                                  "timeout": 0, "allowed_updates": ["message"]})
    updates = resp.get("result", [])
    print(f"{len(updates)} update(s)")

    for u in updates:
        cfg["last_update_id"] = max(cfg["last_update_id"], u["update_id"])
        msg = u.get("message") or {}
        raw = (msg.get("text") or "").strip()
        text = raw.lower().split("@")[0]
        sender = str((msg.get("chat") or {}).get("id", ""))

        if sender != tg.chat():            # the bot only ever answers its owner
            print(f"ignoring message from unknown chat {sender}")
            continue

        lang = cfg["language"]

        # First contact: take the language from the user's own Telegram settings.
        if text == "/start":
            lang = strings.detect(((msg.get("from") or {}).get("language_code")))
            cfg["language"] = lang
            cfg["onboarded"] = True
            print(f"onboarding, telegram locale -> {lang}")
            greet(lang)
            continue

        # Language switch, by button or by command. Match either language's
        # button text, in case the keyboard on screen is from an older message.
        want = None
        if text == "/ru" or raw == strings.BTN_SWITCH["en"]:      # "🇷🇺 Русский"
            want = "ru"
        elif text == "/en" or raw == strings.BTN_SWITCH["ru"]:    # "🇬🇧 English"
            want = "en"

        if want:
            if want != lang:
                cfg["language"] = lang = want
                tg.send(strings.SWITCHED[want], markup=strings.keyboard(want))
                try:
                    tg.call("setMyCommands", {"commands": strings.COMMANDS[want]})
                except RuntimeError:
                    pass
            else:
                tg.send(strings.HELP[lang], markup=strings.keyboard(lang))
            continue

        # Everything else gets the help card.
        tg.send(strings.HELP[lang], markup=strings.keyboard(lang))

    if cfg != before:
        tg.save_config(cfg)
        print(f"saved: language={cfg['language']} offset={cfg['last_update_id']}")
    else:
        print("no change")

if __name__ == "__main__":
    main()
