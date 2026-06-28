<?php

/**
 * Legacy mysqli_connect wrapper.
 * Now reads credentials from centralized db_config.php.
 */

require_once __DIR__ . '/config/db_config.php';

$conn = mysqli_connect(DB_HOST, DB_USER, DB_PASS, DB_NAME, DB_PORT);

if (!$conn) {
    die("Koneksi gagal");
}

mysqli_set_charset($conn, DB_CHARSET);
