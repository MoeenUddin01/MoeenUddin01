#!/usr/bin/env python3
"""
Refresh data/contributions.json with the last year of GitHub contributions.

Primary path: GitHub GraphQL with GITHUB_TOKEN (works in Actions and includes
whatever private contributions the token can see).
Fallback:     scrape the public contribution calendar HTML (no token needed).

Usage:
    GITHUB_TOKEN=... python scripts/fetch_contributions.py
    python scripts/fetch_contributions.py            # public fallback
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "contributions.json"
LOGIN = os.environ.get("GH_LOGIN", "MoeenUddin01")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
          }
        }
      }
    }
  }
}
"""


def request(url: str, *, data: bytes | None = None, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": "MoeenUddin01-profile-card-updater",
            "Accept": "application/vnd.github+json",
            **(headers or {}),
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def from_graphql(today: date) -> dict:
    if not TOKEN:
        raise RuntimeError("no GITHUB_TOKEN/GH_TOKEN")
    start = today - timedelta(days=365)
    payload = json.dumps(
        {
            "query": QUERY,
            "variables": {
                "login": LOGIN,
                "from": f"{start.isoformat()}T00:00:00Z",
                "to": f"{today.isoformat()}T23:59:59Z",
            },
        }
    ).encode("utf-8")
    raw = request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    body = json.loads(raw.decode("utf-8"))
    if body.get("errors"):
        raise RuntimeError("; ".join(item.get("message", "GraphQL error") for item in body["errors"]))
    user = body.get("data", {}).get("user")
    if not user:
        raise RuntimeError(f"GraphQL returned no user for {LOGIN}")

    calendar = user["contributionsCollection"]["contributionCalendar"]
    days = []
    for week in calendar["weeks"]:
        for item in week["contributionDays"]:
            days.append(
                {
                    "date": item["date"],
                    "count": int(item["contributionCount"]),
                    "level": LEVELS.get(item["contributionLevel"], 0),
                }
            )
    days.sort(key=lambda item: item["date"])
    if not days:
        raise RuntimeError("GraphQL returned an empty calendar")
    return {
        "login": LOGIN,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": "github-graphql",
        "range": {"from": days[0]["date"], "to": days[-1]["date"]},
        "total_contributions": int(calendar.get("totalContributions") or sum(d["count"] for d in days)),
        "days": days,
    }


def from_html() -> dict:
    url = f"https://github.com/users/{LOGIN}/contributions"
    raw = request(url, headers={"Accept": "text/html"})
    page = raw.decode("utf-8", "replace")

    cells = []
    for tag in re.findall(r"<td\b[^>]*data-date=\"[^\"]+\"[^>]*>", page):
        day = re.search(r'data-date="([^"]+)"', tag)
        cell_id = re.search(r'id="([^"]+)"', tag)
        level = re.search(r'data-level="([^"]*)"', tag)
        if day and cell_id:
            cells.append((day.group(1), cell_id.group(1), level.group(1) if level else "0"))

    tips = {
        cell_id: html.unescape(re.sub(r"<[^>]+>", "", tip))
        for cell_id, tip in re.findall(
            r'<tool-tip\b[^>]*for="([^"]+)"[^>]*>(.*?)</tool-tip>', page, re.S
        )
    }

    days = []
    for day, cell_id, level in cells:
        label = tips.get(cell_id, "")
        match = re.search(r"^(No|\d[\d,]*)\s+contributions?\b", label.strip(), re.I)
        count = 0 if not match or match.group(1).lower() == "no" else int(match.group(1).replace(",", ""))
        days.append({"date": day, "count": count, "level": int(level or 0)})

    if not days:
        raise RuntimeError("could not parse the public contributions calendar")
    days.sort(key=lambda item: item["date"])
    return {
        "login": LOGIN,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": "github-contributions-html",
        "range": {"from": days[0]["date"], "to": days[-1]["date"]},
        "total_contributions": sum(d["count"] for d in days),
        "days": days,
    }


def main() -> None:
    today = datetime.now(timezone.utc).date()
    try:
        data = from_graphql(today)
    except Exception as exc:  # noqa: BLE001 - fall back on any API/token problem
        print(f"GraphQL unavailable ({exc}); falling back to the public calendar.", file=sys.stderr)
        data = from_html()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {OUT.relative_to(ROOT)} — {data['total_contributions']:,} contributions, "
        f"{len(data['days'])} days, source={data['source']}"
    )


if __name__ == "__main__":
    main()
