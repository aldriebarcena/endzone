import json
from pathlib import Path

from adapters.sleeper import parse_league

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "sleeper_league.json").read_text())


def test_parses_league_level_fields():
    league = parse_league(FIXTURE)
    assert league.league_id == "289646328504385536"
    assert league.name == "Sleeper Friends League"
    assert league.season == "2018"
    assert league.total_rosters == 12
    assert "FLEX" in league.roster_positions


def test_parses_real_scoring_settings():
    league = parse_league(FIXTURE)
    assert league.scoring_settings["pass_td"] == 6.0
    assert league.scoring_settings["rush_td"] == 6.0
    assert league.scoring_settings["rec"] == 1.0
    assert league.scoring_settings["pass_int"] == -2.0
    assert league.scoring_settings["fum_lost"] == -2.0


def test_scoring_settings_covers_dozens_of_stat_categories():
    league = parse_league(FIXTURE)
    # Not an arbitrary threshold — asserts we captured the full breadth of
    # per-stat categories Sleeper tracks, not just a handful of obvious ones.
    assert len(league.scoring_settings) > 50
