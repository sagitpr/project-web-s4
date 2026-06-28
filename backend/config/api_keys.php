<?php
/**
 * =============================================================================
 * api_keys.php — External API Keys Configuration
 * =============================================================================
 *
 * Centralized configuration for all external API keys.
 * Reads from .env file for security.
 *
 * Usage:
 *   require_once __DIR__ . '/api_keys.php';
 *   echo getGoogleMapsApiKey();
 *
 * Environment variables consumed (from root .env):
 *   GOOGLE_MAPS_API_KEY
 *   GOOGLE_CLIENT_ID
 *   MIDTRANS_CLIENT_KEY
 *   etc.
 */

// Ensure env() helper is available
require_once __DIR__ . '/function.php';

// =============================================================================
// Google Maps API
// =============================================================================

define('GOOGLE_MAPS_API_KEY', env(
    'GOOGLE_MAPS_API_KEY',
    'AIzaSyBXr9qOQ5DfcxG-tH288SE9tpdJ5ty7S4I' // Default dev key
));

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

define('GOOGLE_CLIENT_SECRET', env(
    'GOOGLE_CLIENT_SECRET',
    ''
));

function getGoogleClientId()
{
    return GOOGLE_CLIENT_ID;
}

function getGoogleClientSecret()
{
    return GOOGLE_CLIENT_SECRET;
}

// =============================================================================
// Midtrans Payment
// =============================================================================

define('MIDTRANS_CLIENT_KEY', env(
    'MIDTRANS_CLIENT_KEY',
    ''
));

define('MIDTRANS_SERVER_KEY', env(
    'MIDTRANS_SERVER_KEY',
    ''
));

define('MIDTRANS_MERCHANT_ID', env(
    'MIDTRANS_MERCHANT_ID',
    ''
));

define('MIDTRANS_IS_PRODUCTION', env(
    'MIDTRANS_IS_PRODUCTION',
    'false'
) === 'true');

function getMidtransClientKey()
{
    return MIDTRANS_CLIENT_KEY;
}

function getMidtransServerKey()
{
    return MIDTRANS_SERVER_KEY;
}

// =============================================================================
// Helper: Get all API keys (for AJAX endpoints or JSON output)
// =============================================================================

function getPublicApiKeys()
{
    return [
        'google_maps_api_key' => GOOGLE_MAPS_API_KEY,
        'google_client_id' => GOOGLE_CLIENT_ID,
        'midtrans_client_key' => MIDTRANS_CLIENT_KEY,
    ];
}

// =============================================================================
// Validation
// =============================================================================

function validateApiKeys()
{
    $warnings = [];

    if (GOOGLE_MAPS_API_KEY === 'AIzaSyBXr9qOQ5DfcxG-tH288SE9tpdJ5ty7S4I') {
        $warnings[] = 'GOOGLE_MAPS_API_KEY is using default dev key. Set GOOGLE_MAPS_API_KEY in .env for production.';
    }

    if (empty(GOOGLE_CLIENT_ID) || GOOGLE_CLIENT_ID === 'your-google-client-id.apps.googleusercontent.com') {
        $warnings[] = 'GOOGLE_CLIENT_ID not configured. Set GOOGLE_CLIENT_ID in .env.';
    }

    if (empty(MIDTRANS_CLIENT_KEY)) {
        $warnings[] = 'MIDTRANS_CLIENT_KEY not configured. Set MIDTRANS_CLIENT_KEY in .env.';
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
