# MOEX dividend brief → Telegram

Claude ("Mark") writes a brief into `briefs/YYYY-MM-DD.md` each weekday morning.
Pushing that file triggers a GitHub Action that posts it to your Telegram.

Nothing runs on your own computer. Your laptop can be closed.

## Getting these files into the repository

**Unzip the archive first.** Do not upload the `.zip` itself — GitHub needs the
real files, and it only looks for automations in `.github/workflows/`.

### On a Mac, reveal the hidden folder first
After unzipping you will see `README.md`, `config.json` and `samples` — but not
`.github`, which is the important one. Folders starting with a dot are hidden by
Finder.

In the unzipped folder press **Cmd + Shift + .** (period). `.github` appears in
grey. The same shortcut hides it again afterwards.

### Upload
1. In your empty repository click **uploading an existing file**
   (or **Add file → Upload files**).
2. Select all four items — `.github`, `briefs`, `samples`, `config.json`,
   `README.md` — and drag them in together. Dragging whole folders keeps the
   structure; adding files one by one does not.
3. Click **Commit changes**.

Afterwards the repository should show a `.github` folder. If it doesn't, the
hidden folder was missed — repeat with it visible.

**Or skip all of this:** connect GitHub to Claude in **Settings → Connectors**,
tell Claude the repository name, and it will push everything in one step.

## Setup, once

### 1. Make the bot (phone, ~3 min)
1. Open Telegram, search **@BotFather**, send `/newbot`.
2. Display name: anything, e.g. `Mark — MOEX watch`.
3. Username: must end in `bot`, e.g. `my_moex_brief_bot`.
4. BotFather replies with a **token** like `1234567890:AAEhBP9...`.
5. Tap the `t.me/...` link and press **Start**.
   A bot cannot message you until you message it first.

### 2. Find your chat ID
Open in any browser, with your token in place of `<TOKEN>`:

    https://api.telegram.org/bot<TOKEN>/getUpdates

Look for `"chat":{"id":123456789` — that number is your **chat ID**.

### 3. Add both to GitHub
**Settings → Secrets and variables → Actions → New repository secret.** Add two:

| Name                | Value                  |
|---------------------|------------------------|
| `TELEGRAM_TOKEN`    | the token from step 4  |
| `TELEGRAM_CHAT_ID`  | the number from step 2 |

They are encrypted. Nobody can read them back — not you, not Claude.

### 4. Say hello
Send `/start` to your bot. Mark replies instantly, in whatever language your
Telegram app is set to.

If nothing comes back, the webhook is not set up yet — see `worker/SETUP.md`.

## Everyday use

Nothing to do. The brief arrives each weekday at **08:52 Moscow time**.

Two buttons sit above your keyboard at all times:

| Button | What it does |
|--------|--------------|
| 🇷🇺 Русский / 🇬🇧 English | Switch language — applies from the next brief |
| ❓ Help / ❓ Помощь | What this is and when it arrives |

Both answer immediately.

## How replies work

A workflow holds a **long-poll** open to Telegram: the connection stays live
and returns the instant you send something, so Mark answers immediately. Each
run listens for just under six hours and then starts the next, so the chain is
continuous. A six-hourly schedule is the safety net if a link ever breaks.

This is why the repository is public — GitHub gives public repositories
unlimited Actions minutes, and continuous listening needs far more than the
2,000 a month private ones get.

`worker/` holds a Cloudflare Worker that does the same job as a true webhook,
with nothing polling and nothing to keep alive. It is unused, and is the route
to take if the repository ever needs to be private again.


## How the language setting works
`config.json` holds `{"language": "en"}` or `{"language": "ru"}`.
`/start` sets it from your Telegram locale; the button changes it afterwards.
The Worker writes this file directly, which is why it needs a GitHub token.

The daily brief reads this file **before writing anything** and composes the
whole brief in that language — analysis, headings, confidence labels and all,
written natively rather than translated. Tickers stay in Latin (TRNFP, LKOH).

You can also edit `config.json` directly here on GitHub.

## If briefs stop arriving
Open the **Actions** tab and look for a red run; the log says what broke.
Most common cause: the token was regenerated in BotFather — update the secret.

## To stop it
Delete the `TELEGRAM_TOKEN` secret, or disable the workflows in the Actions tab.
