from datetime import datetime, timezone

_JERSEY_MIKES_RED = 0xC8102E  # decimal 13111342


def fmt_odds(odds: int | None) -> str:
    if odds is None:
        return "N/A"
    return f"+{odds}" if odds > 0 else str(odds)


def build_message(games: list[dict]) -> tuple[str, str]:
    """Return (plain_text, html) for the daily reminder."""
    today = datetime.now().strftime("%A, %B %-d")

    if not games:
        plain = (
            f"Jersey Mike's NHL Picks Reminder — {today}\n\n"
            "No NHL games are scheduled today. Enjoy the day off!\n"
        )
        html = f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
  <div style="background:#c8102e;color:white;padding:20px;border-radius:8px 8px 0 0;text-align:center;">
    <h1 style="margin:0;font-size:22px;">NHL Picks Reminder</h1>
    <p style="margin:5px 0 0;opacity:.9;">{today}</p>
  </div>
  <div style="background:#f9f9f9;padding:20px;border:1px solid #ddd;border-radius:0 0 8px 8px;text-align:center;">
    <p>No NHL games today. Enjoy the day off!</p>
  </div>
</body></html>"""
        return plain, html

    # --- Plain text ---
    divider = "-" * 50
    lines = [
        f"Jersey Mike's NHL Picks Reminder — {today}",
        "=" * 50,
        "Time to make your NHL Predictors picks!",
        f"Make picks at: https://www.jerseymikes.com/nhl",
        "",
        f"Today's Games  ({len(games)} game{'s' if len(games) != 1 else ''})",
        divider,
    ]
    for g in games:
        time_str = g["game_time"].strftime("%-I:%M %p %Z")
        lines += [
            f"{g['away_team']}  ({fmt_odds(g['away_odds'])})  @  {g['home_team']}  ({fmt_odds(g['home_odds'])})",
            f"  Vegas Fave : {g['favorite'] or 'Even / No line'}",
            f"  Game Time  : {time_str}",
            divider,
        ]
    lines.append("\nGood luck!")
    plain = "\n".join(lines)

    # --- HTML ---
    html = _build_html(today, games)
    return plain, html


def build_discord_payload(games: list[dict], subject: str) -> dict:
    """Build a Discord webhook payload with an embed for each game."""
    today = datetime.now().strftime("%A, %B %-d")

    if not games:
        return {
            "username": "Jersey Minders",
            "embeds": [{
                "title": f"🏒 {subject}",
                "description": "No NHL games today. Enjoy the day off!",
                "color": _JERSEY_MIKES_RED,
                "footer": {"text": "Jersey Minders · Odds via The Odds API"},
            }],
        }

    fields = []
    for g in games:
        time_str = g["game_time"].strftime("%-I:%M %p %Z")
        fave = g["favorite"] or "Even / No line"
        name = f"{g['away_team']} ({fmt_odds(g['away_odds'])})  @  {g['home_team']} ({fmt_odds(g['home_odds'])})"
        value = f"🏆 **{fave}** · {time_str}"
        fields.append({"name": name, "value": value, "inline": False})

    return {
        "username": "Jersey Minders",
        "embeds": [{
            "title": f"🏒 {subject}",
            "description": (
                f"Time to make your **Jersey Mike's NHL Predictors** picks!\n"
                f"[Make Your Picks](https://www.jerseymikes.com/nhl)"
            ),
            "color": _JERSEY_MIKES_RED,
            "fields": fields,
            "footer": {"text": f"Jersey Minders · Odds via The Odds API · {today}"},
        }],
    }


def _build_html(today: str, games: list[dict]) -> str:
    rows = ""
    for i, g in enumerate(games):
        bg = "#ffffff" if i % 2 == 0 else "#f5f5f5"
        time_str = g["game_time"].strftime("%-I:%M %p %Z")
        fave = g["favorite"] or "—"
        away_bold = " font-weight:bold;" if g["favorite"] == g["away_team"] else ""
        home_bold = " font-weight:bold;" if g["favorite"] == g["home_team"] else ""
        rows += f"""
      <tr style="background:{bg};">
        <td style="padding:10px 14px;{away_bold}">{g['away_team']}</td>
        <td style="padding:10px 14px;color:#555;font-size:13px;">{fmt_odds(g['away_odds'])}</td>
        <td style="padding:10px 14px;color:#888;font-size:13px;text-align:center;">@</td>
        <td style="padding:10px 14px;{home_bold}">{g['home_team']}</td>
        <td style="padding:10px 14px;color:#555;font-size:13px;">{fmt_odds(g['home_odds'])}</td>
        <td style="padding:10px 14px;color:#c8102e;font-weight:bold;">{fave}</td>
        <td style="padding:10px 14px;color:#777;font-size:12px;white-space:nowrap;">{time_str}</td>
      </tr>"""

    return f"""<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;max-width:680px;margin:0 auto;padding:20px;background:#f0f0f0;">
  <div style="background:#c8102e;color:white;padding:24px 20px 18px;border-radius:10px 10px 0 0;text-align:center;">
    <p style="margin:0 0 4px;font-size:13px;letter-spacing:2px;text-transform:uppercase;opacity:.8;">Jersey Mike's</p>
    <h1 style="margin:0;font-size:26px;font-weight:bold;">NHL Picks Reminder</h1>
    <p style="margin:6px 0 0;opacity:.85;font-size:15px;">{today}</p>
  </div>

  <div style="background:white;padding:20px 20px 10px;border-left:1px solid #ddd;border-right:1px solid #ddd;">
    <p style="margin:0 0 16px;font-size:15px;">
      Don't forget to make your <strong>Jersey Mike's NHL Predictors</strong> picks today!
      Vegas favorites are highlighted below.
    </p>

    <table style="width:100%;border-collapse:collapse;font-size:14px;">
      <thead>
        <tr style="background:#1a1a1a;color:white;font-size:12px;text-transform:uppercase;letter-spacing:1px;">
          <th style="padding:9px 14px;text-align:left;" colspan="2">Away</th>
          <th style="padding:9px 4px;"></th>
          <th style="padding:9px 14px;text-align:left;" colspan="2">Home</th>
          <th style="padding:9px 14px;text-align:left;">Pick</th>
          <th style="padding:9px 14px;text-align:left;">Time</th>
        </tr>
      </thead>
      <tbody>{rows}
      </tbody>
    </table>
  </div>

  <div style="background:#c8102e;padding:16px;border-radius:0 0 10px 10px;text-align:center;">
    <a href="https://www.jerseymikes.com/nhl"
       style="background:white;color:#c8102e;padding:11px 30px;border-radius:6px;
              text-decoration:none;font-weight:bold;font-size:15px;display:inline-block;">
      Make Your Picks
    </a>
  </div>

  <p style="text-align:center;color:#aaa;font-size:11px;margin-top:14px;">
    Sent by Jersey Minders &middot; Odds via The Odds API
  </p>
</body>
</html>"""
