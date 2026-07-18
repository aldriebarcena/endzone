from __future__ import annotations

import os

import boto3

import storage
from adapters.espn import from_dict as espn_play_from_dict
from api.common import json_response, user_id_from_event
from fantasy_points import points_for_matched_play
from models import GameState, ScoringEvent


def handler(event, context):
    user_id = user_id_from_event(event)

    game_state = _current_game_state()
    if game_state is None:
        return json_response(404, {"error": "no live game currently tracked"})

    point_values = _point_values_for_user(user_id)

    return json_response(
        200,
        {
            "gameId": game_state.game_id,
            "status": game_state.status,
            "statusCode": game_state.status_code,
            "homeTeam": game_state.home_team,
            "awayTeam": game_state.away_team,
            "homeScore": game_state.home_score,
            "awayScore": game_state.away_score,
            "period": game_state.period,
            "clock": game_state.clock,
            "fetchedAt": game_state.fetched_at.isoformat(),
            "events": [_event_response(e, point_values) for e in game_state.events],
        },
    )


def _current_game_state() -> GameState | None:
    # v1 only ever tracks one game globally (DESIGN.md's explicit scope
    # decision), so "the current game" is just whichever stored item was
    # fetched most recently — handles a previous game's item not yet
    # TTL-expired (up to ~24h) without needing a dedicated "current game"
    # pointer record. Scan is fine at this table's size (one live item
    # at a time, occasional stale ones pending TTL).
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(os.environ["LIVE_GAME_STATE_TABLE"])
    items = table.scan().get("Items", [])
    if not items:
        return None
    latest_item = max(items, key=lambda item: item["fetchedAt"])
    return storage.from_item(latest_item)


def _point_values_for_user(user_id: str) -> dict[str, float]:
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(os.environ["LEAGUE_CONFIG_TABLE"])
    item = table.get_item(Key={"userId": user_id}).get("Item")
    return item.get("pointValues", {}) if item else {}


def _event_response(scoring_event: ScoringEvent, point_values: dict[str, float]) -> dict:
    points: dict[str, float] = {}
    if scoring_event.espn_play is not None:
        espn_play = espn_play_from_dict(scoring_event.espn_play)
        player_categories = {
            player_id: frozenset(categories)
            for player_id, categories in scoring_event.player_categories.items()
        }
        points = points_for_matched_play(
            scoring_event, espn_play, player_categories, scoring_event.player_names, point_values
        )

    return {
        "eventId": scoring_event.event_id,
        "gameId": scoring_event.game_id,
        "team": scoring_event.team,
        "scoringType": scoring_event.scoring_type,
        "description": scoring_event.description,
        "period": scoring_event.period,
        "gameClock": scoring_event.game_clock,
        "homeScore": scoring_event.home_score,
        "awayScore": scoring_event.away_score,
        "playerIds": list(scoring_event.player_ids),
        "points": points,
        "playerNames": scoring_event.player_names,
    }
