/**
 * Home / Landing page - Warungio
 * Fetches products, stores, and categories from Django REST API.
 * Includes mobile responsive menu toggle.
 */
document.addEventListener('DOMContentLoaded', async () => {
  // ── Mobile Menu Toggle ──
  const menuToggle = document.getElementById('menuToggle');
  const sidebar = document.querySelector('.sidebar');
  if (menuToggle && sidebar) {
    // Create mobile drawer overlay
    const overlay = document.createElement('div');
    overlay.className = 'mobile-drawer-overlay';
    document.body.appendChild(overlay);

    // Clone sidebar content into mobile drawer
    const drawer = document.createElement('aside');
    drawer.className = 'mobile-drawer';
    drawer.innerHTML = sidebar.innerHTML;
    document.body.appendChild(drawer);

    function openMobileMenu() {
      drawer.classList.add('open');
      overlay.classList.add('open');
      document.body.style.overflow = 'hidden';
    }

    function closeMobileMenu() {
      drawer.classList.remove('open');
      overlay.classList.remove('open');
      document.body.style.overflow = '';
    }

    menuToggle.addEventListener('click', function() {
      if (drawer.classList.contains('open')) {
        closeMobileMenu();
      } else {
        openMobileMenu();
      }
    });

    overlay.addEventListener('click', closeMobileMenu);

    // Close on escape key
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && drawer.classList.contains('open')) {
        closeMobileMenu();
      }
    });

    // Close drawer when a nav link is clicked
    drawer.querySelectorAll('a').forEach(function(link) {
      link.addEventListener('click', closeMobileMenu);
    });
  }

  // ── Elements ──
  const productGrid = document.getElementById('product-grid') || document.querySelector('.product-grid');
  const storeGrid = document.getElementById('store-grid') || document.querySelector('.store-grid');
  const categoryList = document.getElementById('category-list') || document.querySelector('.category-list');
  const statsEl = document.getElementById('stats-container');

  // ── Load featured products ──
  async function loadProducts() {
    if (!productGrid) return;
    try {
      const data = await WarungioAPI.getProducts({ page: 1, pageSize: 8 });
      if (data.results && data.results.length > 0) {
        productGrid.innerHTML = '';
        data.results.forEach(p => {
          const price = 'Rp ' + Number(p.price).toLocaleString('id-ID');
          const img = p.image || WarungioAssets.img('vega-fresh.png');
          const rating = p.average_rating ? '★'.repeat(Math.round(p.average_rating)) : '★★★★☆';
          productGrid.innerHTML += `
            <div class="product-card" data-id="${p.id}">
              <img src="${img}" alt="${p.name}" loading="lazy" />
              <div class="card-body">
                <h3>${p.name}</h3>
                <p class="store-name">${p.store_name || 'Warung Lokal'}</p>
                <p class="price">${price}</p>
                <div class="rating"><span>${rating}</span><small>(${p.total_reviews || 0})</small></div>
                <button class="btn-buy" onclick="window.location.href='../auth/login/index.html'">Beli Sekarang</button>
              </div>
            </div>`;
        });
      }
    } catch (err) {
      // Static fallback — do nothing, HTML already has content
      console.warn('Products load fallback:', err);
    }
  }

  // ── Load stores ──
  async function loadStores() {
    if (!storeGrid) return;
    try {
      const data = await WarungioAPI.getStores({ page: 1, pageSize: 6 });
      if (data.results && data.results.length > 0) {
        storeGrid.innerHTML = '';
        data.results.forEach(s => {
          storeGrid.innerHTML += `
            <div class="store-card" data-id="${s.id}">
              <img src="${s.logo || WarungioAssets.img('store-icon-T.png')}" alt="${s.store_name}" />
              <h4>${s.store_name}</h4>
              <p>${s.city || ''}</p>
              <span class="store-badge">${s.category || 'Warung'}</span>
            </div>`;
        });
      }
    } catch (err) {
      console.warn('Stores load fallback:', err);
    }
  }

  // ── Load categories ──
  async function loadCategories() {
    if (!categoryList) return;
    try {
      const data = await WarungioAPI.getCategories();
      if (data.results && data.results.length > 0) {
        categoryList.innerHTML = '';
        data.results.forEach(cat => {
          categoryList.innerHTML += `<div class="category-item">${cat.name || cat}</div>`;
        });
      }
    } catch (err) {
      console.warn('Categories load fallback:', err);
    }
  }

  // ── Load dashboard stats ──
  async function loadStats() {
    if (!statsEl) return;
    try {
      const data = await WarungioAPI.getDashboardSummary('all');
      const stats = [
        { value: data.total_products || '500+', label: 'Produk' },
        { value: data.total_stores || '120+', label: 'Warung' },
        { value: data.total_orders || '1000+', label: 'Pesanan' },
        { value: '98%', label: 'Kepuasan' },
      ];
      statsEl.innerHTML = '';
      stats.forEach(s => {
        statsEl.innerHTML += `<div class="stat"><strong>${s.value}</strong><span>${s.label}</span></div>`;
      });
    } catch (err) {
      console.warn('Stats load fallback:', err);
    }
  }

  // ── Load all ──
  await Promise.all([loadProducts(), loadStores(), loadCategories(), loadStats()]);
});
