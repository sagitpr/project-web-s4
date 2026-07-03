<?php
require_once __DIR__ . '/config/db.php';

if (function_exists('initSecureSession')) {
    initSecureSession();
} else {
    session_start();
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Location: ../auth/reset-password/index.html');
    exit();
}

// Validate CSRF token
if (function_exists('requireCsrfToken')) {
    requireCsrfToken();
}

// Rate limiting: max 5 reset attempts per 15 minutes
if (function_exists('checkRateLimit') && !checkRateLimit('reset_password', 5, 15)) {
    header('Location: ../auth/reset-password/index.html?error=rate_limit');
    exit();
}

$identifier = trim($_POST['identifier'] ?? '');
$otpDigits = [];
for ($i = 1; $i <= 6; $i++) {
    $otpDigits[] = trim($_POST['otp_digit_' . $i] ?? '');
}
$otp = implode('', $otpDigits);
$newPassword = trim($_POST['new_password'] ?? '');
$confirmPassword = trim($_POST['confirm_password'] ?? '');

if ($identifier === '' || strlen($otp) !== 6 || $newPassword === '' || $confirmPassword === '') {
    header('Location: ../auth/reset-password/index.html?step=verify&identifier=' . urlencode($identifier) . '&error=1');
    exit();
}

if ($newPassword !== $confirmPassword) {
    header('Location: ../auth/reset-password/index.html?step=verify&identifier=' . urlencode($identifier) . '&error=2');
    exit();
}

try {
    $pdo = getDbConnection();
    $stmt = $pdo->prepare('SELECT id FROM users WHERE (email = ? OR phone = ?) AND otp = ? AND otp_expires >= NOW() LIMIT 1');
    $stmt->execute([$identifier, $identifier, $otp]);
    $user = $stmt->fetch();

    if (!$user) {
        header('Location: ../auth/reset-password/index.html?step=verify&identifier=' . urlencode($identifier) . '&error=3');
        exit();
    }

    $passwordHash = password_hash($newPassword, PASSWORD_DEFAULT);
    $update = $pdo->prepare('UPDATE users SET password_hash = ?, otp = NULL, otp_expires = NULL WHERE id = ?');
    $update->execute([$passwordHash, $user['id']]);

    header('Location: ../auth/login/index.html?reset=success');
    exit();
} catch (Throwable $e) {
    header('Location: ../auth/reset-password/index.html?step=verify&identifier=' . urlencode($identifier) . '&error=1');
    exit();
}
