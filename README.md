# fantasy-bot

Tuesday-night waiver report for **The Shiva Bowl** (Yahoo league 891227, team 6,
*Champion by Skill Alone*). Runs off the Yahoo Fantasy API, so it needs no
browser and no logged-in session — that's the point.

**It is read-only.** It emails a summary for David to approve; it never submits
a claim on its own.

## One-time setup

**1. Create a Yahoo app** — <https://developer.yahoo.com/apps/create/>

| Field | Value |
|---|---|
| Application Name | anything, e.g. `Fantasy Connection` |
| Homepage URL | leave blank |
| **Redirect URI(s)** | **`https://localhost:8080/callback`** |
| OAuth Client Type | **Confidential Client** (the default) |
| API Permissions | tick **Fantasy Sports** → a **Read** radio appears and self-selects |

Copy the **Client ID** and **Client Secret**.

⚠️ **Verified against the live form, 2026-09-29:**
- **`oob` is rejected** — the form says *"Invalid URI."* and leaves *Create App*
  greyed out. An `https://` redirect is mandatory. Nothing has to listen on it:
  after approving you get a browser connection error and copy the `code=` value
  out of the address bar.
- **"Read" is the only Fantasy Sports permission Yahoo still offers.** Read/Write
  is gone. That is fine for this tool, which is read-only by design — but it
  means **waiver claims can never be submitted through the API**. Submitting
  stays a browser job.
- *Create App* only enables once the name, an https redirect URI **and** a
  permission are all set.

**2. Fill in credentials**

```powershell
cd C:\Users\davep\fantasy-bot
copy .env.example .env
notepad .env
```

Put the Client ID/Secret in yourself. For email, Gmail needs an **App Password**
(<https://myaccount.google.com/apppasswords>, requires 2-Step Verification) —
that is not your Google password and can be revoked on its own.

**3. Authorise once**

```powershell
uv run python yahoo_client.py
```

Approve in the browser, paste the code back. It writes `YAHOO_REFRESH_TOKEN`
into `.env`. The refresh token is long-lived — this is the "access in
perpetuity" part, and you can revoke it any time at
<https://login.yahoo.com/account/security#apps>.

**4. Test**

```powershell
uv run python weekly_waivers.py --dry-run
```

**5. Schedule it** — Tuesdays at 7:03pm

```powershell
schtasks /Create /TN "ShivaBowlWaivers" /SC WEEKLY /D TUE /ST 19:03 ^
  /TR "cmd /c cd /d C:\Users\davep\fantasy-bot && uv run python weekly_waivers.py" ^
  /RL LIMITED /F
```

## Gotchas

- **Never hardcode the NFL game key** — it changes each season. `nfl_game_key()`
  discovers it from the account.
- **IR eligibility lapses.** A player on IR whose status improves from `O` to `D`
  stops qualifying and then blocks *every* add/drop with error 845 until moved
  off IR. The report flags roster status for this reason.
- **An IR-eligible add still requires a bench drop** — they land on the bench
  first, not straight into the IR slot.
- `.env` holds live credentials. It is gitignored; keep it that way.
