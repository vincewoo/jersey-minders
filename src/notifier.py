import logging
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.message import build_discord_payload

logger = logging.getLogger(__name__)


def send_notifications(
    subject: str, plain: str, html: str, config: dict, games: list[dict] | None = None
) -> None:
    """Dispatch to all enabled notification channels."""
    any_enabled = False

    if config.get("email_enabled"):
        any_enabled = True
        try:
            _send_email(subject, plain, html, config)
            logger.info("Email sent successfully")
        except Exception as exc:
            logger.error(f"Email failed: {exc}")

    if config.get("ntfy_enabled"):
        any_enabled = True
        try:
            _send_ntfy(subject, plain, config)
            logger.info("ntfy notification sent successfully")
        except Exception as exc:
            logger.error(f"ntfy failed: {exc}")

    if config.get("discord_enabled"):
        any_enabled = True
        try:
            payload = build_discord_payload(games or [], subject)
            _send_discord(payload, config)
            logger.info("Discord notification sent successfully")
        except Exception as exc:
            logger.error(f"Discord failed: {exc}")

    if not any_enabled:
        logger.warning(
            "No notification channels are enabled. "
            "Set EMAIL_ENABLED=true, NTFY_ENABLED=true, or DISCORD_ENABLED=true in your .env file."
        )


def _send_email(subject: str, plain: str, html: str, config: dict) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config["email_from"]
    msg["To"] = config["email_to"]
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    host = config["smtp_host"]
    port = int(config["smtp_port"])
    user = config["smtp_user"]
    password = config["smtp_password"]

    if port == 465:
        with smtplib.SMTP_SSL(host, port) as server:
            server.login(user, password)
            server.sendmail(config["email_from"], [config["email_to"]], msg.as_string())
    else:
        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            server.starttls()
            server.login(user, password)
            server.sendmail(config["email_from"], [config["email_to"]], msg.as_string())


def _send_ntfy(subject: str, plain: str, config: dict) -> None:
    topic = config["ntfy_topic"]
    resp = requests.post(
        f"https://ntfy.sh/{topic}",
        data=plain.encode("utf-8"),
        headers={
            "Title": subject,
            "Priority": "default",
            "Tags": "ice_hockey",
        },
        timeout=15,
    )
    resp.raise_for_status()


def _send_discord(payload: dict, config: dict) -> None:
    resp = requests.post(
        config["discord_webhook_url"],
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
