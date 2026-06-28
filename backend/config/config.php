<?php

/**
 * Legacy global PDO connection.
 * Now delegates to centralized db_config.php.
 */

require_once __DIR__ . '/db_config.php';

// Global PDO instance (backward-compatible with legacy code using $pdo)
$pdo = getDbConnection();

function query($sql, $params = [])
{
    global $pdo;
    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    return $stmt;
}

function sanitize($data)
{
    return htmlspecialchars(trim($data));
}
