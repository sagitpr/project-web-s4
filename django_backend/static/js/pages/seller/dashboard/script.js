/**
 * Seller Dashboard - Warungio
 * Connected to Django analytics API and product management.
 */
document.addEventListener('DOMContentLoaded', () => {
  const LOADING_ERROR_MSG = 'Gagal memuat data. Silakan refresh halaman.';

  if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
    window.location.href = '/?next=' + encodeURIComponent(window.location.pathname);
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

  // ── Load store profile (shop name, ID, wallet balance) ──
  async function loadStoreProfile() {
    try {
      const store = await WarungioAPI.getMyStore();
      const shopNameEl = document.getElementById('shopName');
      const shopIdEl = document.getElementById('shopId');
      const logoEl = document.getElementById('headerStoreLogo');
      if (shopNameEl && store) {
        shopNameEl.textContent = store.store_name || 'Warung';
      }
      if (shopIdEl && store) {
        shopIdEl.textContent = 'ID: ' + (store.slug ? store.slug.toUpperCase() : 'WRG' + (store.id || ''));
      }
      if (logoEl && store && store.store_logo) {
        logoEl.src = store.store_logo;
        logoEl.style.display = 'inline-block';
      }

      // Load wallet balance separately
      try {
        const wallet = await WarungioAPI.getWalletBalance();
        const balanceEl = document.getElementById('store-balance');
        if (balanceEl && wallet) {
          balanceEl.textContent = 'Rp ' + Number(wallet.balance || 0).toLocaleString('id-ID');
        }
      } catch (e) {
        // Wallet API unavailable — keep skeleton
      }
    } catch (e) {
      console.warn('Store profile load failed:', e);
    }
  }

  async function loadDashboardData() {
    try {
      const data = await WarungioAPI.getDashboardSummary('month');

      const salesEl = document.getElementById('total-sales');
      const ordersEl = document.getElementById('new-orders');
      const productsEl = document.getElementById('active-products');
      const ratingEl = document.getElementById('store-rating');

      if (salesEl) salesEl.textContent = 'Rp ' + Number(data.total_sales || 0).toLocaleString('id-ID');
      if (ordersEl) ordersEl.textContent = data.total_orders || 0;
      if (productsEl) productsEl.textContent = data.total_products || 0;
      if (ratingEl) ratingEl.textContent = Number(data.average_rating || 0).toFixed(1);

      // ── Trends: compare current period vs previous period ──
      const deltaSales = Number(data.sales_trend_percent || 0);
      const deltaOrders = Number(data.order_trend_percent || 0);
      renderTrend('sales-trend', deltaSales, 'dari bulan lalu');
      renderTrend('orders-trend', deltaOrders, 'dari bulan lalu');

      const productsTrendEl = document.getElementById('products-trend');
      if (productsTrendEl) {
        productsTrendEl.textContent = data.total_products ? data.total_products + ' produk aktif' : 'Belum ada produk';
        productsTrendEl.className = 'stat-trend';
      }

      const reviewCount = data.total_reviews || data.review_count || 0;
      const ratingTrendEl = document.getElementById('rating-trend');
      if (ratingTrendEl) {
        ratingTrendEl.textContent = '(' + Number(reviewCount).toLocaleString('id-ID') + ' ulasan)';
        ratingTrendEl.className = 'stat-trend';
      }

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
        const badgeEl = document.getElementById('actionBadge');
        if (badgeEl) badgeEl.textContent = data.top_products.length;
      } else if (tableBody) {
        tableBody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--color-text-tertiary);padding:20px;">Belum ada data produk</td></tr>';
        const badgeEl = document.getElementById('actionBadge');
        if (badgeEl) badgeEl.textContent = '0';
      }

      // ── Quality chart from real quality data ──
      refreshQualityChartFromData(data);
    } catch (err) {
      console.warn('Dashboard load fallback:', err);
      if (tableBody) tableBody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#ef4444;padding:20px;">Gagal memuat data produk. ' + LOADING_ERROR_MSG + '</td></tr>';
      if (actList) actList.innerHTML = '<div class="activity-item" style="text-align:center;color:#ef4444;padding:20px;">Gagal memuat aktivitas. ' + LOADING_ERROR_MSG + '</div>';
    }
  }

  function renderTrend(elId, pctChange, suffix) {
    const el = document.getElementById(elId);
    if (!el) return;
    if (pctChange === 0 || isNaN(pctChange)) {
      el.textContent = 'Belum ada data';
      el.className = 'stat-trend';
      return;
    }
    const isUp = pctChange > 0;
    const icon = isUp ? '<i class="fa-solid fa-arrow-up"></i>' : '<i class="fa-solid fa-arrow-down"></i>';
    el.innerHTML = icon + ' ' + Math.abs(pctChange).toFixed(1) + '% ' + suffix;
    el.className = 'stat-trend ' + (isUp ? 'up' : 'down');
  }

  // ── Load categories & populate dropdown ──
  async function loadCategories() {
    try {
      var data = await WarungioAPI.getCategories();
      var cats = Array.isArray(data) ? data : (data.results || []);
      var catSelect = addProductForm ? addProductForm.querySelector('[name="category"]') : null;
      if (catSelect && catSelect.tagName === 'SELECT') {
        catSelect.innerHTML = '<option value="">Pilih kategori</option>';
        cats.forEach(function(c) {
          catSelect.innerHTML += '<option value="' + c.id + '">' + (c.category_name || c.name) + '</option>';
        });
      }
    } catch (err) {
      console.warn('Load categories fallback:', err);
    }
  }

  addProductForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = addProductForm.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Menyimpan...';

    try {
      var catId = parseInt(addProductForm.querySelector('[name="category"]')?.value) || null;
      var data = {
        product_name: addProductForm.querySelector('[name="product_name"]')?.value || '',
        description: addProductForm.querySelector('[name="description"]')?.value || '',
        price: parseFloat(addProductForm.querySelector('[name="price"]')?.value || 0),
        stock: parseInt(addProductForm.querySelector('[name="stock"]')?.value) || 0,
        category: catId,
        unit: addProductForm.querySelector('[name="unit"]')?.value || 'kg',
        is_active: true,
      };
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

  // Initialize real AI scan engines on page load (no blocking)
  if (window.WarungioAIScan) {
    setTimeout(function() {
      WarungioAIScan.initTF().then(function(ready) {
        if (ready) console.info('AI Scan: MobileNet ready');
      });
      WarungioAIScan.initTesseract().then(function(ready) {
        if (ready) console.info('AI Scan: Tesseract.js ready');
      });
    }, 2000); // Defer init to avoid blocking page render
  }

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
    btnManualConfirmSave.textContent = 'Menyimpan...';    try {
      const finalRes = await WarungioAPI.processSmartScan(null, selectedProductId, 'manual', {
        barcode: confirmBarcodeInp?.value || '8991234567890',
        expiration_date: confirmExpDateInp?.value || '2027-12-31',
        bpom_number: confirmBpomInp?.value || 'MD 231456789012'
      });

      if (manualConfirmOverlay) manualConfirmOverlay.style.display = 'none';

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
        let options = {};
        
        // ── Real AI Scan: Use Tesseract.js OCR or MobileNet ──
        if (activeScanMode === 'computer_vision' && window.WarungioAIScan && videoFeed) {
          // Run real MobileNet classification on video frame
          var aiResult = await WarungioAIScan.classifyImage(videoFeed);
          if (aiResult) {
            options.quality_status = aiResult.quality_status;
            options.freshness_score = aiResult.freshness_score;
            options.confidence = aiResult.confidence;
            options.ai_result = 'MobileNet: ' + aiResult.label + ' (confidence: ' + Math.round(aiResult.confidence * 100) + '%)';
          } else {
            // Fallback if AI fails
            options.quality_status = 'fresh';
            options.freshness_score = 85;
            options.confidence = 0.5;
            options.ai_result = 'AI scan unavailable — using estimated quality';
          }
        } else if (activeScanMode === 'ocr' && window.WarungioAIScan && videoFeed) {
          // Run real Tesseract.js OCR on video frame
          var ocrResult = await WarungioAIScan.runOCR(videoFeed);
          if (ocrResult) {
            options.quality_status = ocrResult.confidence > 60 ? 'fresh' : 'warning';
            options.freshness_score = Math.round(ocrResult.confidence);
            options.confidence = ocrResult.confidence / 100;
            options.barcode = ocrResult.barcode;
            options.expiration_date = ocrResult.expiration_date;
            options.bpom_number = ocrResult.bpom_number;
            options.ai_result = 'OCR Text: ' + (ocrResult.text || '').substring(0, 200);
            
            if (ocrResult.confidence_uncertain) {
              // Force manual confirmation when OCR results have uncertain confidence
              if (scannerLaser) scannerLaser.style.display = 'none';
              if (scanResultsOverlay) scanResultsOverlay.style.display = 'none';
              
              if (confirmBarcodeInp) confirmBarcodeInp.value = ocrResult.barcode || '8991234567890';
              if (confirmExpDateInp) confirmExpDateInp.value = ocrResult.expiration_date || '2027-12-31';
              if (confirmBpomInp) confirmBpomInp.value = ocrResult.bpom_number || 'MD 231456789012';
              
              if (manualConfirmOverlay) manualConfirmOverlay.style.display = 'flex';
              return;
            }
          } else {
            options.quality_status = 'warning';
            options.freshness_score = 50;
            options.confidence = 0.3;
            options.ai_result = 'OCR tidak dapat membaca teks — coba mode lain';
          }
        } else {
          // Barcode / Manual mode — use API
        }

        const res = await WarungioAPI.processSmartScan(null, selectedProductId, activeScanMode, options);
        // If AI result was set, override the API response
        if (options.ai_result && res) res.ai_result = options.ai_result;
        
        if (activeScanMode === 'ocr' && (options.confidence || 0) < 0.6 && options.barcode) {
          // Fallback existing OCR low confidence handling
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

  function refreshQualityChartFromData(data) {
    const qualityStats = data.quality_summary || {};
    const feasible = qualityStats.fresh || 0;
    const moderate = qualityStats.normal || 0;
    const low = qualityStats.warning || 0;
    const rejected = qualityStats.rejected || 0;
    const total = feasible + moderate + low + rejected || 1;

    initChart(feasible, moderate, low, rejected);

    // Update labels with real counts
    document.getElementById('qualityFeasible').textContent = feasible;
    document.getElementById('qualityModerate').textContent = moderate;
    document.getElementById('qualityLow').textContent = low;
    document.getElementById('qualityRejected').textContent = rejected;

    // Update progress bars
    document.getElementById('qualityBarFeasible').style.width = (feasible / total * 100) + '%';
    document.getElementById('qualityBarModerate').style.width = (moderate / total * 100) + '%';
    document.getElementById('qualityBarLow').style.width = (low / total * 100) + '%';
    document.getElementById('qualityBarRejected').style.width = (rejected / total * 100) + '%';

    // Center percentage
    const pctEl = document.getElementById('eligibilityPct');
    if (pctEl) {
      const totalProducts = feasible + moderate + low + rejected;
      const healthyPct = totalProducts > 0 ? Math.round((feasible / totalProducts) * 100) : 0;
      pctEl.textContent = healthyPct + '%';
    }
  }

  // ── POS Scanner / Kasir Offline ──
  const posProductSelect = document.getElementById('pos-product-select');
  const posCart = document.getElementById('posCart');
  const posTotal = document.getElementById('posTotal');
  const posCheckoutBtn = document.getElementById('posCheckoutBtn');
  let posCartItems = [];

  async function loadPosProducts() {
    if (!posProductSelect) return;
    try {
      const res = await WarungioAPI.getMyProducts();
      const products = Array.isArray(res) ? res : (res.results || []);
      posProductSelect.innerHTML = '<option value="">-- Cari & Pilih Produk --</option>';
      products.forEach(function(p) {
        if (!p) return;
        var opt = document.createElement('option');
        opt.value = p.id;
        var name = p.product_name || 'Produk';
        var price = Number(p.price || 0);
        opt.setAttribute('data-price', price);
        opt.setAttribute('data-stock', Number(p.stock || 0));
        opt.textContent = name + ' - Rp ' + price.toLocaleString('id-ID');
        posProductSelect.appendChild(opt);
      });
    } catch (err) {
      console.warn('Failed to load products for POS:', err);
    }
  }
  loadPosProducts();

  posProductSelect?.addEventListener('change', function() {
    var selectedId = this.value;
    if (!selectedId) return;
    var selectedOpt = this.options[this.selectedIndex];
    var price = parseFloat(selectedOpt.getAttribute('data-price') || 0);
    var stock = parseInt(selectedOpt.getAttribute('data-stock') || 0);
    var name = selectedOpt.textContent.split(' - ')[0];

    // Check if already in cart
    var existing = posCartItems.find(function(i) { return i.id === parseInt(selectedId); });
    if (existing) {
      existing.qty += 1;
    } else {
      posCartItems.push({ id: parseInt(selectedId), name: name, price: price, qty: 1, stock: stock });
    }
    renderPosCart();
    this.value = '';
  });

  function renderPosCart() {
    if (!posCart) return;
    if (posCartItems.length === 0) {
      posCart.innerHTML = '<div style="text-align:center;color:#94a3b8;font-size:13px;padding:20px;"><i class="fa-solid fa-cart-shopping" style="font-size:24px;display:block;margin-bottom:8px;"></i> Keranjang masih kosong. Pilih produk di atas.</div>';
      if (posCheckoutBtn) posCheckoutBtn.disabled = true;
      if (posTotal) posTotal.textContent = 'Rp 0';
      return;
    }

    var html = '<div style="display:flex;flex-direction:column;gap:8px;">';
    var total = 0;
    posCartItems.forEach(function(item, idx) {
      var subtotal = item.price * item.qty;
      total += subtotal;
      html += '<div style="display:flex;align-items:center;justify-content:space-between;padding:8px;background:#f8fafc;border-radius:8px;">';
      html += '<div style="flex:1;"><b>' + item.name + '</b><br><small style="color:#64748b;">Rp ' + item.price.toLocaleString('id-ID') + ' x ' + item.qty + '</small></div>';
      html += '<div style="display:flex;align-items:center;gap:6px;">';
      html += '<button onclick="window.posDecreaseQty(' + idx + ')" style="width:28px;height:28px;border:1px solid #e2e8f0;border-radius:6px;background:#fff;cursor:pointer;font-size:16px;font-weight:700;line-height:1;">&minus;</button>';
      html += '<span style="font-weight:600;min-width:24px;text-align:center;">' + item.qty + '</span>';
      html += '<button onclick="window.posIncreaseQty(' + idx + ')" style="width:28px;height:28px;border:1px solid #e2e8f0;border-radius:6px;background:#fff;cursor:pointer;font-size:16px;font-weight:700;line-height:1;">+</button>';
      html += '<span style="font-weight:700;color:#16a34a;min-width:80px;text-align:right;">Rp ' + subtotal.toLocaleString('id-ID') + '</span>';
      html += '<button onclick="window.posRemoveItem(' + idx + ')" style="width:28px;height:28px;border:none;border-radius:6px;background:#fee2e2;color:#dc2626;cursor:pointer;font-size:14px;line-height:1;">&times;</button>';
      html += '</div></div>';
    });
    html += '</div>';
    posCart.innerHTML = html;

    if (posTotal) posTotal.textContent = 'Rp ' + total.toLocaleString('id-ID');
    window.posCartTotal = total;
    if (posCheckoutBtn) posCheckoutBtn.disabled = false;
  }

  window.posDecreaseQty = function(idx) {
    if (idx < 0 || idx >= posCartItems.length) return;
    if (posCartItems[idx].qty > 1) {
      posCartItems[idx].qty -= 1;
    } else {
      posCartItems.splice(idx, 1);
    }
    renderPosCart();
  };

  window.posIncreaseQty = function(idx) {
    if (idx < 0 || idx >= posCartItems.length) return;
    var maxStock = posCartItems[idx].stock;
    if (posCartItems[idx].qty < maxStock) {
      posCartItems[idx].qty += 1;
    } else {
      if (window.WarungioToast) {
        window.WarungioToast.show('Stok tidak mencukupi (' + maxStock + ')', 'warning');
      }
    }
    renderPosCart();
  };

  window.posRemoveItem = function(idx) {
    if (idx < 0 || idx >= posCartItems.length) return;
    posCartItems.splice(idx, 1);
    renderPosCart();
  };

  posCheckoutBtn?.addEventListener('click', async function() {
    if (posCartItems.length === 0) return;
    var total = window.posCartTotal || 0;
    var confirmed = confirm('Proses transaksi POS offline sebesar Rp ' + total.toLocaleString('id-ID') + '?');
    if (!confirmed) return;

    this.disabled = true;
    this.innerHTML = 'Memproses...';

    try {
      // Create offline order
      var orderItems = posCartItems.map(function(item) {
        return { product: item.id, quantity: item.qty };
      });
      var orderData = {
        items: orderItems,
        payment_method: 'cash',
        notes: 'POS Offline - Kasir'
      };
      var result = await WarungioAPI.createOrder(orderData);
      
      if (window.WarungioToast) {
        window.WarungioToast.show('Transaksi berhasil! Total: Rp ' + total.toLocaleString('id-ID'), 'success');
      }

      // Clear cart
      posCartItems = [];
      renderPosCart();
      loadDashboardData(); // Refresh stats
      loadPosProducts(); // Refresh stock
    } catch (err) {
      console.error('POS checkout failed:', err);
      if (window.WarungioToast) {
        window.WarungioToast.show('Gagal memproses transaksi: ' + (err.message || 'Coba lagi'), 'error');
      }
    } finally {
      this.disabled = false;
      this.innerHTML = '<i class="fa-solid fa-check"></i> Proses Pembayaran';
    }
  });

  // ── Expired Date Monitoring ──
  async function loadExpiringProducts() {
    var listEl = document.getElementById('expiringProductList');
    var badgeEl = document.getElementById('expiringBadge');
    if (!listEl) return;

    var now = new Date();
    var sevenDaysLater = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
    var aiRecommendations = [];

    // Try to load AI-powered recommendations first
    try {
      var csrf = getCSRFToken();
      var resp = await fetch('/api/inventory/expired-reminder/dashboard/', {
        method: 'GET',
        headers: { 'X-CSRFToken': csrf },
      });
      if (resp.ok) {
        var aiData = await resp.json();
        if (aiData && aiData.recommendations) {
          aiRecommendations = aiData.recommendations;
          // Update badge with AI count
          if (badgeEl) {
            badgeEl.textContent = aiData.total_expiring || aiRecommendations.length || 0;
            badgeEl.style.display = (aiData.total_expiring > 0) ? 'inline-flex' : 'none';
          }
        }
      }
    } catch (e) {
      console.warn('AI expiry dashboard unavailable, falling back:', e.message);
    }

    try {
      var res = await WarungioAPI.getMyProducts();
      var products = Array.isArray(res) ? res : (res.results || []);
      
      var expiringProducts = products.filter(function(p) {
        if (!p.expired_date) return false;
        var expDate = new Date(p.expired_date);
        return expDate >= now && expDate <= sevenDaysLater;
      });

      if (badgeEl && aiRecommendations.length === 0) {
        badgeEl.textContent = expiringProducts.length;
        badgeEl.style.display = expiringProducts.length > 0 ? 'inline-flex' : 'none';
      }

      // Combine AI recommendations with product data
      var displayHtml = '';

      // Show AI-powered discount recommendations with urgency badges
      if (aiRecommendations.length > 0) {
        displayHtml += '<div style="margin-bottom:12px;"><h4 style="font-size:13px;font-weight:700;color:#0f172a;margin:0 0 8px;"><i class="fa-solid fa-robot"></i> Rekomendasi AI Diskon</h4>';
        aiRecommendations.slice(0, 5).forEach(function(rec) {
          var urgencyColor = rec.urgency === 'critical' ? '#ef4444' : rec.urgency === 'high' ? '#f59e0b' : '#0891b2';
          var discountBadge = rec.discount_pct ? rec.discount_pct + '% OFF' : 'Promo';
          displayHtml += '<div style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px;margin-bottom:6px;background:#f8fafc;border-radius:8px;border-left:3px solid ' + urgencyColor + ';">';
          displayHtml += '<div><b style="font-size:13px;">' + escapeHtml(rec.product_name || 'Produk') + '</b><br><small style="color:#64748b;">' + escapeHtml(rec.message || '') + '</small></div>';
          displayHtml += '<div style="text-align:right;"><span style="background:' + urgencyColor + '15;color:' + urgencyColor + ';padding:4px 8px;border-radius:6px;font-weight:700;font-size:11px;">' + discountBadge + '</span>';
          if (rec.suggested_price) {
            displayHtml += '<br><small style="color:#16a34a;font-weight:600;">Rp ' + Number(rec.suggested_price).toLocaleString('id-ID') + '</small>';
          }
          displayHtml += '</div></div>';
        });
        displayHtml += '</div>';
      }

      // Then show basic expiring products
      if (expiringProducts.length > 0) {
        displayHtml += '<h4 style="font-size:13px;font-weight:700;color:#0f172a;margin:0 0 8px;">Produk Hampir Kedaluwarsa</h4>';
        expiringProducts.forEach(function(p) {
          var expDate = new Date(p.expired_date);
          var daysLeft = Math.ceil((expDate - now) / (1000 * 60 * 60 * 24));
          var statusColor = daysLeft <= 2 ? '#ef4444' : '#f59e0b';
          var recommend = daysLeft <= 2 ? 'Diskon besar!' : 'Beri promosi';
          displayHtml += '<div style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px;margin-bottom:6px;background:#f8fafc;border-radius:8px;">';
          displayHtml += '<div><b>' + escapeHtml(p.product_name || 'Produk') + '</b><br><small style="color:#64748b;">Kedaluwarsa: ' + expDate.toLocaleDateString('id-ID') + ' (' + daysLeft + ' hari lagi)</small></div>';
          displayHtml += '<span style="background:' + statusColor + '15;color:' + statusColor + ';padding:4px 10px;border-radius:6px;font-weight:600;font-size:12px;">' + recommend + '</span>';
          displayHtml += '</div>';
        });
      }

      // If nothing found at all
      if (!displayHtml) {
        displayHtml = '<div style="text-align:center;color:#94a3b8;font-size:13px;padding:20px;"><i class="fa-solid fa-check-circle" style="font-size:24px;display:block;margin-bottom:8px;color:#22c55e;"></i> Tidak ada produk yang hampir kedaluwarsa.</div>';
      }

      listEl.innerHTML = displayHtml;
    } catch (err) {
      console.warn('Failed to load expiring products:', err);
    }
  }

  function escapeHtml(s) {
    if (!s) return '';
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/'/g,'&#39;').replace(/"/g,'&#34;');
  }

  function getCSRFToken() {
    var name = 'csrftoken';
    var match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? match[2] : '';
  }

  // ── Chat Unread Badge ──
  async function updateChatUnreadBadge() {
    try {
      var res = await WarungioAPI.getChatUnreadCount();
      var count = res?.unread_count || res?.count || 0;
    } catch (e) {
      // Fallback: count from conversations
      try {
        var conv = await WarungioAPI.getConversations();
        var list = Array.isArray(conv) ? conv : (conv.results || []);
        var count = 0;
        list.forEach(function(c) { count += (c.unread_count || 0); });
      } catch (e2) { return; }
    }
    var badge = document.getElementById('chatUnreadBadge');
    if (badge) {
      badge.textContent = count;
      badge.style.display = count > 0 ? 'inline-flex' : 'none';
    }
  }

  // ── WebSocket Real-time Listeners ──
  function initRealtimeSellerListeners() {
    var _wsRetries = 0;
    var _wsMaxRetries = 10;

    function trySetup() {
      if (_wsRetries >= _wsMaxRetries) return;
      if (typeof WarungioWS === 'undefined' || typeof WarungioWS.on !== 'function') {
        _wsRetries++;
        setTimeout(trySetup, 1000);
        return;
      }

      // New order notification (payment confirmed)
      WarungioWS.on('delivery_update', function (data) {
        if (!data.order_id) return;
        // Refresh dashboard stats to reflect new order
        loadDashboardData();
        updateChatUnreadBadge();
        // Show toast notification
        var msg = data.message || 'Ada update pesanan baru!';
        if (window.WarungioToast) {
          window.WarungioToast.show(msg, 'success');
        }
        // Play voice notification if available
        if (window.WarungioVoiceNotification && data.delivery_status) {
          window.WarungioVoiceNotification.notifyNewOrder(data);
        }
      });

      // Order/payment update — refresh dashboard
      WarungioWS.on('order_update', function (data) {
        if (data.status === 'paid' || data.status === 'cancelled') {
          loadDashboardData();
          loadExpiringProducts();
        }
      });

      // Payment update — refresh balance
      WarungioWS.on('payment_update', function (data) {
        if (data.status === 'settlement' || data.status === 'paid') {
          loadDashboardData();
        }
      });

      // New notification — refresh badge
      WarungioWS.on('notification', function () {
        updateChatUnreadBadge();
      });
    }
    trySetup();
  }

  // ── Restock Prediction Widget ──
  async function loadRestockWidget() {
    var lowCountEl = document.getElementById('restockWidgetLowCount');
    var outCountEl = document.getElementById('restockWidgetOutCount');
    var reorderCountEl = document.getElementById('restockWidgetReorderCount');
    var listEl = document.getElementById('restockWidgetList');
    if (!listEl) return;

    try {
      // Load low stock + reorder suggestions in parallel
      var [lowStockData, reorderData] = await Promise.all([
        WarungioAPI.getLowStockProducts({ threshold: 5 }),
        WarungioAPI.getReorderSuggestions().catch(function () { return null; }),
      ]);

      var lowCount = lowStockData?.total_low_stock || 0;
      var outCount = lowStockData?.total_out_of_stock || 0;
      var reorderCount = reorderData?.urgent_reorders?.length || reorderData?.total_suggestions || (lowCount + outCount);

      if (lowCountEl) lowCountEl.textContent = lowCount;
      if (outCountEl) outCountEl.textContent = outCount;
      if (reorderCountEl) reorderCountEl.textContent = reorderCount;

      // Build product list
      var html = '';
      var products = lowStockData?.low_stock || [];
      var outOfStock = lowStockData?.out_of_stock || [];

      // Show low stock items
      if (products.length > 0) {
        html += '<h4 style="font-size:13px;font-weight:700;color:#f59e0b;margin:0 0 8px;"><i class="fa-solid fa-exclamation-triangle"></i> Stok Menipis</h4>';
        products.slice(0, 5).forEach(function (p) {
          var pct = Math.min(100, Math.round((p.stock / 20) * 100));
          var barColor = p.stock <= 2 ? '#ef4444' : '#f59e0b';
          html += '<div style="display:flex;align-items:center;justify-content:space-between;padding:6px 10px;margin-bottom:4px;background:#f8fafc;border-radius:8px;">' +
            '<div style="flex:1;"><b style="font-size:13px;">' + escapeHtml(p.product_name || 'Produk') + '</b>' +
            '<div style="margin-top:4px;background:#e2e8f0;height:4px;border-radius:2px;max-width:120px;"><div style="width:' + pct + '%;height:4px;background:' + barColor + ';border-radius:2px;"></div></div></div>' +
            '<div style="text-align:right;"><span style="font-weight:700;font-size:13px;color:' + barColor + ';">' + p.stock + '</span><br><small style="font-size:10px;color:#94a3b8;">' + escapeHtml(p.unit || 'pcs') + '</small></div></div>';
        });
      }

      // Show out of stock items
      if (outOfStock.length > 0) {
        html += '<h4 style="font-size:13px;font-weight:700;color:#ef4444;margin:8px 0 8px;"><i class="fa-solid fa-circle-exclamation"></i> Stok Habis</h4>';
        outOfStock.slice(0, 3).forEach(function (p) {
          html += '<div style="display:flex;align-items:center;justify-content:space-between;padding:6px 10px;margin-bottom:4px;background:#fef2f2;border-radius:8px;">' +
            '<div><b style="font-size:13px;color:#dc2626;">' + escapeHtml(p.product_name || 'Produk') + '</b><br><small style="color:#ef4444;">Perlu restok segera</small></div>' +
            '<span style="background:#ef4444;color:#fff;padding:2px 8px;border-radius:4px;font-weight:700;font-size:11px;">0</span></div>';
        });
      }

      if (!html) {
        html = '<div style="text-align:center;color:#94a3b8;font-size:13px;padding:16px;"><i class="fa-solid fa-check-circle" style="font-size:20px;display:block;margin-bottom:6px;color:#22c55e;"></i> Semua produk dalam stok cukup.</div>';
      }

      listEl.innerHTML = html;
    } catch (err) {
      console.warn('Restock widget load failed:', err);
      if (listEl) {
        listEl.innerHTML = '<div style="text-align:center;color:#94a3b8;font-size:13px;padding:16px;">Gagal memuat data prediksi restok.</div>';
      }
    }
  }

  // ── Init everything ──
  loadStoreProfile();
  loadDashboardData();
  loadExpiringProducts();
  loadRestockWidget();
  updateChatUnreadBadge();
  initRealtimeSellerListeners();

  // Periodic refresh for live data (degraded fallback when WS disconnected)
  setInterval(function() {
    updateChatUnreadBadge();
    loadExpiringProducts();
  }, 60000); // every 60 seconds (was 30s, reduced since WS is primary)
});
