from __future__ import annotations

import json
import logging
import os

import boto3

import storage
from adapters.tank01 import fetch_game_state
from diffing import new_events
from models import ScoringEvent

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Confirmed against one real (completed) game via getNFLBoxScore: "Completed".
# Values for in-progress/scheduled/postponed states are unverified — Tank01's
# games-list endpoint uses "Final" for the same finished game, so box-score
# status strings aren't guaranteed to match. Revisit once this has run against
# a live game.
FINAL_STATUSES = {"completed", "final"}


def handler(event, context):
    game_id = event["game_id"]
    table = _table()

    previous_item = table.get_item(Key={"gameId": game_id}).get("Item")
    previous = storage.from_item(previous_item) if previous_item else None

    current = fetch_game_state(game_id)

    # First poll of a game seeds state without emitting events — otherwise
    # every scoring play that already happened before we started tracking
    # would fire as a "new" notification.
    events = () if previous is None else new_events(previous, current)

    for scoring_event in events:
        logger.info("new scoring event: %s", scoring_event.description)
        _publish(scoring_event)

    table.put_item(Item=storage.to_item(current))

    is_final = current.status.strip().lower() in FINAL_STATUSES
    return {"game_id": game_id, "is_final": is_final, "new_event_count": len(events)}


def _table():
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(os.environ["LIVE_GAME_STATE_TABLE"])


def _publish(scoring_event: ScoringEvent) -> None:
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
            }
        ),
    )
