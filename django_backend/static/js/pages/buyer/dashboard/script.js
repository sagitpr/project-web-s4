/**
 * Buyer Dashboard (beranda) - Warungio
 * Connected to Django API for dynamic product/order/store display.
 */
document.addEventListener('DOMContentLoaded', async () => {
  // Check auth
  if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
    // Allow guest browsing
  }

  const productGrid = document.getElementById('product-grid') || document.querySelector('.product-grid');
  const categoryFilter = document.getElementById('category-filter') || document.querySelector('.category-filter');
  const searchInput = document.getElementById('search-input') || document.querySelector('.search-input');
  const searchBtn = document.getElementById('search-btn') || document.querySelector('.search-btn');
  const cartCount = document.getElementById('cart-count') || document.querySelector('.cart-count');
  const recommendedEl = document.getElementById('recommended-section') || document.querySelector('.recommended');

  let currentPage = 1;
  let currentCategory = '';
  let currentSearch = '';

  // ── Show loading skeleton ──
  function showLoadingSkeleton() {
    if (!productGrid) return;
    productGrid.innerHTML = '';
    for (let i = 0; i < 8; i++) {
      const sk = document.createElement('div');
      sk.className = 'product-card';
      sk.innerHTML = '<div class="skeleton skeleton-card" style="height:220px"></div><div class="card-body"><div class="skeleton skeleton-title"></div><div class="skeleton skeleton-text"></div><div class="skeleton skeleton-text" style="width:50%"></div></div>';
      productGrid.appendChild(sk);
    }
  }
  showLoadingSkeleton();

  // ── Load products ──
  async function loadProducts(page = 1, category = '', search = '') {
    if (!productGrid) return;
    try {
      const params = { page, pageSize: 12 };
      if (category) params.category = category;
      if (search) params.search = search;

      const data = await WarungioAPI.getProducts(params);
      if (data.results && data.results.length > 0) {
        productGrid.innerHTML = '';
        data.results.forEach(p => {
          const price = 'Rp ' + Number(p.price).toLocaleString('id-ID');
          const img = p.product_photo || p.image || WarungioAssets.img('vega-fresh.png');
          const name = p.product_name || p.name || 'Produk';
          const rating = p.rating_avg ? '★'.repeat(Math.round(p.rating_avg)) : '★★★★☆';
          const storeId = p.store || 0;
          productGrid.innerHTML += `
            <div class="product-card" data-id="${p.id}">
              <img src="${img}" alt="${name}" loading="lazy" />
              <div class="card-body">
                <h3>${name}</h3>
                <p class="store-name">${p.store_name || 'Warung Lokal'}</p>
                <p class="price">${price}</p>
                <div class="rating"><span>${rating}</span><small>(${p.review_count || p.total_reviews || 0})</small></div>
                <button class="btn-cart" data-product-id="${p.id}" data-store-id="${storeId}">
                  <i class="fa-solid fa-cart-plus"></i> Tambah
                </button>
              </div>
            </div>`;
        });

        // Add cart event listeners
        document.querySelectorAll('.btn-cart').forEach(btn => {
          btn.addEventListener('click', async (e) => {
            e.preventDefault();
            if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
              window.location.href = '/auth/login/';
              return;
            }
            const productId = parseInt(btn.dataset.productId);
            const storeId = parseInt(btn.dataset.storeId);
            try {
              await WarungioAPI.addToCart({ product: productId, qty: 1 });
              if (cartCount) cartCount.textContent = parseInt(cartCount.textContent || '0') + 1;
              btn.textContent = '✓ Ditambahkan';
              btn.style.background = '#22c55e';
              setTimeout(() => {
                btn.textContent = '<i class="fa-solid fa-cart-plus"></i> Tambah';
                btn.style.background = '';
              }, 2000);
            } catch (err) {
              console.warn('Cart add failed:', err);
            }
          });
        });

        // Pagination
        if (data.total_pages && data.total_pages > 1) {
          let pagHtml = '<div class="pagination">';
          for (let i = 1; i <= Math.min(data.total_pages, 5); i++) {
            pagHtml += `<button class="page-btn ${i === page ? 'active' : ''}" data-page="${i}">${i}</button>`;
          }
          pagHtml += '</div>';
          productGrid.insertAdjacentHTML('afterend', pagHtml);
          document.querySelectorAll('.page-btn').forEach(btn => {
            btn.addEventListener('click', () => {
              loadProducts(parseInt(btn.dataset.page), currentCategory, currentSearch);
            });
          });
        }
      }
    } catch (err) {
      console.warn('Products load fallback:', err);
    }
  }

  // ── Load categories filter ──
  async function loadCategories() {
    if (!categoryFilter) return;
    try {
      const data = await WarungioAPI.getCategories();
      if (data.results && data.results.length > 0) {
        let html = '<button class="cat-btn active" data-cat="">Semua</button>';
        data.results.forEach(cat => {
          html += `<button class="cat-btn" data-cat="${cat.id || cat.name}">${cat.name || cat}</button>`;
        });
        categoryFilter.innerHTML = html;
        categoryFilter.querySelectorAll('.cat-btn').forEach(btn => {
          btn.addEventListener('click', () => {
            categoryFilter.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentCategory = btn.dataset.cat;
            currentPage = 1;
            loadProducts(currentPage, currentCategory, currentSearch);
          });
        });
      }
    } catch (err) {
      console.warn('Categories load fallback:', err);
    }
  }

  // ── Search ──
  if (searchInput && searchBtn) {
    function doSearch() {
      currentSearch = searchInput.value.trim();
      currentPage = 1;
      loadProducts(currentPage, currentCategory, currentSearch);
    }
    searchBtn.addEventListener('click', doSearch);
    searchInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') doSearch(); });
  }

  // ── Load recommended products ──
  async function loadRecommended() {
    if (!recommendedEl) return;
    try {
      const data = await WarungioAPI.getProducts({ page: 1, pageSize: 4 });
      if (data.results && data.results.length > 0) {
        const container = recommendedEl.querySelector('.product-grid') || recommendedEl;
        container.innerHTML = '';
        data.results.forEach(p => {
          container.innerHTML += `
            <div class="product-card mini" data-id="${p.id}">
              <img src="${p.product_photo || p.image || WarungioAssets.img('vega-fresh.png')}" alt="${p.product_name || p.name}" />
              <h4>${p.product_name || p.name}</h4>
              <p>Rp ${Number(p.price).toLocaleString('id-ID')}</p>
            </div>`;
        });
      }
    } catch (err) {
      console.warn('Recommended load fallback:', err);
    }
  }

  // ── Load cart count ──
  async function loadCartCount() {
    if (!cartCount) return;
    if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) return;
    try {
      const data = await WarungioAPI.getCartCount();
      const count = data.count || 0;
      cartCount.textContent = count;
    } catch (err) {
      console.warn('Cart load fallback:', err);
    }
  }

  // ── Escape HTML helper ──
  function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ── Load recent orders (only if logged in) ──
  async function loadRecentOrders() {
    if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) return;

    const section = document.getElementById('ordersSection');
    const grid = document.getElementById('ordersDashboardGrid');
    if (!section || !grid) return;

    try {
      const data = await WarungioAPI.getOrders({ page: 1, pageSize: 6 });
      const orders = data.results || [];

      if (orders.length === 0) return;

      section.style.display = 'block';
      grid.innerHTML = '';

      const STATUS_LABELS = {
        pending: 'Menunggu', paid: 'Lunas', processed: 'Diproses',
        shipped: 'Dikirim', completed: 'Selesai', cancelled: 'Dibatalkan', refunded: 'Dikembalikan',
      };

      orders.forEach(function (o) {
        var statusKey = (o.order_status || 'pending').toLowerCase();
        var statusLabel = STATUS_LABELS[statusKey] || statusKey;
        var statusClass = statusKey;
        var itemNames = o.items ? o.items.map(function (i) { return i.product_name || 'Produk'; }).join(', ') : '-';
        if (itemNames.length > 60) itemNames = itemNames.substring(0, 57) + '...';

        var card = document.createElement('div');
        card.className = 'order-card-dash';
        card.innerHTML =
          '<div class="order-card-top">' +
            '<div>' +
              '<div class="order-card-number">' + (o.order_number || '#' + o.id) + '</div>' +
              (o.store_name ? '<div class="order-card-store">' + escapeHtml(o.store_name) + '</div>' : '') +
            '</div>' +
            '<span class="order-card-badge ' + statusClass + '">' + statusLabel + '</span>' +
          '</div>' +
          '<div class="order-card-body">' +
            '<span class="order-card-item">' + escapeHtml(itemNames) + '</span>' +
          '</div>' +
          '<div class="order-card-footer">' +
            '<span class="order-card-total">Rp ' + Number(o.total_price || 0).toLocaleString('id-ID') + '</span>' +
            '<a href="/buyer/order-detail/?id=' + o.id + '" class="order-card-link">' +
              'Lihat Detail' +
              '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>' +
            '</a>' +
          '</div>';
        grid.appendChild(card);
      });
    } catch (err) {
      console.warn('Recent orders load fallback:', err);
    }
  }

  // ── Init ──
  await Promise.all([loadProducts(), loadCategories(), loadRecommended(), loadCartCount(), loadRecentOrders()]);
});
