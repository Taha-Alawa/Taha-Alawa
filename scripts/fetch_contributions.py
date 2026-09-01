#!/usr/bin/env python3
"""
Fetch several calendar years of contributions - no token, no GraphQL.

  python scripts/fetch_contributions.py [username]

GitHub serves the calendar as public HTML at
https://github.com/users/<username>/contributions, and accepts ?from=&to=
to ask for a specific calendar year. Fetch one request per year, parse the
day cells, and write data/contributions.json with per-year grids plus
derived stats.

Note this only sees what a logged-out visitor sees. If most of your work
lives in private repos, turn on Settings -> Public profile -> "Include
private contributions on my profile" or every year here reads as empty.
"""

import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USERNAME = (
    (sys.argv[1] if len(sys.argv) > 1 else None)
    or os.environ.get("GH_USERNAME")
    or "Taha-Alawa"
)

OUT = Path("data/contributions.json")
BASE = f"https://github.com/users/{USERNAME}/contributions"
YEARS = 4                       # how many calendar years to stack
HEADERS = {
    "User-Agent": "Mozilla/5.0 (profile-art bot)",
    "Accept": "text/html",
    "X-Requested-With": "XMLHttpRequest",
}


def parse_count(cell, soup) -> int:
    """The count lives either on the cell or in a linked tooltip."""
    raw = cell.get("data-count")
    if raw is not None:
        return int(raw)

    cid = cell.get("id")
    if cid:
        tip = soup.find("tool-tip", attrs={"for": cid})
        if tip:
            m = re.search(r"([\d,]+|No)\s+contribution", tip.get_text())
            if m:
                return 0 if m.group(1) == "No" else int(m.group(1).replace(",", ""))
    return 0


def fetch_year(year: int) -> list[dict]:
    """One calendar year of day cells, oldest first."""
    r = requests.get(
        BASE,
        params={"from": f"{year}-01-01", "to": f"{year}-12-31"},
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    cells = soup.select("td.ContributionCalendar-day[data-date]")
    if not cells:
        sys.exit(f"no day cells for '{USERNAME}' in {year} - is the profile public?")

    days = [
        {"date": c["data-date"], "count": parse_count(c, soup)}
        for c in cells
        if c.get("data-date")
    ]
    days.sort(key=lambda d: d["date"])
    return days


def assign_levels(days: list[dict]) -> None:
    """GitHub's five buckets are relative to the busiest day. Recompute them
    across every year at once, so a quiet year reads as quiet next to a busy
    one instead of being stretched to fill its own scale."""
    counts = [d["count"] for d in days if d["count"] > 0]
    peak = max(counts) if counts else 0
    thresholds = [0, max(1, peak // 8), max(2, peak // 4), max(3, peak // 2)]

    for d in days:
        n = d["count"]
        lvl = len(thresholds)
        for i, t in enumerate(thresholds):
            if n <= t:
                lvl = i
                break
        if peak and n == peak:
            lvl = 5                             # neon top end for the best day
        d["level"] = lvl


def streaks(days: list[dict]) -> tuple[int, int]:
    today = date.today().isoformat()
    past = [d for d in days if d["date"] <= today]

    longest = run = 0
    for d in past:
        run = run + 1 if d["count"] > 0 else 0
        longest = max(longest, run)

    current = 0
    for d in reversed(past):
        if d["count"] > 0:
            current += 1
        elif d["date"] == today:
            continue                            # today may not be logged yet
        else:
            break
    return current, longest


def main() -> None:
    this_year = date.today().year
    years = list(range(this_year - YEARS + 1, this_year + 1))

    per_year = {}
    for y in years:
        per_year[y] = fetch_year(y)
        print(f"  {y}: {sum(d['count'] for d in per_year[y]):,}")

    flat = [d for y in years for d in per_year[y]]
    assign_levels(flat)

    today = date.today().isoformat()
    past = [d for d in flat if d["date"] <= today]
    current, longest = streaks(flat)
    best = max(past, key=lambda d: d["count"]) if past else {"date": "", "count": 0}

    payload = {
        "username": USERNAME,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "years": [
            {
                "year": y,
                "total": sum(d["count"] for d in per_year[y] if d["date"] <= today),
                "days": per_year[y],
            }
            for y in reversed(years)             # newest first, top of the stack
        ],
        "total": sum(d["count"] for d in past),
        "stats": {
            "current_streak": current,
            "longest_streak": longest,
            "best_day": best["date"],
            "best_day_count": best["count"],
            "active_days": sum(1 for d in past if d["count"] > 0),
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"wrote {OUT}  {payload['total']:,} across {YEARS} years, "
        f"streak {current}, longest {longest}"
    )


if __name__ == "__main__":
    main()
