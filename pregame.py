"""Is an NBA game tipping off in the next 30 minutes? Prints run=true/false (to $GITHUB_OUTPUT
when set). The external pinger calls the workflow with slot=pregame at :15 and :45, so each
tip-off falls in exactly one window and gets one build ~15 minutes before it.
Standard library only, so the workflow can decide before installing anything.
"""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

WINDOW = timedelta(minutes=30)

now = datetime.now(timezone.utc)
day = now.astimezone(ZoneInfo("America/New_York")).strftime("%Y%m%d")
url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={day}"
events = json.load(urllib.request.urlopen(url, timeout=30))["events"]
tips = [datetime.fromisoformat(e["date"].replace("Z", "+00:00")) for e in events]
soon = [t for t in tips if timedelta(0) < t - now <= WINDOW]

print(f"{len(tips)} games today, {len(soon)} tipping off in the next 30 min")
line = f"run={'true' if soon else 'false'}"
print(line)
if os.environ.get("GITHUB_OUTPUT"):
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write(line + "\n")
