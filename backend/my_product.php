<?php

session_start();
require_once '../config.php';
require_once '../functions.php';

if (!isSeller()) redirect('../login.php');

$user_id = $_SESSION['user_id'];
$products = query("SELECT p.* FROM products p 
                   JOIN stores s ON p.store_id = s.id 
                   WHERE s.user_id = ?", [$user_id])->fetchAll();
