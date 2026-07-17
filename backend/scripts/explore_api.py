"""Phase 2, step 1: raw exploration against API-American-Football.

We don't yet know the exact response shape for games/events, so this hits
an arbitrary endpoint and dumps the raw JSON to disk for inspection rather
than guessing field names and writing a transform against them blind.
Once we've looked at real output, src/adapters/api_american_football.py
gets written against the actual shape.

Usage:
    RAPIDAPI_KEY=xxx python scripts/explore_api.py games --id 12345
    RAPIDAPI_KEY=xxx python scripts/explore_api.py games --date 2026-01-04

RAPIDAPI_HOST defaults to a best guess (api-american-football-v1.p.rapidapi.com).
Confirm the real host/base URL from the RapidAPI dashboard's "Code Snippets"
tab after subscribing — RapidAPI hosts aren't always consistent with the
product slug, and this default has not been verified against a real key.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

DEFAULT_HOST = "api-american-football-v1.p.rapidapi.com"
OUTPUT_DIR = Path(__file__).parent / "output"


def fetch(endpoint: str, params: dict[str, str]) -> dict:
    api_key = os.environ.get("RAPIDAPI_KEY")
    if not api_key:
        sys.exit("RAPIDAPI_KEY environment variable is required")
    host = os.environ.get("RAPIDAPI_HOST", DEFAULT_HOST)

    response = requests.get(
        f"https://{host}/{endpoint}",
        headers={"x-rapidapi-host": host, "x-rapidapi-key": api_key},
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("endpoint", help="e.g. games, games/events")
    parser.add_argument("--id", dest="game_id")
    parser.add_argument("--date")
    args = parser.parse_args()

    params = {}
    if args.game_id:
        params["id"] = args.game_id
    if args.date:
        params["date"] = args.date

    data = fetch(args.endpoint, params)

    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = OUTPUT_DIR / f"{args.endpoint.replace('/', '_')}_{timestamp}.json"
    out_path.write_text(json.dumps(data, indent=2))

    print(f"Saved response to {out_path}")
    print(json.dumps(data, indent=2)[:2000])


if __name__ == "__main__":
    main()
