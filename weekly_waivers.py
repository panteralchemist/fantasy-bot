"""Tuesday-night waiver report: read the league, email a summary to approve.

    uv run python weekly_waivers.py            # send the email
    uv run python weekly_waivers.py --dry-run  # print it instead

Deliberately READ-ONLY. It never submits a claim. The email is the thing David
approves; submitting stays a separate, explicit step.
"""

from __future__ import annotations

import argparse
import os
import smtplib
import sys
from datetime import date
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

from yahoo_client import Yahoo

load_dotenv(Path(__file__).with_name(".env"))


def build_report() -> tuple[str, str]:
    y = Yahoo()

    roster = y.roster()
    standings = y.standings()
    me = next((t for t in standings if t.get("faab")), None)

    # Bye-week concentration is the structural trap on this roster - five
    # Eagles plus Monangai all sat out Week 10 as drafted.
    byes: dict[str, list[str]] = {}
    for p in roster:
        if p["bye"]:
            byes.setdefault(p["bye"], []).append(f"{p['name']} ({p['position']})")
    crowded = sorted(
        ((wk, names) for wk, names in byes.items() if len(names) >= 3),
        key=lambda kv: -len(kv[1]),
    )

    injured = [p for p in roster if p["status"]]
    fa_rb = y.free_agents("RB", 10)
    fa_wr = y.free_agents("WR", 10)
    fa_te = y.free_agents("TE", 10)
    stashes = [p for p in y.ir_eligible(25) if _pct(p) >= 5]

    lines: list[str] = []
    add = lines.append

    add(f"Shiva Bowl waiver check - {date.today():%a %d %b %Y}")
    add("=" * 52)
    add("")

    add("STANDINGS")
    for t in standings:
        mark = " <-- you" if t["name"] == "Champion by Skill Alone" else ""
        add(f"  {t['rank']:>2}. {t['name'][:34]:<34} {t['wins']}-{t['losses']}"
            f"  PF {t['points_for']:>7}  FAAB ${t['faab']}{mark}")
    add("")

    if injured:
        add("INJURY / STATUS FLAGS ON YOUR ROSTER")
        for p in injured:
            add(f"  [{p['status']:>4}] {p['name']} ({p['position']}, {p['team']})")
        add("")
        add("  NOTE: an IR-slotted player whose status improves to Doubtful stops")
        add("  qualifying and BLOCKS every add/drop until moved off IR (error 845).")
        add("")

    if crowded:
        add("BYE-WEEK CONCENTRATION")
        for wk, names in crowded:
            add(f"  Week {wk}: {len(names)} players")
            for n in names:
                add(f"      - {n}")
        add("")

    for label, pool in (("RB", fa_rb), ("WR", fa_wr), ("TE", fa_te)):
        add(f"TOP AVAILABLE {label}")
        for p in pool[:6]:
            pct = p["percent_owned"] or "0"
            add(f"  {p['name'][:26]:<26} {p['team']:<4} bye {p['bye'] or '-':<3} "
                f"{pct}% rostered")
        add("")

    if stashes:
        add("IR-ELIGIBLE STASH CANDIDATES (>=5% rostered)")
        for p in stashes[:8]:
            add(f"  {p['name'][:26]:<26} {p['team']:<4} {p['percent_owned']}% rostered")
        add("  NOTE: an IR add still needs a bench drop - they land on the bench first.")
        add("")

    add("-" * 52)
    add("Reply with what you want claimed and I'll submit it before Wednesday.")

    body = "\n".join(lines)
    subject = f"Shiva Bowl waivers - {date.today():%d %b}"
    return subject, body


def _pct(p: dict) -> float:
    try:
        return float(p.get("percent_owned") or 0)
    except ValueError:
        return 0.0


def send(subject: str, body: str) -> None:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    to = os.getenv("MAIL_TO", user)
    if not all([host, user, password, to]):
        sys.exit("SMTP_* / MAIL_TO not configured in .env - see .env.example.")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to
    msg.set_content(body)

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)
    print(f"Sent to {to}.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print instead of emailing")
    args = ap.parse_args()

    subject, body = build_report()
    if args.dry_run:
        print(subject)
        print()
        print(body)
    else:
        send(subject, body)


if __name__ == "__main__":
    main()
