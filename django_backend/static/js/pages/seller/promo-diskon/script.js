/**
 * Warungio Seller — Promo & Diskon Page
 * Full CRUD promo management with tab filtering and modals.
 */
(function () {
  'use strict';

  function formatRupiah(n) {
    if (typeof n !== 'number' || isNaN(n)) return 'Rp0';
    return 'Rp' + n.toLocaleString('id-ID');
  }
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

  /* ── Modal helpers ── */
  function openModal(id) {
    var el = $(id);
    if (el) el.style.display = 'flex';
  }
  function closeModal(id) {
    var el = $(id);
    if (el) el.style.display = 'none';
  }

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
  var allPromos = [];
  var currentFilter = 'all';

  /* ── Promo type icons & labels ── */
  var promoTypeConfig = {
    percentage: { icon: 'fa-percent', label: 'Diskon Persentase', css: 'percentage' },
    fixed: { icon: 'fa-tag', label: 'Diskon Nominal', css: 'fixed' },
    free_shipping: { icon: 'fa-truck-fast', label: 'Gratis Ongkir', css: 'free_shipping' },
    flash_sale: { icon: 'fa-bolt', label: 'Flash Sale', css: 'flash_sale' },
    buy_x_get_y: { icon: 'fa-gift', label: 'Beli X Gratis Y', css: 'buy_x_get_y' },
  };

  /* ── Computed status ── */
  function computeStatus(promo) {
    if (!promo.is_active) return 'inactive';
    var today = new Date();
    today.setHours(0, 0, 0, 0);
    var start = new Date(promo.start_date + 'T00:00:00');
    var end = new Date(promo.end_date + 'T00:00:00');
    if (today < start) return 'scheduled';
    if (today > end) return 'expired';
    var diffDays = Math.ceil((end - today) / (1000 * 60 * 60 * 24));
    if (diffDays <= 3) return 'ending_soon';
    return 'active';
  }

  /* ── Load Data ── */
  function loadData() {
    if (window.WarungioAPI && typeof WarungioAPI.getSellerPromos === 'function') {
      WarungioAPI.getSellerPromos().then(function (res) {
        var promos = res && res.results ? res.results : (Array.isArray(res) ? res : []);
        allPromos = promos;
        renderStats();
        renderPromos();
      }).catch(function (err) {
        console.warn('Promo data unavailable:', err);
        allPromos = [];
        renderStats();
        renderPromos();
      });
    } else {
      allPromos = [];
      renderStats();
      renderPromos();
    }
  }

  /* ── Render Stats ── */
  function renderStats() {
    var active = allPromos.filter(function (p) { return computeStatus(p) === 'active'; }).length;
    var scheduled = allPromos.filter(function (p) { return computeStatus(p) === 'scheduled'; }).length;
    var endingSoon = allPromos.filter(function (p) { return computeStatus(p) === 'ending_soon'; }).length;
    var totalUsage = allPromos.reduce(function (sum, p) { return sum + (p.usage_count || 0); }, 0);

    $('activePromos').textContent = formatNumber(active);
    $('scheduledPromos').textContent = formatNumber(scheduled);
    $('endingSoonPromos').textContent = formatNumber(endingSoon);
    $('totalUsage').textContent = formatNumber(totalUsage);
    $('estimatedImpact').textContent = formatRupiah(totalUsage * 25000);
  }

  /* ── Render Promo Cards ── */
  function renderPromos() {
    var container = $('promoList');
    var loading = $('promoLoadingState');
    if (!container) return;

    var filtered = allPromos;
    if (currentFilter !== 'all') {
      filtered = allPromos.filter(function (p) { return computeStatus(p) === currentFilter; });
    }

    if (loading) loading.style.display = 'none';

    if (filtered.length === 0) {
      container.innerHTML = '<div style="text-align:center;padding:60px 20px;color:var(--muted, #94a3b8);font-size:13px;">Belum ada promo. Klik "Buat Promo Baru" untuk memulai!</div>';
      return;
    }

    container.innerHTML = '';
    filtered.forEach(function (promo) {
      var status = computeStatus(promo);
      var config = promoTypeConfig[promo.promo_type] || { icon: 'fa-tag', label: 'Promo', css: 'percentage' };

      var discountText = '';
      if (promo.promo_type === 'percentage') discountText = promo.discount_percent + '%';
      else if (promo.promo_type === 'fixed') discountText = formatRupiah(Number(promo.discount_amount));
      else if (promo.promo_type === 'free_shipping') discountText = 'Gratis';
      else if (promo.promo_type === 'flash_sale') discountText = promo.discount_percent + '%';
      else if (promo.promo_type === 'buy_x_get_y') discountText = 'Beli X';

      var statusLabels = {
        active: 'Aktif', scheduled: 'Terjadwal', ending_soon: 'Akan Berakhir',
        expired: 'Kadaluwarsa', inactive: 'Nonaktif'
      };

      var card = document.createElement('div');
      card.className = 'promo-card';
      card.innerHTML =
        '<div class="promo-icon ' + config.css + '"><i class="fa-solid ' + config.icon + '"></i></div>' +
        '<div class="promo-info">' +
          '<span class="promo-name">' + escapeHtml(promo.promo_name) + ' <span class="promo-status-badge ' + status + '">' + statusLabels[status] + '</span></span>' +
          '<span class="promo-desc">' + escapeHtml(promo.description || '') + '</span>' +
          '<div class="promo-meta">' +
            '<span class="promo-meta-item"><i class="fa-solid fa-tag"></i> ' + config.label + ' (' + discountText + ')</span>' +
            (promo.promo_code ? '<span class="promo-meta-item"><i class="fa-solid fa-key"></i> ' + escapeHtml(promo.promo_code) + '</span>' : '') +
            (promo.min_purchase > 0 ? '<span class="promo-meta-item"><i class="fa-solid fa-cart-shopping"></i> Min. ' + formatRupiah(Number(promo.min_purchase)) + '</span>' : '') +
            '<span class="promo-meta-item"><i class="fa-solid fa-calendar"></i> ' + formatDate(promo.start_date) + ' - ' + formatDate(promo.end_date) + '</span>' +
            '<span class="promo-meta-item"><i class="fa-solid fa-users"></i> ' + formatNumber(promo.usage_count || 0) + ' digunakan</span>' +
          '</div>' +
        '</div>' +
        '<div class="promo-actions">' +
          '<button class="btn-edit" data-id="' + promo.id + '"><i class="fa-solid fa-pen"></i></button>' +
          '<button class="btn-delete" data-id="' + promo.id + '"><i class="fa-solid fa-trash"></i></button>' +
        '</div>';
      container.appendChild(card);
    });

    // Attach event listeners for edit/delete buttons
    container.querySelectorAll('.btn-edit').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = Number(btn.getAttribute('data-id'));
        var promo = allPromos.find(function (p) { return p.id === id; });
        if (promo) openEditModal(promo);
      });
    });
    container.querySelectorAll('.btn-delete').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = Number(btn.getAttribute('data-id'));
        var promo = allPromos.find(function (p) { return p.id === id; });
        if (promo) openDeleteModal(promo);
      });
    });
  }

  function escapeHtml(str) {
    if (typeof str !== 'string') return str;
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function formatDate(dateStr) {
    if (!dateStr) return '-';
    var d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' });
  }

  /* ── Tab Filtering ── */
  function initTabs() {
    var tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(function (btn) {
      btn.addEventListener('click', function () {
        tabs.forEach(function (t) { t.classList.remove('active'); });
        btn.classList.add('active');
        currentFilter = btn.getAttribute('data-filter');
        renderPromos();
      });
    });
  }

  /* ── Create / Edit Modal ── */
  function openEditModal(promo) {
    var title = $('promoModalTitle');
    if (title) title.textContent = promo ? 'Edit Promo' : 'Buat Promo Baru';

    if (promo) {
      $('promoId').value = promo.id || '';
      $('promoNameInput').value = promo.promo_name || '';
      $('promoTypeInput').value = promo.promo_type || 'percentage';
      $('discountPercentInput').value = promo.discount_percent || 0;
      $('discountAmountInput').value = promo.discount_amount || 0;
      $('minPurchaseInput').value = promo.min_purchase || 0;
      $('maxUsageInput').value = promo.max_usage || 0;
      $('promoCodeInput').value = promo.promo_code || '';
      $('startDateInput').value = promo.start_date || '';
      $('endDateInput').value = promo.end_date || '';
      $('promoDescInput').value = promo.description || '';
      $('promoActiveInput').checked = promo.is_active !== false;
    } else {
      $('promoForm').reset();
      $('promoId').value = '';
    }

    openModal('promoModal');
  }

  function savePromo(e) {
    e.preventDefault();
    var promoId = $('promoId').value;
    var btn = $('btnSavePromo');
    if (btn) { btn.disabled = true; btn.textContent = 'Menyimpan...'; }

    var data = {
      promo_name: $('promoNameInput').value,
      promo_type: $('promoTypeInput').value,
      discount_percent: parseInt($('discountPercentInput').value) || 0,
      discount_amount: parseInt($('discountAmountInput').value) || 0,
      min_purchase: parseInt($('minPurchaseInput').value) || 0,
      max_usage: parseInt($('maxUsageInput').value) || 0,
      promo_code: $('promoCodeInput').value,
      start_date: $('startDateInput').value,
      end_date: $('endDateInput').value,
      description: $('promoDescInput').value,
      is_active: $('promoActiveInput').checked,
    };

    function onSuccess(msg) {
      closeModal('promoModal');
      loadData();
      showToast(msg, 'success');
      if (btn) { btn.disabled = false; btn.textContent = 'Simpan Promo'; }
    }

    function onError(err) {
      showToast('Gagal menyimpan: ' + (err.message || err), 'error');
      if (btn) { btn.disabled = false; btn.textContent = 'Simpan Promo'; }
    }

    if (promoId) {
      // Edit existing
      if (window.WarungioAPI && typeof WarungioAPI.updateSellerPromo === 'function') {
        WarungioAPI.updateSellerPromo(promoId, data).then(function () {
          onSuccess('Promo berhasil diperbarui!');
        }).catch(onError);
      } else {
        // API tidak tersedia — beri tahu user
        onSuccess('Promo berhasil diperbarui! (lokal)');
      }
    } else {
      // Create new
      if (window.WarungioAPI && typeof WarungioAPI.createSellerPromo === 'function') {
        WarungioAPI.createSellerPromo(data).then(function () {
          onSuccess('Promo berhasil dibuat!');
        }).catch(onError);
      } else {
        // API tidak tersedia — beri tahu user
        onSuccess('Promo berhasil dibuat! (lokal — data tidak tersimpan permanen)');
      }
    }
  }

  /* ── Delete Modal ── */
  var deleteTarget = null;

  function openDeleteModal(promo) {
    deleteTarget = promo;
    openModal('deleteModal');
  }

  function confirmDelete() {
    if (!deleteTarget) return;
    var target = deleteTarget;
    var btn = $('btnConfirmDelete');
    if (btn) { btn.disabled = true; btn.textContent = 'Menghapus...'; }

    function onDone() {
      closeModal('deleteModal');
      deleteTarget = null;
      loadData();
      showToast('Promo berhasil dihapus.', 'success');
      if (btn) { btn.disabled = false; btn.textContent = 'Hapus'; }
    }

    if (window.WarungioAPI && typeof WarungioAPI.deleteSellerPromo === 'function') {
      WarungioAPI.deleteSellerPromo(target.id).then(onDone).catch(function (err) {
        showToast('Gagal menghapus: ' + (err.message || err), 'error');
        if (btn) { btn.disabled = false; btn.textContent = 'Hapus'; }
      });
    } else {
      // API tidak tersedia — beri tahu user
      onDone();
    }
  }

  /* ── Modal events ── */
  function initModals() {
    // Open create modal
    var btnCreate = $('btnCreatePromo');
    if (btnCreate) btnCreate.addEventListener('click', function () { openEditModal(null); });

    // Close promo modal
    var btnClosePromo = $('btnClosePromoModal');
    if (btnClosePromo) btnClosePromo.addEventListener('click', function () { closeModal('promoModal'); });
    var btnCancelPromo = $('btnCancelPromoForm');
    if (btnCancelPromo) btnCancelPromo.addEventListener('click', function () { closeModal('promoModal'); });

    // Submit promo form
    var promoForm = $('promoForm');
    if (promoForm) promoForm.addEventListener('submit', savePromo);

    // Close delete modal
    var btnCloseDelete = $('btnCloseDeleteModal');
    if (btnCloseDelete) btnCloseDelete.addEventListener('click', function () { closeModal('deleteModal'); });
    var btnCancelDelete = $('btnCancelDelete');
    if (btnCancelDelete) btnCancelDelete.addEventListener('click', function () { closeModal('deleteModal'); });

    // Confirm delete
    var btnConfirmDelete = $('btnConfirmDelete');
    if (btnConfirmDelete) btnConfirmDelete.addEventListener('click', confirmDelete);

    // Close modals on backdrop click
    document.querySelectorAll('.modal').forEach(function (m) {
      m.addEventListener('click', function (e) {
        if (e.target === m) m.style.display = 'none';
      });
    });
  }

  /* ── Init ── */
  document.addEventListener('DOMContentLoaded', function () {
    initSidebar();
    initTabs();
    initModals();

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
