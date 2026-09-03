# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
# Install dependencies (use a venv)
pip install -r requirements.txt

# Send the NFL reminder immediately (main testing entry point)
python main.py --now

# Resolve pending picks immediately
python main.py --resolve

# Print pick win rate
python main.py --stats

# Run on schedule (blocks; NFL reminder every Tuesday at REMINDER_TIME,
# pick resolution every RESOLVE_EVERY_DAYS days at RESOLVE_TIME)
python main.py

# Docker (runs continuously, persists DB in a named volume)
docker compose up -d
```

There are no automated tests. Verify changes by running `python main.py --now` with a real `.env`.

## Environment setup

Copy `.env.example` to `.env`. Only `ODDS_API_KEY` is required to run. At least one notification channel (`EMAIL_ENABLED`, `NTFY_ENABLED`, or `DISCORD_ENABLED`) must be set to `true` or the app logs a warning and sends nothing.

## Architecture

The app is a single-process Python scheduler (`schedule` library). Two jobs run: the NFL reminder fires every **Tuesday** at `REMINDER_TIME`, and pick resolution fires every `RESOLVE_EVERY_DAYS` days (default 3) at `RESOLVE_TIME`. Entry point is `main.py`; all supporting code lives in `src/`.

**Weekly reminder flow (inside `send_nfl_reminder`):**
1. `get_upcoming_week_nfl_games()` — fetches NFL moneyline odds for the coming 7-day window; returns games sorted by time with the Vegas favorite identified
2. `save_week_picks()` — persists the coming week's games/picks to `pending_picks` table, keyed by each game's own date
3. `get_win_rate()` — reads aggregate correct/total from `stats` table
4. `build_message()` / `build_discord_payload()` — formats plain text + HTML (email) or Discord embed
5. `send_notifications()` — dispatches to enabled channels (email, ntfy.sh, Discord)

**Resolution flow (inside `resolve_picks`, runs every `RESOLVE_EVERY_DAYS` days):**
1. `get_nfl_scores()` — fetches up to 3 days of completed NFL scores
2. Match against pending picks in SQLite, record correct/incorrect, delete resolved rows

**Module responsibilities:**
- `src/database.py` — SQLite via stdlib. Two tables: `stats` (single row, aggregate counters) and `pending_picks` (temp rows with `UNIQUE(game_date, home_team, away_team)`; uses `INSERT OR IGNORE` to handle repeated runs). DB lives at `data/picks.db`.
- `src/odds.py` — The Odds API calls. `get_upcoming_week_nfl_games` filters the coming 7-day window in local time and picks odds from preferred US bookmakers (DraftKings → FanDuel → BetMGM → …). `get_nfl_scores` fetches up to 3 days of completed NFL scores.
- `src/message.py` — Builds all message formats. `build_message` → `(plain, html)`. `build_discord_payload` → dict for Discord webhook. Both accept `win_rate: str`.
- `src/notifier.py` — Dispatches to channels. Each channel catches its own exceptions so one failure doesn't block others.

**Win rate resolution edge cases:** ties (`home_score == away_score`) and games with missing score data are skipped and remain as pending picks until resolved on a future run.

## Key constraints

- The Odds API free tier allows `daysFrom` 1–3 on the scores endpoint (no `daysTo` parameter).
- Team name matching between the odds API and scores API relies on identical strings from the same provider — both endpoints use The Odds API, so this is consistent.
- `data/` is gitignored. Docker persists it via the `picks_data` named volume.
- The Dockerfile's `COPY . .` is guarded by `.dockerignore` (excludes `.env`, `venv/`, `data/`).
