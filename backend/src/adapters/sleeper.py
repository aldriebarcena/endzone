from __future__ import annotations

import requests

from models import SleeperLeague

HOST = "https://api.sleeper.app/v1"


def fetch_league(league_id: str) -> SleeperLeague:
    response = requests.get(f"{HOST}/league/{league_id}", timeout=10)
    response.raise_for_status()
    return parse_league(response.json())


def parse_league(raw: dict) -> SleeperLeague:
    return SleeperLeague(
        league_id=raw["league_id"],
        name=raw["name"],
        season=raw["season"],
        status=raw["status"],
        total_rosters=int(raw["total_rosters"]),
        roster_positions=tuple(raw.get("roster_positions", ())),
        scoring_settings=dict(raw.get("scoring_settings", {})),
    )
