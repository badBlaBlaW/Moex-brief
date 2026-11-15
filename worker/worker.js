/**
 * MarkWatch — Telegram webhook.
 *
 * Telegram pushes every message here the instant it is sent, so replies are
 * immediate. The language choice is written back to config.json in the brief
 * repository, which is what the daily brief reads before it writes a word.
 *
 * Secrets required (Worker → Settings → Variables and Secrets):
 *   TELEGRAM_TOKEN    from @BotFather
 *   TELEGRAM_CHAT_ID  the owner's chat id; every other chat is ignored
 *   WEBHOOK_SECRET    any long random string, also passed to setWebhook
 *   GITHUB_TOKEN      fine-grained PAT, Contents: Read and write, this repo only
 *   GITHUB_REPO       e.g. badBlaBlaW/Moex-brief
 */

const GREETING = {
  en:
    "Hello, I'm <b>Mark</b>.\n\n" +
    "I keep watch over the Moscow Exchange and send you a short brief every " +
    "weekday morning before the open — what moved, what it means, and what " +
    "I'd do about it.\n\n" +
    "I've set myself to <b>English</b> to match your Telegram. " +
    "Use the buttons below to change that at any time.",
  ru:
    "Привет, я <b>Марк</b>.\n\n" +
    "Я слежу за Московской биржей и каждое утро по будням — до открытия " +
    "торгов — присылаю короткий обзор: что изменилось, что это значит и что " +
    "я бы с этим делал.\n\n" +
    "Язык выбран по настройкам вашего Telegram — <b>русский</b>. " +
    "Изменить можно кнопкой ниже в любой момент.",
};

const BTN_SWITCH = { en: "🇷🇺 Русский", ru: "🇬🇧 English" };
const BTN_HELP = { en: "❓ Help", ru: "❓ Помощь" };

const SWITCHED = {
  en: "Done — from the next brief onward, everything will be in <b>English</b>.",
  ru: "Готово — со следующего обзора всё будет на <b>русском</b>.",
};

const HELP = {
  en:
    "<b>How this works</b>\n\n" +
    "A brief arrives automatically every weekday at <b>08:52 Moscow time</b>, " +
    "about an hour before the market opens.\n\n" +
    "There is nothing to do in between — just read it. The buttons below " +
    "switch language; the change applies to the next brief.\n\n" +
    "Each brief covers: the tape, watchlist names that actually moved, ranked " +
    "recommendations, my own read on rumours and patterns, and whether the " +
    "scenario probabilities have shifted.",
  ru:
    "<b>Как это работает</b>\n\n" +
    "Обзор приходит автоматически каждый будний день в <b>08:52 по Москве</b>, " +
    "примерно за час до открытия торгов.\n\n" +
    "Между обзорами делать ничего не нужно — просто читайте. Кнопки ниже " +
    "меняют язык; изменение вступит в силу со следующего обзора.\n\n" +
    "В каждом обзоре: рынок, бумаги из списка, которые реально двигались, " +
    "ранжированные рекомендации, мой личный взгляд на слухи и закономерности, " +
    "и сдвинулись ли вероятности сценариев.",
};

const DISCLAIMER = {
  en: "<i>Analysis, not licensed investment advice.</i>",
  ru: "<i>Аналитика, а не лицензированная инвестиционная рекомендация.</i>",
};

const COMMANDS = {
  en: [{ command: "help", description: "How this works" },
       { command: "ru", description: "Переключить на русский" }],
  ru: [{ command: "help", description: "Как это работает" },
       { command: "en", description: "Switch to English" }],
};

export function detect(code) {
  return (code || "").toLowerCase().startsWith("ru") ? "ru" : "en";
}

export function keyboard(lang) {
  return {
    keyboard: [[{ text: BTN_SWITCH[lang] }, { text: BTN_HELP[lang] }]],
    resize_keyboard: true,
    is_persistent: true,
  };
}

/** Pure routing: what should the bot do with this text? */
export function route(raw) {
  const text = (raw || "").trim();
  const cmd = text.toLowerCase().split("@")[0];
  if (cmd === "/start") return { action: "start" };
  if (cmd === "/ru" || text === BTN_SWITCH.en) return { action: "switch", lang: "ru" };
  if (cmd === "/en" || text === BTN_SWITCH.ru) return { action: "switch", lang: "en" };
  return { action: "help" };
}

async function tg(env, method, payload) {
  const r = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_TOKEN}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) console.log(`${method} failed: ${r.status} ${await r.text()}`);
  return r;
}

const send = (env, text, lang) =>
  tg(env, "sendMessage", {
    chat_id: env.TELEGRAM_CHAT_ID,
    text,
    parse_mode: "HTML",
    disable_web_page_preview: true,
    reply_markup: keyboard(lang),
  });

const GH = (env, path) => `https://api.github.com/repos/${env.GITHUB_REPO}/contents/${path}`;
const ghHeaders = (env) => ({
  Authorization: `Bearer ${env.GITHUB_TOKEN}`,
  Accept: "application/vnd.github+json",
  "User-Agent": "markwatch-worker",
});

async function readConfig(env) {
  try {
    const r = await fetch(GH(env, "config.json"), { headers: ghHeaders(env) });
    if (!r.ok) return { cfg: { language: "en" }, sha: null };
    const j = await r.json();
    const cfg = JSON.parse(atob(j.content.replace(/\n/g, "")));
    return { cfg, sha: j.sha };
  } catch (e) {
    console.log("readConfig failed:", e);
    return { cfg: { language: "en" }, sha: null };
  }
}

async function writeLanguage(env, lang) {
  const { cfg, sha } = await readConfig(env);
  if (cfg.language === lang && sha) return;          // nothing to change
  const next = { ...cfg, language: lang, onboarded: true };
  const body = {
    message: `bot: language -> ${lang}`,
    content: btoa(unescape(encodeURIComponent(JSON.stringify(next, null, 2) + "\n"))),
    ...(sha ? { sha } : {}),
  };
  const r = await fetch(GH(env, "config.json"), {
    method: "PUT", headers: ghHeaders(env), body: JSON.stringify(body),
  });
  if (!r.ok) console.log(`config write failed: ${r.status} ${await r.text()}`);
}

export default {
  async fetch(request, env, ctx) {
    if (request.method === "GET") return new Response("MarkWatch webhook: up", { status: 200 });
    if (request.method !== "POST") return new Response("ok", { status: 200 });

    // Only Telegram knows this header's value.
    if (request.headers.get("X-Telegram-Bot-Api-Secret-Token") !== env.WEBHOOK_SECRET) {
      return new Response("forbidden", { status: 403 });
    }

    let update;
    try { update = await request.json(); } catch { return new Response("ok"); }

    const msg = update.message;
    if (!msg) return new Response("ok");

    // The bot answers its owner and nobody else.
    if (String(msg.chat?.id) !== String(env.TELEGRAM_CHAT_ID)) {
      return new Response("ok");
    }

    const r = route(msg.text);

    if (r.action === "start") {
      const lang = detect(msg.from?.language_code);
      await send(env, `${GREETING[lang]}\n\n${DISCLAIMER[lang]}`, lang);
      ctx.waitUntil(Promise.all([
        writeLanguage(env, lang),
        tg(env, "setMyCommands", { commands: COMMANDS[lang] }),
      ]));
      return new Response("ok");
    }

    if (r.action === "switch") {
      await send(env, SWITCHED[r.lang], r.lang);     // reply first, persist after
      ctx.waitUntil(Promise.all([
        writeLanguage(env, r.lang),
        tg(env, "setMyCommands", { commands: COMMANDS[r.lang] }),
      ]));
      return new Response("ok");
    }

    const { cfg } = await readConfig(env);
    const lang = cfg.language === "ru" ? "ru" : "en";
    await send(env, HELP[lang], lang);
    return new Response("ok");
  },
};
