import base64
import json

import httpx
import pytest


def b64url_decode(s: str) -> bytes:
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode())


def decode_payload(jwt_str: str) -> dict:
    _, payload, _ = jwt_str.split(".")
    return json.loads(b64url_decode(payload))


@pytest.fixture(scope="session")
def alice_tokens(discovery, claim_inspector_secret):
    """Use ROPC via claim-inspector (which has directAccessGrantsEnabled=true)."""
    r = httpx.post(
        discovery["token_endpoint"],
        data={
            "grant_type": "password",
            "client_id": "claim-inspector",
            "client_secret": claim_inspector_secret,
            "username": "alice",
            "password": "Sandbox!Alice",
            "scope": "openid profile email oidc-kafe-profile",
        },
        timeout=10,
    )
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="session")
def alice_id_claims(alice_tokens):
    return decode_payload(alice_tokens["id_token"])


@pytest.fixture(scope="session")
def alice_userinfo(discovery, alice_tokens):
    r = httpx.get(
        discovery["userinfo_endpoint"],
        headers={"Authorization": f"Bearer {alice_tokens['access_token']}"},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    return r.json()


FORBIDDEN_IN_ID_TOKEN = [
    "email", "email_verified",
    "eduPersonPrincipalName", "eduPersonUniqueId",
    "eduPersonAffiliation", "eduPersonScopedAffiliation",
    "schacHomeOrganization", "schacHomeOrganizationType",
    "o", "ou", "isMemberOf",
]


@pytest.mark.parametrize("claim", FORBIDDEN_IN_ID_TOKEN)
def test_id_token_does_not_carry_user_claim(alice_id_claims, claim):
    assert claim not in alice_id_claims, \
        f"P3 violation: '{claim}' leaked into ID token"


REQUIRED_IN_USERINFO = [
    "sub", "preferred_username", "email", "name",
    "eduPersonPrincipalName", "eduPersonAffiliation",
    "schacHomeOrganization", "o",
]


@pytest.mark.parametrize("claim", REQUIRED_IN_USERINFO)
def test_userinfo_carries_user_claim(alice_userinfo, claim):
    assert claim in alice_userinfo, \
        f"userinfo missing expected claim '{claim}': {list(alice_userinfo.keys())}"


def test_affiliation_is_array(alice_userinfo):
    assert isinstance(alice_userinfo["eduPersonAffiliation"], list)
    assert "student" in alice_userinfo["eduPersonAffiliation"]
    assert "member" in alice_userinfo["eduPersonAffiliation"]


def test_preferred_username_is_uid_not_email(alice_userinfo):
    assert alice_userinfo["preferred_username"] == "alice"
