<?php
session_start();
require_once '../config.php';
require_once '../functions.php';

if (!isLoggedIn()) redirect('../login.php');

$products = query("SELECT p.*, s.store_name 
                   FROM products p 
                   JOIN stores s ON p.store_id = s.id 
                   WHERE p.stock > 0 LIMIT 20")->fetchAll();
