/**
 * Local test of the Worker against a stubbed KV and a stubbed Telegram.
 *
 * Nothing here touches the network. Every fetch is intercepted: calls to
 * api.telegram.org are recorded, calls to raw.githubusercontent.com are served
 * from a fixture. Run with:  node worker/test-worker.mjs
 */
import worker, { route, guessLang, nextBrief, chunk, mdToHtml } from "./worker.js";

let pass = 0, fail = 0;
const ok = (cond, what) => {
  if (cond) { pass++; console.log(`  ok    ${what}`); }
  else { fail++; console.log(`  FAIL  ${what}`); }
};
const section = (s) => console.log(`\n${s}\n${"-".repeat(s.length)}`);

/* ----------------------------------------------------------- the stubs */

function makeKV(initial = {}) {
  const store = new Map(Object.entries(initial));
  return {
    store,
    async get(k, opts) {
      const v = store.get(k);
      if (v === undefined) return null;
      return opts?.type === "json" ? JSON.parse(v) : v;
    },
    async put(k, v) { store.set(k, String(v)); },
    async delete(k) { store.delete(k); },
  };
}

let sent = [];
const BRIEF = "# Обзор\n\n" + "**Рынок** — индекс вырос. ".repeat(60) +
              "\n\nИсточники: https://example.com/a";

function stubFetch() {
  globalThis.fetch = async (urlStr, init) => {
    const u = String(urlStr);
    if (u.includes("api.telegram.org")) {
      const method = u.split("/").pop();
      const body = JSON.parse(init.body);
      sent.push({ method, body });
      if (method === "getMe") {
        return { ok: true, json: async () => ({ result: { username: "ShareMarkWatch_bot" } }) };
      }
      return { ok: true, json: async () => ({ ok: true, result: { message_id: sent.length } }) };
    }
    if (u.includes("raw.githubusercontent.com")) {
      return u.endsWith("2026-11-20.md")
        ? { ok: true, text: async () => BRIEF }
        : { ok: false, text: async () => "404" };
    }
    throw new Error(`unexpected fetch: ${u}`);
  };
}

const env = (kv) => ({
  STATE: kv,
  TELEGRAM_TOKEN: "000:test",
  OWNER_CHAT_ID: "100000001",
  WEBHOOK_SECRET: "s3cret",
  GITHUB_REPO: "badBlaBlaW/Moex-brief",
  BRIEF_TIME: "08:47",
});
const ctx = { waitUntil: (p) => p?.catch?.(() => {}) };

const hit = (text, chat = "100000001", from = { language_code: "ru" }) =>
  new Request("https://w.dev/", {
    method: "POST",
    headers: { "X-Telegram-Bot-Api-Secret-Token": "s3cret", "Content-Type": "application/json" },
    body: JSON.stringify({ message: { chat: { id: chat }, from, text } }),
  });

const texts = () => sent.filter((s) => s.method === "sendMessage").map((s) => s.body.text);
const reset = () => { sent = []; };

/* ----------------------------------------------------------- pure units */

section("pure functions");
ok(route("/start").do === "start", "/start");
ok(route("/start abc123").do === "redeem" && route("/start abc123").token === "abc123",
   "/start with a token is a redemption, not a greeting");
ok(route("/brief@ShareMarkWatch_bot").do === "brief", "command with @botname");
ok(route("📄 Последний обзор").do === "brief", "Russian button");
ok(route("🔗 Add a device").do === "invite", "invite button");
ok(route("что там по сберу").do === "help", "anything else falls through to help");
ok(guessLang({ language_code: "ru-RU" }) === "ru", "ru-RU detected as Russian");
ok(guessLang({ language_code: "en-GB" }) === "en", "en-GB detected as English");
ok(guessLang({}) === "en", "no language code falls back to English");
ok(chunk(BRIEF).every((p) => p.length <= 3800), "every chunk inside the cap");
ok(mdToHtml("**x** <b>").includes("<b>x</b>") && mdToHtml("**x** <b>").includes("&lt;b&gt;"),
   "bold converted, raw angle brackets escaped");
{
  const fri = new Date("2026-11-20T06:00:00Z");   // 09:00 MSK, after the brief
  const sat = new Date("2026-11-21T10:00:00Z");
  ok(nextBrief("ru", fri).includes("в понедельник"),
     "Friday after the brief points at Monday, not tomorrow");
  ok(nextBrief("en", sat).includes("Monday"), "Saturday points at Monday");
  ok(nextBrief("ru", new Date("2026-11-20T05:00:00Z")).startsWith("сегодня"),
     "Friday before the brief says today");
}

/* ----------------------------------------------------------- the handler */

section("a known owner");
{
  stubFetch(); reset();
  const kv = makeKV();
  await worker.fetch(hit("/start"), env(kv), ctx);
  ok(texts().length === 1 && texts()[0].includes("Я Марк"), "/start greets once");

  reset();
  await worker.fetch(hit("/start"), env(kv), ctx);
  ok(texts().length === 0, "a second /start inside the cooldown is ignored");

  reset();
  await worker.fetch(hit("🇷🇺 Русский"), env(kv), ctx);
  ok(await kv.get("lang:100000001") === "ru", "language stored per chat, in KV");
  ok(texts().some((t) => t.includes("по-русски")) && texts().some((t) => t.includes("обзор")),
     "confirms, then offers today's brief");

  reset();
  await worker.fetch(hit("Да, пришли"), env(kv), ctx);
  ok(texts().length >= 2, "brief sent as announcement plus parts");
  const kbs = sent.filter((s) => s.body.reply_markup);
  ok(kbs.length === 1, "keyboard rides on the final message only");
  ok(JSON.stringify(kbs[0].body.reply_markup).includes("Добавить устройство"),
     "menu is in Russian and offers the invite button");
}

section("invites and enrolment");
{
  stubFetch(); reset();
  const kv = makeKV({ "lang:100000001": "ru" });
  await worker.fetch(hit("🔗 Добавить устройство"), env(kv), ctx);
  const link = texts().join("\n").match(/https:\/\/t\.me\/\S+\?start=(\w+)/);
  ok(!!link, "invite message carries a deep link");
  const token = link[1];
  ok((await kv.get("invite", { type: "json" })).token === token, "token stored in KV");

  reset();
  await worker.fetch(hit("/start wrongtoken", "999000111"), env(kv), ctx);
  ok(texts().length === 1 && /invalid|недействительна/i.test(texts()[0]),
     "a stranger with a bad token is refused");
  ok(!(await kv.get("owners") || "").includes("999000111"), "and is not enrolled");

  reset();
  await worker.fetch(hit("какой прогноз?", "999000111"), env(kv), ctx);
  ok(texts().length === 0, "a stranger with no token gets nothing at all");

  reset();
  await worker.fetch(hit(`/start ${token}`, "999000111", { language_code: "en" }), env(kv), ctx);
  ok(texts().some((t) => t.includes("Device added")), "valid token enrols, in the client's language");
  ok(JSON.parse(await kv.get("owners")).includes("999000111"), "new chat added to owners");
  ok((await kv.get("invite")) === null, "token consumed");

  reset();
  await worker.fetch(hit(`/start ${token}`, "888000222"), env(kv), ctx);
  ok(texts().length === 1 && /invalid|недействительна/i.test(texts()[0]),
     "the same token cannot be used twice");
}

section("expired invite");
{
  stubFetch(); reset();
  const kv = makeKV({ invite: JSON.stringify({ token: "old", exp: Date.now() - 1000 }) });
  await worker.fetch(hit("/start old", "777000333"), env(kv), ctx);
  ok(/invalid|недействительна/i.test(texts()[0] || ""), "an expired token is refused");
}

section("publish fan-out");
{
  stubFetch(); reset();
  const kv = makeKV({
    owners: JSON.stringify(["999000111"]),
    "lang:100000001": "ru",
    "lang:999000111": "en",
  });
  const req = new Request("https://w.dev/publish", {
    method: "POST",
    headers: { "X-Publish-Secret": "s3cret", "Content-Type": "application/json" },
    body: JSON.stringify({ markdown: BRIEF, date: "2026-11-20" }),
  });
  const res = await worker.fetch(req, env(kv), ctx);
  const out = await res.json();
  ok(res.status === 200 && out.ok, "publish accepted");
  ok(out.recipients === 2 && out.sent === 2, `fanned out to both chats (${out.sent})`);
  const chats = new Set(sent.map((s) => s.body.chat_id));
  ok(chats.has("100000001") && chats.has("999000111"), "owner and enrolled device both reached");
  ok((await kv.get("brief:latest")) === BRIEF, "brief cached for the /brief button");

  reset();
  const bad = new Request("https://w.dev/publish", {
    method: "POST", headers: { "X-Publish-Secret": "wrong" }, body: "{}",
  });
  ok((await worker.fetch(bad, env(kv), ctx)).status === 403, "wrong publish secret rejected");

  reset();
  const short = new Request("https://w.dev/publish", {
    method: "POST",
    headers: { "X-Publish-Secret": "s3cret", "Content-Type": "application/json" },
    body: JSON.stringify({ markdown: "too short" }),
  });
  ok((await worker.fetch(short, env(kv), ctx)).status === 400, "a stub brief is refused");
  ok(sent.length === 0, "and nothing was sent");
}

section("webhook guard");
{
  stubFetch(); reset();
  const kv = makeKV();
  const spoof = new Request("https://w.dev/", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: { chat: { id: "100000001" }, text: "/brief" } }),
  });
  ok((await worker.fetch(spoof, env(kv), ctx)).status === 403, "no secret header rejected");
  ok(sent.length === 0, "and nothing was sent");
}

section("brief fetched from the public repo when KV is cold");
{
  stubFetch(); reset();
  const kv = makeKV({ "lang:100000001": "ru" });
  // Fixture serves only 2026-11-20, so the walk-back has to find it.
  const realNow = Date.now;
  Date.now = () => new Date("2026-11-21T09:00:00Z").getTime();
  try {
    await worker.fetch(hit("/brief"), env(kv), ctx);
    ok(texts().some((t) => t.includes("Рынок")), "walked back a day and found the brief");
    ok((await kv.get("brief:latest")) === BRIEF, "and cached it");
  } finally { Date.now = realNow; }
}

console.log(`\n${"=".repeat(46)}`);
console.log(fail ? `FAILED — ${fail} of ${pass + fail}` : `ALL ${pass} CHECKS PASSED`);
process.exit(fail ? 1 : 0);
