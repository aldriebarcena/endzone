import json
from unittest.mock import MagicMock, patch

from api.register_device_token.app import handler


def _event(body: dict | None) -> dict:
    return {
        "requestContext": {"authorizer": {"jwt": {"claims": {"sub": "apple-user-123"}}}},
        "body": json.dumps(body) if body is not None else None,
    }


@patch("api.register_device_token.app.boto3.resource")
def test_registers_device_token_for_authenticated_user(mock_resource, monkeypatch):
    monkeypatch.setenv("LEAGUE_CONFIG_TABLE", "fantasee-league-config")
    mock_table = MagicMock()
    mock_resource.return_value.Table.return_value = mock_table

    response = handler(_event({"deviceToken": "abc123"}), None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"userId": "apple-user-123", "deviceToken": "abc123"}
    mock_table.update_item.assert_called_once_with(
        Key={"userId": "apple-user-123"},
        UpdateExpression="SET deviceToken = :token",
        ExpressionAttributeValues={":token": "abc123"},
    )


def test_missing_device_token_returns_400():
    response = handler(_event({}), None)

    assert response["statusCode"] == 400
    assert "deviceToken" in json.loads(response["body"])["error"]
