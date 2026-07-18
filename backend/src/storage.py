from __future__ import annotations

from datetime import datetime, timedelta

from models import GameState, ScoringEvent

TTL_HOURS = 24


def to_item(state: GameState) -> dict:
    expires_at = int((state.fetched_at + timedelta(hours=TTL_HOURS)).timestamp())
    return {
        "gameId": state.game_id,
        "status": state.status,
        "statusCode": state.status_code,
        "homeTeam": state.home_team,
        "awayTeam": state.away_team,
        "homeScore": state.home_score,
        "awayScore": state.away_score,
        "period": state.period,
        "clock": state.clock,
        "events": [_event_to_item(event) for event in state.events],
        "fetchedAt": state.fetched_at.isoformat(),
        "expiresAt": expires_at,
    }


def from_item(item: dict) -> GameState:
    return GameState(
        game_id=item["gameId"],
        status=item["status"],
        status_code=int(item["statusCode"]),
        home_team=item["homeTeam"],
        away_team=item["awayTeam"],
        home_score=int(item["homeScore"]),
        away_score=int(item["awayScore"]),
        period=item["period"],
        clock=item.get("clock"),
        events=tuple(_event_from_item(e) for e in item.get("events", [])),
        fetched_at=datetime.fromisoformat(item["fetchedAt"]),
    )


def _event_to_item(event: ScoringEvent) -> dict:
    return {
        "eventId": event.event_id,
        "gameId": event.game_id,
        "team": event.team,
        "scoringType": event.scoring_type,
        "description": event.description,
        "period": event.period,
        "gameClock": event.game_clock,
        "homeScore": event.home_score,
        "awayScore": event.away_score,
        "playerIds": list(event.player_ids),
        "fetchedAt": event.fetched_at.isoformat(),
    }


def _event_from_item(item: dict) -> ScoringEvent:
    return ScoringEvent(
        event_id=item["eventId"],
        game_id=item["gameId"],
        team=item["team"],
        scoring_type=item["scoringType"],
        description=item["description"],
        period=item["period"],
        game_clock=item["gameClock"],
        home_score=int(item["homeScore"]),
        away_score=int(item["awayScore"]),
        player_ids=tuple(item.get("playerIds", ())),
        fetched_at=datetime.fromisoformat(item["fetchedAt"]),
    )
