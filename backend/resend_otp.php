<?php
session_start();
require_once __DIR__ . '/config/db.php';

$identifier = trim($_GET['identifier'] ?? '');
if ($identifier === '') {
    header('Location: ../otp/index.html?error=2');
    exit();
}

try {
    $pdo = getDbConnection();

    if (isset($_SESSION['pending_login_user_id'])) {
        $stmt = $pdo->prepare('SELECT id, phone FROM users WHERE id = ? AND (email = ? OR phone = ?) LIMIT 1');
        $stmt->execute([$_SESSION['pending_login_user_id'], $identifier, $identifier]);
    } else {
        $stmt = $pdo->prepare('SELECT id, phone FROM users WHERE (email = ? OR phone = ?) AND is_verified = 0 LIMIT 1');
        $stmt->execute([$identifier, $identifier]);
    }

    $user = $stmt->fetch();

    if (!$user) {
        header('Location: ../otp/index.html?error=2&identifier=' . urlencode($identifier));
        exit();
    }

    $otp = str_pad((string) random_int(0, 999999), 6, '0', STR_PAD_LEFT);
    $otpExpires = date('Y-m-d H:i:s', strtotime('+' . OTP_EXPIRE_MINUTES . ' minutes'));

    $update = $pdo->prepare('UPDATE users SET otp = ?, otp_expires = ? WHERE id = ?');
    $update->execute([$otp, $otpExpires, $user['id']]);
    $smsSent = sendOtpSms($user['phone'], $otp);

    $query = 'identifier=' . urlencode($user['phone']) . '&sent=1';
    if (isset($_SESSION['pending_login_user_id'])) {
        $query .= '&login=1';
    }
    if (!$smsSent) {
        $query .= '&sms=0&otp=' . urlencode($otp);
    }

    header('Location: ../otp/index.html?' . $query);
    exit();
} catch (PDOException $e) {
    header('Location: ../otp/index.html?error=2&identifier=' . urlencode($identifier));
    exit();
}
