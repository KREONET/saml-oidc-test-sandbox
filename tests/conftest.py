import os
import time

import httpx
import pytest


@pytest.fixture(scope="session")
def issuer():
    return os.environ["IDP_ISSUER"].rstrip("/")


@pytest.fixture(scope="session")
def discovery(issuer):
    url = f"{issuer}/.well-known/openid-configuration"
    deadline = time.time() + 90
    last = None
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=5)
            if r.status_code == 200:
                return r.json()
            last = r
        except httpx.HTTPError as e:
            last = e
        time.sleep(2)
    pytest.fail(f"discovery not ready after 90s: {last!r}")


@pytest.fixture(scope="session")
def rp_cli_secret():
    return os.environ["RP_CLI_SECRET"]


@pytest.fixture(scope="session")
def claim_inspector_secret():
    return os.environ["CLAIM_INSPECTOR_SECRET"]


@pytest.fixture(scope="session")
def saml_idp_descriptor_url(issuer):
    return f"{issuer}/protocol/saml/descriptor"


@pytest.fixture(scope="session")
def stest_base_url():
    return os.environ.get("STEST_URL", "http://stest.sandbox.ac.kr")
