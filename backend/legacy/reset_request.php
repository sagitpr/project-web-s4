<?php
require_once __DIR__ . '/config/db.php';

if (function_exists('initSecureSession')) {
    initSecureSession();
} else {
    session_start();
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Location: ../reset_password/index.html');
    exit();
}

// Validate CSRF token
if (function_exists('requireCsrfToken')) {
    requireCsrfToken();
}

// Rate limiting: max 3 reset requests per 15 minutes
if (function_exists('checkRateLimit') && !checkRateLimit('reset_request', 3, 15)) {
    header('Location: ../reset_password/index.html?error=rate_limit');
    exit();
}

$identifier = trim($_POST['identifier'] ?? '');
if ($identifier === '') {
    header('Location: ../reset_password/index.html?error=1');
    exit();
}

try {
    $pdo = getDbConnection();
    $stmt = $pdo->prepare('SELECT id, email, phone FROM users WHERE email = ? OR phone = ? LIMIT 1');
    $stmt->execute([$identifier, $identifier]);
    $user = $stmt->fetch();

    if (!$user) {
        header('Location: ../reset_password/index.html?error=1');
        exit();
    }

    $otp = str_pad((string) random_int(0, 999999), 6, '0', STR_PAD_LEFT);
    $otpExpires = date('Y-m-d H:i:s', strtotime('+' . OTP_EXPIRE_MINUTES . ' minutes'));

    $update = $pdo->prepare('UPDATE users SET otp = ?, otp_expires = ? WHERE id = ?');
    $update->execute([$otp, $otpExpires, $user['id']]);

    $smsSent = sendOtpSms($user['phone'], $otp);
    $query = 'step=verify&identifier=' . urlencode($identifier) . '&sent=1';

    if (!$smsSent) {
        $query .= '&sms=0&otp=' . urlencode($otp);
    }

    header('Location: ../reset_password/index.html?' . $query);
    exit();
} catch (Throwable $e) {
    header('Location: ../reset_password/index.html?error=1');
    exit();
}
