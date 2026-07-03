<?php

session_start();
require_once '../config.php';
require_once '../functions.php';

if (!isLoggedIn() || !isSeller()) {
    redirect('../login.php');
}

if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $user_id = $_SESSION['user_id'];
    $store_name = sanitize($_POST['store_name']);
    $category = sanitize($_POST['category']);
    $description = sanitize($_POST['description']);
    $address = sanitize($_POST['address']);
    $city = sanitize($_POST['city']);
    $province = sanitize($_POST['province']);

    try {
        query(
            "INSERT INTO stores (user_id, store_name, category, description, address, city, province, status) 
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')",
            [$user_id, $store_name, $category, $description, $address, $city, $province]
        );

        echo "<script>alert('Permohonan toko berhasil dikirim. Menunggu approval admin.'); window.location='dashboard.php';</script>";
    } catch (Exception $e) {
        echo "Error: " . $e->getMessage();
    }
}
