document.addEventListener('DOMContentLoaded', function () {
  var reviews = [];
  var selectedId = null;
  var storeName = 'Warung Saya';

  // Load reviews from API
  async function loadReviews() {
    if (!window.WarungioAPI) {
      document.getElementById('reviewsBody').innerHTML = '<tr><td colspan="7" style="text-align:center;padding:34px;color:#94a3b8">Memuat ulasan...</td></tr>';
      return;
    }
    try {
      // Load store profile for name
      try {
        var store = await WarungioAPI.getMyStore();
        if (store && store.store_name) storeName = store.store_name;
        var nameEl = document.querySelector('.store-head h2');
        if (nameEl) {
          nameEl.innerHTML = (store.store_name || 'Warung Saya') + ' <span>Aktif</span>';
        }
        var idEl = document.getElementById('storeIdDisplay');
        if (idEl) {
          idEl.textContent = (store.slug ? store.slug.toUpperCase() : (store.id ? 'WRG' + store.id : '---'));
        }
        var avatarEl = document.querySelector('.user-info img');
        if (avatarEl && store.store_logo) avatarEl.src = store.store_logo;
        var nameDisplay = document.querySelector('.user-info div strong');
        if (nameDisplay) nameDisplay.textContent = store.store_name || 'Seller';
      } catch (e) { /* keep defaults */ }

      var data = await WarungioAPI.getStoreReviews();
      reviews = Array.isArray(data) ? data : (data.results || []);

      // Map API response to review format
      reviews = reviews.map(function(r, idx) {
        return {
          id: r.id || (idx + 1),
          customer: r.user_name || r.user?.full_name || 'Pembeli',
          tag: r.user_tag || 'Pelanggan',
          avatar: r.user_avatar || r.user?.profile_photo || '/static/images/store-icon-T.png',
          product: r.product_name || r.product?.product_name || 'Produk',
          qty: r.quantity ? r.quantity + ' item' : '1 item',
          rating: r.rating || 5,
          text: r.comment || r.review_text || '',
          date: r.created_at ? new Date(r.created_at).toLocaleDateString('id-ID', { day:'numeric', month:'long', year:'numeric' }) : '',
          time: r.created_at ? new Date(r.created_at).toLocaleTimeString('id-ID', { hour:'2-digit', minute:'2-digit' }) + ' WIB' : '',
          replied: !!r.reply,
          reply: r.reply || '',
          order: r.order_number || '#WRG-000000',
          images: r.images || []
        };
      });
    } catch (err) {
      console.warn('Failed to load reviews from API, using empty state:', err);
      reviews = [];
    }
    renderMetrics();
    renderReviews();
  }
  var searchInput = document.getElementById('searchInput');
  var ratingFilter = document.getElementById('ratingFilter');
  var statusFilter = document.getElementById('statusFilter');
  var reviewsBody = document.getElementById('reviewsBody');
  var mobileReviews = document.getElementById('mobileReviews');
  var modal = document.getElementById('reviewModal');
  var modalBody = document.getElementById('modalBody');
  var replyInput = document.getElementById('replyInput');
  var saveReplyBtn = document.getElementById('saveReplyBtn');
  var deleteReplyBtn = document.getElementById('deleteReplyBtn');

  function stars(n) {
    var out = '';
    for (var i = 1; i <= 5; i++) out += i <= n ? '<i class="fa-solid fa-star"></i>' : '<i class="fa-regular fa-star"></i>';
    return '<span class="stars">' + out + '</span>';
  }

  function pct(part, total) { return total ? Math.round((part / total) * 100) : 0; }
  function escapeHtml(str) {
    var d = document.createElement('div');
    d.textContent = str || '';
    return d.innerHTML;
  }
  function reviewType(rating) {
    if (rating >= 4) return 'positive';
    if (rating === 3) return 'neutral';
    return 'negative';
  }

  function filteredReviews() {
    var q = (searchInput.value || '').toLowerCase().trim();
    var rf = Number(ratingFilter.value || 0);
    var sf = statusFilter.value;
    return reviews.filter(function (r) {
      var matchSearch = !q || r.product.toLowerCase().includes(q) || r.customer.toLowerCase().includes(q) || r.text.toLowerCase().includes(q);
      var matchRating = !rf || r.rating === rf;
      var matchStatus = !sf || (sf === 'replied' ? r.replied : !r.replied);
      return matchSearch && matchRating && matchStatus;
    });
  }

  function renderMetrics() {
    var total = reviews.length;
    var avg = reviews.reduce(function (s, r) { return s + r.rating; }, 0) / total;
    var positive = reviews.filter(function (r) { return reviewType(r.rating) === 'positive'; }).length;
    var neutral = reviews.filter(function (r) { return reviewType(r.rating) === 'neutral'; }).length;
    var negative = reviews.filter(function (r) { return reviewType(r.rating) === 'negative'; }).length;
    var unreplied = reviews.filter(function (r) { return !r.replied; }).length;
    document.getElementById('metricsGrid').innerHTML = [
      ['star', 'fa-star', 'Rating Rata-rata', avg.toFixed(1) + ' / 5', 'Dari ' + total + ' ulasan'],
      ['good', 'fa-face-smile', 'Ulasan Positif', positive, pct(positive, total) + '% dari total ulasan'],
      ['neutral', 'fa-face-meh', 'Ulasan Netral', neutral, pct(neutral, total) + '% dari total ulasan'],
      ['bad', 'fa-face-frown', 'Ulasan Negatif', negative, pct(negative, total) + '% dari total ulasan'],
      ['wait', 'fa-message', 'Belum Dibalas', unreplied, 'Perlu respon segera']
    ].map(function (m) {
      return '<article class="metric-card"><div class="metric-icon ' + m[0] + '"><i class="fa-solid ' + m[1] + '"></i></div><div><span>' + m[2] + '</span><h3>' + m[3] + '</h3><p>' + m[4] + '</p></div></article>';
    }).join('');
    document.getElementById('avgRating').textContent = avg.toFixed(1);
    document.getElementById('avgStars').innerHTML = stars(Math.round(avg));
    document.getElementById('totalReviews').textContent = 'Dari ' + total + ' ulasan';

    document.getElementById('ratingBars').innerHTML = [5, 4, 3, 2, 1].map(function (n) {
      var count = reviews.filter(function (r) { return r.rating === n; }).length;
      var percent = pct(count, total);
      return '<div class="bar-row"><b>' + n + ' Star</b><div class="track"><div class="fill" style="width:' + percent + '%"></div></div><span>' + count + ' (' + percent + '%)</span></div>';
    }).join('');
  }

  function statusHtml(r) {
    return r.replied ? '<span class="status-pill replied"><i class="fa-regular fa-circle-check"></i> Dibalas</span>' : '<span class="status-pill unreplied"><i class="fa-regular fa-clock"></i> Belum Dibalas</span>';
  }

  function renderReviews() {
    var data = filteredReviews();
    if (!data.length) {
      reviewsBody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:34px;color:#64748b">Tidak ada ulasan yang cocok.</td></tr>';
      mobileReviews.innerHTML = '<div class="review-card-mobile">Tidak ada ulasan yang cocok.</div>';
      return;
    }
    reviewsBody.innerHTML = data.map(function (r) {
      return '<tr><td><div class="customer"><img src="' + r.avatar + '" alt="' + r.customer + '"><div><b>' + r.customer + '</b><small>' + r.tag + '</small></div></div></td>' +
        '<td><div class="product"><b>' + r.product + '</b><small>' + r.qty + '</small></div></td>' +
        '<td>' + stars(r.rating) + '</td><td><div class="review-text">' + escapeHtml(r.text) + '</div><div class="thumbs">' + r.images.slice(0, 3).map(function (img) { return '<img src="' + img + '" alt="Foto ulasan">'; }).join('') + '</div></td>' +
        '<td><div class="date">' + r.date + '<small>' + r.time + '</small></div></td><td>' + statusHtml(r) + '</td>' +
        '<td><div class="action-row"><button class="mini-btn" data-open="' + r.id + '"><i class="fa-regular fa-eye"></i> Lihat</button><button class="mini-btn" data-reply="' + r.id + '"><i class="fa-regular fa-comment"></i> ' + (r.replied ? 'Edit' : 'Balas') + '</button></div></td></tr>';
    }).join('');

    mobileReviews.innerHTML = data.map(function (r) {
      return '<article class="review-card-mobile"><div class="top"><div class="customer"><img src="' + r.avatar + '" alt="' + r.customer + '"><div><b>' + r.customer + '</b><small>' + r.product + '</small></div></div>' + statusHtml(r) + '</div><div>' + stars(r.rating) + '</div><p>' + escapeHtml(r.text) + '</p><button class="mini-btn" data-open="' + r.id + '"><i class="fa-regular fa-eye"></i> Lihat Detail</button></article>';
    }).join('');
  }

  function openModal(id) {
    var r = reviews.find(function (item) { return item.id === Number(id); });
    if (!r) return;
    selectedId = r.id;
    document.getElementById('modalTitle').textContent = r.customer;
    replyInput.value = r.reply || '';
    saveReplyBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> ' + (r.replied ? 'Edit Reply' : 'Reply');
    deleteReplyBtn.style.display = r.replied ? 'inline-flex' : 'none';
    modalBody.innerHTML =
      '<div class="detail-grid"><div class="detail-card"><h4>Customer profile</h4><div class="profile-line"><img src="' + r.avatar + '" alt="' + r.customer + '"><div><b>' + r.customer + '</b><p>' + r.tag + '</p><small>Terverifikasi</small></div></div></div>' +
      '<div class="detail-card"><h4>Product purchased</h4><div class="kv"><b>' + r.product + '</b><span>Jumlah: ' + r.qty + '</span><span>Rating: ' + stars(r.rating) + '</span></div></div>' +
      '<div class="detail-card"><h4>Order information</h4><div class="kv"><span>Nomor: ' + r.order + '</span><span>Tanggal: ' + r.date + ', ' + r.time + '</span><span>Status: Pesanan selesai</span></div></div>' +
      '<div class="detail-card"><h4>Images uploaded by buyer</h4><div class="image-grid">' + r.images.map(function (img) { return '<img src="' + img + '" alt="Foto pembeli">'; }).join('') + '</div></div></div>' +
      '<div class="detail-card"><h4>Isi Ulasan</h4><p class="review-text">' + escapeHtml(r.text) + '</p></div>' +
      (r.reply ? '<div class="reply-preview"><b>Balasan toko:</b><br>' + escapeHtml(r.reply) + '</div>' : '');
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    selectedId = null;
  }

  function toast(msg) {
    var el = document.createElement('div');
    el.className = 'toast';
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(function () { el.remove(); }, 2400);
  }

  document.addEventListener('click', function (e) {
    var openBtn = e.target.closest('[data-open], [data-reply]');
    if (openBtn) openModal(openBtn.dataset.open || openBtn.dataset.reply);
  });
  document.getElementById('closeModal').addEventListener('click', closeModal);
  modal.addEventListener('click', function (e) { if (e.target === modal) closeModal(); });

  document.getElementById('aiReplyBtn').addEventListener('click', function () {
    var r = reviews.find(function (item) { return item.id === selectedId; });
    if (!r) return;
    var apology = r.rating <= 3 ? 'Mohon maaf atas kendala yang dialami. ' : '';
    replyInput.value = 'Halo ' + r.customer + ', terima kasih sudah memberikan ulasan untuk ' + r.product + '. ' + apology + 'Masukan Anda sangat berarti untuk menjaga kualitas layanan ' + storeName + '.';
  });

  saveReplyBtn.addEventListener('click', function () {
    var r = reviews.find(function (item) { return item.id === selectedId; });
    if (!r || !replyInput.value.trim()) return toast('Balasan belum diisi.');
    var replyText = replyInput.value.trim();
    
    // Save to API
    var btn = saveReplyBtn;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Menyimpan...';
    
    var apiCall = window.WarungioAPI && window.WarungioAPI.replyToReview
      ? WarungioAPI.replyToReview(r.id, { reply: replyText })
      : Promise.resolve();
    
    apiCall.then(function() {
      r.reply = replyText;
      r.replied = true;
      renderMetrics();
      renderReviews();
      openModal(r.id);
      toast('Balasan tersimpan.');
    }).catch(function(err) {
      console.warn('Failed to save reply to API:', err);
      // Still save locally as fallback
      r.reply = replyText;
      r.replied = true;
      renderMetrics();
      renderReviews();
      openModal(r.id);
      toast('Balasan tersimpan (lokal).');
    }).finally(function() {
      btn.disabled = false;
      // Restore original label based on modal state
      var currentR = reviews.find(function (item) { return item.id === selectedId; });
      btn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> ' + (currentR && currentR.replied ? 'Edit Reply' : 'Reply');
    });
  });

  deleteReplyBtn.addEventListener('click', function () {
    var r = reviews.find(function (item) { return item.id === selectedId; });
    if (!r) return;
    
    // Delete from API
    var btn = deleteReplyBtn;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Menghapus...';
    
    var apiCall = window.WarungioAPI && window.WarungioAPI.replyToReview
      ? WarungioAPI.replyToReview(r.id, { reply: '' })
      : Promise.resolve();
    
    apiCall.then(function() {
      r.reply = '';
      r.replied = false;
      renderMetrics();
      renderReviews();
      openModal(r.id);
      toast('Balasan dihapus.');
    }).catch(function(err) {
      console.warn('Failed to delete reply from API:', err);
      // Still delete locally as fallback
      r.reply = '';
      r.replied = false;
      renderMetrics();
      renderReviews();
      openModal(r.id);
      toast('Balasan dihapus (lokal).');
    }).finally(function() {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-trash"></i> Delete Reply';
    });
  });

  [searchInput, ratingFilter, statusFilter].forEach(function (el) {
    el.addEventListener('input', renderReviews);
    el.addEventListener('change', renderReviews);
  });

  // Load from API instead of hardcoded data
  loadReviews();
});
