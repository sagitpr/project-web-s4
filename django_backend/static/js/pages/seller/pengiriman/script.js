/**
 * Warungio Seller — Pengiriman Page
 * Delivery tracking, Mitra Driver management, Tariff management, Driver assignment.
 * All data from real API — no mock/placeholder.
 */
(function () {
  'use strict';

  if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
    window.location.href = '/?next=' + encodeURIComponent(window.location.pathname);
    return;
  }

  var API = window.WarungioAPI;

  /* ── Helpers ── */
  function $(id) { return document.getElementById(id); }

  function toRupiah(n) { return 'Rp ' + Number(n).toLocaleString('id-ID'); }

  function escapeHtml(str) {
    if (!str) return '';
    var d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  function showToast(msg, type) {
    if (window.WarungioToast) { WarungioToast.show(msg, type || 'success'); return; }
    var t = document.createElement('div');
    t.className = 'toast-notification';
    t.textContent = msg;
    if (type === 'error') t.style.background = '#DC2626'; else t.style.background = '#16A34A';
    document.body.appendChild(t);
    setTimeout(function () { t.classList.add('show'); }, 50);
    setTimeout(function () { t.classList.remove('show'); setTimeout(function () { t.remove(); }, 300); }, 4000);
  }

  /* ── Tab Navigation ── */
  function initTabs() {
    var tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(function (btn) {
      btn.addEventListener('click', function () {
        tabs.forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        document.querySelectorAll('.tab-content').forEach(function (c) { c.classList.remove('active'); });
        var tabId = 'tab' + btn.dataset.tab.charAt(0).toUpperCase() + btn.dataset.tab.slice(1);
        var content = $(tabId);
        if (content) content.classList.add('active');
      });
    });
  }

  /* ── DELIVERY TRACKING ── */
  var LABELS = {
    menunggu_konfirmasi: 'Menunggu', diproses_penjual: 'Diproses',
    menunggu_penjemputan: 'Jemput', kurir_menjemput: 'Kurir Jemput',
    dalam_perjalanan: 'Dikirim', pesanan_diterima: 'Sampai', dibatalkan: 'Batal'
  };
  var BADGES = {
    menunggu_konfirmasi: 'badge-waiting', diproses_penjual: 'badge-processing',
    menunggu_penjemputan: 'badge-pickup', kurir_menjemput: 'badge-pickup',
    dalam_perjalanan: 'badge-delivery', pesanan_diterima: 'badge-completed', dibatalkan: 'badge-cancelled'
  };
  var currentFilter = 'all';
  var allDeliveries = [];

  async function loadDeliveries() {
    try {
      var orders = await API.getSellerOrders();
      allDeliveries = orders.results || orders || [];
      renderDeliveries();
    } catch (e) {
      $('deliveryTableBody').innerHTML = '<tr><td colspan="7" class="empty-cell"><div class="empty-state"><i class="fa-solid fa-truck"></i><p>Gagal memuat data. Pastikan Anda sudah login.</p></div></td></tr>';
    }
  }

  function renderDeliveries() {
    var filtered = currentFilter === 'all' ? allDeliveries : allDeliveries.filter(function (o) { return (o.order_status || o.delivery?.delivery_status) === currentFilter; });
    var stats = { menunggu_konfirmasi: 0, diproses_penjual: 0, menunggu_penjemputan: 0, kurir_menjemput: 0, dalam_perjalanan: 0, pesanan_diterima: 0, dibatalkan: 0 };
    allDeliveries.forEach(function (o) {
      var s = o.delivery?.delivery_status || o.order_status;
      if (stats[s] !== undefined) stats[s]++;
    });
    $('countOnDelivery').textContent = stats.dalam_perjalanan || 0;
    $('countPickup').textContent = stats.menunggu_penjemputan || 0;
    $('countReady').textContent = (stats.diproses_penjual || 0) + (stats.kurir_menjemput || 0);
    $('countCompleted').textContent = stats.pesanan_diterima || 0;

    if (!filtered.length) {
      $('deliveryTableBody').innerHTML = '<tr><td colspan="7" class="empty-cell"><div class="empty-state"><i class="fa-solid fa-box-open"></i><p>Tidak ada data pengiriman.</p></div></td></tr>';
      return;
    }
    $('deliveryTableBody').innerHTML = filtered.map(function (o) {
      var status = o.delivery?.delivery_status || o.order_status || 'menunggu_konfirmasi';
      var detailUrl = '{% url "page-seller-order-detail" %}?id=' + o.id;
      var driverName = o.delivery?.driver_name || '-';
      var estTime = o.delivery?.estimated_time || '-';
      var orderDetailBase = window.WarungioOrderDetailURL || '/seller/order-detail/';
      var detailUrl = orderDetailBase + '?id=' + o.id;
      return '<tr><td><strong>' + escapeHtml(o.order_number || '#') + '</strong></td>' +
        '<td>' + escapeHtml(o.recipient_name || '-') + '</td>' +
        '<td>' + escapeHtml(o.courier || (o.delivery && o.delivery.courier_name) || 'GoSend') + '</td>' +
        '<td><span class="badge ' + (BADGES[status] || 'badge-waiting') + '">' + (LABELS[status] || status) + '</span></td>' +
        '<td>' + escapeHtml(driverName) + '</td>' +
        '<td>' + escapeHtml(estTime) + '</td>' +
        '<td style="text-align:right">' +
        '<a href="' + detailUrl + '" class="btn btn-sm btn-ghost" style="margin-right:4px;"><i class="fa-solid fa-eye"></i></a>' +
        '<button class="btn btn-sm btn-ghost qr-delivery-btn" data-order-id="' + o.id + '" title="Generate QR Delivery"><i class="fa-solid fa-qrcode"></i> QR</button> ' +
        '<button class="btn btn-sm btn-ghost qr-pickup-btn" data-order-id="' + o.id + '" title="Generate QR Pickup"><i class="fa-solid fa-box"></i> Pickup</button> ' +
        '<button class="btn btn-sm btn-primary assign-driver-btn" data-delivery-id="' + ((o.delivery && o.delivery.id) || '') + '" data-order-id="' + o.id + '" data-order-number="' + escapeHtml(o.order_number || '') + '"><i class="fa-solid fa-user-plus"></i> Driver</button>' +
        '</td></tr>';
    }).join('');

    // Assign driver button handlers
    document.querySelectorAll('.assign-driver-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        openAssignModal(this.dataset.deliveryId, this.dataset.orderId, this.dataset.orderNumber);
      });
    });
  }

  /* ── Filter Buttons ── */
  function initFilters() {
    document.querySelectorAll('.filter-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        document.querySelectorAll('.filter-btn').forEach(function (b) { b.classList.remove('active'); });
        this.classList.add('active');
        currentFilter = this.dataset.filter;
        renderDeliveries();
      });
    });
  }

  /* ── DRIVER CRUD ── */
  var drivers = [];

  async function loadDrivers() {
    try {
      var res = await API.getMitraDrivers();
      drivers = Array.isArray(res) ? res : (res.results || []);
      renderDrivers();
    } catch (e) {
      $('driverTableBody').innerHTML = '<tr><td colspan="8" class="empty-cell"><div class="empty-state"><i class="fa-solid fa-users"></i><p>Gagal memuat driver.</p></div></td></tr>';
    }
  }

  function renderDrivers() {
    if (!drivers.length) {
      $('driverTableBody').innerHTML = '<tr><td colspan="8" class="empty-cell"><div class="empty-state"><i class="fa-solid fa-users"></i><p>Belum ada driver. Klik "Tambah Driver" untuk menambahkan.</p></div></td></tr>';
      return;
    }
    var statusLabels = { available: 'Tersedia', on_delivery: 'Mengantar', offline: 'Offline', inactive: 'Nonaktif' };
    var statusColors = { available: '#22c55e', on_delivery: '#f59e0b', offline: '#94a3b8', inactive: '#ef4444' };
    $('driverTableBody').innerHTML = drivers.map(function (d) {
      var vehicleType = d.vehicle_type || '-';
      var vehiclePlate = d.vehicle_plate || '-';
      return '<tr>' +
        '<td><strong>' + escapeHtml(d.name) + '</strong></td>' +
        '<td>' + escapeHtml(d.phone) + '</td>' +
        '<td>' + escapeHtml(vehicleType) + '</td>' +
        '<td>' + escapeHtml(vehiclePlate) + '</td>' +
        '<td>' + escapeHtml(d.service_area || 'Semua') + '</td>' +
        '<td><span style="background:' + (statusColors[d.status] || '#94a3b8') + '20;color:' + (statusColors[d.status] || '#94a3b8') + ';padding:2px 8px;border-radius:4px;font-weight:600;font-size:11px;">' + (statusLabels[d.status] || d.status) + '</span></td>' +
        '<td>' + (d.total_deliveries || 0) + '</td>' +
        '<td style="text-align:right">' +
        '<button class="btn btn-sm btn-ghost edit-driver-btn" data-id="' + d.id + '"><i class="fa-solid fa-pen"></i></button> ' +
        '<button class="btn btn-sm btn-danger delete-driver-btn" data-id="' + d.id + '" data-name="' + escapeHtml(d.name) + '"><i class="fa-solid fa-trash"></i></button>' +
        '</td></tr>';
    }).join('');

    document.querySelectorAll('.edit-driver-btn').forEach(function (btn) {
      btn.addEventListener('click', function () { editDriver(parseInt(this.dataset.id)); });
    });
    document.querySelectorAll('.delete-driver-btn').forEach(function (btn) {
      btn.addEventListener('click', function () { deleteDriver(parseInt(this.dataset.id), this.dataset.name); });
    });
  }

  function openDriverModal(driver) {
    $('driverModalTitle').textContent = driver ? 'Edit Driver' : 'Tambah Driver';
    $('driverId').value = driver ? driver.id : '';
    $('driverName').value = driver ? driver.name : '';
    $('driverPhone').value = driver ? driver.phone : '';
    $('driverEmail').value = driver ? (driver.email || '') : '';
    $('driverVehicleType').value = driver ? (driver.vehicle_type || 'Motor') : 'Motor';
    $('driverVehicleBrand').value = driver ? (driver.vehicle_brand || '') : '';
    $('driverVehiclePlate').value = driver ? (driver.vehicle_plate || '') : '';
    $('driverVehicleColor').value = driver ? (driver.vehicle_color || '') : '';
    $('driverServiceArea').value = driver ? (driver.service_area || '') : '';
    $('driverMaxDistance').value = driver ? (driver.max_distance_km || 10) : 10;
    $('driverStatus').value = driver ? (driver.status || 'available') : 'available';
    $('driverModal').style.display = 'flex';
  }

  function editDriver(id) {
    var d = drivers.find(function (x) { return x.id === id; });
    if (d) openDriverModal(d);
  }

  async function saveDriver() {
    var id = $('driverId').value;
    var data = {
      name: $('driverName').value,
      phone: $('driverPhone').value,
      email: $('driverEmail').value,
      vehicle_type: $('driverVehicleType').value,
      vehicle_brand: $('driverVehicleBrand').value,
      vehicle_plate: $('driverVehiclePlate').value,
      vehicle_color: $('driverVehicleColor').value,
      service_area: $('driverServiceArea').value,
      max_distance_km: parseFloat($('driverMaxDistance').value) || 10,
      status: $('driverStatus').value,
    };
    try {
      if (id) {
        await API.updateMitraDriver(parseInt(id), data);
        showToast('Driver berhasil diperbarui.', 'success');
      } else {
        await API.createMitraDriver(data);
        showToast('Driver baru berhasil ditambahkan.', 'success');
      }
      $('driverModal').style.display = 'none';
      loadDrivers();
    } catch (e) {
      showToast(e.message || 'Gagal menyimpan driver.', 'error');
    }
  }

  async function deleteDriver(id, name) {
    if (!confirm('Yakin ingin menghapus driver "' + name + '"?')) return;
    try {
      await API.deleteMitraDriver(id);
      showToast('Driver berhasil dihapus.', 'success');
      loadDrivers();
    } catch (e) {
      showToast(e.message || 'Gagal menghapus driver.', 'error');
    }
  }

  /* ── TARIFF CRUD ── */
  var tariffs = [];

  async function loadTariffs() {
    try {
      var res = await API.getMitraTariffs();
      tariffs = Array.isArray(res) ? res : (res.results || []);
      renderTariffs();
    } catch (e) {
      $('tariffTableBody').innerHTML = '<tr><td colspan="9" class="empty-cell"><div class="empty-state"><i class="fa-solid fa-money-bill-wave"></i><p>Gagal memuat tarif.</p></div></td></tr>';
    }
  }

  function renderTariffs() {
    if (!tariffs.length) {
      $('tariffTableBody').innerHTML = '<tr><td colspan="9" class="empty-cell"><div class="empty-state"><i class="fa-solid fa-money-bill-wave"></i><p>Belum ada tarif.</p></div></td></tr>';
      return;
    }
    $('tariffTableBody').innerHTML = tariffs.map(function (t) {
      return '<tr>' +
        '<td><strong>' + escapeHtml(t.name) + '</strong></td>' +
        '<td>' + toRupiah(t.base_fee) + '</td>' +
        '<td>' + toRupiah(t.price_per_km) + '</td>' +
        '<td>' + (t.free_km || 0) + ' km</td>' +
        '<td>' + toRupiah(t.min_fee) + '</td>' +
        '<td>' + (t.max_fee ? toRupiah(t.max_fee) : '-') + '</td>' +
        '<td>' + (t.max_distance_km || 20) + ' km</td>' +
        '<td><span class="badge ' + (t.is_active ? 'badge-completed' : 'badge-cancelled') + '">' + (t.is_active ? 'Aktif' : 'Nonaktif') + '</span></td>' +
        '<td style="text-align:right">' +
        '<button class="btn btn-sm btn-ghost edit-tariff-btn" data-id="' + t.id + '"><i class="fa-solid fa-pen"></i></button>' +
        '</td></tr>';
    }).join('');
    document.querySelectorAll('.edit-tariff-btn').forEach(function (btn) {
      btn.addEventListener('click', function () { editTariff(parseInt(this.dataset.id)); });
    });
  }

  function openTariffModal(tariff) {
    $('tariffModalTitle').textContent = tariff ? 'Edit Tarif' : 'Tambah Tarif';
    $('tariffId').value = tariff ? tariff.id : '';
    $('tariffName').value = tariff ? tariff.name : 'Standar';
    $('tariffBaseFee').value = tariff ? tariff.base_fee : 5000;
    $('tariffPerKm').value = tariff ? tariff.price_per_km : 2000;
    $('tariffFreeKm').value = tariff ? tariff.free_km : 2;
    $('tariffMinFee').value = tariff ? tariff.min_fee : 5000;
    $('tariffMaxFee').value = tariff ? (tariff.max_fee || '') : '';
    $('tariffMaxDistance').value = tariff ? tariff.max_distance_km : 20;
    $('tariffIsActive').checked = tariff ? tariff.is_active : true;
    $('tariffModal').style.display = 'flex';
  }

  function editTariff(id) {
    var t = tariffs.find(function (x) { return x.id === id; });
    if (t) openTariffModal(t);
  }

  async function saveTariff() {
    var id = $('tariffId').value;
    var data = {
      name: $('tariffName').value,
      base_fee: parseFloat($('tariffBaseFee').value) || 0,
      price_per_km: parseFloat($('tariffPerKm').value) || 0,
      free_km: parseFloat($('tariffFreeKm').value) || 0,
      min_fee: parseFloat($('tariffMinFee').value) || 0,
      max_fee: $('tariffMaxFee').value ? parseFloat($('tariffMaxFee').value) : null,
      max_distance_km: parseFloat($('tariffMaxDistance').value) || 20,
      is_active: $('tariffIsActive').checked,
    };
    try {
      if (id) {
        await API.updateMitraTariff(parseInt(id), data);
        showToast('Tarif berhasil diperbarui.', 'success');
      } else {
        await API.createMitraTariff(data);
        showToast('Tarif baru berhasil ditambahkan.', 'success');
      }
      $('tariffModal').style.display = 'none';
      loadTariffs();
    } catch (e) {
      showToast(e.message || 'Gagal menyimpan tarif.', 'error');
    }
  }

  /* ── ASSIGN DRIVER MODAL ── */
  var assignDeliveryId = null;
  var assignOrderId = null;

  function openAssignModal(deliveryId, orderId, orderNumber) {
    assignDeliveryId = deliveryId;
    assignOrderId = orderId;
    $('assignDeliveryId').value = deliveryId || '';
    $('assignOrderNumber').textContent = orderNumber || '#' + orderId;

    // Populate driver select
    var select = $('assignDriverSelect');
    select.innerHTML = '<option value="">-- Pilih Driver --</option>';
    var availableDrivers = drivers.filter(function (d) { return d.status === 'available' && d.is_active; });
    if (!availableDrivers.length) availableDrivers = drivers.filter(function (d) { return d.status !== 'inactive'; });
    availableDrivers.forEach(function (d) {
      var opt = document.createElement('option');
      opt.value = d.id;
      opt.textContent = d.name + ' (' + (d.vehicle_type || 'Motor') + ') - ' + d.phone;
      select.appendChild(opt);
    });
    $('assignDriverModal').style.display = 'flex';
  }

  async function confirmAssignDriver() {
    var driverId = $('assignDriverSelect').value;
    if (!driverId) {
      showToast('Pilih driver terlebih dahulu.', 'error');
      return;
    }
    var confirmBtn = $('assignModalConfirm');
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = 'Menugaskan...';
    try {
      var deliveryId = assignDeliveryId || assignOrderId;
      if (!deliveryId) deliveryId = assignOrderId;
      await API.assignMitraDriver({ delivery_id: deliveryId, driver_id: parseInt(driverId) });
      showToast('Driver berhasil ditugaskan!', 'success');
      $('assignDriverModal').style.display = 'none';
      loadDeliveries();
      loadDrivers();
    } catch (e) {
      showToast(e.message || 'Gagal menugaskan driver.', 'error');
    } finally {
      confirmBtn.disabled = false;
      confirmBtn.innerHTML = 'Tugaskan';
    }
  }

  /* ── Modal helpers ── */
  function initModals() {
    // Driver modal
    $('addDriverBtn')?.addEventListener('click', function () { openDriverModal(null); });
    $('driverModalClose')?.addEventListener('click', function () { $('driverModal').style.display = 'none'; });
    $('driverModalCancel')?.addEventListener('click', function () { $('driverModal').style.display = 'none'; });
    $('driverModal')?.addEventListener('click', function (e) { if (e.target === this) this.style.display = 'none'; });
    $('driverModalSave')?.addEventListener('click', saveDriver);

    // Tariff modal
    $('addTariffBtn')?.addEventListener('click', function () { openTariffModal(null); });
    $('tariffModalClose')?.addEventListener('click', function () { $('tariffModal').style.display = 'none'; });
    $('tariffModalCancel')?.addEventListener('click', function () { $('tariffModal').style.display = 'none'; });
    $('tariffModal')?.addEventListener('click', function (e) { if (e.target === this) this.style.display = 'none'; });
    $('tariffModalSave')?.addEventListener('click', saveTariff);

    // Assign modal
    $('assignModalClose')?.addEventListener('click', function () { $('assignDriverModal').style.display = 'none'; });
    $('assignModalCancel')?.addEventListener('click', function () { $('assignDriverModal').style.display = 'none'; });
    $('assignDriverModal')?.addEventListener('click', function (e) { if (e.target === this) this.style.display = 'none'; });
    $('assignModalConfirm')?.addEventListener('click', confirmAssignDriver);
  }

  /* ── WebSocket Realtime ── */
  function initRealtimeUpdates() {
    var retries = 0;
    function trySetup() {
      if (retries >= 10) return;
      if (typeof WarungioWS === 'undefined' || typeof WarungioWS.on !== 'function') {
        retries++;
        setTimeout(trySetup, 1000);
        return;
      }
      WarungioWS.on('delivery_update', function () { loadDeliveries(); });
      WarungioWS.on('order_update', function () { loadDeliveries(); });
      WarungioWS.on('payment_update', function () { loadDeliveries(); });
    }
    trySetup();
  }

  /* ── Sidebar ads close ── */
  $('sidebarAdsClose')?.addEventListener('click', function() {
    var ads = document.querySelector('.sidebar-ads');
    if (ads) ads.style.display = 'none';
  });

  /* ── QR CODE GENERATION ── */
  function attachQRActions() {
    document.querySelectorAll('.qr-delivery-btn, .qr-pickup-btn').forEach(function (btn) {
      btn.removeEventListener('click', btn._qrHandler);
    });
    document.querySelectorAll('.qr-delivery-btn').forEach(function (btn) {
      var handler = async function () {
        var orderId = this.dataset.orderId;
        if (!orderId) return;
        try {
          await API.generateDeliveryQR(orderId, 'delivery');
          showToast('QR Delivery berhasil dibuat!', 'success');
          loadDeliveries();
        } catch (e) {
          showToast(e.message || 'Gagal generate QR', 'error');
        }
      };
      btn._qrHandler = handler;
      btn.addEventListener('click', handler);
    });
    document.querySelectorAll('.qr-pickup-btn').forEach(function (btn) {
      var handler = async function () {
        var orderId = this.dataset.orderId;
        if (!orderId) return;
        try {
          await API.generateDeliveryQR(orderId, 'pickup');
          showToast('QR Pickup berhasil dibuat!', 'success');
          loadDeliveries();
        } catch (e) {
          showToast(e.message || 'Gagal generate QR', 'error');
        }
      };
      btn._qrHandler = handler;
      btn.addEventListener('click', handler);
    });
  }

  /* ── Override renderDeliveries to add QR columns ── */
  var _origRD = renderDeliveries;
  renderDeliveries = function() {
    _origRD();
    attachQRActions();
  };

  /* ── Init ── */
  document.addEventListener('DOMContentLoaded', function () {
    initTabs();
    initFilters();
    initModals();
    loadDeliveries();
    loadDrivers();
    loadTariffs();
    initRealtimeUpdates();
  });

})();
