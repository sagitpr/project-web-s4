<?php
header('Content-Type: application/json');
require_once __DIR__ . '/config/db.php';

try {
    $pdo = getDbConnection();

    $products = [];
    $stmt = $pdo->query(
        'SELECT p.product_name, c.category_name, p.stock, p.price, p.product_status, p.created_at
         FROM products p
         LEFT JOIN categories c ON c.id = p.category_id
         ORDER BY p.created_at DESC
         LIMIT 10'
    );

    while ($row = $stmt->fetch()) {
        $status = $row['product_status'] ?? 'fresh';
        $statusClass = 'status-green';

        if ($status === 'normal') {
            $statusClass = 'status-yellow';
        } elseif ($status === 'low') {
            $statusClass = 'status-orange';
        } elseif ($status === 'bad') {
            $statusClass = 'status-red';
        }

        $issue = 'Stok tersedia';
        if ((int) $row['stock'] <= 0) {
            $issue = 'Stok habis';
        } elseif ((int) $row['stock'] < 5) {
            $issue = 'Stok menipis';
        }

        $products[] = [
            'name' => $row['product_name'],
            'cat' => $row['category_name'] ?: 'Lainnya',
            'status' => ucfirst($status),
            'statusClass' => $statusClass,
            'issue' => $issue,
            'action' => 'Edit',
            'price' => 'Rp ' . number_format((float) $row['price'], 0, ',', '.')
        ];
    }

    $activities = [
        ['msg' => 'Data produk terakhir diperbarui.', 'time' => 'Baru saja'],
        ['msg' => 'Pesanan baru memasuki proses pengemasan.', 'time' => '15 menit lalu'],
        ['msg' => 'Produk baru ditambahkan ke warung.', 'time' => '1 jam lalu']
    ];

    echo json_encode(['products' => $products, 'activities' => $activities]);
} catch (Throwable $e) {
    echo json_encode(['products' => [], 'activities' => []]);
}
?>
