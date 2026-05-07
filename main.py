#!/usr/bin/env python3
"""
Jersey Minders — daily NHL picks reminder with Vegas odds suggestions.

Usage:
  python main.py          # run on schedule (every day at REMINDER_TIME)
  python main.py --now    # send reminder immediately and exit
  python main.py --stats  # print win rate and exit
"""

import logging
import os
import sys
import time
from datetime import datetime

import schedule
from dotenv import load_dotenv

from src.database import (
    delete_pending_pick,
    get_pending_picks,
    get_win_rate,
    init_db,
    record_result,
    save_pending_pick,
)
from src.message import build_message
from src.notifier import send_notifications
from src.odds import get_nhl_scores, get_todays_nhl_games

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _load_config() -> dict:
    api_key = os.environ.get("ODDS_API_KEY", "").strip()
    if not api_key:
        logger.error("ODDS_API_KEY is not set. Add it to your .env file.")
        sys.exit(1)

    return {
        "odds_api_key": api_key,
        "reminder_time": os.getenv("REMINDER_TIME", "09:00"),
        # Email
        "email_enabled": os.getenv("EMAIL_ENABLED", "false").lower() == "true",
        "smtp_host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "smtp_port": os.getenv("SMTP_PORT", "587"),
        "smtp_user": os.getenv("SMTP_USER", ""),
        "smtp_password": os.getenv("SMTP_PASSWORD", ""),
        "email_from": os.getenv("EMAIL_FROM") or os.getenv("SMTP_USER", ""),
        "email_to": os.getenv("EMAIL_TO", ""),
        # ntfy.sh
        "ntfy_enabled": os.getenv("NTFY_ENABLED", "false").lower() == "true",
        "ntfy_topic": os.getenv("NTFY_TOPIC", ""),
        # Discord
        "discord_enabled": os.getenv("DISCORD_ENABLED", "false").lower() == "true",
        "discord_webhook_url": os.getenv("DISCORD_WEBHOOK_URL", ""),
    }


def resolve_picks(config: dict) -> None:
    """Match completed game scores against pending picks, record result, then delete."""
    pending = get_pending_picks()
    if not pending:
        logger.info("No pending picks to resolve")
        return

    try:
        scores = get_nhl_scores(config["odds_api_key"])
    except Exception as exc:
        logger.error(f"Could not fetch scores: {exc}")
        return

    # Build lookup: (away_team, home_team) -> list of games (same matchup can appear
    # on multiple dates within the daysFrom window, e.g. a playoff series)
    scores_by_teams: dict[tuple[str, str], list[dict]] = {}
    for game in scores:
        key = (game["away_team"], game["home_team"])
        scores_by_teams.setdefault(key, []).append(game)

    resolved = 0
    for pick in pending:
        key = (pick["away_team"], pick["home_team"])
        if key not in scores_by_teams:
            continue

        # Find the completed game whose local date matches the pick's game_date.
        # This prevents a later incomplete game (e.g. tomorrow's rematch) from
        # shadowing yesterday's completed result.
        score_data = None
        for candidate in scores_by_teams[key]:
            if not candidate.get("completed"):
                continue
            game_date = datetime.fromisoformat(
                candidate["commence_time"].replace("Z", "+00:00")
            ).astimezone().strftime("%Y-%m-%d")
            if game_date == pick["game_date"]:
                score_data = candidate
                break

        if score_data is None:
            continue

        # Extract scores — use `or []` to handle an explicit null from the API
        scores_list = score_data.get("scores") or []
        home_score = None
        away_score = None
        for s in scores_list:
            if s["name"] == pick["home_team"]:
                home_score = int(s["score"]) if s["score"] is not None else None
            elif s["name"] == pick["away_team"]:
                away_score = int(s["score"]) if s["score"] is not None else None

        if home_score is None or away_score is None:
            continue

        if home_score == away_score:
            continue

        # Determine winner and if pick was correct
        winner = pick["home_team"] if home_score > away_score else pick["away_team"]
        correct = winner == pick["pick_team"]

        record_result(correct)
        delete_pending_pick(pick["id"])
        resolved += 1
        logger.info(
            f"Resolved: {pick['away_team']} ({away_score}) @ {pick['home_team']} ({home_score}) "
            f"— Picked {pick['pick_team']} → {'correct' if correct else 'incorrect'}"
        )

    logger.info(f"Resolved {resolved} pick(s)")


def save_today_picks(games: list[dict]) -> None:
    """Save today's picks to the pending picks table."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    count = 0
    for g in games:
        pick_team = g["favorite"] or ""
        if not pick_team:
            continue
        save_pending_pick(
            game_date=today_str,
            home_team=g["home_team"],
            away_team=g["away_team"],
            pick_team=pick_team,
        )
        count += 1
    logger.info(f"Saved {count} pending pick(s) for {today_str}")


def send_reminder(config: dict) -> None:
    logger.info("Checking results for previous picks...")
    resolve_picks(config)

    logger.info("Fetching today's NHL games and odds...")
    try:
        games = get_todays_nhl_games(config["odds_api_key"])
        logger.info(f"Found {len(games)} NHL game(s) today")
    except Exception as exc:
        logger.error(f"Could not fetch odds: {exc}")
        games = []

    # Save today's picks for future resolution
    if games:
        save_today_picks(games)

    # Get win rate
    _, _, win_rate_str = get_win_rate()

    today = datetime.now().strftime("%A, %B %-d")
    subject = f"NHL Picks Reminder - {today}"
    plain, html = build_message(games, win_rate=win_rate_str)
    send_notifications(subject, plain, html, config, games=games, win_rate=win_rate_str)


def print_stats() -> None:
    """Print win rate stats and exit."""
    _, _, win_rate_str = get_win_rate()
    print(f"\nJersey Minders Win Rate: {win_rate_str}\n")


def main() -> None:
    init_db()

    if "--stats" in sys.argv:
        print_stats()
        return

    config = _load_config()

    if "--now" in sys.argv:
        logger.info("Sending reminder now (--now flag detected)")
        send_reminder(config)
        return

    reminder_time = config["reminder_time"]
    logger.info(f"Jersey Minders started — will remind daily at {reminder_time}")
    schedule.every().day.at(reminder_time).do(send_reminder, config=config)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
