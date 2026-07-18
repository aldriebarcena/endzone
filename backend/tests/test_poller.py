import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

import storage
from adapters.tank01 import parse_box_score
from poller.app import handler

TANK01_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "tank01_box_score_final.json").read_text()
)["body"]
ESPN_FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "espn_summary.json").read_text())


@patch("poller.app.boto3.resource")
@patch("poller.app.fetch_box_score_raw")
def test_first_poll_seeds_state_without_emitting_events(mock_fetch, mock_resource, monkeypatch):
    monkeypatch.setenv("LIVE_GAME_STATE_TABLE", "endzone-live-game-state")
    mock_fetch.return_value = TANK01_FIXTURE

    mock_table = MagicMock()
    mock_table.get_item.return_value = {}
    mock_resource.return_value.Table.return_value = mock_table

    result = handler({"game_id": TANK01_FIXTURE["gameID"]}, None)

    assert result["new_event_count"] == 0
    assert result["is_final"] is True
    mock_table.put_item.assert_called_once()
    put_item = mock_table.put_item.call_args.kwargs["Item"]
    assert put_item["gameId"] == TANK01_FIXTURE["gameID"]
    assert put_item["statusCode"] == 2


@patch("poller.app.fetch_scoring_plays")
@patch("poller.app.boto3.client")
@patch("poller.app.boto3.resource")
@patch("poller.app.fetch_box_score_raw")
def test_second_poll_publishes_new_events_with_espn_enrichment(
    mock_fetch, mock_resource, mock_client, mock_fetch_espn, monkeypatch
):
    monkeypatch.setenv("LIVE_GAME_STATE_TABLE", "endzone-live-game-state")
    monkeypatch.setenv(
        "SCORING_EVENTS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123/endzone-scoring-events"
    )
    earlier = parse_box_score({**TANK01_FIXTURE, "scoringPlays": TANK01_FIXTURE["scoringPlays"][:3]})
    mock_fetch.return_value = TANK01_FIXTURE
    mock_fetch_espn.return_value = _parse_espn_fixture()

    mock_table = MagicMock()
    mock_table.get_item.return_value = {"Item": storage.to_item(earlier)}
    mock_resource.return_value.Table.return_value = mock_table
    mock_sqs = MagicMock()
    mock_client.return_value = mock_sqs

    result = handler({"game_id": TANK01_FIXTURE["gameID"], "espn_game_id": "401772967"}, None)

    assert result["new_event_count"] == 3
    assert result["is_final"] is True
    mock_fetch_espn.assert_called_once_with("401772967")
    assert mock_sqs.send_message.call_count == 3

    first_message = json.loads(mock_sqs.send_message.call_args_list[0].kwargs["MessageBody"])
    assert first_message["description"] == TANK01_FIXTURE["scoringPlays"][3]["score"]
    assert first_message["espn_play"]["play_type"] in {"Passing Touchdown", "Rushing Touchdown"}
    assert first_message["player_categories"]
    assert first_message["player_names"]

    # Regression coverage for GET /live-game: enrichment must be attached
    # to the *stored* game state, not just the SQS message -- otherwise a
    # later on-demand read has nothing to compute points from.
    stored_item = mock_table.put_item.call_args.kwargs["Item"]
    stored_state = storage.from_item(stored_item)
    new_stored_events = [e for e in stored_state.events if e.espn_play is not None]
    assert len(new_stored_events) == 3


@patch("poller.app.fetch_scoring_plays")
@patch("poller.app.boto3.client")
@patch("poller.app.boto3.resource")
@patch("poller.app.fetch_box_score_raw")
def test_third_poll_carries_forward_enrichment_without_refetching_espn(
    mock_fetch, mock_resource, mock_client, mock_fetch_espn, monkeypatch
):
    monkeypatch.setenv("LIVE_GAME_STATE_TABLE", "endzone-live-game-state")
    monkeypatch.setenv(
        "SCORING_EVENTS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123/endzone-scoring-events"
    )
    espn_plays = _parse_espn_fixture()

    # Simulate state as poller itself would have stored it after poll 2:
    # first 3 plays already enriched, plays 4-6 not yet seen.
    previous = parse_box_score({**TANK01_FIXTURE, "scoringPlays": TANK01_FIXTURE["scoringPlays"][:3]})
    from adapters.espn import to_dict as espn_play_to_dict
    from fantasy_points import match_espn_play

    enriched_events = tuple(
        replace(e, espn_play=espn_play_to_dict(match_espn_play(e, espn_plays)))
        for e in previous.events
    )
    previous = replace(previous, events=enriched_events)

    mock_fetch.return_value = TANK01_FIXTURE  # now has all 6 plays
    mock_fetch_espn.return_value = espn_plays
    mock_table = MagicMock()
    mock_table.get_item.return_value = {"Item": storage.to_item(previous)}
    mock_resource.return_value.Table.return_value = mock_table
    mock_sqs = MagicMock()
    mock_client.return_value = mock_sqs

    result = handler({"game_id": TANK01_FIXTURE["gameID"], "espn_game_id": "401772967"}, None)

    assert result["new_event_count"] == 3
    # ESPN is only fetched for the genuinely new plays this poll -- the
    # first 3 (already enriched in a prior poll) don't trigger a re-fetch.
    mock_fetch_espn.assert_called_once_with("401772967")

    stored_state = storage.from_item(mock_table.put_item.call_args.kwargs["Item"])
    assert all(e.espn_play is not None for e in stored_state.events)


@patch("poller.app.boto3.client")
@patch("poller.app.boto3.resource")
@patch("poller.app.fetch_box_score_raw")
def test_no_espn_game_id_publishes_without_enrichment(mock_fetch, mock_resource, mock_client, monkeypatch):
    monkeypatch.setenv("LIVE_GAME_STATE_TABLE", "endzone-live-game-state")
    monkeypatch.setenv(
        "SCORING_EVENTS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123/endzone-scoring-events"
    )
    earlier = parse_box_score({**TANK01_FIXTURE, "scoringPlays": TANK01_FIXTURE["scoringPlays"][:5]})
    mock_fetch.return_value = TANK01_FIXTURE

    mock_table = MagicMock()
    mock_table.get_item.return_value = {"Item": storage.to_item(earlier)}
    mock_resource.return_value.Table.return_value = mock_table
    mock_sqs = MagicMock()
    mock_client.return_value = mock_sqs

    result = handler({"game_id": TANK01_FIXTURE["gameID"]}, None)

    assert result["new_event_count"] == 1
    message = json.loads(mock_sqs.send_message.call_args.kwargs["MessageBody"])
    assert message["espn_play"] is None
    assert message["player_categories"] == {}


@patch("poller.app.fetch_scoring_plays")
@patch("poller.app.boto3.client")
@patch("poller.app.boto3.resource")
@patch("poller.app.fetch_box_score_raw")
def test_espn_fetch_failure_does_not_break_publishing(
    mock_fetch, mock_resource, mock_client, mock_fetch_espn, monkeypatch
):
    # ESPN is unofficial/unsupported -- a fetch failure here must not
    # break the core scoring pipeline, which only depends on Tank01.
    monkeypatch.setenv("LIVE_GAME_STATE_TABLE", "endzone-live-game-state")
    monkeypatch.setenv(
        "SCORING_EVENTS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123/endzone-scoring-events"
    )
    earlier = parse_box_score({**TANK01_FIXTURE, "scoringPlays": TANK01_FIXTURE["scoringPlays"][:5]})
    mock_fetch.return_value = TANK01_FIXTURE
    mock_fetch_espn.side_effect = Exception("ESPN is down")

    mock_table = MagicMock()
    mock_table.get_item.return_value = {"Item": storage.to_item(earlier)}
    mock_resource.return_value.Table.return_value = mock_table
    mock_sqs = MagicMock()
    mock_client.return_value = mock_sqs

    result = handler({"game_id": TANK01_FIXTURE["gameID"], "espn_game_id": "401772967"}, None)

    assert result["new_event_count"] == 1
    message = json.loads(mock_sqs.send_message.call_args.kwargs["MessageBody"])
    assert message["espn_play"] is None


@patch("poller.app.boto3.resource")
@patch("poller.app.fetch_box_score_raw")
def test_in_progress_game_is_not_final(mock_fetch, mock_resource, monkeypatch):
    monkeypatch.setenv("LIVE_GAME_STATE_TABLE", "endzone-live-game-state")
    mock_fetch.return_value = {**TANK01_FIXTURE, "gameStatus": "In Progress", "gameStatusCode": "1"}

    mock_table = MagicMock()
    mock_table.get_item.return_value = {}
    mock_resource.return_value.Table.return_value = mock_table

    result = handler({"game_id": TANK01_FIXTURE["gameID"]}, None)

    assert result["is_final"] is False


def _parse_espn_fixture():
    from adapters.espn import parse_scoring_plays

    return parse_scoring_plays(ESPN_FIXTURE)
