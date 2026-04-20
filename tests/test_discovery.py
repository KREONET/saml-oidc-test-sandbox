REQUIRED_FIELDS = {
    "issuer",
    "authorization_endpoint",
    "token_endpoint",
    "userinfo_endpoint",
    "jwks_uri",
    "response_types_supported",
    "subject_types_supported",
    "id_token_signing_alg_values_supported",
    "scopes_supported",
    "claims_supported",
}

# Keycloak's discovery publishes only a curated set of builtin claims in
# `claims_supported`; custom mappers (eduPerson*, schac*, o, ou, isMemberOf)
# are reachable via /userinfo but are not auto-advertised here, and
# even `email_verified` is omitted by Keycloak 26. We assert only the
# subset Keycloak actually advertises, and rely on
# test_claims_distribution.py to verify the custom claims flow.
BUILTIN_CLAIMS_ADVERTISED = {
    "sub", "preferred_username",
    "email",
    "name", "given_name", "family_name",
}


def test_required_discovery_fields(discovery):
    missing = REQUIRED_FIELDS - discovery.keys()
    assert not missing, f"missing discovery fields: {missing}"


def test_builtin_claims_advertised(discovery):
    supported = set(discovery.get("claims_supported", []))
    missing = BUILTIN_CLAIMS_ADVERTISED - supported
    assert not missing, f"claims_supported missing builtin claims: {missing}"


def test_kafe_profile_scope_present(discovery):
    assert "oidc-kafe-profile" in discovery.get("scopes_supported", [])
