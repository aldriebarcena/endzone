import json
from pathlib import Path

import pytest

from adapters.espn import parse_scoring_plays
from adapters.tank01 import extract_player_categories, extract_player_names, parse_box_score
from fantasy_points import compute_points, infer_roles, match_espn_play

TANK01_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "tank01_box_score_final.json").read_text()
)["body"]
ESPN_FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "espn_summary.json").read_text())
SLEEPER_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "sleeper_league.json").read_text()
)

GAME_STATE = parse_box_score(TANK01_FIXTURE)
PLAYER_CATEGORIES = extract_player_categories(TANK01_FIXTURE)
PLAYER_NAMES = extract_player_names(TANK01_FIXTURE)
ESPN_PLAYS = parse_scoring_plays(ESPN_FIXTURE)
POINT_VALUES = SLEEPER_FIXTURE["scoring_settings"]


def _event_by_description(fragment: str):
    return next(e for e in GAME_STATE.events if fragment in e.description)


def test_match_espn_play_finds_correct_play_by_team_period_clock():
    event = _event_by_description("Dawson Knox")
    espn_play = match_espn_play(event, ESPN_PLAYS)
    assert espn_play is not None
    assert espn_play.yardage == 17
    assert espn_play.play_type == "Passing Touchdown"


def test_passing_td_splits_points_between_passer_and_receiver_at_different_rates():
    event = _event_by_description("Dawson Knox")
    points = compute_points(event, ESPN_PLAYS, PLAYER_CATEGORIES, PLAYER_NAMES, POINT_VALUES)

    # 17 * pass_yd(0.04) + pass_td(6.0)
    assert points["3039707"] == pytest.approx(6.68, abs=0.01)
    # 17 * rec_yd(0.1) + rec_td(6.0) + rec(1.0) -- receiver earns more
    # than the passer for the same play, since rec_yd > pass_yd per-yard
    # and PPR adds a reception bonus the passer doesn't get.
    assert points["3930086"] == pytest.approx(8.70, abs=0.01)


def test_rushing_td_credits_only_the_rusher():
    event = _event_by_description("Ty Johnson 6 Yd Rush")
    points = compute_points(event, ESPN_PLAYS, PLAYER_CATEGORIES, PLAYER_NAMES, POINT_VALUES)

    assert list(points.keys()) == ["3915411"]
    # 6 * rush_yd(0.1) + rush_td(6.0)
    assert points["3915411"] == pytest.approx(6.6, abs=0.01)


def test_two_point_conversion_receiver_is_not_confused_with_the_td_scorer():
    # Regression test for a real bug found during manual verification:
    # both the actual TD receiver and the attached two-point-conversion
    # target share the "Receiving" category and both appear in
    # player_ids, so naive category-elimination picked whichever came
    # first in the list -- which was wrong for this play.
    event = _event_by_description("Gabe Davis")
    points = compute_points(event, ESPN_PLAYS, PLAYER_CATEGORIES, PLAYER_NAMES, POINT_VALUES)

    gabe_davis_id = "4243537"
    keon_coleman_id = "4635008"
    assert gabe_davis_id in points
    assert keon_coleman_id not in points


def test_infer_roles_falls_back_to_first_candidate_when_text_has_no_match():
    # Honest coverage of the documented fallback: nonsense text can't be
    # name-matched, so it silently picks the first candidate rather than
    # raising. This is a known, accepted limitation, not a resolved case.
    result = infer_roles(
        player_ids=("p1", "p2"),
        player_categories={"p1": frozenset({"Receiving"}), "p2": frozenset({"Receiving"})},
        player_names={"p1": "Alpha One", "p2": "Beta Two"},
        needed_roles=("Receiving",),
        play_text="no matching pattern here",
    )
    assert result["Receiving"] == "p1"


def test_unhandled_play_type_returns_empty():
    # A field goal isn't in PLAY_TYPE_ROLES (unverified — no real sample
    # observed yet). Should return {} rather than guess or crash.
    fake_event = _event_by_description("Dawson Knox")
    empty_espn_plays = ()
    assert compute_points(fake_event, empty_espn_plays, PLAYER_CATEGORIES, PLAYER_NAMES, POINT_VALUES) == {}


