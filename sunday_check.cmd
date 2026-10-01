@echo off
REM Fired by the Windows scheduled task "FantasySundayCheck".
REM Timed for just after NFL inactives post (90 min before the 1pm ET kickoff),
REM leaving roughly 85 minutes to change the lineup before it locks.
cd /d C:\Users\davep\fantasy-bot
uv run python remind.py "Fantasy: check DeVonta Smith before lineups lock" "DeVonta Smith (Phi WR) was listed QUESTIONABLE for Week 4. Inactives are out now. If he is OUT or a late scratch, swap him for DK Metcalf on the bench (projected 9.07 vs Smith 11.55). Lineup locks at 1:00pm ET / 11:00am MT. Team: https://football.fantasysports.yahoo.com/f1/891227/6 -- Also worth a glance: Kenyon Sadiq (NYJ TE) was Questionable too, though Kyle Pitts is the starter at TE this week and plays Monday night."
