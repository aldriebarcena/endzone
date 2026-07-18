from api.common import json_body, json_response, user_id_from_event


def _authorized_event(**overrides) -> dict:
    event = {
        "requestContext": {"authorizer": {"jwt": {"claims": {"sub": "apple-user-123"}}}},
        "body": None,
    }
    event.update(overrides)
    return event


def test_user_id_from_event_reads_verified_jwt_sub_claim():
    assert user_id_from_event(_authorized_event()) == "apple-user-123"


def test_json_body_parses_json_string_body():
    event = _authorized_event(body='{"sleeperLeagueId": "123"}')
    assert json_body(event) == {"sleeperLeagueId": "123"}


def test_json_body_returns_empty_dict_for_missing_body():
    assert json_body(_authorized_event(body=None)) == {}


def test_json_response_shape():
    response = json_response(200, {"ok": True})
    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"] == "application/json"
    assert response["body"] == '{"ok": true}'
