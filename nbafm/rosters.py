"""League rosters -> ESPN player ids.

data/rosters.json is a snapshot read from the Yahoo league pages in the browser (the API
still returns 403). Refresh it whenever rosters change; it goes stale otherwise.
"""
import json
import re
import unicodedata
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "data" / "rosters.json"
YAHOO_TO_ESPN_TEAM = {"GSW": "GS", "NYK": "NY", "NOP": "NO", "SAS": "SA", "UTA": "UTAH", "WAS": "WSH"}


def _norm(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z ]", "", s.replace("-", " "))
    return " ".join(w for w in s.split() if w not in ("jr", "sr", "ii", "iii", "iv"))


def _initial_last(name):
    """'N. Alexander-Walker' and 'Nickeil Alexander-Walker' -> 'n alexander walker'"""
    words = _norm(name).split()
    return f"{words[0][0]} {' '.join(words[1:])}" if len(words) > 1 else _norm(name)


def load(players):
    """Annotate players (model output) with owner/slot/elig; return the league dict or None."""
    if not PATH.exists():
        return None
    snap = json.loads(PATH.read_text())
    by_full, by_short = {}, {}
    for p in players:
        by_full.setdefault(_norm(p["name"]), []).append(p)
        by_short.setdefault(_initial_last(p["name"]), []).append(p)
    teams = []
    for t in snap["teams"]:
        ids, unmatched = [], []
        for r in t["players"]:
            team = YAHOO_TO_ESPN_TEAM.get(r["nba"], r["nba"])
            cands = by_full.get(_norm(r["name"])) or by_short.get(_initial_last(r["name"])) or []
            if len(cands) > 1:
                cands = [c for c in cands if c["team"] == team] or cands
            if len(cands) != 1:
                unmatched.append(r["name"])  # usually: hasn't played a game yet this season
                continue
            p = cands[0]
            p.update(owner=t["id"], slot=r["slot"], elig=r["elig"])
            ids.append(p["id"])
        if unmatched:
            print(f"rosters: {t['name']}: no ESPN match for {unmatched}")
        teams.append({"id": t["id"], "name": t["name"], "players": ids, "unmatched": unmatched})
    return {"as_of": snap["as_of"], "my_team": snap["my_team"], "teams": teams}
