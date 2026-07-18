from __future__ import annotations

import json
import logging
import os
from dataclasses import replace

import boto3

import storage
from adapters.espn import EspnScoringPlay, fetch_scoring_plays, to_dict as espn_play_to_dict
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
    previous_by_id = {e.event_id: e for e in (previous.events if previous else ())}

    box_score = fetch_box_score_raw(game_id)
    current = parse_box_score(box_score)

    # First poll of a game seeds state without treating anything as
    # "new" — otherwise every scoring play that already happened before
    # we started tracking would fire as a fresh notification.
    new_ids = set() if previous is None else {e.event_id for e in new_events(previous, current)}

    # ESPN is fetched once per poll (not per event) and only when there's
    # something new to enrich — already-known events carry their
    # enrichment forward from the previous poll instead of re-fetching.
    if new_ids and espn_game_id:
        espn_plays = _fetch_espn_plays_safely(espn_game_id)
        player_categories = extract_player_categories(box_score)
        player_names = extract_player_names(box_score)
    else:
        espn_plays, player_categories, player_names = (), {}, {}

    enriched_events = tuple(
        _resolve_event(e, new_ids, previous_by_id, espn_plays, player_categories, player_names)
        for e in current.events
    )
    current = replace(current, events=enriched_events)

    new_scoring_events = tuple(e for e in enriched_events if e.event_id in new_ids)
    for scoring_event in new_scoring_events:
        logger.info("new scoring event: %s", scoring_event.description)
        _publish(scoring_event)

    # Stored with enrichment attached to every event (not just this
    # poll's new ones) so a later on-demand read (GET /live-game) can
    # compute personalized points for the whole game, not only whatever
    # was newest when someone happened to open the app.
    table.put_item(Item=storage.to_item(current))

    is_final = current.status_code == FINAL_STATUS_CODE
    return {
        "game_id": game_id,
        "espn_game_id": espn_game_id,
        "is_final": is_final,
        "new_event_count": len(new_scoring_events),
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


def _resolve_event(
    scoring_event: ScoringEvent,
    new_ids: set[str],
    previous_by_id: dict[str, ScoringEvent],
    espn_plays: tuple[EspnScoringPlay, ...],
    player_categories: dict[str, frozenset[str]],
    player_names: dict[str, str],
) -> ScoringEvent:
    if scoring_event.event_id in new_ids:
        return _enrich(scoring_event, espn_plays, player_categories, player_names)

    prior = previous_by_id.get(scoring_event.event_id)
    if prior is not None and prior.espn_play is not None:
        return replace(
            scoring_event,
            espn_play=prior.espn_play,
            player_categories=prior.player_categories,
            player_names=prior.player_names,
        )
    return scoring_event


def _enrich(
    scoring_event: ScoringEvent,
    espn_plays: tuple[EspnScoringPlay, ...],
    player_categories: dict[str, frozenset[str]],
    player_names: dict[str, str],
) -> ScoringEvent:
    # Point *values* are league-dependent (each push subscriber, and each
    # GET /live-game caller, can have different LeagueConfig.pointValues),
    # so the actual point computation happens downstream, per requester —
    # this only attaches the raw ingredients points_for_matched_play()
    # needs, scoped to just the players on this play.
    espn_play = match_espn_play(scoring_event, espn_plays) if espn_plays else None
    if espn_play is None:
        return scoring_event

    relevant_categories = {
        player_id: tuple(sorted(player_categories[player_id]))
        for player_id in scoring_event.player_ids
        if player_id in player_categories
    }
    relevant_names = {
        player_id: player_names[player_id]
        for player_id in scoring_event.player_ids
        if player_id in player_names
    }
    return replace(
        scoring_event,
        espn_play=espn_play_to_dict(espn_play),
        player_categories=relevant_categories,
        player_names=relevant_names,
    )


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
                "espn_play": scoring_event.espn_play,
                "player_categories": {
                    pid: list(cats) for pid, cats in scoring_event.player_categories.items()
                },
                "player_names": scoring_event.player_names,
            }
        ),
    )
