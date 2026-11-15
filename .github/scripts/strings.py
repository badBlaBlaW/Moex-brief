"""Text used when SENDING a brief.

Everything Mark says in conversation — the greeting, help, the language
confirmations — lives in worker/worker.js, because the Cloudflare Worker is
what answers messages. Do not duplicate those strings here: one source of
truth per string.
"""

# Reply-keyboard buttons. The language button always offers the OTHER language.
# These must stay identical to BTN_SWITCH / BTN_HELP in worker/worker.js —
# the Worker matches on this exact text when the user taps a button.
BTN_SWITCH = {"en": "🇷🇺 Русский", "ru": "🇬🇧 English"}
BTN_HELP   = {"en": "❓ Help",      "ru": "❓ Помощь"}

def keyboard(lang: str) -> dict:
    """A persistent keyboard that stays above the text field on every message."""
    return {
        "keyboard": [[{"text": BTN_SWITCH[lang]}, {"text": BTN_HELP[lang]}]],
        "resize_keyboard": True,
        "is_persistent": True,
    }

# Part counter on a brief split across several messages.
PART = {"en": "({i}/{n})", "ru": "({i} из {n})"}
