#!/usr/bin/env python3
"""Ask Telegram who the configured recipients actually are.

A send can return HTTP 200 and still land somewhere the person is not looking:
a different account, a chat they have since deleted, an ID that was right once
and is stale now. The logs cannot tell those apart, so this asks Telegram
directly and sends a one-off probe carrying a code printed here.

Whichever device shows the code is the account this repository talks to. If no
device shows it, the configured ID belongs to an account that is not yours.

Prints nothing that identifies a person: this repository is public. Chat IDs
appear as their last three digits, names as a length only.
"""
import os, random, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import tg


def tail(value: str) -> str:
    v = str(value)
    return f"…{v[-3:]} ({len(v)} digits)"


def main() -> None:
    code = f"{random.randint(1000, 9999)}"
    print("=" * 56)

    try:
        me = tg.call("getMe", {})["result"]
        print(f"bot:            @{me.get('username')}  (id {tail(me.get('id'))})")
    except Exception as e:
        sys.exit(f"getMe failed — the TELEGRAM_TOKEN secret is wrong or revoked:\n  {e}")

    cfg = tg.load_config()
    recipients = tg.owners(cfg)
    print(f"configured:     {len(recipients)} recipient(s)")
    if len(recipients) == 1:
        print("                TELEGRAM_OWNERS is empty — only one device is "
              "configured, whatever is in TELEGRAM_CHAT_ID")
    print("-" * 56)

    reachable = 0
    for c in recipients:
        print(f"chat {tail(c)}")
        try:
            info = tg.call("getChat", {"chat_id": c})["result"]
            name_len = len(info.get("first_name", "") or "")
            print(f"  exists:       yes, type={info.get('type')}, "
                  f"first_name is {name_len} characters long")
        except Exception as e:
            msg = str(e)
            print(f"  exists:       NO — {msg[:160]}")
            if "chat not found" in msg:
                print("  meaning:      this ID is not a chat the bot can reach. "
                      "Either it is wrong, or that account never pressed Start.")
            elif "blocked" in msg:
                print("  meaning:      that account blocked the bot. Unblock it "
                      "and press Start again.")
            continue

        try:
            r = tg.call("sendMessage", {
                "chat_id": c,
                "text": f"🔎 ПРОВЕРКА / PROBE {code}\n\n"
                        f"Если вы это видите — обзоры приходят именно на это "
                        f"устройство.\nIf you can see this, the briefs are going "
                        f"to this device.",
            })["result"]
            print(f"  probe sent:   yes, message_id={r.get('message_id')}")
            reachable += 1
        except Exception as e:
            print(f"  probe sent:   NO — {str(e)[:160]}")

    print("=" * 56)
    print(f"PROBE CODE: {code}")
    print(f"{reachable} of {len(recipients)} configured chat(s) accepted a message.")
    print("Check every phone. The device showing this code is the one the")
    print("briefs reach. If no device shows it, TELEGRAM_CHAT_ID is the wrong")
    print("account and needs replacing.")
    if reachable == 0:
        sys.exit("no configured chat could be reached")


if __name__ == "__main__":
    main()
