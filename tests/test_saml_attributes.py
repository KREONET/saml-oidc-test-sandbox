"""SAML attribute release regression.

Drives stest-app through a full SP-initiated SSO roundtrip as alice and
asserts that the assertion's AttributeStatement carries the KAFE
attribute bundle — the SAML counterpart to
test_claims_distribution.py's OIDC checks.
"""
import httpx
import pytest
from bs4 import BeautifulSoup


@pytest.fixture(scope="session")
def alice_saml_ava(stest_base_url):
    """Runs the full SP-initiated SSO flow and returns the parsed ava dict.

    Steps:
      1. GET stest-app /login  → 302 to Keycloak with SAMLRequest
      2. GET the Keycloak login page, scrape the form
      3. POST username/password → Keycloak returns an auto-submit POST form
         with the SAMLResponse targeting the SP's ACS
      4. POST the SAMLResponse to /acs → SP session is populated
      5. GET /me.json → parsed assertion attributes
    """
    with httpx.Client(timeout=15, follow_redirects=False) as client:
        r = client.get(f"{stest_base_url}/login")
        assert r.status_code == 302, f"SP /login should redirect, got {r.status_code}"
        kc_sso_url = r.headers["location"]

        r = client.get(kc_sso_url)
        assert r.status_code == 200, f"Keycloak SSO page: {r.status_code}\n{r.text[:500]}"

        soup = BeautifulSoup(r.text, "lxml")
        form = soup.find("form", id="kc-form-login") or soup.find("form")
        assert form is not None, f"no login form in Keycloak response: {r.text[:800]}"
        action = form.get("action")
        data = {i.get("name"): i.get("value", "")
                for i in form.find_all("input") if i.get("name")}
        data["username"] = "alice"
        data["password"] = "Sandbox!Alice"

        r = client.post(action, data=data)
        assert r.status_code == 200, f"Keycloak login POST: {r.status_code}\n{r.text[:500]}"

        soup = BeautifulSoup(r.text, "lxml")
        form = soup.find("form")
        assert form is not None, f"no auto-submit SAMLResponse form: {r.text[:800]}"
        acs_url = form.get("action")
        data = {i.get("name"): i.get("value", "")
                for i in form.find_all("input") if i.get("name")}
        assert "SAMLResponse" in data, f"missing SAMLResponse input: keys={list(data)}"

        r = client.post(acs_url, data=data)
        assert r.status_code in (302, 303), \
            f"ACS should redirect to RelayState; got {r.status_code}\n{r.text[:500]}"

        r = client.get(f"{stest_base_url}/me.json")
        assert r.status_code == 200, f"/me.json {r.status_code}: {r.text}"
        return r.json()


REQUIRED_ATTRIBUTES = [
    "eduPersonPrincipalName",
    "eduPersonUniqueId",
    "eduPersonAffiliation",
    "eduPersonScopedAffiliation",
    "eduPersonEntitlement",
    "schacHomeOrganization",
    "schacHomeOrganizationType",
    "o",
    "ou",
    "isMemberOf",
    "displayName",
    "uid",
    "mail",
]


@pytest.mark.parametrize("attr", REQUIRED_ATTRIBUTES)
def test_attribute_present_in_assertion(alice_saml_ava, attr):
    ava = alice_saml_ava["ava"]
    assert attr in ava, \
        f"assertion missing attribute '{attr}' — ava keys: {sorted(ava.keys())}"


def test_nameid_is_persistent(alice_saml_ava):
    name_id = alice_saml_ava["name_id"]
    assert name_id["format"] == "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"
    assert name_id["text"], "NameID value is empty"


def test_session_index_present(alice_saml_ava):
    assert alice_saml_ava["session_index"], "SessionIndex missing from AuthnStatement"


def test_issuer_matches_idp(alice_saml_ava):
    assert alice_saml_ava["issuer"] == "http://iam.sandbox.ac.kr/realms/sandbox"


def test_affiliation_is_multivalued(alice_saml_ava):
    aff = alice_saml_ava["ava"]["eduPersonAffiliation"]
    assert isinstance(aff, list)
    assert "student" in aff and "member" in aff


def test_uid_is_alice(alice_saml_ava):
    uid = alice_saml_ava["ava"]["uid"]
    assert uid == ["alice"] or uid == "alice"
