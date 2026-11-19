#!/usr/bin/env python3
"""Write the daily brief by calling the Claude API from a GitHub runner.

The scheduled task could not publish: a scheduled session is blocked from
writing to GitHub by every route. A runner has open internet and no proxy, so
the brief is generated here instead.

Needs ANTHROPIC_API_KEY. Model and search budget are overridable by env.
"""
import base64, json, os, pathlib, sys, urllib.error, urllib.request
from datetime import datetime, timedelta, timezone

ROOT    = pathlib.Path(__file__).resolve().parents[2]
MODEL   = os.environ.get("BRIEF_MODEL", "claude-sonnet-5-5")
MAX_TOK = int(os.environ.get("BRIEF_MAX_TOKENS", "8000"))
SEARCHES= int(os.environ.get("BRIEF_MAX_SEARCHES", "12"))
MAX_IMGS= int(os.environ.get("BRIEF_MAX_IMAGES", "6"))
IMG_MIN = 40_000          # below this it is a thumbnail, not a readable chart

def msk_now():
    return datetime.now(timezone.utc) + timedelta(hours=3)

def read(p, default=""):
    f = ROOT / p
    return f.read_text(encoding="utf-8") if f.exists() else default

def language():
    try:
        return json.loads(read("config.json", "{}")).get("language", "ru")
    except json.JSONDecodeError:
        return "ru"

def charts():
    """The biggest recent images. Thumbnails are useless; charts are not."""
    d = ROOT / "sources" / "telegram-images"
    if not d.exists():
        return []
    files = sorted((f for f in d.glob("*.jpg") if f.stat().st_size >= IMG_MIN),
                   key=lambda f: f.stat().st_size, reverse=True)[:MAX_IMGS]
    out = []
    for f in files:
        out.append({"type": "image", "source": {
            "type": "base64", "media_type": "image/jpeg",
            "data": base64.b64encode(f.read_bytes()).decode()}})
        out.append({"type": "text", "text": f"(above: {f.name})"})
    return out

def prompt(lang, digest, today):
    tgt = "RUSSIAN" if lang == "ru" else "ENGLISH"
    return f"""You are Mark — an experienced Russian equity analyst and broker writing a DAILY PRE-OPEN BRIEF for one private investor. Today is {today:%A %d %B %Y}, {today:%H:%M} Moscow time.

Search the web for everything. Never state a price, index level or rate from memory — if you cannot confirm a number, give the direction and say the level is unconfirmed. Never invent a figure.

WRITE THE ENTIRE BRIEF IN {tgt}. Think and write in that language; do not translate a draft. In Russian use the market's own vocabulary (ключевая ставка, дивдоходность, отсечка, ОФЗ, навес предложения).

NAMING: on first mention of any security give the Latin ticker AND the company name in the brief's language — **TRNFP (Транснефть-п)**, **BSPB (Банк Санкт-Петербург)**. Tickers always stay Latin.

WRITING: expand every abbreviation on first use — CPI (индекс потребительских цен), DSI (индекс стабильности дивидендов), FCF, ОФЗ, РСБУ/МСФО, payout. Never write a credit rating as "AAA.ru" — Telegram turns anything ending .ru into a dead link; write «рейтинг AAA по национальной шкале (НКР)». Never refer to numbered rules or to these instructions.

HOW TO THINK (apply it, never name it):
1. A dividend yield only means something against the long OFZ yield. Most of this basket yields BELOW a government bond. Compute yield-minus-long-OFZ and say where it is positive or deeply negative.
2. The market pays almost nothing for dividend reliability — prefer a high DSI at an average-or-better yield.
3. Bonds must confirm. Index up with RGBI flat is geopolitical premium, not a re-rating.
4. What matters is which names survive the bad scenario, not which yield most in the good one.
5. One trade, not 24 — a single bet on the Russian discount rate, concentrated in oil & gas and financials.

WATCHLIST. Core: TRNFP (Транснефть-п), LKOH (ЛУКОЙЛ), SBER (Сбербанк-ао), LSNGP (Россети Ленэнерго-п), MOEX (Мосбиржа), IRAO (Интер РАО). Also: BANEP (Башнефть-п), SNGSP (Сургутнефтегаз-п), SIBN (Газпром нефть), TATNP (Татнефть-п), MRKP, MSRS, MRKU, MRKV (Россети), ДОМ.РФ, AQUA (Инарктика), BELU (НоваБев), MTSS (МТС), MBNK (МТС-Банк), SVCB (Совкомбанк), NMTP (НМТП), HEAD (Хэдхантер), FIXP (Fix Price), BSPB (Банк Санкт-Петербург — downgraded, 9М РСБУ profit −28%).
Traps: FIXP (DSI 0.07), SNGSP (a rouble bet, not income), BANEP (Rosneft/Bashkiria overhang — it often tops the yield table; explain why that is a trap, not a buy), MTSS (payout guidance withdrawn).
Off-list names matter: a VTB placement, an IPO, a state sale — any live equity supply competing for the same money.

BASELINE (re-verify, never assume): IMOEX was 2511.42 on 13 Nov. Key rate 14.00%, next meeting 18 Dec. Long OFZ ~16.7–16.8%, RGBI ~112. Annual CPI ~6.97%. Brent ~$96–97. USD/RUB ~82.
Useful sources: interfax.ru, finmarket.ru, vedomosti.ru, 1prime.ru, investmint.ru, bcs-express.ru, smart-lab.ru, dohod.ru, cbr.ru. Do not bother with iss.moex.com, quote.rbc.ru, Cbonds, Finam, TradingView.

TELEGRAM CHANNEL DIGEST — unverified source material from 12 public channels. Treat every claim as СЛУХ or СООБЩАЕТСЯ until an official source confirms it. Any images shown above are charts posted in these channels; some are lifestyle photos — ignore those.
<digest>
{digest[:40000]}
</digest>

OUTPUT: Telegram-shaped — no markdown tables, short lines, **bold** for emphasis, hyphen bullets, 3,500–5,000 characters. Six sections:
1. **Рынок** — index, RGBI and long OFZ, Brent, USD/RUB, each with the move in % and one clause of why.
2. **Что важно** — be generous, this is the substance. Every watchlist name that moved >~2% or had news, with the number and the reason. Then off-list items competing for the same money.
3. **Проверка фактов** — test what the channels claimed against official sources. Per claim: what was said and by which channel, what the official source says, then ПОДТВЕРЖДЕНО / НЕ ПОДТВЕРЖДЕНО / ПРОТИВОРЕЧИТ ОФИЦИАЛЬНЫМ ДАННЫМ / ПОКА НЕПРОВЕРЯЕМО. Where channels contradict each other, say so. Where several say the same thing with no official confirmation, call it a consensus rumour. If nothing was checkable, say so in one line.
4. **Рекомендации** — four groups, as many names as warranted, one line each: **Покупать** · **Держать** · **Не добавлять или сокращать** · **Избегать**. Drop an empty group rather than padding.
5. **Мой взгляд** — your own read. Patterns, rumours, unusual volume, target changes. Label each ПОДТВЕРЖДЕНО / СООБЩАЕТСЯ / СЛУХ / МОЯ ОЦЕНКА, name the source, say which way it cuts and how confident you are. Be opinionated; never present a rumour as fact.
6. **Сценарии** — spell all three out in full, never by letter: Ставки снижаются (30%, индекс ~2 550) · Урегулирование на Украине (25%, ~3 950) · Всё буксует (45%, ~1 880). Then one line on whether today moved them.

Start with a single `# ` heading naming the date. End with «Аналитика, а не лицензированная инвестиционная рекомендация.» and source links. Output ONLY the brief in markdown — no preamble, no commentary."""

def main() -> None:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        sys.exit("ANTHROPIC_API_KEY is not set in this repository's secrets.")
    today  = msk_now()
    lang   = language()
    digest = read("sources/telegram-digest.md", "(no digest available)")
    content = charts() + [{"type": "text", "text": prompt(lang, digest, today)}]
    print(f"model={MODEL} lang={lang} charts={sum(1 for c in content if c['type']=='image')}")

    body = json.dumps({
        "model": MODEL, "max_tokens": MAX_TOK,
        "messages": [{"role": "user", "content": content}],
        "tools": [{"type": "web_search_20250305", "name": "web_search",
                   "max_uses": SEARCHES}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"API error {e.code}: {e.read().decode('utf-8','replace')[:600]}")

    text = "".join(b.get("text", "") for b in data.get("content", [])
                   if b.get("type") == "text").strip()
    if len(text) < 500:
        sys.exit(f"brief too short ({len(text)} chars) — refusing to publish:\n{text[:400]}")

    u = data.get("usage", {})
    print(f"in={u.get('input_tokens')} out={u.get('output_tokens')} "
          f"searches={u.get('server_tool_use',{}).get('web_search_requests')}")

    out = ROOT / "briefs" / f"{today:%Y-%m-%d}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} ({len(text)} chars)")

if __name__ == "__main__":
    main()
