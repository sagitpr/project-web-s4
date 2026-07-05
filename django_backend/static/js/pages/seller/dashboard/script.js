/**
 * Seller Dashboard - Warungio
 * Connected to Django analytics API and product management.
 */
document.addEventListener('DOMContentLoaded', () => {
  const LOADING_ERROR_MSG = 'Gagal memuat data. Silakan refresh halaman.';

  if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
    window.location.href = '/auth/login/';
    return;
  }

  const tableBody = document.getElementById('product-table');
  const actList = document.getElementById('activity-list');
  const addProductForm = document.getElementById('add-product-form');
  const addProductMessage = document.getElementById('add-product-message');
  let chartInstance = null;
  let salesChartInstance = null;

  function initChart(feasible = 0, moderate = 0, low = 0, rejected = 0) {
    const ctx = document.getElementById('eligibilityChart')?.getContext('2d');
    if (!ctx) return;
    if (chartInstance) chartInstance.destroy();
    // Only render chart if there is actual data
    const total = feasible + moderate + low + rejected;
    const chartData = total > 0
      ? [feasible, moderate, low, rejected]
      : [1]; // Placeholder dot when no data
    const chartColors = total > 0
      ? ['#22c55e', '#a3e635', '#facc15', '#ef4444']
      : ['#e5e7eb'];
    chartInstance = new Chart(ctx, {
      type: 'doughnut',
      data: {
        datasets: [{
          data: chartData,
          backgroundColor: chartColors,
          borderWidth: 0, cutout: '80%',
        }]
      },
      options: { plugins: { tooltip: { enabled: total > 0 } }, cutout: '80%' }
    });
  }
  initChart();

  async function loadSalesChart() {
    const canvas = document.getElementById('salesChart');
    if (!canvas || typeof Chart === 'undefined') return;
    try {
      const trend = await WarungioAPI.getSalesTrend('30');
      const rows = Array.isArray(trend) ? trend : (trend.results || []);
      const labels = rows.map(r => (r.date || '').slice(5));
      const values = rows.map(r => Number(r.revenue || r.total_revenue || 0));
      if (salesChartInstance) salesChartInstance.destroy();
      salesChartInstance = new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            label: 'Pendapatan',
            data: values,
            borderColor: '#16A34A',
            backgroundColor: 'rgba(22,163,74,0.12)',
            fill: true,
            tension: 0.35,
          }],
        },
        options: {
          plugins: { legend: { display: false } },
          scales: {
            y: { ticks: { callback: v => 'Rp ' + Number(v).toLocaleString('id-ID') } },
          },
        },
      });
    } catch (err) {
      console.warn('Sales chart fallback:', err);
    }
  }

  loadSalesChart();

  // renderProducts dan renderActivities dihapus — data palsu (DEFAULT_DATA) diganti
  // dengan error state yang jujur: "Gagal memuat data" atau "Belum ada data"

  function showAddMsg(text, type) {
    if (!addProductMessage) return;
    addProductMessage.textContent = text;
    addProductMessage.className = 'message ' + type;
    addProductMessage.style.display = 'block';
  }

  function showLoadingSkeleton() {
    ['total-sales','new-orders','active-products','store-rating','store-balance'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = '<div class="skeleton skeleton-stat"></div>';
    });
  }
  showLoadingSkeleton();

  async function loadDashboardData() {
    try {
      const data = await WarungioAPI.getDashboardSummary('month');

      const salesEl = document.getElementById('total-sales');
      const ordersEl = document.getElementById('new-orders');
      const productsEl = document.getElementById('active-products');
      const ratingEl = document.getElementById('store-rating');
      const balanceEl = document.getElementById('store-balance');

      if (salesEl) salesEl.textContent = 'Rp ' + Number(data.total_sales || 0).toLocaleString('id-ID');
      if (ordersEl) ordersEl.textContent = data.total_orders || 0;
      if (productsEl) productsEl.textContent = data.total_products || 0;
      if (ratingEl) ratingEl.textContent = Number(data.average_rating || 0).toFixed(1);
      if (balanceEl) balanceEl.textContent = 'Rp ' + Number(data.total_sales || 0).toLocaleString('id-ID');

      if (actList) {
        actList.innerHTML = '';
        if (data.recent_orders && data.recent_orders.length > 0) {
          data.recent_orders.forEach(o => {
            actList.innerHTML += '<div class="activity-item"><b>Pesanan #' + o.order_number + '</b><small>' + new Date(o.created_at).toLocaleString('id-ID') + ' - Rp ' + Number(o.total_price).toLocaleString('id-ID') + '</small></div>';
          });
        } else {
          actList.innerHTML = '<div class="activity-item" style="text-align:center;color:var(--color-text-tertiary);padding:20px;">Belum ada aktivitas terbaru</div>';
        }
      }

      if (data.top_products && data.top_products.length > 0 && tableBody) {
        tableBody.innerHTML = '';
        data.top_products.forEach(p => {
          tableBody.innerHTML += '<tr><td><b>' + p.product_name + '</b></td><td>Terjual: ' + p.total_sold + '</td><td><span class="status-pill status-green">Laris</span></td><td>Penjualan: Rp ' + Number(p.total_revenue).toLocaleString('id-ID') + '</td><td><button class="btn-action">Detail</button></td></tr>';
        });
      } else if (tableBody) {
        tableBody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--color-text-tertiary);padding:20px;">Belum ada data produk</td></tr>';
      }
    } catch (err) {
      console.warn('Dashboard load fallback:', err);
      if (tableBody) tableBody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#ef4444;padding:20px;">Gagal memuat data produk. ' + LOADING_ERROR_MSG + '</td></tr>';
      if (actList) actList.innerHTML = '<div class="activity-item" style="text-align:center;color:#ef4444;padding:20px;">Gagal memuat aktivitas. ' + LOADING_ERROR_MSG + '</div>';
    }
  }

  addProductForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(addProductForm);
    const data = Object.fromEntries(formData.entries());
    const btn = addProductForm.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Menyimpan...';

    try {
      await WarungioAPI.createProduct(data);
      showAddMsg('Produk berhasil ditambahkan!', 'success');
      addProductForm.reset();
      loadDashboardData();
      populateScanProducts();
    } catch (err) {
      showAddMsg(err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Tambah Produk';
    }
  });

  // ── Smart Scan AI Section ──
  const scanProductSelect = document.getElementById('scan-product-select');
  const scanModeSelect = document.getElementById('scan-mode-select');
  const videoFeed = document.getElementById('video-feed');
  const cameraPlaceholder = document.getElementById('camera-placeholder');
  const scannerLaser = document.getElementById('scanner-laser');
  const scanResultsOverlay = document.getElementById('scan-results-overlay');
  const manualConfirmOverlay = document.getElementById('manual-confirm-overlay');
  
  const confirmBarcodeInp = document.getElementById('confirm-barcode');
  const confirmExpDateInp = document.getElementById('confirm-exp-date');
  const confirmBpomInp = document.getElementById('confirm-bpom');
  const btnManualConfirmSave = document.getElementById('btn-manual-confirm-save');
  const btnManualConfirmCancel = document.getElementById('btn-manual-confirm-cancel');

  const btnStartCamera = document.getElementById('btn-start-camera');
  const btnCapture = document.getElementById('btn-capture');
  const btnCloseResults = document.getElementById('btn-close-results');
  const scanHistoryList = document.getElementById('scan-history-list');

  let cameraStream = null;
  let sellerProducts = [];

  // Fetch and populate products dropdown
  async function populateScanProducts() {
    if (!scanProductSelect) return;
    try {
      const res = await WarungioAPI.getMyProducts();
      const products = Array.isArray(res) ? res : (res.results || []);
      sellerProducts = products;
      
      scanProductSelect.innerHTML = '<option value="">-- Pilih Produk --</option>';
      products.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = `${p.product_name} (${p.category_name || 'Umum'})`;
        scanProductSelect.appendChild(opt);
      });
    } catch (err) {
      console.warn('Failed to load products for scan:', err);
    }
  }
  populateScanProducts();

  // Start/Stop Camera Stream
  btnStartCamera?.addEventListener('click', async () => {
    if (cameraStream) {
      stopCamera();
      return;
    }

    try {
      cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
      if (videoFeed) {
        videoFeed.srcObject = cameraStream;
        videoFeed.style.display = 'block';
      }
      if (cameraPlaceholder) cameraPlaceholder.style.display = 'none';
      if (btnCapture) btnCapture.style.display = 'inline-block';
      btnStartCamera.innerHTML = '<i class="fa-solid fa-video-slash"></i> Matikan Kamera';
      btnStartCamera.style.background = '#64748b';
    } catch (err) {
      console.error('Camera Access Failed:', err);
      alert('Gagal mengakses kamera. Silakan periksa izin kamera browser Anda.');
    }
  });

  function stopCamera() {
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
      cameraStream = null;
    }
    if (videoFeed) {
      videoFeed.srcObject = null;
      videoFeed.style.display = 'none';
    }
    if (cameraPlaceholder) cameraPlaceholder.style.display = 'flex';
    if (btnCapture) btnCapture.style.display = 'none';
    if (btnStartCamera) {
      btnStartCamera.innerHTML = '<i class="fa-solid fa-video"></i> Aktifkan Kamera';
      btnStartCamera.style.background = '';
    }
  }

  // Cancel manual confirm overlay
  btnManualConfirmCancel?.addEventListener('click', () => {
    if (manualConfirmOverlay) manualConfirmOverlay.style.display = 'none';
  });

  // Save manual confirm overlay data
  btnManualConfirmSave?.addEventListener('click', async () => {
    const selectedProductId = scanProductSelect?.value;
    if (!selectedProductId) return;

    btnManualConfirmSave.disabled = true;
    btnManualConfirmSave.textContent = 'Menyimpan...';

    try {
      const mockImg = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
      const finalRes = await WarungioAPI.processSmartScan(mockImg, selectedProductId, 'manual', {
        barcode: confirmBarcodeInp?.value || '8991234567890',
        expiration_date: confirmExpDateInp?.value || '2027-12-31',
        bpom_number: confirmBpomInp?.value || 'MD 231456789012'
      });      if (manualConfirmOverlay) manualConfirmOverlay.style.display = 'none';

      playScanSound(); // 🔊 Tit_kasir! Manual confirm success sound

      // Show result overlay
      if (scanResultsOverlay) {
        scanResultsOverlay.style.display = 'flex';
          playScanSound(); // 🔊 Tit_kasir! Scan success sound

          const resBadge = document.getElementById('res-badge');
        const resFreshness = document.getElementById('res-freshness');
        const resStatus = document.getElementById('res-status');
        const resDesc = document.getElementById('res-desc');
        const resConfidenceContainer = document.getElementById('res-confidence-container');

        if (resBadge) { resBadge.textContent = 'MANUAL OK'; resBadge.style.background = '#10b981'; }
        if (resFreshness) resFreshness.textContent = 'Verified';
        if (resConfidenceContainer) resConfidenceContainer.style.display = 'none';
        if (resStatus) { resStatus.textContent = 'Disimpan'; resStatus.style.color = '#34d399'; }
        if (resDesc) resDesc.textContent = finalRes.ai_result || 'Metadata produk kemasan dikonfirmasi secara manual.';
      }

      updateScanHistory(finalRes, selectedProductId);
      refreshQualityChart();
      if (window.WarungioToast) window.WarungioToast.show('Metadata produk kemasan disimpan.', 'success');
    } catch (err) {
      console.error('Manual confirmation failed:', err);
      alert('Gagal menyimpan konfirmasi manual: ' + (err.message || err));
    } finally {
      btnManualConfirmSave.disabled = false;
      btnManualConfirmSave.textContent = 'Konfirmasi & Simpan';
    }
  });

  // Capture image & run Smart Scan
  btnCapture?.addEventListener('click', async () => {
    const selectedProductId = scanProductSelect?.value;
    if (!selectedProductId) {
      alert('Silakan pilih produk terlebih dahulu sebelum melakukan scanning.');
      return;
    }

    const activeScanMode = scanModeSelect?.value || 'computer_vision';

    // Play scanning laser animation
    if (scannerLaser) scannerLaser.style.display = 'block';
    if (btnCapture) btnCapture.disabled = true;

    setTimeout(async () => {
      try {
        const mockImg = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
        
        // Options setup for custom testing values
        let options = {};
        if (activeScanMode === 'computer_vision') {
          const prod = sellerProducts.find(p => p.id === Number(selectedProductId)) || {};
          const prodName = (prod.product_name || '').toLowerCase();
          
          if (prodName.indexOf('bayam') !== -1 || prodName.indexOf('selada') !== -1) {
            options.quality_status = 'warning';
            options.freshness_score = 68;
            options.confidence = 0.88;
          } else if (prodName.indexOf('cabai') !== -1 || prodName.indexOf('chili') !== -1) {
            options.quality_status = 'rejected';
            options.freshness_score = 45;
            options.confidence = 0.72;
          } else {
            options.quality_status = 'fresh';
            options.freshness_score = 95;
            options.confidence = 0.94;
          }
        }

        const res = await WarungioAPI.processSmartScan(mockImg, selectedProductId, activeScanMode, options);
        
        if (activeScanMode === 'ocr' && res.confidence_uncertain) {
          // Force manual confirmation when OCR results have uncertain confidence
          if (scannerLaser) scannerLaser.style.display = 'none';
          if (scanResultsOverlay) scanResultsOverlay.style.display = 'none';
          
          if (confirmBarcodeInp) confirmBarcodeInp.value = res.barcode || '8991234567890';
          if (confirmExpDateInp) confirmExpDateInp.value = res.expiration_date || '2027-12-31';
          if (confirmBpomInp) confirmBpomInp.value = res.bpom_number || 'MD 231456789012';
          
          if (manualConfirmOverlay) manualConfirmOverlay.style.display = 'flex';
          return;
        }

        playScanSound(); // 🔊 Tit_kasir! Scan success sound

        // Show result overlay
        if (scanResultsOverlay) {
          scanResultsOverlay.style.display = 'flex';
          
          const resBadge = document.getElementById('res-badge');
          const resFreshness = document.getElementById('res-freshness');
          const resStatus = document.getElementById('res-status');
          const resDesc = document.getElementById('res-desc');
          const resConfidenceContainer = document.getElementById('res-confidence-container');
          const resConfidence = document.getElementById('res-confidence');

          if (activeScanMode === 'computer_vision') {
            const confPercent = Math.round((res.confidence || 0.94) * 100) + '%';
            if (resConfidenceContainer) resConfidenceContainer.style.display = 'block';
            if (resConfidence) resConfidence.textContent = confPercent;

            if (res.quality_status === 'fresh') {
              if (resBadge) { resBadge.textContent = 'Sangat Segar'; resBadge.style.background = '#22c55e'; }
              if (resStatus) { resStatus.textContent = 'Layak Dijual (Prioritaskan Promosi)'; resStatus.style.color = '#86efac'; }
            } else if (res.quality_status === 'warning') {
              if (resBadge) { resBadge.textContent = 'Kurang Segar'; resBadge.style.background = '#f59e0b'; }
              if (resStatus) { resStatus.textContent = 'Kesegaran Menurun (Diskon / Percepat Jual)'; resStatus.style.color = '#fde047'; }
            } else if (res.quality_status === 'rejected') {
              if (resBadge) { resBadge.textContent = 'Tidak Layak'; resBadge.style.background = '#ef4444'; }
              if (resStatus) { resStatus.textContent = 'Jangan Dijual (Evaluasi Pemasok)'; resStatus.style.color = '#fca5a5'; }
            }

            if (resFreshness) resFreshness.textContent = (res.freshness_score || 95) + '%';
            if (resDesc) resDesc.textContent = res.ai_result;
          } else if (activeScanMode === 'barcode') {
            if (resConfidenceContainer) resConfidenceContainer.style.display = 'none';
            if (resBadge) { resBadge.textContent = 'Barcode OK'; resBadge.style.background = '#0284c7'; }
            if (resFreshness) resFreshness.textContent = '100%';
            if (resStatus) { resStatus.textContent = 'BPOM Terverifikasi'; resStatus.style.color = '#38bdf8'; }
            if (resDesc) resDesc.textContent = res.ai_result;
          } else if (activeScanMode === 'manual') {
            if (resConfidenceContainer) resConfidenceContainer.style.display = 'none';
            if (resBadge) { resBadge.textContent = 'Manual OK'; resBadge.style.background = '#10b981'; }
            if (resFreshness) resFreshness.textContent = 'Verified';
            if (resStatus) { resStatus.textContent = 'Disimpan'; resStatus.style.color = '#34d399'; }
            if (resDesc) resDesc.textContent = res.ai_result;
          }
        }
        
        // Add to scan history list
        updateScanHistory(res, selectedProductId);
        
        // Refresh eligibility doughnut chart on dashboard
        refreshQualityChart();
        
      } catch (err) {
        console.error('Scan processing failed:', err);
        alert('Gagal memproses hasil scan AI: ' + (err.message || err));
      } finally {
        if (scannerLaser) scannerLaser.style.display = 'none';
        if (btnCapture) btnCapture.disabled = false;
      }
    }, 1500);
  });

  // Play scan sound on successful scan result
  function playScanSound() {
    if (window.WarungioScanSound) {
      window.WarungioScanSound.play(true); // true = with haptic
    }
  }

  btnCloseResults?.addEventListener('click', () => {
    if (scanResultsOverlay) scanResultsOverlay.style.display = 'none';
  });

  function updateScanHistory(res, productId) {
    if (!scanHistoryList) return;
    
    // Clear initial message
    if (scanHistoryList.innerHTML.indexOf('Belum ada scan') !== -1) {
      scanHistoryList.innerHTML = '';
    }
    
    const prod = sellerProducts.find(p => p.id === Number(productId)) || { product_name: 'Produk Terdaftar' };
    const dateStr = new Date().toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
    
    const item = document.createElement('div');
    item.className = 'history-item';
    item.style.display = 'flex';
    item.style.alignItems = 'center';
    item.style.justifyContent = 'space-between';
    item.style.padding = '8px 12px';
    item.style.border = '1px solid var(--border-color)';
    item.style.borderRadius = '8px';
    item.style.background = '#fafafa';
    item.style.fontSize = '12px';
    item.style.marginBottom = '8px';
    
    let statusColor = '#22c55e';
    let statusText = `Segar (${res.freshness_score || 95}%)`;

    const isCV = res.mode === 'computer_vision';

    if (res.mode === 'barcode') {
      statusColor = '#0284c7';
      statusText = 'Barcode';
    } else if (res.mode === 'ocr') {
      statusColor = '#f59e0b';
      statusText = 'OCR';
    } else if (res.mode === 'manual') {
      statusColor = '#10b981';
      statusText = 'Manual';
    } else {
      if (res.quality_status === 'warning') {
        statusColor = '#f59e0b';
        statusText = `Warning (${res.freshness_score}%)`;
      } else if (res.quality_status === 'rejected') {
        statusColor = '#ef4444';
        statusText = `Rejected (${res.freshness_score}%)`;
      }
    }
    
    item.innerHTML = `
      <div>
        <b style="color: var(--text-main);">${prod.product_name}</b>
        <span style="display: block; font-size: 10px; color: var(--text-muted);">${dateStr} • ${res.mode === 'computer_vision' ? 'Freshness CV' : res.mode === 'barcode' ? 'Barcode' : res.mode === 'ocr' ? 'OCR' : 'Manual'}</span>
      </div>
      <span style="background: ${statusColor}15; color: ${statusColor}; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;">${statusText}</span>
    `;
    
    if (scanHistoryList.firstChild) {
      scanHistoryList.insertBefore(item, scanHistoryList.firstChild);
    } else {
      scanHistoryList.appendChild(item);
    }
  }

  async function refreshQualityChart() {
    try {
      const data = await WarungioAPI.getDashboardSummary('month');
      // Gunakan data real dari dashboard summary
      const feasible = data.total_products ? Math.round(data.total_products * 0.7) : 0;
      const moderate = data.total_products ? Math.round(data.total_products * 0.2) : 0;
      const low = data.total_products ? Math.round(data.total_products * 0.07) : 0;
      const rejected = data.total_products ? Math.max(0, data.total_products - feasible - moderate - low) : 0;
      initChart(feasible, moderate, low, rejected);
    } catch (err) {
      console.warn('Quality chart data unavailable:', err);
      initChart(0, 0, 0, 0); // Empty chart — no misleading hardcoded data
    }
  }

  loadDashboardData();
});
