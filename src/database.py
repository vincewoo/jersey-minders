"""
SQLite helpers for tracking pick win rate.

Stores:
- Aggregate counters (correct/incorrect) permanently for win rate calculation.
- Pending picks temporarily until resolved, then deleted.
"""

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "picks.db"


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    with _get_connection() as conn:
        # Aggregate stats — single row, kept forever
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                correct INTEGER DEFAULT 0,
                incorrect INTEGER DEFAULT 0
            )
        """)
        count = conn.execute("SELECT COUNT(*) FROM stats").fetchone()[0]
        if count == 0:
            conn.execute("INSERT INTO stats (id, correct, incorrect) VALUES (1, 0, 0)")

        # Pending picks — stored temporarily until resolved, then deleted
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pending_picks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_date TEXT NOT NULL,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                pick_team TEXT NOT NULL,
                UNIQUE (game_date, home_team, away_team)
            )
        """)
        conn.commit()
    logger.info(f"Database initialized at {DB_PATH}")


def save_pending_pick(game_date: str, home_team: str, away_team: str, pick_team: str) -> None:
    """Save a pick to be resolved later."""
    with _get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO pending_picks (game_date, home_team, away_team, pick_team) VALUES (?, ?, ?, ?)",
            (game_date, home_team, away_team, pick_team),
        )
        conn.commit()


def get_pending_picks() -> list[sqlite3.Row]:
    """Return all unresolved picks."""
    with _get_connection() as conn:
        rows = conn.execute("SELECT * FROM pending_picks ORDER BY id").fetchall()
    return rows


def delete_pending_pick(pick_id: int) -> None:
    """Delete a resolved pick."""
    with _get_connection() as conn:
        conn.execute("DELETE FROM pending_picks WHERE id = ?", (pick_id,))
        conn.commit()


def record_result(correct: bool) -> None:
    """Increment the correct or incorrect counter."""
    with _get_connection() as conn:
        if correct:
            conn.execute("UPDATE stats SET correct = correct + 1 WHERE id = 1")
        else:
            conn.execute("UPDATE stats SET incorrect = incorrect + 1 WHERE id = 1")
        conn.commit()


def get_win_rate() -> tuple[int, int, str]:
    """Return (correct, total, formatted_string)."""
    with _get_connection() as conn:
        row = conn.execute("SELECT correct, incorrect FROM stats WHERE id = 1").fetchone()

    correct = row["correct"]
    incorrect = row["incorrect"]
    total = correct + incorrect

    if total == 0:
        return 0, 0, "No results yet"
    pct = (correct / total) * 100
    return correct, total, f"{correct}/{total} ({pct:.0f}%)"