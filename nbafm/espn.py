"""ESPN public NBA API: team schedules, box scores, injuries.

Box scores of finished games never change, so each is cached in data/games/<id>.json
(committed to the repo) and only new games are fetched on each run.
"""
import json
import re
from pathlib import Path

import requests

BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
GAMES_DIR = Path(__file__).resolve().parent.parent / "data" / "games"
STAT_KEYS = {"points": "PTS", "rebounds": "REB", "assists": "AST", "steals": "STL",
             "blocks": "BLK", "turnovers": "TO", "minutes": "MIN",
             "offensiveRebounds": "OREB", "defensiveRebounds": "DREB"}
# "made-attempted" columns, kept so any Yahoo scoring setting can be applied to the cache
SPLIT_KEYS = {"fieldGoalsMade-fieldGoalsAttempted": ("FGM", "FGA"),
              "threePointFieldGoalsMade-threePointFieldGoalsAttempted": ("3PTM", "3PTA"),
              "freeThrowsMade-freeThrowsAttempted": ("FTM", "FTA")}

session = requests.Session()


def _get(path, **params):
    r = session.get(f"{BASE}/{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def _num(s):
    """ESPN uses '--' (and sometimes '') for empty cells."""
    try:
        return float(s)
    except (TypeError, ValueError):
        return 0.0


def teams():
    """{espn team id: abbreviation}"""
    league = _get("teams")["sports"][0]["leagues"][0]
    return {t["team"]["id"]: t["team"]["abbreviation"] for t in league["teams"]}


def schedule(team_ids):
    """Every regular-season game: [{id, date (UTC ISO), home, away, completed}], deduped."""
    games = {}
    for tid in team_ids:
        for e in _get(f"teams/{tid}/schedule", seasontype=2)["events"]:
            c = e["competitions"][0]
            side = {x["homeAway"]: x["team"]["abbreviation"] for x in c["competitors"]}
            games[e["id"]] = {"id": e["id"], "date": e["date"], "home": side["home"],
                              "away": side["away"], "completed": c["status"]["type"]["completed"]}
    return sorted(games.values(), key=lambda g: g["date"])


def box_score(game):
    """Player lines for a finished game, cached on disk. [{pid, name, pos, team, MIN, PTS, ...}]"""
    path = GAMES_DIR / f"{game['id']}.json"
    if path.exists():
        return json.loads(path.read_text())
    lines = []
    for side in _get("summary", event=game["id"])["boxscore"]["players"]:
        team = side["team"]["abbreviation"]
        st = side["statistics"][0]
        keys = st["keys"]
        for a in st["athletes"]:
            if a.get("didNotPlay") or not a["stats"]:
                continue
            row = dict(zip(keys, a["stats"]))
            if not _num(row.get("minutes")):
                continue
            line = {"pid": a["athlete"]["id"], "name": a["athlete"]["displayName"],
                    "pos": a["athlete"].get("position", {}).get("abbreviation", ""), "team": team}
            for k, short in STAT_KEYS.items():
                line[short] = _num(row.get(k))
            for k, (made, att) in SPLIT_KEYS.items():
                m, _, a_ = (row.get(k) or "").partition("-")
                line[made], line[att] = _num(m), _num(a_)
            lines.append(line)
    path.write_text(json.dumps(lines, separators=(",", ":")))
    return lines


def injuries():
    """{espn player id: {status, return_date, note}}"""
    out = {}
    for team in _get("injuries")["injuries"]:
        for i in team["injuries"]:
            links = i["athlete"].get("links", [])
            m = next((re.search(r"/id/(\d+)", l["href"]) for l in links if "/id/" in l["href"]), None)
            if not m:
                continue
            out[m.group(1)] = {"status": i["status"],
                               "return_date": i.get("details", {}).get("returnDate"),
                               "note": i.get("shortComment", "")}
    return out
