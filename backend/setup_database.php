<?php

/**
 * Database setup script — creates database and imports schema.
 * Now reads credentials from centralized db_config.php.
 */

require_once __DIR__ . '/config/db_config.php';

echo "<h1>Setup Database Warungio</h1>";

// Connect without selecting a database first (to create it)
$mysqli = new mysqli(DB_HOST, DB_USER, DB_PASS, '', DB_PORT);

if ($mysqli->connect_errno) {
    echo "<p style='color:red;'>Koneksi ke MySQL gagal: " . $mysqli->connect_error . "</p>";
    echo "<p>Pastikan XAMPP (Apache dan MySQL) sudah berjalan.</p>";
    exit();
}

$dbName = DB_NAME;

if ($mysqli->query("CREATE DATABASE IF NOT EXISTS `$dbName` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci")) {
    echo "<p>Database <b>$dbName</b> berhasil dibuat/ditemukan.</p>";
} else {
    echo "<p style='color:red;'>Gagal membuat database: " . $mysqli->error . "</p>";
    exit();
}

$mysqli->select_db($dbName);

$dbDir = __DIR__ . '/database/';

// Import schema files
executeSqlFile($mysqli, $dbDir . 'warungio_db.sql');
executeSqlFile($mysqli, $dbDir . 'create_partner_registrations_table.sql');
executeSqlFile($mysqli, $dbDir . 'alter_users_table.sql');

echo "<h2 style='color:green;'>Semua sistem database berhasil disiapkan!</h2>";
echo "<p>Anda dapat mengakses halaman lain sekarang. Sistem sudah terhubung ke database.</p>";
echo "<p><strong>Konfigurasi:</strong> Host=" . DB_HOST . " | Database=" . DB_NAME . " | User=" . DB_USER . "</p>";
