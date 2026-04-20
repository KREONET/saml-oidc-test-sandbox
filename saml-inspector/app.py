"""stest.sandbox.ac.kr — SAML 2.0 Assertion Inspector.

Mirrors the OIDC `otest-app` but for SAML: shows the parsed AuthnResponse
(NameID, SubjectConfirmation, AttributeStatement, SessionIndex,
AuthnContext) side-by-side with the raw assertion XML so the SAML
↔ OIDC attribute parity is observable at a glance.
"""
import base64
import logging
import os
import threading

from flask import Flask, redirect, render_template, request, session, url_for
from saml2 import BINDING_HTTP_POST, BINDING_HTTP_REDIRECT
from saml2.client import Saml2Client
from saml2.config import SPConfig

log = logging.getLogger("saml-inspector")

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]

IDP_METADATA_URL = os.environ["IDP_METADATA_URL"]
SP_ENTITY_ID = os.environ.get("SP_ENTITY_ID", "http://stest.sandbox.ac.kr/metadata")
SP_BASE_URL = os.environ.get("SP_BASE_URL", "http://stest.sandbox.ac.kr")
SP_KEY_FILE = os.environ.get("SP_KEY_FILE", "/app/keys/sp.key")
SP_CERT_FILE = os.environ.get("SP_CERT_FILE", "/app/keys/sp.crt")

_client: Saml2Client | None = None
_client_lock = threading.Lock()


def _build_config() -> SPConfig:
    cfg = SPConfig()
    cfg.load({
        "entityid": SP_ENTITY_ID,
        "description": "KAFE Test Sandbox — SAML Assertion Inspector",
        "service": {
            "sp": {
                "endpoints": {
                    "assertion_consumer_service": [
                        (f"{SP_BASE_URL}/acs", BINDING_HTTP_POST),
                    ],
                    "single_logout_service": [
                        (f"{SP_BASE_URL}/slo", BINDING_HTTP_REDIRECT),
                    ],
                },
                "allow_unsolicited": True,
                "authn_requests_signed": True,
                "logout_requests_signed": True,
                "want_assertions_signed": True,
                "want_response_signed": False,
                "name_id_format": [
                    "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent",
                ],
            },
        },
        "metadata": {
            "remote": [{"url": IDP_METADATA_URL}],
        },
        "key_file": SP_KEY_FILE,
        "cert_file": SP_CERT_FILE,
        "xmlsec_binary": "/usr/bin/xmlsec1",
        "allow_unknown_attributes": True,
        "accepted_time_diff": 60,
    })
    return cfg


def get_client() -> Saml2Client:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = Saml2Client(config=_build_config())
    return _client


@app.route("/")
def index():
    user = session.get("ava")
    return render_template(
        "index.html",
        user=user,
        entity_id=SP_ENTITY_ID,
        idp_metadata_url=IDP_METADATA_URL,
    )


@app.route("/metadata")
def metadata():
    from saml2.metadata import entity_descriptor
    cfg = _build_config()
    md = entity_descriptor(cfg)
    return str(md), 200, {"Content-Type": "application/samlmetadata+xml"}


@app.route("/login")
def login():
    client = get_client()
    reqid, info = client.prepare_for_authenticate(
        entityid=None,
        relay_state="/me",
        binding=BINDING_HTTP_REDIRECT,
    )
    session["authn_request_id"] = reqid
    headers = dict(info["headers"])
    return redirect(headers["Location"], code=302)


@app.route("/acs", methods=["POST"])
def acs():
    saml_response = request.form.get("SAMLResponse")
    if not saml_response:
        return "missing SAMLResponse", 400
    client = get_client()
    try:
        authn_response = client.parse_authn_request_response(
            saml_response,
            BINDING_HTTP_POST,
            outstanding={session.get("authn_request_id"): "/me"} if session.get("authn_request_id") else None,
        )
    except Exception as e:
        log.exception("assertion parse failed")
        return f"assertion parse failed: {e}", 400

    if authn_response is None:
        return "authn_response is None (signature/validation failure)", 400

    ava = authn_response.ava or {}
    name_id = authn_response.name_id
    assertion = authn_response.assertion

    session["ava"] = ava
    session["name_id"] = {
        "format": getattr(name_id, "format", None),
        "text": getattr(name_id, "text", None),
        "sp_name_qualifier": getattr(name_id, "sp_name_qualifier", None),
        "name_qualifier": getattr(name_id, "name_qualifier", None),
    }
    authn_stmt = assertion.authn_statement[0] if assertion.authn_statement else None
    session["session_index"] = getattr(authn_stmt, "session_index", None) if authn_stmt else None
    try:
        authn_context_class_ref = (
            authn_stmt.authn_context.authn_context_class_ref.text
            if authn_stmt and authn_stmt.authn_context
            else None
        )
    except AttributeError:
        authn_context_class_ref = None
    session["authn_context_class_ref"] = authn_context_class_ref
    session["assertion_xml"] = str(assertion)
    iss = authn_response.issuer()
    session["issuer"] = iss if isinstance(iss, str) else getattr(iss, "text", None)

    relay_state = request.form.get("RelayState", "/me")
    if not relay_state.startswith("/"):
        relay_state = "/me"
    return redirect(relay_state)


@app.route("/me")
def me():
    if "ava" not in session:
        return redirect(url_for("index"))
    return render_template(
        "me.html",
        ava=session.get("ava", {}),
        name_id=session.get("name_id", {}),
        session_index=session.get("session_index"),
        authn_context_class_ref=session.get("authn_context_class_ref"),
        assertion_xml=session.get("assertion_xml", ""),
        issuer=session.get("issuer"),
    )


@app.route("/me.json")
def me_json():
    return {
        "ava": session.get("ava", {}),
        "name_id": session.get("name_id", {}),
        "session_index": session.get("session_index"),
        "authn_context_class_ref": session.get("authn_context_class_ref"),
        "issuer": session.get("issuer"),
    }


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/healthz")
def healthz():
    return {"ok": True}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
