"""Conversation text for the temporary bridge only.

The real source of truth is worker/worker.js. This file exists so the bridge
can answer /start before the Worker is set up, and is deleted with the bridge.
"""
GREETING = {
    "en": ("Hello, I'm <b>Mark</b>.\n\n"
           "I keep watch over the Moscow Exchange and send you a short brief every "
           "weekday morning before the open — what moved, what it means, and what "
           "I'd do about it.\n\n"
           "I've set myself to <b>English</b> to match your Telegram. "
           "Use the buttons below to change that at any time."),
    "ru": ("Привет, я <b>Марк</b>.\n\n"
           "Я слежу за Московской биржей и каждое утро по будням — до открытия "
           "торгов — присылаю короткий обзор: что изменилось, что это значит и что "
           "я бы с этим делал.\n\n"
           "Язык выбран по настройкам вашего Telegram — <b>русский</b>. "
           "Изменить можно кнопкой ниже в любой момент."),
}
SWITCHED = {
    "en": "Done — from the next brief onward, everything will be in <b>English</b>.",
    "ru": "Готово — со следующего обзора всё будет на <b>русском</b>.",
}
HELP = {
    "en": ("<b>How this works</b>\n\n"
           "A brief arrives automatically every weekday at <b>08:52 Moscow time</b>, "
           "about an hour before the market opens.\n\n"
           "There is nothing to do in between — just read it. The buttons below "
           "switch language; the change applies to the next brief."),
    "ru": ("<b>Как это работает</b>\n\n"
           "Обзор приходит автоматически каждый будний день в <b>08:52 по Москве</b>, "
           "примерно за час до открытия торгов.\n\n"
           "Между обзорами делать ничего не нужно — просто читайте. Кнопки ниже "
           "меняют язык; изменение вступит в силу со следующего обзора."),
}
DISCLAIMER = {
    "en": "<i>Analysis, not licensed investment advice.</i>",
    "ru": "<i>Аналитика, а не лицензированная инвестиционная рекомендация.</i>",
}
COMMANDS = {
    "en": [{"command": "help", "description": "How this works"},
           {"command": "ru", "description": "Переключить на русский"}],
    "ru": [{"command": "help", "description": "Как это работает"},
           {"command": "en", "description": "Switch to English"}],
}
def detect(code):
    return "ru" if (code or "").lower().startswith("ru") else "en"
