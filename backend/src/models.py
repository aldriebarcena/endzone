from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ScoringEvent:
    """A single scoring play. Fantasy point *values* are league-dependent
    (league-specific custom point settings) and aren't computed here — that
    happens downstream against a LeagueConfig, using scoring_type.
    player_ids often includes multiple people (e.g. passer + receiver +
    kicker on a passing TD) with no reliable single "the" scorer in the
    raw data; description already names them in order for display.

    espn_play/player_categories/player_names are the raw ingredients
    fantasy_points.points_for_matched_play() needs — populated by
    poller.py when it matches this event against ESPN's enrichment data,
    and persisted (via storage.py) so a later on-demand read (the
    GET /live-game API) can compute personalized points without
    re-fetching ESPN. espn_play is kept as a plain dict here rather than
    adapters.espn.EspnScoringPlay to avoid models.py depending on the
    adapters package — same pattern poller.py already uses for the SQS
    message. None/empty when no ESPN match was found (unhandled play
    type, ESPN fetch failed, or espn_game_id wasn't available).
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
    espn_play: dict | None = None
    player_categories: dict[str, tuple[str, ...]] = field(default_factory=dict)
    player_names: dict[str, str] = field(default_factory=dict)


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
    ("TD"/"FG"/etc, no pass/rush/rec distinction) is still unresolved.
    """

    league_id: str
    name: str
    season: str
    status: str
    total_rosters: int
    roster_positions: tuple[str, ...]
    scoring_settings: dict[str, float]
