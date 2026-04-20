"""otest.sandbox.ac.kr — OIDC claim inspector.

Renders ID token claims vs userinfo claims side by side so you can see
the P3 contract (ID token minimal / userinfo full) in action.
"""
import base64
import json
import os
import secrets
from urllib.parse import urlencode

import httpx
from flask import Flask, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]

ISSUER = os.environ["OIDC_ISSUER"].rstrip("/")
CLIENT_ID = os.environ["OIDC_CLIENT_ID"]
CLIENT_SECRET = os.environ["OIDC_CLIENT_SECRET"]
REDIRECT_URI = os.environ["OIDC_REDIRECT_URI"]
SCOPES = os.environ.get("OIDC_SCOPES", "openid profile email oidc-kafe-profile")


def discovery():
    if "_discovery" not in app.config:
        r = httpx.get(f"{ISSUER}/.well-known/openid-configuration", timeout=10)
        r.raise_for_status()
        app.config["_discovery"] = r.json()
    return app.config["_discovery"]


def b64url_decode(s: str) -> bytes:
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode())


def decode_jwt_payload(jwt_str: str) -> dict:
    try:
        _, payload, _ = jwt_str.split(".")
        return json.loads(b64url_decode(payload))
    except Exception as e:
        return {"_error": f"decode failed: {e}"}


def pkce_pair():
    verifier = secrets.token_urlsafe(64)
    import hashlib
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


@app.route("/")
def index():
    user = session.get("userinfo")
    return render_template("index.html", user=user, issuer=ISSUER, client_id=CLIENT_ID)


@app.route("/login")
def login():
    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)
    verifier, challenge = pkce_pair()
    session["oauth_state"] = state
    session["oauth_nonce"] = nonce
    session["oauth_verifier"] = verifier

    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return redirect(f"{discovery()['authorization_endpoint']}?{urlencode(params)}")


@app.route("/callback")
def callback():
    if request.args.get("state") != session.get("oauth_state"):
        return "state mismatch", 400

    code = request.args.get("code")
    if not code:
        return f"error: {request.args.get('error')} — {request.args.get('error_description')}", 400

    token_r = httpx.post(
        discovery()["token_endpoint"],
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code_verifier": session.pop("oauth_verifier", ""),
        },
        timeout=10,
    )
    if token_r.status_code != 200:
        return f"token exchange failed: {token_r.status_code} {token_r.text}", 400
    tokens = token_r.json()

    id_token_claims = decode_jwt_payload(tokens["id_token"])
    access_token_claims = decode_jwt_payload(tokens["access_token"])

    ui_r = httpx.get(
        discovery()["userinfo_endpoint"],
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        timeout=10,
    )
    userinfo = ui_r.json() if ui_r.status_code == 200 else {"_error": ui_r.text}

    session["id_token"] = tokens["id_token"]
    session["refresh_token"] = tokens.get("refresh_token")
    session["id_claims"] = id_token_claims
    session["access_claims"] = access_token_claims
    session["userinfo"] = userinfo
    return redirect(url_for("me"))


@app.route("/me")
def me():
    if "userinfo" not in session:
        return redirect(url_for("index"))

    id_claims = session.get("id_claims", {})
    at_claims = session.get("access_claims", {})
    userinfo = session.get("userinfo", {})

    all_keys = sorted(set(id_claims.keys()) | set(userinfo.keys()) | set(at_claims.keys()))
    protocol_keys = {
        "iss", "aud", "azp", "exp", "iat", "nbf", "jti", "sub",
        "sid", "nonce", "auth_time", "acr", "amr", "typ", "scope",
        "session_state", "at_hash", "c_hash", "allowed-origins",
        "resource_access", "realm_access",
    }
    rows = []
    for k in all_keys:
        rows.append({
            "name": k,
            "is_protocol": k in protocol_keys,
            "in_id": k in id_claims,
            "in_userinfo": k in userinfo,
            "in_access": k in at_claims,
            "id_value": id_claims.get(k, "—"),
            "userinfo_value": userinfo.get(k, "—"),
        })

    return render_template(
        "me.html",
        rows=rows,
        id_claims=id_claims,
        at_claims=at_claims,
        userinfo=userinfo,
    )


@app.route("/me.json")
def me_json():
    return {
        "id_token_claims": session.get("id_claims", {}),
        "access_token_claims": session.get("access_claims", {}),
        "userinfo": session.get("userinfo", {}),
    }


@app.route("/logout", methods=["GET", "POST"])
def logout():
    id_token = session.get("id_token")
    session.clear()
    params = {"post_logout_redirect_uri": request.host_url.rstrip("/") + "/"}
    if id_token:
        params["id_token_hint"] = id_token
    return redirect(f"{discovery()['end_session_endpoint']}?{urlencode(params)}")


@app.route("/healthz")
def healthz():
    return {"ok": True}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
