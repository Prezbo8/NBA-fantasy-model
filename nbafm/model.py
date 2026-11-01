"""Turn box scores + schedule into per-player fantasy projections.

All dates are Eastern (an 8 PM ET tip is 00:00Z the next day in ESPN's feed).
Fantasy weeks run Monday-Sunday, like Yahoo's.
"""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from . import config

ET = ZoneInfo("America/New_York")


def et_date(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ET).date()


def fantasy_points(line, scoring):
    tens = sum(line[k] >= 10 for k in ("PTS", "REB", "AST", "STL", "BLK"))
    line = {**line, "DD": tens >= 2, "TD": tens >= 3}
    return sum(w * line.get(stat, 0) for stat, w in scoring.items())


def _avg(xs):
    return sum(xs) / len(xs) if xs else None


def _available_from(inj, today):
    """First date an injured player can play, or None if not ruled out."""
    if not inj or inj["status"] != "Out":
        return None
    if inj["return_date"]:
        return max(date.fromisoformat(inj["return_date"][:10]), today)
    return today + timedelta(days=7 - today.weekday())  # no date given: out the rest of this week


def build(schedule, box_scores, injuries, scoring, today, replacement_rank):
    """
    schedule:   [{id, date, home, away, completed}]
    box_scores: {game id: [player lines]}   (finished games only)
    injuries:   {player id: {status, return_date, note}}
    Returns the dict written to docs/data.json.
    """
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    horizon = [week_start + timedelta(days=i) for i in range(14)]  # this week + next

    # Remaining games per team (today's unfinished games count)
    team_dates = {}
    for g in schedule:
        d = et_date(g["date"])
        if d >= today and not g["completed"]:
            for t in (g["home"], g["away"]):
                team_dates.setdefault(t, []).append(d)
    games_by_day = {d.isoformat(): 0 for d in horizon}
    for g in schedule:
        k = et_date(g["date"]).isoformat()
        if k in games_by_day:
            games_by_day[k] += 1

    # Game logs
    logs = {}
    game_date = {g["id"]: et_date(g["date"]) for g in schedule}
    for gid, lines in box_scores.items():
        for ln in lines:
            logs.setdefault(ln["pid"], []).append((game_date[gid], ln))

    players = []
    for pid, log in logs.items():
        log.sort(key=lambda x: x[0])
        last = log[-1][1]
        fps = [(d, fantasy_points(ln, scoring), ln["MIN"]) for d, ln in log]
        windows = {"season": [f for _, f, _ in fps],
                   "l14": [f for d, f, _ in fps if d > today - timedelta(days=14)],
                   "l7": [f for d, f, _ in fps if d > today - timedelta(days=7)]}
        avgs = {k: _avg(v) for k, v in windows.items()}
        used = {k: w for k, w in config.BLEND.items() if avgs[k] is not None}
        blended = sum(avgs[k] * w for k, w in used.items()) / sum(used.values())
        min_season = _avg([m for _, _, m in fps])
        min_l7 = _avg([m for d, _, m in fps if d > today - timedelta(days=7)])
        players.append({
            "id": pid, "name": last["name"], "team": last["team"], "pos": last["pos"],
            "gp": len(fps), "min": round(min_season, 1),
            "min_trend": round(min_l7 - min_season, 1) if min_l7 is not None else None,
            "fp_season": round(avgs["season"], 2),
            "fp_l14": round(avgs["l14"], 2) if avgs["l14"] is not None else None,
            "fp_l7": round(avgs["l7"], 2) if avgs["l7"] is not None else None,
            "_blended": blended,
        })

    # Replacement level from raw blends, then shrink small samples toward it
    ranked = sorted((p["_blended"] for p in players), reverse=True)
    repl = ranked[min(replacement_rank, len(ranked)) - 1]
    k = config.SHRINK_GAMES
    for p in players:
        proj = (p["gp"] * p.pop("_blended") + k * repl) / (p["gp"] + k)
        inj = injuries.get(p["id"])
        avail = _available_from(inj, today)
        dates = [d for d in team_dates.get(p["team"], []) if avail is None or d >= avail]
        p.update({
            "proj": round(proj, 2),
            "vorp": round(proj - repl, 2),
            "inj": inj["status"] if inj else None,
            "inj_note": inj["note"] if inj else None,
            "wk_games": sum(1 for d in dates if d <= week_end),
            "nw_games": sum(1 for d in dates if week_end < d <= horizon[-1]),
            "ros_games": len(dates),
            "days": [d.isoformat() for d in dates if d <= horizon[-1]],
            "_dates": dates,  # full season, for power_rankings; removed before writing JSON
        })
        p["wk_fp"] = round(proj * p["wk_games"], 1)
        p["nw_fp"] = round(proj * p["nw_games"], 1)
        p["ros_fp"] = round(proj * p["ros_games"], 1)

    players.sort(key=lambda p: p["ros_fp"], reverse=True)
    return {
        "updated": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"),
        "today": today.isoformat(),
        "week": [week_start.isoformat(), week_end.isoformat()],
        "horizon": [d.isoformat() for d in horizon],
        "games_by_day": games_by_day,
        "team_days": {t: [d.isoformat() for d in ds if d <= horizon[-1]] for t, ds in sorted(team_dates.items())},
        "scoring": scoring,
        "replacement_fp": round(repl, 2),
        "players": players,
    }


def power_rankings(league, players, next_week, today):
    """Rank fantasy teams by roster alone: simulate every remaining day, each team scoring
    its 10 best projected players with a game (10 active slots), injured players skipped."""
    by_id = {p["id"]: p for p in players}
    # Same denominator for every team: full weeks left, from tomorrow (today may be half played)
    tomorrow = today + timedelta(days=1)
    season = {d for p in players for d in p["_dates"] if d >= tomorrow}
    weeks = len({d - timedelta(days=d.weekday()) for d in season})
    out = []
    for t in league["teams"]:
        ps = [by_id[i] for i in t["players"]]
        days = sorted({d for p in ps for d in p["_dates"] if d >= tomorrow})
        daily = {d: sum(sorted((p["proj"] for p in ps if d in p["_dates"]), reverse=True)[:10]) for d in days}
        out.append({
            "id": t["id"], "name": t["name"],
            "ros_wk": round(sum(daily.values()) / weeks),
            "next_wk": round(sum(v for d, v in daily.items() if d.isoformat() in next_week)),
            "healthy": round(sum(sorted((p["proj"] for p in ps), reverse=True)[:10]), 1),
            "stars": [[p["name"], round(p["proj"])] for p in sorted(ps, key=lambda p: -p["proj"])[:3]],
            "out": [p["name"] for p in ps if p["inj"] == "Out"],
            "unmatched": t["unmatched"],
        })
    return sorted(out, key=lambda t: -t["ros_wk"])
