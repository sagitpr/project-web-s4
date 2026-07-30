/**
 * Home / Landing page - Warungio (Buyer)
 * Redesigned with premium hyperlocal marketplace interfaces.
 * Handles storefront grids, geolocation fallback, right sidebar widgets,
 * active order tracking, countdown timer, and quick add-to-cart actions.
 */
document.addEventListener('DOMContentLoaded', async () => {
  // ── Mobile Menu Drawer Toggle ──
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

  // ── Dynamic Authentication States ──
  function toggleAuthStates() {
    const isAuthenticated = window.WarungioAuth && window.WarungioAuth.isAuthenticated();
    const authHeader = document.getElementById('authHeaderActions');
    const guestHeader = document.getElementById('guestHeaderActions');
    const authSidebar = document.getElementById('authSidebarWidgets');
    const guestSidebar = document.getElementById('guestSidebarWidget');

    if (isAuthenticated) {
      if (authHeader) authHeader.style.display = 'flex';
      if (guestHeader) guestHeader.style.display = 'none';
      if (authSidebar) authSidebar.style.display = 'flex';
      if (guestSidebar) guestSidebar.style.display = 'none';
    } else {
      if (authHeader) authHeader.style.display = 'none';
      if (guestHeader) guestHeader.style.display = 'flex';
      if (authSidebar) authSidebar.style.display = 'none';
      if (guestSidebar) guestSidebar.style.display = 'flex';
    }
  }

  // ── Profile Dropdown Binding ──
  function bindDropdownMenu() {
    const profileBox = document.getElementById('profileBox');
    const dropdownMenu = document.getElementById('dropdownMenu');
    const btnLogout = document.getElementById('btnLogout');

    if (profileBox && dropdownMenu) {
      profileBox.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdownMenu.classList.toggle('show');
      });

      document.addEventListener('click', () => {
        dropdownMenu.classList.remove('show');
      });
    }

    if (btnLogout) {
      btnLogout.addEventListener('click', (e) => {
        e.preventDefault();
        if (window.WarungioAuth) {
          window.WarungioAuth.logout();
          // logout() already redirects to '/', no need to override
        }
      });
    }
  }

  // ── User Information (Name, Balance, Photo) ──
  async function loadUserProfile() {
    if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) return;
    try {
      const u = await WarungioAPI.checkAuth();
      if (u && u.user) {
        const userNameEl = document.getElementById('userName');
        const userAvatarEl = document.getElementById('userAvatar');
        const userBalanceEl = document.getElementById('userBalance');
        const userRoleBadge = document.getElementById('userRoleBadge');
        const userBalanceDropdownEl = document.getElementById('userBalanceDropdown');

        const displayName = u.user.full_name || u.user.email;
        if (userNameEl) userNameEl.textContent = `Hai, ${displayName}`;
        if (userBalanceEl) userBalanceEl.textContent = 'Rp ' + Number(u.user.wallet_balance ?? 0).toLocaleString('id-ID');
        if (userBalanceDropdownEl) userBalanceDropdownEl.textContent = 'Rp ' + Number(u.user.wallet_balance ?? 0).toLocaleString('id-ID');
        
        if (u.user.profile_photo && userAvatarEl) {
          userAvatarEl.src = u.user.profile_photo;
        }
        if (userRoleBadge) {
          userRoleBadge.textContent = u.user.role === 'seller' ? 'Penjual' : 'Member';
          if (u.user.role === 'seller') {
            userRoleBadge.style.background = 'var(--warning)';
          }
        }
      }
    } catch (err) {
      console.warn('Failed to load user profile:', err);
    }
  }

  // ── Sync existing filter-row buttons with category cards ──
  function syncFilterBtnToCategoryCards() {
    const filterBtns = document.querySelectorAll('.filter-row .filter-btn');
    filterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const catId = btn.dataset.category;
        const catCards = document.querySelectorAll('.category-tab-card');
        catCards.forEach(c => {
          c.classList.remove('active');
          if (c.dataset.catId === catId || (catId === 'all' && c.dataset.catId === 'all')) {
            c.classList.add('active');
          }
        });
      });
    });
  }

  // ── Best Deals & Product Timer Countdowns ──
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

  // Store catalog state
  let storeCatalogState = {
    category: 'all',
    freeShipping: false,
    openOnly: false,
    verifiedOnly: false,
    codOnly: false,
    nearOnly: false,
    ratingOnly: false,
    promoOnly: false,
    sort: 'distance',
    page: 1,
    pageSize: 8,
    loadedAll: false,
    loading: false,
    coords: null,
    hasInitialized: false
  };

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
          storeCatalogState.coords = { lat, lon };
          updateLocationLabel({ lat, lon });
          await fetchStoresFromAPI({ lat, lon });
        },
        async (error) => {
          console.warn('Geolocation blocked or unavailable. Falling back to recommended stores:', error.message);
          updateLocationLabel(null);
          await fetchStoresFromAPI(); // Fallback to fetching all/default recommended stores
        },
        { timeout: 5000 }
      );
    } else {
      console.warn('Geolocation not supported by browser. Falling back to default stores.');
      updateLocationLabel(null);
      await fetchStoresFromAPI();
    }
  }

  function updateLocationLabel(coords) {
    const userLocationEl = document.getElementById('userLocation');
    if (userLocationEl) {
      if (coords) {
        userLocationEl.innerHTML = `Lokasi Aktif`;
      } else {
        userLocationEl.innerHTML = `Pilih Lokasi...`;
      }
    }
  }

  async function fetchStoresFromAPI(coords = null) {
    // If catalog view is active, we bypass loading carousel home mode and defer to fetchStoreCatalog
    if (document.body.classList.contains('stores-catalog-view-active')) {
      if (!storeCatalogState.hasInitialized) {
        await initStoreCatalog();
      }
      return;
    }
    
    try {
      const params = { page: 1, pageSize: 6 };
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
        const bannerUrl = s.store_banner_url || '/static/images/promosi-toko.png';
        const logoUrl = s.store_logo_url || '';
        const categoryName = s.category || 'Toko';
        const cityName = s.city || 'Lokal';
        const rating = Number(s.rating_avg != null ? s.rating_avg : 0).toFixed(1);
        const deliveryTime = s.is_open ? '10-20 min' : 'Tutup';
        const favClass = s.is_favorite ? 'is-fav' : '';
        const openClass = s.is_open ? 'open' : 'closed';
        const openText = s.is_open ? 'Buka' : 'Tutup';

        const card = document.createElement('div');
        card.className = 'premium-warung-card';
        card.innerHTML = `
          <div class="pwc-banner">
            <img src="${bannerUrl}" alt="${s.store_name}" onerror="this.src='/static/images/promosi-toko.png'">
            <span class="pwc-status ${openClass}">
              <span style="width:5px;height:5px;border-radius:50%;background:${s.is_open ? '#fff' : '#fff'};display:inline-block;${s.is_open ? 'animation:pulse-dot 1.5s infinite' : ''}"></span>
              ${openText}
            </span>
            <button class="pwc-fav ${favClass}" data-id="${s.id}">
              <i class="fa-${favClass ? 'solid' : 'regular'} fa-heart"></i>
            </button>
          </div>
          <div class="pwc-body">
            <div class="pwc-name-row">
              <span class="pwc-name">${s.store_name} <i class="fa-solid fa-circle-check pwc-verified"></i></span>
            </div>
            <span class="pwc-category">${categoryName}</span>
            <span style="font-size:10px;color:#64748B;"><i class="fa-solid fa-location-dot" style="margin-right:2px;"></i>${cityName}</span>
            <div class="pwc-meta">
              <span><i class="fa-solid fa-star pwc-star"></i> ${rating}</span>
              <span>|</span>
              <span><i class="fa-regular fa-clock"></i> ${deliveryTime}</span>
              ${s.has_active_promo ? `<span class="pwc-promo-badge"><i class="fa-solid fa-tag"></i> Diskon</span>` : ''}
            </div>
            <button class="pwc-cta">Kunjungi Warung</button>
          </div>
        `;

        card.addEventListener('click', () => {
          window.location.href = '/toko/' + s.slug + '/';
        });

        card.querySelector('.pwc-fav')?.addEventListener('click', (e) => {
          e.stopPropagation();
          const btn = e.currentTarget;
          btn.classList.toggle('is-fav');
          const icon = btn.querySelector('i');
          if (btn.classList.contains('is-fav')) {
            icon.className = 'fa-solid fa-heart';
          } else {
            icon.className = 'fa-regular fa-heart';
          }
        });

        storeGrid.appendChild(card);
      });
    } catch (err) {
      console.warn('Failed to load stores:', err);
      storeGrid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--muted);padding:20px;">Gagal memuat warung terdekat.</div>';
    }
  }

  // ── Nearby Stores Catalog Event Bindings ──
  function setupStoreCatalogEvents() {
    // Category chips
    const chips = document.querySelectorAll('#storeCategoryFilter .store-filter-btn');
    chips.forEach(chip => {
      chip.addEventListener('click', async (e) => {
        chips.forEach(c => c.classList.remove('active', 'bg-primary', 'text-white'));
        chips.forEach(c => c.classList.add('bg-white', 'border', 'border-slate-200', 'text-slate-500'));
        
        chip.classList.add('active', 'bg-primary', 'text-white');
        chip.classList.remove('bg-white', 'border', 'border-slate-200', 'text-slate-500');
        
        storeCatalogState.category = chip.getAttribute('data-category');
        storeCatalogState.page = 1;
        storeCatalogState.loadedAll = false;
        await fetchStoreCatalog({ append: false });
      });
    });

    // Checkboxes
    const binds = [
      { id: 'storeCheckFreeShipping', prop: 'freeShipping' },
      { id: 'storeCheckOpen', prop: 'openOnly' },
      { id: 'storeCheckVerified', prop: 'verifiedOnly' },
      { id: 'storeCheckCod', prop: 'codOnly' },
      { id: 'storeCheckNear', prop: 'nearOnly' },
      { id: 'storeCheckRating', prop: 'ratingOnly' },
      { id: 'storeCheckDiskon', prop: 'promoOnly' }
    ];
    binds.forEach(b => {
      const el = document.getElementById(b.id);
      if (el) {
        el.addEventListener('change', async (e) => {
          storeCatalogState[b.prop] = e.target.checked;
          storeCatalogState.page = 1;
          storeCatalogState.loadedAll = false;
          await fetchStoreCatalog({ append: false });
        });
      }
    });

    // Sort Dropdown
    const sortSelect = document.getElementById('storeSortSelect');
    if (sortSelect) {
      sortSelect.addEventListener('change', async (e) => {
        storeCatalogState.sort = e.target.value;
        storeCatalogState.page = 1;
        storeCatalogState.loadedAll = false;
        await fetchStoreCatalog({ append: false });
      });
    }

    // Load More Button
    const loadMoreBtn = document.getElementById('loadMoreStoresBtn');
    if (loadMoreBtn) {
      loadMoreBtn.addEventListener('click', async () => {
        if (storeCatalogState.loading || storeCatalogState.loadedAll) return;
        storeCatalogState.page += 1;
        await fetchStoreCatalog({ append: true });
      });
    }

    // Reset Filters
    const resetBtn = document.getElementById('btnResetStoreFilters');
    if (resetBtn) {
      resetBtn.addEventListener('click', async () => {
        storeCatalogState.category = 'all';
        storeCatalogState.freeShipping = false;
        storeCatalogState.openOnly = false;
        storeCatalogState.verifiedOnly = false;
        storeCatalogState.codOnly = false;
        storeCatalogState.nearOnly = false;
        storeCatalogState.ratingOnly = false;
        storeCatalogState.promoOnly = false;
        storeCatalogState.sort = 'distance';
        storeCatalogState.page = 1;
        storeCatalogState.loadedAll = false;

        chips.forEach((c, idx) => {
          if (idx === 0) {
            c.classList.add('active', 'bg-primary', 'text-white');
            c.classList.remove('bg-white', 'border', 'border-slate-200', 'text-slate-500');
          } else {
            c.classList.remove('active', 'bg-primary', 'text-white');
            c.classList.add('bg-white', 'border', 'border-slate-200', 'text-slate-500');
          }
        });
        binds.forEach(b => {
          const el = document.getElementById(b.id);
          if (el) el.checked = false;
        });
        if (sortSelect) sortSelect.value = 'distance';

        await fetchStoreCatalog({ append: false });
      });
    }

    // Change Location
    const changeLocBtn = document.getElementById('btnChangeLocationStore');
    if (changeLocBtn) {
      changeLocBtn.addEventListener('click', () => {
        if (navigator.geolocation) {
          navigator.geolocation.getCurrentPosition(
            async (position) => {
              storeCatalogState.coords = {
                lat: position.coords.latitude,
                lon: position.coords.longitude
              };
              updateLocationLabel(storeCatalogState.coords);
              storeCatalogState.page = 1;
              storeCatalogState.loadedAll = false;
              await fetchStoreCatalog({ append: false });
            },
            (error) => {
              alert('Gagal mendapatkan lokasi Anda.');
            }
          );
        } else {
          alert('Geolocation tidak didukung oleh browser Anda.');
        }
      });
    }
  }

  // ── Fetch & Render Nearby Stores Catalog Grid ──
  async function fetchStoreCatalog({ append = false }) {
    if (storeCatalogState.loading) return;
    storeCatalogState.loading = true;

    const loadMoreWrapper = document.getElementById('loadMoreStoresWrapper');
    const emptyState = document.getElementById('storesEmptyState');
    const storeBadge = document.getElementById('storeCountBadge');
    
    // Show Skeletons
    if (!append) {
      storeGrid.innerHTML = `
        <div class="skeleton-store-card shimmer"></div>
        <div class="skeleton-store-card shimmer"></div>
        <div class="skeleton-store-card shimmer"></div>
        <div class="skeleton-store-card shimmer"></div>
      `;
      if (loadMoreWrapper) loadMoreWrapper.style.display = 'none';
      if (emptyState) emptyState.style.display = 'none';
    } else {
      const skeletons = document.createElement('div');
      skeletons.id = 'storeSkeletonsAppend';
      skeletons.className = 'contents';
      skeletons.innerHTML = `
        <div class="skeleton-store-card shimmer"></div>
        <div class="skeleton-store-card shimmer"></div>
        <div class="skeleton-store-card shimmer"></div>
        <div class="skeleton-store-card shimmer"></div>
      `;
      storeGrid.appendChild(skeletons);
    }

    try {
      const params = {
        page: storeCatalogState.page,
        pageSize: storeCatalogState.pageSize,
        ordering: storeCatalogState.sort
      };

      if (storeCatalogState.category && storeCatalogState.category !== 'all') {
        params.category = storeCatalogState.category;
      }
      if (storeCatalogState.promoOnly) {
        params.has_promo = 'true';
      }
      if (storeCatalogState.coords) {
        params.latitude = storeCatalogState.coords.lat;
        params.longitude = storeCatalogState.coords.lon;
      }
      
      const data = await WarungioAPI.getStores(params);
      const list = Array.isArray(data) ? data : (data.results || []);
      const totalCount = data.count || list.length;
      
      if (storeBadge) storeBadge.textContent = totalCount;

      if (!append) {
        storeGrid.innerHTML = '';
      } else {
        const skeletonsAppend = document.getElementById('storeSkeletonsAppend');
        if (skeletonsAppend) skeletonsAppend.remove();
      }

      if (list.length === 0 && !append) {
        if (emptyState) emptyState.style.display = 'block';
        if (loadMoreWrapper) loadMoreWrapper.style.display = 'none';
        storeCatalogState.loading = false;
        return;
      }

      list.forEach(s => {
        const rating = Number(s.rating_avg != null ? s.rating_avg : 0).toFixed(1);
        const distance = storeCatalogState.coords ? '0.8 km' : '0.5 km';
        const deliveryTime = s.is_open ? '10-20 min' : 'Tutup';
        const logoUrl = s.store_logo_url || '';
        const bannerUrl = s.store_banner_url || '/static/images/promosi-toko.png';
        const favClass = s.is_favorite ? 'is-fav' : '';
        const openText = s.is_open ? 'Buka' : 'Tutup';
        const categoryName = s.category || 'Toko';
        const totalProducts = s.product_count != null ? s.product_count : 0;
        const desc = s.description || '';
        const shortDesc = desc.length > 80 ? desc.substring(0, 80) + '...' : desc;
        const addressShort = s.address || s.city || 'Lokal';
        const memberSince = s.created_at ? new Date(s.created_at).getFullYear() : new Date().getFullYear();
        
        const card = document.createElement('div');
        card.className = 'mini-storefront-card';
        card.setAttribute('data-store-slug', s.slug);
        card.innerHTML = `
          <div class="msf-banner">
            <img src="${bannerUrl}" alt="${s.store_name}" onerror="this.src='/static/images/promosi-toko.png'">
            <div class="msf-banner-overlay"></div>
            <div class="msf-badges">
              <span class="msf-badge ${s.is_open ? 'msf-badge-open' : 'msf-badge-closed'}">
                ${s.is_open ? '<span class="msf-dot"></span>' : ''} ${openText}
              </span>
              <span class="msf-badge msf-badge-verified"><i class="fa-solid fa-circle-check"></i> Verified</span>
              <span class="msf-badge msf-badge-free-ship"><i class="fa-solid fa-truck-fast"></i> Gratis</span>
              ${s.has_active_promo ? `<span class="msf-badge msf-badge-promo"><i class="fa-solid fa-fire"></i> Diskon</span>` : ''}
            </div>
            <button class="msf-fav-btn ${favClass}" data-id="${s.id}">
              <i class="fa-${favClass ? 'solid' : 'regular'} fa-heart"></i>
            </button>
            <div class="msf-logo-wrapper">
              ${logoUrl ? `<img src="${logoUrl}" alt="${s.store_name}">` : `<div class="msf-logo-placeholder">${s.store_name.charAt(0).toUpperCase()}</div>`}
            </div>
          </div>
          <div class="msf-body">
            <h3 class="msf-store-name">${s.store_name} <i class="fa-solid fa-circle-check msf-verified-icon"></i></h3>
            <span class="msf-category-tag"><i class="fa-solid fa-tag" style="font-size:8px;margin-right:2px;"></i> ${categoryName}</span>
            <div class="msf-stats">
              <span><i class="fa-solid fa-star msf-star"></i> ${rating}</span>
              <span class="msf-stat-divider">|</span>
              <span>${s.follower_count || 0} pengikut</span>
              <span class="msf-stat-divider">|</span>
              <span>${totalProducts} produk</span>
            </div>
            ${shortDesc ? `<p class="msf-desc">${shortDesc}</p>` : ''}
            <div class="msf-info-row">
              <span class="msf-info-item"><i class="fa-solid fa-location-dot"></i> ${addressShort}</span>
              <span class="msf-info-item"><i class="fa-regular fa-clock"></i> ${deliveryTime}</span>
              <span class="msf-info-item"><i class="fa-regular fa-calendar"></i> Sejak ${memberSince}</span>
            </div>
            ${s.featured_products && s.featured_products.length > 0 ? `
            <div class="msf-featured-products">
              ${s.featured_products.slice(0, 4).map(fp => `
                <div class="msf-mini-product">
                  <img src="${fp.product_photo_url || '/static/images/paket-sayur.png'}" alt="${fp.product_name}" loading="lazy" onerror="this.src='/static/images/paket-sayur.png'">
                  <div class="msf-mini-product-info">
                    <span class="msf-mini-product-name">${fp.product_name}</span>
                    <span class="msf-mini-product-price">Rp ${Number(fp.price).toLocaleString('id-ID')}</span>
                  </div>
                </div>
              `).join('')}
            </div>
            ` : ''}
            <div class="msf-actions">
              <button class="msf-btn-primary"><i class="fa-solid fa-store"></i> Kunjungi Warung</button>
              <button class="msf-btn-secondary"><i class="fa-solid fa-box"></i> Lihat Produk</button>
            </div>
          </div>
        `;

        card.querySelector('.msf-btn-primary')?.addEventListener('click', (e) => {
          e.stopPropagation();
          window.location.href = '/toko/' + s.slug + '/';
        });

        card.querySelector('.msf-btn-secondary')?.addEventListener('click', (e) => {
          e.stopPropagation();
          window.location.href = '/toko/' + s.slug + '/products/';
        });

        card.addEventListener('click', () => {
          window.location.href = '/toko/' + s.slug + '/';
        });

        card.querySelector('.msf-fav-btn')?.addEventListener('click', async (e) => {
          e.stopPropagation();
          const btn = e.currentTarget;
          btn.classList.toggle('is-fav');
          const icon = btn.querySelector('i');
          if (btn.classList.contains('is-fav')) {
            icon.className = 'fa-solid fa-heart';
            try {
              await WarungioAPI.addFavoriteStore(s.id);
            } catch (err) {}
          } else {
            icon.className = 'fa-regular fa-heart';
            try {
              await WarungioAPI.removeFavoriteStore(s.id);
            } catch (err) {}
          }
        });

        storeGrid.appendChild(card);
      });

      if (list.length < storeCatalogState.pageSize) {
        storeCatalogState.loadedAll = true;
        if (loadMoreWrapper) loadMoreWrapper.style.display = 'none';
      } else {
        if (loadMoreWrapper) loadMoreWrapper.style.display = 'flex';
      }

    } catch (err) {
      console.warn('Failed to load store catalog:', err);
      if (!append) {
        storeGrid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--muted);padding:40px;">Gagal memuat warung terdekat. Silakan klik Coba Lagi.</div>';
      } else {
        const skeletonsAppend = document.getElementById('storeSkeletonsAppend');
        if (skeletonsAppend) skeletonsAppend.remove();
        alert('Gagal memuat data halaman berikutnya.');
      }
    } finally {
      storeCatalogState.loading = false;
    }
  }

  async function initStoreCatalog() {
    storeCatalogState.hasInitialized = true;
    setupStoreCatalogEvents();
    if (storeCatalogState.coords === null) {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (position) => {
            storeCatalogState.coords = {
              lat: position.coords.latitude,
              lon: position.coords.longitude
            };
            fetchStoreCatalog({ append: false });
          },
          () => {
            fetchStoreCatalog({ append: false });
          }
        );
      } else {
        fetchStoreCatalog({ append: false });
      }
    } else {
      fetchStoreCatalog({ append: false });
    }
  }

  // ── Load Kategori Populer (Dynamic rectangular cards) ──
  async function loadPopularCategories() {
    const catGrid = document.getElementById('popularCategoriesGrid');
    if (!catGrid) return;

    try {
      const data = await WarungioAPI.getCategories();
      const cats = Array.isArray(data) ? data : (data.results || []);

      if (cats.length === 0) {
        catGrid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:#94a3b8;padding:16px;font-size:13px;">Belum ada kategori tersedia.</div>';
        return;
      }

      catGrid.innerHTML = '';

      // Add "Semua" as first card
      const allCard = document.createElement('div');
      allCard.className = 'category-tab-card active';
      allCard.textContent = 'Semua';
      allCard.dataset.catId = 'all';
      allCard.addEventListener('click', () => {
        handleCategoryCardClick(allCard, 'all');
      });
      catGrid.appendChild(allCard);

      cats.forEach(cat => {
        const card = document.createElement('div');
        card.className = 'category-tab-card';
        const catName = cat.name || cat.category_name || cat;
        const catId = cat.id || cat.name || cat;
        card.textContent = catName;
        card.dataset.catId = catId;
        card.addEventListener('click', () => {
          handleCategoryCardClick(card, catId);
        });
        catGrid.appendChild(card);
      });
    } catch (err) {
      console.warn('Failed to load categories:', err);
      catGrid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:#94a3b8;padding:16px;font-size:13px;">Gagal memuat kategori.</div>';
    }
  }

  function handleCategoryCardClick(card, catId) {
    // Toggle active state on category cards
    const allCards = document.querySelectorAll('.category-tab-card');
    allCards.forEach(c => c.classList.remove('active'));
    card.classList.add('active');

    // Also activate the corresponding filter-btn in the produk filter row
    const filterBtns = document.querySelectorAll('.filter-row .filter-btn');
    filterBtns.forEach(btn => {
      btn.classList.remove('active');
      if (btn.dataset.category === String(catId)) {
        btn.classList.add('active');
      }
    });
    // If catId is 'all', activate the first filter-btn
    if (catId === 'all' && filterBtns.length > 0) {
      filterBtns[0].classList.add('active');
    }

    // Load fresh products filtered by this category
    loadFreshProducts(catId === 'all' ? null : catId);

    // Smooth scroll to the produk section
    const produkSection = document.getElementById('produkGrid')?.closest('.home-section');
    if (produkSection) {
      setTimeout(() => {
        produkSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
  }

  // ── Load Fresh Products & Quick Add to Cart ──
  async function loadFreshProducts(categoryId = null) {
    if (!productGrid) return;
    try {
      const params = { page: 1, pageSize: 8 };
      if (categoryId && categoryId !== 'others' && categoryId !== 'all') {
        params.category = categoryId;
      }
      
      const data = await WarungioAPI.getProducts(params);
      let products = Array.isArray(data) ? data : (data.results || []);
      
      if (categoryId === 'others') {
        products = products.filter(p => p.category !== 1 && p.category !== 2 && p.category !== 3 && p.category !== 4);
      }
      
      productGrid.innerHTML = '';
      if (products.length === 0) {
        productGrid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--muted);padding:20px;">Tidak ada produk tersedia.</div>';
        return;
      }
      
      products.forEach(p => {
        const priceStr = 'Rp ' + Number(p.price).toLocaleString('id-ID');
        const originalPrice = Math.round(Number(p.price) / 0.85); // 15% discount simulation
        const oldPriceStr = 'Rp ' + originalPrice.toLocaleString('id-ID');
        const img = p.product_photo || p.image || `/static/images/paket-sayur.png`;
        const rating = Number(p.rating_avg != null ? p.rating_avg : 4.8).toFixed(1);
        
        const card = document.createElement('div');
        card.className = 'produk-card';
        card.innerHTML = `
          <div class="produk-image-wrapper">
            <img src="${img}" alt="${p.product_name}" class="produk-img" loading="lazy">
            <span class="card-badge-fresh">Segar</span>
            <span class="card-badge-discount">-15%</span>
            <button class="btn-wishlist-product" data-id="${p.id}"><i class="fa-regular fa-heart"></i></button>
          </div>
          <div class="produk-info">
            <span class="produk-category">${p.category_name || 'Kategori'}</span>
            <h4 class="produk-name">${p.product_name}</h4>
            <span class="produk-store-name">${p.store_name || 'Warung Lokal'}</span>
            <div class="produk-rating-sold">
              <i class="fa-solid fa-star"></i>
              <span>${rating}</span>
              <span class="meta-divider">•</span>
              <span>Terjual ${p.sold_count != null ? p.sold_count : 10}+</span>
            </div>
            <div class="produk-price-row">
              <div class="produk-price-box">
                <span class="price-old-strikethrough">${oldPriceStr}</span>
                <span class="price-actual">${priceStr} <span class="price-unit">/ ${p.unit || 'pcs'}</span></span>
              </div>
              <button class="btn-add-cart" data-id="${p.id}"><i class="fa-solid fa-plus"></i></button>
            </div>
          </div>
        `;
        
        productGrid.appendChild(card);

        // Click on card goes to product detail
        card.addEventListener('click', () => {
          window.location.href = `/products/${p.id}/`;
        });

        // Bind wishlist toggle
        card.querySelector('.btn-wishlist-product')?.addEventListener('click', (e) => {
          e.stopPropagation();
          const btn = e.currentTarget;
          btn.classList.toggle('is-fav');
          const icon = btn.querySelector('i');
          if (btn.classList.contains('is-fav')) {
            icon.className = 'fa-solid fa-heart';
          } else {
            icon.className = 'fa-regular fa-heart';
          }
        });

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
      window.location.href = '/?next=' + encodeURIComponent(window.location.pathname);
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
        div.innerHTML = `
          <img src="${img}" alt="${p.product_name}" style="width:40px; height:40px; border-radius:8px; object-fit:cover;" loading="lazy">
          <div style="flex:1; min-width:0;">
            <b style="color:var(--text); font-weight:700; font-size:12px; display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${p.product_name}</b>
            <span style="display:block; font-size:10px; color:var(--muted);">${p.store_name || 'Warung Lokal'}</span>
            <span style="font-weight:700; color:var(--text); font-size:11px; display:block; margin-top:2px;">${priceStr}</span>
          </div>
          <button class="btn-add-rec btn-add-cart" data-id="${p.id}"><i class="fa-solid fa-plus"></i></button>
        `;

        div.addEventListener('click', () => {
          window.location.href = `/products/${p.id}/`;
        });

        div.querySelector('.btn-add-rec')?.addEventListener('click', (e) => {
          e.stopPropagation();
          handleQuickAddToCart(p.id);
        });

        recomendList.appendChild(div);
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
            driverInfo = `${tracking.driver_name} (${tracking.driver_phone || ''})`;
          }
        }
      } catch (err) {
        console.warn('Could not fetch tracking detail:', err);
      }

      activeOrderContent.innerHTML = `
        <div class="active-order-tracking-card" onclick="window.location.href='/buyer/orders/'" style="cursor:pointer;">
            <div class="tracking-card-header-row" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span class="order-inv-num" style="font-weight:800; color:#166534; font-size:13px;">#${o.order_number}</span>
                <span class="tracking-status-badge" style="background:#166534; color:white; font-size:10px; padding:2px 8px; border-radius:6px; font-weight:700;">${statusLabel}</span>
            </div>
            <div class="tracking-courier-details" style="font-size:12px; color:#475569; display:flex; align-items:center; gap:6px; margin-bottom:8px;">
                <i class="fa-solid fa-motorcycle"></i>
                <span>Kurir: <b>${courierText}</b></span>
            </div>
            <div class="tracking-total-price" style="display:flex; justify-content:space-between; align-items:center; font-size:12px; font-weight:600; color:#0F172A;">
                <span>Total Belanja</span>
                <strong>Rp ${Number(o.total_price).toLocaleString('id-ID')}</strong>
            </div>
            ${driverInfo ? `
            <div class="driver-profile-widget" style="display:flex; align-items:center; gap:10px; border-top:1px dashed #E2E8F0; padding-top:10px; margin-top:10px;">
                <div class="driver-avatar-circle" style="width:28px; height:28px; border-radius:50%; background:#F1F5F9; display:flex; align-items:center; justify-content:center; color:#475569; font-size:12px;">
                    <i class="fa-solid fa-user"></i>
                </div>
                <div class="driver-contact-info" style="display:flex; flex-direction:column; font-size:11px;">
                    <span class="driver-name" style="font-weight:700;">${driverInfo.split(' (')[0]}</span>
                    <span class="driver-phone" style="color:#64748B;">${driverInfo.split(' (')[1]?.replace(')', '') || ''}</span>
                </div>
            </div>
            ` : ''}
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
        window.location.href = '/?next=' + encodeURIComponent(window.location.pathname);
        return;
      }

      // Create a nice programmatic prompt modal for top-up
      const modal = document.createElement('div');
      modal.style.cssText = 'position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:9999; display:flex; align-items:center; justify-content:center; font-family:var(--font-main);';
      
      const card = document.createElement('div');
      card.style.cssText = 'background:white; padding:24px; border-radius:24px; width:90%; max-width:400px; box-shadow:0 20px 40px rgba(0,0,0,0.15); display:flex; flex-direction:column; gap:16px; border: 1px solid #E5E7EB;';
      
      card.innerHTML = `
        <h3 style="font-size:18px; font-weight:800; color:#0F172A; margin:0;">Top Up Saldo Dompet</h3>
        <p style="font-size:13px; color:#64748B; margin:0; line-height:1.5;">Pilih nominal top-up saldo atau masukkan jumlah kustom (minimal Rp 10.000):</p>
        
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:8px;">
          <button class="nominal-btn" data-val="50000" style="padding:12px; border:1px solid #E5E7EB; border-radius:12px; background:transparent; font-weight:700; color:#475569; cursor:pointer; font-size:13px; transition:all 0.2s;">Rp 50.000</button>
          <button class="nominal-btn" data-val="100000" style="padding:12px; border:1px solid #E5E7EB; border-radius:12px; background:transparent; font-weight:700; color:#475569; cursor:pointer; font-size:13px; transition:all 0.2s;">Rp 100.000</button>
          <button class="nominal-btn" data-val="200000" style="padding:12px; border:1px solid #E5E7EB; border-radius:12px; background:transparent; font-weight:700; color:#475569; cursor:pointer; font-size:13px; transition:all 0.2s;">Rp 200.000</button>
          <button class="nominal-btn" data-val="500000" style="padding:12px; border:1px solid #E5E7EB; border-radius:12px; background:transparent; font-weight:700; color:#475569; cursor:pointer; font-size:13px; transition:all 0.2s;">Rp 500.000</button>
        </div>
        
        <div style="display:flex; flex-direction:column; gap:6px;">
          <label style="font-size:12px; font-weight:700; color:#0F172A;">Nominal Kustom (Rp)</label>
          <input type="number" id="customAmountInput" placeholder="Masukkan nominal (contoh: 25000)" style="padding:12px; border:1px solid #E5E7EB; border-radius:12px; font-size:14px; width:100%; outline:none; font-weight:600;" min="10000" />
        </div>
        
        <div style="display:flex; justify-content:flex-end; gap:12px; margin-top:8px;">
          <button id="cancelTopUpBtn" style="padding:12px 18px; border:none; background:#F1F5F9; border-radius:12px; font-weight:700; color:#475569; cursor:pointer; font-size:13px;">Batal</button>
          <button id="submitTopUpBtn" style="padding:12px 18px; border:none; background:#16A34A; border-radius:12px; font-weight:700; color:white; cursor:pointer; font-size:13px; box-shadow:0 4px 12px rgba(22, 163, 74, 0.2);">Top Up Sekarang</button>
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
            b.style.borderColor = '#E5E7EB';
            b.style.background = 'transparent';
            b.style.color = '#475569';
          });
          btnBtn.style.borderColor = '#16A34A';
          btnBtn.style.background = '#F0FDF4';
          btnBtn.style.color = '#16A34A';
          selectedAmount = Number(btnBtn.dataset.val);
          customInput.value = ''; // clear custom input
        });
      });
      
      customInput.addEventListener('input', () => {
        // Clear nominal selections
        nominalBtns.forEach(b => {
          b.style.borderColor = '#E5E7EB';
          b.style.background = 'transparent';
          b.style.color = '#475569';
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
          // Client key fetched from backend configuration
          let midtransClientKey = '';
          try {
            const config = await WarungioAPI.getPaymentConfig();
            if (config && config.client_key) {
              midtransClientKey = config.client_key;
            }
          } catch (e) {
            console.error('Payment config fetch failed — cannot proceed:', e);
            alert('Gagal memuat konfigurasi pembayaran. Coba refresh halaman.');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Top Up Sekarang';
            return;
          }
          
          // Load Midtrans Snap JS dynamically
          if (!window.snap || !window.snap.pay) {
            await new Promise((resolve, reject) => {
              const script = document.createElement('script');
              // Load Snap JS from backend-provided URL (NEVER fall back to sandbox)
              // Uses window.WARUNGIO_SNAP_JS_URL if set by websocket.js config fetch
              var snapJsUrl = window.WARUNGIO_SNAP_JS_URL || (
                window.WARUNGIO_SNAP_BASE_URL || 'https://app.midtrans.com'
              ) + '/snap/snap.js';
              script.src = snapJsUrl;
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

  // ── Load Best Deals Section ──
  async function loadBestDeals() {
    const bestDealsGrid = document.getElementById('bestDealsGrid');
    if (!bestDealsGrid) return;
    try {
      const data = await WarungioAPI.getProducts({ page: 1, pageSize: 8 });
      const products = Array.isArray(data) ? data : (data.results || []);
      
      bestDealsGrid.innerHTML = '';
      if (products.length === 0) {
        bestDealsGrid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--muted);padding:20px;">Tidak ada promo tersedia.</div>';
        return;
      }
      
      products.forEach(p => {
        const promoPrice = Number(p.price);
        const originalPrice = Math.round(promoPrice / 0.85); // simulate 15% discount
        const priceStr = 'Rp ' + promoPrice.toLocaleString('id-ID');
        const oldPriceStr = 'Rp ' + originalPrice.toLocaleString('id-ID');
        const img = p.product_photo || p.image || `/static/images/paket-sayur.png`;
        
        const card = document.createElement('div');
        card.className = 'deal-card';
        card.innerHTML = `
          <span class="deal-badge card-badge-discount">-15%</span>
          <div class="deal-image-wrapper">
            <img src="${img}" alt="${p.product_name}" loading="lazy" />
          </div>
          <div class="deal-content">
            <span class="produk-category">${p.category_name || 'Kategori'}</span>
            <h4 class="deal-title">${p.product_name}</h4>
            <span class="deal-store">${p.store_name || 'Warung Lokal'}</span>
            <div class="deal-price-row" style="display:flex; justify-content:space-between; align-items:flex-end;">
              <div class="deal-prices">
                <span class="deal-old-price">${oldPriceStr}</span>
                <strong class="deal-price">${priceStr}</strong>
              </div>
              <button class="btn-add-deal btn-add-cart" data-id="${p.id}"><i class="fa-solid fa-plus"></i></button>
            </div>
          </div>
        `;

        card.addEventListener('click', () => {
          window.location.href = `/products/${p.id}/`;
        });

        // Bind quick add-to-cart click handler
        card.querySelector('.btn-add-deal')?.addEventListener('click', (e) => {
          e.stopPropagation();
          handleQuickAddToCart(p.id);
        });

        bestDealsGrid.appendChild(card);
      });
    } catch (err) {
      console.warn('Failed to load best deals:', err);
    }
  }

  // ── Best Deals Countdown Timer ──
  function startDealsCountdown() {
    const timerVal = document.getElementById('deals-timer-val');
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

  // ── Category Chip Click Handlers ──
  function setupCategoryChips() {
    const filterBtns = document.querySelectorAll('.filter-row .filter-btn');
    filterBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        filterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const cat = btn.getAttribute('data-category');
        
        // Show loading shimmer skeleton on click
        if (productGrid) {
          productGrid.innerHTML = `
            <div class="skeleton-product-card shimmer"></div>
            <div class="skeleton-product-card shimmer"></div>
            <div class="skeleton-product-card shimmer"></div>
            <div class="skeleton-product-card shimmer"></div>
          `;
        }
        loadFreshProducts(cat);
      });
    });
  }

  // ── Setup Carousel Pagination Dots ──
  function setupCarouselDots(trackId, dotsContainerId) {
    const track = document.getElementById(trackId);
    const dotsContainer = document.getElementById(dotsContainerId);
    if (!track || !dotsContainer) return;

    dotsContainer.innerHTML = '';
    const numDots = 5;
    const dots = [];

    for (let i = 0; i < numDots; i++) {
      const dot = document.createElement('span');
      dot.className = `w-2 h-2 rounded-full cursor-pointer transition-all duration-300 ${i === 0 ? 'bg-primary w-4' : 'bg-slate-300'}`;
      dot.addEventListener('click', () => {
        const scrollWidth = track.scrollWidth - track.clientWidth;
        const targetScroll = (scrollWidth / (numDots - 1)) * i;
        track.scrollTo({ left: targetScroll, behavior: 'smooth' });
      });
      dotsContainer.appendChild(dot);
      dots.push(dot);
    }

    track.addEventListener('scroll', () => {
      const scrollWidth = track.scrollWidth - track.clientWidth;
      if (scrollWidth <= 0) return;
      const progress = track.scrollLeft / scrollWidth;
      const activeIndex = Math.min(Math.round(progress * (numDots - 1)), numDots - 1);

      dots.forEach((dot, idx) => {
        if (idx === activeIndex) {
          dot.className = 'w-4 h-2 rounded-full bg-primary transition-all duration-300 cursor-pointer';
        } else {
          dot.className = 'w-2 h-2 rounded-full bg-slate-300 transition-all duration-300 cursor-pointer';
        }
      });
    });
  }

  // ── Setup Carousel Auto-Scroll (Pause on hover) ──
  function setupCarouselAutoScroll(trackId) {
    const track = document.getElementById(trackId);
    if (!track) return;
    
    let intervalId = null;
    let isHovered = false;
    
    const startScroll = () => {
      intervalId = setInterval(() => {
        if (isHovered) return;
        const maxScrollLeft = track.scrollWidth - track.clientWidth;
        if (track.scrollLeft >= maxScrollLeft - 10) {
          track.scrollTo({ left: 0, behavior: 'smooth' });
        } else {
          track.scrollBy({ left: 300, behavior: 'smooth' });
        }
      }, 5000);
    };
    
    track.addEventListener('mouseenter', () => isHovered = true);
    track.addEventListener('mouseleave', () => isHovered = false);
    
    startScroll();
  }

  // ── Button Ripple Click Animation ──
  function setupButtonRipple() {
    document.addEventListener('click', (e) => {
      const target = e.target.closest('.btn-login-premium, .btn-register-premium, .btn-mitra-premium, .btn-visit-store, .btn-add-cart, .btn-sub-primary, .btn-topup-premium, .btn-guest-primary');
      if (!target) return;
      
      const ripple = document.createElement('span');
      ripple.className = 'ripple-effect';
      
      const rect = target.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      ripple.style.width = ripple.style.height = `${size}px`;
      
      const x = e.clientX - rect.left - size / 2;
      const y = e.clientY - rect.top - size / 2;
      ripple.style.left = `${x}px`;
      ripple.style.top = `${y}px`;
      
      target.classList.add('ripple');
      target.appendChild(ripple);
      
      ripple.addEventListener('animationend', () => {
        ripple.remove();
      });
    });
  }

  // ── Initialize All Components ──
  toggleAuthStates();
  bindDropdownMenu();
  bindWalletTopUp();
  setupCategoryChips();
  syncFilterBtnToCategoryCards();
  setupButtonRipple();

  // ── SPA Routing for Store Catalog ──
  async function checkHashNav() {
    const isStoreCatalog = window.location.hash === '#warung-section';
    if (isStoreCatalog) {
      document.body.classList.add('stores-catalog-view-active');
      
      // Update sidebar nav active links
      document.querySelectorAll('.sidebar-nav .nav-link, .nav-links-custom a').forEach(link => {
        const href = link.getAttribute('href');
        if (href && href.includes('#warung-section')) {
          link.classList.add('active');
        } else {
          link.classList.remove('active');
        }
      });

      if (!storeCatalogState.hasInitialized) {
        await initStoreCatalog();
      }
    } else {
      document.body.classList.remove('stores-catalog-view-active');
      
      // Update sidebar active links back to Beranda
      document.querySelectorAll('.sidebar-nav .nav-link, .nav-links-custom a').forEach(link => {
        const href = link.getAttribute('href');
        if (href === '/buyer/home/' || href === '/home/' || href === '' || href === '#') {
          link.classList.add('active');
        } else {
          link.classList.remove('active');
        }
      });
    }
  }

  window.addEventListener('hashchange', checkHashNav);
  await checkHashNav();

  // Load public components
  await Promise.all([loadStores(), loadFreshProducts(), loadBestDeals(), loadPopularCategories()]);

  // Setup carousels
  setupCarouselDots('warungGrid', 'warungCarouselDots');
  setupCarouselDots('bestDealsGrid', 'dealsCarouselDots');
  setupCarouselAutoScroll('warungGrid');
  setupCarouselAutoScroll('bestDealsGrid');

  // Load authenticated-only components if authenticated
  if (window.WarungioAuth && window.WarungioAuth.isAuthenticated()) {
    await loadUserProfile();
    await Promise.all([loadRecommendations(), loadActiveOrders()]);

    // Load initial cart count
    try {
      const countRes = await WarungioAPI.getCartCount();
      const cartBadgeHeader = document.getElementById('cartBadgeHeader');
      if (countRes && countRes.count !== undefined) {
        if (cartBadge) cartBadge.textContent = countRes.count;
        if (cartBadgeHeader) cartBadgeHeader.textContent = countRes.count;
      }
    } catch (e) {}
  }
});
