import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

import storage
from adapters.espn import parse_scoring_plays, to_dict as espn_play_to_dict
from adapters.tank01 import extract_player_categories, extract_player_names, parse_box_score
from api.get_live_game.app import handler
from fantasy_points import match_espn_play

TANK01_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "tank01_box_score_final.json").read_text()
)["body"]
ESPN_FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "espn_summary.json").read_text())
SLEEPER_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "sleeper_league.json").read_text()
)


def _authorized_event(user_id: str = "apple-user-123") -> dict:
    return {"requestContext": {"authorizer": {"jwt": {"claims": {"sub": user_id}}}}}


def _fully_enriched_game_state():
    espn_plays = parse_scoring_plays(ESPN_FIXTURE)
    player_categories = extract_player_categories(TANK01_FIXTURE)
    player_names = extract_player_names(TANK01_FIXTURE)
    state = parse_box_score(TANK01_FIXTURE)
    enriched_events = tuple(
        replace(
            e,
            espn_play=espn_play_to_dict(match_espn_play(e, espn_plays)),
            player_categories={
                pid: tuple(sorted(player_categories[pid])) for pid in e.player_ids if pid in player_categories
            },
            player_names={pid: player_names[pid] for pid in e.player_ids if pid in player_names},
        )
        for e in state.events
    )
    return replace(state, events=enriched_events)


def _table_side_effect(game_table, league_table):
    def side_effect(table_name):
        return {"fantasee-live-game-state": game_table, "fantasee-league-config": league_table}[table_name]

    return side_effect


@patch("api.get_live_game.app.boto3.resource")
def test_returns_personalized_points_for_the_authenticated_user(mock_resource, monkeypatch):
    monkeypatch.setenv("LIVE_GAME_STATE_TABLE", "fantasee-live-game-state")
    monkeypatch.setenv("LEAGUE_CONFIG_TABLE", "fantasee-league-config")
    game_state = _fully_enriched_game_state()

    mock_game_table = MagicMock()
    mock_game_table.scan.return_value = {"Items": [storage.to_item(game_state)]}
    mock_league_table = MagicMock()
    mock_league_table.get_item.return_value = {
        "Item": {"pointValues": SLEEPER_FIXTURE["scoring_settings"]}
    }
    mock_resource.return_value.Table.side_effect = _table_side_effect(mock_game_table, mock_league_table)

    response = handler(_authorized_event(), None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["gameId"] == TANK01_FIXTURE["gameID"]
    first_event = next(e for e in body["events"] if "Dawson Knox" in e["description"])
    # Same real numbers verified in test_fantasy_points.py
    assert first_event["points"]["3930086"] == 8.7
    assert first_event["points"]["3039707"] == 6.68
    assert first_event["playerNames"]["3930086"] == "Dawson Knox"


@patch("api.get_live_game.app.boto3.resource")
def test_no_live_game_returns_404(mock_resource, monkeypatch):
    monkeypatch.setenv("LIVE_GAME_STATE_TABLE", "fantasee-live-game-state")
    monkeypatch.setenv("LEAGUE_CONFIG_TABLE", "fantasee-league-config")
    mock_game_table = MagicMock()
    mock_game_table.scan.return_value = {"Items": []}
    mock_resource.return_value.Table.side_effect = _table_side_effect(mock_game_table, MagicMock())

    response = handler(_authorized_event(), None)

    assert response["statusCode"] == 404


@patch("api.get_live_game.app.boto3.resource")
def test_user_with_no_imported_league_gets_zero_points_not_a_crash(mock_resource, monkeypatch):
    # No pointValues configured -> every stat lookup defaults to 0.0, so
    # credited players still appear with 0-point entries rather than the
    # whole response falling over. Correct: the shape stays consistent
    # regardless of whether the league has real scoring settings yet.
    monkeypatch.setenv("LIVE_GAME_STATE_TABLE", "fantasee-live-game-state")
    monkeypatch.setenv("LEAGUE_CONFIG_TABLE", "fantasee-league-config")
    game_state = _fully_enriched_game_state()

    mock_game_table = MagicMock()
    mock_game_table.scan.return_value = {"Items": [storage.to_item(game_state)]}
    mock_league_table = MagicMock()
    mock_league_table.get_item.return_value = {}  # no LeagueConfig item for this user yet
    mock_resource.return_value.Table.side_effect = _table_side_effect(mock_game_table, mock_league_table)

    response = handler(_authorized_event(), None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    enriched_events = [e for e in body["events"] if e["points"]]
    assert enriched_events
    assert all(value == 0.0 for e in enriched_events for value in e["points"].values())


@patch("api.get_live_game.app.boto3.resource")
def test_picks_the_most_recently_fetched_game_when_multiple_stored(mock_resource, monkeypatch):
    # TTL cleans up stale games within ~24h, but a brief window can have
    # more than one non-expired item -- must not pick an arbitrary one.
    monkeypatch.setenv("LIVE_GAME_STATE_TABLE", "fantasee-live-game-state")
    monkeypatch.setenv("LEAGUE_CONFIG_TABLE", "fantasee-league-config")
    stale = parse_box_score(TANK01_FIXTURE)
    stale_item = storage.to_item(stale)
    stale_item["gameId"] = "old-game"
    stale_item["fetchedAt"] = "2020-01-01T00:00:00+00:00"

    fresh_item = storage.to_item(_fully_enriched_game_state())

    mock_game_table = MagicMock()
    mock_game_table.scan.return_value = {"Items": [stale_item, fresh_item]}
    mock_league_table = MagicMock()
    mock_league_table.get_item.return_value = {"Item": {"pointValues": {}}}
    mock_resource.return_value.Table.side_effect = _table_side_effect(mock_game_table, mock_league_table)

    response = handler(_authorized_event(), None)

    body = json.loads(response["body"])
    assert body["gameId"] == TANK01_FIXTURE["gameID"]
