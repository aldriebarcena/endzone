import json
from pathlib import Path

import storage
from adapters.tank01 import parse_box_score

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "tank01_box_score_final.json").read_text()
)["body"]


def test_round_trip_preserves_game_state():
    state = parse_box_score(FIXTURE)
    item = storage.to_item(state)
    restored = storage.from_item(item)
    assert restored == state


def test_item_has_ttl_24h_after_fetch():
    state = parse_box_score(FIXTURE)
    item = storage.to_item(state)
    assert item["expiresAt"] == int(state.fetched_at.timestamp()) + 24 * 3600


def test_from_item_handles_missing_clock():
    state = parse_box_score(FIXTURE)
    item = storage.to_item(state)
    item["clock"] = None
    restored = storage.from_item(item)
    assert restored.clock is None
