#!/usr/bin/env bash
# Adds sandbox.ac.kr subdomains to /etc/hosts so the browser and RPs can
# reach the sandbox stack by name. Idempotent.
#
# Subdomain convention:
#   iam.*    — IdP (Keycloak)
#   o*.*     — OIDC-facing apps (otest, owiki)
#   s*.*     — SAML-facing apps (stest, swiki — added when SAML support lands)
set -euo pipefail

HOSTS_FILE="/etc/hosts"
MARKER="# oidc-test-sandbox"
ENTRIES=(
    "127.0.0.1 iam.sandbox.ac.kr"
    "127.0.0.1 otest.sandbox.ac.kr"
    "127.0.0.1 owiki.sandbox.ac.kr"
    "127.0.0.1 stest.sandbox.ac.kr"
    "127.0.0.1 swiki.sandbox.ac.kr"
)

if [[ $EUID -ne 0 ]]; then
    echo "this script edits /etc/hosts — rerun with sudo." >&2
    exit 1
fi

if grep -q "$MARKER" "$HOSTS_FILE"; then
    echo "already present — nothing to do."
    exit 0
fi

{
    echo ""
    echo "$MARKER (do not remove this marker line)"
    for e in "${ENTRIES[@]}"; do echo "$e"; done
} >> "$HOSTS_FILE"

echo "added:"
printf '  %s\n' "${ENTRIES[@]}"
echo "remove with:  sudo sed -i.bak '/$MARKER/,+${#ENTRIES[@]}d' $HOSTS_FILE"
