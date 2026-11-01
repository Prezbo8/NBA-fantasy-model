# NBA Fantasy Model

H2H points model for Yahoo league "NBA 2027" (108458). Dashboard: https://prezbo8.github.io/NBA-fantasy-model/

- `build.py` — daily run: ESPN schedule + box scores + injuries (and Yahoo league settings once the API works) → `docs/data.json`
- `nbafm/espn.py` — ESPN public API; finished box scores cached in `data/games/`
- `nbafm/yahoo.py` — Yahoo OAuth refresh + league scoring; skipped (default scoring) when unavailable
- `nbafm/model.py` — projections: blend season/L14/L7 FP per game, replacement level, schedule + injury availability
- `docs/index.html` — dashboard (Rankings, Schedule, Streamers, Trade; Waivers/Matchup/Drop need Yahoo)

Run locally: `.venv/bin/python build.py && .venv/bin/python -m http.server -d docs`
Secrets (Actions): `YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET`, `YAHOO_REFRESH_TOKEN`. Locally these come from the macOS Keychain.
