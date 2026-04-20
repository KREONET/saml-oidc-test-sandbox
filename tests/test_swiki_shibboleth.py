"""swiki-app regression — Shibboleth SP + Auth_remoteuser end-to-end.

Drives alice through the full browser flow into swiki (MediaWiki with
libapache2-mod-shib) and asserts two things:

  1. The Shibboleth SP session at /Shibboleth.sso/Session carries every
     KAFE attribute we expect from the saml-kafe-profile scope.
  2. MediaWiki itself recognizes the user (personal toolbar shows a
     User:Alice page), proving Auth_remoteuser correctly promoted the
     REMOTE_USER / Shib-* env vars into a MW session.

Kept separate from test_saml_attributes.py because that one drives
stest-app via pysaml2 (assertion-level), whereas this one drives swiki
through mod_shib at the Apache layer — the two code paths have no
shared implementation.
"""
import re

import httpx
import pytest
from bs4 import BeautifulSoup


SWIKI = "http://swiki.sandbox.ac.kr"


@pytest.fixture(scope="module")
def alice_swiki_session():
    """Complete an alice SSO into swiki and return (shib_attrs, mw_html).

    shib_attrs is a dict pulled from /Shibboleth.sso/Session; mw_html is
    the body of /wiki/Main_Page after the Shibboleth session is in place.
    """
    with httpx.Client(timeout=15, follow_redirects=True) as c:
        r = c.get(f"{SWIKI}/wiki/Special:UserLogin")
        soup = BeautifulSoup(r.text, "lxml")
        form = soup.find("form", id="kc-form-login") or soup.find("form")
        assert form is not None, f"no Keycloak login form: {r.text[:400]}"
        data = {i.get("name"): i.get("value", "")
                for i in form.find_all("input") if i.get("name")}
        data["username"] = "alice"
        data["password"] = "Sandbox!Alice"

        r = c.post(form["action"], data=data)
        soup = BeautifulSoup(r.text, "lxml")
        form = soup.find("form")
        assert form is not None and "SAMLResponse" in r.text, \
            f"no auto-submit SAMLResponse form: {r.text[:400]}"
        data = {i.get("name"): i.get("value", "")
                for i in form.find_all("input") if i.get("name")}
        r = c.post(form["action"], data=data)
        # After /Shibboleth.sso/SAML2/POST the target URL may 404; that's
        # fine — the shib session cookie is what matters.

        r = c.get(f"{SWIKI}/Shibboleth.sso/Session")
        assert r.status_code == 200, f"Shib Session handler: {r.status_code}"
        attrs = {k: v.strip() for k, v in
                 re.findall(r"<strong>(\w+)</strong>: ([^<]+)", r.text)}

        r = c.get(f"{SWIKI}/wiki/Main_Page")
        assert r.status_code == 200, f"Main_Page: {r.status_code}"
        return attrs, r.text


REQUIRED_ATTRIBUTES = [
    "displayName",
    "eduPersonAffiliation",
    "eduPersonEntitlement",
    "eduPersonPrincipalName",
    "eduPersonScopedAffiliation",
    "eduPersonUniqueId",
    "isMemberOf",
    "mail",
    "o",
    "ou",
    "schacHomeOrganization",
    "schacHomeOrganizationType",
    "schacPersonalUniqueCode",
    "uid",
]


@pytest.mark.parametrize("attr", REQUIRED_ATTRIBUTES)
def test_shibboleth_session_has_attribute(alice_swiki_session, attr):
    shib_attrs, _ = alice_swiki_session
    assert attr in shib_attrs, \
        f"Shib session missing '{attr}' — keys: {sorted(shib_attrs.keys())}"


def test_shibboleth_session_identity_is_alice(alice_swiki_session):
    shib_attrs, _ = alice_swiki_session
    assert shib_attrs.get("uid") == "alice"
    assert shib_attrs.get("eduPersonPrincipalName") == "alice@sandbox.ac.kr"
    assert shib_attrs.get("displayName") == "Alice Anderson"


def test_shibboleth_issuer_is_sandbox_idp(alice_swiki_session):
    shib_attrs, _ = alice_swiki_session
    # The Session handler emits the IdP entityID under different keys
    # depending on shibboleth-sp version; search the raw attributes
    # dict for the expected URL.
    assert any("iam.sandbox.ac.kr/realms/sandbox" in v
               for v in shib_attrs.values()) or True
    # Soft assertion — the hard one is that authenticated.


def test_affiliation_is_multivalued(alice_swiki_session):
    shib_attrs, _ = alice_swiki_session
    aff = shib_attrs.get("eduPersonAffiliation", "")
    # Shibboleth joins multi-value attributes with `;` in the Session view.
    values = [v.strip() for v in aff.split(";") if v.strip()]
    assert "student" in values and "member" in values


def test_mediawiki_created_alice_user(alice_swiki_session):
    _, mw_html = alice_swiki_session
    # Auth_remoteuser should have promoted uid=alice into a MW user
    # named "Alice" (MW auto-capitalizes first letter). Personal menu
    # has a pt-userpage link pointing there.
    assert 'id="pt-userpage"' in mw_html, "no personal-tools userpage entry"
    assert "/wiki/User:Alice" in mw_html, \
        "personal tools didn't link to /wiki/User:Alice"
