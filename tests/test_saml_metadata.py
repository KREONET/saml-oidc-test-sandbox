"""SAML metadata regression.

The sandbox IdP is supposed to publish a stable SAML 2.0 descriptor
alongside its OIDC discovery document; likewise the stest-app SP must
advertise an SPSSODescriptor with signed-request + POST ACS + persistent
NameID support. These are the hard shape checks — attribute content
flows through test_saml_attributes.py.
"""
from xml.etree import ElementTree as ET

import httpx
import pytest

NS = {
    "md": "urn:oasis:names:tc:SAML:2.0:metadata",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}


@pytest.fixture(scope="session")
def idp_metadata_xml(saml_idp_descriptor_url):
    r = httpx.get(saml_idp_descriptor_url, timeout=10)
    assert r.status_code == 200, r.text
    return ET.fromstring(r.text)


@pytest.fixture(scope="session")
def sp_metadata_xml(stest_base_url):
    r = httpx.get(f"{stest_base_url}/metadata", timeout=10)
    assert r.status_code == 200, r.text
    return ET.fromstring(r.text)


def test_idp_entity_id_matches_issuer(idp_metadata_xml, issuer):
    assert idp_metadata_xml.get("entityID") == issuer


def test_idp_advertises_idp_sso_descriptor(idp_metadata_xml):
    desc = idp_metadata_xml.find("md:IDPSSODescriptor", NS)
    assert desc is not None, "IDPSSODescriptor missing"
    assert desc.get("WantAuthnRequestsSigned") == "true", \
        "IdP should require signed AuthnRequests (realm-level setting)"


def test_idp_has_sso_endpoints_for_both_bindings(idp_metadata_xml):
    desc = idp_metadata_xml.find("md:IDPSSODescriptor", NS)
    bindings = {e.get("Binding") for e in desc.findall("md:SingleSignOnService", NS)}
    assert "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" in bindings
    assert "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect" in bindings


def test_idp_advertises_persistent_nameid_format(idp_metadata_xml):
    desc = idp_metadata_xml.find("md:IDPSSODescriptor", NS)
    formats = {e.text for e in desc.findall("md:NameIDFormat", NS)}
    assert "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent" in formats


def test_sp_entity_id_is_stable(sp_metadata_xml):
    assert sp_metadata_xml.get("entityID") == "http://stest.sandbox.ac.kr/metadata"


def test_sp_requires_signed_assertions(sp_metadata_xml):
    desc = sp_metadata_xml.find("md:SPSSODescriptor", NS)
    assert desc is not None
    assert desc.get("AuthnRequestsSigned") == "true"
    assert desc.get("WantAssertionsSigned") == "true"


def test_sp_has_post_acs(sp_metadata_xml):
    desc = sp_metadata_xml.find("md:SPSSODescriptor", NS)
    acs_list = desc.findall("md:AssertionConsumerService", NS)
    post_acs = [e for e in acs_list
                if e.get("Binding") == "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"]
    assert post_acs, "SP must expose a POST-binding AssertionConsumerService"
    assert post_acs[0].get("Location") == "http://stest.sandbox.ac.kr/acs"
