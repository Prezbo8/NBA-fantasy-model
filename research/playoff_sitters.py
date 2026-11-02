"""For the top-30 players who sat through half or more of the fantasy playoffs: their team's
record and clinch status when the window opened, how the season ended, and the did-not-play
reasons from the box scores of the games they missed."""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nbafm import espn, model  # noqa: E402
from analyze_history import load  # noqa: E402
from fetch_history import CACHE, SEASONS  # noqa: E402

CLINCH = {"z": "clinched #1 seed", "y": "clinched division", "x": "clinched playoffs",
          "pb": "play-in", "e": "eliminated", "*": "clinched best record"}


def standings(season):
    return {t: {**s, "record": f"{s['wins']}-{s['losses']}"} for t, s in espn.standings(season).items()}


def results(season):
    """[(et_date, winner, loser)] from cached box scores (team points = sum of player points)."""
    d = CACHE / str(season)
    out = []
    for g in json.loads((d / "schedule.json").read_text()):
        pts = defaultdict(float)
        for ln in json.loads((d / f"{g['id']}.json").read_text()):
            pts[ln["team"]] += ln["PTS"]
        if len(pts) == 2:
            (a, pa), (b, pb) = pts.items()
            out.append((model.et_date(g["date"]), g["id"], a if pa > pb else b, b if pa > pb else a))
    return out


def status_on(team, day, res, stand):
    """Record + approximate clinch status before `day` (tiebreakers ignored, so 'clinched'
    here means mathematically safe even losing every tie)."""
    w, l, games = defaultdict(int), defaultdict(int), defaultdict(int)
    for d, _, win, lose in res:
        games[win] += 1
        games[lose] += 1
        if d < day:
            w[win] += 1
            l[lose] += 1
    conf = [t for t in stand if stand[t]["conf"] == stand[team]["conf"]]
    mx = {t: games[t] - l[t] for t in conf}  # max possible wins
    rivals = [t for t in conf if t != team]
    can_pass = sum(mx[t] >= w[team] for t in rivals)  # teams that could still finish ahead
    surely_ahead = sum(w[t] > mx[team] for t in rivals)
    rank = 1 + sum(w[t] > w[team] for t in rivals)
    if can_pass == 0:
        tag = "had locked up the #1 seed"
    elif can_pass <= 5:
        tag = "had clinched a top-6 (playoff) spot"
    elif surely_ahead >= 10:
        tag = "was already eliminated"
    elif surely_ahead >= 6:
        tag = "could no longer reach the top 6 (play-in at best)"
    else:
        tag = "was still playing for seeding/a spot"
    return f"{w[team]}-{l[team]}, #{rank} in {stand[team]['conf']}", tag


def dnp_reasons(pid, game_ids):
    """Why he sat, from the box scores' did-not-play reason (recorded at the time).
    (Don't use the summaries' "injuries" list for old games: ESPN fills it with today's report.)"""
    reasons = defaultdict(int)
    for gid in game_ids:
        rows = [a for side in espn._get("summary", event=gid)["boxscore"]["players"]
                for a in side["statistics"][0]["athletes"] if a["athlete"]["id"] == pid]
        reasons[(rows[0].get("reason") or "no reason given").title() if rows else "not on the box score"] += 1
    return [f"{r} ×{n}" for r, n in sorted(reasons.items(), key=lambda x: -x[1])]


def main():
    for season in SEASONS:
        ranked, (a, b) = load(season)
        stand, res = standings(season), results(season)
        team_games = max(p["po_gp"] for p in ranked)
        print(f"\n### {season - 1}-{str(season)[2:]} (fantasy playoffs {a:%b %d}–{b:%b %d})")
        for p in [p for p in ranked[:30] if p["po_gp"] <= team_games / 2]:
            t = p["team"]
            rec, tag = status_on(t, a, res, stand)
            window = [gid for d, gid, w_, l_ in res if a <= d <= b and t in (w_, l_)]
            played = {gid for gid in window if any(ln["pid"] == p["id"] for ln in json.loads((CACHE / str(season) / f"{gid}.json").read_text()))}
            missed = [gid for gid in window if gid not in played]
            s = stand[t]
            print(f"- **{p['name']}** ({t}) played {len(played)} of {len(window)} team games")
            print(f"  - when the window opened: {rec}, {tag}")
            print(f"  - final: {s['record']}, #{s['seed']} seed{', ' + CLINCH[s['clincher']] if s['clincher'] in CLINCH else ''}")
            print(f"  - why he missed games: {'; '.join(dnp_reasons(p['id'], missed))}")


if __name__ == "__main__":
    main()
