"""Daily build: ESPN (+ Yahoo when it works) -> docs/data.json for the dashboard."""
import json
from datetime import datetime
from pathlib import Path

from nbafm import config, espn, model, rosters, yahoo

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs" / "data.json"
LAST_SEASON = ROOT / "data" / "last_season.json"  # research/export_last_season.py


def main():
    today = datetime.now(model.ET).date()
    team_ids = espn.teams()
    schedule = espn.schedule(team_ids)
    finished = [g for g in schedule if g["completed"]]
    box = {g["id"]: espn.box_score(g) for g in finished}
    print(f"espn: {len(schedule)} games, {len(finished)} finished")
    injuries = espn.injuries()

    lg = yahoo.league()
    scoring = lg["scoring"] if lg else config.DEFAULT_SCORING
    repl_rank = lg["num_teams"] * lg["roster_size"] if lg else config.REPLACEMENT_RANK

    data = model.build(schedule, box, injuries, scoring, today, repl_rank)
    data["yahoo"] = lg is not None
    last = json.loads(LAST_SEASON.read_text())
    b = config.BUY_LOW
    for p in data["players"]:
        ls = last.get(p["id"])
        p["last_fpg"] = ls["fpg"] if ls else None
        p["vs_last"] = round(p["fp_season"] - ls["fpg"], 1) if ls else None
        p["buy_low"] = bool(ls and ls["fpg"] >= b["min_last_fpg"] and ls["gp"] >= b["min_last_gp"]
                            and p["vs_last"] <= -b["gap"] and p["min"] >= ls["min"] - b["max_min_drop"])
    risk = model.playoff_risk(espn.standings(), espn.standings(config.PRIOR_SEASON))
    data["playoff_risk"] = risk
    for p in data["players"]:
        r = risk.get(p["team"])
        p["po_tier"], p["po_avail"] = (r["tier"], r["avail"]) if r else (None, None)
    data["league"] = rosters.load(data["players"])
    if data["league"]:
        data["league"]["power"] = model.power_rankings(data["league"], data["players"], data["horizon"][7:], today)
    for p in data["players"]:
        del p["_dates"]
    OUT.write_text(json.dumps(data, separators=(",", ":")))
    print(f"wrote {OUT} ({len(data['players'])} players, scoring={'yahoo' if lg else 'config'})")


if __name__ == "__main__":
    main()
