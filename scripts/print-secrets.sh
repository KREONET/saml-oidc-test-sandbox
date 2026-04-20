#!/usr/bin/env bash
# Prints each confidential client's secret. Reads them from the running
# Keycloak via kcadm.sh inside the container — not from import.json —
# so it reflects the actual state after any manual rotation.
set -euo pipefail

COMPOSE="${COMPOSE:-docker compose}"
ADMIN_USER="${KEYCLOAK_ADMIN:-admin}"
ADMIN_PASS="${KEYCLOAK_ADMIN_PASSWORD:-admin}"
REALM="sandbox"

CLIENTS=$($COMPOSE exec -T iam-app /opt/keycloak/bin/kcadm.sh get clients \
    -r "$REALM" --fields clientId --format csv --noquotes)

printf '%-20s  %s\n' "CLIENT_ID" "SECRET"
printf '%-20s  %s\n' "--------------------" "--------------------------------"

for c in $CLIENTS; do
    # Only try to get secret for clients that might have one (filter out standard console clients if needed)
    # We'll just try to get it, and if it fails, we skip
    id=$($COMPOSE exec -T iam-app /opt/keycloak/bin/kcadm.sh get clients \
        -r "$REALM" -q "clientId=$c" --fields id --format csv --noquotes | tail -n1)

    # Try to fetch secret, suppress stderr because public clients don't have secrets
    secret=$($COMPOSE exec -T iam-app /opt/keycloak/bin/kcadm.sh get "clients/$id/client-secret" \
        -r "$REALM" --fields value --format csv --noquotes 2>/dev/null | tail -n1)
    
    if [[ -n "$secret" ]]; then
        printf '%-20s  %s\n' "$c" "$secret"
    fi
done
