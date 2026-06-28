<?php
session_start();
header('Content-Type: application/json');
require_once __DIR__ . '/config/db.php';

try {
    $pdo = getDbConnection();

    // Ensure balance column exists
    try {
        $stmt = $pdo->prepare("SHOW COLUMNS FROM users LIKE 'balance'");
        $stmt->execute();
        if (!$stmt->fetch()) {
            $pdo->exec("ALTER TABLE users ADD COLUMN balance DECIMAL(12,2) DEFAULT 0");
        }
    } catch (Exception $e) {}

    // Mock login for testing if no session
    $userId = $_SESSION['user_id'] ?? 1; 

    // Get user balance
    $balance = 0;
    $userName = "Sari";
    $avatar = "../assets/images/av-siti.png";
    $stmt = $pdo->prepare("SELECT full_name, profile_photo, balance FROM users WHERE id = ?");
    $stmt->execute([$userId]);
    $user = $stmt->fetch();
    if ($user) {
        $balance = (float)($user['balance'] ?? 0);
        $userName = explode(" ", $user['full_name'])[0];
        if ($user['profile_photo']) {
            $avatar = $user['profile_photo'];
        }
    }

    // Get active orders
    $stmt = $pdo->prepare("
        SELECT o.id as order_no, s.store_name, s.store_logo, o.order_status, o.created_at
        FROM orders o
        JOIN stores s ON o.store_id = s.id
        WHERE o.user_id = ? AND o.order_status IN ('pending', 'processed', 'shipped', 'paid')
        ORDER BY o.created_at DESC LIMIT 1
    ");
    $stmt->execute([$userId]);
    $activeOrder = $stmt->fetch();
    
    // Format active order
    $orderData = null;
    if ($activeOrder) {
        // Mock estimate time (+1 hour from created_at)
        $estimateTime = date('d M Y, H:i', strtotime($activeOrder['created_at']) + 3600);
        $orderData = [
            'store_name' => $activeOrder['store_name'],
            'store_logo' => $activeOrder['store_logo'] ?: '../assets/images/av-kelvin.png',
            'order_no' => 'WAR/' . date('y/m/d/', strtotime($activeOrder['created_at'])) . str_pad($activeOrder['order_no'], 4, '0', STR_PAD_LEFT),
            'status' => ucfirst($activeOrder['order_status']),
            'estimate' => $estimateTime
        ];
    }

    // Get recommendations (products)
    $stmt = $pdo->query("
        SELECT id, product_name, price, product_photo, stock
        FROM products
        ORDER BY RAND() LIMIT 4
    ");
    $recommendations = [];
    while($row = $stmt->fetch()) {
        $recommendations[] = [
            'id' => $row['id'],
            'name' => $row['product_name'],
            'price' => $row['price'],
            'image' => $row['product_photo'] ?: '../assets/images/bayam.png',
            'weight' => '~250 gr' // Mock weight since not in DB
        ];
    }

    // Get Warung Terdekat (stores)
    $stmt = $pdo->query("
        SELECT id, store_name, store_logo, address 
        FROM stores 
        WHERE status = 'active'
        ORDER BY id DESC LIMIT 4
    ");
    $warungs = [];
    while($row = $stmt->fetch()) {
        // mock location/rating for now as latitude/longitude logic requires complex query
        $warungs[] = [
            'id' => $row['id'],
            'name' => $row['store_name'],
            'location' => '1.2 km', 
            'rating' => 4.8,
            'image' => $row['store_logo'] ?: '../assets/images/warung1.png',
            'avatar' => '../assets/images/av-kelvin.png'
        ];
    }

    // Get Products (Sayuran dll)
    $stmt = $pdo->query("
        SELECT p.id, p.product_name, p.price, p.product_photo, c.category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        ORDER BY p.id DESC LIMIT 8
    ");
    $products = [];
    while($row = $stmt->fetch()) {
        $cat = strtolower($row['category_name'] ?? 'lainnya');
        $products[] = [
            'id' => $row['id'],
            'name' => $row['product_name'],
            'price' => $row['price'],
            'image' => $row['product_photo'] ?: '../assets/images/bayam.png',
            'category' => $cat,
            'rating' => 4.8,
            'weight' => '~250 gr'
        ];
    }

    echo json_encode([
        'success' => true,
        'user' => [
            'name' => "Hai, " . $userName,
            'avatar' => $avatar,
            'balance' => $balance
        ],
        'activeOrder' => $orderData,
        'recommendations' => $recommendations,
        'warungs' => $warungs,
        'products' => $products
    ]);

} catch (Exception $e) {
    echo json_encode(['success' => false, 'error' => $e->getMessage()]);
}
