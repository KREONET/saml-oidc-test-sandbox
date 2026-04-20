#!/usr/bin/env bash
# Full teardown including volumes. Useful when Keycloak rejected an
# --import-realm pass (it only imports on an empty DB).
set -euo pipefail
docker compose --profile tools --profile tests down -v
echo "cleaned. next: docker compose up -d"
