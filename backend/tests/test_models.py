from datetime import datetime, timezone

from src.models import GameState, ScoringEvent


def _event(**overrides) -> ScoringEvent:
    fields = dict(
        event_id="evt-1",
        game_id="game-1",
        player_id="player-1",
        player_name="Test Player",
        team="KC",
        event_type="passing_td",
        description="Test Player threw a TD",
        fantasy_points=6.0,
        occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    fields.update(overrides)
    return ScoringEvent(**fields)


def test_scoring_event_construction():
    event = _event()
    assert event.fantasy_points == 6.0
    assert event.event_type == "passing_td"


def test_game_state_construction():
    event = _event()
    state = GameState(
        game_id="game-1",
        status="live",
        home_team="KC",
        away_team="BUF",
        home_score=7,
        away_score=0,
        period="Q1",
        clock="10:32",
        events=(event,),
        fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert state.events == (event,)
    assert state.home_score == 7


def test_game_state_can_have_no_events_yet():
    state = GameState(
        game_id="game-1",
        status="scheduled",
        home_team="KC",
        away_team="BUF",
        home_score=0,
        away_score=0,
        period="pregame",
        clock=None,
        events=(),
        fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert state.events == ()
