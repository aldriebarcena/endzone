import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from league_import import import_league
from adapters.sleeper import parse_league

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "sleeper_league.json").read_text())


@patch("league_import.fetch_league")
def test_import_league_writes_expected_item(mock_fetch_league):
    mock_fetch_league.return_value = parse_league(FIXTURE)
    mock_table = MagicMock()

    result = import_league(mock_table, user_id="user-1", league_id="289646328504385536")

    mock_table.put_item.assert_called_once()
    put_item = mock_table.put_item.call_args.kwargs["Item"]
    assert put_item == result
    assert put_item["userId"] == "user-1"
    assert put_item["sleeperLeagueId"] == "289646328504385536"
    assert put_item["leagueName"] == "Sleeper Friends League"
    assert put_item["pointValues"]["pass_td"] == 6.0
    assert "importedAt" in put_item


@patch("league_import.fetch_league")
def test_import_league_calls_adapter_with_given_league_id(mock_fetch_league):
    mock_fetch_league.return_value = parse_league(FIXTURE)
    mock_table = MagicMock()

    import_league(mock_table, user_id="user-1", league_id="289646328504385536")

    mock_fetch_league.assert_called_once_with("289646328504385536")
