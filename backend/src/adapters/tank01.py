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
    return parse_box_score(fetch_box_score_raw(game_id))


def fetch_box_score_raw(game_id: str) -> dict:
    """Exposed separately (not just wrapped inside fetch_game_state) so
    callers that also need extract_player_categories() can reuse the same
    fetch instead of costing a second request against Tank01's scarce
    budget.
    """
    return _get("getNFLBoxScore", {"gameID": game_id})


def extract_player_names(box_score: dict) -> dict[str, str]:
    """player_id -> longName ("Gabe Davis"). Used alongside
    extract_player_categories() to disambiguate which of two same-
    category players (e.g. a TD receiver vs. an attached two-point-
    conversion's receiver, both "Receiving") is the actual scorer — see
    fantasy_points.py.
    """
    return {
        player_id: stats.get("longName", "")
        for player_id, stats in box_score.get("playerStats", {}).items()
    }


def extract_player_categories(box_score: dict) -> dict[str, frozenset[str]]:
    """player_id -> the set of stat categories ("Passing", "Rushing",
    "Receiving", "Kicking", ...) present for them in this box score.
    Used by fantasy_points.py to infer a scoring play's roles by
    elimination within the play's own player_ids, since Tank01's
    playerIDs list order isn't reliably [passer, receiver, kicker] (it
    breaks on two-point-conversion plays — see PROJECT_PLAN.md).
    """
    ignored_keys = {"gameID", "teamID", "team", "teamAbv", "playerID", "longName", "snapCounts"}
    return {
        player_id: frozenset(k for k in stats if k not in ignored_keys)
        for player_id, stats in box_score.get("playerStats", {}).items()
    }


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
        status_code=int(box_score["gameStatusCode"]),
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
