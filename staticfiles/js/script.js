/**
 * Home / Landing page - Warungio (Buyer)
 * Handles storefront grids, geolocation fallback, right sidebar widgets,
 * active order tracking, countdown timer, and quick add-to-cart actions.
 */
document.addEventListener('DOMContentLoaded', async () => {
  // ── Mobile Menu Toggle ──
  const menuToggle = document.getElementById('menuToggle');
  const sidebar = document.querySelector('.sidebar');
  if (menuToggle && sidebar) {
    const overlay = document.createElement('div');
    overlay.className = 'mobile-drawer-overlay';
    document.body.appendChild(overlay);

    const drawer = document.createElement('aside');
    drawer.className = 'mobile-drawer';
    drawer.innerHTML = sidebar.innerHTML;
    document.body.appendChild(drawer);

    function openMobileMenu() {
      drawer.classList.add('open');
      overlay.classList.add('open');
      document.body.style.overflow = 'hidden';
    }

    function closeMobileMenu() {
      drawer.classList.remove('open');
      overlay.classList.remove('open');
      document.body.style.overflow = '';
    }

    menuToggle.addEventListener('click', function() {
      if (drawer.classList.contains('open')) {
        closeMobileMenu();
      } else {
        openMobileMenu();
      }
    });

    overlay.addEventListener('click', closeMobileMenu);
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && drawer.classList.contains('open')) {
        closeMobileMenu();
      }
    });
    drawer.querySelectorAll('a').forEach(function(link) {
      link.addEventListener('click', closeMobileMenu);
    });
  }

  // ── DOM Elements ──
  const productGrid = document.getElementById('produkGrid');
  const storeGrid = document.getElementById('warungGrid');
  const recomendList = document.getElementById('rekomendasiList');
  const activeOrderContent = document.getElementById('pesananAktifContent');
  const timerVal = document.getElementById('timer-val');
  const cartBadge = document.getElementById('cartBadge') || document.querySelector('.icon-badge');

  // ── User Information (Name, Balance, Photo) ──
  async function loadUserProfile() {
    if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) return;
    try {
      const u = await WarungioAPI.checkAuth();
      if (u && u.user) {
        const userNameEl = document.getElementById('userName');
        const userAvatarEl = document.getElementById('userAvatar');
        const userBalanceEl = document.getElementById('userBalance');

        if (userNameEl) userNameEl.textContent = `Hai, ${u.user.full_name || u.user.email}`;
        if (userBalanceEl) userBalanceEl.textContent = 'Rp ' + Number(u.user.wallet_balance ?? 0).toLocaleString('id-ID');
        if (u.user.profile_photo && userAvatarEl) {
          userAvatarEl.src = u.user.profile_photo;
        }
      }
    } catch (err) {
      console.warn('Failed to load user profile:', err);
    }
  }

  // ── Best Deals Countdown Timer ──
  function startCountdown() {
    if (!timerVal) return;
    function updateTimer() {
      const now = new Date();
      const endOfDay = new Date();
      endOfDay.setHours(23, 59, 59, 999);
      
      const diff = endOfDay - now;
      if (diff <= 0) {
        timerVal.textContent = '00:00:00';
        return;
      }
      
      const hrs = String(Math.floor(diff / (1000 * 60 * 60))).padStart(2, '0');
      const mins = String(Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))).padStart(2, '0');
      const secs = String(Math.floor((diff % (1000 * 60)) / 1000)).padStart(2, '0');
      
      timerVal.textContent = `${hrs}:${mins}:${secs}`;
    }
    updateTimer();
    setInterval(updateTimer, 1000);
  }

  // ── Geolocation Fallback Hyperlocal Store Loading ──
  async function loadStores() {
    if (!storeGrid) return;
    
    // Attempt HTML5 Geolocation API
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const lat = position.coords.latitude;
          const lon = position.coords.longitude;
          console.info(`Geolocation found: Lat ${lat}, Lon ${lon}. Loading nearby stores.`);
          await fetchStoresFromAPI({ lat, lon });
        },
        async (error) => {
          console.warn('Geolocation blocked or unavailable. Falling back to recommended stores:', error.message);
          await fetchStoresFromAPI(); // Fallback to fetching all/default recommended stores
        },
        { timeout: 5000 }
      );
    } else {
      console.warn('Geolocation not supported by browser. Falling back to default stores.');
      await fetchStoresFromAPI();
    }
  }

  async function fetchStoresFromAPI(coords = null) {
    try {
      const params = { page: 1, pageSize: 4 };
      if (coords) {
        params.latitude = coords.lat;
        params.longitude = coords.lon;
      }
      
      const data = await WarungioAPI.getStores(params);
      const list = Array.isArray(data) ? data : (data.results || []);
      
      storeGrid.innerHTML = '';
      if (list.length === 0) {
        storeGrid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--muted);padding:20px;">Tidak ada warung tersedia.</div>';
        return;
      }
      
      list.forEach(s => {
        const rating = (s.rating_avg || 4.7).toFixed(1);
        const distance = coords ? '0.8 km' : 'Dekat Anda';
        const deliveryTime = s.is_open ? '10-20 min' : 'Tutup';
        const freeOngkir = 'Gratis Ongkir';
        const logo = s.logo || `/static/images/store-icon-T.png`;
        
        storeGrid.innerHTML += `
          <div class="warung-card" onclick="window.location.href='/stores/${s.id}/'" style="cursor:pointer; background: white; border: 1px solid var(--border); border-radius: 16px; padding: 16px; display: flex; flex-direction: column; gap: 12px; transition: all 0.2s;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <img src="${logo}" alt="${s.store_name}" style="width: 48px; height: 48px; border-radius: 50%; object-fit: cover;">
              <span class="heart-icon" style="color:var(--muted); cursor:pointer;"><i class="fa-regular fa-heart"></i></span>
            </div>
            <div>
              <h4 style="font-size:14px; font-weight:700; color:var(--text); display:flex; align-items:center; gap:4px;">
                ${s.store_name}
                <i class="fa-solid fa-circle-check" style="color:var(--primary); font-size:12px;" title="Terverifikasi"></i>
              </h4>
              <span style="font-size:11px; color:var(--muted);">${s.city || 'Mitra Warungio'}</span>
            </div>
            <div style="display:flex; align-items:center; gap:12px; font-size:12px; color:var(--text); font-weight:600;">
              <span><i class="fa-solid fa-star" style="color:#fbbf24;"></i> ${rating}</span>
              <span style="color:var(--border);">|</span>
              <span>${deliveryTime}</span>
              <span style="color:var(--border);">|</span>
              <span style="color:var(--primary);">${freeOngkir}</span>
            </div>
          </div>
        `;
      });
    } catch (err) {
      console.warn('Failed to load stores:', err);
      storeGrid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--muted);padding:20px;">Gagal memuat warung terdekat.</div>';
    }
  }

  // ── Load Fresh Products & Quick Add to Cart ──
  async function loadFreshProducts() {
    if (!productGrid) return;
    try {
      const data = await WarungioAPI.getProducts({ page: 1, pageSize: 8 });
      const products = Array.isArray(data) ? data : (data.results || []);
      
      productGrid.innerHTML = '';
      if (products.length === 0) {
        productGrid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--muted);padding:20px;">Tidak ada produk tersedia.</div>';
        return;
      }
      
      products.forEach(p => {
        const priceStr = 'Rp ' + Number(p.price).toLocaleString('id-ID');
        const img = p.product_photo || p.image || `/static/images/paket-sayur.png`;
        const rating = (p.rating_avg || 4.8).toFixed(1);
        
        const card = document.createElement('div');
        card.className = 'produk-card';
        card.style.cssText = 'background: white; border: 1px solid var(--border); border-radius: 16px; overflow: hidden; display: flex; flex-direction: column; transition: all 0.2s; position: relative;';
        card.innerHTML = `
          <div style="position:relative; width:100%; height:140px; background:#f8fafc;">
            <img src="${img}" alt="${p.product_name}" style="width:100%; height:100%; object-fit:cover;" />
            <span style="position:absolute; top:8px; left:8px; background:#dcfce7; color:#166534; font-size:10px; font-weight:700; padding:2px 8px; border-radius:4px;">Segar</span>
          </div>
          <div style="padding:12px; display:flex; flex-direction:column; gap:6px; flex:1;">
            <span style="font-size:10px; color:var(--muted); text-transform:uppercase; font-weight:700;">${p.category_name || 'Kategori'}</span>
            <h4 style="font-size:13px; font-weight:700; color:var(--text); line-height:1.4; height:38px; overflow:hidden;">${p.product_name}</h4>
            <span style="font-size:11px; color:var(--muted);">${p.store_name || 'Warung Lokal'}</span>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:auto; pt:6px;">
              <div>
                <strong style="font-size:14px; font-weight:800; color:var(--text);">${priceStr}</strong>
                <span style="font-size:10px; color:var(--muted); block;">/ ${p.unit || 'pcs'}</span>
              </div>
              <button class="btn-add-cart" data-id="${p.id}" style="width: 32px; height: 32px; border-radius: 50%; border: none; background: var(--primary); color: white; display: flex; align-items: center; justify-content: center; font-size: 16px; cursor: pointer; transition: all 0.2s; font-weight:700;">+</button>
            </div>
          </div>
        `;
        productGrid.appendChild(card);

        // Bind quick add-to-cart click handler
        card.querySelector('.btn-add-cart')?.addEventListener('click', (e) => {
          e.stopPropagation();
          handleQuickAddToCart(p.id);
        });
      });
    } catch (err) {
      console.warn('Failed to load fresh products:', err);
    }
  }

  // ── Handle Add to Cart API Call ──
  async function handleQuickAddToCart(productId) {
    if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
      window.location.href = '/auth/login/';
      return;
    }
    
    try {
      await WarungioAPI.addToCart({ product: Number(productId), qty: 1 });
      if (window.WarungioToast) {
        window.WarungioToast.show('Produk berhasil ditambahkan ke keranjang.', 'success');
      } else {
        alert('Produk berhasil ditambahkan ke keranjang!');
      }
      
      // Update cart count badge
      const countRes = await WarungioAPI.getCartCount();
      if (cartBadge && countRes) {
        cartBadge.textContent = countRes.count || 0;
        cartBadge.classList.remove('hidden');
      }
    } catch (err) {
      console.error('Failed to add to cart:', err);
      if (window.WarungioToast) {
        window.WarungioToast.show('Gagal menambahkan ke keranjang: ' + (err.message || err), 'error');
      }
    }
  }

  // ── Load Personal Recommendations ──
  async function loadRecommendations() {
    if (!recomendList) return;
    try {
      const data = await WarungioAPI.getProducts({ is_featured: true, page: 1, pageSize: 3 });
      const products = Array.isArray(data) ? data : (data.results || []);
      
      recomendList.innerHTML = '';
      if (products.length === 0) {
        recomendList.innerHTML = '<div style="text-align:center;color:var(--muted);font-size:11px;padding:10px 0;">Tidak ada rekomendasi.</div>';
        return;
      }
      
      products.forEach(p => {
        const priceStr = 'Rp ' + Number(p.price).toLocaleString('id-ID');
        const img = p.product_photo || p.image || `/static/images/paket-sayur.png`;
        
        const div = document.createElement('div');
        div.className = 'rec-item';
        div.style.cssText = 'display:flex; align-items:center; gap:10px; margin-bottom:12px; background:#fafafa; padding:8px; border-radius:8px; border:1px solid #f1f5f9; font-size:12px;';
        div.innerHTML = `
          <img src="${img}" alt="${p.product_name}" style="width:40px; height:40px; border-radius:6px; object-fit:cover;">
          <div style="flex:1; min-width:0;">
            <b style="color:var(--text); font-weight:700; block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${p.product_name}</b>
            <span style="display:block; font-size:10px; color:var(--muted);">${p.store_name || 'Warung Lokal'}</span>
            <span style="font-weight:700; color:var(--text); display:block; margin-top:2px;">${priceStr}</span>
          </div>
          <button class="btn-add-rec" style="width:24px; height:24px; border-radius:50%; border:none; background:#e2e8f0; color:var(--text); font-size:12px; display:flex; align-items:center; justify-content:center; cursor:pointer;">+</button>
        `;
        recomendList.appendChild(div);
        
        div.querySelector('.btn-add-rec')?.addEventListener('click', () => handleQuickAddToCart(p.id));
      });
    } catch (err) {
      console.warn('Failed to load recommendations:', err);
    }
  }

  // ── Load Active Orders Tracker Status ──
  async function loadActiveOrders() {
    if (!activeOrderContent) return;
    try {
      if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
        activeOrderContent.innerHTML = '<div style="padding:10px;text-align:center;color:var(--muted);font-size:12px;">Silakan login untuk melihat pelacakan.</div>';
        return;
      }

      const res = await WarungioAPI.getOrders({ status: 'on_delivery' });
      const orders = Array.isArray(res) ? res : (res.results || []);
      
      if (orders.length === 0) {
        activeOrderContent.innerHTML = `
          <div style="text-align:center; padding:16px 8px; color:var(--muted); font-size:12px;">
            Tidak ada pengiriman aktif saat ini.
          </div>
        `;
        return;
      }
      
      const o = orders[0];
      let statusLabel = 'Dalam Perjalanan';
      let courierText = o.courier || 'Kurir Instan';
      let driverInfo = '';
      
      try {
        const tracking = await WarungioAPI.getDeliveryTracking(o.id);
        if (tracking) {
          statusLabel = tracking.delivery_status_label || statusLabel;
          courierText = tracking.courier || courierText;
          if (tracking.driver_name) {
            driverInfo = `<div style="margin-top:6px; font-size:11px; color:#475569; background:white; padding:6px; border-radius:6px;">🛵 Driver: ${tracking.driver_name} (${tracking.driver_phone || ''})</div>`;
          }
        }
      } catch (err) {
        console.warn('Could not fetch tracking detail:', err);
      }

      activeOrderContent.innerHTML = `
        <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:10px; padding:12px; font-size:12px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <b style="color:#166534;">#${o.order_number}</b>
            <span style="background:#166534; color:white; font-size:9px; padding:1px 6px; border-radius:4px; font-weight:700;">${statusLabel}</span>
          </div>
          <div style="color:var(--text-muted); font-size:11px; margin-bottom:4px;">Kurir: ${courierText}</div>
          <div style="color:var(--text); font-weight:600;">Total: Rp ${Number(o.total_price).toLocaleString('id-ID')}</div>
          ${driverInfo}
        </div>
      `;
    } catch (err) {
      console.warn('Failed to load active orders tracker:', err);
      activeOrderContent.innerHTML = '<div style="padding:10px;text-align:center;color:var(--muted);font-size:12px;">Gagal memuat pelacakan pesanan.</div>';
    }
  }
  // ── Wallet Top Up midtrans snap integration ──
  function bindWalletTopUp() {
    const btn = document.querySelector('.btn-topup');
    if (!btn) return;

    btn.addEventListener('click', async () => {
      if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
        window.location.href = '/auth/login/';
        return;
      }

      // Create a nice programmatic prompt modal for top-up
      const modal = document.createElement('div');
      modal.style.cssText = 'position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:9999; display:flex; align-items:center; justify-content:center; font-family:var(--font-main);';
      
      const card = document.createElement('div');
      card.style.cssText = 'background:white; padding:24px; border-radius:16px; width:90%; max-width:400px; box-shadow:0 10px 25px rgba(0,0,0,0.1); display:flex; flex-direction:column; gap:16px;';
      
      card.innerHTML = `
        <h3 style="font-size:18px; font-weight:700; color:var(--text); margin-bottom:4px;">Top Up Saldo Dompet</h3>
        <p style="font-size:13px; color:var(--muted); margin:0;">Pilih nominal top-up saldo atau masukkan jumlah kustom (minimal Rp 10.000):</p>
        
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:8px;">
          <button class="nominal-btn" data-val="50000" style="padding:10px; border:1px solid var(--border); border-radius:8px; background:transparent; font-weight:600; color:var(--text); cursor:pointer;">Rp 50.000</button>
          <button class="nominal-btn" data-val="100000" style="padding:10px; border:1px solid var(--border); border-radius:8px; background:transparent; font-weight:600; color:var(--text); cursor:pointer;">Rp 100.000</button>
          <button class="nominal-btn" data-val="200000" style="padding:10px; border:1px solid var(--border); border-radius:8px; background:transparent; font-weight:600; color:var(--text); cursor:pointer;">Rp 200.000</button>
          <button class="nominal-btn" data-val="500000" style="padding:10px; border:1px solid var(--border); border-radius:8px; background:transparent; font-weight:600; color:var(--text); cursor:pointer;">Rp 500.000</button>
        </div>
        
        <div style="display:flex; flex-direction:column; gap:6px;">
          <label style="font-size:12px; font-weight:600; color:var(--text);">Nominal Kustom (Rp)</label>
          <input type="number" id="customAmountInput" placeholder="Masukkan nominal (contoh: 25000)" style="padding:10px; border:1px solid var(--border); border-radius:8px; font-size:14px; width:100%; outline:none;" min="10000" />
        </div>
        
        <div style="display:flex; justify-content:flex-end; gap:12px; margin-top:8px;">
          <button id="cancelTopUpBtn" style="padding:10px 16px; border:none; background:#f1f5f9; border-radius:8px; font-weight:600; color:var(--text-muted); cursor:pointer;">Batal</button>
          <button id="submitTopUpBtn" style="padding:10px 16px; border:none; background:var(--primary); border-radius:8px; font-weight:700; color:white; cursor:pointer;">Top Up Sekarang</button>
        </div>
      `;
      
      modal.appendChild(card);
      document.body.appendChild(modal);
      
      let selectedAmount = null;
      
      // Nominal buttons event
      const nominalBtns = card.querySelectorAll('.nominal-btn');
      const customInput = card.querySelector('#customAmountInput');
      
      nominalBtns.forEach(btnBtn => {
        btnBtn.addEventListener('click', () => {
          nominalBtns.forEach(b => {
            b.style.borderColor = 'var(--border)';
            b.style.background = 'transparent';
            b.style.color = 'var(--text)';
          });
          btnBtn.style.borderColor = 'var(--primary)';
          btnBtn.style.background = 'var(--primary-soft)';
          btnBtn.style.color = 'var(--primary-dark)';
          selectedAmount = Number(btnBtn.dataset.val);
          customInput.value = ''; // clear custom input
        });
      });
      
      customInput.addEventListener('input', () => {
        // Clear nominal selections
        nominalBtns.forEach(b => {
          b.style.borderColor = 'var(--border)';
          b.style.background = 'transparent';
          b.style.color = 'var(--text)';
        });
        selectedAmount = null;
      });
      
      // Cancel btn
      card.querySelector('#cancelTopUpBtn').addEventListener('click', () => {
        modal.remove();
      });
      
      // Submit btn
      const submitBtn = card.querySelector('#submitTopUpBtn');
      submitBtn.addEventListener('click', async () => {
        let finalAmount = selectedAmount;
        if (!finalAmount) {
          finalAmount = Number(customInput.value.trim());
        }
        
        if (!finalAmount || isNaN(finalAmount) || finalAmount < 10000) {
          alert('Nominal top-up minimal adalah Rp 10.000.');
          return;
        }
        
        submitBtn.disabled = true;
        submitBtn.textContent = 'Memproses...';
        
        try {
          // Fetch midtrans client key
          let midtransClientKey = 'SB-Mid-client-wZQ4B2RbLEEIlCq9';
          try {
            const config = await WarungioAPI.getPaymentConfig();
            if (config && config.client_key) {
              midtransClientKey = config.client_key;
            }
          } catch (e) {
            console.warn('Payment config fetch failed, using fallback key:', e);
          }
          
          // Load Midtrans Snap JS dynamically
          if (!window.snap || !window.snap.pay) {
            await new Promise((resolve, reject) => {
              const script = document.createElement('script');
              script.src = 'https://app.sandbox.midtrans.com/snap/snap.js';
              script.setAttribute('data-client-key', midtransClientKey);
              script.onload = resolve;
              script.onerror = () => reject(new Error('Gagal memuat Midtrans Snap.'));
              document.head.appendChild(script);
            });
          }
          
          // Call topup API
          const snapData = await WarungioAPI.topUpWallet(finalAmount);
          if (!snapData.token) {
            throw new Error('Gagal mendapatkan token pembayaran dari server.');
          }
          
          modal.remove(); // Remove input modal before opening Snap popup
          
          window.snap.pay(snapData.token, {
            onSuccess: function (result) {
              if (window.WarungioToast) {
                window.WarungioToast.show('Pembayaran berhasil! Saldo sedang diperbarui.', 'success');
              } else {
                alert('Top-up berhasil!');
              }
              // Refresh profile to update balance display
              setTimeout(loadUserProfile, 1000);
            },
            onPending: function (result) {
              if (window.WarungioToast) {
                window.WarungioToast.show('Pembayaran pending. Silakan selesaikan pembayaran.', 'warning');
              } else {
                alert('Pembayaran tertunda.');
              }
            },
            onError: function (result) {
              alert('Pembayaran gagal: ' + (result.status_message || 'Terjadi kesalahan.'));
            },
            onClose: function () {
              // Reload user profile in case transaction went through
              loadUserProfile();
            }
          });
        } catch (err) {
          console.error(err);
          alert(err.message || 'Gagal memulai pembayaran.');
          submitBtn.disabled = false;
          submitBtn.textContent = 'Top Up Sekarang';
        }
      });
    });
  }

  // ── Initialize All Components ──
  bindWalletTopUp();
  await loadUserProfile();
  startCountdown();
  await Promise.all([loadStores(), loadFreshProducts(), loadRecommendations(), loadActiveOrders()]);

  // Load initial cart count
  if (window.WarungioAuth && window.WarungioAuth.isAuthenticated()) {
    try {
      const countRes = await WarungioAPI.getCartCount();
      if (cartBadge && countRes) {
        cartBadge.textContent = countRes.count || 0;
        cartBadge.classList.remove('hidden');
      }
    } catch (e) {}
  }
});
