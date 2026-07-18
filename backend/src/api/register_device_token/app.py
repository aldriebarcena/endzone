from __future__ import annotations

import os

import boto3

from api.common import json_body, json_response, user_id_from_event


def handler(event, context):
    user_id = user_id_from_event(event)
    device_token = json_body(event).get("deviceToken")
    if not device_token:
        return json_response(400, {"error": "deviceToken is required"})

    table = boto3.resource("dynamodb").Table(os.environ["LEAGUE_CONFIG_TABLE"])
    # UpdateItem upserts — a user can register a device token before ever
    # importing a league (order-independent), consistent with push.py
    # treating deviceToken as just another optional LeagueConfig attribute.
    table.update_item(
        Key={"userId": user_id},
        UpdateExpression="SET deviceToken = :token",
        ExpressionAttributeValues={":token": device_token},
    )

    return json_response(200, {"userId": user_id, "deviceToken": device_token})
