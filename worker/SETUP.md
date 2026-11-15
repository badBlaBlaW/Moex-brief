# Instant replies — Cloudflare Worker setup

Telegram pushes each message to this Worker the moment you send it, so Mark
answers immediately. About 15 minutes, all free, all in a browser.

**Do the steps in order.** Step 5 switches Telegram over, and until the Worker
exists there is nothing for it to switch to.

---

## 1. Make a GitHub token (so Mark can remember your language)

1. Go to **github.com/settings/personal-access-tokens/new**
2. **Token name:** `markwatch-worker`
3. **Expiration:** 1 year
4. **Repository access** → **Only select repositories** → pick **Moex-brief**
5. **Permissions** → **Repository permissions** → find **Contents** → set to
   **Read and write**
6. **Generate token**, then copy it. It starts `github_pat_...`
   You cannot see it again after leaving the page.

## 2. Make a webhook secret

Any long random string of your own invention — letters and digits, 30+
characters, no spaces. Write it down; you need it twice.

## 3. Create the Worker

1. Sign up free at **dash.cloudflare.com**
2. Left sidebar → **Compute (Workers)** → **Create** → **Start with Hello World**
3. Name it `markwatch` → **Deploy**
4. Click **Edit code**
5. Delete everything in the editor, paste the entire contents of `worker.js`
6. **Deploy**

Copy the Worker's address — it looks like
`https://markwatch.<your-subdomain>.workers.dev`

## 4. Add the five secrets

In the Worker → **Settings** → **Variables and Secrets** → **Add**.
For each one choose type **Secret**, not Text.

| Name | Value |
|------|-------|
| `TELEGRAM_TOKEN` | from @BotFather |
| `TELEGRAM_CHAT_ID` | `<your chat id>` |
| `WEBHOOK_SECRET` | the random string from step 2 |
| `GITHUB_TOKEN` | the `github_pat_...` from step 1 |
| `GITHUB_REPO` | `badBlaBlaW/Moex-brief` |

**Deploy** again after adding them.

## 5. Point Telegram at the Worker

Open this in a browser, replacing the three bracketed parts:

    https://api.telegram.org/bot<TOKEN>/setWebhook?url=<WORKER_URL>&secret_token=<WEBHOOK_SECRET>

You should see `{"ok":true,"result":true,"description":"Webhook was set"}`.

## 6. Test

Send `/start` to the bot. Within a second Mark should ask, in both languages,
which one you want. Then:

1. Tap 🇷🇺 Русский or 🇬🇧 English
2. He confirms and tells you when the next brief lands
3. He asks whether to send today's brief now
4. Tap yes and it arrives; tap no and he signs off until the next one

## 7. Remove the temporary bridge

Once the webhook works, delete these three files from the repository — they
were only there to answer the bot before the Worker existed:

    .github/workflows/listen.yml
    .github/scripts/listen.py
    .github/scripts/bridge_text.py

They retire themselves quietly if you forget (Telegram stops serving
getUpdates once a webhook is set), but there is no reason to keep them.

---

## Checking on it

Worker not replying? Cloudflare dashboard → your Worker → **Logs** → **Begin log
stream**, then message the bot. Every request and error appears live.

Telegram's own view of the connection:

    https://api.telegram.org/bot<TOKEN>/getWebhookInfo

`last_error_message` is the field that matters.

## Turning it off

    https://api.telegram.org/bot<TOKEN>/deleteWebhook

The daily briefs keep arriving either way — they do not go through the Worker.
Only the buttons stop working.

## What costs what

Cloudflare's free tier is 100,000 requests a day. A bot used by one person uses
a handful. The Worker sleeps at zero cost between messages.
