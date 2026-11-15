/**
 * MarkWatch — Telegram webhook.
 *
 * Telegram pushes each message here the instant it is sent, so Mark answers
 * immediately. Conversation state and the language choice live in config.json
 * in the brief repository, which is also what the daily brief reads.
 *
 * Secrets (Worker → Settings → Variables and Secrets):
 *   TELEGRAM_TOKEN    from @BotFather
 *   TELEGRAM_CHAT_ID  the owner's chat id; every other chat is ignored
 *   WEBHOOK_SECRET    a long random string, also passed to setWebhook
 *   GITHUB_TOKEN      fine-grained PAT, Contents: Read and write, this repo only
 *   GITHUB_REPO       e.g. badBlaBlaW/Moex-brief
 */
/* ---- Mark's conversation text (inlined so this is one file) ---- */
const ASK_LANGUAGE =
  "👋 <b>Привет! Я Марк.</b>\n" +
  "Присылаю короткий обзор Мосбиржи каждое утро по будням — до открытия торгов.\n\n" +
  "👋 <b>Hi, I'm Mark.</b>\n" +
  "I send a short Moscow Exchange brief every weekday morning, before the open.\n\n" +
  "На каком языке присылать обзоры?  /  Which language would you like?";

const LANG_BTN = { ru: "🇷🇺 Русский", en: "🇬🇧 English" };

const CONFIRMED = {
  ru: (when) =>
    `Отлично — буду писать по-русски.\n\nСледующий обзор: <b>${when}</b>.`,
  en: (when) =>
    `English it is.\n\nYour next brief: <b>${when}</b>.`,
};

const OFFER = {
  ru: "Прислать сегодняшний обзор прямо сейчас?",
  en: "Want today's brief now?",
};

const OFFER_BTN = {
  ru: { yes: "Да, пришли", no: "Нет, спасибо" },
  en: { yes: "Yes, send it", no: "No thanks" },
};

const DECLINED = {
  ru: (when) => `Хорошо. Тогда ${when}.`,
  en: (when) => `Right — see you ${when}.`,
};

const NO_BRIEF_YET = {
  ru: (when) =>
    `Сегодняшнего обзора ещё нет — первый придёт ${when}.`,
  en: (when) =>
    `There is no brief yet — the first one arrives ${when}.`,
};

const SENDING = { ru: "Сейчас пришлю 👇", en: "Here it comes 👇" };

const SWITCHED = {
  ru: "Готово — со следующего обзора всё будет на <b>русском</b>.",
  en: "Done — from the next brief onward, everything will be in <b>English</b>.",
};

const HELP = {
  ru:
    "<b>Как это работает</b>\n\n" +
    "Обзор приходит сам, каждый будний день в <b>08:52 МСК</b> — примерно за час " +
    "до открытия торгов.\n\n" +
    "В каждом обзоре: рынок, бумаги из списка, которые реально двигались, " +
    "рекомендации по порядку важности, мой личный взгляд на слухи и " +
    "закономерности, и сдвинулись ли вероятности сценариев.\n\n" +
    "Кнопки ниже: сменить язык или прислать последний обзор ещё раз.",
  en:
    "<b>How this works</b>\n\n" +
    "A brief arrives on its own every weekday at <b>08:52 Moscow time</b>, about " +
    "an hour before the market opens.\n\n" +
    "Each one covers: the tape, watchlist names that actually moved, ranked " +
    "recommendations, my own read on rumours and patterns, and whether the " +
    "scenario probabilities have shifted.\n\n" +
    "The buttons below switch language or resend the latest brief.",
};

const MENU_BTN = {
  ru: { lang: "🇬🇧 English", brief: "📄 Последний обзор", help: "❓ Помощь" },
  en: { lang: "🇷🇺 Русский", brief: "📄 Latest brief", help: "❓ Help" },
};

const DISCLAIMER = {
  ru: "<i>Аналитика, а не лицензированная инвестиционная рекомендация.</i>",
  en: "<i>Analysis, not licensed investment advice.</i>",
};

const COMMANDS = {
  ru: [{ command: "brief", description: "Последний обзор" },
       { command: "help", description: "Как это работает" },
       { command: "en", description: "Switch to English" }],
  en: [{ command: "brief", description: "Latest brief" },
       { command: "help", description: "How this works" },
       { command: "ru", description: "Переключить на русский" }],
};

/** When the next brief lands, in words. Briefs go out 08:52 MSK, Mon–Fri. */
function nextBrief(lang, now = new Date()) {
  const msk = new Date(now.getTime() + 3 * 3600 * 1000);   // UTC+3
  const mins = msk.getUTCHours() * 60 + msk.getUTCMinutes();
  const DOW = msk.getUTCDay();                             // 0 Sun .. 6 Sat
  const weekday = (d) => d >= 1 && d <= 5;

  if (weekday(DOW) && mins < 8 * 60 + 52) {
    return lang === "ru" ? "сегодня в 08:52 МСК" : "today at 08:52 Moscow time";
  }
  let d = DOW, hops = 0;
  do { d = (d + 1) % 7; hops++; } while (!weekday(d));
  if (hops === 1) {
    return lang === "ru" ? "завтра в 08:52 МСК" : "tomorrow at 08:52 Moscow time";
  }
  const RU = ["в воскресенье","в понедельник","во вторник","в среду","в четверг","в пятницу","в субботу"];
  const EN = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
  return lang === "ru" ? `${RU[d]} в 08:52 МСК` : `on ${EN[d]} at 08:52 Moscow time`;
}

const T = { ASK_LANGUAGE, LANG_BTN, CONFIRMED, OFFER, OFFER_BTN, DECLINED, NO_BRIEF_YET, SENDING, SWITCHED, HELP, MENU_BTN, DISCLAIMER, COMMANDS, nextBrief };


const LIMIT = 3800;                       // Telegram caps a message at 4096

/* ---------------------------------------------------------------- Telegram */

async function tg(env, method, payload) {
  const r = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_TOKEN}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) console.log(`${method} -> ${r.status} ${await r.text()}`);
  return r;
}

const rows = (...r) => ({ keyboard: r, resize_keyboard: true, is_persistent: true });

const kbLanguage = () => rows([{ text: T.LANG_BTN.ru }, { text: T.LANG_BTN.en }]);
const kbOffer = (l) => rows([{ text: T.OFFER_BTN[l].yes }, { text: T.OFFER_BTN[l].no }]);
const kbMenu = (l) => rows(
  [{ text: T.MENU_BTN[l].brief }],
  [{ text: T.MENU_BTN[l].lang }, { text: T.MENU_BTN[l].help }],
);

async function say(env, text, markup) {
  return tg(env, "sendMessage", {
    chat_id: env.TELEGRAM_CHAT_ID, text, parse_mode: "HTML",
    disable_web_page_preview: true, ...(markup ? { reply_markup: markup } : {}),
  });
}

/* ------------------------------------------------------------------ GitHub */

const ghUrl = (env, p) => `https://api.github.com/repos/${env.GITHUB_REPO}/contents/${p}`;
const ghHead = (env) => ({
  Authorization: `Bearer ${env.GITHUB_TOKEN}`,
  Accept: "application/vnd.github+json",
  "User-Agent": "markwatch-worker",
});
const b64decode = (s) =>
  decodeURIComponent(Array.prototype.map
    .call(atob(s.replace(/\n/g, "")), (c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
    .join(""));
const b64encode = (s) => btoa(unescape(encodeURIComponent(s)));

async function readConfig(env) {
  try {
    const r = await fetch(ghUrl(env, "config.json"), { headers: ghHead(env) });
    if (!r.ok) return { cfg: {}, sha: null };
    const j = await r.json();
    return { cfg: JSON.parse(b64decode(j.content)), sha: j.sha };
  } catch (e) { console.log("readConfig:", e); return { cfg: {}, sha: null }; }
}

async function saveConfig(env, patch) {
  const { cfg, sha } = await readConfig(env);
  const next = { ...cfg, ...patch };
  const r = await fetch(ghUrl(env, "config.json"), {
    method: "PUT", headers: ghHead(env),
    body: JSON.stringify({
      message: "bot: update settings",
      content: b64encode(JSON.stringify(next, null, 2) + "\n"),
      ...(sha ? { sha } : {}),
    }),
  });
  if (!r.ok) console.log(`saveConfig -> ${r.status} ${await r.text()}`);
}

async function latestBrief(env) {
  try {
    const r = await fetch(ghUrl(env, "briefs"), { headers: ghHead(env) });
    if (!r.ok) return null;
    const files = (await r.json())
      .filter((f) => f.name.endsWith(".md") && f.name.toLowerCase() !== "readme.md")
      .sort((a, b) => a.name.localeCompare(b.name));
    if (!files.length) return null;
    const f = await fetch(ghUrl(env, `briefs/${files.at(-1).name}`), { headers: ghHead(env) });
    if (!f.ok) return null;
    return b64decode((await f.json()).content);
  } catch (e) { console.log("latestBrief:", e); return null; }
}

/* --------------------------------------------------------------- Rendering */

export function mdToHtml(md) {
  return md.split("\n").map((line) => {
    let s = line.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    s = s.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
    s = s.replace(/(^|[^\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])/g, "$1<i>$2</i>");
    s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
    s = s.replace(/\[(.+?)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2">$1</a>');
    const h = s.match(/^#{1,6}\s+(.*)$/);
    if (h) s = `<b>${h[1]}</b>`;
    s = s.replace(/^\s*[-*]\s+/, "• ");
    if (/^\s*([-*_])(\s*\1){2,}\s*$/.test(line)) s = "————————————";
    return s;
  }).join("\n");
}

export function chunk(text, limit = LIMIT) {
  const parts = []; let cur = "";
  for (let block of text.split("\n\n")) {
    while (block.length > limit) {
      if (cur.trim()) { parts.push(cur.trim()); cur = ""; }
      parts.push(block.slice(0, limit)); block = block.slice(limit);
    }
    if (cur.length + block.length + 2 > limit) {
      if (cur.trim()) parts.push(cur.trim());
      cur = block;
    } else cur = cur ? `${cur}\n\n${block}` : block;
  }
  if (cur.trim()) parts.push(cur.trim());
  return parts.filter((p) => p.trim());
}

async function sendBrief(env, lang) {
  const md = await latestBrief(env);
  if (!md) { await say(env, T.NO_BRIEF_YET[lang](T.nextBrief(lang)), kbMenu(lang)); return; }
  await say(env, T.SENDING[lang]);
  const parts = chunk(mdToHtml(md.trim()));
  for (let i = 0; i < parts.length; i++) {
    const last = i === parts.length - 1;
    const tag = parts.length > 1
      ? `\n\n<i>(${i + 1}${lang === "ru" ? " из " : "/"}${parts.length})</i>` : "";
    await say(env, parts[i] + tag, last ? kbMenu(lang) : undefined);
  }
}

/* ----------------------------------------------------------------- Routing */

export function route(raw, lang) {
  const t = (raw || "").trim();
  const c = t.toLowerCase().split("@")[0];
  if (c === "/start") return { do: "start" };
  if (t === T.LANG_BTN.ru || c === "/ru") return { do: "language", lang: "ru" };
  if (t === T.LANG_BTN.en || c === "/en") return { do: "language", lang: "en" };
  if (t === T.OFFER_BTN.ru.yes || t === T.OFFER_BTN.en.yes) return { do: "yes" };
  if (t === T.OFFER_BTN.ru.no  || t === T.OFFER_BTN.en.no)  return { do: "no" };
  if (c === "/brief" || t === T.MENU_BTN.ru.brief || t === T.MENU_BTN.en.brief)
    return { do: "brief" };
  return { do: "help" };
}

export default {
  async fetch(request, env, ctx) {
    if (request.method === "GET") return new Response("MarkWatch webhook: up");
    if (request.method !== "POST") return new Response("ok");
    if (request.headers.get("X-Telegram-Bot-Api-Secret-Token") !== env.WEBHOOK_SECRET)
      return new Response("forbidden", { status: 403 });

    let update;
    try { update = await request.json(); } catch { return new Response("ok"); }
    const msg = update.message;
    if (!msg || String(msg.chat?.id) !== String(env.TELEGRAM_CHAT_ID))
      return new Response("ok");

    const { cfg } = await readConfig(env);
    const lang = cfg.language === "ru" ? "ru" : "en";
    const r = route(msg.text, lang);

    if (r.do === "start") {
      await say(env, T.ASK_LANGUAGE, kbLanguage());
      ctx.waitUntil(saveConfig(env, { stage: "awaiting_language" }));
      return new Response("ok");
    }

    if (r.do === "language") {
      const L = r.lang;
      await say(env, T.CONFIRMED[L](T.nextBrief(L)));
      await say(env, T.OFFER[L], kbOffer(L));
      ctx.waitUntil(Promise.all([
        saveConfig(env, { language: L, stage: "awaiting_offer", onboarded: true }),
        tg(env, "setMyCommands", { commands: T.COMMANDS[L] }),
      ]));
      return new Response("ok");
    }

    if (r.do === "yes")   { await sendBrief(env, lang);
                            ctx.waitUntil(saveConfig(env, { stage: "idle" }));
                            return new Response("ok"); }

    if (r.do === "no")    { await say(env, T.DECLINED[lang](T.nextBrief(lang)) +
                                      "\n\n" + T.DISCLAIMER[lang], kbMenu(lang));
                            ctx.waitUntil(saveConfig(env, { stage: "idle" }));
                            return new Response("ok"); }

    if (r.do === "brief") { await sendBrief(env, lang); return new Response("ok"); }

    await say(env, T.HELP[lang], kbMenu(lang));
    return new Response("ok");
  },
};
