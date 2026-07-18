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
    # Tank01's documented numeric enum (0 not started, 1 in progress,
    # 2 final, 3 postponed, 4 suspended) — same meaning across every
    # Tank01 endpoint per their docs, unlike `status` (free text: seen
    # both "Completed" from getNFLBoxScore and "Final" from
    # getNFLGamesForDate for the same finished game). Use this field for
    # any "is the game over" logic, not `status`.
    status_code: int
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    period: str
    clock: str | None
    events: tuple[ScoringEvent, ...]
    fetched_at: datetime


@dataclass(frozen=True)
class SleeperLeague:
    """scoring_settings is Sleeper's real per-stat point values for this
    league (e.g. pass_td, rush_td, rec, fum_lost — dozens of keys) — used
    as-is to seed LeagueConfig's custom point values on import. Mapping
    these granular keys against Tank01's coarse ScoringEvent.scoring_type
    ("TD"/"FG"/etc, no pass/rush/rec distinction) is still unresolved —
    see PROJECT_PLAN.md open questions.
    """

    league_id: str
    name: str
    season: str
    status: str
    total_rosters: int
    roster_positions: tuple[str, ...]
    scoring_settings: dict[str, float]
