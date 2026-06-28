<?php
require_once '../config.php';
require_once '../functions.php';
$user_id = $_SESSION['user_id'];
$store = query("SELECT id FROM stores WHERE user_id = ?", [$user_id])->fetch();

$orders = query("SELECT o.*, u.fullname FROM orders o 
                 JOIN users u ON o.user_id = u.id 
                 WHERE o.store_id = ? ORDER BY o.created_at DESC", [$store['id']])->fetchAll();
