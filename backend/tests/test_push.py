import json
from unittest.mock import MagicMock, patch

from push.app import handler

EVENT_BODY = {
    "event_id": "game-1:Q1:8:17:BUF:TD",
    "game_id": "game-1",
    "team": "BUF",
    "scoring_type": "TD",
    "description": "Dawson Knox 17 Yd pass from Mitchell Trubisky (Matt Prater Kick)",
    "period": "Q1",
    "game_clock": "8:17",
    "home_score": 7,
    "away_score": 0,
    "player_ids": ["3039707", "3930086", "11122"],
}


def _sqs_record(message_id: str = "msg-1") -> dict:
    return {"messageId": message_id, "body": json.dumps(EVENT_BODY)}


def _env(monkeypatch):
    monkeypatch.setenv("LEAGUE_CONFIG_TABLE", "endzone-league-config")
    monkeypatch.setenv("APNS_TEAM_ID", "TEAM123")
    monkeypatch.setenv("APNS_KEY_ID", "KEY456")
    monkeypatch.setenv("APNS_PRIVATE_KEY", "fake-key")
    monkeypatch.setenv("APNS_BUNDLE_ID", "com.example.endzone")


@patch("push.app.send_push")
@patch("push.app.build_auth_token")
@patch("push.app.boto3.resource")
def test_pushes_to_every_subscribed_device_token(
    mock_resource, mock_build_token, mock_send_push, monkeypatch
):
    _env(monkeypatch)
    mock_table = MagicMock()
    mock_table.scan.return_value = {
        "Items": [
            {"userId": "u1", "deviceToken": "token-1"},
            {"userId": "u2", "deviceToken": "token-2"},
            {"userId": "u3"},  # no device token registered — skipped
        ]
    }
    mock_resource.return_value.Table.return_value = mock_table
    mock_build_token.return_value = "fake-jwt"
    mock_send_push.return_value = MagicMock(status_code=200)

    result = handler({"Records": [_sqs_record()]}, None)

    assert result == {"batchItemFailures": []}
    assert mock_send_push.call_count == 2
    sent_tokens = {call.args[0] for call in mock_send_push.call_args_list}
    assert sent_tokens == {"token-1", "token-2"}


@patch("push.app.send_push")
@patch("push.app.build_auth_token")
@patch("push.app.boto3.resource")
def test_no_subscribers_is_a_noop(mock_resource, mock_build_token, mock_send_push, monkeypatch):
    _env(monkeypatch)
    mock_table = MagicMock()
    mock_table.scan.return_value = {"Items": []}
    mock_resource.return_value.Table.return_value = mock_table

    result = handler({"Records": [_sqs_record()]}, None)

    assert result == {"batchItemFailures": []}
    mock_send_push.assert_not_called()
    mock_build_token.assert_not_called()


@patch("push.app.send_push")
@patch("push.app.build_auth_token")
@patch("push.app.boto3.resource")
def test_personalizes_points_per_subscriber_point_values(
    mock_resource, mock_build_token, mock_send_push, monkeypatch
):
    # Same play, two subscribers with different league scoring settings —
    # this is the whole reason point computation moved to push.py instead
    # of poller.py computing one canonical number.
    _env(monkeypatch)
    message = {
        **EVENT_BODY,
        "espn_play": {
            "play_type": "Passing Touchdown",
            "text": "M.Trubisky pass deep right to D.Knox for 17 yards, TOUCHDOWN.",
            "yardage": 17,
            "team": "BUF",
            "period": 1,
            "clock": "8:17",
        },
        "player_categories": {"3039707": ["Passing"], "3930086": ["Receiving"]},
        "player_names": {"3039707": "Mitchell Trubisky", "3930086": "Dawson Knox"},
    }
    mock_table = MagicMock()
    mock_table.scan.return_value = {
        "Items": [
            {
                "userId": "u1",
                "deviceToken": "token-1",
                "pointValues": {"pass_yd": 0.04, "pass_td": 6.0, "rec_yd": 0.1, "rec_td": 6.0, "rec": 1.0},
            },
            {
                "userId": "u2",
                "deviceToken": "token-2",
                "pointValues": {"pass_yd": 0.04, "pass_td": 4.0, "rec_yd": 0.1, "rec_td": 6.0, "rec": 1.0},
            },
        ]
    }
    mock_resource.return_value.Table.return_value = mock_table
    mock_build_token.return_value = "fake-jwt"
    mock_send_push.return_value = MagicMock(status_code=200)

    record = {"messageId": "msg-1", "body": json.dumps(message)}
    handler({"Records": [record]}, None)

    assert mock_send_push.call_count == 2
    bodies = [call.kwargs["body"] for call in mock_send_push.call_args_list]
    assert any("Mitchell Trubisky +6.68 pts" in body for body in bodies)
    assert any("Mitchell Trubisky +4.68 pts" in body for body in bodies)


@patch("push.app.send_push")
@patch("push.app.build_auth_token")
@patch("push.app.boto3.resource")
def test_no_espn_play_falls_back_to_plain_description(
    mock_resource, mock_build_token, mock_send_push, monkeypatch
):
    _env(monkeypatch)
    mock_table = MagicMock()
    mock_table.scan.return_value = {
        "Items": [{"userId": "u1", "deviceToken": "token-1", "pointValues": {"pass_td": 6.0}}]
    }
    mock_resource.return_value.Table.return_value = mock_table
    mock_build_token.return_value = "fake-jwt"
    mock_send_push.return_value = MagicMock(status_code=200)

    handler({"Records": [_sqs_record()]}, None)

    body = mock_send_push.call_args.kwargs["body"]
    assert body == EVENT_BODY["description"]


@patch("push.app.send_push")
@patch("push.app.build_auth_token")
@patch("push.app.boto3.resource")
def test_malformed_record_reported_as_batch_item_failure(
    mock_resource, mock_build_token, mock_send_push, monkeypatch
):
    _env(monkeypatch)
    mock_table = MagicMock()
    mock_table.scan.return_value = {"Items": [{"userId": "u1", "deviceToken": "token-1"}]}
    mock_resource.return_value.Table.return_value = mock_table
    mock_build_token.return_value = "fake-jwt"

    bad_record = {"messageId": "bad-msg", "body": "not json"}
    result = handler({"Records": [bad_record]}, None)

    assert result == {"batchItemFailures": [{"itemIdentifier": "bad-msg"}]}
