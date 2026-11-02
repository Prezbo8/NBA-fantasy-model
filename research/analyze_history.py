"""What kind of players win a 10-team league with OUR scoring? 3 past seasons of box scores
(research/fetch_history.py), scored with config.DEFAULT_SCORING.

Rostered pool = top 130 by season total (10 teams x 13 non-IL spots).
Fantasy playoffs = the 3 Mon-Sun weeks ending the Sunday before the NBA's final week,
the same rule as this league (weeks 20-22 end Apr 4 2027; NBA ends Apr 11).
"""
import json
import statistics as st
import sys
from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nbafm import config, model  # noqa: E402
from fetch_history import CACHE, SEASONS  # noqa: E402

SC = config.DEFAULT_SCORING
POOL, STARS = 130, 20
# FP by source, to see which stats our scoring rewards
SOURCES = {"PTS": ["PTS"], "3PTM": ["3PTM"], "FTM": ["FTM"], "REB": ["OREB", "DREB"], "AST": ["AST"],
           "STL+BLK": ["STL", "BLK"], "TO": ["TO"], "DD/TD": ["DD", "TD"]}


def pos_group(pos):
    return "C" if "C" in pos else "G" if "G" in pos else "F"


def load(season):
    d = CACHE / str(season)
    games = json.loads((d / "schedule.json").read_text())
    last = max(model.et_date(g["date"]) for g in games)
    po_end = last - timedelta(days=last.weekday()) - timedelta(days=1)
    po_start = po_end - timedelta(days=20)
    players = defaultdict(lambda: {"gp": 0, "fp": 0.0, "min": 0.0, "po_gp": 0, "po_fp": 0.0,
                                   "src": Counter(), "pos": Counter()})
    for g in games:
        f = d / f"{g['id']}.json"
        if not f.exists():
            continue
        day = model.et_date(g["date"])
        for ln in json.loads(f.read_text()):
            p = players[ln["pid"]]
            fp = model.fantasy_points(ln, SC)
            tens = sum(ln[k] >= 10 for k in ("PTS", "REB", "AST", "STL", "BLK"))
            ln = {**ln, "DD": tens >= 2, "TD": tens >= 3}
            for s, keys in SOURCES.items():
                p["src"][s] += sum(SC.get(k, 0) * ln.get(k, 0) for k in keys)
            p["name"] = ln["name"]
            p["team"] = ln["team"]  # games are in date order, so this ends as his latest team
            p["pos"][pos_group(ln["pos"])] += 1
            p["gp"] += 1
            p["fp"] += fp
            p["min"] += ln["MIN"]
            if po_start <= day <= po_end:
                p["po_gp"] += 1
                p["po_fp"] += fp
    for pid, p in players.items():
        p["id"] = pid
        p["pos"] = p["pos"].most_common(1)[0][0]
        p["fpg"] = p["fp"] / p["gp"]
    ranked = sorted(players.values(), key=lambda p: -p["fp"])
    for i, p in enumerate(ranked, 1):
        p["rank"] = i
    return ranked, (po_start, po_end)


def pct(n, d):
    return f"{100 * n / d:.0f}%"


def main():
    seasons = {s: load(s) for s in SEASONS}
    out = []
    w = out.append
    label = {s: f"{s - 1}-{str(s)[2:]}" for s in SEASONS}

    w("## 1. Positions: who fills the top of the rankings\n")
    w("| Season | Top 20: G / F / C | Top 130: G / F / C | All players: G / F / C |")
    w("|---|---|---|---|")
    for s, (r, _) in seasons.items():
        def mix(ps):
            c = Counter(p["pos"] for p in ps)
            return " / ".join(pct(c[x], len(ps)) for x in "GFC")
        regulars = [p for p in r if p["gp"] >= 20]
        w(f"| {label[s]} | {mix(r[:STARS])} | {mix(r[:POOL])} | {mix(regulars)} |")

    w("\n## 2. Where the points come from (share of FP, before turnovers)\n")
    w("| Season | Group | " + " | ".join(k for k in SOURCES if k != "TO") + " | TO |")
    w("|---|---|" + "---|" * len(SOURCES))
    for s, (r, _) in seasons.items():
        for name, ps in (("Top 20", r[:STARS]), ("Top 21-130", r[STARS:POOL])):
            tot = Counter()
            for p in ps:
                tot.update(p["src"])
            pos_sum = sum(v for k, v in tot.items() if k != "TO")
            cells = [pct(tot[k], pos_sum) for k in SOURCES if k != "TO"]
            w(f"| {label[s]} | {name} | " + " | ".join(cells) + f" | {pct(-tot['TO'], pos_sum)} |")

    w("\n## 3. Top 10 by season total\n")
    for s, (r, _) in seasons.items():
        w(f"**{label[s]}:** " + ", ".join(f"{p['name']} ({p['pos']}, {p['fpg']:.1f}/g, {p['gp']} GP)" for p in r[:10]))
        w("")

    w("## 4. Durability: games played vs per-game production\n")
    w("| Season | Avg GP, top 20 by total | Top-20-per-game players (20+ GP) who missed the top 20 by total | GP of those |")
    w("|---|---|---|---|")
    for s, (r, _) in seasons.items():
        top_total = {p["id"] for p in r[:STARS]}
        by_pg = sorted((p for p in r if p["gp"] >= 20), key=lambda p: -p["fpg"])[:STARS]
        missed = [p for p in by_pg if p["id"] not in top_total]
        w(f"| {label[s]} | {st.mean(p['gp'] for p in r[:STARS]):.0f} | {len(missed)} of 20 | "
          + ", ".join(f"{p['name']} {p['gp']}" for p in missed) + " |")

    w("\n## 5. Fantasy playoffs (weeks 20-22 equivalent)\n")
    w("| Season | Window | Top-30 players who played ≤ 50% of playoff games | Best playoff scorers outside the season top 50 |")
    w("|---|---|---|---|")
    for s, (r, (a, b)) in seasons.items():
        team_games = max(p["po_gp"] for p in r)  # most games any player played in the window
        sat = [p for p in r[:30] if p["po_gp"] <= team_games / 2]
        sleepers = sorted((p for p in r[50:] if p["po_gp"]), key=lambda p: -p["po_fp"])[:5]
        w(f"| {label[s]} | {a:%b %d}–{b:%b %d} ({team_games} max G) | {len(sat)}: "
          + ", ".join(f"{p['name']} ({p['po_gp']}G)" for p in sat) + " | "
          + ", ".join(f"{p['name']} {p['po_fp']:.0f}" for p in sleepers) + " |")

    w("\n## 6. Breakouts: top-130 players who were outside the top 130 the season before\n")
    for prev, s in zip(SEASONS, SEASONS[1:]):
        prev_rank = {p["id"]: p["rank"] for p in seasons[prev][0]}
        r = seasons[s][0]
        new = [p for p in r[:POOL] if prev_rank.get(p["id"], 999) > POOL]
        top50_new = [p for p in r[:50] if prev_rank.get(p["id"], 999) > POOL]
        w(f"**{label[s]}:** {len(new)} of 130 ({pct(len(new), POOL)}) were new, {len(top50_new)} of them in the top 50: "
          + ", ".join(f"{p['name']} (#{p['rank']}, was {'#' + str(prev_rank[p['id']]) if p['id'] in prev_rank else 'no games'})" for p in top50_new[:8]))
        w("")

    text = "\n".join(out)
    (Path(__file__).resolve().parent / "findings.md").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
