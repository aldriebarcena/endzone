from __future__ import annotations

import os
from datetime import datetime, timezone

import requests

from models import GameState, ScoringEvent

HOST = "tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com"


def _get(endpoint: str, params: dict[str, str]) -> dict:
    api_key = os.environ["RAPIDAPI_KEY"]
    response = requests.get(
        f"https://{HOST}/{endpoint}",
        headers={"x-rapidapi-host": HOST, "x-rapidapi-key": api_key},
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["body"]


def fetch_game_state(game_id: str) -> GameState:
    return parse_box_score(_get("getNFLBoxScore", {"gameID": game_id}))


def fetch_games_for_date(date: str) -> list[dict]:
    """date is YYYYMMDD. Returns the raw provider game list — gameID,
    gameStatusCode (0 not started, 1 in progress, 2 final, 3 postponed,
    4 suspended), among other fields. No internal model for this yet;
    the checker only needs gameID + gameStatusCode.
    """
    return _get("getNFLGamesForDate", {"gameDate": date})


def parse_box_score(box_score: dict) -> GameState:
    fetched_at = datetime.now(timezone.utc)
    events = tuple(
        _to_scoring_event(play, box_score["gameID"], fetched_at)
        for play in box_score.get("scoringPlays", [])
    )
    return GameState(
        game_id=box_score["gameID"],
        status=box_score["gameStatus"],
        home_team=box_score["home"],
        away_team=box_score["away"],
        home_score=int(box_score["homePts"]),
        away_score=int(box_score["awayPts"]),
        period=box_score["currentPeriod"],
        clock=box_score.get("gameClock") or None,
        events=events,
        fetched_at=fetched_at,
    )


def _to_scoring_event(play: dict, game_id: str, fetched_at: datetime) -> ScoringEvent:
    event_id = f"{game_id}:{play['scorePeriod']}:{play['scoreTime']}:{play['team']}:{play['scoreType']}"
    return ScoringEvent(
        event_id=event_id,
        game_id=game_id,
        team=play["team"],
        scoring_type=play["scoreType"],
        description=play["score"],
        period=play["scorePeriod"],
        game_clock=play["scoreTime"],
        home_score=int(play["homeScore"]),
        away_score=int(play["awayScore"]),
        player_ids=tuple(play.get("playerIDs", ())),
        fetched_at=fetched_at,
    )
