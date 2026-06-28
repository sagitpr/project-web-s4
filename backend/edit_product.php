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

    $product_name = trim($_POST['product_name'] ?? '');
    $category = trim($_POST['category'] ?? '');
    $sku = trim($_POST['sku'] ?? '');
    $price = floatval($_POST['price'] ?? 0);
    $stock = intval($_POST['stock'] ?? 0);
    $description = trim($_POST['description'] ?? '');
    
    if (empty($product_name) || empty($sku) || $price <= 0) {
        throw new Exception('Data produk tidak lengkap');
    }

    $stmt = $pdo->prepare('SELECT image_url FROM products WHERE id = ?');
    $stmt->execute([$product_id]);
    $current = $stmt->fetch();
    
    if (!$current) {
        throw new Exception('Produk tidak ditemukan');
    }

    $image_url = $current['image_url'];
    
    if (!empty($_FILES['product_image']['tmp_name'])) {
        if ($image_url && file_exists(__DIR__ . '/' . $image_url)) {
            @unlink(__DIR__ . '/' . $image_url);
        }
        
        $upload_dir = __DIR__ . '/../assets/images/products/';
        if (!is_dir($upload_dir)) {
            mkdir($upload_dir, 0755, true);
        }
        
        $file_name = uniqid() . '_' . basename($_FILES['product_image']['name']);
        $file_path = $upload_dir . $file_name;
        
        if (move_uploaded_file($_FILES['product_image']['tmp_name'], $file_path)) {
            $image_url = '../assets/images/products/' . $file_name;
        }
    }

    $stmt = $pdo->prepare('
        UPDATE products 
        SET product_name = ?, category = ?, sku = ?, price = ?, stock = ?, 
            description = ?, image_url = ?, updated_at = NOW()
        WHERE id = ?
    ');
    
    $stmt->execute([
        $product_name,
        $category,
        $sku,
        $price,
        $stock,
        $description,
        $image_url,
        $product_id
    ]);

    echo json_encode([
        'success' => true,
        'message' => 'Produk berhasil diperbarui'
    ]);
} catch (Exception $e) {
    http_response_code(400);
    echo json_encode([
        'success' => false,
        'message' => $e->getMessage()
    ]);
}
?>
