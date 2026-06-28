<?php
require_once __DIR__ . '/config/db.php';

if (function_exists('initSecureSession')) {
    initSecureSession();
} else {
    session_start();
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Location: ../auth/otp/index.html');
    exit();
}

// Validate CSRF token
if (function_exists('requireCsrfToken')) {
    requireCsrfToken();
}

// Rate limiting: max 10 OTP attempts per 15 minutes
if (function_exists('checkRateLimit') && !checkRateLimit('verify_otp', 10, 15)) {
    header('Location: ../auth/otp/index.html?error=rate_limit');
    exit();
}

$identifier = trim($_POST['identifier'] ?? '');
$otp = trim($_POST['otp'] ?? '');

if ($identifier === '' || $otp === '') {
    header('Location: ../auth/otp/index.html?error=1&identifier=' . urlencode($identifier));
    exit();
}

try {
    $pdo = getDbConnection();
    $stmt = $pdo->prepare('SELECT id, full_name, email FROM users WHERE (email = ? OR phone = ?) AND otp = ? AND otp_expires >= NOW() LIMIT 1');
    $stmt->execute([$identifier, $identifier, $otp]);
    $user = $stmt->fetch();

    if (!$user) {
        header('Location: ../auth/otp/index.html?error=1&identifier=' . urlencode($identifier));
        exit();
    }

    $update = $pdo->prepare('UPDATE users SET is_verified = 1, otp = NULL, otp_expires = NULL WHERE id = ?');
    $update->execute([$user['id']]);

    if (isset($_SESSION['pending_login_user_id']) && (int) $_SESSION['pending_login_user_id'] === (int) $user['id']) {
        $_SESSION['user_id'] = $user['id'];
        $_SESSION['user_name'] = $_SESSION['pending_login_user_name'] ?? $user['full_name'];
        $_SESSION['user_email'] = $_SESSION['pending_login_user_email'] ?? $user['email'];

        unset($_SESSION['pending_login_user_id'], $_SESSION['pending_login_user_name'], $_SESSION['pending_login_user_email']);

        header('Location: ../home/index.php');
        exit();
    }

    header('Location: ../auth/login/index.html?verified=1');
    exit();
} catch (PDOException $e) {
    header('Location: ../auth/otp/index.html?error=1&identifier=' . urlencode($identifier));
    exit();
}
