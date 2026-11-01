"""Daily build: ESPN (+ Yahoo when it works) -> docs/data.json for the dashboard."""
import json
from datetime import datetime
from pathlib import Path

from nbafm import config, espn, model, rosters, yahoo

OUT = Path(__file__).resolve().parent / "docs" / "data.json"


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
    data["league"] = rosters.load(data["players"])
    OUT.write_text(json.dumps(data, separators=(",", ":")))
    print(f"wrote {OUT} ({len(data['players'])} players, scoring={'yahoo' if lg else 'config'})")


if __name__ == "__main__":
    main()
