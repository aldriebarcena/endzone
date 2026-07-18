from __future__ import annotations

import re

from adapters.espn import EspnScoringPlay
from models import ScoringEvent

# Only verified against real data: passing and rushing touchdowns (see
# PROJECT_PLAN.md). Field goals, safeties, defensive/special-teams TDs,
# and two-point conversions themselves are real ESPN play types this
# project hasn't observed samples of yet — extending this mapping
# without real data would be guessing, which this project has
# specifically tried to avoid throughout (see DESIGN.md's provider-
# verification history).
PLAY_TYPE_ROLES: dict[str, tuple[str, ...]] = {
    "Passing Touchdown": ("Passing", "Receiving"),
    "Rushing Touchdown": ("Rushing",),
}

YARDAGE_STAT_BY_ROLE = {"Passing": "pass_yd", "Rushing": "rush_yd", "Receiving": "rec_yd"}
TOUCHDOWN_STAT_BY_ROLE = {"Passing": "pass_td", "Rushing": "rush_td", "Receiving": "rec_td"}
RECEPTION_STAT = "rec"

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


def compute_points(
    event: ScoringEvent,
    espn_plays: tuple[EspnScoringPlay, ...],
    player_categories: dict[str, frozenset[str]],
    player_names: dict[str, str],
    point_values: dict[str, float],
) -> dict[str, float]:
    """player_id -> fantasy points earned from this specific scoring
    play, using the league's real point_values (e.g. Sleeper's
    scoring_settings). Returns {} for anything not in PLAY_TYPE_ROLES —
    logged upstream as unhandled rather than guessed at.
    """
    espn_play = match_espn_play(event, espn_plays)
    if espn_play is None or espn_play.play_type not in PLAY_TYPE_ROLES:
        return {}

    roles = PLAY_TYPE_ROLES[espn_play.play_type]
    role_assignments = infer_roles(
        event.player_ids, player_categories, player_names, roles, espn_play.text
    )
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
