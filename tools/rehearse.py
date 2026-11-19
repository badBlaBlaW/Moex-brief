#!/usr/bin/env python3
"""Dress-rehearse the whole delivery path without touching Telegram.

This container cannot reach api.telegram.org, and the real pipeline cannot run
until GitHub Actions is unblocked. So every step the runner would take is run
here against a stub that captures what Telegram would have received, and the
captured payloads are then checked the way Telegram itself would judge them:
valid HTML, inside the 4,096-character cap, buttons attached once.

    python3 tools/rehearse.py briefs/2026-11-19.md

Exits non-zero if any check fails. Writes the captured payloads to
/tmp/rehearsal/ so they can be read back.
"""
import html.parser, json, os, pathlib, shutil, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github" / "scripts"))
OUT = pathlib.Path("/tmp/rehearsal")
HARD_LIMIT = 4096                 # Telegram's own cap on a message
ALLOWED_TAGS = {"b", "i", "u", "s", "code", "pre", "a", "tg-spoiler", "blockquote"}

captured: list[dict] = []
failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"  FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"  ok    {msg}")


class TagCheck(html.parser.HTMLParser):
    """Telegram rejects unknown tags and unbalanced nesting with HTTP 400."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.bad = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            self.bad.append(f"unsupported tag <{tag}>")
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack:
            self.bad.append(f"</{tag}> with nothing open")
        elif self.stack[-1] != tag:
            self.bad.append(f"</{tag}> closes <{self.stack[-1]}>")
            self.stack.pop()
        else:
            self.stack.pop()


def install_stub():
    """Replace the network call with a recorder, leaving every other step real."""
    import tg

    def stub(method, payload, retries=2, http_timeout=35):
        captured.append({"method": method, "payload": payload})
        return {"ok": True, "result": {"message_id": len(captured)}}

    tg.call = stub
    return tg


def check_message(i: int, n: int, msg: dict, tg) -> None:
    p = msg["payload"]
    text = p.get("text", "")
    label = f"message {i}/{n}"

    if len(text) > HARD_LIMIT:
        fail(f"{label}: {len(text)} chars, over Telegram's {HARD_LIMIT} cap")
    if not text.strip():
        fail(f"{label}: empty")
    if p.get("parse_mode") != "HTML":
        fail(f"{label}: parse_mode is {p.get('parse_mode')!r}, not HTML")

    checker = TagCheck()
    checker.feed(text)
    for b in checker.bad:
        fail(f"{label}: {b}")
    if checker.stack:
        fail(f"{label}: tags left open: {checker.stack}")

    # A bare '&' or '<' that escaping missed is what actually triggers the 400.
    for raw in ("&nbsp", "&&"):
        if raw in text:
            fail(f"{label}: unescaped {raw!r}")


def main() -> None:
    brief = sys.argv[1] if len(sys.argv) > 1 else ""
    if not brief or not (ROOT / brief).exists():
        sys.exit(f"usage: rehearse.py <brief path>   (got {brief!r})")

    os.chdir(ROOT)
    print(f"\nREHEARSAL — {brief}\n" + "=" * 60)

    # Stand in for the secrets the runner would hold.
    os.environ.setdefault("TELEGRAM_TOKEN", "000:rehearsal")
    os.environ.setdefault("TELEGRAM_CHAT_ID", "1000000001")
    os.environ.setdefault("TELEGRAM_OWNERS", "1000000002, 1000000003")
    os.environ["BRIEF_FILE"] = brief

    print("\n1. the gate (check_brief.py)")
    rc = os.system(f"BRIEF={brief} python3 .github/scripts/check_brief.py")
    if rc != 0:
        fail("check_brief.py rejected the brief — the run would stop here")
    else:
        ok("gate passed")

    print("\n2. the send path (send.py, network stubbed)")
    tg = install_stub()
    import send
    try:
        send.main()
    except SystemExit as e:
        if e.code not in (0, None):
            fail(f"send.py exited {e.code}")
    except Exception as e:
        fail(f"send.py raised {type(e).__name__}: {e}")

    if not captured:
        fail("nothing was sent")
        return report()

    devices = {m["payload"]["chat_id"] for m in captured}
    per = len(captured) // max(len(devices), 1)
    ok(f"{len(captured)} API calls — {per} message(s) to each of {len(devices)} devices")
    ok(f"recipients: {sorted(devices)}")

    print("\n3. what Telegram would make of each message")
    for i, m in enumerate(captured, 1):
        check_message(i, len(captured), m, tg)
    if not failures:
        ok("every message is valid HTML, inside the cap")

    print("\n4. the buttons")
    with_kb = [m for m in captured if "reply_markup" in m["payload"]]
    if len(with_kb) != len(devices):
        fail(f"{len(with_kb)} messages carry the keyboard, expected {len(devices)}"
             " — one on the last message per device")
    else:
        kb = with_kb[0]["payload"]["reply_markup"]
        rows = kb.get("keyboard", [])
        labels = [b if isinstance(b, str) else b.get("text") for r in rows for b in r]
        ok(f"keyboard on the final message only, persistent={kb.get('is_persistent')}")
        ok(f"buttons: {labels}")

    print("\n5. capture written to /tmp/rehearsal")
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    (OUT / "calls.json").write_text(json.dumps(captured, ensure_ascii=False, indent=2))
    seen = set()
    for m in captured:
        c = m["payload"]["chat_id"]
        if c in seen:
            continue
        seen.add(c)
        for j, mm in enumerate([x for x in captured
                                if x["payload"]["chat_id"] == c], 1):
            (OUT / f"device-{c}-msg{j}.html").write_text(mm["payload"]["text"])
    ok(f"{len(list(OUT.iterdir()))} files")

    report()


def report() -> None:
    print("\n" + "=" * 60)
    if failures:
        print(f"REHEARSAL FAILED — {len(failures)} problem(s)")
        for f in failures:
            print(f"  · {f}")
        sys.exit(1)
    print("REHEARSAL PASSED — this brief would reach the bot intact")


if __name__ == "__main__":
    main()
