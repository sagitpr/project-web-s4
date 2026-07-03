<?php
header("Content-Type: application/json");
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: GET");
header("Access-Control-Allow-Headers: Content-Type");

require_once __DIR__ . '/config/db.php';

try {
    $pdo = getDbConnection();
    
    // Simulate real-time stats (usually filtered by seller's user_id, but here we query all or mock some if empty)
    
    // Total Penjualan
    $total_sales_stmt = $pdo->query("SELECT SUM(total_price) as total FROM orders WHERE order_status = 'completed'");
    $total_sales = $total_sales_stmt->fetchColumn();
    if (!$total_sales) $total_sales = 8560000; // Mock if empty
    
    // Pesanan Baru
    $new_orders_stmt = $pdo->query("SELECT COUNT(*) FROM orders WHERE order_status = 'pending'");
    $new_orders = $new_orders_stmt->fetchColumn();
    if (!$new_orders) $new_orders = 12; // Mock
    
    // Produk Aktif
    $active_products_stmt = $pdo->query("SELECT COUNT(*) FROM products WHERE stock > 0");
    $active_products = $active_products_stmt->fetchColumn();
    if (!$active_products) $active_products = 128; // Mock
    
    // Penilaian
    $rating = 4.9;
    $reviews = 236;
    
    // Saldo
    $saldo = 2350000;
    
    // Aktivitas Terbaru (Orders)
    $activities_stmt = $pdo->query("SELECT id, order_number, order_status AS status, created_at, total_price FROM orders ORDER BY created_at DESC LIMIT 5");
    $activities = $activities_stmt->fetchAll();
    
    if (empty($activities)) {
        // Mock activities
        $activities = [
            ["id" => 1, "order_number" => "ORD-001", "status" => "pending", "created_at" => date("Y-m-d H:i:s", strtotime("-5 mins")), "total_price" => 150000],
            ["id" => 2, "order_number" => "ORD-002", "status" => "completed", "created_at" => date("Y-m-d H:i:s", strtotime("-1 hour")), "total_price" => 45000],
            ["id" => 3, "order_number" => "ORD-003", "status" => "processing", "created_at" => date("Y-m-d H:i:s", strtotime("-2 hours")), "total_price" => 80000]
        ];
    }
    
    echo json_encode([
        "status" => "success",
        "data" => [
            "total_sales" => $total_sales,
            "new_orders" => $new_orders,
            "active_products" => $active_products,
            "rating" => $rating,
            "reviews" => $reviews,
            "balance" => $saldo,
            "activities" => $activities
        ]
    ]);
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(["status" => "error", "message" => "Database error: " . $e->getMessage()]);
}
?>
