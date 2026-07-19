from __future__ import annotations

import json

# API Gateway HTTP API's JWT authorizer verifies the Sign in with Apple
# identity token (signature, issuer, audience, expiry) *before* invoking
# the Lambda — see template.yaml's EndzoneHttpApi. By the time a handler
# sees this event, `sub` is already a trusted claim; no token verification
# needed here. Per Apple's documented identity-token format (stable OIDC
# claims: iss=https://appleid.apple.com, aud=bundle ID for native apps,
# sub=stable per-user identifier) — not independently re-verified against
# a live token, since that needs a real device + deployed API Gateway,
# neither of which exist yet.
def user_id_from_event(event: dict) -> str:
    return event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]


def json_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def json_body(event: dict) -> dict:
    return json.loads(event.get("body") or "{}")
