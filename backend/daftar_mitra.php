<?php
header("Content-Type: application/json");
header("Access-Control-Allow-Origin: " . (isset($_SERVER['HTTP_ORIGIN']) ? $_SERVER['HTTP_ORIGIN'] : '*'));
header("Access-Control-Allow-Methods: POST");
header("Access-Control-Allow-Headers: Content-Type, X-CSRF-TOKEN");

require_once __DIR__ . '/config/function.php';
require_once __DIR__ . '/config/db.php';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $data = json_decode(file_get_contents("php://input"), true);
    
    if (!$data) {
        echo json_encode(["status" => "error", "message" => "Data tidak valid"]);
        exit;
    }
    
    // CSRF validation for JSON requests
    initSecureSession();
    if (isset($data['_csrf_token']) && isset($_SESSION['_csrf_token'])) {
        if (!hash_equals($_SESSION['_csrf_token'], $data['_csrf_token'])) {
            http_response_code(403);
            echo json_encode(["status" => "error", "message" => "Token CSRF tidak valid. Silakan muat ulang halaman."]);
            exit;
        }
    }
    
    try {
        $pdo = getDbConnection();
        
        // Buat tabel jika belum ada (untuk memastikan database mendukung input)
        $pdo->exec("CREATE TABLE IF NOT EXISTS mitra_registrations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            store_name VARCHAR(255),
            category VARCHAR(100),
            description TEXT,
            address TEXT,
            district VARCHAR(100),
            city VARCHAR(100),
            province VARCHAR(100),
            postal_code VARCHAR(10),
            latitude VARCHAR(50),
            longitude VARCHAR(50),
            store_phone VARCHAR(20),
            store_email VARCHAR(100),
            owner_name VARCHAR(255),
            owner_phone VARCHAR(20),
            owner_email VARCHAR(100),
            identity_number VARCHAR(50),
            open_time VARCHAR(10),
            close_time VARCHAR(10),
            minimum_order DECIMAL(10,2),
            delivery_services TEXT,
            service_area VARCHAR(100),
            bank_name VARCHAR(50),
            account_holder VARCHAR(255),
            account_number VARCHAR(50),
            status VARCHAR(50) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )");

        $stmt = $pdo->prepare("INSERT INTO mitra_registrations (
            store_name, category, description, address, district, city, province, postal_code,
            latitude, longitude, store_phone, store_email, owner_name, owner_phone, owner_email,
            identity_number, open_time, close_time, minimum_order, delivery_services, service_area,
            bank_name, account_holder, account_number
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )");
        
        $delivery_services = isset($data['deliveryServices']) ? implode(", ", $data['deliveryServices']) : "";

        $stmt->execute([
            $data['storeName'] ?? '',
            $data['category'] ?? '',
            $data['description'] ?? '',
            $data['address'] ?? '',
            $data['district'] ?? '',
            $data['city'] ?? '',
            $data['province'] ?? '',
            $data['postalCode'] ?? '',
            $data['latitude'] ?? '',
            $data['longitude'] ?? '',
            $data['storePhone'] ?? '',
            $data['storeEmail'] ?? '',
            $data['ownerName'] ?? '',
            $data['ownerPhone'] ?? '',
            $data['ownerEmail'] ?? '',
            $data['identityNumber'] ?? '',
            $data['openTime'] ?? '',
            $data['closeTime'] ?? '',
            $data['minimumOrder'] ?? 0,
            $delivery_services,
            $data['serviceArea'] ?? '',
            $data['bankName'] ?? '',
            $data['accountHolder'] ?? '',
            $data['accountNumber'] ?? ''
        ]);
        
        echo json_encode(["status" => "success", "message" => "Pendaftaran berhasil dikirim ke database"]);
    } catch (PDOException $e) {
        http_response_code(500);
        echo json_encode(["status" => "error", "message" => "Database error: " . $e->getMessage()]);
    }
} else {
    http_response_code(405);
    echo json_encode(["status" => "error", "message" => "Method not allowed"]);
}
?>
