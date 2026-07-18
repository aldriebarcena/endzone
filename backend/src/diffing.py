from __future__ import annotations

from models import GameState, ScoringEvent


def new_events(previous: GameState, current: GameState) -> tuple[ScoringEvent, ...]:
    seen = {event.event_id for event in previous.events}
    return tuple(event for event in current.events if event.event_id not in seen)
