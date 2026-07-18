from __future__ import annotations

import json
import logging
import os

import boto3

from apns import build_auth_token, send_push

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    device_tokens = _subscribed_device_tokens()

    if not device_tokens:
        logger.info("no subscribers with a registered device token, nothing to push")
        return {"batchItemFailures": []}

    auth_token = build_auth_token(
        team_id=os.environ["APNS_TEAM_ID"],
        key_id=os.environ["APNS_KEY_ID"],
        private_key=os.environ["APNS_PRIVATE_KEY"],
    )

    failures = []
    for record in event.get("Records", []):
        try:
            _process_record(record, device_tokens, auth_token)
        except Exception:
            logger.exception("failed to process record %s", record.get("messageId"))
            failures.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": failures}


def _process_record(record: dict, device_tokens: list[str], auth_token: str) -> None:
    scoring_event = json.loads(record["body"])
    title = f"{scoring_event['team']} — {scoring_event['scoring_type']}"
    # Fantasy point value isn't included: it's league-dependent (custom
    # scoring settings) and that computation isn't designed yet — see
    # PROJECT_PLAN.md open questions. Raw play description stands in for now.
    body = scoring_event["description"]

    for device_token in device_tokens:
        response = send_push(
            device_token,
            title=title,
            body=body,
            bundle_id=os.environ["APNS_BUNDLE_ID"],
            auth_token=auth_token,
            sandbox=os.environ.get("APNS_SANDBOX", "true").lower() == "true",
        )
        if response.status_code != 200:
            logger.warning(
                "APNs push failed for %s: %s %s",
                device_token,
                response.status_code,
                response.text,
            )


def _subscribed_device_tokens() -> list[str]:
    # Scan is fine at portfolio scale (single-digit to low-dozens of
    # users); would need a GSI on deviceToken, or a dedicated table, if
    # this ever needed to scale further. No write path for deviceToken
    # exists yet either — see PROJECT_PLAN.md's API-surface open question.
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(os.environ["LEAGUE_CONFIG_TABLE"])
    response = table.scan()
    return [
        item["deviceToken"] for item in response.get("Items", []) if item.get("deviceToken")
    ]
