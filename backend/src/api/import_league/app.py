from __future__ import annotations

import logging
import os

import boto3

from api.common import json_body, json_response, user_id_from_event
from league_import import import_league

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    user_id = user_id_from_event(event)
    sleeper_league_id = json_body(event).get("sleeperLeagueId")
    if not sleeper_league_id:
        return json_response(400, {"error": "sleeperLeagueId is required"})

    table = boto3.resource("dynamodb").Table(os.environ["LEAGUE_CONFIG_TABLE"])
    try:
        item = import_league(table, user_id, sleeper_league_id)
    except Exception:
        logger.exception("failed to import league %s for user %s", sleeper_league_id, user_id)
        return json_response(502, {"error": "failed to import league"})

    return json_response(200, item)
