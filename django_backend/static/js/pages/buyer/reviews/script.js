/**
 * Buyer Reviews Page - Warungio
 * Menampilkan daftar ulasan yang pernah ditulis buyer.
 */
(function () {
  'use strict';

  if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
    window.location.href = '/?next=' + encodeURIComponent(window.location.pathname);
    return;
  }

  const reviewList = document.getElementById('reviewList');
  const loadingState = document.getElementById('loadingState');
  const emptyState = document.getElementById('emptyState');

  async function loadMyReviews() {
    if (loadingState) loadingState.style.display = 'block';
    if (emptyState) emptyState.style.display = 'none';

    try {
      const data = await WarungioAuth.api('/api/products/reviews/mine/');
      const reviews = data.results || data || [];

      if (loadingState) loadingState.style.display = 'none';

      if (reviewList && reviews.length > 0) {
        reviewList.innerHTML = reviews.map(function(r) {
          var filled = Array(r.rating || 0).fill(0).map(function() { return '&#9733;'; }).join('');
          var empty = Array(5 - (r.rating || 0)).fill(0).map(function() { return '&#9734;'; }).join('');
          return '<div class="review-card">' +
            '<img class="product-img" src="' + (r.product?.product_photo_url || '/static/images/placeholder.png') + '" alt="" onerror="this.src=\'/static/images/placeholder.png\'">' +
            '<div class="review-body">' +
              '<p class="product-name">' + (r.product?.name || 'Produk') + '</p>' +
              '<div class="stars">' + filled + empty + '</div>' +
              '<p class="review-date">' + (r.created_at ? new Date(r.created_at).toLocaleDateString('id-ID', { year: 'numeric', month: 'long', day: 'numeric' }) : '') + '</p>' +
              (r.comment ? '<p class="review-text">' + r.comment + '</p>' : '') +
            '</div>' +
          '</div>';
        }).join('');
      } else {
        if (emptyState) emptyState.style.display = 'block';
      }
    } catch (err) {
      console.warn('Reviews load error:', err);
      if (loadingState) loadingState.style.display = 'none';
      if (emptyState) emptyState.style.display = 'block';
    }
  }

  document.addEventListener('DOMContentLoaded', function() {
    if (window.WarungioAuth && window.WarungioAuth.isAuthenticated()) {
      var authActions = document.getElementById('authHeaderActions');
      var guestActions = document.getElementById('guestHeaderActions');
      if (authActions) authActions.style.display = 'flex';
      if (guestActions) guestActions.style.display = 'none';
      var u = window.WarungioAuth.getUser();
      if (u && u.full_name) {
        var nameEl = document.getElementById('userName');
        if (nameEl) nameEl.textContent = 'Hai, ' + u.full_name.split(' ')[0];
      }
    } else {
      var authActions = document.getElementById('authHeaderActions');
      var guestActions = document.getElementById('guestHeaderActions');
      if (authActions) authActions.style.display = 'none';
      if (guestActions) guestActions.style.display = 'flex';
    }

    document.getElementById('btnLogout')?.addEventListener('click', function(e) {
      e.preventDefault();
      if (window.WarungioAuth) { WarungioAuth.logout(); }
    });

    loadMyReviews();
  });
})();
