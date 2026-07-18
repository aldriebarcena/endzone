import json
from unittest.mock import MagicMock, patch

from checker.app import _pick_game_to_track, handler

LIVE_GAMES = [
    {"gameID": "20260101_AAA@BBB", "gameStatusCode": "2"},
    {"gameID": "20260101_CCC@DDD", "gameStatusCode": "1"},
    {"gameID": "20260101_EEE@FFF", "gameStatusCode": "0"},
]


def test_pick_game_to_track_returns_first_live_game():
    assert _pick_game_to_track(LIVE_GAMES)["gameID"] == "20260101_CCC@DDD"


def test_pick_game_to_track_returns_none_when_no_live_games():
    games = [{"gameID": "x", "gameStatusCode": "2"}]
    assert _pick_game_to_track(games) is None


@patch("checker.app.boto3.client")
@patch("checker.app.fetch_games_for_date")
def test_handler_starts_execution_for_live_game(mock_fetch, mock_boto_client, monkeypatch):
    monkeypatch.setenv("POLLER_STATE_MACHINE_ARN", "arn:aws:states:us-east-1:123:stateMachine:fantasee-poller")
    mock_fetch.return_value = LIVE_GAMES
    mock_sfn = MagicMock()
    mock_boto_client.return_value = mock_sfn

    result = handler({}, None)

    assert result == {"started": True, "game_id": "20260101_CCC@DDD"}
    mock_sfn.start_execution.assert_called_once()
    _, kwargs = mock_sfn.start_execution.call_args
    assert kwargs["name"] == "20260101_CCC@DDD"
    assert json.loads(kwargs["input"]) == {"game_id": "20260101_CCC@DDD"}


@patch("checker.app.boto3.client")
@patch("checker.app.fetch_games_for_date")
def test_handler_noop_when_no_live_games(mock_fetch, mock_boto_client):
    mock_fetch.return_value = [{"gameID": "x", "gameStatusCode": "2"}]

    result = handler({}, None)

    assert result == {"started": False}
    mock_boto_client.assert_not_called()


@patch("checker.app.boto3.client")
@patch("checker.app.fetch_games_for_date")
def test_handler_treats_already_running_execution_as_success(mock_fetch, mock_boto_client, monkeypatch):
    monkeypatch.setenv("POLLER_STATE_MACHINE_ARN", "arn:aws:states:us-east-1:123:stateMachine:fantasee-poller")
    mock_fetch.return_value = LIVE_GAMES
    mock_sfn = MagicMock()
    mock_sfn.exceptions.ExecutionAlreadyExists = type("ExecutionAlreadyExists", (Exception,), {})
    mock_sfn.start_execution.side_effect = mock_sfn.exceptions.ExecutionAlreadyExists()
    mock_boto_client.return_value = mock_sfn

    result = handler({}, None)

    assert result == {"started": False, "game_id": "20260101_CCC@DDD"}
