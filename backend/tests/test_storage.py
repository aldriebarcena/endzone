import json
from dataclasses import replace
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


def test_round_trip_preserves_enrichment_data():
    # Regression coverage for the GET /live-game feature: enrichment
    # attached by poller.py must survive a DynamoDB round-trip, or a
    # later on-demand read can't compute fantasy points at all.
    state = parse_box_score(FIXTURE)
    enriched_first_event = replace(
        state.events[0],
        espn_play={
            "play_type": "Passing Touchdown",
            "text": "M.Trubisky pass deep right to D.Knox for 17 yards, TOUCHDOWN.",
            "yardage": 17,
            "team": "BUF",
            "period": 1,
            "clock": "8:17",
        },
        player_categories={"3039707": ("Passing",), "3930086": ("Receiving",)},
        player_names={"3039707": "Mitchell Trubisky", "3930086": "Dawson Knox"},
    )
    state = replace(state, events=(enriched_first_event, *state.events[1:]))

    item = storage.to_item(state)
    restored = storage.from_item(item)

    assert restored == state
    assert restored.events[0].espn_play["yardage"] == 17
    assert restored.events[0].player_categories["3930086"] == ("Receiving",)


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
