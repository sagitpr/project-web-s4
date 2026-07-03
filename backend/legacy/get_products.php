<?php
/**
 * Get Products API
 * Retrieves products from the database.
 * Falls back gracefully if table doesn't exist yet.
 */
require_once __DIR__ . '/config/db.php';

header('Content-Type: application/json');

try {
    $pdo = getDbConnection();
    
    // Check if products table exists
    $tableCheck = $pdo->query("SHOW TABLES LIKE 'products'")->fetch();
    
    $products = [];
    
    if ($tableCheck) {
        // Table exists — query real data
        $stmt = $pdo->query('
            SELECT id, product_name, sku, category, price, stock, 
                   status, views, image_url, description 
            FROM products 
            ORDER BY created_at DESC
        ');
        $products = $stmt->fetchAll();
        
        // Cast numeric fields for JS
        $products = array_map(function($p) {
            $p['id'] = (int)$p['id'];
            $p['price'] = (float)$p['price'];
            $p['stock'] = (int)$p['stock'];
            $p['views'] = (int)$p['views'];
            return $p;
        }, $products);
    }
    
    echo json_encode([
        'success' => true,
        'products' => $products,
        'source' => $tableCheck ? 'database' : 'empty'
    ]);
} catch (Exception $e) {
    // Graceful fallback — return empty array instead of crashing
    echo json_encode([
        'success' => true,
        'products' => [],
        'source' => 'error',
        'message' => 'Gagal memuat produk: ' . $e->getMessage()
    ]);
}
?>
