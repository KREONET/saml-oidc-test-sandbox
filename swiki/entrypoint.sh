#!/usr/bin/env bash
# MediaWiki (sqlite) + Shibboleth SP seed script. First boot installs
# MediaWiki as www-data, swaps in the pre-baked LocalSettings.php,
# then brings up shibd and chains to Apache.
set -euo pipefail

MW_ROOT=/var/www/html
DATA_DIR=$MW_ROOT/data
LS=$MW_ROOT/LocalSettings.php

mkdir -p "$DATA_DIR"
chown -R www-data:www-data "$DATA_DIR"
chmod 755 "$DATA_DIR"

if [[ ! -f "$LS" ]]; then
    if [[ -f "$DATA_DIR/swiki.sqlite" ]]; then
        # Image was rebuilt but the swiki-data volume persisted. The DB
        # already has all MediaWiki tables; re-running install.php would
        # collide on "CREATE TABLE ... already exists". Just re-seed
        # LocalSettings.php from the image and run update.php for any
        # new extension tables.
        echo "[swiki-entrypoint] existing sqlite DB found in volume, skipping install"
        cp /tmp/LocalSettings.php.template "$LS"
        chown www-data:www-data "$LS"
        sudo -u www-data -E php "$MW_ROOT/maintenance/update.php" --quick
    else
        echo "[swiki-entrypoint] first boot: installing MediaWiki (sqlite)..."
        sudo -u www-data -E php "$MW_ROOT/maintenance/install.php" \
            --dbtype=sqlite \
            --dbname=swiki \
            --dbpath="$DATA_DIR" \
            --server="http://swiki.sandbox.ac.kr" \
            --scriptpath="" \
            --lang=en \
            --pass="SandboxAdmin2026!" \
            --installdbuser=root \
            "Sandbox Wiki (SAML)" \
            "WikiAdmin"

        echo "[swiki-entrypoint] seeding LocalSettings.php"
        cp /tmp/LocalSettings.php.template "$LS"
        chown www-data:www-data "$LS"

        echo "[swiki-entrypoint] running update.php for Auth_remoteuser tables"
        sudo -u www-data -E php "$MW_ROOT/maintenance/update.php" --quick
    fi
fi

chown -R www-data:www-data "$DATA_DIR"

# ─── Wait for Keycloak so shibd's MetadataProvider can fetch on start ─
# Hit via nginx (port 80) — see note in shibboleth2.xml.
IDP_DESCRIPTOR="http://iam.sandbox.ac.kr/realms/sandbox/protocol/saml/descriptor"
for attempt in $(seq 1 30); do
    if curl -fsS --max-time 5 "$IDP_DESCRIPTOR" >/dev/null 2>&1; then
        echo "[swiki-entrypoint] Keycloak SAML descriptor reachable (attempt $attempt)"
        break
    fi
    echo "[swiki-entrypoint] waiting for Keycloak IdP metadata (attempt $attempt)"
    sleep 2
done

# ─── Start shibd in the background ────────────────────────────────
echo "[swiki-entrypoint] starting shibd"
mkdir -p /var/run/shibboleth /var/log/shibboleth /var/cache/shibboleth
chown -R _shibd:_shibd /var/run/shibboleth /var/log/shibboleth /var/cache/shibboleth \
    /etc/shibboleth 2>/dev/null || true

/usr/sbin/shibd -f -p /var/run/shibboleth/shibd.pid -F &
SHIBD_PID=$!

# Wait a moment for shibd to open its socket before Apache's mod_shib
# tries to connect (otherwise every first request 500s).
for attempt in $(seq 1 20); do
    if [[ -S /var/run/shibboleth/shibd.sock ]] || [[ -S /run/shibboleth/shibd.sock ]]; then
        echo "[swiki-entrypoint] shibd socket ready"
        break
    fi
    sleep 0.5
done

# Forward shibd exit to container exit if it dies.
trap 'kill -TERM "$SHIBD_PID" 2>/dev/null || true' TERM INT

exec "$@"
