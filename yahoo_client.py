"""Yahoo Fantasy Sports API client with durable OAuth.

Run this file directly once to do the interactive authorisation:

    uv run python yahoo_client.py

That writes YAHOO_REFRESH_TOKEN into .env. After that everything runs headless
- no browser, no logged-in session - which is the whole point of moving off the
Yahoo web UI.
"""

from __future__ import annotations

import os
import sys
import time
import webbrowser
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv, set_key

ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(ENV_PATH)

AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
API_BASE = "https://fantasysports.yahooapis.com/fantasy/v2"

# Every element in a Yahoo fantasy response carries this namespace.
NS = {"y": "http://fantasysports.yahooapis.com/fantasy/v2/base.rng"}


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.exit(f"{name} is not set in {ENV_PATH}. See .env.example.")
    return value


def authorize() -> None:
    """One-time interactive flow that mints a long-lived refresh token."""
    client_id = _require("YAHOO_CLIENT_ID")
    client_secret = _require("YAHOO_CLIENT_SECRET")
    redirect_uri = os.getenv("YAHOO_REDIRECT_URI", "https://localhost:8080/callback")

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "language": "en-us",
    }
    url = f"{AUTH_URL}?{urlencode(params)}"
    print("\nOpen this URL, sign in as yourself, and approve access:\n")
    print(url + "\n")
    print("Yahoo no longer accepts the 'oob' redirect, so after you approve it will")
    print(f"bounce you to {redirect_uri} and the browser will show a")
    print("connection error. That is expected - nothing is listening there.")
    print("Copy the 'code=' value out of the ADDRESS BAR (stop at any '&').\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass

    code = input("Paste the authorisation code here: ").strip()
    if not code:
        sys.exit("No code entered.")
    exchange_code(code)


def exchange_code(code: str) -> None:
    """Swap an authorisation code for a refresh token and save it.

    Split out so it can run non-interactively:  uv run python yahoo_client.py <code>
    Authorisation codes are single-use and expire quickly, so do this promptly.
    """
    client_id = _require("YAHOO_CLIENT_ID")
    client_secret = _require("YAHOO_CLIENT_SECRET")
    redirect_uri = os.getenv("YAHOO_REDIRECT_URI", "https://localhost:8080/callback")

    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": code,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    if not resp.ok:
        sys.exit(f"Token exchange failed ({resp.status_code}): {resp.text[:400]}")

    refresh_token = resp.json().get("refresh_token")
    if not refresh_token:
        sys.exit(f"No refresh_token in response: {resp.text[:400]}")

    set_key(str(ENV_PATH), "YAHOO_REFRESH_TOKEN", refresh_token)
    print(f"\nDone. Refresh token saved to {ENV_PATH}.")
    print("You should not need to repeat this.")


class Yahoo:
    """Thin read/write client. Refreshes the access token on construction."""

    def __init__(self) -> None:
        self.client_id = _require("YAHOO_CLIENT_ID")
        self.client_secret = _require("YAHOO_CLIENT_SECRET")
        self.refresh_token = _require("YAHOO_REFRESH_TOKEN")
        self._access_token = None
        self._expires_at = 0.0

    @property
    def access_token(self) -> str:
        if self._access_token and time.time() < self._expires_at - 60:
            return self._access_token
        resp = requests.post(
            TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": os.getenv("YAHOO_REDIRECT_URI", "oob"),
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        self._access_token = payload["access_token"]
        self._expires_at = time.time() + int(payload.get("expires_in", 3600))
        return self._access_token

    def get(self, path: str) -> ET.Element:
        resp = requests.get(
            f"{API_BASE}/{path.lstrip('/')}",
            headers={"Authorization": f"Bearer {self.access_token}"},
            timeout=30,
        )
        resp.raise_for_status()
        return ET.fromstring(resp.content)

    # -- key discovery ---------------------------------------------------
    # The NFL game key changes every season, so never hardcode it.

    def nfl_game_key(self) -> str:
        root = self.get("users;use_login=1/games;game_keys=nfl")
        keys = [el.text for el in root.iterfind(".//y:game_key", NS)]
        if not keys:
            raise RuntimeError("No NFL game key returned for this account.")
        return keys[-1]  # most recent season

    def league_key(self) -> str:
        return f"{self.nfl_game_key()}.l.{_require('LEAGUE_ID')}"

    def team_key(self) -> str:
        return f"{self.league_key()}.t.{_require('TEAM_ID')}"

    # -- reads -----------------------------------------------------------

    def roster(self) -> list[dict]:
        root = self.get(f"team/{self.team_key()}/roster/players")
        return [_player(p) for p in root.iterfind(".//y:player", NS)]

    def free_agents(self, position: str | None = None, count: int = 25) -> list[dict]:
        path = f"league/{self.league_key()}/players;status=A;sort=AR;count={count}"
        if position:
            path += f";position={position}"
        root = self.get(path)
        return [_player(p) for p in root.iterfind(".//y:player", NS)]

    def ir_eligible(self, count: int = 25) -> list[dict]:
        path = f"league/{self.league_key()}/players;status=IR;sort=AR;count={count}"
        root = self.get(path)
        return [_player(p) for p in root.iterfind(".//y:player", NS)]

    def standings(self) -> list[dict]:
        root = self.get(f"league/{self.league_key()}/standings")
        out = []
        for t in root.iterfind(".//y:team", NS):
            out.append(
                {
                    "name": _text(t, "y:name"),
                    "rank": _text(t, ".//y:rank"),
                    "wins": _text(t, ".//y:wins"),
                    "losses": _text(t, ".//y:losses"),
                    "points_for": _text(t, ".//y:points_for"),
                    "faab": _text(t, "y:faab_balance"),
                }
            )
        return out


def _text(el: ET.Element, path: str) -> str | None:
    found = el.find(path, NS)
    return found.text if found is not None else None


def _player(p: ET.Element) -> dict:
    return {
        "key": _text(p, "y:player_key"),
        "name": _text(p, "y:name/y:full"),
        "team": _text(p, "y:editorial_team_abbr"),
        "position": _text(p, "y:display_position"),
        "status": _text(p, "y:status"),
        "bye": _text(p, ".//y:bye_weeks/y:week"),
        "percent_owned": _text(p, ".//y:percent_owned/y:value"),
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        exchange_code(sys.argv[1])
    else:
        authorize()
