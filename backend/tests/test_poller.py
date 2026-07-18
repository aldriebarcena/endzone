import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import storage
from adapters.tank01 import parse_box_score
from poller.app import handler

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "tank01_box_score_final.json").read_text()
)["body"]


@patch("poller.app.boto3.resource")
@patch("poller.app.fetch_game_state")
def test_first_poll_seeds_state_without_emitting_events(mock_fetch, mock_resource, monkeypatch):
    monkeypatch.setenv("LIVE_GAME_STATE_TABLE", "fantasee-live-game-state")
    current = parse_box_score(FIXTURE)
    mock_fetch.return_value = current

    mock_table = MagicMock()
    mock_table.get_item.return_value = {}
    mock_resource.return_value.Table.return_value = mock_table

    result = handler({"game_id": current.game_id}, None)

    assert result["new_event_count"] == 0
    assert result["is_final"] is True
    mock_table.put_item.assert_called_once()
    put_item = mock_table.put_item.call_args.kwargs["Item"]
    assert put_item["gameId"] == current.game_id


@patch("poller.app.boto3.client")
@patch("poller.app.boto3.resource")
@patch("poller.app.fetch_game_state")
def test_second_poll_detects_new_events(mock_fetch, mock_resource, mock_client, monkeypatch):
    monkeypatch.setenv("LIVE_GAME_STATE_TABLE", "fantasee-live-game-state")
    monkeypatch.setenv("SCORING_EVENTS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123/fantasee-scoring-events")
    earlier = parse_box_score({**FIXTURE, "scoringPlays": FIXTURE["scoringPlays"][:3]})
    later = parse_box_score(FIXTURE)
    mock_fetch.return_value = later

    mock_table = MagicMock()
    mock_table.get_item.return_value = {"Item": storage.to_item(earlier)}
    mock_resource.return_value.Table.return_value = mock_table
    mock_sqs = MagicMock()
    mock_client.return_value = mock_sqs

    result = handler({"game_id": later.game_id}, None)

    assert result["new_event_count"] == 3
    assert result["is_final"] is True
    assert mock_sqs.send_message.call_count == 3
    first_call_body = json.loads(mock_sqs.send_message.call_args_list[0].kwargs["MessageBody"])
    assert first_call_body["description"] == FIXTURE["scoringPlays"][3]["score"]


@patch("poller.app.boto3.resource")
@patch("poller.app.fetch_game_state")
def test_in_progress_game_is_not_final(mock_fetch, mock_resource, monkeypatch):
    monkeypatch.setenv("LIVE_GAME_STATE_TABLE", "fantasee-live-game-state")
    in_progress = parse_box_score({**FIXTURE, "gameStatus": "In Progress"})
    mock_fetch.return_value = in_progress

    mock_table = MagicMock()
    mock_table.get_item.return_value = {}
    mock_resource.return_value.Table.return_value = mock_table

    result = handler({"game_id": in_progress.game_id}, None)

    assert result["is_final"] is False
