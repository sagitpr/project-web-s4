<?php
// Landing page — PUBLIC, no authentication required.
// Visitors see the marketplace homepage with value proposition.
// Authenticated users get redirected to their dashboard.
session_start();

if (isset($_SESSION['user_id'])) {
    $role = $_SESSION['role'] ?? 'buyer';
    if ($role === 'seller') {
        header('Location: ../seller/dashboard/index.html');
        exit();
    } else {
        header('Location: ../buyer/dashboard/index.html');
        exit();
    }
}

// Serve landing page for all visitors
readfile(__DIR__ . '/index.html');
