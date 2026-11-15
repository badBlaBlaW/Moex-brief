"""Shared Telegram + config helpers."""
import html, json, os, pathlib, re, sys, time, urllib.error, urllib.request

API = "https://api.telegram.org/bot{}/{}"
LIMIT = 3800                       # Telegram caps at 4096; leave headroom
CONFIG = pathlib.Path("config.json")

def token() -> str:
    t = os.environ.get("TELEGRAM_TOKEN", "").strip()
    if not t:
        sys.exit("TELEGRAM_TOKEN secret is not set in this repository.")
    return t

def chat() -> str:
    c = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not c:
        sys.exit("TELEGRAM_CHAT_ID secret is not set in this repository.")
    return c

def load_config() -> dict:
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        cfg = {}
    cfg.setdefault("language", "en")
    cfg.setdefault("last_update_id", 0)
    if cfg["language"] not in ("en", "ru"):
        cfg["language"] = "en"
    return cfg

def save_config(cfg: dict) -> None:
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")

def call(method: str, payload: dict, retries: int = 2, http_timeout: int = 35):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(API.format(token(), method), data=data,
                                 headers={"Content-Type": "application/json"})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=http_timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code == 429 and attempt < retries:        # rate limited
                wait = 3 * (attempt + 1)
                print(f"::warning::429 from Telegram, waiting {wait}s")
                time.sleep(wait); continue
            raise RuntimeError(f"{method} failed (HTTP {e.code}): {body[:400]}") from None
        except urllib.error.URLError as e:
            if attempt < retries:
                time.sleep(3); continue
            raise RuntimeError(f"{method} unreachable: {e.reason}") from None

def send(text: str, chat_id: str | None = None, markup: dict | None = None):
    """Send one message as HTML; fall back to plain text if Telegram rejects the markup."""
    target = chat_id or chat()
    payload = {"chat_id": target, "text": text, "parse_mode": "HTML",
               "disable_web_page_preview": True}
    if markup:
        payload["reply_markup"] = markup
    try:
        return call("sendMessage", payload)
    except RuntimeError as e:
        if "HTTP 400" not in str(e):
            raise
        print(f"::warning::HTML rejected, resending as plain text — {e}")
        payload["text"] = re.sub(r"<[^>]+>", "", text)
        payload.pop("parse_mode")
        return call("sendMessage", payload)

def md_to_html(md: str) -> str:
    """Markdown subset -> Telegram HTML. Escape first, then reintroduce tags."""
    out = []
    for line in md.split("\n"):
        esc = html.escape(line, quote=False)
        esc = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", esc)
        esc = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", esc)
        esc = re.sub(r"`([^`]+)`", r"<code>\1</code>", esc)
        esc = re.sub(r"\[(.+?)\]\((https?://[^\s)]+)\)", r'<a href="\2">\1</a>', esc)
        m = re.match(r"^(#{1,6})\s+(.*)$", esc)
        if m:
            esc = f"<b>{m.group(2)}</b>"
        esc = re.sub(r"^\s*[-*]\s+", "• ", esc)
        if re.match(r"^\s*([-*_])(\s*\1){2,}\s*$", line):
            esc = "—" * 12
        out.append(esc)
    return "\n".join(out)

def chunk(text: str, limit: int = LIMIT):
    """Split on blank lines so sections stay intact; hard-split an oversized block."""
    parts, cur = [], ""
    for block in text.split("\n\n"):
        while len(block) > limit:
            if cur.strip():
                parts.append(cur.strip()); cur = ""
            parts.append(block[:limit]); block = block[limit:]
        if len(cur) + len(block) + 2 > limit:
            if cur.strip():
                parts.append(cur.strip())
            cur = block
        else:
            cur = f"{cur}\n\n{block}" if cur else block
    if cur.strip():
        parts.append(cur.strip())
    return [p for p in parts if p.strip()]
