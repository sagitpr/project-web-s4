/**
 * Favorites page - Warungio
 * Menampilkan produk favorit pengguna.
 */
(function () {
  'use strict';

  if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
    window.location.href = '/?next=' + encodeURIComponent(window.location.pathname);
    return;
  }

  const favGrid = document.getElementById('favoritesGrid');
  const loadingState = document.getElementById('loadingState');
  const emptyState = document.getElementById('emptyState');

  function toRupiah(num) {
    return 'Rp ' + Number(num).toLocaleString('id-ID');
  }

  async function loadFavorites() {
    if (loadingState) loadingState.style.display = 'block';
    if (emptyState) emptyState.style.display = 'none';

    try {
      // Fetch products and filter favorites client-side via the API
      const data = await WarungioAPI.getProducts({ page: 1, page_size: 100, is_favorite: true });
      
      if (loadingState) loadingState.style.display = 'none';

      if (favGrid && data.results && data.results.length > 0) {
        favGrid.innerHTML = data.results.map(function (p) {
          const imgSrc = p.product_photo_url || p.product_photo || '/static/images/paket-sayur.png';
          return '<div class="favorite-card">' +
            '<img src="' + imgSrc + '" alt="' + p.product_name + '" loading="lazy">' +
            '<div class="fav-card-body">' +
              '<h3>' + p.product_name + '</h3>' +
              '<p class="fav-price">' + toRupiah(p.price) + '</p>' +
              '<p class="fav-store">' + (p.store_name || 'Warung') + '</p>' +
              '<button class="btn-primary btn-sm" onclick="window.location.href=\'/products/' + p.id + '/\'">Lihat Detail</button>' +
            '</div>' +
          '</div>';
        }).join('');
      } else {
        if (emptyState) emptyState.style.display = 'block';
      }
    } catch (err) {
      console.warn('Favorites load error:', err);
      if (loadingState) loadingState.style.display = 'none';
      if (emptyState) emptyState.style.display = 'block';
    }
  }

  loadFavorites();
})();
