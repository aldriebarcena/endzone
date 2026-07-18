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
    sfn = boto3.client("stepfunctions")
    try:
        sfn.start_execution(
            stateMachineArn=os.environ["POLLER_STATE_MACHINE_ARN"],
            name=game_id,
            input=json.dumps({"game_id": game_id}),
        )
        started = True
        logger.info("started poller execution for %s", game_id)
    except sfn.exceptions.ExecutionAlreadyExists:
        started = False
        logger.info("poller execution already running for %s", game_id)

    return {"started": started, "game_id": game_id}


def _pick_game_to_track(games: list[dict]) -> dict | None:
    """First live game found, by provider list order. Not the "highest-
    scoring active game in their league" DESIGN.md describes — that needs
    per-user league context (Sleeper import, Phase 5) and box-score calls
    per candidate to compare scores, which isn't built yet and would burn
    through Tank01's scarce request budget just to rank candidates. See
    PROJECT_PLAN.md open questions.
    """
    return next(
        (game for game in games if game.get("gameStatusCode") == LIVE_STATUS_CODE),
        None,
    )
