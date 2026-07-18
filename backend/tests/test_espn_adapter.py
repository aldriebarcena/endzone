import json
from pathlib import Path

from adapters.espn import parse_scoring_plays

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "espn_summary.json").read_text())


def test_parses_all_scoring_plays():
    plays = parse_scoring_plays(FIXTURE)
    assert len(plays) == 6


def test_parses_real_structured_yardage_and_type():
    plays = parse_scoring_plays(FIXTURE)
    first = plays[0]
    assert first.play_type == "Passing Touchdown"
    assert first.yardage == 17
    assert first.team == "BUF"
    assert first.period == 1
    assert first.clock == "8:17"


def test_distinguishes_passing_and_rushing_touchdowns():
    plays = parse_scoring_plays(FIXTURE)
    play_types = {play.play_type for play in plays}
    assert "Passing Touchdown" in play_types
    assert "Rushing Touchdown" in play_types
