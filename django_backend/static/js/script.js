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
          window.location.href = '/home/';
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
        const banner = s.banner || `/static/images/promosi-toko.png`;
        const category = s.category_name || (s.id === 1 ? 'Toko Sembako' : 'Warung Segar');
        const city = s.city || (s.id === 1 ? 'Bandung' : 'Jakarta Pusat');
        const rating = Number(s.rating_avg || 4.5).toFixed(1);
        const deliveryTime = s.is_open ? '10-20 min' : 'Tutup';
        const favClass = s.is_favorite ? 'is-fav' : '';

        const card = document.createElement('div');
        card.className = 'warung-card';
        card.innerHTML = `
          <div class="relative h-[120px] rounded-xl overflow-hidden mb-3 image-container" style="position: relative;">
            <img src="${banner}" alt="${s.store_name} Banner" class="w-full h-full object-cover" onerror="this.src='/static/images/promosi-toko.png'" style="width: 100%; height: 100%; object-fit: cover;">
            <button class="absolute top-2 right-2 w-8 h-8 rounded-full bg-white/90 backdrop-blur-sm flex items-center justify-center text-slate-400 hover:text-red-500 transition-all btn-favorite-store ${favClass}" data-id="${s.id}" style="position: absolute; top: 8px; right: 8px; border: none; z-index: 10;">
              <i class="fa-${favClass ? 'solid' : 'regular'} fa-heart"></i>
            </button>
          </div>
          <div class="flex flex-col gap-1.5" style="display: flex; flex-direction: column; gap: 6px;">
            <span class="inline-block self-start px-2 py-0.5 bg-slate-50 text-[10px] font-extrabold text-[#16A34A] rounded" style="align-self: flex-start; background: #DCFCE7; color: #16A34A; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 6px;">${category}</span>
            <h4 class="font-extrabold text-slate-800 text-sm truncate" style="font-weight: 800; color: #0F172A; margin: 0; font-size: 14px;">${s.store_name}</h4>
            <span class="text-xs text-slate-400 font-medium" style="font-size: 12px; color: #64748B; font-weight: 500;">${city}</span>
            <div class="flex items-center gap-3 text-[11px] text-slate-500 mt-1" style="display: flex; align-items: center; gap: 12px; font-size: 11px; color: #64748B; font-weight: 600;">
              <span class="flex items-center gap-1 text-amber-500"><i class="fa-solid fa-star"></i> ${rating}</span>
              <span class="flex items-center gap-1"><i class="fa-regular fa-clock"></i> ${deliveryTime}</span>
              <span class="flex items-center gap-1 text-primary"><i class="fa-solid fa-truck-fast"></i> Gratis Ongkir</span>
            </div>
          </div>
        `;

        card.addEventListener('click', () => {
          window.location.href = `/stores/${s.id}/`;
        });

        card.querySelector('.btn-favorite-store')?.addEventListener('click', (e) => {
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
      { id: 'storeCheckRating', prop: 'ratingOnly' }
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
        const rating = Number(s.rating_avg || 4.7).toFixed(1);
        const distance = storeCatalogState.coords ? '0.8 km' : '0.5 km';
        const deliveryTime = s.is_open ? '10-20 min' : 'Tutup';
        const logo = s.logo || `/static/images/store-icon-T.png`;
        const banner = s.banner || `/static/images/promosi-toko.png`;
        const favClass = s.is_favorite ? 'is-fav' : '';
        const openStatusClass = s.is_open ? 'bg-primary/10 text-primary' : 'bg-red-500/10 text-red-500';
        const openStatusText = s.is_open ? 'Buka' : 'Tutup';
        const category = s.category_name || (s.id === 1 ? 'Sembako' : 'Sayuran');
        const totalProducts = s.product_count || 150;
        
        const card = document.createElement('div');
        card.className = 'store-card bg-white rounded-3xl overflow-hidden border border-slate-100 flex flex-col shadow-sm relative group cursor-pointer';
        card.setAttribute('data-store-id', s.id);
        card.innerHTML = `
          <div class="relative h-48 overflow-hidden image-container">
            <img src="${banner}" alt="${s.store_name} Banner" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" onerror="this.src='/static/images/promosi-toko.png'">
            <div class="absolute top-4 left-4 ${openStatusClass} px-3 py-1 rounded-full flex items-center space-x-1 backdrop-blur-md">
              <div class="w-1.5 h-1.5 rounded-full ${s.is_open ? 'bg-primary animate-pulse' : 'bg-red-500'}"></div>
              <span class="text-[10px] font-extrabold">${openStatusText}</span>
            </div>
            <button class="absolute top-4 right-4 bg-white/80 backdrop-blur-md p-2 rounded-full text-slate-400 hover:text-red-500 transition-colors btn-favorite-store ${favClass}" data-id="${s.id}">
              <i class="fa-${favClass ? 'solid' : 'regular'} fa-heart"></i>
            </button>
            <div class="absolute -bottom-6 left-4 w-12 h-12 rounded-full bg-white border-2 border-white overflow-hidden shadow-md">
              <img src="${logo}" alt="${s.store_name} Logo" class="w-full h-full object-cover">
            </div>
          </div>
          <div class="pt-8 px-4 pb-4 flex flex-col flex-1">
            <div class="flex items-center gap-1 mb-1">
              <h3 class="font-bold text-slate-800 text-sm truncate flex-1">${s.store_name}</h3>
              <i class="fa-solid fa-circle-check text-primary text-xs" title="Verified Store"></i>
            </div>
            <span class="inline-block self-start px-2 py-0.5 bg-slate-50 text-[10px] font-bold text-[#16A34A] rounded mb-2">${category}</span>
            <div class="flex items-center gap-2 text-[10px] text-slate-500 mb-4">
              <div class="flex items-center text-amber-500 font-bold">
                <i class="fa-solid fa-star mr-1"></i> ${rating} <span class="text-slate-400 font-normal ml-0.5">(128 ulasan)</span>
              </div>
              <span>•</span>
              <span class="font-bold text-slate-700">${distance}</span>
            </div>
            <div class="space-y-2 mb-4 text-[11px] text-slate-500">
              <div class="flex items-center justify-between">
                <span class="flex items-center"><i class="fa-solid fa-truck-fast mr-2"></i> ${deliveryTime}</span>
                <span class="text-primary font-bold">Gratis Ongkir</span>
              </div>
              <div class="flex items-center"><i class="fa-regular fa-clock mr-2"></i> ${s.open_time || '07:00'} - ${s.close_time || '21:00'} WIB</div>
              <div class="flex items-center"><i class="fa-solid fa-location-dot mr-2"></i> <span class="truncate">${s.address || s.city || 'Jakarta, ID'}</span></div>
              <div class="flex items-center"><i class="fa-solid fa-boxes-stacked mr-2"></i> ${totalProducts}+ Produk Tersedia</div>
            </div>
            <div class="mt-auto space-y-2">
              <button class="w-full bg-primary text-white py-2 rounded-xl font-bold text-xs hover:bg-[#15803d] transition-all btn-visit-store-action">Kunjungi Warung</button>
              <button class="w-full bg-white border border-slate-200 text-slate-500 py-2 rounded-xl font-bold text-xs hover:bg-slate-50 transition-colors btn-see-products-action">Lihat Produk</button>
            </div>
          </div>
        `;

        card.addEventListener('click', () => {
          window.location.href = `/stores/${s.id}/`;
        });

        card.querySelector('.btn-visit-store-action')?.addEventListener('click', (e) => {
          e.stopPropagation();
          window.location.href = `/stores/${s.id}/`;
        });

        card.querySelector('.btn-see-products-action')?.addEventListener('click', (e) => {
          e.stopPropagation();
          window.location.href = `/buyer/products/?store_id=${s.id}`;
        });

        card.querySelector('.btn-favorite-store')?.addEventListener('click', async (e) => {
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
        const rating = Number(p.rating_avg || 4.8).toFixed(1);
        
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
              <span>Terjual ${p.sold_count || 10}+</span>
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
      window.location.href = '/auth/login/?next=' + encodeURIComponent(window.location.pathname);
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
        window.location.href = '/auth/login/';
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
              var snapBaseUrl = window.WARUNGIO_SNAP_BASE_URL || 'https://app.sandbox.midtrans.com';
              script.src = snapBaseUrl + '/snap/snap.js';
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
  await Promise.all([loadStores(), loadFreshProducts(), loadBestDeals()]);

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
