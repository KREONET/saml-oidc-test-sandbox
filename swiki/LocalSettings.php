<?php
// KAFE Test Sandbox — MediaWiki LocalSettings (SAML SP via Shibboleth)
// Seeded by swiki-entrypoint.sh on first boot.

if ( !defined( 'MEDIAWIKI' ) ) { exit; }

// ─── site identity ────────────────────────────────────────────────
$wgSitename      = 'Sandbox Wiki (SAML)';
$wgMetaNamespace = 'Sandbox_Wiki';
$wgServer        = 'http://swiki.sandbox.ac.kr';
$wgScriptPath    = '';
$wgArticlePath   = '/wiki/$1';
$wgUsePathInfo   = true;

$wgResourceBasePath = $wgScriptPath;
$wgLogos = [ '1x' => null, 'icon' => null ];

// ─── database: SQLite for sandbox simplicity ──────────────────────
$wgDBtype        = 'sqlite';
$wgDBname        = 'swiki';
$wgSQLiteDataDir = '/var/www/html/data';

// ─── secrets (stable across restarts; DO NOT reuse in production) ──
$wgSecretKey  = 'swiki-dev-secret-key-do-not-reuse-000000000000000000000000000000000000';
$wgUpgradeKey = 'swiki-upgrade-key';
$wgAuthenticationTokenVersion = '1';

// ─── look-and-feel ────────────────────────────────────────────────
$wgDefaultSkin = 'vector-2022';
wfLoadSkin( 'Vector' );

// ─── permissions: require login to edit, allow anonymous read ─────
$wgGroupPermissions['*']['createaccount']    = false;
$wgGroupPermissions['*']['autocreateaccount'] = true;
$wgGroupPermissions['*']['read']             = true;
$wgGroupPermissions['*']['edit']             = false;
$wgGroupPermissions['user']['edit']          = true;

// ─── Auth_remoteuser: trust Apache/mod_shib's REMOTE_USER ─────────
wfLoadExtension( 'Auth_remoteuser' );

// mod_shib sets REMOTE_USER from the first of uid / eduPersonPrincipalName
// that appears in the assertion (see shibboleth2.xml REMOTE_USER attr).
$wgAuthRemoteuserUserName = static function () {
    return $_SERVER['REMOTE_USER'] ?? $_SERVER['HTTP_X_REMOTE_USER'] ?? '';
};

// Populate displayName + email from other Shib headers on account creation.
$wgAuthRemoteuserUserPrefs = static function () {
    $prefs = [];
    if ( !empty( $_SERVER['displayName'] ) ) {
        $prefs['realname'] = $_SERVER['displayName'];
    }
    if ( !empty( $_SERVER['mail'] ) ) {
        $prefs['email'] = $_SERVER['mail'];
    }
    return $prefs;
};

$wgAuthRemoteuserUserUrls = [ 'logout' => '/Shibboleth.sso/Logout?return=/' ];
$wgAuthRemoteuserAllowUserSwitch = false;
$wgAuthRemoteuserNotify = false;

// Sandbox debug: surface auth errors so the first-time reader sees why.
$wgShowExceptionDetails = true;
$wgDebugLogFile = '/tmp/mw-debug.log';
