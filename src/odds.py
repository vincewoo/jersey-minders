import logging
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

_ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/"
_SCORES_API_URL = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/scores/"
_PREFERRED_BOOKMAKERS = ["draftkings", "fanduel", "betmgm", "caesars", "williamhill_us"]


def get_upcoming_week_nfl_games(api_key: str) -> list[dict]:
    """Fetch NFL games for the coming week.

    Returns games whose local game date falls within [today, today + 7 days],
    sorted by game time.
    """
    data = _fetch_odds(api_key)
    today_local = datetime.now().date()
    week_end = today_local + timedelta(days=7)

    games = []
    for game in data:
        game_time_utc = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00"))
        game_time_local = game_time_utc.astimezone()
        game_date = game_time_local.date()
        if today_local <= game_date <= week_end:
            parsed = _parse_game(game, game_time_local)
            if parsed:
                games.append(parsed)

    return sorted(games, key=lambda g: g["game_time"])


def get_nfl_scores(api_key: str, days_from: int = 3) -> list[dict]:
    """Fetch recent NFL scores.

    Args:
        api_key: The Odds API key.
        days_from: How many days back to include (1-3 on the free tier).

    Returns:
        Raw list of game dicts from The Odds API scores endpoint.
    """
    resp = requests.get(
        _SCORES_API_URL,
        params={
            "apiKey": api_key,
            "daysFrom": days_from,
            "includeAll": "true",
        },
        timeout=15,
    )
    remaining = resp.headers.get("x-requests-remaining", "?")
    logger.info(f"Scores API requests remaining: {remaining}")
    resp.raise_for_status()
    return resp.json()


def _fetch_odds(api_key: str) -> list[dict]:
    resp = requests.get(
        _ODDS_API_URL,
        params={
            "apiKey": api_key,
            "regions": "us",
            "markets": "h2h",
            "oddsFormat": "american",
            "dateFormat": "iso",
        },
        timeout=15,
    )
    remaining = resp.headers.get("x-requests-remaining", "?")
    logger.info(f"Odds API requests remaining: {remaining}")
    resp.raise_for_status()
    return resp.json()


def _parse_game(game: dict, game_time_local: datetime) -> dict | None:
    home_team = game["home_team"]
    away_team = game["away_team"]

    home_odds, away_odds = _extract_odds(game, home_team, away_team)

    favorite = None
    if home_odds is not None and away_odds is not None:
        favorite = home_team if home_odds < away_odds else away_team

    return {
        "home_team": home_team,
        "away_team": away_team,
        "game_time": game_time_local,
        "home_odds": home_odds,
        "away_odds": away_odds,
        "favorite": favorite,
    }


def _extract_odds(game: dict, home_team: str, away_team: str) -> tuple[int | None, int | None]:
    """Pull moneyline odds, preferring well-known US sportsbooks."""
    bookmakers = game.get("bookmakers", [])

    def odds_from_bookmaker(bm: dict) -> tuple[int | None, int | None]:
        for market in bm.get("markets", []):
            if market["key"] != "h2h":
                continue
            home_odds = away_odds = None
            for outcome in market.get("outcomes", []):
                if outcome["name"] == home_team:
                    home_odds = outcome["price"]
                elif outcome["name"] == away_team:
                    away_odds = outcome["price"]
            if home_odds is not None and away_odds is not None:
                return home_odds, away_odds
        return None, None

    # Try preferred bookmakers first for consistency
    bm_by_key = {bm["key"]: bm for bm in bookmakers}
    for key in _PREFERRED_BOOKMAKERS:
        if key in bm_by_key:
            h, a = odds_from_bookmaker(bm_by_key[key])
            if h is not None:
                return h, a

    # Fall back to whatever is available
    for bm in bookmakers:
        h, a = odds_from_bookmaker(bm)
        if h is not None:
            return h, a

    return None, None
