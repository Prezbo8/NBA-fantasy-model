"""Download 3 past seasons of ESPN box scores into research/cache/<season>/ (gitignored).
Re-running only fetches games not cached yet."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nbafm import espn  # noqa: E402

SEASONS = [2024, 2025, 2026]  # 2023-24, 2024-25, 2025-26
CACHE = Path(__file__).resolve().parent / "cache"

if __name__ == "__main__":
    team_ids = espn.teams()
    for season in SEASONS:
        d = CACHE / str(season)
        d.mkdir(parents=True, exist_ok=True)
        games = [g for g in espn.schedule(team_ids, season) if g["completed"]]
        (d / "schedule.json").write_text(json.dumps(games))
        with ThreadPoolExecutor(4) as pool:  # a few at a time; ESPN's public API, be polite
            done = sum(1 for _ in pool.map(lambda g: espn.box_score(g, d), games))
        print(f"{season}: {done} games cached")
