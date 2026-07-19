from __future__ import annotations

from datetime import datetime, timezone

from adapters.sleeper import fetch_league


def import_league(table, user_id: str, league_id: str) -> dict:
    """Fetches the Sleeper league and writes/overwrites this user's
    LeagueConfig item. Custom point values are seeded from Sleeper's own
    scoring_settings — accurate defaults reflecting the user's real
    league, since no override UI/API exists yet.
    Re-importing the same league_id overwrites pointValues, so any
    manual overrides a future override feature made would be lost; that
    feature doesn't exist yet so it isn't a real loss today, but is worth
    remembering once it does.
    """
    league = fetch_league(league_id)

    item = {
        "userId": user_id,
        "sleeperLeagueId": league.league_id,
        "leagueName": league.name,
        "season": league.season,
        "pointValues": league.scoring_settings,
        "importedAt": datetime.now(timezone.utc).isoformat(),
    }
    table.put_item(Item=item)
    return item
