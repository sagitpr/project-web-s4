/**
 * Warungio Buyer — Products Catalog (Consolidated)
 * Single source of truth for catalog browsing: categories, search, filters, sorting, pagination, wishlist, cart.
 */
(function () {
  'use strict';

  /* ── State ── */
  var currentPage = 1;
  var currentCategory = 'all';
  var currentSearch = '';
  var currentSort = '';
  var appendedMode = false;
  var cache = { products: [], categories: [] };
  var PAGE_SIZE = 20;

  /* ── Helpers ── */
  function $(id) { return document.getElementById(id); }

  function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function toRupiah(num) {
    return 'Rp ' + Number(num || 0).toLocaleString('id-ID');
  }

  function showToast(msg, type) {
    var c = $('toastContainer');
    if (!c) {
      c = document.createElement('div');
      c.id = 'toastContainer';
      c.className = 'toast-container';
      document.body.appendChild(c);
    }
    var t = document.createElement('div');
    t.className = 'toast toast-' + (type || 'info');
    t.innerHTML = '<span>' + escapeHtml(msg) + '</span>';
    c.appendChild(t);
    setTimeout(function () { if (t.parentNode) t.remove(); }, 4000);
  }

  /* ── Load Categories ── */
  async function loadCategories() {
    try {
      if (window.WarungioAPI && window.WarungioAPI.getCategories) {
        var data = await WarungioAPI.getCategories();
        cache.categories = data.results || data || [];
      }
    } catch (e) { console.warn('Categories load error:', e); }

    var filterBar = $('categoryFilter');
    if (!filterBar) return;

    // Clear existing (keep "Semua")
    var allBtn = filterBar.querySelector('[data-category="all"]');
    filterBar.innerHTML = '';
    if (allBtn) filterBar.appendChild(allBtn);
    else {
      var defaultBtn = document.createElement('button');
      defaultBtn.className = 'cat-btn cat-btn-active';
      defaultBtn.dataset.category = 'all';
      defaultBtn.textContent = 'Semua';
      filterBar.appendChild(defaultBtn);
    }

    cache.categories.forEach(function (cat) {
      var btn = document.createElement('button');
      btn.className = 'cat-btn';
      btn.dataset.category = cat.id || cat.slug || cat.category_name;
      btn.textContent = cat.name || cat.category_name;
      btn.addEventListener('click', function () {
        filterBar.querySelectorAll('.cat-btn').forEach(function (b) { b.classList.remove('cat-btn-active'); });
        this.classList.add('cat-btn-active');
        currentCategory = this.dataset.category;
        currentPage = 1;
        appendedMode = false;
        loadProducts();
      });
      filterBar.appendChild(btn);
    });
  }

  /* ── Filter Checkboxes ── */
  function getCheckboxFilters() {
    return {
      is_free_shipping: $('checkFreeShipping') ? $('checkFreeShipping').checked : false,
      is_cod: $('checkCod') ? $('checkCod').checked : false,
      is_near: $('checkNear') ? $('checkNear').checked : false,
      is_fresh: $('checkFresh') ? $('checkFresh').checked : false,
      has_promo: $('checkDiscount') ? $('checkDiscount').checked : false,
      is_verified: $('checkVerified') ? $('checkVerified').checked : false,
    };
  }

  function initCheckboxFilters() {
    ['checkFreeShipping', 'checkCod', 'checkNear', 'checkFresh', 'checkDiscount', 'checkVerified'].forEach(function (id) {
      var el = $(id);
      if (el) {
        el.addEventListener('change', function () {
          currentPage = 1;
          appendedMode = false;
          loadProducts();
        });
      }
    });
  }

  /* ── Load Products ── */
  async function loadProducts() {
    var grid = $('productGrid');
    var skeleton = $('loadingSkeleton');
    var empty = $('emptyState');
    var loadMoreBtn = $('loadMoreBtn');
    var loader = $('loader');
    var resultCount = $('resultCount');
    var resultCountBadge = $('resultCountBadge');

    if (skeleton) skeleton.style.display = 'grid';
    if (loader) loader.style.display = 'block';
    if (loadMoreBtn) loadMoreBtn.style.display = 'none';
    if (!appendedMode && grid) grid.innerHTML = '';
    if (empty) empty.style.display = 'none';

    try {
      var params = { page: currentPage, page_size: PAGE_SIZE };
      if (currentCategory !== 'all') params.category = currentCategory;
      if (currentSearch) params.search = currentSearch;
      if (currentSort) params.ordering = currentSort;

      // Merge checkbox filters
      var extraFilters = getCheckboxFilters();
      Object.keys(extraFilters).forEach(function (k) {
        if (extraFilters[k]) params[k] = true;
      });

      var data = {};
      if (window.WarungioAPI && window.WarungioAPI.getProducts) {
        data = await WarungioAPI.getProducts(params);
      }
      var products = data.results || data || [];
      var count = data.count || products.length;

      if (skeleton) skeleton.style.display = 'none';
      if (loader) loader.style.display = 'none';

      if (products.length === 0 && !appendedMode) {
        if (grid) grid.innerHTML = '';
        if (empty) empty.style.display = 'block';
        if (resultCount) resultCount.textContent = 'Menampilkan 0 produk';
        if (resultCountBadge) resultCountBadge.textContent = '0';
        return;
      }

      if (resultCount) {
        resultCount.textContent = 'Menampilkan ' + (appendedMode ? grid.children.length + products.length : products.length) + ' dari ' + count + ' produk';
      }
      if (resultCountBadge) resultCountBadge.textContent = Number(count).toLocaleString('id-ID');

      var productsHtml = products.map(function (p) {
        var imgSrc = p.product_photo_url || p.product_photo || '/static/images/paket-sayur.png';
        var price = toRupiah(p.price || 0);
        var oldPrice = p.old_price ? toRupiah(p.old_price) : '';
        var discountPct = p.discount_pct || 0;
        var discountBadge = discountPct > 0 ? '<span class="badge badge-discount">-' + discountPct + '%</span>' : '';
        var freshBadge = p.is_fresh ? '<span class="badge badge-fresh">Segar</span>' : '';
        var rating = Number(p.rating_avg || 0).toFixed(1);
        var favClass = p.is_favorite ? 'is-fav' : '';
        var storeName = escapeHtml(p.store_name || 'Warung Lokal');
        var productUrl = '/products/' + p.id + '/';

        return '<div class="produk-card" onclick="window.location.href=\'' + productUrl + '\'">' +
          '<div class="produk-image-wrapper">' +
            '<img src="' + imgSrc + '" alt="' + escapeHtml(p.product_name) + '" class="produk-img" loading="lazy" onerror="this.src=\'/static/images/paket-sayur.png\'">' +
            '<div class="badge-list">' + freshBadge + discountBadge + '</div>' +
            '<button class="btn-wishlist-product ' + favClass + '" onclick="event.stopPropagation();window.toggleFav(' + p.id + ', this)" title="Favorit">' +
              '<i class="fa-' + (p.is_favorite ? 'solid' : 'regular') + ' fa-heart"></i>' +
            '</button>' +
          '</div>' +
          '<div class="produk-info">' +
            '<span class="produk-category">' + escapeHtml(p.category_name || 'Kategori') + '</span>' +
            '<h4 class="produk-name">' + escapeHtml(p.product_name) + '</h4>' +
            '<span class="produk-store-name">' + storeName + '</span>' +
            '<div class="produk-rating-sold">' +
              '<i class="fa-solid fa-star"></i>' +
              '<span>' + rating + '</span>' +
              '<span class="meta-divider">\u2022</span>' +
              '<span>Terjual ' + (p.sold_count || 0) + '</span>' +
            '</div>' +
            '<div class="produk-price-row">' +
              '<div class="produk-price-box">' +
                (oldPrice ? '<span class="price-old-strikethrough">' + oldPrice + '</span>' : '') +
                '<span class="price-actual">' + price + ' <span class="price-unit">/ ' + escapeHtml(p.unit || 'pcs') + '</span></span>' +
              '</div>' +
              '<button class="btn-add-cart" onclick="event.stopPropagation();window.addToCart(' + p.id + ')"><i class="fa-solid fa-plus"></i></button>' +
            '</div>' +
          '</div>' +
        '</div>';
      }).join('');

      if (grid) {
        if (appendedMode) grid.insertAdjacentHTML('beforeend', productsHtml);
        else grid.innerHTML = productsHtml;
      }

      // Show/hide load more
      var totalPages = Math.ceil(count / PAGE_SIZE);
      if (loadMoreBtn) {
        loadMoreBtn.style.display = currentPage < totalPages ? 'block' : 'none';
      }
    } catch (e) {
      console.warn('Products load error:', e);
      if (skeleton) skeleton.style.display = 'none';
      if (loader) loader.style.display = 'none';
      if (grid && !appendedMode) {
        grid.innerHTML = '<div class="error-state"><i class="fa-solid fa-circle-exclamation"></i><span>Gagal memuat produk. Silakan coba kembali.</span><button class="btn btn-primary btn-sm" onclick="window.location.reload()">Coba Lagi</button></div>';
      }
    }
  }

  /* ── Global: toggleFav ── */
  window.toggleFav = async function (productId, btn) {
    try {
      if (window.WarungioAPI && window.WarungioAPI.toggleFavorite) {
        var result = await WarungioAPI.toggleFavorite(productId);
        if (result.is_favorite) {
          btn.classList.add('is-fav');
          btn.innerHTML = '<i class="fa-solid fa-heart"></i>';
          showToast('Ditambahkan ke favorit', 'success');
        } else {
          btn.classList.remove('is-fav');
          btn.innerHTML = '<i class="fa-regular fa-heart"></i>';
          showToast('Dihapus dari favorit', 'info');
        }
      }
    } catch (e) { showToast('Gagal mengubah favorit', 'error'); }
  };

  /* ── Global: addToCart ── */
  window.addToCart = async function (productId) {
    try {
      if (window.WarungioAPI && window.WarungioAPI.addToCart) {
        await WarungioAPI.addToCart({ product: productId, qty: 1 });
        showToast('Produk ditambahkan ke keranjang!', 'success');
        if (window.WarungioAPI && window.WarungioAPI.getCartCount) {
          var countData = await WarungioAPI.getCartCount();
          var badges = document.querySelectorAll('.cart-badge, #cartBadgeHeader');
          badges.forEach(function (b) { b.textContent = countData.count || 0; });
        }
      }
    } catch (e) { showToast('Gagal menambahkan ke keranjang', 'error'); }
  };

  /* ── Init Wishlist buttons (handled via onclick in template) ── */
  /* ── Init Load More ── */
  function initLoadMore() {
    var btn = $('loadMoreBtn');
    if (btn) {
      btn.addEventListener('click', function () {
        currentPage++;
        appendedMode = true;
        loadProducts();
      });
    }
  }

  /* ── Init Reset Filters ── */
  function initResetFilters() {
    var btn = $('btnResetFilters');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var searchInput = $('searchInput');
      if (searchInput) { searchInput.value = ''; currentSearch = ''; }
      var sortSelect = $('sortSelect');
      if (sortSelect) { sortSelect.value = ''; currentSort = ''; }

      // Reset categories
      var filterBar = $('categoryFilter');
      if (filterBar) {
        filterBar.querySelectorAll('.cat-btn').forEach(function (b) { b.classList.remove('cat-btn-active'); });
        var allBtn = filterBar.querySelector('[data-category="all"]');
        if (allBtn) allBtn.classList.add('cat-btn-active');
      }
      currentCategory = 'all';

      // Reset checkboxes
      ['checkFreeShipping', 'checkCod', 'checkNear', 'checkFresh', 'checkDiscount', 'checkVerified'].forEach(function (id) {
        var el = $(id);
        if (el) el.checked = false;
      });

      currentPage = 1;
      appendedMode = false;
      loadProducts();
    });
  }

  /* ── Init Search ── */
  function initSearch() {
    var searchInput = $('searchInput');
    if (!searchInput) return;
    var searchTimeout;
    searchInput.addEventListener('input', function () {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(function () {
        currentSearch = searchInput.value.trim();
        currentPage = 1;
        appendedMode = false;
        loadProducts();
      }, 300);
    });
  }

  /* ── Init Sort ── */
  function initSort() {
    var sortSelect = $('sortSelect');
    if (!sortSelect) return;
    sortSelect.addEventListener('change', function () {
      currentSort = this.value;
      currentPage = 1;
      appendedMode = false;
      loadProducts();
    });
  }

  /* ── Init Auth UI ── */
  function initAuthUI() {
    var isAuth = window.WarungioAuth && window.WarungioAuth.isAuthenticated();
    var authActions = $('authHeaderActions');
    var guestActions = $('guestHeaderActions');
    if (authActions) authActions.style.display = isAuth ? 'flex' : 'none';
    if (guestActions) guestActions.style.display = isAuth ? 'none' : 'flex';

    // Profile dropdown
    var profileBox = $('profileBox');
    var dropdown = $('dropdownMenu');
    if (profileBox && dropdown) {
      profileBox.addEventListener('click', function (e) { e.stopPropagation(); dropdown.classList.toggle('show'); });
      document.addEventListener('click', function () { dropdown.classList.remove('show'); });
    }

    // Logout
    var logoutBtn = $('btnLogout');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', function (e) {
        e.preventDefault();
        if (window.WarungioAuth) WarungioAuth.logout();
      });
    }

    // Cart count
    if (isAuth && window.WarungioAPI && window.WarungioAPI.getCartCount) {
      WarungioAPI.getCartCount().then(function (res) {
        var badges = document.querySelectorAll('.cart-badge, #cartBadgeHeader');
        badges.forEach(function (b) { b.textContent = res.count || 0; });
      }).catch(function () {});
    }

    // User name
    if (isAuth && window.WarungioAPI) {
      WarungioAPI.checkAuth().then(function (u) {
        if (u && u.user) {
          var nameEl = $('userName');
          if (nameEl && u.user.full_name) nameEl.textContent = 'Hai, ' + u.user.full_name.split(' ')[0];
        }
      }).catch(function () {});
    }
  }

  /* ── Init ── */
  document.addEventListener('DOMContentLoaded', function () {
    initAuthUI();
    initCheckboxFilters();
    initSearch();
    initSort();
    initLoadMore();
    initResetFilters();

    loadCategories().then(function () { loadProducts(); });
  });
})();
