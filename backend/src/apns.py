from __future__ import annotations

import time

import httpx
import jwt

PRODUCTION_HOST = "https://api.push.apple.com"
SANDBOX_HOST = "https://api.sandbox.push.apple.com"


def build_auth_token(*, team_id: str, key_id: str, private_key: str) -> str:
    """APNs token-based auth (RFC 7519 JWT, ES256) — the current Apple-
    recommended approach, no certificate renewal needed. Callers should
    cache/reuse a token for up to ~55 minutes rather than minting one per
    push; Apple rate-limits token generation.
    """
    return jwt.encode(
        {"iss": team_id, "iat": int(time.time())},
        private_key,
        algorithm="ES256",
        headers={"kid": key_id},
    )


def send_push(
    device_token: str,
    *,
    title: str,
    body: str,
    bundle_id: str,
    auth_token: str,
    sandbox: bool = True,
) -> httpx.Response:
    host = SANDBOX_HOST if sandbox else PRODUCTION_HOST
    payload = {"aps": {"alert": {"title": title, "body": body}, "sound": "default"}}
    with httpx.Client(http2=True) as client:
        return client.post(
            f"{host}/3/device/{device_token}",
            json=payload,
            headers={
                "authorization": f"bearer {auth_token}",
                "apns-topic": bundle_id,
                "apns-push-type": "alert",
            },
            timeout=10,
        )
