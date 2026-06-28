<?php

// =============================================================================
// Environment Variables (.env loader)
// =============================================================================

function loadEnv($path = null)
{
    if ($path === null) {
        // Load from project root .env (single source of truth)
        $path = __DIR__ . '/../../.env';
        
        // Fallback: try backend/.env if root .env doesn't exist
        if (!file_exists($path)) {
            $path = __DIR__ . '/../.env';
        }
    }

    if (!file_exists($path)) {
        return;
    }

    $lines = file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($lines as $line) {
        $line = trim($line);
        if (strpos($line, '#') === 0 || strpos($line, '=') === false) {
            continue;
        }
        list($key, $value) = explode('=', $line, 2);
        $key = trim($key);
        $value = trim($value);
        if (strlen($value) > 1 && in_array($value[0], ['"', "'"]) && $value[0] === $value[strlen($value) - 1]) {
            $value = substr($value, 1, -1);
        }
        putenv("$key=$value");
        $_ENV[$key] = $value;
    }
}

function env($key, $default = null)
{
    $value = getenv($key);
    return ($value === false || $value === null) ? $default : $value;
}

// Load environment variables immediately
loadEnv();

// =============================================================================
// Session Security
// =============================================================================

function initSecureSession()
{
    if (session_status() === PHP_SESSION_NONE) {
        // Set secure session cookie parameters
        session_set_cookie_params([
            'lifetime' => 86400 * 7, // 7 days
            'path' => '/',
            'domain' => '',
            'secure' => false, // Set to true when HTTPS is enabled
            'httponly' => true,
            'samesite' => 'Lax',
        ]);
        session_start();
    }

    // Regenerate session ID periodically to prevent fixation
    if (!isset($_SESSION['_last_regenerated'])) {
        $_SESSION['_last_regenerated'] = time();
    } elseif (time() - $_SESSION['_last_regenerated'] > 1800) { // Every 30 minutes
        session_regenerate_id(true);
        $_SESSION['_last_regenerated'] = time();
    }
}

// CSRF Token functions
function generateCsrfToken()
{
    if (empty($_SESSION['_csrf_token'])) {
        $_SESSION['_csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['_csrf_token'];
}

function getCsrfToken()
{
    return $_SESSION['_csrf_token'] ?? '';
}

function validateCsrfToken($token)
{
    if (empty($_SESSION['_csrf_token']) || empty($token)) {
        return false;
    }
    return hash_equals($_SESSION['_csrf_token'], $token);
}

function requireCsrfToken()
{
    $token = $_POST['_csrf_token'] ?? $_SERVER['HTTP_X_CSRF_TOKEN'] ?? '';
    if (!validateCsrfToken($token)) {
        http_response_code(403);
        die('CSRF token tidak valid. Silakan refresh halaman dan coba lagi.');
    }
}

// Rate Limiting
function checkRateLimit($action, $maxAttempts = 5, $windowMinutes = 15)
{
    $key = '_rate_limit_' . $action;
    $now = time();

    // Initialize rate limit tracking
    if (!isset($_SESSION[$key])) {
        $_SESSION[$key] = [];
    }

    // Remove expired attempts
    $_SESSION[$key] = array_filter(
        $_SESSION[$key],
        function ($timestamp) use ($now, $windowMinutes) {
            return $timestamp > $now - ($windowMinutes * 60);
        }
    );

    // Check if over limit
    if (count($_SESSION[$key]) >= $maxAttempts) {
        return false; // Rate limit exceeded
    }

    // Record attempt
    $_SESSION[$key][] = $now;
    return true; // OK to proceed
}

function isLoggedIn()
{
    return isset($_SESSION['user_id']);
}
function isBuyer()
{
    return isset($_SESSION['role']) && $_SESSION['role'] == 'buyer';
}
function isSeller()
{
    return isset($_SESSION['role']) && $_SESSION['role'] == 'seller';
}
function isAdmin()
{
    return isset($_SESSION['role']) && $_SESSION['role'] == 'admin';
}

function redirect($url)
{
    header("Location: $url");
    exit;
}
