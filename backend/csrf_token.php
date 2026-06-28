<?php
/**
 * CSRF Token API Endpoint
 * Returns the current CSRF token as JSON for static HTML pages.
 * Called via fetch() from frontend JavaScript.
 */
require_once __DIR__ . '/config/function.php';
initSecureSession();
header('Content-Type: application/json');
echo json_encode(['token' => getCsrfToken()]);
