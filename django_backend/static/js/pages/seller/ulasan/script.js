/**
 * Warungio Seller — Ulasan (Reviews) Page
 * Displays product reviews with rating breakdown, filter tabs, and reply functionality.
 */
(function () {
  'use strict';

  function formatNumber(n) {
    if (typeof n !== 'number') return '0';
    return n.toLocaleString('id-ID');
  }
  function $(id) { return document.getElementById(id); }

  /* ── Toast ── */
  function showToast(msg, type) {
    if (window.WarungioToast) {
      WarungioToast.show(msg, type || 'success');
      return;
    }
    var t = document.createElement('div');
    t.className = 'toast ' + (type || '');
    t.innerHTML = '<i class="fa-solid fa-check-circle"></i> ' + msg;
    t.style.display = 'flex';
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 3000);
  }

  /* ── Modal ── */
  function openModal(id) { var el = $(id); if (el) el.style.display = 'flex'; }
  function closeModal(id) { var el = $(id); if (el) el.style.display = 'none'; }

  /* ── Sidebar ── */
  function initSidebar() {
    var btn = $('hamburgerBtn');
    var sidebar = $('sidebarNav');
    var overlay = $('sidebarOverlay');
    if (!btn) return;
    btn.addEventListener('click', function () {
      sidebar.classList.toggle('open');
      overlay.classList.toggle('open');
    });
    if (overlay) overlay.addEventListener('click', function () {
      sidebar.classList.remove('open');
      overlay.classList.remove('open');
    });
    var closeBtn = $('sidebarAdsClose');
    if (closeBtn) closeBtn.addEventListener('click', function () {
      closeBtn.parentElement.style.display = 'none';
    });
  }

  /* ── Data Store ── */
  var allReviews = [];
  var currentFilter = 'all';
  var searchQuery = '';

  /* ── Helpers ── */
  function getInitials(name) {
    if (!name) return '?';
    var parts = name.split(' ');
    return parts[0][0] + (parts[1] ? parts[1][0] : '');
  }

  function renderStars(rating) {
    var s = '';
    for (var i = 0; i < 5; i++) {
      s += i < rating ? '\u2605' : '\u2606';
    }
    return s;
  }

  function formatDate(dateStr) {
    if (!dateStr) return '-';
    var d = new Date(dateStr);
    return d.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' }) + ' ' + d.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
  }

  function escapeHtml(str) {
    if (typeof str !== 'string') return str;
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /* ── Load Data ── */
  function loadData() {
    if (window.WarungioAPI && typeof WarungioAPI.getStoreReviews === 'function') {
      WarungioAPI.getStoreReviews().then(function (res) {
        var reviews = res && res.results ? res.results : (Array.isArray(res) ? res : []);
        allReviews = reviews;
        renderAll();
      }).catch(function (err) {
        console.warn('Reviews data unavailable:', err);
        allReviews = [];
        renderAll();
      });
    } else {
      allReviews = [];
      renderAll();
    }
  }

  /* ── Render All ── */
  function renderAll() {
    renderStats();
    renderRatingBars();
    renderReviews();
  }

  /* ── Render Stats ── */
  function renderStats() {
    var total = allReviews.length;
    var sumRating = allReviews.reduce(function (s, r) { return s + (r.rating || 0); }, 0);
    var avg = total > 0 ? (sumRating / total) : 0;
    var count5 = allReviews.filter(function (r) { return r.rating === 5; }).length;
    var count4 = allReviews.filter(function (r) { return r.rating === 4; }).length;
    var countLow = allReviews.filter(function (r) { return r.rating <= 3; }).length;
    var replied = allReviews.filter(function (r) { return r.seller_reply; }).length;

    $('avgRating').textContent = avg.toFixed(1) + '/5';
    $('ratingCount').textContent = 'Dari ' + formatNumber(total) + ' ulasan';
    $('rating5Count').textContent = formatNumber(count5);
    $('rating4Count').textContent = formatNumber(count4);
    $('ratingLowCount').textContent = formatNumber(countLow);
    $('repliedCount').textContent = formatNumber(replied);
  }

  /* ── Render Rating Bars ── */
  function renderRatingBars() {
    var total = allReviews.length || 1;
    var colors = ['5', '4', '3', '2', '1'];
    for (var i = 1; i <= 5; i++) {
      var count = allReviews.filter(function (r) { return r.rating === i; }).length;
      var pct = Math.round((count / total) * 100);
      var bar = $('bar' + i);
      var countEl = $('bar' + i + 'Count');
      if (bar) bar.style.width = pct + '%';
      if (countEl) countEl.textContent = formatNumber(count);
    }
  }

  /* ── Filter Reviews ── */
  function getFilteredReviews() {
    var list = allReviews;

    // Filter by rating
    if (currentFilter !== 'all' && currentFilter !== 'unreplied') {
      list = list.filter(function (r) { return r.rating === Number(currentFilter); });
    } else if (currentFilter === 'unreplied') {
      list = list.filter(function (r) { return !r.seller_reply; });
    }

    // Search
    if (searchQuery) {
      var q = searchQuery.toLowerCase();
      list = list.filter(function (r) {
        return (r.comment && r.comment.toLowerCase().indexOf(q) !== -1) ||
               (r.product_name && r.product_name.toLowerCase().indexOf(q) !== -1) ||
               (r.user && r.user.full_name && r.user.full_name.toLowerCase().indexOf(q) !== -1);
      });
    }

    return list;
  }

  /* ── Render Reviews ── */
  function renderReviews() {
    var container = $('reviewsList');
    var loading = $('reviewLoadingState');
    if (!container) return;

    var filtered = getFilteredReviews();
    if (loading) loading.style.display = 'none';

    if (filtered.length === 0) {
      container.innerHTML = '<div style="text-align:center;padding:60px 20px;color:var(--muted, #94a3b8);font-size:13px;"><i class="fa-solid fa-star" style="font-size:32px;display:block;margin-bottom:16px;opacity:0.3;"></i> Belum ada ulasan yang cocok dengan filter ini.</div>';
      return;
    }

    container.innerHTML = '';
    filtered.forEach(function (review) {
      var user = review.user || {};
      var userName = review.user_name || user.full_name || 'Anonymous';
      var userPhoto = review.user_photo || user.profile_photo || null;
      var initials = getInitials(userName);
      var avatarHtml = userPhoto
        ? '<img src="' + userPhoto + '" class="review-avatar" alt="">'
        : '<div class="review-avatar">' + initials + '</div>';

      var replyHtml = '';
      if (review.seller_reply) {
        replyHtml =
          '<div class="review-reply" id="reply-' + review.id + '">' +
            '<div class="reply-header"><i class="fa-solid fa-reply"></i> Balasan Penjual</div>' +
            '<div class="reply-text">' + escapeHtml(review.seller_reply) + '</div>' +
            '<div class="reply-time">' + formatDate(review.seller_reply_at) + '</div>' +
          '</div>';
      }

      var card = document.createElement('div');
      card.className = 'review-card';
      card.innerHTML =
        '<div class="review-header">' +
          '<div class="review-user">' +
            avatarHtml +
            '<div>' +
              '<span class="review-name">' + escapeHtml(userName) + '</span>' +
              '<span class="review-date">' + formatDate(review.created_at) + '</span>' +
            '</div>' +
          '</div>' +
          '<div class="review-stars">' + renderStars(review.rating || 0) + '</div>' +
        '</div>' +
        '<div class="review-product">' + escapeHtml(review.product_name || 'Produk') + '</div>' +
        '<div class="review-comment">' + escapeHtml(review.comment || '') + '</div>' +
        replyHtml +
        (review.seller_reply ? '' : '<div style="margin-top:12px;"><button class="btn-reply" data-review-id="' + review.id + '"><i class="fa-solid fa-reply"></i> Balas Ulasan</button></div>');

      container.appendChild(card);
    });

    // Attach reply button handlers
    container.querySelectorAll('.btn-reply').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = Number(btn.getAttribute('data-review-id'));
        var review = allReviews.find(function (r) { return r.id === id; });
        if (review) openReplyModal(review);
      });
    });
  }

  /* ── Tab Filtering ── */
  function initTabs() {
    var tabs = document.querySelectorAll('.review-tabs .tab-btn');
    tabs.forEach(function (btn) {
      btn.addEventListener('click', function () {
        tabs.forEach(function (t) { t.classList.remove('active'); });
        btn.classList.add('active');
        currentFilter = btn.getAttribute('data-filter') || 'all';
        renderReviews();
      });
    });
  }

  /* ── Search ── */
  function initSearch() {
    var input = $('reviewSearch');
    if (!input) return;
    input.addEventListener('input', function () {
      searchQuery = input.value;
      renderReviews();
    });
  }

  /* ── Reply Modal ── */
  var replyTarget = null;

  function openReplyModal(review) {
    replyTarget = review;
    $('replyReviewId').value = review.id;

    var preview = $('replyReviewPreview');
    if (preview) {
      var user = review.user || {};
      var previewName = review.user_name || user.full_name || 'Anonymous';
      preview.innerHTML =
        '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">' +
          '<span style="font-size:12px;font-weight:600;">' + escapeHtml(previewName) + '</span>' +
          '<span class="review-stars" style="font-size:12px;">' + renderStars(review.rating || 0) + '</span>' +
        '</div>' +
        '<div class="review-product">' + escapeHtml(review.product_name || 'Produk') + '</div>' +
        '<div class="review-comment">" ' + escapeHtml(review.comment || '') + ' "</div>';
    }

    $('replyInput').value = '';
    openModal('replyModal');
  }

  function sendReply(e) {
    e.preventDefault();
    var reviewId = $('replyReviewId').value;
    var replyText = $('replyInput').value;

    if (!replyText.trim()) {
      showToast('Balasan tidak boleh kosong.', 'error');
      return;
    }

    var btn = $('btnSendReply');
    btn.disabled = true;
    btn.textContent = 'Mengirim...';

    // Coba kirim ke backend API
    function onSuccess() {
      closeModal('replyModal');
      renderReviews();
      renderStats();
      showToast('Balasan berhasil dikirim!', 'success');
      btn.disabled = false;
      btn.textContent = 'Kirim Balasan';
    }

    function onError(err) {
      showToast('Gagal mengirim balasan: ' + (err.message || err), 'error');
      btn.disabled = false;
      btn.textContent = 'Kirim Balasan';
    }

    if (window.WarungioAPI && typeof WarungioAPI.replyToReview === 'function') {
      WarungioAPI.replyToReview(reviewId, { reply: replyText }).then(onSuccess).catch(onError);
    } else {
      // Fallback lokal
      var review = allReviews.find(function (r) { return r.id === Number(reviewId); });
      if (review) {
        review.seller_reply = replyText;
        review.seller_reply_at = new Date().toISOString();
      }
      onSuccess();
    }
  }

  function initReplyModal() {
    var btnClose = $('btnCloseReplyModal');
    if (btnClose) btnClose.addEventListener('click', function () { closeModal('replyModal'); });
    var btnCancel = $('btnCancelReply');
    if (btnCancel) btnCancel.addEventListener('click', function () { closeModal('replyModal'); });

    var replyForm = $('replyForm');
    if (replyForm) replyForm.addEventListener('submit', sendReply);

    // Close on backdrop click
    var modal = $('replyModal');
    if (modal) modal.addEventListener('click', function (e) {
      if (e.target === modal) modal.style.display = 'none';
    });
  }

  /* ── Init ── */
  document.addEventListener('DOMContentLoaded', function () {
    initSidebar();
    initTabs();
    initSearch();
    initReplyModal();

    // Set shop name
    if (window.WarungioAPI && typeof WarungioAPI.getMyStore === 'function') {
      WarungioAPI.getMyStore().then(function (res) {
        var store = res && res.data ? res.data : res;
        if (store && store.store_name) $('shopName').textContent = store.store_name;
      }).catch(function () {});
    }

    loadData();
  });
})();
