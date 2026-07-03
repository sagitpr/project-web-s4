<?php
require_once __DIR__ . '/config/db.php';

header('Content-Type: application/json');

try {
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
        throw new Exception('Invalid request method');
    }

    $pdo = getDbConnection();
    
    $product_id = intval($_POST['product_id'] ?? 0);
    if ($product_id <= 0) {
        throw new Exception('ID produk tidak valid');
    }

    $stmt = $pdo->prepare('SELECT image_url FROM products WHERE id = ?');
    $stmt->execute([$product_id]);
    $product = $stmt->fetch();
    
    if (!$product) {
        throw new Exception('Produk tidak ditemukan');
    }

    if ($product['image_url'] && file_exists(__DIR__ . '/' . $product['image_url'])) {
        @unlink(__DIR__ . '/' . $product['image_url']);
    }

    $stmt = $pdo->prepare('DELETE FROM products WHERE id = ?');
    $stmt->execute([$product_id]);

    echo json_encode([
        'success' => true,
        'message' => 'Produk berhasil dihapus'
    ]);
} catch (Exception $e) {
    http_response_code(400);
    echo json_encode([
        'success' => false,
        'message' => $e->getMessage()
    ]);
}
?>
