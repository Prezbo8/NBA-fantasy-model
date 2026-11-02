"""Write data/last_season.json: {espn id: {fpg, gp, min}} for 2025-26 under league scoring,
used by the daily build for the Buy-low column. Re-run if the league's scoring changes."""
import json
from pathlib import Path

from analyze_history import load

if __name__ == "__main__":
    ranked, _ = load(2026)
    out = {p["id"]: {"fpg": round(p["fpg"], 2), "gp": p["gp"], "min": round(p["min"] / p["gp"], 1)} for p in ranked}
    path = Path(__file__).resolve().parent.parent / "data" / "last_season.json"
    path.write_text(json.dumps(out, separators=(",", ":")))
    print(f"wrote {path} ({len(out)} players)")
