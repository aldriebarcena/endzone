from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ScoringEvent:
    """A single scoring play. Fantasy point *values* are league-dependent
    (DESIGN.md's custom point settings) and aren't computed here — that
    happens downstream against a LeagueConfig, using scoring_type.
    player_ids often includes multiple people (e.g. passer + receiver +
    kicker on a passing TD) with no reliable single "the" scorer in the
    raw data; description already names them in order for display.
    """

    event_id: str
    game_id: str
    team: str
    scoring_type: str
    description: str
    period: str
    game_clock: str
    home_score: int
    away_score: int
    player_ids: tuple[str, ...]
    fetched_at: datetime


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
