# Jersey Minders

Weekly reminder (every Tuesday) to make your **Jersey Mike's NFL Picks** for the coming week, with the Vegas moneyline favorite highlighted for each game.

## What it does

- **Every Tuesday** at a time you set, it:
  1. Fetches the coming week's NFL games and moneyline odds (via [The Odds API](https://the-odds-api.com))
  2. Identifies the Vegas favorite in each matchup
  3. Sends you a formatted reminder listing the week's games and picks via **email**, **ntfy.sh push notification**, and/or **Discord**, including your running win rate
- **Every 3 days** at a time you set, it resolves any pending picks from games that have been completed and updates your win rate.

## Quick start

### 1. Get a free Odds API key

Sign up at [the-odds-api.com](https://the-odds-api.com) — the free tier gives you 500 requests/month, well above the usage this app needs (1 odds call per week + 1 scores call every 3 days).

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your API key and notification settings
```

At minimum, set `ODDS_API_KEY`. Then enable at least one notification channel (see below).

### 3. Run

**Docker (recommended — runs continuously):**
```bash
# Edit the TZ line in docker-compose.yml to match your timezone first
docker compose up -d
```

**Local Python:**
```bash
pip install -r requirements.txt
python main.py           # runs on schedule
python main.py --now     # send the NFL reminder immediately (good for testing)
python main.py --resolve # resolve pending picks immediately
python main.py --stats   # print your pick win rate and exit
```

**Cron (send once and exit):**
```cron
0 9 * * * cd /path/to/jersey-minders && python main.py --now
```

## Notification channels

### Email (SMTP)

Works with Gmail, Outlook, or any SMTP provider.

**Gmail setup:**
1. Enable 2-factor authentication on your Google account
2. Go to [Google App Passwords](https://myaccount.google.com/apppasswords) and generate a password for "Mail"
3. Use that 16-character password as `SMTP_PASSWORD` (not your regular Gmail password)

```env
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
EMAIL_FROM=you@gmail.com
EMAIL_TO=you@gmail.com
```

### ntfy.sh (free push notifications to your phone)

No account needed. Install the [ntfy app](https://ntfy.sh) on your phone, subscribe to your topic, done.

```env
NTFY_ENABLED=true
NTFY_TOPIC=my-secret-nfl-picks-topic-abc123   # keep this private
```

### Discord (webhook)

Posts a formatted embed to any Discord channel you choose.

**Setup:**
1. Open the Discord channel you want reminders in
2. Go to **Edit Channel → Integrations → Webhooks → New Webhook**
3. Copy the webhook URL and paste it as `DISCORD_WEBHOOK_URL`

```env
DISCORD_ENABLED=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdefg...
```

You can enable any combination of channels at the same time.

## Configuration reference

| Variable | Default | Description |
|---|---|---|
| `ODDS_API_KEY` | — | **Required.** Your Odds API key |
| `REMINDER_TIME` | `09:00` | Tuesday send time for the NFL reminder (24h, system/container timezone) |
| `RESOLVE_TIME` | `09:00` | Time (24h) to run pick resolution |
| `RESOLVE_EVERY_DAYS` | `3` | How often (in days) picks are resolved |
| `EMAIL_ENABLED` | `false` | Enable email notifications |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | `587` | SMTP port (587 = STARTTLS, 465 = SSL) |
| `SMTP_USER` | — | SMTP login username |
| `SMTP_PASSWORD` | — | SMTP password or app password |
| `EMAIL_FROM` | `SMTP_USER` | Sender address |
| `EMAIL_TO` | — | Recipient address |
| `NTFY_ENABLED` | `false` | Enable ntfy.sh push notifications |
| `NTFY_TOPIC` | — | Your private ntfy topic name |
| `DISCORD_ENABLED` | `false` | Enable Discord notifications |
| `DISCORD_WEBHOOK_URL` | — | Discord channel webhook URL |

## Notes

- **Win rate tracking** — picks are saved on the Tuesday reminder (keyed by each game's own date) and resolved every `RESOLVE_EVERY_DAYS` days (default 3) by fetching completed NFL scores. The win rate appears in every notification and in `--stats`. Data is stored in a local SQLite database (`data/picks.db`); Docker users get this persisted in a named volume automatically.
- **Odds** are sourced from DraftKings/FanDuel/BetMGM (whichever is available). The displayed favorite is based on the moneyline — the team with the lower (more negative) number.
- **No games this week** — if there are no NFL games in the coming week, the reminder still sends so you don't wonder whether it's broken.
- **Free-tier scores window** — the scores API only reaches back 3 days on the free tier, so the every-3-days resolution cadence is what ensures each finished game is caught within its window.
