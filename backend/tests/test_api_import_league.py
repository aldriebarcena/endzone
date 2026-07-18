import json
from unittest.mock import MagicMock, patch

from api.import_league.app import handler


def _event(body: dict | None) -> dict:
    return {
        "requestContext": {"authorizer": {"jwt": {"claims": {"sub": "apple-user-123"}}}},
        "body": json.dumps(body) if body is not None else None,
    }


@patch("api.import_league.app.boto3.resource")
@patch("api.import_league.app.import_league")
def test_imports_league_for_authenticated_user(mock_import_league, mock_resource, monkeypatch):
    monkeypatch.setenv("LEAGUE_CONFIG_TABLE", "endzone-league-config")
    mock_import_league.return_value = {
        "userId": "apple-user-123",
        "sleeperLeagueId": "289646328504385536",
        "leagueName": "Sleeper Friends League",
        "season": "2018",
        "pointValues": {"pass_td": 6.0},
        "importedAt": "2026-01-01T00:00:00+00:00",
    }
    mock_table = MagicMock()
    mock_resource.return_value.Table.return_value = mock_table

    response = handler(_event({"sleeperLeagueId": "289646328504385536"}), None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["sleeperLeagueId"] == "289646328504385536"
    mock_import_league.assert_called_once_with(mock_table, "apple-user-123", "289646328504385536")


def test_missing_sleeper_league_id_returns_400():
    response = handler(_event({}), None)

    assert response["statusCode"] == 400
    assert "sleeperLeagueId" in json.loads(response["body"])["error"]


@patch("api.import_league.app.boto3.resource")
@patch("api.import_league.app.import_league")
def test_adapter_failure_returns_502(mock_import_league, mock_resource, monkeypatch):
    monkeypatch.setenv("LEAGUE_CONFIG_TABLE", "endzone-league-config")
    mock_import_league.side_effect = Exception("Sleeper is down")
    mock_resource.return_value.Table.return_value = MagicMock()

    response = handler(_event({"sleeperLeagueId": "289646328504385536"}), None)

    assert response["statusCode"] == 502
