"""Yahoo Fantasy API: OAuth refresh + league settings.

Credentials come from env vars (GitHub Actions secrets) or, locally, the macOS Keychain.
As of Nov 1 2026 every Fantasy call returns 403 "This application is not authorized";
league() then returns None and the model runs on config.DEFAULT_SCORING.
Rosters / free agents get added once real responses can be inspected.
"""
import os
import subprocess

import requests

from . import config

KEYCHAIN = {"YAHOO_CLIENT_ID": "nba-fantasy-yahoo-client-id",
            "YAHOO_CLIENT_SECRET": "nba-fantasy-yahoo-client-secret",
            "YAHOO_REFRESH_TOKEN": "nba-fantasy-yahoo-refresh-token"}
API = "https://fantasysports.yahooapis.com/fantasy/v2"
# Yahoo stat display names -> box-score keys in espn.py
STAT_NAMES = {"PTS": "PTS", "REB": "REB", "AST": "AST", "ST": "STL", "BLK": "BLK", "TO": "TO",
              "OREB": "OREB", "DREB": "DREB", "FGM": "FGM", "FGA": "FGA", "FTM": "FTM",
              "FTA": "FTA", "3PTM": "3PTM", "3PTA": "3PTA", "DD": "DD", "TD": "TD"}


def _secret(name):
    if os.environ.get(name):
        return os.environ[name]
    try:
        r = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN[name], "-w"],
                           capture_output=True, text=True)
    except FileNotFoundError:  # not macOS (e.g. GitHub Actions without the secrets set)
        return None
    return r.stdout.strip() or None


def _access_token():
    cid, sec, rt = (_secret(k) for k in KEYCHAIN)
    if not (cid and sec and rt):
        return None
    r = requests.post("https://api.login.yahoo.com/oauth2/get_token", auth=(cid, sec), timeout=30,
                      data={"grant_type": "refresh_token", "refresh_token": rt,
                            "redirect_uri": "https://localhost:8000"})
    r.raise_for_status()
    return r.json()["access_token"]


def league():
    """{scoring: {stat: weight}, num_teams, roster_size} or None if Yahoo is unavailable."""
    try:
        token = _access_token()
        if not token:
            print("yahoo: no credentials, skipping")
            return None
        r = requests.get(f"{API}/league/nba.l.{config.LEAGUE_ID}/settings", timeout=30,
                         params={"format": "json"}, headers={"Authorization": f"Bearer {token}"})
        if r.status_code != 200:
            print(f"yahoo: HTTP {r.status_code} {r.text[:200]!r}, skipping")
            return None
        lg = r.json()["fantasy_content"]["league"]
        settings = lg[1]["settings"][0]
    except (requests.RequestException, KeyError, IndexError) as e:
        print(f"yahoo: {e!r}, skipping")
        return None
    names = {c["stat"]["stat_id"]: c["stat"]["display_name"]
             for c in settings["stat_categories"]["stats"]}
    scoring = {}
    for m in settings["stat_modifiers"]["stats"]:
        name = names.get(m["stat"]["stat_id"])
        if name in STAT_NAMES:
            scoring[STAT_NAMES[name]] = float(m["stat"]["value"])
        else:
            print(f"yahoo: unscored stat {name!r} (weight {m['stat']['value']})")
    roster_size = sum(int(p["roster_position"]["count"]) for p in settings["roster_positions"]
                      if p["roster_position"]["position"] not in ("IL", "IL+"))
    return {"scoring": scoring, "num_teams": int(lg[0]["num_teams"]), "roster_size": roster_size}
