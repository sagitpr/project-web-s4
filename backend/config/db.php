<?php

/**
 * Legacy database configuration and SMS helper.
 * Database config now delegates to centralized db_config.php.
 * SMS/Twilio functions remain here for backward compatibility.
 */

require_once __DIR__ . '/db_config.php';

// Database config constants (aliases for backward compatibility)
define('OTP_DB_HOST', DB_HOST);
define('OTP_DB_NAME', DB_NAME);
define('OTP_DB_USER', DB_USER);
define('OTP_DB_PASS', DB_PASS);

// SMS Gateway config
define('SMS_GATEWAY_PROVIDER', 'twilio');
define('TWILIO_ACCOUNT_SID', env('TWILIO_ACCOUNT_SID', 'YOUR_TWILIO_ACCOUNT_SID'));
define('TWILIO_AUTH_TOKEN', env('TWILIO_AUTH_TOKEN', 'YOUR_TWILIO_AUTH_TOKEN'));
define('TWILIO_FROM_NUMBER', env('TWILIO_FROM_NUMBER', '+1234567890'));
define('OTP_EXPIRE_MINUTES', env('OTP_EXPIRE_MINUTES', 15));

// getDbConnection() is now defined in db_config.php

function normalizePhoneNumber($phone)
{
    $digits = preg_replace('/[^0-9\+]/', '', $phone);

    if ($digits === '') {
        return $phone;
    }

    if (strpos($digits, '+') !== 0) {
        if (strpos($digits, '0') === 0) {
            $digits = '+62' . substr($digits, 1);
        } else {
            $digits = '+' . $digits;
        }
    }

    return $digits;
}

function sendSmsGateway($to, $message)
{
    if (SMS_GATEWAY_PROVIDER !== 'twilio') {
        return false;
    }

    if (TWILIO_ACCOUNT_SID === 'YOUR_TWILIO_ACCOUNT_SID' || TWILIO_AUTH_TOKEN === 'YOUR_TWILIO_AUTH_TOKEN' || TWILIO_FROM_NUMBER === '+1234567890') {
        return false;
    }

    $to = normalizePhoneNumber($to);
    $url = 'https://api.twilio.com/2010-04-01/Accounts/' . TWILIO_ACCOUNT_SID . '/Messages.json';
    $postData = http_build_query([
        'From' => TWILIO_FROM_NUMBER,
        'To' => $to,
        'Body' => $message,
    ]);

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $postData);
    curl_setopt($ch, CURLOPT_USERPWD, TWILIO_ACCOUNT_SID . ':' . TWILIO_AUTH_TOKEN);
    curl_setopt($ch, CURLOPT_HTTPAUTH, CURLAUTH_BASIC);
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    return $httpCode >= 200 && $httpCode < 300;
}

function sendOtpSms($phone, $otp)
{
    $message = 'Kode OTP Warungio Anda adalah: ' . $otp . '. Berlaku ' . OTP_EXPIRE_MINUTES . ' menit.';
    return sendSmsGateway($phone, $message);
}
