<?php
/**
 * =============================================================================
 * api_keys.php — External API Keys Configuration (Shared PHP Backend)
 * =============================================================================
 *
 * Centralized configuration for all external API keys.
 * Reads from root .env file via PHP dotenv.
 *
 * Usage:
 *   require_once __DIR__ . '/api_keys.php';
 *   $key = getGoogleMapsApiKey();
 *
 * Environment variables consumed (from root .env):
 *   GOOGLE_MAPS_API_KEY
 *   GOOGLE_CLIENT_ID
 *   MIDTRANS_CLIENT_KEY
 *   BINDERBYTE_API_KEY
 */

// ── Load .env via PHP dotenv (composer require vlucas/phpdotenv) ──
// Falls back to getenv() if dotenv is not available (e.g., prod env vars).
$rootDir = dirname(__DIR__, 2); // project root (same level as .env)
$dotenvPath = $rootDir . '/.env';

if (file_exists($dotenvPath)) {
    try {
        if (class_exists('\Dotenv\Dotenv')) {
            $dotenv = \Dotenv\Dotenv::createImmutable($rootDir);
            $dotenv->load();
        }
    } catch (\Exception $e) {
        error_log('dotenv load warning: ' . $e->getMessage());
    }
}

/**
 * Read env var with fallback.
 */
function env($key, $default = '')
{
    $value = getenv($key);
    if ($value === false || $value === null) {
        return $default;
    }
    return $value;
}

// =============================================================================
// Google Maps API
// =============================================================================
define('GOOGLE_MAPS_API_KEY', env('GOOGLE_MAPS_API_KEY', ''));

function getGoogleMapsApiKey()
{
    return GOOGLE_MAPS_API_KEY;
}

// =============================================================================
// Google OAuth
// =============================================================================
define('GOOGLE_CLIENT_ID', env(
    'GOOGLE_CLIENT_ID',
    'your-google-client-id.apps.googleusercontent.com'
));
define('GOOGLE_CLIENT_SECRET', env('GOOGLE_CLIENT_SECRET', ''));

function getGoogleClientId()
{
    return GOOGLE_CLIENT_ID;
}

function getGoogleClientSecret()
{
    return GOOGLE_CLIENT_SECRET;
}

// =============================================================================
// Binderbyte — Indonesian Courier Tracking + Regional Data API
// =============================================================================
define('BINDERBYTE_API_KEY', env('BINDERBYTE_API_KEY', ''));
define('BINDERBYTE_BASE_URL', 'https://api.binderbyte.com/v1');

function getBinderbyteApiKey()
{
    return BINDERBYTE_API_KEY;
}

function getBinderbyteBaseUrl()
{
    return BINDERBYTE_BASE_URL;
}

// =============================================================================
// Midtrans Payment
// =============================================================================
define('MIDTRANS_CLIENT_KEY', env('MIDTRANS_CLIENT_KEY', ''));
define('MIDTRANS_SERVER_KEY', env('MIDTRANS_SERVER_KEY', ''));
define('MIDTRANS_MERCHANT_ID', env('MIDTRANS_MERCHANT_ID', ''));
define('MIDTRANS_IS_PRODUCTION', env('MIDTRANS_IS_PRODUCTION', 'false') === 'true');

function getMidtransClientKey()
{
    return MIDTRANS_CLIENT_KEY;
}

function getMidtransServerKey()
{
    return MIDTRANS_SERVER_KEY;
}

// =============================================================================
// Public API Keys (safe to expose to frontend)
// =============================================================================
function getPublicApiKeys()
{
    return [
        'google_maps_api_key' => GOOGLE_MAPS_API_KEY,
        'google_client_id' => GOOGLE_CLIENT_ID,
        'midtrans_client_key' => MIDTRANS_CLIENT_KEY,
        'binderbyte_api_key' => BINDERBYTE_API_KEY,
    ];
}

// =============================================================================
// Validation
// =============================================================================
function validateApiKeys()
{
    $warnings = [];

    if (empty(GOOGLE_MAPS_API_KEY)) {
        $warnings[] = 'GOOGLE_MAPS_API_KEY not configured. Maps will not load.';
    }
    if (empty(BINDERBYTE_API_KEY)) {
        $warnings[] = 'BINDERBYTE_API_KEY not configured. Tracking + wilayah fallback to mock.';
    }
    if (empty(MIDTRANS_CLIENT_KEY)) {
        $warnings[] = 'MIDTRANS_CLIENT_KEY not configured. Payments will not work.';
    }

    return $warnings;
}

// Log warnings in development
if (env('APP_ENV', 'development') === 'development') {
    $warnings = validateApiKeys();
    if (!empty($warnings)) {
        error_log('API Configuration Warnings: ' . json_encode($warnings));
    }
}
