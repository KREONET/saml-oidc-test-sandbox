FROM mediawiki:1.43

# ─── system deps: Shibboleth SP, Apache mods, sqlite ──────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        libapache2-mod-shib \
        shibboleth-sp-utils \
        curl \
        ca-certificates \
        sqlite3 \
        sudo \
        xsltproc \
    && rm -rf /var/lib/apt/lists/*

# Apache modules MediaWiki pretty URLs + Shibboleth + required helpers
RUN a2enmod rewrite headers

# ─── MediaWiki extension: Auth_remoteuser ────────────────────────
# Reads REMOTE_USER + Shib-* env vars set by mod_shib and maps to an
# automatically-created MediaWiki user — the whole SAML dance lives
# outside PHP, so there is no SimpleSAMLphp↔MediaWiki session clash.
WORKDIR /var/www/html/extensions
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && git clone --branch REL1_43 --depth 1 \
        https://gerrit.wikimedia.org/r/mediawiki/extensions/Auth_remoteuser Auth_remoteuser \
    && rm -rf Auth_remoteuser/.git \
    && apt-get purge -y git \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# ─── Shibboleth SP config ─────────────────────────────────────────
COPY shib-config/shibboleth2.xml /etc/shibboleth/shibboleth2.xml
COPY shib-config/attribute-map.xml /etc/shibboleth/attribute-map.xml
COPY shib-config/attribute-policy.xml /etc/shibboleth/attribute-policy.xml
COPY shib-keys/sp-cert.pem /etc/shibboleth/sp-cert.pem
COPY shib-keys/sp-key.pem /etc/shibboleth/sp-key.pem
RUN chown _shibd:_shibd /etc/shibboleth/sp-key.pem \
    && chmod 600 /etc/shibboleth/sp-key.pem

# ─── Apache conf: enable mod_shib + protect locations ────────────
COPY apache-conf/shib.conf /etc/apache2/conf-available/shib.conf
RUN a2enconf shib

# ─── MediaWiki LocalSettings + entrypoint ─────────────────────────
WORKDIR /var/www/html
COPY LocalSettings.php /tmp/LocalSettings.php.template
COPY entrypoint.sh /usr/local/bin/swiki-entrypoint.sh
RUN chmod +x /usr/local/bin/swiki-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/swiki-entrypoint.sh"]
CMD ["apache2-foreground"]
