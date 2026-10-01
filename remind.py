"""Send a plain reminder email using the SMTP settings already in .env.

    uv run python remind.py "Subject here" "Body here"

Used by the Windows scheduled tasks. Kept separate from weekly_waivers.py so a
reminder still fires even if the Yahoo API is unavailable.
"""

from __future__ import annotations

import os
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))


def send(subject: str, body: str) -> None:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    to = os.getenv("MAIL_TO", user)
    if not all([host, user, password, to]):
        sys.exit("SMTP_* / MAIL_TO not configured in .env")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to
    msg.set_content(body)

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)
    print(f"Sent '{subject}' to {to}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit('usage: remind.py "Subject" "Body"')
    send(sys.argv[1], sys.argv[2])
