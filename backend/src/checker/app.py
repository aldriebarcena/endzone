from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import boto3

from adapters.tank01 import fetch_games_for_date

logger = logging.getLogger()
logger.setLevel(logging.INFO)

LIVE_STATUS_CODE = "1"

# Tank01 dates NFL games by US Eastern game-day, not UTC calendar day —
# using UTC here would misfire near midnight ET.
GAME_DAY_TIMEZONE = ZoneInfo("America/New_York")


def handler(event, context):
    today = datetime.now(GAME_DAY_TIMEZONE).strftime("%Y%m%d")
    games = fetch_games_for_date(today)

    live_game = _pick_game_to_track(games)
    if live_game is None:
        logger.info("no live games for %s", today)
        return {"started": False}

    game_id = live_game["gameID"]
    # Only present in getNFLGamesForDate's response, not getNFLBoxScore's
    # (which is all poller calls) — passed through the execution input so
    # poller can reach ESPN's enrichment data without a second Tank01
    # request just to look this up.
    espn_game_id = live_game.get("espnID")
    sfn = boto3.client("stepfunctions")
    try:
        sfn.start_execution(
            stateMachineArn=os.environ["POLLER_STATE_MACHINE_ARN"],
            name=game_id,
            input=json.dumps({"game_id": game_id, "espn_game_id": espn_game_id}),
        )
        started = True
        logger.info("started poller execution for %s", game_id)
    except sfn.exceptions.ExecutionAlreadyExists:
        started = False
        logger.info("poller execution already running for %s", game_id)

    return {"started": started, "game_id": game_id}


def _pick_game_to_track(games: list[dict]) -> dict | None:
    """First live game found, by provider list order. Deliberately not
    "highest-scoring active game in their league" (DESIGN.md's stated
    goal) — that's not a "haven't gotten to it yet" gap, it's a reasoned
    dead end given this project's actual constraints:

    1. Budget: ranking live candidates by score needs a getNFLBoxScore
       call per candidate, since Tank01's games-list response carries no
       score field. A quiet Sunday slate (3-4 simultaneous live games)
       checked every 15 min for 3 hours is already 36-48 extra requests;
       a normal Sunday (up to ~13 simultaneous games across slates) could
       burn a meaningful fraction of the entire 1,000/month budget in a
       single day, just to rank candidates.

    2. Even if the budget were spent: "highest-scoring, globally" isn't
       the same thing as "highest-scoring in their league" — the actual
       goal needs per-user roster awareness (which players are on which
       user's team) to know which games are even relevant to a given
       push subscriber. That needs full Sleeper roster import (Phase 5
       deliberately skipped this as speculative — see PROJECT_PLAN.md)
       AND a player-ID mapping across three providers whose ID schemes
       have never been cross-checked against each other (Sleeper, Tank01,
       ESPN all use different numbering).

    3. Even solving #2 runs into DESIGN.md's own explicit v1 non-goal:
       multi-game concurrent tracking is out of scope ("explicit future
       work, not an oversight"). Different users caring about different
       games would need exactly that.

    So: spending budget on cross-game ranking would optimize a heuristic
    (global highest score) that still wouldn't reach the actual stated
    goal, given the other v1 scope boundaries already in place. First-
    live-game-found is the correct choice within current constraints, not
    a placeholder waiting to be finished — it'd need those other
    boundaries (multi-game tracking, roster import) revisited first, at
    which point this function would need to be redesigned anyway rather
    than incrementally improved.
    """
    return next(
        (game for game in games if game.get("gameStatusCode") == LIVE_STATUS_CODE),
        None,
    )
