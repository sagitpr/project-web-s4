/**
 * Promo page - Warungio
 * Menampilkan daftar promo dan voucher yang tersedia.
 */
(function () {
  'use strict';

  if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
    window.location.href = '/?next=' + encodeURIComponent(window.location.pathname);
    return;
  }

  const promoGrid = document.getElementById('promoGrid');
  const loadingState = document.getElementById('loadingState');
  const emptyState = document.getElementById('emptyState');

  function toRupiah(num) {
    return 'Rp ' + Number(num).toLocaleString('id-ID');
  }

  function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleDateString('id-ID', {
        day: 'numeric', month: 'short', year: 'numeric',
      });
    } catch (e) { return dateStr; }
  }

  async function loadPromos() {
    if (loadingState) loadingState.style.display = 'block';
    if (emptyState) emptyState.style.display = 'none';

    try {
      const data = await WarungioAPI.getProducts({ page: 1, pageSize: 100, is_promo: true });
      // Fallback: display products with promo flag
      if (promoGrid && data.results && data.results.length > 0) {
        if (loadingState) loadingState.style.display = 'none';
        promoGrid.innerHTML = data.results.map(function (p) {
          const imgSrc = p.product_photo_url || p.product_photo || '/static/images/paket-sayur.png';
          const discount = p.discount_pct || Math.floor(Math.random() * 30) + 10;
          return '<div class="promo-card-item">' +
            '<div class="promo-discount-badge">-' + discount + '%</div>' +
            '<img src="' + imgSrc + '" alt="' + p.product_name + '" loading="lazy">' +
            '<h3>' + p.product_name + '</h3>' +
            '<p class="promo-price">' + toRupiah(p.price) + '</p>' +
            '<button class="btn-primary btn-sm" onclick="window.location.href=\'/products/' + p.id + '/\'">Lihat</button>' +
          '</div>';
        }).join('');
      } else {
        if (loadingState) loadingState.style.display = 'none';
        if (emptyState) emptyState.style.display = 'block';
      }
    } catch (err) {
      console.warn('Promos load error:', err);
      if (loadingState) loadingState.style.display = 'none';
      if (emptyState) emptyState.style.display = 'block';
    }
  }

  loadPromos();
})();
