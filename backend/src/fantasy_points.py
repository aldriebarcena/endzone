from __future__ import annotations

import re

from adapters.espn import EspnScoringPlay
from models import ScoringEvent

# Verified against real ESPN data (live API calls against real games, not
# guessed): passing/rushing TDs against the original 6-play sample game,
# plus "Field Goal Good" (id 59) confirmed across three other real games
# with statYardage matching the actual kick distance (40/57/25 yards,
# cross-checked against those games' real text descriptions). Safeties,
# defensive/special-teams TDs, and interception/fumble returns (ids 20,
# 36, 39 — also confirmed real) are deliberately NOT mapped: they need
# individual-defender attribution, and this project has zero Tank01 data
# showing what category name (if any) Tank01 gives defensive players —
# no sample game with a defensive score has been observed. Unlike the
# offense/kicking cases, that's not a "haven't gotten to it" gap, it's an
# undesigned scoring model (team-defense vs. individual-defender credit
# isn't even decided) — extending PLAY_TYPE_ROLES to cover it would be
# guessing on two fronts at once, which this project has consistently
# avoided (see DESIGN.md's provider-verification history).
FIELD_GOAL_PLAY_TYPE = "Field Goal Good"

PLAY_TYPE_ROLES: dict[str, tuple[str, ...]] = {
    "Passing Touchdown": ("Passing", "Receiving"),
    "Rushing Touchdown": ("Rushing",),
    FIELD_GOAL_PLAY_TYPE: ("Kicking",),
}

YARDAGE_STAT_BY_ROLE = {"Passing": "pass_yd", "Rushing": "rush_yd", "Receiving": "rec_yd"}
TOUCHDOWN_STAT_BY_ROLE = {"Passing": "pass_td", "Rushing": "rush_td", "Receiving": "rec_td"}
RECEPTION_STAT = "rec"

# Sleeper's real scoring_settings tier field goals by distance rather
# than a flat per-yard rate (confirmed real: fgm_0_19, fgm_20_29,
# fgm_30_39: 3.0 each; fgm_40_49: 4.0; fgm_50p: 5.0) — a fundamentally
# different shape than the yardage*rate model touchdowns use, so field
# goals get their own computation path below rather than reusing
# YARDAGE_STAT_BY_ROLE.
_FIELD_GOAL_TIERS = ((19, "fgm_0_19"), (29, "fgm_20_29"), (39, "fgm_30_39"), (49, "fgm_40_49"))
_FIELD_GOAL_50_PLUS_KEY = "fgm_50p"

# Matches ESPN's standardized NFL-gamebook phrasing: "... to G.Davis for
# 2 yards, TOUCHDOWN." Only verified for the passing-TD case — a play
# with an attached two-point-conversion attempt puts a second
# "Receiving"-category player in the same play's IDs (the conversion
# target), and category-elimination alone can't tell them apart. Not
# extended to rushing TDs: no real sample of a rushing-role collision has
# been observed, so infer_roles() falls back to an unverified guess
# (first candidate) if one ever occurs there.
_TD_RECEIVER_NAME = re.compile(r"to ([\w.'-]+) for \d+ yards,\s*TOUCHDOWN", re.IGNORECASE)


def match_espn_play(
    event: ScoringEvent, espn_plays: tuple[EspnScoringPlay, ...]
) -> EspnScoringPlay | None:
    """Matches by (team, period, clock) — verified as a clean, collision-
    free match key against a real 6-scoring-play game. Not a formal
    guarantee for all games (e.g. two same-team scores in the same
    literal clock second would collide), but that's vanishingly rare.
    """
    period_number = int(event.period.removeprefix("Q")) if event.period.startswith("Q") else None
    return next(
        (
            play
            for play in espn_plays
            if play.team == event.team
            and play.period == period_number
            and play.clock == event.game_clock
        ),
        None,
    )


def _match_name(abbreviated: str, candidates: list[str], player_names: dict[str, str]) -> str | None:
    if "." not in abbreviated:
        return None
    initial, _, last_name = abbreviated.partition(".")
    for player_id in candidates:
        parts = player_names.get(player_id, "").split()
        if len(parts) < 2:
            continue
        first, last = parts[0], parts[-1]
        if last.lower() == last_name.lower() and first[:1].lower() == initial.lower():
            return player_id
    return None


def infer_roles(
    player_ids: tuple[str, ...],
    player_categories: dict[str, frozenset[str]],
    player_names: dict[str, str],
    needed_roles: tuple[str, ...],
    play_text: str,
) -> dict[str, str]:
    """role -> player_id. When exactly one candidate has the needed
    category, use it directly. When multiple do (a TD play with an
    attached two-point-conversion attempt puts both the TD scorer and
    the conversion target in player_ids with the same category), use
    the ESPN play text to pick the actual TD scorer by name. If that
    text match fails too, falls back to the first candidate — an
    unverified guess, not a resolved case.
    """
    assigned: dict[str, str] = {}
    used: set[str] = set()
    for role in needed_roles:
        candidates = [
            player_id
            for player_id in player_ids
            if player_id not in used and role in player_categories.get(player_id, frozenset())
        ]
        if not candidates:
            continue
        if len(candidates) == 1:
            chosen = candidates[0]
        else:
            name_match = _TD_RECEIVER_NAME.search(play_text)
            chosen = (
                _match_name(name_match.group(1), candidates, player_names) if name_match else None
            ) or candidates[0]
        assigned[role] = chosen
        used.add(chosen)
    return assigned


def points_for_matched_play(
    event: ScoringEvent,
    espn_play: EspnScoringPlay,
    player_categories: dict[str, frozenset[str]],
    player_names: dict[str, str],
    point_values: dict[str, float],
) -> dict[str, float]:
    """player_id -> fantasy points earned from this specific scoring
    play, using the league's real point_values (e.g. Sleeper's
    scoring_settings). Returns {} for anything not in PLAY_TYPE_ROLES —
    logged upstream as unhandled rather than guessed at. Split out from
    compute_points() so a caller that's already matched the play (poller
    matches once; push.py reuses that match per-subscriber rather than
    re-matching against the full espn_plays list every time) can skip
    straight to this step.
    """
    if espn_play.play_type not in PLAY_TYPE_ROLES:
        return {}

    roles = PLAY_TYPE_ROLES[espn_play.play_type]
    role_assignments = infer_roles(
        event.player_ids, player_categories, player_names, roles, espn_play.text
    )

    if espn_play.play_type == FIELD_GOAL_PLAY_TYPE:
        return _field_goal_points(role_assignments, espn_play.yardage, point_values)

    is_touchdown = espn_play.play_type.endswith("Touchdown")

    points: dict[str, float] = {}
    for role, player_id in role_assignments.items():
        role_points = 0.0

        yardage_stat = YARDAGE_STAT_BY_ROLE.get(role)
        if yardage_stat:
            role_points += espn_play.yardage * point_values.get(yardage_stat, 0.0)

        if is_touchdown:
            td_stat = TOUCHDOWN_STAT_BY_ROLE.get(role)
            if td_stat:
                role_points += point_values.get(td_stat, 0.0)

        if role == "Receiving":
            role_points += point_values.get(RECEPTION_STAT, 0.0)

        points[player_id] = round(role_points, 2)
    return points


def _field_goal_points(
    role_assignments: dict[str, str], yardage: int, point_values: dict[str, float]
) -> dict[str, float]:
    kicker_id = role_assignments.get("Kicking")
    if kicker_id is None:
        return {}
    key = next((key for max_yards, key in _FIELD_GOAL_TIERS if yardage <= max_yards), _FIELD_GOAL_50_PLUS_KEY)
    return {kicker_id: round(point_values.get(key, 0.0), 2)}


def compute_points(
    event: ScoringEvent,
    espn_plays: tuple[EspnScoringPlay, ...],
    player_categories: dict[str, frozenset[str]],
    player_names: dict[str, str],
    point_values: dict[str, float],
) -> dict[str, float]:
    """Convenience wrapper: match_espn_play() + points_for_matched_play()."""
    espn_play = match_espn_play(event, espn_plays)
    if espn_play is None:
        return {}
    return points_for_matched_play(event, espn_play, player_categories, player_names, point_values)
