/**
 * Product Detail — Warungio Marketplace
 * Enhanced interactivity: gallery zoom, wishlist, share, reviews, carousels
 */
document.addEventListener('DOMContentLoaded', async () => {
  'use strict';

  if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.href = '/auth/login/?next=' + next;
    return;
  }

  // ── Helper: redirect to role-appropriate dashboard (WarungioAuth confirmed available at this point) ──
  function redirectToDashboard() {
    window.WarungioAuth.redirectToDashboard();
  }

  // ── Extract Product ID ──
  const pathParts = window.location.pathname.split('/').filter(Boolean);
  const productId = pathParts[pathParts.length - 1];
  if (!productId || isNaN(productId)) {
    redirectToDashboard();
    return;
  }

  // ── State ──
  let productData = null;
  let isFavorite = false;

  // ── DOM refs ──
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => document.querySelectorAll(s);

  const els = {
    breadcrumbTitle: $('#pdBreadcrumbTitle'),
    category: $('#pdCategory'),
    title: $('#pdTitle'),
    ratingStars: $('#pdRatingStars'),
    ratingValue: $('#pdRatingValue'),
    ratingCount: $('#pdRatingCount'),
    soldCount: $('#pdSoldCount'),
    currentPrice: $('#pdCurrentPrice'),
    originalPrice: $('#pdOriginalPrice'),
    discountBadge: $('#pdDiscountBadge'),
    stockDot: $('#pdStockDot'),
    stockText: $('#pdStockText'),
    mainImg: $('#pdMainImg'),
    thumbnails: $('#pdThumbnails'),
    zoomLens: $('#pdZoomLens'),
    sellerLogo: $('#pdSellerLogo'),
    sellerName: $('#pdSellerName'),
    sellerMeta: $('#pdSellerMeta'),
    btnChat: $('#pdBtnChat'),
    btnVisitStore: $('#pdBtnVisitStore'),
    qtyInput: $('#pdQtyInput'),
    btnMinus: $('#pdBtnMinus'),
    btnPlus: $('#pdBtnPlus'),
    btnAddCart: $('#pdBtnAddCart'),
    btnBuy: $('#pdBtnBuy'),
    btnWishlist: $('#pdBtnWishlist'),
    btnShare: $('#pdBtnShare'),
    promoBadge: $('#pdPromoBadge'),
    specTable: $('#pdSpecTable'),
    description: $('#pdDescription'),
    reviewSummary: $('#pdReviewSummary'),
    reviewList: $('#pdReviewList'),
    relatedTrack: $('#pdRelatedTrack'),
    recentlyTrack: $('#pdRecentlyTrack'),
  };

  const cartBadge = document.getElementById('cartBadgeHeader');

  // ── Quantity Picker ──
  if (els.btnMinus && els.btnPlus && els.qtyInput) {
    els.btnMinus.addEventListener('click', () => {
      let v = parseInt(els.qtyInput.value) || 1;
      if (v > 1) els.qtyInput.value = v - 1;
    });
    els.btnPlus.addEventListener('click', () => {
      let v = parseInt(els.qtyInput.value) || 1;
      if (productData && v < parseInt(productData.stock || 999)) {
        els.qtyInput.value = v + 1;
      }
    });
  }

  // ── Gallery Zoom ──
  function initZoom() {
    const mainImg = els.mainImg;
    const lens = els.zoomLens;
    if (!mainImg || !lens) return;
    const container = mainImg.parentElement;

    container.addEventListener('mousemove', (e) => {
      const rect = container.getBoundingClientRect();
      let x = e.clientX - rect.left;
      let y = e.clientY - rect.top;
      const lw = lens.offsetWidth / 2;
      const lh = lens.offsetHeight / 2;
      x = Math.max(lw, Math.min(rect.width - lw, x));
      y = Math.max(lh, Math.min(rect.height - lh, y));
      lens.style.left = x + 'px';
      lens.style.top = y + 'px';
      // Zoom handled purely via CSS :hover — just show lens
    });

    container.addEventListener('mouseenter', () => {
      lens.style.opacity = '1';
    });
    container.addEventListener('mouseleave', () => {
      lens.style.opacity = '0';
    });
  }
  initZoom();

  // ── Thumbnail clicks ──
  function setMainImage(src) {
    if (!els.mainImg) return;
    els.mainImg.src = src || els.mainImg.src;
    $$('.pd-thumb').forEach((t) => t.classList.toggle('active', t.dataset.src === src));
  }

  function renderThumbnails(images) {
    if (!els.thumbnails) return;
    const unique = [els.mainImg.src, ...images.filter((s) => s !== els.mainImg.src)].slice(0, 6);
    els.thumbnails.innerHTML = unique.map((src, i) =>
      `<div class="pd-thumb ${i === 0 ? 'active' : ''}" data-src="${src}" onclick="document.getElementById('pdMainImg').src=this.dataset.src;document.querySelectorAll('.pd-thumb').forEach(t=>t.classList.toggle('active',t===this))">
        <img src="${src}" alt="" loading="${i > 2 ? 'lazy' : 'eager'}" onerror="this.parentElement.style.display='none'">
      </div>`
    ).join('');
  }

  // ── Load Product ──
  async function loadProduct() {
    try {
      const p = await WarungioAPI.getProduct(productId);
      if (!p) throw new Error('Not found');
      productData = p;

      // Breadcrumb
      if (els.breadcrumbTitle) els.breadcrumbTitle.textContent = p.product_name;

      // Category
      if (els.category) els.category.textContent = p.category_name || 'Produk';

      // Title
      if (els.title) els.title.textContent = p.product_name;
      document.title = p.product_name + ' - Warungio';

      // Rating
      const rating = Number(p.rating_avg || 0).toFixed(1);
      const count = p.review_count || 0;
      const sold = p.sold_count || 0;
      if (els.ratingStars) els.ratingStars.innerHTML = getStars(rating);
      if (els.ratingValue) els.ratingValue.textContent = rating;
      if (els.ratingCount) els.ratingCount.textContent = `(${count} ulasan)`;
      if (els.soldCount) els.soldCount.textContent = `Terjual ${sold} ${p.unit || 'pcs'}`;

      // Price
      const price = Number(p.price || 0);
      if (els.currentPrice) els.currentPrice.textContent = 'Rp ' + price.toLocaleString('id-ID');

      // Discount (mock: could come from actual promo data)
      if (els.originalPrice) els.originalPrice.style.display = 'none';
      if (els.discountBadge) els.discountBadge.style.display = 'none';

      // Stock
      const stock = parseInt(p.stock || 0);
      if (stock <= 0) {
        if (els.stockDot) { els.stockDot.className = 'pd-stock-dot out-of-stock'; }
        if (els.stockText) { els.stockText.className = 'pd-stock-text out-of-stock'; els.stockText.textContent = 'Stok Habis'; }
      } else if (stock <= 5) {
        if (els.stockDot) { els.stockDot.className = 'pd-stock-dot low-stock'; }
        if (els.stockText) { els.stockText.className = 'pd-stock-text low-stock'; els.stockText.textContent = `Sisa ${stock} ${p.unit || 'pcs'}`; }
      } else {
        if (els.stockDot) { els.stockDot.className = 'pd-stock-dot in-stock'; }
        if (els.stockText) { els.stockText.className = 'pd-stock-text in-stock'; els.stockText.textContent = 'Stok Tersedia'; }
      }

      // Main image + thumbnails
      const mainImgSrc = p.product_photo_url || p.product_photo || '/static/images/paket-sayur.png';
      if (els.mainImg) els.mainImg.src = mainImgSrc;

      // Gallery images
      const galleryImages = (p.gallery || []).map((g) => g.image).filter(Boolean);
      renderThumbnails([mainImgSrc, ...galleryImages]);

      // Seller
      const store = p.store || {};
      if (els.sellerLogo) els.sellerLogo.src = store.store_logo || '/static/images/store-icon-T.png';
      if (els.sellerName) els.sellerName.textContent = store.store_name || 'Warung Mitra';
      if (els.sellerMeta) {
        const parts = [];
        if (store.city) parts.push(store.city);
        if (store.rating_avg) parts.push('★ ' + Number(store.rating_avg).toFixed(1));
        if (store.follower_count) parts.push(Number(store.follower_count).toLocaleString('id-ID') + ' pengikut');
        els.sellerMeta.textContent = parts.join(' • ') || (store.city || '');
      }
      if (els.btnChat) {
        els.btnChat.onclick = () => window.location.href = '/buyer/chat/?store=' + (store.id || '');
      }
      if (els.btnVisitStore) {
        els.btnVisitStore.onclick = () => window.location.href = '/home/?store=' + (store.id || '');
      }

      // Description
      if (els.description) els.description.textContent = p.description || 'Tidak ada deskripsi produk.';

      // Specifications table
      renderSpecs(p);

      // Check favorite status
      await checkFavorite();

      // Record view
      try {
        await WarungioAPI.recordProductView(productId);
      } catch (e) { /* ignore */ }
    } catch (err) {
      console.error('Failed to load product:', err);
      redirectToDashboard();
    }
  }

  // ── Render Stars ──
  function getStars(rating) {
    const full = Math.floor(rating);
    const half = rating - full >= 0.5;
    return (
      '<i class="fa-solid fa-star"></i>'.repeat(full) +
      (half ? '<i class="fa-solid fa-star-half-stroke"></i>' : '') +
      '<i class="fa-regular fa-star"></i>'.repeat(Math.max(0, 5 - full - (half ? 1 : 0)))
    );
  }

  // ── Render Specs ──
  function renderSpecs(p) {
    if (!els.specTable) return;
    const rows = [
      { label: 'Berat', value: p.weight ? p.weight + ' g' : '-' },
      { label: 'Kategori', value: p.category_name || '-' },
      { label: 'Satuan', value: p.unit || 'pcs' },
      { label: 'Stok', value: p.stock + ' ' + (p.unit || 'pcs') },
      { label: 'Terjual', value: (p.sold_count || 0) + ' ' + (p.unit || 'pcs') },
      { label: 'Status', value: p.product_status || 'fresh' },
      { label: 'Kualitas', value: p.quality_score ? p.quality_score + '/100' : '-' },
    ].filter((r) => r.value && r.value !== '-');

    els.specTable.innerHTML = rows.map((r) =>
      `<tr><td>${r.label}</td><td>${r.value}</td></tr>`
    ).join('');
  }

  // ── Favorite Toggle ──
  async function checkFavorite() {
    try {
      const res = await WarungioAPI.getProductFavorite(productId);
      isFavorite = res && res.is_favorite;
      if (els.btnWishlist) {
        els.btnWishlist.classList.toggle('active', isFavorite);
        els.btnWishlist.innerHTML = isFavorite
          ? '<i class="fa-solid fa-heart"></i>'
          : '<i class="fa-regular fa-heart"></i>';
      }
    } catch (e) { /* ignore */ }
  }

  if (els.btnWishlist) {
    els.btnWishlist.addEventListener('click', async () => {
      try {
        const res = await WarungioAPI.toggleFavorite(productId);
        isFavorite = res && res.is_favorite;
        els.btnWishlist.classList.toggle('active', isFavorite);
        els.btnWishlist.innerHTML = isFavorite
          ? '<i class="fa-solid fa-heart"></i>'
          : '<i class="fa-regular fa-heart"></i>';
        showToast(isFavorite ? 'Ditambahkan ke favorit' : 'Dihapus dari favorit');
      } catch (e) {
        showToast('Gagal mengubah favorit', 'error');
      }
    });
  }

  // ── Share ──
  if (els.btnShare) {
    els.btnShare.addEventListener('click', async () => {
      const url = window.location.href;
      if (navigator.share) {
        try {
          await navigator.share({ title: document.title, url });
        } catch (e) { /* user cancelled */ }
      } else {
        try {
          await navigator.clipboard.writeText(url);
          showToast('Tautan produk disalin!');
        } catch (e) {
          showToast('Gagal menyalin tautan', 'error');
        }
      }
    });
  }

  // ── Add to Cart ──
  if (els.btnAddCart && els.qtyInput) {
    els.btnAddCart.addEventListener('click', async () => {
      const qty = parseInt(els.qtyInput.value) || 1;
      els.btnAddCart.disabled = true;
      els.btnAddCart.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Menambahkan...';

      try {
        await WarungioAPI.addToCart({ product: Number(productId), qty });
        showToast('Produk ditambahkan ke keranjang!', 'success');
        try {
          const c = await WarungioAPI.getCartCount();
          if (cartBadge && c) cartBadge.textContent = c.count || 0;
        } catch (e) {}
      } catch (err) {
        showToast('Gagal menambahkan: ' + (err.message || err), 'error');
      } finally {
        els.btnAddCart.disabled = false;
        els.btnAddCart.innerHTML = '<i class="fa-solid fa-cart-shopping"></i> Tambah ke Keranjang';
      }
    });
  }

  // ── Buy Now ──
  if (els.btnBuy && els.qtyInput) {
    els.btnBuy.addEventListener('click', async () => {
      const qty = parseInt(els.qtyInput.value) || 1;
      try {
        await WarungioAPI.addToCart({ product: Number(productId), qty });
        window.location.href = '/buyer/checkout/';
      } catch (err) {
        showToast('Gagal: ' + (err.message || err), 'error');
      }
    });
  }

  // ── Load Reviews ──
  async function loadReviews() {
    if (!els.reviewList || !els.reviewSummary) return;
    try {
      const data = await WarungioAPI.getProductReviews(productId);
      const reviews = Array.isArray(data) ? data : (data.results || []);
      const total = reviews.length;
      const avg = total ? (reviews.reduce((s, r) => s + (r.rating || 0), 0) / total) : 0;

      // Star breakdown
      const dist = [0, 0, 0, 0, 0];
      reviews.forEach((r) => { const i = Math.min(Math.max((r.rating || 1) - 1, 0), 4); dist[i]++; });

      els.reviewSummary.innerHTML = `
        <div class="pd-review-average">
          <div class="pd-review-big-number">${avg.toFixed(1)}</div>
          <div class="pd-review-big-stars">${getStars(avg)}</div>
          <div class="pd-review-big-label">${total} ulasan</div>
        </div>
        ${[5,4,3,2,1].map((star) => {
          const pct = total ? (dist[star-1] / total) * 100 : 0;
          return `<div class="pd-star-bar-row">
            <span class="pd-star-bar-label">${star} ★</span>
            <div class="pd-star-bar-track"><div class="pd-star-bar-fill" style="width:${pct}%"></div></div>
            <span class="pd-star-bar-count">${dist[star-1]}</span>
          </div>`;
        }).join('')}
      `;

      // Review cards
      if (total === 0) {
        els.reviewList.innerHTML = '<div style="text-align:center;padding:20px;color:var(--color-text-tertiary);font-size:13px;">Belum ada ulasan untuk produk ini.</div>';
        return;
      }

      els.reviewList.innerHTML = reviews.map((r) => {
        const stars = '<i class="fa-solid fa-star"></i>'.repeat(r.rating || 0);
        const avatar = r.user_photo || '/static/images/av-siti.png';
        const name = r.user_name || 'Pelanggan';
        const date = r.created_at ? new Date(r.created_at).toLocaleDateString('id-ID', { day: 'numeric', month: 'long', year: 'numeric' }) : '';
        return `<div class="pd-review-card">
          <div class="pd-review-card-header">
            <div class="pd-review-user">
              <img src="${avatar}" alt="${name}" class="pd-review-avatar" onerror="this.src='/static/images/av-siti.png'">
              <span class="pd-review-name">${name}</span>
            </div>
            <div class="pd-review-stars">${stars}</div>
          </div>
          <p class="pd-review-comment">${r.comment || 'Ulasan tanpa komentar.'}</p>
          ${r.seller_reply ? `<div class="pd-review-seller-reply"><strong>${r.store_name || 'Penjual'} — Balasan</strong>${r.seller_reply}</div>` : ''}
          <span class="pd-review-date">${date}</span>
        </div>`;
      }).join('');
    } catch (e) {
      console.warn('Failed to load reviews:', e);
    }
  }

  // ── Load Related Products ──
  async function loadRelated() {
    if (!els.relatedTrack) return;
    try {
      const data = await WarungioAPI.getProducts({ page: 1, pageSize: 8 });
      const products = Array.isArray(data) ? data : (data.results || []);
      if (products.length === 0) {
        document.getElementById('pdRelatedSection')?.remove();
        return;
      }
      const filtered = products.filter((p) => p.id !== Number(productId)).slice(0, 8);
      if (filtered.length === 0) {
        document.getElementById('pdRelatedSection')?.remove();
        return;
      }
      els.relatedTrack.innerHTML = filtered.map((p) => `
        <div class="pd-carousel-item">
          <a href="/products/${p.id}/" style="text-decoration:none;color:inherit;">
            <div class="pd-mini-card">
              <img src="${p.product_photo_url || '/static/images/paket-sayur.png'}" alt="${p.product_name}" loading="lazy" onerror="this.src='/static/images/paket-sayur.png'">
              <div class="pd-mini-card-body">
                <div class="pd-mini-card-name">${p.product_name}</div>
                <div class="pd-mini-card-price">Rp ${Number(p.price || 0).toLocaleString('id-ID')}</div>
                <div class="pd-mini-card-store">${p.store_name || ''}</div>
              </div>
            </div>
          </a>
        </div>
      `).join('');
    } catch (e) {
      document.getElementById('pdRelatedSection')?.remove();
    }
  }

  // ── Load Recently Viewed ──
  async function loadRecentlyViewed() {
    if (!els.recentlyTrack) return;
    try {
      const data = await WarungioAPI.getRecentlyViewed();
      const items = data && data.results ? data.results : [];
      const views = items.filter((v) => String(v.product_detail?.id) !== String(productId)).slice(0, 6);
      if (views.length === 0) {
        document.getElementById('pdRecentlySection')?.remove();
        return;
      }
      els.recentlyTrack.innerHTML = views.map((v) => {
        const p = v.product_detail || {};
        const img = p.product_photo_url || '/static/images/paket-sayur.png';
        return `<a href="/products/${p.id}/" style="text-decoration:none;color:inherit;">
          <div class="pd-recently-item">
            <img src="${img}" alt="${p.product_name}" onerror="this.src='/static/images/paket-sayur.png'">
            <div class="pd-recently-item-info">
              <div class="pd-recently-item-name">${p.product_name || 'Produk'}</div>
              <div class="pd-recently-item-price">Rp ${Number(p.price || 0).toLocaleString('id-ID')}</div>
            </div>
          </div>
        </a>`;
      }).join('');
    } catch (e) {
      document.getElementById('pdRecentlySection')?.remove();
    }
  }

  // ── Toast (delegates to shared utility) ──
  function showToast(msg, type) {
    if (window.WarungioAuthUI) {
      WarungioAuthUI.showToast(msg, type || 'info');
      return;
    }
    if (window.WarungioToast) {
      window.WarungioToast.show(msg, type || 'info');
      return;
    }
    // Fallback
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const t = document.createElement('div');
    t.className = 'toast ' + (type || 'info');
    t.innerHTML = '<span>' + msg + '</span>';
    container.appendChild(t);
    setTimeout(() => { if (t.parentNode) t.remove(); }, 4000);
  }

  // ── Profile Dropdown (handled by WarungioAuthUI.init()) ──
  function bindProfile() {
    // auth-ui.js handles this via init() — skip if available
    if (window.WarungioAuthUI) return;
    const profileBox = document.getElementById('profileBox');
    const dropdown = document.getElementById('dropdownMenu');
    const btnLogout = document.getElementById('btnLogout');
    if (profileBox && dropdown) {
      profileBox.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('show');
      });
      document.addEventListener('click', () => dropdown.classList.remove('show'));
    }
    if (btnLogout) {
      btnLogout.addEventListener('click', (e) => {
        e.preventDefault();
        if (window.WarungioAuth) {
          window.WarungioAuth.logout();
          window.location.href = '/';
        }
      });
    }
  }

  // ── Load User Profile ──
  async function loadProfile() {
    try {
      const u = await WarungioAPI.checkAuth();
      if (u && u.user) {
        const nameEl = document.getElementById('userName');
        const avatarEl = document.getElementById('userAvatar');
        const badgeEl = document.getElementById('userRoleBadge');
        if (nameEl) nameEl.textContent = 'Hai, ' + (u.user.full_name || u.user.email);
        if (avatarEl && u.user.profile_photo) avatarEl.src = u.user.profile_photo;
        if (badgeEl) {
          badgeEl.textContent = u.user.role === 'seller' ? 'Penjual' : 'Member';
          if (u.user.role === 'seller') badgeEl.style.background = 'var(--color-warning)';
        }
      }
    } catch (e) {}
  }

  // ── Init ──
  bindProfile();
  await Promise.all([loadProfile(), loadProduct(), loadReviews(), loadRelated(), loadRecentlyViewed()]);

  // Cart count
  try {
    const c = await WarungioAPI.getCartCount();
    if (cartBadge && c) cartBadge.textContent = c.count || 0;
  } catch (e) {}
});
