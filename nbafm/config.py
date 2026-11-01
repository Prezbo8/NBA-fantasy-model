"""League settings and model knobs."""

LEAGUE_ID = "108458"  # Yahoo "NBA 2027"

# Yahoo's default H2H points weights. Used until the Yahoo API works; after that the
# league's own stat_modifiers replace these (yahoo.py -> build.py).
DEFAULT_SCORING = {
    "PTS": 1.0,
    "REB": 1.2,
    "AST": 1.5,
    "STL": 3.0,
    "BLK": 3.0,
    "TO": -1.0,
}

# Projected FP/game = weighted blend of these windows (weights renormalize over windows
# that have games, so a player with no games in the last 7 days falls back to season/L14).
BLEND = {"season": 0.5, "l14": 0.3, "l7": 0.2}

# Shrink toward replacement level as if every player also had K replacement-level games,
# so one hot night doesn't top the rankings: proj = (n*fp + K*repl) / (n + K).
SHRINK_GAMES = 1

# Replacement level = FP/game of the Nth best player (roughly teams x roster spots, e.g.
# 12 x 13 = 156). Replaced by the real number once Yahoo league settings load.
REPLACEMENT_RANK = 150
