#!/usr/bin/env python3
"""Deliver the brief, preferring the Worker so one recipient list governs.

The Worker keeps the enrolled devices in its own storage, because a device that
enrols itself through an invite link cannot write to a GitHub secret. If the
brief were sent straight from here it would reach only the chats named in
TELEGRAM_OWNERS, and a self-enrolled phone would get silence.

So: POST the brief to the Worker and let it fan out. If the Worker is not
configured, refuses, or cannot be reached, fall back to sending directly, so a
brief is never lost to a Worker problem. Failing both is a failed run.

Environment:
  WORKER_URL       e.g. https://markwatch.<subdomain>.workers.dev  (optional)
  WEBHOOK_SECRET   the Worker's shared secret
  BRIEF_FILE       path to the brief to deliver
  TELEGRAM_*       used by the direct fallback
"""
import json, os, pathlib, sys, urllib.error, urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).parent))

TIMEOUT = 60          # fan-out to several chats happens inside this one call


def brief_path() -> pathlib.Path:
    named = os.environ.get("BRIEF_FILE", "").strip()
    if named:
        p = pathlib.Path(named)
        if not p.is_file():
            sys.exit(f"{named} not found")
        return p
    files = sorted(p for p in pathlib.Path("briefs").glob("*.md")
                   if p.stat().st_size and p.name.lower() != "readme.md")
    if not files:
        print("No brief to send yet — nothing to do.")
        sys.exit(0)
    return files[-1]


def via_worker(md: str) -> bool:
    url = os.environ.get("WORKER_URL", "").strip().rstrip("/")
    secret = os.environ.get("WEBHOOK_SECRET", "").strip()
    if not url or not secret:
        print("Worker not configured (WORKER_URL / WEBHOOK_SECRET unset) — "
              "sending directly.")
        return False

    req = urllib.request.Request(
        f"{url}/publish",
        data=json.dumps({"markdown": md}).encode(),
        headers={"Content-Type": "application/json", "X-Publish-Secret": secret},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        print(f"::warning::Worker refused the brief (HTTP {e.code}): {detail}")
        return False
    except Exception as e:
        print(f"::warning::Worker unreachable: {type(e).__name__}: {e}")
        return False

    if not body.get("ok"):
        print(f"::warning::Worker reported a problem: {body}")
        return False
    sent, total = body.get("sent", 0), body.get("recipients", 0)
    if sent == 0:
        print(f"::warning::Worker reached none of its {total} recipient(s)")
        return False
    if body.get("failed"):
        print(f"::warning::Worker could not reach {body['failed']} of {total} chats")
    print(f"Delivered through the Worker to {sent} of {total} recipient(s).")
    return True


def via_telegram_directly(path: pathlib.Path) -> bool:
    import send
    os.environ["BRIEF_FILE"] = str(path)
    try:
        send.main()
        return True
    except SystemExit as e:
        return e.code in (0, None)
    except Exception as e:
        print(f"::error::direct send failed: {type(e).__name__}: {e}")
        return False


def main() -> None:
    path = brief_path()
    md = path.read_text(encoding="utf-8")
    print(f"Delivering {path} ({len(md)} chars)")

    if via_worker(md):
        return
    print("Falling back to sending straight from the runner.")
    if not via_telegram_directly(path):
        sys.exit("both delivery routes failed — the brief reached nobody")


if __name__ == "__main__":
    main()
