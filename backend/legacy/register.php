<?php

session_start();
require_once 'config.php';
require_once 'functions.php';

if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $fullname = sanitize($_POST['fullname']);
    $email    = sanitize($_POST['email']);
    $phone    = sanitize($_POST['phone']);
    $password = password_hash($_POST['password'], PASSWORD_DEFAULT);
    $role     = $_POST['role'] ?? 'buyer';

    try {
        query(
            "INSERT INTO users (fullname, email, phone, password, role) VALUES (?, ?, ?, ?, ?)",
            [$fullname, $email, $phone, $password, $role]
        );
        echo "<script>alert('Registrasi berhasil! Silakan login.'); window.location='login.php';</script>";
    } catch (Exception $e) {
        echo "Error: " . $e->getMessage();
    }
}
