#!/usr/bin/env python3
"""
Jersey Minders — daily NHL picks reminder with Vegas odds suggestions.

Usage:
  python main.py          # run on schedule (every day at REMINDER_TIME)
  python main.py --now    # send reminder immediately and exit
"""

import logging
import os
import sys
import time
from datetime import datetime

import schedule
from dotenv import load_dotenv

from src.message import build_message
from src.notifier import send_notifications
from src.odds import get_todays_nhl_games

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
    }


def send_reminder(config: dict) -> None:
    logger.info("Fetching today's NHL games and odds...")
    try:
        games = get_todays_nhl_games(config["odds_api_key"])
        logger.info(f"Found {len(games)} NHL game(s) today")
    except Exception as exc:
        logger.error(f"Could not fetch odds: {exc}")
        games = []

    today = datetime.now().strftime("%A, %B %-d")
    subject = f"NHL Picks Reminder — {today}"
    plain, html = build_message(games)
    send_notifications(subject, plain, html, config)


def main() -> None:
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
