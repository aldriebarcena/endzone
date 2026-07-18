import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

from apns import build_auth_token


def _throwaway_keypair() -> tuple[str, str]:
    """APNs auth keys are ES256 (P-256) EC keys. Real Apple keys can't be
    used in a test, so we generate a disposable one and sign/verify with
    it — this validates the JWT construction, not real Apple auth.
    """
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


def test_build_auth_token_has_expected_claims_and_header():
    private_pem, public_pem = _throwaway_keypair()

    token = build_auth_token(team_id="TEAM123", key_id="KEY456", private_key=private_pem)

    header = jwt.get_unverified_header(token)
    assert header["kid"] == "KEY456"
    assert header["alg"] == "ES256"

    claims = jwt.decode(token, public_pem, algorithms=["ES256"])
    assert claims["iss"] == "TEAM123"
    assert "iat" in claims
