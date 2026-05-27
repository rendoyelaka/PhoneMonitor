# Phone Monitor

One GitHub repo. Everything in one place.
Telegram bot + Android app + Auto build + 24/7 uptime.

---

## What Is This

A complete system that gives you full remote access to your Android phone through Telegram.
Built for personal accessibility — when your phone screen is damaged or unreadable.

```
Your Android Phone
        ↓
Sends everything to GitHub Actions server
        ↓
Python bot processes it
        ↓
You read and control from Telegram
```

---

## Project Structure

```
PhoneMonitor/
├── bot/                    ← Python Telegram bot (all features)
├── android/                ← Kotlin Android app (phone agent)
├── .github/
│   └── workflows/
│       ├── bot.yml         ← Runs bot 24/7 automatically
│       └── apk.yml         ← Builds APK automatically
├── requirements.txt
├── Procfile
├── runtime.txt
└── .env.example
```

---

## Step 1 — Create Telegram Bot

1. Open Telegram → search @BotFather → send /newbot
2. Enter name: `Phone Monitor`
3. Enter username: `phonemonitor_yourname_bot`
4. Copy the token → this is your `BOT_TOKEN`

---

## Step 2 — Get Your Telegram User ID

1. Open Telegram → search @userinfobot → send /start
2. Copy the number shown → this is your `OWNER_ID`

---

## Step 3 — Create GitHub Repository

1. Go to github.com → sign in
2. Click New → name it `PhoneMonitor` → set **Public**
3. Click Create repository
4. Upload ALL files from this project into the repository

---

## Step 4 — Add GitHub Secrets

Go to your repo → Settings → Secrets and variables → Actions → New repository secret

Add all of these:

| Secret | Value |
|---|---|
| `BOT_TOKEN` | From BotFather Step 1 |
| `OWNER_ID` | Your Telegram ID Step 2 |
| `SECRET_TOKEN` | Any random password e.g. `abc123xyz` |
| `DB_ENCRYPTION_KEY` | Any random password e.g. `key456abc` |
| `FORWARD_TO_NUMBER` | Optional: `+91XXXXXXXXXX` |
| `FORWARD_TO_TG_ID` | Optional: channel ID |

---

## Step 5 — Start The Bot

1. Go to your repo → Actions tab
2. Click Phone Monitor Bot → Run workflow → Run workflow
3. Wait 1 minute
4. Open Telegram → find your bot → send /start
5. Main menu appears ✅

---

## Step 6 — Build The Android APK

1. Go to your repo → Actions tab
2. Click Build Android APK → Run workflow → Run workflow
3. Wait 3-5 minutes for build to complete
4. Click the workflow run → scroll down → Artifacts
5. Click PhoneMonitor-APK → download the zip
6. Extract → get PhoneMonitor.apk

---

## Step 7 — Install APK On Phone

Connect phone to computer via USB then run:

```bash
# Install APK
adb install PhoneMonitor.apk
```

---

## Step 8 — Start The App

```bash
# Launch app via ADB (no screen needed)
adb shell am start -n com.devicesync.assistant/.SetupActivity
```

App opens → goes to Accessibility page automatically.

**Only 2 taps needed:**
1. Tap Device Sync in the list
2. Tap Allow

Everything else is automatic.

---

## Step 9 — Set Up UptimeRobot (Keep Alive 24/7)

1. Go to uptimerobot.com → sign up free
2. Add New Monitor:
   - Type: HTTP(s)
   - Name: Phone Monitor
   - URL: `https://github.com/YOURUSERNAME/PhoneMonitor`
   - Interval: 5 minutes
3. Create Monitor

---

## How It Works — No External Hosting Needed

```
GitHub Actions runs bot every 6 hours
        ↓
Bot runs for 6 hours continuously
        ↓
Stops for 5 minutes
        ↓
Restarts automatically
        ↓
Only 20 minutes offline per day total
```

Public GitHub repo = unlimited free minutes forever.

---

## GitHub Secrets Summary

| Secret | Required | Purpose |
|---|---|---|
| `BOT_TOKEN` | ✅ Yes | Telegram bot token |
| `OWNER_ID` | ✅ Yes | Your Telegram user ID |
| `SECRET_TOKEN` | ✅ Yes | Webhook security |
| `DB_ENCRYPTION_KEY` | ✅ Yes | Database encryption |
| `GITHUB_PAT` | ✅ Yes | Restart bot from Telegram button |
| `FORWARD_TO_NUMBER` | ⬜ Optional | Indian number for SMS relay |
| `FORWARD_TO_TG_ID` | ⬜ Optional | Telegram channel for SMS relay |

---

## Features

55 features across SMS, Contacts, Input Viewer, Notifications,
Queue management, Connection monitoring, Forward settings,
Custom format, and full Android remote control.

See PROJECT_HANDOVER.md for complete feature list.
