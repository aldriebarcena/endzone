"""Phase 2, step 1: raw exploration against SportAPI7 (RapidAPI, rapidsportapi).

We don't yet know the exact response shape for games/events, so this hits
an arbitrary endpoint and dumps the raw JSON to disk for inspection rather
than guessing field names and writing a transform against them blind.
Once we've looked at real output, src/adapters/sportapi7.py gets written
against the actual shape.

Usage:
    RAPIDAPI_KEY=xxx python scripts/explore_api.py api/american-football/matches/live
    RAPIDAPI_KEY=xxx python scripts/explore_api.py api/american-football/match/12345

RAPIDAPI_HOST defaults to a best guess (sportapi7.p.rapidapi.com), and the
endpoint paths above are a guess based on this provider's typical SofaScore-
style REST convention — neither has been verified against a real key yet.
Confirm both from the RapidAPI dashboard's "Code Snippets" / "Endpoints"
tab after subscribing.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

DEFAULT_HOST = "sportapi7.p.rapidapi.com"
OUTPUT_DIR = Path(__file__).parent / "output"


def fetch(endpoint: str, params: dict[str, str]) -> dict:
    api_key = os.environ.get("RAPIDAPI_KEY")
    if not api_key:
        sys.exit("RAPIDAPI_KEY environment variable is required")
    host = os.environ.get("RAPIDAPI_HOST", DEFAULT_HOST)

    response = requests.get(
        f"https://{host}/{endpoint.lstrip('/')}",
        headers={"x-rapidapi-host": host, "x-rapidapi-key": api_key},
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("endpoint", help="path, e.g. api/american-football/match/12345")
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="repeatable query param, e.g. --param date=2026-01-04",
    )
    args = parser.parse_args()

    params = dict(p.split("=", 1) for p in args.param)

    data = fetch(args.endpoint, params)

    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = OUTPUT_DIR / f"{args.endpoint.replace('/', '_')}_{timestamp}.json"
    out_path.write_text(json.dumps(data, indent=2))

    print(f"Saved response to {out_path}")
    print(json.dumps(data, indent=2)[:2000])


if __name__ == "__main__":
    main()
