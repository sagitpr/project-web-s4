<?php
/**
 * =============================================================================
 * db_config.php — SINGLE SOURCE OF TRUTH for database configuration
 * =============================================================================
 *
 * All PHP backends MUST use this file for database credentials.
 * Reads from the project root .env file via function.php's loadEnv().
 *
 * Usage:
 *   require_once __DIR__ . '/db_config.php';
 *   $pdo = getDbConnection();
 *
 * Environment variables consumed (from root .env):
 *   DB_HOST   (default: localhost)
 *   DB_PORT   (default: 3306)
 *   DB_NAME   (default: warungio_db)
 *   DB_USER   (default: root)
 *   DB_PASS   (default: '')
 */

// Ensure env() helper is available
require_once __DIR__ . '/function.php';

// =============================================================================
// Database configuration constants (immutable)
// =============================================================================

define('DB_HOST', env('DB_HOST', 'localhost'));
define('DB_PORT', env('DB_PORT', '3306'));
define('DB_NAME', env('DB_NAME', 'warungio_db'));
define('DB_USER', env('DB_USER', 'root'));
define('DB_PASS', env('DB_PASS', ''));
define('DB_CHARSET', 'utf8mb4');

// =============================================================================
// Connection factory — returns a PDO singleton
// =============================================================================

function getDbConnection()
{
    static $pdo = null;

    if ($pdo === null) {
        $dsn = sprintf(
            'mysql:host=%s;port=%s;dbname=%s;charset=%s',
            DB_HOST,
            DB_PORT,
            DB_NAME,
            DB_CHARSET
        );

        $pdo = new PDO($dsn, DB_USER, DB_PASS, [
            PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES   => false,
        ]);
    }

    return $pdo;
}

// =============================================================================
// Raw mysqli connection (for setup scripts that need multi_query)
// =============================================================================

function getMysqliConnection()
{
    static $mysqli = null;

    if ($mysqli === null) {
        $mysqli = new mysqli(DB_HOST, DB_USER, DB_PASS, DB_NAME, DB_PORT);
        if ($mysqli->connect_errno) {
            die("Koneksi MySQL gagal: " . $mysqli->connect_error);
        }
        $mysqli->set_charset(DB_CHARSET);
    }

    return $mysqli;
}

// =============================================================================
// Config accessor (for non-PHP consumers via JSON output)
// =============================================================================

function getDbConfig()
{
    return [
        'host'     => DB_HOST,
        'port'     => DB_PORT,
        'name'     => DB_NAME,
        'user'     => DB_USER,
        'pass'     => DB_PASS,
        'charset'  => DB_CHARSET,
    ];
}

// =============================================================================
// Helper: execute SQL file (for setup/seed scripts)
// =============================================================================

function executeSqlFile($mysqli, $filePath)
{
    if (!file_exists($filePath)) {
        echo "<p style='color:red'>File tidak ditemukan: <b>" . basename($filePath) . "</b></p>";
        return;
    }

    $sql = file_get_contents($filePath);
    if (trim($sql) === '') return;

    if ($mysqli->multi_query($sql)) {
        do {
            if ($result = $mysqli->store_result()) {
                $result->free();
            }
        } while ($mysqli->more_results() && $mysqli->next_result());
        echo "<p>Berhasil import: <b>" . basename($filePath) . "</b></p>";
    } else {
        // Ignore duplicate column errors for alter scripts
        if ($mysqli->errno == 1060) {
            echo "<p>Catatan untuk " . basename($filePath) . ": Kolom sudah ada (aman diabaikan).</p>";
        } else {
            echo "<p style='color:red'>Gagal import <b>" . basename($filePath) . "</b> - Error: " . $mysqli->error . "</p>";
        }
    }
}
