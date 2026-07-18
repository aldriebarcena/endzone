from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

import boto3

from adapters.espn import from_dict as espn_play_from_dict
from apns import build_auth_token, send_push
from fantasy_points import points_for_matched_play
from models import ScoringEvent

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    subscribers = _subscribers()

    if not subscribers:
        logger.info("no subscribers with a registered device token, nothing to push")
        return {"batchItemFailures": []}

    auth_token = build_auth_token(
        team_id=os.environ["APNS_TEAM_ID"],
        key_id=os.environ["APNS_KEY_ID"],
        private_key=os.environ["APNS_PRIVATE_KEY"],
    )

    failures = []
    for record in event.get("Records", []):
        try:
            _process_record(record, subscribers, auth_token)
        except Exception:
            logger.exception("failed to process record %s", record.get("messageId"))
            failures.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": failures}


def _process_record(record: dict, subscribers: list[dict], auth_token: str) -> None:
    message = json.loads(record["body"])
    scoring_event = _event_from_message(message)
    espn_play_data = message.get("espn_play")
    espn_play = espn_play_from_dict(espn_play_data) if espn_play_data else None
    player_categories = {
        player_id: frozenset(categories)
        for player_id, categories in message.get("player_categories", {}).items()
    }
    player_names = message.get("player_names", {})
    title = f"{scoring_event.team} — {scoring_event.scoring_type}"

    for subscriber in subscribers:
        # Personalized per subscriber, not computed once upstream in
        # poller.py — different subscribers can have different leagues
        # with different pointValues, so the same play is worth different
        # amounts to different people. See PROJECT_PLAN.md open questions.
        points: dict[str, float] = {}
        if espn_play is not None:
            points = points_for_matched_play(
                scoring_event, espn_play, player_categories, player_names,
                subscriber.get("pointValues", {}),
            )
        body = _format_body(scoring_event, points, player_names)

        response = send_push(
            subscriber["deviceToken"],
            title=title,
            body=body,
            bundle_id=os.environ["APNS_BUNDLE_ID"],
            auth_token=auth_token,
            sandbox=os.environ.get("APNS_SANDBOX", "true").lower() == "true",
        )
        if response.status_code != 200:
            logger.warning(
                "APNs push failed for %s: %s %s",
                subscriber["deviceToken"],
                response.status_code,
                response.text,
            )


def _format_body(scoring_event: ScoringEvent, points: dict[str, float], player_names: dict[str, str]) -> str:
    if not points:
        return scoring_event.description
    breakdown = ", ".join(
        f"{player_names.get(player_id, player_id)} +{value:g} pts"
        for player_id, value in points.items()
    )
    return f"{scoring_event.description} ({breakdown})"


def _event_from_message(message: dict) -> ScoringEvent:
    # fetched_at isn't semantically meaningful on a reconstructed event
    # (the real fetch happened in poller.py) — fantasy_points.py doesn't
    # read it, it's only here to satisfy the dataclass.
    return ScoringEvent(
        event_id=message["event_id"],
        game_id=message["game_id"],
        team=message["team"],
        scoring_type=message["scoring_type"],
        description=message["description"],
        period=message["period"],
        game_clock=message["game_clock"],
        home_score=message["home_score"],
        away_score=message["away_score"],
        player_ids=tuple(message.get("player_ids", ())),
        fetched_at=datetime.now(timezone.utc),
    )


def _subscribers() -> list[dict]:
    # Scan is fine at portfolio scale (single-digit to low-dozens of
    # users); would need a GSI on deviceToken, or a dedicated table, if
    # this ever needed to scale further.
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(os.environ["LEAGUE_CONFIG_TABLE"])
    response = table.scan()
    return [
        {"deviceToken": item["deviceToken"], "pointValues": item.get("pointValues", {})}
        for item in response.get("Items", [])
        if item.get("deviceToken")
    ]
