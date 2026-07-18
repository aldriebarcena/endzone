import json
from pathlib import Path

from src.adapters.tank01 import parse_box_score

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "tank01_box_score_final.json").read_text()
)["body"]


def test_parses_game_level_fields():
    state = parse_box_score(FIXTURE)
    assert state.game_id == "20260104_NYJ@BUF"
    assert state.home_team == "BUF"
    assert state.away_team == "NYJ"
    assert state.home_score == 35
    assert state.away_score == 8
    assert state.status == "Completed"


def test_parses_scoring_plays_as_events():
    state = parse_box_score(FIXTURE)
    assert len(state.events) == 6
    first = state.events[0]
    assert first.scoring_type == "TD"
    assert first.team == "BUF"
    assert first.period == "Q1"
    assert "Dawson Knox" in first.description
    assert "3930086" in first.player_ids


def test_event_ids_are_unique():
    state = parse_box_score(FIXTURE)
    event_ids = [event.event_id for event in state.events]
    assert len(event_ids) == len(set(event_ids))
