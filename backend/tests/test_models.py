from datetime import datetime, timezone

from models import GameState, ScoringEvent


def _event(**overrides) -> ScoringEvent:
    fields = dict(
        event_id="game-1:Q1:8:17:BUF:TD",
        game_id="game-1",
        team="BUF",
        scoring_type="TD",
        description="Dawson Knox 17 Yd pass from Mitchell Trubisky (Matt Prater Kick)",
        period="Q1",
        game_clock="8:17",
        home_score=7,
        away_score=0,
        player_ids=("3039707", "3930086", "11122"),
        fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    fields.update(overrides)
    return ScoringEvent(**fields)


def test_scoring_event_construction():
    event = _event()
    assert event.scoring_type == "TD"
    assert event.player_ids == ("3039707", "3930086", "11122")


def test_game_state_construction():
    event = _event()
    state = GameState(
        game_id="game-1",
        status="In Progress",
        status_code=1,
        home_team="BUF",
        away_team="NYJ",
        home_score=7,
        away_score=0,
        period="Q1",
        clock="8:17",
        events=(event,),
        fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert state.events == (event,)
    assert state.home_score == 7


def test_game_state_can_have_no_events_yet():
    state = GameState(
        game_id="game-1",
        status="scheduled",
        status_code=0,
        home_team="BUF",
        away_team="NYJ",
        home_score=0,
        away_score=0,
        period="pregame",
        clock=None,
        events=(),
        fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert state.events == ()
