from __future__ import annotations

import json
import logging
import os

import boto3

import storage
from adapters.espn import EspnScoringPlay, fetch_scoring_plays
from adapters.tank01 import (
    extract_player_categories,
    extract_player_names,
    fetch_box_score_raw,
    parse_box_score,
)
from diffing import new_events
from fantasy_points import match_espn_play
from models import ScoringEvent

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Tank01's documented numeric enum, confirmed against a real box score
# (gameStatusCode "2" for a game with gameStatus "Completed") — see
# GameState.status_code's docstring for why this replaced text matching
# on `status` (which isn't consistent across Tank01's own endpoints).
FINAL_STATUS_CODE = 2


def handler(event, context):
    game_id = event["game_id"]
    espn_game_id = event.get("espn_game_id")
    table = _table()

    previous_item = table.get_item(Key={"gameId": game_id}).get("Item")
    previous = storage.from_item(previous_item) if previous_item else None

    box_score = fetch_box_score_raw(game_id)
    current = parse_box_score(box_score)

    # First poll of a game seeds state without emitting events — otherwise
    # every scoring play that already happened before we started tracking
    # would fire as a "new" notification.
    events = () if previous is None else new_events(previous, current)

    if events:
        espn_plays = _fetch_espn_plays_safely(espn_game_id) if espn_game_id else ()
        player_categories = extract_player_categories(box_score) if espn_plays else {}
        player_names = extract_player_names(box_score) if espn_plays else {}
        for scoring_event in events:
            logger.info("new scoring event: %s", scoring_event.description)
            _publish(scoring_event, espn_plays, player_categories, player_names)

    table.put_item(Item=storage.to_item(current))

    is_final = current.status_code == FINAL_STATUS_CODE
    return {
        "game_id": game_id,
        "espn_game_id": espn_game_id,
        "is_final": is_final,
        "new_event_count": len(events),
    }


def _table():
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(os.environ["LIVE_GAME_STATE_TABLE"])


def _fetch_espn_plays_safely(espn_game_id: str) -> tuple[EspnScoringPlay, ...]:
    # ESPN is unofficial/unsupported — a fetch failure here shouldn't
    # break the core scoring pipeline, which only depends on Tank01.
    # Losing the fantasy-point enrichment for this event is an acceptable
    # degradation; losing the notification entirely isn't.
    try:
        return fetch_scoring_plays(espn_game_id)
    except Exception:
        logger.exception(
            "ESPN enrichment fetch failed for %s; publishing without it", espn_game_id
        )
        return ()


def _publish(
    scoring_event: ScoringEvent,
    espn_plays: tuple[EspnScoringPlay, ...],
    player_categories: dict[str, frozenset[str]],
    player_names: dict[str, str],
) -> None:
    # Point *values* are league-dependent (each push subscriber can have
    # different LeagueConfig.pointValues), so the actual computation
    # happens in push.py, per subscriber — this only packages the raw
    # ingredients fantasy_points.points_for_matched_play() needs, scoped
    # to just the players on this play (not the whole game's roster).
    espn_play = match_espn_play(scoring_event, espn_plays) if espn_plays else None
    relevant_categories: dict[str, list[str]] = {}
    relevant_names: dict[str, str] = {}
    if espn_play is not None:
        for player_id in scoring_event.player_ids:
            if player_id in player_categories:
                relevant_categories[player_id] = sorted(player_categories[player_id])
            if player_id in player_names:
                relevant_names[player_id] = player_names[player_id]

    sqs = boto3.client("sqs")
    sqs.send_message(
        QueueUrl=os.environ["SCORING_EVENTS_QUEUE_URL"],
        MessageBody=json.dumps(
            {
                "event_id": scoring_event.event_id,
                "game_id": scoring_event.game_id,
                "team": scoring_event.team,
                "scoring_type": scoring_event.scoring_type,
                "description": scoring_event.description,
                "period": scoring_event.period,
                "game_clock": scoring_event.game_clock,
                "home_score": scoring_event.home_score,
                "away_score": scoring_event.away_score,
                "player_ids": list(scoring_event.player_ids),
                "espn_play": _espn_play_to_dict(espn_play) if espn_play else None,
                "player_categories": relevant_categories,
                "player_names": relevant_names,
            }
        ),
    )


def _espn_play_to_dict(espn_play: EspnScoringPlay) -> dict:
    return {
        "play_type": espn_play.play_type,
        "text": espn_play.text,
        "yardage": espn_play.yardage,
        "team": espn_play.team,
        "period": espn_play.period,
        "clock": espn_play.clock,
    }
