from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ScoringEvent:
    event_id: str
    game_id: str
    player_id: str
    player_name: str
    team: str
    event_type: str
    description: str
    fantasy_points: float
    occurred_at: datetime


@dataclass(frozen=True)
class GameState:
    game_id: str
    status: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    period: str
    clock: str | None
    events: tuple[ScoringEvent, ...]
    fetched_at: datetime
