"""League settings and model knobs."""

LEAGUE_ID = "108458"  # Yahoo "NBA 2027"

# League scoring, copied from the league's Scoring & Settings page (Nov 1 2026).
# Once the Yahoo API works, its stat_modifiers replace these (yahoo.py -> build.py).
# DD/TD are derived per game in model.fantasy_points (a triple-double scores both).
DEFAULT_SCORING = {
    "FTM": 1.0,
    "3PTM": 3.0,
    "PTS": 0.5,
    "OREB": 2.0,
    "DREB": 1.0,
    "AST": 2.0,
    "STL": 3.0,
    "BLK": 3.0,
    "TO": -2.0,
    "DD": 5.0,
    "TD": 7.0,
}

# Projected FP/game = weighted blend of these windows (weights renormalize over windows
# that have games, so a player with no games in the last 7 days falls back to season/L14).
BLEND = {"season": 0.5, "l14": 0.3, "l7": 0.2}

# Shrink toward replacement level as if every player also had K replacement-level games,
# so one hot night doesn't top the rankings: proj = (n*fp + K*repl) / (n + K).
SHRINK_GAMES = 1

# Replacement level = FP/game of the Nth best player: 10 teams x 13 non-IL roster spots.
REPLACEMENT_RANK = 130

# Fantasy-playoff (weeks 20-22) risk. Share of team games top-100 players played during the
# fantasy playoffs, 2023-24 to 2025-26, by where their team finished (research/, Nov 2026).
# Before the window everyone played ~91-95%.
PLAYOFF_AVAIL = {"Top-2 seed": 0.83, "Seeds 3-6": 0.85, "Play-in": 0.84, "Lottery": 0.71}
# Projected finish = current record + last season's win% counted as this many extra games
PRIOR_GAMES = 20
PRIOR_SEASON = 2026  # ESPN season year of last season (2025-26)
