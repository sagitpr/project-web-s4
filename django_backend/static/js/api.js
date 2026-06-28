/**
 * Warungio API Client + Mock Interceptor
 *
 * Architecture:
 *   1. RealAPI  — all methods use auth.api() as before (works with real backend)
 *   2. MockAPI  — all mock handlers return dummy data (only when MOCK_API=true)
 *   3. Assembly — RealAPI first, MockAPI methods overlaid on top if MOCK_API=true
 *
 * Usage:
 *   window.MOCK_API = true          // enable mock mode
 *   window.MOCK_API = false         // (or unset) real backend mode
 */
(function () {
  'use strict';

  var auth = window.WarungioAuth;

  // ──────────────────────────────────────────────────────────────────────────
  //  HELPERS
  // ──────────────────────────────────────────────────────────────────────────

  function delay() {
    var ms = 150 + Math.random() * 300;
    return new Promise(function (r) { return setTimeout(r, ms); });
  }

  var _nextId = 100;
  function uid() { return ++_nextId; }

  function daysAgo(n) {
    var d = new Date();
    d.setDate(d.getDate() - Math.floor(Math.random() * n));
    return d.toISOString();
  }

  function ok(data) {
    return Promise.resolve(data);
  }

  function fail(msg, status) {
    return Promise.reject({ error: msg || 'Terjadi kesalahan.', status: status || 400 });
  }

  function filterProducts(params) {
    var result = products.slice();
    if (params.category) result = result.filter(function (p) { return p.category == params.category; });
    if (params.store) result = result.filter(function (p) { return p.store == params.store; });
    if (params.search) {
      var q = params.search.toLowerCase();
      result = result.filter(function (p) { return p.product_name.toLowerCase().indexOf(q) !== -1 || p.store_name.toLowerCase().indexOf(q) !== -1; });
    }
    if (params.is_featured) result = result.filter(function (p) { return p.is_featured; });
    if (params.price_min) result = result.filter(function (p) { return p.price >= Number(params.price_min); });
    if (params.price_max) result = result.filter(function (p) { return p.price <= Number(params.price_max); });
    if (params.ordering === 'price') result.sort(function (a, b) { return a.price - b.price; });
    if (params.ordering === '-price') result.sort(function (a, b) { return b.price - a.price; });
    if (params.ordering === '-sold_count') result.sort(function (a, b) { return b.sold_count - a.sold_count; });
    return result;
  }

  function filterOrders(list, params) {
    var result = list.slice();
    if (params.order_status) result = result.filter(function (o) { return o.order_status === params.order_status; });
    if (params.status) result = result.filter(function (o) { return o.order_status === params.status; });
    return result;
  }

  // ──────────────────────────────────────────────────────────────────────────
  //  MOCK DATA STORE
  // ──────────────────────────────────────────────────────────────────────────

  var user = {
    id: 1, email: 'demo@warungio.id', full_name: 'Demo User', phone: '081234567890',
    role: 'buyer', address: 'Jl. Merdeka No. 123, Jakarta Pusat', profile_photo: '', bio: 'Pengguna demo Warungio',
    is_verified: true, is_mobile: false, is_tablet: false, is_desktop: true,
    created_at: '2026-01-15T08:00:00Z',
  };

  var sellerUser = {
    id: 2, email: 'seller@warungio.id', full_name: 'Budi Santoso', phone: '081298765432',
    role: 'seller', address: 'Jl. Mangga Dua No. 45, Jakarta Utara', profile_photo: '', bio: 'Penjual sayur segar sejak 2020',
    is_verified: true, is_mobile: false, is_tablet: false, is_desktop: true,
    created_at: '2026-01-10T08:00:00Z',
  };

  var store = {
    id: 1, user: 2, store_name: 'Vega Fresh', slug: 'vega-fresh',
    description: 'Toko sayur dan buah segar langsung dari petani.',
    logo: '', banner: '', city: 'Jakarta Utara', province: 'DKI Jakarta',
    address: 'Jl. Mangga Dua No. 45', phone: '081298765432', whatsapp: '081298765432',
    rating_avg: 4.7, follower_count: 234, total_sales: 156700000, product_count: 12,
    status: 'active', is_open: true, open_time: '07:00', close_time: '21:00',
    created_at: '2026-01-10T08:00:00Z',
  };

  var store2 = {
    id: 2, user: 3, store_name: 'Toko Berkah Jaya', slug: 'berkah-jaya',
    description: 'Toko sembako dan kebutuhan sehari-hari dengan harga terjangkau.',
    logo: '', banner: '', city: 'Jakarta Timur', province: 'DKI Jakarta',
    address: 'Jl. Raya Bogor KM 12', phone: '081211223344', whatsapp: '081211223344',
    rating_avg: 4.5, follower_count: 156, total_sales: 89200000, product_count: 4,
    status: 'active', is_open: true, open_time: '06:00', close_time: '22:00',
    created_at: '2026-02-01T08:00:00Z',
  };

  var categories = [
    { id: 1, name: 'Sayuran', slug: 'sayuran', icon: '🥬', is_active: true },
    { id: 2, name: 'Buah-buahan', slug: 'buah', icon: '🍎', is_active: true },
    { id: 3, name: 'Daging & Ikan', slug: 'daging-ikan', icon: '🥩', is_active: true },
    { id: 4, name: 'Sembako', slug: 'sembako', icon: '📦', is_active: true },
    { id: 5, name: 'Minuman', slug: 'minuman', icon: '🥤', is_active: true },
    { id: 6, name: 'Bumbu Dapur', slug: 'bumbu-dapur', icon: '🧂', is_active: true },
  ];

  var products = [
    { id: 1, store: 1, store_name: 'Vega Fresh', category: 1, category_name: 'Sayuran', product_name: 'Bayam Segar', slug: 'bayam-segar', product_photo: '/static/images/paket-sayur.png', description: 'Bayam segar langsung dari petani Lembang. Kaya zat besi.', price: 5000, stock: 100, unit: 'ikat', sold_count: 340, rating_avg: 4.8, review_count: 45, is_active: true, is_featured: true, product_status: 'available', quality_score: 95, weight: 250, created_at: daysAgo(60) },
    { id: 2, store: 1, store_name: 'Vega Fresh', category: 1, category_name: 'Sayuran', product_name: 'Kangkung', slug: 'kangkung', product_photo: '/static/images/paket-sayur.png', description: 'Kangkung segar dari kebun hidroponik.', price: 4000, stock: 80, unit: 'ikat', sold_count: 280, rating_avg: 4.6, review_count: 32, is_active: true, is_featured: false, product_status: 'available', quality_score: 92, weight: 200, created_at: daysAgo(55) },
    { id: 3, store: 1, store_name: 'Vega Fresh', category: 2, category_name: 'Buah-buahan', product_name: 'Apel Fuji', slug: 'apel-fuji', product_photo: '/static/images/fruit.png', description: 'Apel Fuji import quality, manis dan renyah.', price: 25000, stock: 50, unit: 'kg', sold_count: 190, rating_avg: 4.7, review_count: 28, is_active: true, is_featured: true, product_status: 'available', quality_score: 93, weight: 1000, created_at: daysAgo(50) },
    { id: 4, store: 1, store_name: 'Vega Fresh', category: 2, category_name: 'Buah-buahan', product_name: 'Pisang Cavendish', slug: 'pisang-cavendish', product_photo: '/static/images/fruit.png', description: 'Pisang Cavendish matang pohon.', price: 18000, stock: 70, unit: 'sisir', sold_count: 210, rating_avg: 4.5, review_count: 25, is_active: true, is_featured: false, product_status: 'available', quality_score: 90, weight: 500, created_at: daysAgo(45) },
    { id: 5, store: 1, store_name: 'Vega Fresh', category: 3, category_name: 'Daging & Ikan', product_name: 'Daging Sapi Giling', slug: 'daging-sapi-giling', product_photo: '/static/images/meat.png', description: 'Daging sapi giling segar, cocok untuk bakso dan spaghetti.', price: 55000, stock: 30, unit: 'kg', sold_count: 120, rating_avg: 4.6, review_count: 18, is_active: true, is_featured: true, product_status: 'available', quality_score: 91, weight: 1000, created_at: daysAgo(40) },
    { id: 6, store: 1, store_name: 'Vega Fresh', category: 3, category_name: 'Daging & Ikan', product_name: 'Ikan Nila Segar', slug: 'ikan-nila-segar', product_photo: '/static/images/meat.png', description: 'Ikan nila segar dari kolam, sudah dibersihkan.', price: 35000, stock: 25, unit: 'kg', sold_count: 95, rating_avg: 4.4, review_count: 14, is_active: true, is_featured: false, product_status: 'available', quality_score: 88, weight: 1000, created_at: daysAgo(35) },
    { id: 7, store: 2, store_name: 'Toko Berkah Jaya', category: 4, category_name: 'Sembako', product_name: 'Beras Premium 5kg', slug: 'beras-premium-5kg', product_photo: '/static/images/paket-sayur.png', description: 'Beras premium kualitas terbaik, pulen dan wangi.', price: 75000, stock: 200, unit: 'karung', sold_count: 430, rating_avg: 4.8, review_count: 62, is_active: true, is_featured: true, product_status: 'available', quality_score: 96, weight: 5000, created_at: daysAgo(30) },
    { id: 8, store: 2, store_name: 'Toko Berkah Jaya', category: 4, category_name: 'Sembako', product_name: 'Minyak Goreng 1L', slug: 'minyak-goreng-1l', product_photo: '/static/images/paket-sayur.png', description: 'Minyak goreng kemasan 1 liter, bening dan sehat.', price: 22000, stock: 150, unit: 'botol', sold_count: 380, rating_avg: 4.6, review_count: 48, is_active: true, is_featured: false, product_status: 'available', quality_score: 92, weight: 1000, created_at: daysAgo(25) },
    { id: 9, store: 2, store_name: 'Toko Berkah Jaya', category: 5, category_name: 'Minuman', product_name: 'Teh Botol Sosro', slug: 'teh-botol-sosro', product_photo: '/static/images/beverage.png', description: 'Teh botol asli Indonesia, siap minum.', price: 7000, stock: 300, unit: 'botol', sold_count: 520, rating_avg: 4.5, review_count: 55, is_active: true, is_featured: false, product_status: 'available', quality_score: 89, weight: 350, created_at: daysAgo(20) },
    { id: 10, store: 1, store_name: 'Vega Fresh', category: 6, category_name: 'Bumbu Dapur', product_name: 'Bawang Merah 250g', slug: 'bawang-merah-250g', product_photo: '/static/images/paket-sayur.png', description: 'Bawang merah segar, cocok untuk bumbu masakan.', price: 12000, stock: 90, unit: 'bungkus', sold_count: 160, rating_avg: 4.7, review_count: 22, is_active: true, is_featured: false, product_status: 'available', quality_score: 94, weight: 250, created_at: daysAgo(15) },
    { id: 11, store: 1, store_name: 'Vega Fresh', category: 1, category_name: 'Sayuran', product_name: 'Wortel Impor', slug: 'wortel-impor', product_photo: '/static/images/paket-sayur.png', description: 'Wortel impor fresh, besar dan manis.', price: 15000, stock: 60, unit: 'kg', sold_count: 145, rating_avg: 4.6, review_count: 20, is_active: true, is_featured: false, product_status: 'available', quality_score: 91, weight: 1000, created_at: daysAgo(10) },
    { id: 12, store: 1, store_name: 'Vega Fresh', category: 2, category_name: 'Buah-buahan', product_name: 'Jeruk Sunkist', slug: 'jeruk-sunkist', product_photo: '/static/images/fruit.png', description: 'Jeruk sunkist manis, kaya vitamin C.', price: 28000, stock: 40, unit: 'kg', sold_count: 98, rating_avg: 4.5, review_count: 16, is_active: true, is_featured: false, product_status: 'available', quality_score: 90, weight: 1000, created_at: daysAgo(5) },
  ];

  var cartItems = [
    { id: 1, product: products[0], qty: 2 },
    { id: 2, product: products[2], qty: 1 },
  ];

  var orders = [
    { id: 1, order_number: 'WRG-20260601-001', user: user, store: store, items: [{ id: 1, product: products[0], product_name: 'Bayam Segar', qty: 2, price: 5000, subtotal: 10000 }, { id: 2, product: products[2], product_name: 'Apel Fuji', qty: 1, price: 25000, subtotal: 25000 }], subtotal: 35000, shipping_cost: 5000, discount: 0, total_price: 40000, order_status: 'completed', payment_method: 'bank_transfer', payment_status: 'paid', delivery_address: 'Jl. Merdeka No. 123, Jakarta Pusat', recipient_name: 'Demo User', recipient_phone: '081234567890', notes: '', courier: 'GoSend', tracking_number: 'GOSEND123456', created_at: daysAgo(5), completed_at: daysAgo(4) },
    { id: 2, order_number: 'WRG-20260603-002', user: user, store: store, items: [{ id: 3, product: products[4], product_name: 'Daging Sapi Giling', qty: 1, price: 55000, subtotal: 55000 }, { id: 4, product: products[10], product_name: 'Bawang Merah 250g', qty: 3, price: 12000, subtotal: 36000 }], subtotal: 91000, shipping_cost: 8000, discount: 5000, total_price: 94000, order_status: 'on_delivery', payment_method: 'gopay', payment_status: 'paid', delivery_address: 'Jl. Merdeka No. 123, Jakarta Pusat', recipient_name: 'Demo User', recipient_phone: '081234567890', notes: 'Tolong bell dulu ya', courier: 'GoSend', tracking_number: 'GOSEND789012', created_at: daysAgo(1) },
    { id: 3, order_number: 'WRG-20260606-003', user: user, store: store2, items: [{ id: 5, product: products[6], product_name: 'Beras Premium 5kg', qty: 1, price: 75000, subtotal: 75000 }, { id: 6, product: products[7], product_name: 'Minyak Goreng 1L', qty: 2, price: 22000, subtotal: 44000 }], subtotal: 119000, shipping_cost: 10000, discount: 0, total_price: 129000, order_status: 'pending', payment_method: 'cod', payment_status: 'unpaid', delivery_address: 'Jl. Merdeka No. 123, Jakarta Pusat', recipient_name: 'Demo User', recipient_phone: '081234567890', notes: '', courier: '', tracking_number: '', created_at: daysAgo(0) },
  ];

  var deliveries = [
    { id: 1, order: 1, shipping_method: { id: 1, name: 'GoSend', slug: 'gosend', base_fee: 5000, is_active: true, estimated_time: '30-60 menit' }, delivery_status: 'pesanan_diterima', courier_name: 'GoSend', driver_name: 'Ahmad', driver_phone: '081312345678', pickup_code: '654321', tracking_number: 'GOSEND123456', picked_up_at: daysAgo(5), delivered_at: daysAgo(4), created_at: daysAgo(5) },
    { id: 2, order: 2, shipping_method: { id: 1, name: 'GoSend', slug: 'gosend', base_fee: 8000, is_active: true, estimated_time: '30-60 menit' }, delivery_status: 'dalam_perjalanan', courier_name: 'GoSend', driver_name: 'Bambang', driver_phone: '081398765432', pickup_code: '123456', tracking_number: 'GOSEND789012', estimated_time: '15 menit lagi', picked_up_at: daysAgo(1), delivered_at: null, created_at: daysAgo(1) },
  ];

  var notifications = [
    { id: 1, notification_type: 'order', title: 'Pesanan Dikonfirmasi', description: 'Pesanan WRG-20260603-002 telah dikonfirmasi oleh Vega Fresh.', is_read: false, action_url: '/buyer/orders/index.html?id=2', action_text: 'Lihat Pesanan', created_at: daysAgo(0) },
    { id: 2, notification_type: 'order', title: 'Pesanan Dalam Perjalanan', description: 'Pesanan WRG-20260603-002 sedang dalam perjalanan!', is_read: false, action_url: '/buyer/orders/index.html?id=2', action_text: 'Lacak Pesanan', created_at: daysAgo(0) },
    { id: 3, notification_type: 'payment', title: 'Pembayaran Berhasil', description: 'Pembayaran untuk pesanan WRG-20260603-002 berhasil.', is_read: true, action_url: '/buyer/orders/index.html?id=2', action_text: 'Lihat Detail', created_at: daysAgo(1) },
    { id: 4, notification_type: 'order', title: 'Pesanan Selesai', description: 'Pesanan WRG-20260601-001 sudah diterima. Terima kasih!', is_read: true, action_url: '/buyer/orders/index.html?id=1', action_text: 'Beri Rating', created_at: daysAgo(3) },
    { id: 5, notification_type: 'promo', title: 'Promo Akhir Pekan', description: 'Diskon 20% untuk semua produk sayuran!', is_read: true, action_url: '/products/', action_text: 'Lihat Promo', created_at: daysAgo(2) },
  ];

  var shippingMethods = [
    { id: 1, name: 'GoSend', slug: 'gosend', description: 'Pengiriman instan dengan Gojek', base_fee: 5000, estimated_time: '30-60 menit', is_active: true },
    { id: 2, name: 'GrabExpress', slug: 'grabexpress', description: 'Pengiriman cepat dengan Grab', base_fee: 6000, estimated_time: '30-60 menit', is_active: true },
    { id: 3, name: 'Maxim', slug: 'maxim', description: 'Pengiriman dengan Maxim', base_fee: 4000, estimated_time: '45-90 menit', is_active: true },
    { id: 4, name: 'Antar Sendiri', slug: 'antar-sendiri', description: 'Ambil langsung di toko', base_fee: 0, estimated_time: 'Siap dalam 30 menit', is_active: true },
  ];

  var paymentMethods = [
    { id: 1, name: 'Bank Transfer BCA', slug: 'bca', type: 'bank_transfer', icon: '/static/images/credit-card-icon.png', is_active: true },
    { id: 2, name: 'Bank Transfer BNI', slug: 'bni', type: 'bank_transfer', icon: '/static/images/credit-card-icon.png', is_active: true },
    { id: 3, name: 'Bank Transfer BRI', slug: 'bri', type: 'bank_transfer', icon: '/static/images/credit-card-icon.png', is_active: true },
    { id: 4, name: 'GoPay', slug: 'gopay', type: 'gopay', icon: '/static/images/credit-card-icon.png', is_active: true },
    { id: 5, name: 'OVO', slug: 'ovo', type: 'ovo', icon: '/static/images/credit-card-icon.png', is_active: true },
    { id: 6, name: 'DANA', slug: 'dana', type: 'dana', icon: '/static/images/credit-card-icon.png', is_active: true },
    { id: 7, name: 'QRIS', slug: 'qris', type: 'qris', icon: '/static/images/credit-card-icon.png', is_active: true },
    { id: 8, name: 'COD (Bayar di Tempat)', slug: 'cod', type: 'cod', icon: '/static/images/cod-icon.png', is_active: true },
  ];

  var analyticsData = {
    total_revenue: 156700000, total_orders: 234, total_products: 23, total_customers: 189,
    avg_order_value: 67000, conversion_rate: 12.5, period_revenue: 23500000, period_orders: 42,
    period_customers: 35, revenue_growth: 15.3, order_growth: 8.7,
  };

  var salesTrend = [];
  for (var t = 0; t < 30; t++) {
    var dd = new Date();
    dd.setDate(dd.getDate() - (29 - t));
    salesTrend.push({ date: dd.toISOString().slice(0, 10), revenue: 500000 + Math.floor(Math.random() * 1500000), orders: 5 + Math.floor(Math.random() * 30), customers: 3 + Math.floor(Math.random() * 20) });
  }

  var deviceAnalytics = [
    { device_type: 'mobile', visits: 1250, percentage: 58.4 },
    { device_type: 'desktop', visits: 680, percentage: 31.8 },
    { device_type: 'tablet', visits: 210, percentage: 9.8 },
  ];

  var mockPromos = [
    { id: 1, store: 1, promo_name: 'Diskon Lebaran', promo_type: 'percentage', promo_code: 'LEBARAN20', discount_percent: 20, discount_amount: 0, min_purchase: 50000, max_usage: 100, usage_count: 45, start_date: '2026-06-01', end_date: '2026-07-15', description: 'Diskon spesial menyambut Lebaran!', is_active: true, created_at: '2026-05-15T08:00:00Z', updated_at: '2026-06-01T08:00:00Z' },
    { id: 2, store: 1, promo_name: 'Gratis Ongkir Akhir Pekan', promo_type: 'free_shipping', promo_code: 'GRATISONGKIR', discount_percent: 0, discount_amount: 10000, min_purchase: 30000, max_usage: 50, usage_count: 23, start_date: '2026-06-10', end_date: '2026-06-30', description: 'Gratis ongkir setiap hari Sabtu & Minggu', is_active: true, created_at: '2026-06-01T08:00:00Z', updated_at: '2026-06-10T08:00:00Z' },
    { id: 3, store: 1, promo_name: 'Flash Sale Sayuran', promo_type: 'flash_sale', promo_code: 'FLASH50', discount_percent: 50, discount_amount: 0, min_purchase: 0, max_usage: 200, usage_count: 187, start_date: '2026-06-15', end_date: '2026-06-16', description: 'Flash sale 50% untuk semua produk sayuran!', is_active: true, created_at: '2026-06-10T08:00:00Z', updated_at: '2026-06-15T08:00:00Z' },
    { id: 4, store: 1, promo_name: 'Diskon 10rb', promo_type: 'fixed', promo_code: 'DISKON10', discount_percent: 0, discount_amount: 10000, min_purchase: 0, max_usage: 0, usage_count: 12, start_date: '2026-05-01', end_date: '2026-05-31', description: 'Diskon Rp10.000 tanpa minimal belanja', is_active: false, created_at: '2026-04-20T08:00:00Z', updated_at: '2026-05-01T08:00:00Z' },
    { id: 5, store: 1, promo_name: 'Beli 2 Gratis 1', promo_type: 'buy_x_get_y', promo_code: 'B2G1', discount_percent: 0, discount_amount: 0, min_purchase: 0, max_usage: 30, usage_count: 8, start_date: '2026-07-01', end_date: '2026-07-31', description: 'Beli 2 produk dapat 1 gratis!', is_active: true, created_at: '2026-06-20T08:00:00Z', updated_at: '2026-07-01T08:00:00Z' },
  ];

  var userActivities = [
    { id: 1, activity_type: 'product_added', description: 'Menambahkan produk baru: Wortel Impor', created_at: daysAgo(0) },
    { id: 2, activity_type: 'order_processed', description: 'Memproses pesanan WRG-20260606-003', created_at: daysAgo(0) },
    { id: 3, activity_type: 'store_updated', description: 'Memperbarui informasi toko', created_at: daysAgo(1) },
  ];

  var mockConversations = [
    {
      id: 1,
      subject: 'Tanya Stok Sayur',
      last_message_preview: 'Bayamnya ready Kak?',
      last_message_time: daysAgo(1),
      last_sender: 1,
      unread_count: 0,
      other_participant: {
        id: store.user,
        full_name: store.store_name,
        photo: '/static/images/store-icon-T.png'
      },
      created_at: daysAgo(2)
    },
    {
      id: 2,
      subject: 'Pengiriman Beras',
      last_message_preview: 'Sudah diproses ya Kak, sedang dikirim.',
      last_message_time: daysAgo(0),
      last_sender: store2.user,
      unread_count: 1,
      other_participant: {
        id: store2.user,
        full_name: store2.store_name,
        photo: '/static/images/store-icon-T.png'
      },
      created_at: daysAgo(1)
    }
  ];

  var mockMessages = {
    1: [
      { id: 1, conversation: 1, sender: 1, sender_name: 'Demo User', sender_photo: '', receiver: store.user, content: 'Halo, apakah bayamnya segar?', is_read: true, created_at: daysAgo(2) },
      { id: 2, conversation: 1, sender: store.user, sender_name: store.store_name, sender_photo: '/static/images/store-icon-T.png', receiver: 1, content: 'Halo Kak! Iya, baru dipetik pagi ini dari Lembang.', is_read: true, created_at: daysAgo(2) },
      { id: 3, conversation: 1, sender: 1, sender_name: 'Demo User', sender_photo: '', receiver: store.user, content: 'Bayamnya ready Kak?', is_read: true, created_at: daysAgo(1) }
    ],
    2: [
      { id: 4, conversation: 2, sender: 1, sender_name: 'Demo User', sender_photo: '', receiver: store2.user, content: 'Pesanan beras saya kapan dikirim ya?', is_read: true, created_at: daysAgo(1) },
      { id: 5, conversation: 2, sender: store2.user, sender_name: store2.store_name, sender_photo: '/static/images/store-icon-T.png', receiver: 1, content: 'Sudah diproses ya Kak, sedang dikirim.', is_read: false, created_at: daysAgo(0) }
    ]
  };

  // ──────────────────────────────────────────────────────────────────────────
  //  REAL API  — all methods delegate to auth.api() (works with real backend)
  // ──────────────────────────────────────────────────────────────────────────

  var RealAPI = {};

  function real(method, url, opts) {
    opts = opts || {};
    return function () {
      if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
      return auth.api(url, opts);
    };
  }

  function realWithBody(url, method, bodyKey) {
    return function () {
      if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
      return auth.api(url, { method: method, body: JSON.stringify(arguments.length > (bodyKey ? 1 : 0) ? arguments[0] : {}) });
    };
  }

  // Auth
  RealAPI.register = function (data) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/auth/register/', { method: 'POST', body: JSON.stringify(data) }); };
  RealAPI.login = function (email, password) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/auth/login/', { method: 'POST', body: JSON.stringify({ email: email, password: password }) }); };
  RealAPI.requestOTP = function (email, purpose) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/auth/otp/request/', { method: 'POST', body: JSON.stringify({ email: email, purpose: purpose || 'registration' }) }); };
  RealAPI.verifyOTP = function (email, otpCode, purpose) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/auth/otp/verify/', { method: 'POST', body: JSON.stringify({ email: email, otp_code: otpCode, purpose: purpose || 'registration' }) }); };
  RealAPI.forgotPassword = function (email) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/auth/forgot-password/', { method: 'POST', body: JSON.stringify({ email: email }) }); };
  RealAPI.resetPassword = function (email, otpCode, newPassword) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/auth/reset-password/', { method: 'POST', body: JSON.stringify({ email: email, otp_code: otpCode, new_password: newPassword, new_password2: newPassword }) }); };
  RealAPI.checkAuth = function () { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/auth/check-auth/'); };
  RealAPI.updateProfile = function (data) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/auth/profile/', { method: 'PATCH', body: JSON.stringify(data) }); };
  RealAPI.changePassword = function (data) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/auth/change-password/', { method: 'POST', body: JSON.stringify(data) }); };
  RealAPI.uploadProfilePhoto = function (file) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); var fd = new FormData(); fd.append('profile_photo', file); return auth.apiUpload('/auth/profile/', fd, 'PATCH'); };

  // Social auth
  RealAPI.socialLogin = function (provider, data) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/auth/social/' + provider + '/', { method: 'POST', body: JSON.stringify(data) }); };
  RealAPI.getSocialAuthConfig = function (provider) { if (!auth) return Promise.resolve({}); return auth.api('/auth/social/config/' + provider + '/').catch(function () { return {}; }); };
  RealAPI.getSocialAccounts = function () { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/auth/social/accounts/'); };
  RealAPI.unlinkSocialAccount = function (provider) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/auth/social/accounts/', { method: 'DELETE', body: JSON.stringify({ provider: provider }) }); };

  // Stores
  RealAPI.getStores = function (params) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); var qs = params ? new URLSearchParams(params).toString() : ''; return auth.api('/stores/' + (qs ? '?' + qs : '')); };
  RealAPI.getStore = function (id) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/stores/' + id + '/'); };
  RealAPI.createStore = function (data) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/stores/create/', { method: 'POST', body: JSON.stringify(data) }); };
  RealAPI.getMyStore = function () { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/stores/my-store/'); };
  RealAPI.updateStore = function (id, data) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/stores/' + id + '/', { method: 'PATCH', body: JSON.stringify(data) }); };
  RealAPI.followStore = function (id) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/stores/' + id + '/follow/', { method: 'POST' }); };
  RealAPI.unfollowStore = function (id) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/stores/' + id + '/unfollow/', { method: 'POST' }); };

  // Products
  RealAPI.getProducts = function (params) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); var qs = params ? new URLSearchParams(params).toString() : ''; return auth.api('/products/' + (qs ? '?' + qs : '')); };
  RealAPI.getMyProducts = function (params) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); var qs = params ? new URLSearchParams(params).toString() : ''; return auth.api('/products/my-products/' + (qs ? '?' + qs : '')); };
  RealAPI.getCategories = function () { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/products/categories/'); };
  RealAPI.getProduct = function (id) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/products/' + id + '/'); };
  RealAPI.createProduct = function (data) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/products/create/', { method: 'POST', body: JSON.stringify(data) }); };
  RealAPI.updateProduct = function (id, data) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/products/' + id + '/manage/', { method: 'PATCH', body: JSON.stringify(data) }); };
  RealAPI.deleteProduct = function (id) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/products/' + id + '/manage/', { method: 'DELETE' }); };
  RealAPI.getProductReviews = function (productId) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/products/' + productId + '/reviews/'); };
  RealAPI.getProductFavorite = function (productId) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/products/' + productId + '/favorite/'); };
  RealAPI.toggleFavorite = function (productId) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/products/' + productId + '/favorite/', { method: 'POST' }); };

  // Seller Store Reviews
  RealAPI.getStoreReviews = function (params) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); var qs = params ? new URLSearchParams(params).toString() : ''; return auth.api('/products/store-reviews/' + (qs ? '?' + qs : '')); };

  // Seller Promos
  RealAPI.getSellerPromos = function () { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/products/seller-promos/'); };
  RealAPI.createSellerPromo = function (data) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/products/seller-promos/', { method: 'POST', body: JSON.stringify(data) }); };
  RealAPI.updateSellerPromo = function (id, data) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/products/seller-promos/' + id + '/', { method: 'PATCH', body: JSON.stringify(data) }); };
  RealAPI.deleteSellerPromo = function (id) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/products/seller-promos/' + id + '/', { method: 'DELETE' }); };

  // Cart
  RealAPI.getCart = function () { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/orders/cart/'); };
  RealAPI.getCartCount = function () { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/orders/cart/count/'); };
  RealAPI.addToCart = function (data) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/orders/cart/', { method: 'POST', body: JSON.stringify(data) }); };
  RealAPI.updateCartItem = function (itemId, data) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/orders/cart/' + itemId + '/', { method: 'PATCH', body: JSON.stringify(data) }); };
  RealAPI.removeCartItem = function (itemId) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/orders/cart/' + itemId + '/', { method: 'DELETE' }); };
  RealAPI.clearCart = function () { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/orders/cart/clear/', { method: 'DELETE' }); };
  RealAPI.checkout = function (data) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/orders/create/', { method: 'POST', body: JSON.stringify(data) }); };
  RealAPI.checkVoucher = function (code, total) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/products/check-voucher/', { method: 'POST', body: JSON.stringify({ code: code, total: total }) }); };

  // Orders
  RealAPI.getOrders = function (params) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); var qs = params ? new URLSearchParams(params).toString() : ''; return auth.api('/orders/my-orders/' + (qs ? '?' + qs : '')); };
  RealAPI.getSellerOrders = function (params) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); var qs = params ? new URLSearchParams(params).toString() : ''; return auth.api('/orders/seller/' + (qs ? '?' + qs : '')); };
  RealAPI.getOrder = function (id) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/orders/' + id + '/'); };
  RealAPI.getDeliveryTracking = function (orderId) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/orders/' + orderId + '/tracking/'); };
  RealAPI.createOrder = function (data) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/orders/create/', { method: 'POST', body: JSON.stringify(data) }); };
  RealAPI.updateOrderStatus = function (orderId, status, courier, trackingNumber, cancelReason, cancelReasonText, extraFields) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    extraFields = extraFields || {};
    var body = { status: status };
    if (courier) body.courier = courier;
    if (trackingNumber) body.tracking_number = trackingNumber;
    if (cancelReason) body.cancel_reason = cancelReason;
    if (cancelReasonText) body.cancel_reason_text = cancelReasonText;
    if (extraFields.driver_name) body.driver_name = extraFields.driver_name;
    if (extraFields.driver_phone) body.driver_phone = extraFields.driver_phone;
    if (extraFields.pickup_code) body.pickup_code = extraFields.pickup_code;
    if (extraFields.estimated_time) body.estimated_time = extraFields.estimated_time;
    if (extraFields.estimated_pickup) body.estimated_pickup = extraFields.estimated_pickup;
    return auth.api('/orders/' + orderId + '/status/', { method: 'POST', body: JSON.stringify(body) });
  };
  RealAPI.cancelOrder = function (orderId, reason, reasonText) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    var body = {};
    if (reason) body.reason = reason;
    if (reasonText) body.reason_text = reasonText;
    return auth.api('/orders/' + orderId + '/cancel/', { method: 'POST', body: JSON.stringify(body) });
  };

  // Payments
  RealAPI.getShippingMethods = function () { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/orders/shipping-methods/'); };
  RealAPI.getPaymentMethods = function () { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/payments/methods/'); };
  RealAPI.getPaymentConfig = function () { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/payments/config/'); };
  RealAPI.createSnapTransaction = function (orderId, paymentMethod, bank) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); var data = { order_id: orderId, payment_method: paymentMethod || 'bank_transfer' }; if (bank) data.bank = bank; return auth.api('/payments/create-snap/', { method: 'POST', body: JSON.stringify(data) }); };
  RealAPI.getPaymentStatus = function (orderId) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/payments/status/' + orderId + '/'); };
  RealAPI.topUpWallet = function (amount) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/payments/wallet/topup/', { method: 'POST', body: JSON.stringify({ amount: amount }) }); };

  // Analytics
  RealAPI.getDashboardSummary = function (period) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/analytics/dashboard/?period=' + (period || 'month')); };
  RealAPI.getSalesTrend = function (period) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/analytics/sales/trend/?period=' + (period || '30')); };
  RealAPI.getDeviceAnalytics = function (period) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/analytics/devices/?period=' + (period || '30')); };
  RealAPI.getSellerReport = function (params) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); var qs = params ? new URLSearchParams(params).toString() : ''; return auth.api('/analytics/seller-report/' + (qs ? '?' + qs : '')); };
  RealAPI.getRealtimeAnalytics = function () { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/analytics/realtime/'); };
  RealAPI.getSalesAnalytics = function () { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/analytics/sales/'); };
  RealAPI.getDailyReports = function () { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/analytics/reports/'); };

  // Smart Scan AI Camera
  RealAPI.getSmartScanConfig = function () { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return Promise.resolve({ enabled: true, modes: ['barcode', 'ocr', 'computer_vision', 'manual'] }); };
  RealAPI.createSmartScanSession = function (deviceType) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return Promise.resolve({ session_id: 'smartscan-session-' + Math.random().toString(36).substr(2, 9), device_type: deviceType || 'desktop', created_at: new Date().toISOString() }); };
  RealAPI.endSmartScanSession = function (sessionId) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return Promise.resolve({ message: 'Sesi Smart Scan berakhir.', session_id: sessionId }); };
  RealAPI.processSmartScan = function (imageData, productId, scanType, options) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    options = options || {};
    // Delegate to server-side Smart Scan endpoint
    return auth.api('/products/smart-scan/', {
      method: 'POST',
      body: JSON.stringify({
        product_id: Number(productId),
        scan_type: scanType,
        options: {
          barcode: options.barcode,
          bpom_number: options.bpom_number,
          expiration_date: options.expiration_date,
        },
      }),
    }).then(function (result) {
      // Ensure frontend-compatible fields
      result.mode = result.mode || scanType;
      result.confidence = result.confidence || 0.94;
      result.confidence_uncertain = result.confidence_uncertain || false;
      result.eligible_for_sale = result.eligible_for_sale !== false;
      result.product_type = result.product?.product_name || 'Produk';
      return result;
    });
  };
  RealAPI.getQualityChecks = function (productId) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/products/' + productId + '/quality-checks/'); };

  // Notifications
  RealAPI.getNotifications = function (params) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); var qs = params ? new URLSearchParams(params).toString() : ''; return auth.api('/notifications/' + (qs ? '?' + qs : '')); };
  RealAPI.markNotificationRead = function (id) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/notifications/' + id + '/read/', { method: 'POST' }); };
  RealAPI.markAllNotificationsRead = function () { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/notifications/read-all/', { method: 'POST' }); };

  // Favorite Stores (followed stores)
  RealAPI.getFollowedStores = function () { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/stores/my-followed/'); };
  RealAPI.checkFollowStatus = function (storeId) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/stores/' + storeId + '/follow/'); };

  // Recently Viewed
  RealAPI.recordProductView = function (productId) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/products/recently-viewed/', { method: 'POST', body: JSON.stringify({ product_id: productId }) }); };
  RealAPI.getRecentlyViewed = function () { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/products/recently-viewed/'); };

  // Smart Search (autocomplete)
  RealAPI.searchSuggestions = function (q) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/products/search-suggestions/?q=' + encodeURIComponent(q || '')); };

  // Search History (client-side localStorage)
  RealAPI.getSearchHistory = function () {
    try {
      var history = JSON.parse(localStorage.getItem('warungio_search_history') || '[]');
      return Promise.resolve({ count: history.length, results: history });
    } catch (e) {
      return Promise.resolve({ count: 0, results: [] });
    }
  };
  RealAPI.saveSearchHistory = function (query) {
    try {
      var history = JSON.parse(localStorage.getItem('warungio_search_history') || '[]');
      // Remove duplicate if exists
      history = history.filter(function (h) { return h.query.toLowerCase() !== query.toLowerCase(); });
      // Add to front
      history.unshift({ query: query, timestamp: new Date().toISOString() });
      // Keep max 10
      if (history.length > 10) history = history.slice(0, 10);
      localStorage.setItem('warungio_search_history', JSON.stringify(history));
      return Promise.resolve({ message: 'Tersimpan.', count: history.length });
    } catch (e) {
      return Promise.resolve({ message: 'Gagal menyimpan.', count: 0 });
    }
  };
  RealAPI.clearSearchHistory = function () {
    try {
      localStorage.removeItem('warungio_search_history');
      return Promise.resolve({ message: 'Riwayat pencarian dihapus.' });
    } catch (e) {
      return Promise.resolve({ message: 'Gagal menghapus.' });
    }
  };

  // Refunds
  RealAPI.getMyRefunds = function (params) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); var qs = params ? new URLSearchParams(params).toString() : ''; return auth.api('/refunds/my-refunds/' + (qs ? '?' + qs : '')); };
  RealAPI.getRefund = function (id) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/refunds/' + id + '/'); };
  RealAPI.createRefund = function (data) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/refunds/create/', { method: 'POST', body: JSON.stringify(data) }); };
  RealAPI.cancelRefund = function (id) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/refunds/' + id + '/cancel/', { method: 'POST' }); };
  RealAPI.getStoreRefunds = function (params) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); var qs = params ? new URLSearchParams(params).toString() : ''; return auth.api('/refunds/store-refunds/' + (qs ? '?' + qs : '')); };
  RealAPI.sellerRefundAction = function (id, data) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/refunds/' + id + '/seller-action/', { method: 'POST', body: JSON.stringify(data) }); };
  RealAPI.getAdminRefunds = function (params) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); var qs = params ? new URLSearchParams(params).toString() : ''; return auth.api('/refunds/admin/all/' + (qs ? '?' + qs : '')); };
  RealAPI.adminRefundAction = function (id, data) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/refunds/' + id + '/admin-action/', { method: 'POST', body: JSON.stringify(data) }); };
  RealAPI.getRefundStats = function () { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/refunds/stats/'); };

  // Stock Alerts
  RealAPI.getLowStockProducts = function (threshold) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/products/low-stock/?threshold=' + (threshold || 5)); };

  // Chat
  RealAPI.getConversations = function () { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/chat/conversations/'); };
  RealAPI.getConversationMessages = function (conversationId) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/chat/conversations/' + conversationId + '/messages/'); };
  RealAPI.sendMessage = function (data) { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/chat/messages/send/', { method: 'POST', body: JSON.stringify(data) }); };
  RealAPI.getUnreadChatCount = function () { if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' }); return auth.api('/chat/unread-count/'); };

  // ──────────────────────────────────────────────────────────────────────────
  //  MOCK HANDLERS  — only used when window.MOCK_API = true
  // ──────────────────────────────────────────────────────────────────────────

  var MockHandlers = {};

  MockHandlers.getConversations = function () { return ok({ results: mockConversations }); };
  MockHandlers.getConversationMessages = function (conversationId) {
    var cid = Number(conversationId);
    var list = mockMessages[cid] || [];
    return ok({ results: list });
  };
  MockHandlers.sendMessage = function (data) {
    var cid = Number(data.conversation_id || 1);
    if (!mockMessages[cid]) mockMessages[cid] = [];
    var newMsg = {
      id: uid(),
      conversation: cid,
      sender: user.id,
      sender_name: user.full_name,
      sender_photo: '',
      receiver: data.receiver_id || 1,
      content: data.content,
      is_read: false,
      created_at: new Date().toISOString()
    };
    mockMessages[cid].push(newMsg);
    
    // Simulate assistant reply
    if (cid === 1 || data.receiver_id === 1) {
      setTimeout(function() {
        var reply = {
          id: uid(),
          conversation: cid,
          sender: 1, // Admin/Assistant
          sender_name: 'Warungio Assistant',
          sender_photo: '/static/images/store-icon-T.png',
          receiver: user.id,
          content: 'Halo! Terima kasih telah menghubungi kami. Kami akan membantu Anda secepatnya.',
          is_read: false,
          created_at: new Date().toISOString()
        };
        mockMessages[cid].push(reply);
      }, 1000);
    }
    
    return ok(newMsg);
  };
  MockHandlers.getUnreadChatCount = function () { return ok({ unread_count: 1 }); };

  MockHandlers.register = function (data) {
    user.id = uid(); user.email = data.email || user.email; user.full_name = data.full_name || data.name || user.full_name;
    user.phone = data.phone || user.phone; user.address = data.address || user.address; user.role = data.role || 'buyer';
    user.is_verified = false;
    var otpCode = String(100000 + Math.floor(Math.random() * 900000));
    return ok({ message: 'Registrasi berhasil. Silakan verifikasi OTP.', user: user, otp_code: otpCode });
  };

  MockHandlers.login = function (email, password) {
    if (!email || !password) return fail('Email dan password harus diisi.');
    if (email === 'seller@warungio.id' || email === 'seller') {
      user = sellerUser;
      return ok({ message: 'Login berhasil.', access: 'mock_access_' + Date.now(), refresh: 'mock_refresh_' + Date.now(), user: sellerUser });
    }
    user.is_verified = true;
    return ok({ message: 'Login berhasil.', access: 'mock_access_' + Date.now(), refresh: 'mock_refresh_' + Date.now(), user: user });
  };

  MockHandlers.requestOTP = function (email, purpose) { return ok({ message: 'Kode OTP telah dikirim.', otp_code: String(100000 + Math.floor(Math.random() * 900000)), expires_in_minutes: 5 }); };
  MockHandlers.verifyOTP = function () { user.is_verified = true; return ok({ message: 'Verifikasi OTP berhasil.', verified: true }); };
  MockHandlers.forgotPassword = function (email) { return ok({ message: 'Kode reset password telah dikirim ke email Anda.', otp_code: '123456' }); };
  MockHandlers.resetPassword = function () { return ok({ message: 'Password berhasil direset. Silakan login dengan password baru.' }); };
  MockHandlers.checkAuth = function () { return ok({ authenticated: true, user: user }); };
  MockHandlers.updateProfile = function (data) { Object.keys(data).forEach(function (k) { if (data[k] !== undefined) user[k] = data[k]; }); return ok({ message: 'Profil berhasil diperbarui.', user: user }); };
  MockHandlers.changePassword = function () { return ok({ message: 'Password berhasil diubah.' }); };
  MockHandlers.uploadProfilePhoto = function (file) { user.profile_photo = URL.createObjectURL(file); return ok({ message: 'Foto profil berhasil diunggah.', user: user }); };

  MockHandlers.socialLogin = function (provider, data) { user.is_verified = true; return ok({ message: 'Login berhasil dengan ' + provider, access: 'mock_access_' + Date.now(), refresh: 'mock_refresh_' + Date.now(), user: user }); };
  MockHandlers.getSocialAuthConfig = function () { return ok({ google_client_id: 'mock-google-client-id.apps.googleusercontent.com' }); };
  MockHandlers.getSocialAccounts = function () { return ok([]); };
  MockHandlers.unlinkSocialAccount = function () { return ok({ message: 'Akun sosial berhasil diputuskan.' }); };

  MockHandlers.getStores = function (params) {
    var list = [store, store2];
    if (params && params.search) { var q = params.search.toLowerCase(); list = list.filter(function (s) { return s.store_name.toLowerCase().indexOf(q) !== -1; }); }
    return ok({ count: list.length, results: list });
  };
  MockHandlers.getStore = function (id) { id = Number(id); if (id === store.id) return ok(store); if (id === store2.id) return ok(store2); return fail('Toko tidak ditemukan.', 404); };
  MockHandlers.createStore = function (data) { store.store_name = data.store_name || store.store_name; store.description = data.description || store.description; store.city = data.city || store.city; store.id = uid(); user.role = 'seller'; return ok({ message: 'Toko berhasil dibuat.', store: store }); };
  MockHandlers.updateStore = function (id, data) { Object.keys(data).forEach(function (k) { if (data[k] !== undefined) store[k] = data[k]; }); return ok(store); };
  MockHandlers.followStore = function () { store.follower_count = (store.follower_count || 0) + 1; return ok({ message: 'Berhasil mengikuti toko.', is_following: true }); };
  MockHandlers.unfollowStore = function () { store.follower_count = Math.max(0, (store.follower_count || 1) - 1); return ok({ message: 'Berhenti mengikuti toko.', is_following: false }); };

  MockHandlers.getProducts = function (params) { params = params || {}; var list = filterProducts(params); return ok({ count: list.length, results: list, next: null, previous: null }); };
  MockHandlers.getProduct = function (id) { var p = products.find(function (pr) { return pr.id === Number(id); }); return p ? ok(p) : fail('Produk tidak ditemukan.', 404); };
  MockHandlers.createProduct = function (data) {
    var p = { id: uid(), store: 1, store_name: 'Vega Fresh', category: Number(data.category) || 1, category_name: 'Sayuran', product_name: data.product_name || 'Produk Baru', slug: (data.product_name || 'produk-baru').toLowerCase().replace(/\s+/g, '-'), product_photo: data.product_photo || '/static/images/paket-sayur.png', description: data.description || '', price: Number(data.price) || 0, stock: Number(data.stock) || 0, unit: data.unit || 'pcs', sold_count: 0, rating_avg: 0, review_count: 0, is_active: true, is_featured: false, product_status: 'available', quality_score: 90, weight: Number(data.weight) || 0, created_at: new Date().toISOString() };
    products.push(p); store.product_count = products.filter(function (pr) { return pr.store === 1; }).length;
    return ok({ message: 'Produk berhasil ditambahkan.', product: p });
  };
  MockHandlers.updateProduct = function (id, data) { var p = products.find(function (pr) { return pr.id === Number(id); }); if (!p) return fail('Produk tidak ditemukan.', 404); Object.keys(data).forEach(function (k) { if (data[k] !== undefined) p[k] = data[k]; }); return ok(p); };
  MockHandlers.deleteProduct = function (id) { var idx = products.findIndex(function (pr) { return pr.id === Number(id); }); if (idx === -1) return fail('Produk tidak ditemukan.', 404); products.splice(idx, 1); store.product_count = products.filter(function (pr) { return pr.store === 1; }).length; return ok({ message: 'Produk berhasil dihapus.' }); };
  MockHandlers.getProductReviews = function () { return ok({ count: 0, results: [] }); };

  // Store Reviews mock
  var mockStoreReviews = [
    { id: 1, user: { id: 10, full_name: 'Siti Rahmawati' }, user_name: 'Siti Rahmawati', user_photo: null, product: 1, product_name: 'Bayam Segar', rating: 5, comment: 'Bayamnya segar banget! Besar-besar daunnya.', is_verified: true, seller_reply: 'Terima kasih Kak Siti!', seller_reply_at: '2026-06-25T14:00:00Z', created_at: '2026-06-25T10:30:00Z' },
    { id: 2, user: { id: 11, full_name: 'Ahmad Fauzi' }, user_name: 'Ahmad Fauzi', user_photo: null, product: 3, product_name: 'Apel Fuji', rating: 4, comment: 'Apelnya manis dan renyah.', is_verified: true, seller_reply: null, seller_reply_at: null, created_at: '2026-06-24T08:15:00Z' },
    { id: 3, user: { id: 12, full_name: 'Dewi Lestari' }, user_name: 'Dewi Lestari', user_photo: null, product: 5, product_name: 'Daging Sapi Giling', rating: 5, comment: 'Dagingnya fresh, tidak bau.', is_verified: true, seller_reply: 'Alhamdulillah, terima kasih!', seller_reply_at: '2026-06-23T19:30:00Z', created_at: '2026-06-23T16:45:00Z' },
    { id: 4, user: { id: 13, full_name: 'Bambang Susilo' }, user_name: 'Bambang Susilo', user_photo: null, product: 10, product_name: 'Bawang Merah 250g', rating: 3, comment: 'Bawangnya sedang aja.', is_verified: true, seller_reply: null, seller_reply_at: null, created_at: '2026-06-22T11:20:00Z' },
    { id: 5, user: { id: 14, full_name: 'Rina Marlina' }, user_name: 'Rina Marlina', user_photo: null, product: 4, product_name: 'Pisang Cavendish', rating: 5, comment: 'Pisang manis sekali!', is_verified: true, seller_reply: 'Terima kasih Kak Rina!', seller_reply_at: '2026-06-21T12:15:00Z', created_at: '2026-06-21T09:00:00Z' },
    { id: 6, user: { id: 15, full_name: 'Fitriani' }, user_name: 'Fitriani', user_photo: null, product: 1, product_name: 'Bayam Segar', rating: 5, comment: 'Recommended!', is_verified: true, seller_reply: null, seller_reply_at: null, created_at: '2026-06-19T13:45:00Z' },
  ];
  MockHandlers.getStoreReviews = function () { return ok({ count: mockStoreReviews.length, results: mockStoreReviews }); };

  MockHandlers.getCart = function () { return ok({ count: cartItems.length, results: cartItems }); };
  MockHandlers.getCartCount = function () { var count = cartItems.reduce(function (s, i) { return s + i.qty; }, 0); return ok({ count: count }); };
  MockHandlers.addToCart = function (data) {
    var productId = Number(data.product); var qty = Number(data.qty) || 1; var product = products.find(function (p) { return p.id === productId; });
    if (!product) return fail('Produk tidak ditemukan.', 404);
    var existing = cartItems.find(function (c) { return c.product.id === productId; });
    if (existing) { existing.qty += qty; return ok(existing); }
    var item = { id: uid(), product: product, qty: qty }; cartItems.push(item); return ok(item);
  };
  MockHandlers.updateCartItem = function (itemId, data) { var item = cartItems.find(function (c) { return c.id === Number(itemId); }); if (!item) return fail('Item keranjang tidak ditemukan.', 404); if (data.qty !== undefined) item.qty = Number(data.qty); return ok(item); };
  MockHandlers.removeCartItem = function (itemId) { var idx = cartItems.findIndex(function (c) { return c.id === Number(itemId); }); if (idx === -1) return fail('Item keranjang tidak ditemukan.', 404); cartItems.splice(idx, 1); return ok({ message: 'Item berhasil dihapus dari keranjang.' }); };
  MockHandlers.clearCart = function () { cartItems = []; return ok({ message: 'Keranjang berhasil dikosongkan.' }); };
  MockHandlers.checkout = function (data) {
    var newOrder = { id: uid(), order_number: 'WRG-DEMO-' + String(Date.now()).slice(-6), user: user, store: store, items: cartItems.map(function (c) { return { id: uid(), product: c.product, product_name: c.product.product_name, qty: c.qty, price: c.product.price, subtotal: c.qty * c.product.price }; }), subtotal: cartItems.reduce(function (s, c) { return s + c.qty * c.product.price; }, 0), shipping_cost: Number(data.shipping_cost) || 5000, discount: 0, total_price: 0, order_status: 'pending', payment_method: data.payment_method || 'cod', payment_status: 'unpaid', delivery_address: data.delivery_address || user.address, recipient_name: data.recipient_name || user.full_name, recipient_phone: data.recipient_phone || user.phone, notes: data.notes || '', created_at: new Date().toISOString() };
    newOrder.total_price = newOrder.subtotal + newOrder.shipping_cost - newOrder.discount; orders.unshift(newOrder); cartItems = [];
    return ok({ message: 'Pesanan berhasil dibuat.', orders: [newOrder] });
  };
  MockHandlers.checkVoucher = function (code, total) {
    if (code && code.toLowerCase() === 'warungio10') return ok({ valid: true, discount: 10000, code: code, message: 'Voucher berlaku!' });
    if (code && code.toLowerCase() === 'promo20') return ok({ valid: true, discount: Math.round(total * 0.2), code: code, message: 'Diskon 20%!' });
    return ok({ valid: false, error: 'Kode voucher tidak valid.' });
  };

  MockHandlers.getOrders = function (params) { params = params || {}; return ok({ count: filterOrders(orders, params).length, results: filterOrders(orders, params) }); };
  MockHandlers.getSellerOrders = function (params) { params = params || {}; var list = orders.filter(function (o) { return o.store && o.store.id === store.id; }); return ok({ count: filterOrders(list, params).length, results: filterOrders(list, params) }); };
  MockHandlers.getOrder = function (id) { var o = orders.find(function (ord) { return ord.id === Number(id); }); return o ? ok(o) : fail('Pesanan tidak ditemukan.', 404); };
  MockHandlers.createOrder = function (data) { return MockHandlers.checkout(data); };

  MockHandlers.updateOrderStatus = function (orderId, status) {
    var order = orders.find(function (o) { return o.id === Number(orderId); }); if (!order) return fail('Pesanan tidak ditemukan.', 404);
    order.order_status = status; if (status === 'completed') order.completed_at = new Date().toISOString();
    return ok({ message: 'Status pesanan berhasil diubah.', order: order });
  };
  MockHandlers.cancelOrder = function (orderId) {
    var order = orders.find(function (o) { return o.id === Number(orderId); }); if (!order) return fail('Pesanan tidak ditemukan.', 404);
    if (order.order_status !== 'pending' && order.order_status !== 'paid') return fail('Pesanan tidak dapat dibatalkan pada status saat ini.');
    order.order_status = 'cancelled'; return ok({ message: 'Pesanan berhasil dibatalkan.', order: order });
  };

  MockHandlers.getDeliveryTracking = function (orderId) {
    var order = orders.find(function (o) { return o.id === Number(orderId); }); if (!order) return fail('Pesanan tidak ditemukan.', 404);
    var delivery = deliveries.find(function (d) { return d.order === Number(orderId); });
    if (!delivery) {
      delivery = { id: uid(), order: order.id, shipping_method: shippingMethods[0], delivery_status: 'menunggu_penjemputan', courier_name: order.courier || 'GoSend', driver_name: 'Ahmad', driver_phone: '081312345678', pickup_code: '654321', tracking_number: order.tracking_number || 'TRK' + order.id, estimated_time: '30 menit lagi', picked_up_at: order.created_at, delivered_at: order.completed_at || null, created_at: order.created_at };
      deliveries.push(delivery);
    }
    var labels = { 'menunggu_konfirmasi': 'Menunggu Konfirmasi', 'diproses_penjual': 'Diproses Penjual', 'menunggu_penjemputan': 'Menunggu Penjemputan', 'kurir_menjemput': 'Kurir Menjemput', 'dalam_perjalanan': 'Dalam Perjalanan', 'pesanan_diterima': 'Pesanan Diterima', 'dibatalkan': 'Dibatalkan' };
    var milestones = [{ status: 'Pesanan dibuat', icon: 'package', time: order.created_at, is_current: false }];
    if (delivery.picked_up_at) milestones.push({ status: 'Kurir menjemput', icon: 'bike', time: delivery.picked_up_at, is_current: delivery.delivery_status === 'kurir_menjemput' });
    if (order.order_status === 'on_delivery' || delivery.delivery_status === 'dalam_perjalanan') milestones.push({ status: 'Dalam perjalanan', icon: 'truck', time: daysAgo(0), is_current: delivery.delivery_status === 'dalam_perjalanan' });
    if (order.order_status === 'completed' || delivery.delivered_at) milestones.push({ status: 'Pesanan diterima', icon: 'check', time: delivery.delivered_at || daysAgo(0), is_current: delivery.delivery_status === 'pesanan_diterima' });
    return ok({ courier: delivery.courier_name, delivery_status: delivery.delivery_status, delivery_status_label: labels[delivery.delivery_status] || delivery.delivery_status, status: order.order_status, milestones: milestones, driver_name: delivery.driver_name, driver_phone: delivery.driver_phone, pickup_code: delivery.pickup_code, estimated_time: delivery.estimated_time, source: 'hyperlocal' });
  };

  MockHandlers.getShippingMethods = function () { return ok({ count: shippingMethods.length, results: shippingMethods }); };
  MockHandlers.getPaymentMethods = function () { return ok({ count: paymentMethods.length, results: paymentMethods }); };
  MockHandlers.getPaymentConfig = function () { return ok({ client_key: 'SB-Mid-client-mock_key', snap_url: 'https://app.sandbox.midtrans.com/snap/snap.js', is_production: false, merchant_id: 'MOCK-MERCHANT' }); };
  MockHandlers.createSnapTransaction = function (orderId, paymentMethod) {
    var order = orders.find(function (o) { return o.id === Number(orderId); }); if (!order) return fail('Pesanan tidak ditemukan.', 404);
    order.payment_status = 'paid'; order.order_status = 'paid';
    return ok({ token: 'mock-snap-token-' + Date.now(), redirect_url: 'https://app.sandbox.midtrans.com/snap/v2/vtweb/mock', transaction_id: 'TRX-MOCK-' + Date.now(), payment: { id: uid(), order: order.id, amount: order.total_price, payment_status: 'pending', payment_type: paymentMethod || 'bank_transfer' } });
  };
  MockHandlers.getPaymentStatus = function (orderId) {
    var order = orders.find(function (o) { return o.id === Number(orderId); });
    if (!order) return ok({ status: 'no_payment' });
    return ok({ payment_status: order.payment_status || 'unpaid', payment_type: order.payment_method || 'bank_transfer', transaction_code: 'MOCK-TRX-' + order.id, amount: order.total_price || 0, paid_at: order.payment_status === 'paid' ? new Date().toISOString() : null });
  };

  MockHandlers.getDashboardSummary = function () { return ok(analyticsData); };
  MockHandlers.getSalesTrend = function () { return ok(salesTrend); };
  MockHandlers.getDeviceAnalytics = function () { return ok(deviceAnalytics); };
  MockHandlers.getRealtimeAnalytics = function () { return ok({ active_visitors: 12 + Math.floor(Math.random() * 20), today_orders: 3 + Math.floor(Math.random() * 8), today_revenue: 150000 + Math.floor(Math.random() * 400000), current_carts: 5 + Math.floor(Math.random() * 10) }); };
  MockHandlers.getSalesAnalytics = function () { return ok({ count: 7, results: salesTrend.slice(-7) }); };
  MockHandlers.getDailyReports = function () { return ok({ count: 7, results: salesTrend.slice(-7) }); };

  // Seller Promos
  MockHandlers.getSellerPromos = function () {
    var list = mockPromos.filter(function (p) { return p.store === store.id; });
    return ok({ count: list.length, results: list });
  };
  MockHandlers.createSellerPromo = function (data) {
    var newPromo = { id: uid(), store: store.id, usage_count: 0, created_at: new Date().toISOString(), updated_at: new Date().toISOString() };
    Object.keys(data).forEach(function (k) { if (data[k] !== undefined) newPromo[k] = data[k]; });
    mockPromos.unshift(newPromo);
    return ok(newPromo);
  };
  MockHandlers.updateSellerPromo = function (id, data) {
    var p = mockPromos.find(function (pr) { return pr.id === Number(id); });
    if (!p) return fail('Promo tidak ditemukan.', 404);
    Object.keys(data).forEach(function (k) { if (data[k] !== undefined) p[k] = data[k]; });
    p.updated_at = new Date().toISOString();
    return ok(p);
  };
  MockHandlers.deleteSellerPromo = function (id) {
    var idx = mockPromos.findIndex(function (p) { return p.id === Number(id); });
    if (idx === -1) return fail('Promo tidak ditemukan.', 404);
    mockPromos.splice(idx, 1);
    return ok({ message: 'Promo berhasil dihapus.' });
  };

  var mockQualityChecks = {};

  MockHandlers.getSmartScanConfig = function () { return ok({ enabled: true, modes: ['barcode', 'ocr', 'computer_vision', 'manual'], supported_devices: ['mobile', 'tablet', 'desktop'] }); };
  MockHandlers.createSmartScanSession = function (deviceType) { return ok({ session_id: 'smartscan-session-' + uid(), device_type: deviceType || 'desktop', created_at: new Date().toISOString() }); };
  MockHandlers.endSmartScanSession = function (sessionId) { return ok({ message: 'Sesi Smart Scan berakhir.', session_id: sessionId }); };
  MockHandlers.processSmartScan = function (imageData, productId, scanType, options) {
    var prod = products.find(function(p) { return p.id === Number(productId); }) || products[0];
    var pid = Number(productId);
    options = options || {};

    if (!mockQualityChecks[pid]) {
      mockQualityChecks[pid] = [
        { id: uid(), product: pid, quality_status: 'fresh', freshness_score: 95, stock_status: 'sufficient', ai_result: 'Produk terdeteksi sangat segar.', checked_at: daysAgo(2) },
        { id: uid(), product: pid, quality_status: 'normal', freshness_score: 82, stock_status: 'sufficient', ai_result: 'Produk terdeteksi cukup segar.', checked_at: daysAgo(5) }
      ];
    }

    if (scanType === 'computer_vision') {
      var freshness = options.freshness_score !== undefined ? Number(options.freshness_score) : 95;
      var qStatus = options.quality_status || 'fresh';
      var aiRes = 'Produk terdeteksi sebagai ' + prod.product_name + ' dengan tingkat kesegaran ' + freshness + '%. ';
      if (qStatus === 'fresh') {
        aiRes += 'Produk layak dijual dan disarankan diprioritaskan untuk promosi.';
      } else if (qStatus === 'warning') {
        aiRes += 'Tingkat kesegaran menurun. Disarankan mempercepat penjualan atau memberikan diskon.';
      } else if (qStatus === 'rejected') {
        aiRes += 'Kualitas buruk dan tidak layak dijual. Disarankan evaluasi pemasok.';
      }

      var newCheck = {
        id: uid(),
        product: pid,
        quality_status: qStatus,
        freshness_score: freshness,
        stock_status: 'sufficient',
        ai_result: aiRes,
        checked_at: new Date().toISOString()
      };
      mockQualityChecks[pid].unshift(newCheck);

      return ok({
        mode: 'computer_vision',
        product: prod,
        product_type: prod.product_name,
        freshness_score: freshness,
        confidence: options.confidence || 0.94,
        quality_status: qStatus,
        eligible_for_sale: qStatus !== 'rejected',
        ai_result: aiRes
      });
    } else if (scanType === 'ocr') {
      // Returns low confidence to require seller confirmation
      return ok({
        mode: 'ocr',
        product: prod,
        barcode: '8991234567890',
        expiration_date: '2027-12-31',
        bpom_number: 'MD 231456789012',
        confidence: 0.65,
        confidence_uncertain: true,
        ai_result: 'Produk kemasan terdeteksi OCR dengan tingkat kepercayaan rendah (0.65). Butuh konfirmasi seller.'
      });
    } else if (scanType === 'barcode') {
      var newCheck = {
        id: uid(),
        product: pid,
        quality_status: 'fresh',
        freshness_score: 100,
        stock_status: 'sufficient',
        ai_result: 'Produk kemasan terverifikasi Barcode: 8991234567890.',
        checked_at: new Date().toISOString()
      };
      mockQualityChecks[pid].unshift(newCheck);

      return ok({
        mode: 'barcode',
        product: prod,
        barcode: '8991234567890',
        confidence: 0.98,
        confidence_uncertain: false,
        ai_result: 'Produk kemasan terverifikasi Barcode: 8991234567890.'
      });
    } else if (scanType === 'manual') {
      var newCheck = {
        id: uid(),
        product: pid,
        quality_status: 'fresh',
        freshness_score: 100,
        stock_status: 'sufficient',
        ai_result: 'Konfirmasi Manual: Barcode: ' + (options.barcode || '8991234567890') + ', BPOM: ' + (options.bpom_number || 'MD 231456789012') + ', Exp: ' + (options.expiration_date || '2027-12-31') + '.',
        checked_at: new Date().toISOString()
      };
      mockQualityChecks[pid].unshift(newCheck);

      return ok({
        mode: 'manual',
        product: prod,
        barcode: options.barcode || '8991234567890',
        expiration_date: options.expiration_date || '2027-12-31',
        bpom_number: options.bpom_number || 'MD 231456789012',
        confidence: 1.0,
        ai_result: 'Metadata produk kemasan dikonfirmasi secara manual oleh seller.'
      });
    }
  };
  MockHandlers.getQualityChecks = function (productId) {
    var pid = Number(productId);
    if (!mockQualityChecks[pid]) {
      mockQualityChecks[pid] = [
        { id: uid(), product: pid, quality_status: 'fresh', freshness_score: 95, stock_status: 'sufficient', ai_result: 'Produk terdeteksi sangat segar.', checked_at: daysAgo(2) },
        { id: uid(), product: pid, quality_status: 'normal', freshness_score: 82, stock_status: 'sufficient', ai_result: 'Produk terdeteksi cukup segar.', checked_at: daysAgo(5) }
      ];
    }
    return ok({
      count: mockQualityChecks[pid].length,
      results: mockQualityChecks[pid]
    });
  };

  // ── Favorite Stores Mock ──
  var mockFollowedStores = [store];
  MockHandlers.getFollowedStores = function () { return ok({ count: mockFollowedStores.length, results: mockFollowedStores }); };
  MockHandlers.checkFollowStatus = function (storeId) {
    var is_following = mockFollowedStores.some(function (s) { return s.id === Number(storeId); });
    return ok({ is_following: is_following, count: mockFollowedStores.length });
  };

  // ── Favorites Mock ──
  var mockFavorites = [];
  MockHandlers.getProductFavorite = function (productId) {
    var is_fav = mockFavorites.some(function (f) { return f === Number(productId); });
    return ok({ is_favorite: is_fav });
  };
  MockHandlers.toggleFavorite = function (productId) {
    var idx = mockFavorites.indexOf(Number(productId));
    if (idx === -1) {
      mockFavorites.push(Number(productId));
      return ok({ message: 'Produk ditambahkan ke favorit.', is_favorite: true });
    } else {
      mockFavorites.splice(idx, 1);
      return ok({ message: 'Produk dihapus dari favorit.', is_favorite: false });
    }
  };

  // ── Refunds Mock ──
  var mockRefunds = [
    { id: 1, refund_number: 'RFN-A1B2C3D4', order: { id: 1, order_number: 'WRG-20260601-001' }, store_name: 'Vega Fresh', reason: 'product_damaged', reason_display: 'Produk Rusak/Cacat', amount_requested: 50000, amount_approved: null, refund_status: 'pending', status_display: 'Menunggu Review', is_escalated: false, created_at: daysAgo(1), resolved_at: null, store: { id: 1 }, buyer_name: 'Demo User', reason_text: 'Produk datang dalam kondisi rusak saat dibuka.', evidence_images: ['/static/images/paket-sayur.png'], seller_notes: '' },
    { id: 2, refund_number: 'RFN-E5F6G7H8', order: { id: 2, order_number: 'WRG-20260603-002' }, store_name: 'Vega Fresh', reason: 'expired', reason_display: 'Produk Kadaluarsa', amount_requested: 55000, amount_approved: 55000, refund_status: 'approved', status_display: 'Disetujui', is_escalated: false, created_at: daysAgo(3), resolved_at: daysAgo(1), store: { id: 1 }, buyer_name: 'Demo User', seller_notes: 'Mohon maaf, kami proses refund.' },
    { id: 3, refund_number: 'RFN-I9J0K1L2', order: { id: 3, order_number: 'WRG-20260606-003' }, store_name: 'Toko Berkah Jaya', reason: 'not_as_described', reason_display: 'Tidak Sesuai Deskripsi', amount_requested: 75000, amount_approved: 75000, refund_status: 'refunded', status_display: 'Telah Direfund', is_escalated: false, created_at: daysAgo(5), resolved_at: daysAgo(2), store: { id: 2 }, buyer_name: 'Siti Rahma', seller_notes: 'Dana sudah kami kembalikan.' },
  ];
  var mockRefundTimeline = {
    1: [
      { event_type: 'created', description: 'Refund diajukan dengan alasan: Produk Rusak/Cacat', created_by_name: 'Demo User', created_by_role: 'buyer', created_at: daysAgo(1) },
      { event_type: 'review_started', description: 'Review dimulai oleh penjual.', created_by_name: 'Vega Fresh', created_by_role: 'seller', created_at: daysAgo(1) },
    ],
    2: [
      { event_type: 'created', description: 'Refund diajukan dengan alasan: Produk Kadaluarsa', created_by_name: 'Demo User', created_by_role: 'buyer', created_at: daysAgo(3) },
      { event_type: 'approved', description: 'Refund disetujui oleh penjual. Jumlah: Rp 55,000.', created_by_name: 'Vega Fresh', created_by_role: 'seller', created_at: daysAgo(1) },
    ],
    3: [
      { event_type: 'created', description: 'Refund diajukan dengan alasan: Tidak Sesuai Deskripsi', created_by_name: 'Demo User', created_by_role: 'buyer', created_at: daysAgo(5) },
      { event_type: 'seller_responded', description: 'Penjual setuju untuk refund.', created_by_name: 'Toko Berkah Jaya', created_by_role: 'seller', created_at: daysAgo(4) },
      { event_type: 'refunded', description: 'Dana telah direfund.', created_by_name: 'System', created_by_role: 'system', created_at: daysAgo(2) },
    ],
  };

  MockHandlers.getMyRefunds = function () { return ok({ count: mockRefunds.length, results: mockRefunds }); };
  MockHandlers.getRefund = function (id) {
    var r = mockRefunds.find(function (rf) { return rf.id === Number(id); });
    if (!r) return fail('Refund tidak ditemukan.', 404);
    return ok({
      ...r,
      timeline: mockRefundTimeline[r.id] || [],
      order_items: [
        { id: 1, product_name: 'Bayam Segar', product_photo: '/static/images/paket-sayur.png', qty: 2, price: 5000, subtotal: 10000 },
        { id: 2, product_name: 'Apel Fuji', product_photo: '/static/images/fruit.png', qty: 1, price: 25000, subtotal: 25000 },
      ],
      store_logo: '/static/images/store-icon-T.png',
      evidence_description: 'Foto menunjukkan produk rusak',
    });
  };
  MockHandlers.createRefund = function (data) {
    var newRefund = {
      id: uid(), refund_number: 'RFN-' + uid(),
      order: { id: data.order, order_number: 'WRG-NEW-' + uid() },
      store_name: 'Vega Fresh', reason: data.reason || 'other',
      reason_display: 'Lainnya', amount_requested: Number(data.amount_requested) || 0,
      amount_approved: null, refund_status: 'pending', status_display: 'Menunggu Review',
      is_escalated: false, created_at: new Date().toISOString(), resolved_at: null,
      store: { id: 1 }, buyer_name: 'Demo User', seller_notes: '',
    };
    mockRefunds.unshift(newRefund);
    mockRefundTimeline[newRefund.id] = [
      { event_type: 'created', description: 'Refund diajukan', created_by_name: 'Demo User', created_by_role: 'buyer', created_at: new Date().toISOString() },
    ];
    return ok(newRefund);
  };
  MockHandlers.cancelRefund = function (id) {
    var r = mockRefunds.find(function (rf) { return rf.id === Number(id); });
    if (!r) return fail('Refund tidak ditemukan.', 404);
    r.refund_status = 'cancelled'; r.status_display = 'Dibatalkan';
    return ok({ message: 'Refund berhasil dibatalkan.' });
  };
  MockHandlers.getStoreRefunds = function () { return ok({ count: mockRefunds.length, results: mockRefunds }); };
  MockHandlers.sellerRefundAction = function (id, data) {
    var r = mockRefunds.find(function (rf) { return rf.id === Number(id); });
    if (!r) return fail('Refund tidak ditemukan.', 404);
    if (data.action === 'approve') {
      r.refund_status = 'approved'; r.status_display = 'Disetujui';
      r.amount_approved = data.amount_approved || r.amount_requested;
    } else if (data.action === 'reject') {
      r.refund_status = 'rejected'; r.status_display = 'Ditolak';
    } else if (data.action === 'negotiate') {
      r.refund_status = 'waiting_buyer'; r.status_display = 'Menunggu Pembeli';
      r.amount_approved = data.amount_approved;
    }
    return ok(r);
  };
  MockHandlers.getAdminRefunds = function () { return ok({ count: mockRefunds.length, results: mockRefunds }); };
  MockHandlers.adminRefundAction = function (id, data) {
    var r = mockRefunds.find(function (rf) { return rf.id === Number(id); });
    if (!r) return fail('Refund tidak ditemukan.', 404);
    if (data.action === 'resolve') {
      r.refund_status = 'refunded'; r.status_display = 'Telah Direfund';
      r.resolved_at = new Date().toISOString();
    }
    return ok(r);
  };
  MockHandlers.getRefundStats = function () {
    return ok({ total: 12, pending: 3, under_review: 2, approved: 4, rejected: 1, refunded: 2, cancelled: 0, escalated: 1, total_amount_requested: 4500000, total_amount_refunded: 3200000 });
  };

  // ── Recently Viewed Mock ──
  var mockRecentlyViewed = [
    { id: 1, product: products[0], product_detail: products[0], viewed_at: daysAgo(0) },
    { id: 2, product: products[2], product_detail: products[2], viewed_at: daysAgo(0) },
    { id: 3, product: products[4], product_detail: products[4], viewed_at: daysAgo(1) },
    { id: 4, product: products[6], product_detail: products[6], viewed_at: daysAgo(2) },
  ];
  MockHandlers.recordProductView = function (productId) {
    var prod = products.find(function (p) { return p.id === Number(productId); });
    if (prod) {
      var idx = mockRecentlyViewed.findIndex(function (r) { return r.product.id === Number(productId); });
      if (idx !== -1) mockRecentlyViewed.splice(idx, 1);
      mockRecentlyViewed.unshift({ id: uid(), product: prod, product_detail: prod, viewed_at: new Date().toISOString() });
      if (mockRecentlyViewed.length > 20) mockRecentlyViewed.pop();
    }
    return ok({ message: 'Produk dicatat.', viewed_at: new Date().toISOString() });
  };
  MockHandlers.getRecentlyViewed = function () { return ok({ count: mockRecentlyViewed.length, results: mockRecentlyViewed }); };

  // ── Search Suggestions Mock ──
  var mockCategories = [
    { id: 1, category_name: 'Sayuran' },
    { id: 2, category_name: 'Buah-buahan' },
    { id: 3, category_name: 'Daging & Ikan' },
    { id: 4, category_name: 'Sembako' },
  ];
  MockHandlers.searchSuggestions = function (q) {
    var query = (q || '').toLowerCase();
    if (query.length < 1) return ok({ suggestions: [], products: [], stores: [], categories: [] });
    var matchedProducts = products.filter(function (p) { return p.product_name.toLowerCase().indexOf(query) !== -1; }).slice(0, 5).map(function (p) { return { type: 'product', label: p.product_name, value: p.slug, id: p.id }; });
    var matchedStores = [store, store2].filter(function (s) { return s.store_name.toLowerCase().indexOf(query) !== -1; }).slice(0, 5).map(function (s) { return { type: 'store', label: s.store_name, value: s.slug, id: s.id, subtitle: s.city }; });
    var matchedCategories = mockCategories.filter(function (c) { return c.category_name.toLowerCase().indexOf(query) !== -1; }).slice(0, 5).map(function (c) { return { type: 'category', label: c.category_name, value: c.category_name.toLowerCase(), id: c.id }; });
    var all = matchedProducts.concat(matchedStores).concat(matchedCategories);
    return ok({ suggestions: all, products: matchedProducts, stores: matchedStores, categories: matchedCategories });
  };

  // ── Stock Alerts Mock ──
  MockHandlers.getLowStockProducts = function (threshold) {
    threshold = threshold || 5;
    var out_of_stock = [
      { id: 100, product_name: 'Telur Ayam', stock: 0, unit: 'kg', price: 28000, category: 'Sembako', product_photo: null, slug: 'telur-ayam' },
    ];
    var low_stock = [
      { id: 101, product_name: 'Bayam Segar', stock: 3, unit: 'ikat', price: 5000, category: 'Sayuran', product_photo: null, slug: 'bayam-segar' },
      { id: 102, product_name: 'Ikan Nila Segar', stock: 2, unit: 'kg', price: 35000, category: 'Daging & Ikan', product_photo: null, slug: 'ikan-nila-segar' },
    ];
    return ok({
      count: low_stock.length + out_of_stock.length,
      low_stock: low_stock,
      out_of_stock: out_of_stock,
      total_low_stock: low_stock.length,
      total_out_of_stock: out_of_stock.length,
    });
  };

  MockHandlers.getNotifications = function (params) {
    params = params || {};
    var list = notifications.slice();
    if (params.type) list = list.filter(function (n) { return n.notification_type === params.type; });
    if (params.unread === 'true') list = list.filter(function (n) { return !n.is_read; });
    return ok({ count: list.length, results: list });
  };
  MockHandlers.markNotificationRead = function (id) { var n = notifications.find(function (notif) { return notif.id === Number(id); }); if (n) n.is_read = true; return ok({ message: 'Notifikasi ditandai sudah dibaca.' }); };
  MockHandlers.markAllNotificationsRead = function () { notifications.forEach(function (n) { n.is_read = true; }); return ok({ message: 'Semua notifikasi ditandai sudah dibaca.' }); };

  // ──────────────────────────────────────────────────────────────────────────
  //  ASSEMBLY  — RealAPI first, then overlay mock if MOCK_API=true
  // ──────────────────────────────────────────────────────────────────────────

  var WarungioAPI = {};

  // Copy all real methods first
  Object.keys(RealAPI).forEach(function (k) {
    WarungioAPI[k] = RealAPI[k];
  });

  // If mock mode is active, overlay mock handlers with delay
  if (window.MOCK_API) {
    Object.keys(MockHandlers).forEach(function (k) {
      var mockFn = MockHandlers[k];
      WarungioAPI[k] = function () {
        var args = arguments;
        return delay().then(function () { return mockFn.apply(null, args); });
      };
    });
    console.info('WarungioAPI [MOCK MODE] — ' + Object.keys(MockHandlers).length + ' endpoints mocked');
  } else {
    console.info('WarungioAPI [LIVE MODE] — proxying to backend');
  }

  window.WarungioAPI = WarungioAPI;
})();
