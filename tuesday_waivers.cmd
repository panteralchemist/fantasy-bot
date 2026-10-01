@echo off
REM Fired by the Windows scheduled task "FantasyTuesdayWaivers".
REM Tuesday evening, ahead of Wednesday waiver processing.
REM weekly_waivers.py degrades to a "do it manually" email if the Yahoo API
REM is still gated, so this always sends something actionable.
cd /d C:\Users\davep\fantasy-bot
uv run python weekly_waivers.py
