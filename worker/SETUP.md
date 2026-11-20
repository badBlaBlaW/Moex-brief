# Instant replies — Cloudflare Worker setup

Right now the bot can only answer while a GitHub job happens to be running,
which is almost never. This puts Mark on a Cloudflare Worker: Telegram pushes
every message straight to it, so the bot replies the moment you press a button.

It also becomes the keeper of the device list, so a new phone can enrol itself
from a link instead of you editing a secret.

**Cost: nothing.** The free plan allows 100,000 Worker requests a day and
100,000 storage reads; this uses a few dozen. There is no trial that lapses and
no card required.

Everything below is clicking and pasting. No command line.

---

## 1. Make a Cloudflare account

Go to **dash.cloudflare.com** and sign up. You do not need a domain and you do
not need to move any DNS. Choose the **Free** plan if asked.

## 2. Make the storage

In the left sidebar: **Storage & Databases** → **KV** → **Create instance**.

- Name it `markwatch`
- **Create**

This is where the language choice, the enrolled devices and the invite tokens
live. None of it goes in the repository, because the repository is public.

## 3. Create the Worker

Left sidebar: **Compute (Workers)** → **Create** → **Start from Hello World** →
**Create**.

- Name it `markwatch`

When the editor opens, delete everything in it, then paste the whole contents of
`worker/worker.js` from this repository. Click **Deploy**.

Copy the address it gives you — something like
`https://markwatch.yourname.workers.dev`. You need it twice below.

## 4. Attach the storage

In the Worker: **Settings** → **Bindings** → **Add** → **KV namespace**.

- Variable name: `STATE`  ← exactly this, capital letters
- KV namespace: `markwatch`
- **Deploy**

## 5. Make a webhook secret

This is one long random string that you will paste in three places. Invent one —
30 characters of letters and digits, no spaces. For example:

```
mark7watch4quiet9river2stone6blue
```

Write it down somewhere; you need it in steps 6, 7 and 9.

## 6. Add the Worker's settings

In the Worker: **Settings** → **Variables and Secrets**.

Add these as **Secret** (the type that cannot be read back):

| Name | Value |
|---|---|
| `TELEGRAM_TOKEN` | the bot token from @BotFather |
| `OWNER_CHAT_ID` | your own chat id — the number @userinfobot gave you |
| `WEBHOOK_SECRET` | the string from step 5 |

Add these as **Text**:

| Name | Value |
|---|---|
| `GITHUB_REPO` | `badBlaBlaW/Moex-brief` |
| `BRIEF_TIME` | `08:47` |

**Deploy** after adding them.

Note what is *not* here: no GitHub token. The repository is public, so the
Worker reads briefs without any credential, and it has no way to write to your
repository at all.

## 7. Point Telegram at the Worker

Open this in a browser, with your own values substituted:

```
https://api.telegram.org/bot<TELEGRAM_TOKEN>/setWebhook?url=https://markwatch.yourname.workers.dev&secret_token=<WEBHOOK_SECRET>
```

You should see `{"ok":true,"result":true,"description":"Webhook was set"}`.

From this moment Telegram stops queuing messages for polling and pushes them to
the Worker instead.

## 8. Test it

Open the bot on your phone and press **Start**. The greeting should appear
instantly. Pick a language, then try **📄 Последний обзор** — the latest brief
should arrive in a second or two.

Then press **🔗 Добавить устройство**. You get a one-time link, valid 15
minutes. Open it on another phone and that phone enrols itself and starts
receiving briefs. No secrets to edit.

## 9. Let the daily brief use the Worker

So that a self-enrolled phone also gets the *daily* brief, the GitHub job hands
each finished brief to the Worker to deliver.

In the repository: **Settings → Secrets and variables → Actions**, add two
secrets:

| Name | Value |
|---|---|
| `WORKER_URL` | `https://markwatch.yourname.workers.dev` |
| `WEBHOOK_SECRET` | the same string from step 5 |

Until these exist the job sends briefs itself, to the chats in
`TELEGRAM_OWNERS`, exactly as it does today. Once they exist the Worker
delivers, and the job falls back to sending directly if the Worker is ever
unreachable — so a Worker problem can never cost you a brief.

## 10. Turn off the listener

The old polling workflow is now redundant. In the repository: **Actions** →
**Mark is listening** → the `...` menu → **Disable workflow**.

---

## Checking on it

- **Cloudflare** → your Worker → **Logs** → **Begin log stream**, then press a
  button in the bot. You see each request as it happens.
- **Is the webhook healthy?** Open
  `https://api.telegram.org/bot<TELEGRAM_TOKEN>/getWebhookInfo`.
  `pending_update_count` should be 0 and `last_error_message` absent.

## Turning it off

Open `https://api.telegram.org/bot<TELEGRAM_TOKEN>/deleteWebhook`. Telegram goes
back to queuing updates, and the polling workflow can be re-enabled. Delete the
`WORKER_URL` secret and the daily brief sends directly again.

## What it costs

| | Free allowance | This uses |
|---|---|---|
| Requests | 100,000/day | a few dozen |
| CPU per request | 10 ms | well under; waiting on the network does not count |
| Storage reads | 100,000/day | a handful |
| Storage writes | 1,000/day | a handful — only on enrolment or a language change |

Nothing here approaches a paid tier.
