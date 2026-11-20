/**
 * MarkWatch — Telegram webhook and brief fan-out.
 *
 * Telegram pushes each message here the instant it is sent, so Mark answers
 * immediately rather than whenever a polling job happens to be awake.
 *
 * All state lives in Workers KV, never in the repository: the repository is
 * public, and chat ids and live invite tokens must not be. Briefs are read
 * from raw.githubusercontent.com, which serves a public repo to anyone, so the
 * Worker holds no GitHub credential at all.
 *
 * The Worker also owns the recipient list. The daily job POSTs each finished
 * brief to /publish and this fans it out to everyone enrolled, so a device
 * that enrols itself through an invite link starts receiving briefs without
 * anyone editing a secret.
 *
 * Bindings (Worker → Settings):
 *   KV namespace, bound as        STATE
 *   secret  TELEGRAM_TOKEN        from @BotFather
 *   secret  OWNER_CHAT_ID         your own chat id; always allowed
 *   secret  WEBHOOK_SECRET        long random string, also passed to setWebhook
 *           and sent by the daily job as X-Publish-Secret
 *   var     GITHUB_REPO           e.g. badBlaBlaW/Moex-brief
 *   var     BRIEF_TIME            optional, default "08:47"
 */

/* ------------------------------------------------- Mark's conversation text */

const ASK_LANGUAGE =
  "👋 <b>Привет! Я Марк.</b>\n" +
  "Присылаю короткий обзор Мосбиржи каждое утро по будням — до открытия торгов.\n\n" +
  "👋 <b>Hi, I'm Mark.</b>\n" +
  "I send a short Moscow Exchange brief every weekday morning, before the open.\n\n" +
  "На каком языке присылать обзоры?  /  Which language would you like?";

const LANG_BTN = { ru: "🇷🇺 Русский", en: "🇬🇧 English" };

const CONFIRMED = {
  ru: (when) => `Отлично — буду писать по-русски.\n\nСледующий обзор: <b>${when}</b>.`,
  en: (when) => `English it is.\n\nYour next brief: <b>${when}</b>.`,
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
  ru: (when) => `Сегодняшнего обзора ещё нет — следующий придёт ${when}.`,
  en: (when) => `There is no brief yet — the next one arrives ${when}.`,
};

const SENDING = { ru: "Сейчас пришлю 👇", en: "Here it comes 👇" };

const SWITCHED = {
  ru: "Готово — со следующего обзора всё будет на <b>русском</b>.",
  en: "Done — from the next brief onward, everything will be in <b>English</b>.",
};

const HELP = {
  ru:
    "<b>Как это работает</b>\n\n" +
    "Обзор приходит сам, каждый будний день — примерно за час до открытия торгов.\n\n" +
    "В каждом обзоре: рынок, бумаги из списка, которые реально двигались, " +
    "рекомендации, мой личный взгляд на слухи и закономерности, проверка " +
    "фактов из Telegram-каналов и сдвинулись ли вероятности сценариев.\n\n" +
    "Кнопки ниже: прислать последний обзор, сменить язык, добавить ещё одно " +
    "устройство.",
  en:
    "<b>How this works</b>\n\n" +
    "A brief arrives on its own every weekday, about an hour before the market " +
    "opens.\n\n" +
    "Each one covers: the tape, watchlist names that actually moved, " +
    "recommendations, my own read on rumours and patterns, a fact-check of the " +
    "Telegram channels, and whether the scenario probabilities have shifted.\n\n" +
    "The buttons below resend the latest brief, switch language, or add another " +
    "device.",
};

const MENU_BTN = {
  ru: { brief: "📄 Последний обзор", lang: "🇬🇧 English", help: "❓ Помощь",
        invite: "🔗 Добавить устройство" },
  en: { brief: "📄 Latest brief", lang: "🇷🇺 Русский", help: "❓ Help",
        invite: "🔗 Add a device" },
};

const INVITE_MSG = {
  ru: (link, mins) =>
    "<b>Ссылка для нового устройства</b>\n\n" +
    `${link}\n\n` +
    `Откройте её на новом телефоне. Ссылка одноразовая и действует ${mins} минут.`,
  en: (link, mins) =>
    "<b>Link for a new device</b>\n\n" +
    `${link}\n\n` +
    `Open it on the new phone. One use only, valid for ${mins} minutes.`,
};

const ENROLLED = {
  ru: "✅ Устройство добавлено. Обзоры будут приходить и сюда.",
  en: "✅ Device added. Briefs will arrive here too.",
};

const INVITE_BAD = {
  ru: "Ссылка недействительна или уже использована. Попросите новую.",
  en: "That link is invalid or already used. Ask for a fresh one.",
};

const DISCLAIMER = {
  ru: "<i>Аналитика, а не лицензированная инвестиционная рекомендация.</i>",
  en: "<i>Analysis, not licensed investment advice.</i>",
};

const COMMANDS = {
  ru: [{ command: "brief", description: "Последний обзор" },
       { command: "help", description: "Как это работает" },
       { command: "invite", description: "Добавить устройство" },
       { command: "en", description: "Switch to English" }],
  en: [{ command: "brief", description: "Latest brief" },
       { command: "help", description: "How this works" },
       { command: "invite", description: "Add a device" },
       { command: "ru", description: "Переключить на русский" }],
};

const LIMIT = 3800;            // Telegram caps a message at 4096
const GREET_COOLDOWN_MS = 20_000;   // clients re-send /start on their own
const INVITE_MINUTES = 15;
const BRIEF_LOOKBACK_DAYS = 10;

/* ------------------------------------------------------------------ helpers */

/** When the next brief lands, in words. */
export function nextBrief(lang, now = new Date(), hhmm = "08:47") {
  const [H, M] = hhmm.split(":").map(Number);
  const msk = new Date(now.getTime() + 3 * 3600 * 1000);      // UTC+3
  const mins = msk.getUTCHours() * 60 + msk.getUTCMinutes();
  const DOW = msk.getUTCDay();                                // 0 Sun .. 6 Sat
  const weekday = (d) => d >= 1 && d <= 5;
  const at = lang === "ru" ? `в ${hhmm} МСК` : `at ${hhmm} Moscow time`;

  if (weekday(DOW) && mins < H * 60 + M) {
    return lang === "ru" ? `сегодня ${at}` : `today ${at}`;
  }
  let d = DOW, hops = 0;
  do { d = (d + 1) % 7; hops++; } while (!weekday(d));
  if (hops === 1) return lang === "ru" ? `завтра ${at}` : `tomorrow ${at}`;
  const RU = ["в воскресенье", "в понедельник", "во вторник", "в среду",
              "в четверг", "в пятницу", "в субботу"];
  const EN = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday",
              "Friday", "Saturday"];
  return lang === "ru" ? `${RU[d]} ${at}` : `on ${EN[d]} ${at}`;
}

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

/** Telegram sends the client's own language; honour it before asking. */
export function guessLang(from) {
  return String(from?.language_code || "").toLowerCase().startsWith("ru") ? "ru" : "en";
}

export function route(raw) {
  const t = (raw || "").trim();
  const first = t.split(/\s+/)[0].toLowerCase().split("@")[0];
  if (first === "/start") {
    const arg = t.split(/\s+/)[1];
    return arg ? { do: "redeem", token: arg } : { do: "start" };
  }
  if (t === LANG_BTN.ru || first === "/ru") return { do: "language", lang: "ru" };
  if (t === LANG_BTN.en || first === "/en") return { do: "language", lang: "en" };
  if (t === OFFER_BTN.ru.yes || t === OFFER_BTN.en.yes) return { do: "yes" };
  if (t === OFFER_BTN.ru.no || t === OFFER_BTN.en.no) return { do: "no" };
  if (first === "/brief" || t === MENU_BTN.ru.brief || t === MENU_BTN.en.brief)
    return { do: "brief" };
  if (first === "/invite" || t === MENU_BTN.ru.invite || t === MENU_BTN.en.invite)
    return { do: "invite" };
  return { do: "help" };
}

/* ----------------------------------------------------------------- KV state */

const rows = (...r) => ({ keyboard: r, resize_keyboard: true, is_persistent: true });
const kbLanguage = () => rows([{ text: LANG_BTN.ru }, { text: LANG_BTN.en }]);
const kbOffer = (l) => rows([{ text: OFFER_BTN[l].yes }, { text: OFFER_BTN[l].no }]);
const kbMenu = (l) => rows(
  [{ text: MENU_BTN[l].brief }],
  [{ text: MENU_BTN[l].lang }, { text: MENU_BTN[l].help }],
  [{ text: MENU_BTN[l].invite }],
);

async function getOwners(env) {
  const primary = String(env.OWNER_CHAT_ID || "").trim();
  let extra = [];
  try { extra = JSON.parse((await env.STATE.get("owners")) || "[]"); } catch { extra = []; }
  const all = primary ? [primary] : [];
  for (const c of extra) if (!all.includes(String(c))) all.push(String(c));
  return all;
}

async function addOwner(env, chatId) {
  const id = String(chatId);
  if (id === String(env.OWNER_CHAT_ID)) return;
  let extra = [];
  try { extra = JSON.parse((await env.STATE.get("owners")) || "[]"); } catch { extra = []; }
  if (!extra.map(String).includes(id)) {
    extra.push(id);
    await env.STATE.put("owners", JSON.stringify(extra));
  }
}

async function isOwner(env, chatId) {
  return (await getOwners(env)).includes(String(chatId));
}

const langKey = (c) => `lang:${c}`;
async function getLang(env, chatId, fallback = "en") {
  const v = await env.STATE.get(langKey(chatId));
  return v === "ru" || v === "en" ? v : fallback;
}
const setLang = (env, chatId, l) => env.STATE.put(langKey(chatId), l);

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

async function say(env, chatId, text, markup) {
  return tg(env, "sendMessage", {
    chat_id: chatId, text, parse_mode: "HTML", disable_web_page_preview: true,
    ...(markup ? { reply_markup: markup } : {}),
  });
}

async function botUsername(env) {
  const cached = await env.STATE.get("bot_username");
  if (cached) return cached;
  try {
    const r = await tg(env, "getMe", {});
    const u = (await r.json())?.result?.username;
    if (u) { await env.STATE.put("bot_username", u); return u; }
  } catch (e) { console.log("getMe:", e); }
  return null;
}

/* ------------------------------------------------------------------ briefs */

/**
 * The newest brief. /publish caches it in KV, so normally this costs no
 * subrequest. Otherwise walk back from today over raw.githubusercontent.com,
 * which needs no credential because the repository is public. A directory
 * cannot be listed over raw, hence the walk.
 */
async function latestBrief(env) {
  const cached = await env.STATE.get("brief:latest");
  if (cached) return cached;
  const base = `https://raw.githubusercontent.com/${env.GITHUB_REPO}/main/briefs`;
  const now = new Date(Date.now() + 3 * 3600 * 1000);
  for (let i = 0; i < BRIEF_LOOKBACK_DAYS; i++) {
    const d = new Date(now.getTime() - i * 86400 * 1000);
    const name = d.toISOString().slice(0, 10);
    try {
      const r = await fetch(`${base}/${name}.md`);
      if (r.ok) {
        const md = await r.text();
        if (md.trim().length > 500) {
          await env.STATE.put("brief:latest", md, { expirationTtl: 86400 });
          return md;
        }
      }
    } catch (e) { console.log("latestBrief:", e); }
  }
  return null;
}

async function sendBriefTo(env, chatId, lang, md, announce = false) {
  if (!md) {
    await say(env, chatId, NO_BRIEF_YET[lang](nextBrief(lang, new Date(), env.BRIEF_TIME)),
              kbMenu(lang));
    return 0;
  }
  if (announce) await say(env, chatId, SENDING[lang]);
  const parts = chunk(mdToHtml(md.trim()));
  for (let i = 0; i < parts.length; i++) {
    const last = i === parts.length - 1;
    const tag = parts.length > 1
      ? `\n\n<i>(${i + 1}${lang === "ru" ? " из " : "/"}${parts.length})</i>` : "";
    await say(env, chatId, parts[i] + tag, last ? kbMenu(lang) : undefined);
  }
  return parts.length;
}

/* ---------------------------------------------------------------- handlers */

async function handleMessage(env, ctx, msg) {
  const chatId = String(msg.chat.id);
  const r = route(msg.text);
  const known = await isOwner(env, chatId);

  // An unenrolled chat may do exactly one thing: redeem a valid invite.
  if (!known) {
    if (r.do !== "redeem") return;
    const stored = await env.STATE.get("invite", { type: "json" });
    const ok = stored && stored.token === r.token && Date.now() < stored.exp;
    const lang = guessLang(msg.from);
    if (!ok) { await say(env, chatId, INVITE_BAD[lang]); return; }
    await env.STATE.delete("invite");           // single use
    await addOwner(env, chatId);
    await setLang(env, chatId, lang);
    await say(env, chatId, ENROLLED[lang], kbMenu(lang));
    return;
  }

  const lang = await getLang(env, chatId, guessLang(msg.from));

  if (r.do === "start" || r.do === "redeem") {
    // Telegram clients re-send /start when a cleared chat is reopened or a deep
    // link is followed, which is what produced duplicate greetings before.
    const last = Number((await env.STATE.get(`greet:${chatId}`)) || 0);
    if (Date.now() - last < GREET_COOLDOWN_MS) return;
    await env.STATE.put(`greet:${chatId}`, String(Date.now()), { expirationTtl: 300 });
    await say(env, chatId, ASK_LANGUAGE, kbLanguage());
    return;
  }

  if (r.do === "language") {
    const L = r.lang;
    await setLang(env, chatId, L);
    await say(env, chatId, CONFIRMED[L](nextBrief(L, new Date(), env.BRIEF_TIME)));
    await say(env, chatId, OFFER[L], kbOffer(L));
    ctx.waitUntil(tg(env, "setMyCommands", { commands: COMMANDS[L] }));
    return;
  }

  if (r.do === "yes") {
    await sendBriefTo(env, chatId, lang, await latestBrief(env), true);
    return;
  }

  if (r.do === "no") {
    await say(env, chatId,
      DECLINED[lang](nextBrief(lang, new Date(), env.BRIEF_TIME)) + "\n\n" + DISCLAIMER[lang],
      kbMenu(lang));
    return;
  }

  if (r.do === "brief") {
    await sendBriefTo(env, chatId, lang, await latestBrief(env), true);
    return;
  }

  if (r.do === "invite") {
    const token = crypto.randomUUID().replace(/-/g, "").slice(0, 22);
    const exp = Date.now() + INVITE_MINUTES * 60_000;
    await env.STATE.put("invite", JSON.stringify({ token, exp }),
                        { expirationTtl: INVITE_MINUTES * 60 + 60 });
    const user = await botUsername(env);
    const link = user ? `https://t.me/${user}?start=${token}` : `/start ${token}`;
    await say(env, chatId, INVITE_MSG[lang](link, INVITE_MINUTES), kbMenu(lang));
    return;
  }

  await say(env, chatId, HELP[lang], kbMenu(lang));
}

/** The daily job POSTs the finished brief here; fan it out from KV. */
async function handlePublish(env, body) {
  const md = String(body?.markdown || "");
  if (md.trim().length < 500) {
    return { ok: false, error: "markdown missing or too short", sent: 0 };
  }
  await env.STATE.put("brief:latest", md, { expirationTtl: 86400 });
  const owners = await getOwners(env);
  let sent = 0, failed = [];
  for (const c of owners) {
    try {
      await sendBriefTo(env, c, await getLang(env, c, "ru"), md, false);
      sent++;
    } catch (e) { failed.push(c); console.log(`publish to ${c}:`, e); }
  }
  return { ok: true, recipients: owners.length, sent, failed: failed.length };
}

/* ----------------------------------------------------------------- routing */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (request.method === "GET") {
      return new Response("MarkWatch webhook: up");
    }
    if (request.method !== "POST") return new Response("ok");

    // The daily job's fan-out endpoint, guarded by the same shared secret.
    if (url.pathname === "/publish") {
      if (request.headers.get("X-Publish-Secret") !== env.WEBHOOK_SECRET) {
        return new Response("forbidden", { status: 403 });
      }
      let body;
      try { body = await request.json(); }
      catch { return Response.json({ ok: false, error: "bad json" }, { status: 400 }); }
      const result = await handlePublish(env, body);
      return Response.json(result, { status: result.ok ? 200 : 400 });
    }

    // Telegram's webhook.
    if (request.headers.get("X-Telegram-Bot-Api-Secret-Token") !== env.WEBHOOK_SECRET) {
      return new Response("forbidden", { status: 403 });
    }
    let update;
    try { update = await request.json(); } catch { return new Response("ok"); }
    const msg = update.message;
    if (!msg || !msg.chat || !msg.text) return new Response("ok");

    // Always answer Telegram promptly; a slow handler means repeated deliveries.
    try { await handleMessage(env, ctx, msg); }
    catch (e) { console.log("handleMessage:", e); }
    return new Response("ok");
  },
};
