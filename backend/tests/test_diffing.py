import json
from pathlib import Path

from src.adapters.tank01 import parse_box_score
from src.diffing import new_events

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "tank01_box_score_final.json").read_text()
)["body"]


def _box_score_through_play(count: int) -> dict:
    return {**FIXTURE, "scoringPlays": FIXTURE["scoringPlays"][:count]}


def test_new_events_detects_plays_added_between_polls():
    earlier_poll = parse_box_score(_box_score_through_play(3))
    later_poll = parse_box_score(_box_score_through_play(6))

    detected = new_events(earlier_poll, later_poll)

    assert len(detected) == 3
    assert [event.description for event in detected] == [
        play["score"] for play in FIXTURE["scoringPlays"][3:6]
    ]


def test_new_events_is_empty_when_nothing_changed():
    poll = parse_box_score(_box_score_through_play(3))
    assert new_events(poll, poll) == ()
