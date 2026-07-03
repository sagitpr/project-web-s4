<?php
header('Content-Type: application/json; charset=utf-8');
require_once __DIR__ . '/config/db.php';
session_start();

if (!isset($_SESSION['user_id']) || ($_SESSION['role'] ?? '') !== 'seller') {
    http_response_code(401);
    echo json_encode(['error' => 'Unauthorized']);
    exit;
}

try {
    $pdo = getDbConnection();
    $userId = $_SESSION['user_id'];

    $storeStmt = $pdo->prepare('SELECT id, store_name FROM stores WHERE user_id = ? LIMIT 1');
    $storeStmt->execute([$userId]);
    $store = $storeStmt->fetch();

    if (!$store) {
        echo json_encode([ 'orders' => [], 'summary' => [ 'total_orders' => 0, 'pending' => 0, 'processed' => 0, 'total_revenue' => 0 ] ]);
        exit;
    }

    $orderStmt = $pdo->prepare(
        'SELECT o.id, o.total_price, o.shipping_cost, o.payment_method, o.order_status, o.delivery_address, o.created_at,
                u.full_name AS buyer_name, u.phone AS buyer_phone
         FROM orders o
         LEFT JOIN users u ON o.user_id = u.id
         WHERE o.store_id = ?
         ORDER BY o.created_at DESC'
    );
    $orderStmt->execute([$store['id']]);
    $orders = $orderStmt->fetchAll();

    $orderIds = array_column($orders, 'id');
    $items = [];

    if (!empty($orderIds)) {
        $placeholders = implode(',', array_fill(0, count($orderIds), '?'));
        $itemsStmt = $pdo->prepare(
            "SELECT oi.order_id, oi.qty, oi.price, oi.subtotal, p.product_name
             FROM order_items oi
             LEFT JOIN products p ON p.id = oi.product_id
             WHERE oi.order_id IN ($placeholders)"
        );
        $itemsStmt->execute($orderIds);
        $items = $itemsStmt->fetchAll();
    }

    $orderItemsMap = [];
    foreach ($items as $item) {
        $orderItemsMap[$item['order_id']][] = [
            'product_name' => $item['product_name'] ?? 'Tidak tersedia',
            'qty' => (int)$item['qty'],
            'price' => (float)$item['price'],
            'subtotal' => (float)$item['subtotal'],
        ];
    }

    $resultOrders = [];
    $summary = [
        'total_orders' => 0,
        'pending' => 0,
        'processed' => 0,
        'total_revenue' => 0,
    ];

    foreach ($orders as $order) {
        $orderId = (int)$order['id'];
        $status = $order['order_status'] ?? 'pending';
        $summary['total_orders']++;
        $summary['total_revenue'] += (float)$order['total_price'];

        if ($status === 'pending') {
            $summary['pending']++;
        }
        if (in_array($status, ['processed', 'shipped'], true)) {
            $summary['processed']++;
        }

        $resultOrders[] = [
            'id' => $orderId,
            'buyer_name' => $order['buyer_name'] ?? 'Pembeli',
            'buyer_phone' => $order['buyer_phone'] ?? '',
            'payment_method' => $order['payment_method'] ?? 'Belum diisi',
            'delivery_address' => $order['delivery_address'] ?? 'Alamat tidak tersedia',
            'order_status' => $status,
            'total_price' => (float)$order['total_price'],
            'shipping_cost' => (float)$order['shipping_cost'],
            'created_at' => $order['created_at'],
            'items' => $orderItemsMap[$orderId] ?? [],
            'item_count' => count($orderItemsMap[$orderId] ?? []),
        ];
    }

    echo json_encode(['orders' => $resultOrders, 'summary' => $summary]);
} catch (Throwable $error) {
    http_response_code(500);
    echo json_encode(['error' => 'Server error, gagal memuat pesanan.']);
}
