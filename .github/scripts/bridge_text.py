"""Conversation text for the temporary bridge. Mirrors worker/worker.js.

The Worker is the real implementation; this exists only so the bot answers
before Cloudflare is set up. Deleted together with listen.py and listen.yml.
"""
from datetime import datetime, timedelta, timezone

ASK_LANGUAGE = (
    "👋 <b>Привет! Я Марк.</b>\n"
    "Присылаю короткий обзор Мосбиржи каждое утро по будням — до открытия торгов.\n\n"
    "👋 <b>Hi, I'm Mark.</b>\n"
    "I send a short Moscow Exchange brief every weekday morning, before the open.\n\n"
    "На каком языке присылать обзоры?  /  Which language would you like?"
)
LANG_BTN  = {"ru": "🇷🇺 Русский", "en": "🇬🇧 English"}
OFFER_BTN = {"ru": {"yes": "Да, пришли", "no": "Нет, спасибо"},
             "en": {"yes": "Yes, send it", "no": "No thanks"}}
MENU_BTN  = {"ru": {"lang": "🇬🇧 English", "brief": "📄 Последний обзор", "help": "❓ Помощь"},
             "en": {"lang": "🇷🇺 Русский", "brief": "📄 Latest brief", "help": "❓ Help"}}
CONFIRMED = {"ru": "Отлично — буду писать по-русски.\n\nСледующий обзор: <b>{w}</b>.",
             "en": "English it is.\n\nYour next brief: <b>{w}</b>."}
OFFER     = {"ru": "Прислать сегодняшний обзор прямо сейчас?",
             "en": "Want today's brief now?"}
DECLINED  = {"ru": "Хорошо. Тогда {w}.", "en": "Right — see you {w}."}
NO_BRIEF  = {"ru": "Сегодняшнего обзора ещё нет — первый придёт {w}.",
             "en": "There is no brief yet — the first one arrives {w}."}
SENDING   = {"ru": "Сейчас пришлю 👇", "en": "Here it comes 👇"}
HELP = {
    "ru": ("<b>Как это работает</b>\n\n"
           "Обзор приходит сам, каждый будний день в <b>08:52 МСК</b> — примерно за час "
           "до открытия торгов.\n\nКнопки ниже: сменить язык или прислать последний обзор."),
    "en": ("<b>How this works</b>\n\n"
           "A brief arrives on its own every weekday at <b>08:52 Moscow time</b>, about "
           "an hour before the market opens.\n\nThe buttons below switch language or "
           "resend the latest brief."),
}
DISCLAIMER = {"ru": "<i>Аналитика, а не лицензированная инвестиционная рекомендация.</i>",
              "en": "<i>Analysis, not licensed investment advice.</i>"}
COMMANDS = {
    "ru": [{"command": "brief", "description": "Последний обзор"},
           {"command": "help", "description": "Как это работает"},
           {"command": "en", "description": "Switch to English"}],
    "en": [{"command": "brief", "description": "Latest brief"},
           {"command": "help", "description": "How this works"},
           {"command": "ru", "description": "Переключить на русский"}],
}
_RU = ["в воскресенье","в понедельник","во вторник","в среду","в четверг","в пятницу","в субботу"]
_EN = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]

def next_brief(lang, now=None):
    """When the next brief lands, in words. Briefs go out 08:52 MSK, Mon-Fri."""
    msk = (now or datetime.now(timezone.utc)) + timedelta(hours=3)
    dow = (msk.weekday() + 1) % 7                       # 0 Sun .. 6 Sat
    if msk.weekday() < 5 and msk.hour*60 + msk.minute < 8*60 + 52:
        return "сегодня в 08:52 МСК" if lang == "ru" else "today at 08:52 Moscow time"
    d, hops = dow, 0
    while True:
        d = (d + 1) % 7; hops += 1
        if 1 <= d <= 5: break
    if hops == 1:
        return "завтра в 08:52 МСК" if lang == "ru" else "tomorrow at 08:52 Moscow time"
    return f"{_RU[d]} в 08:52 МСК" if lang == "ru" else f"on {_EN[d]} at 08:52 Moscow time"

def keyboard(*rows_):
    return {"keyboard": [[{"text": t} for t in r] for r in rows_],
            "resize_keyboard": True, "is_persistent": True}

kb_language = lambda: keyboard([LANG_BTN["ru"], LANG_BTN["en"]])
kb_offer    = lambda l: keyboard([OFFER_BTN[l]["yes"], OFFER_BTN[l]["no"]])
kb_menu     = lambda l: keyboard([MENU_BTN[l]["brief"]], [MENU_BTN[l]["lang"], MENU_BTN[l]["help"]])
