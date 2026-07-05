/**
 * Cart page - Warungio
 * Manages cart: list items, update qty, remove items, checkout flow.
 */
document.addEventListener('DOMContentLoaded', async () => {
  if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
    window.location.href = '/auth/login/?next=' + encodeURIComponent(window.location.pathname);
    return;
  }

  // ── DOM refs ──
  const cartContainer = document.getElementById('cartContainer');
  const cartItemsEl = document.getElementById('cartItems');
  const emptyState = document.getElementById('emptyState');
  const loadingState = document.getElementById('loadingState');
  const cartStatus = document.getElementById('cartStatus');
  const itemCount = document.getElementById('itemCount');
  const summaryCount = document.getElementById('summaryCount');
  const summarySubtotal = document.getElementById('summarySubtotal');
  const summaryTotal = document.getElementById('summaryTotal');
  const checkoutBtn = document.getElementById('checkoutBtn');
  const clearCartBtn = document.getElementById('clearCartBtn');
  const toast = document.getElementById('toast');

  let cartData = [];

  function showToast(text, type) {
    // Delegate to shared utility — eliminates duplicate code
    if (window.WarungioAuthUI) {
      WarungioAuthUI.showToast(text, type || 'success');
      return;
    }
    // Fallback if shared utility not available
    if (!toast) return;
    toast.textContent = text;
    toast.className = 'toast ' + (type || 'success');
    toast.classList.add('show');
    clearTimeout(toast._hide);
    toast._hide = setTimeout(() => toast.classList.remove('show'), 3000);
  }

  function toRupiah(num) {
    return 'Rp ' + Number(num).toLocaleString('id-ID');
  }

  function renderStoreIcon() {
    return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>';
  }

  // ── Load Cart ──
  async function loadCart() {
    loadingState.style.display = 'block';
    cartContainer.style.display = 'none';
    emptyState.style.display = 'none';
    checkoutBtn.disabled = true;
    clearCartBtn.disabled = true;

    try {
      const data = await WarungioAPI.getCart();
      cartData = data.results || data || [];
      if (!Array.isArray(cartData)) cartData = [];

      if (cartData.length === 0) {
        loadingState.style.display = 'none';
        emptyState.style.display = 'flex';
        cartStatus.textContent = 'Keranjang kosong';
        itemCount.textContent = '0';
        return;
      }

      renderCart(cartData);
      updateSummary(cartData);
      loadingState.style.display = 'none';
      cartContainer.style.display = 'grid';
      cartStatus.textContent = cartData.length + ' item di keranjang';
      itemCount.textContent = cartData.length;
      checkoutBtn.disabled = false;
      clearCartBtn.disabled = false;
    } catch (err) {
      console.warn('Load cart fallback:', err);
      loadingState.style.display = 'none';
      emptyState.style.display = 'flex';
      emptyState.querySelector('p').textContent = 'Gagal memuat keranjang: ' + (err.message || 'Coba refresh halaman.');
      cartStatus.textContent = 'Gagal memuat';
    }
  }

  // ── Render Cart ──
  function renderCart(items) {
    // Group by store
    const grouped = {};
    items.forEach(item => {
      const storeId = item.store_id || 'unknown';
      const storeName = item.store_name || 'Warung';
      if (!grouped[storeId]) grouped[storeId] = { storeName, storeId, items: [] };
      grouped[storeId].items.push(item);
    });

    cartItemsEl.innerHTML = '';
    Object.values(grouped).forEach(group => {
      const groupDiv = document.createElement('div');
      groupDiv.className = 'store-group';
      groupDiv.innerHTML = '<div class="store-header">' +
        renderStoreIcon() +
        '<h3>' + escapeHtml(group.storeName) + '</h3></div>';

      group.items.forEach(item => {
        const photo = item.product_photo
          ? (item.product_photo.startsWith('http') ? '' : window.location.origin) + item.product_photo
          : WarungioAssets.img('vega-fresh.png');
        const name = item.product_name || 'Produk';
        const price = Number(item.product_price || item.price || 0);
        const qty = item.qty || 1;
        const subtotal = price * qty;

        const itemDiv = document.createElement('div');
        itemDiv.className = 'cart-item';
        itemDiv.dataset.cartId = item.id;
        itemDiv.innerHTML = `
          <img src="${photo}" alt="${escapeHtml(name)}" class="item-image" loading="lazy">
          <div class="item-details">
            <p class="item-name">${escapeHtml(name)}</p>
            <p class="item-price">${toRupiah(price)}</p>
            <p class="item-store">${escapeHtml(group.storeName)}</p>
          </div>
          <div class="item-qty">
            <button class="qty-btn qty-minus" data-id="${item.id}">-</button>
            <input type="number" class="qty-value" value="${qty}" min="1" max="${item.product_stock || 99}" data-id="${item.id}">
            <button class="qty-btn qty-plus" data-id="${item.id}">+</button>
          </div>
          <div class="item-subtotal">
            <div class="subtotal-label">Subtotal</div>
            <div class="subtotal-value">${toRupiah(subtotal)}</div>
          </div>
          <button class="btn-remove" data-id="${item.id}" title="Hapus">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>`;

        groupDiv.appendChild(itemDiv);
      });

      cartItemsEl.appendChild(groupDiv);
    });

    // ── Event Listeners ──
    document.querySelectorAll('.qty-minus').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.dataset.id;
        const input = document.querySelector(`.qty-value[data-id="${id}"]`);
        const val = parseInt(input.value) - 1;
        if (isNaN(val) || val < 1) return;
        await updateQty(id, val);
      });
    });

    document.querySelectorAll('.qty-plus').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.dataset.id;
        const input = document.querySelector(`.qty-value[data-id="${id}"]`);
        const max = parseInt(input.max);
        const val = parseInt(input.value) + 1;
        if (val > max) {
          showToast('Stok tidak mencukupi. Maksimal ' + max, 'error');
          return;
        }
        await updateQty(id, val);
      });
    });

    document.querySelectorAll('.qty-value').forEach(input => {
      input.addEventListener('change', async () => {
        const id = input.dataset.id;
        let val = parseInt(input.value);
        const max = parseInt(input.max);
        if (isNaN(val) || val < 1) val = 1;
        if (val > max) val = max;
        input.value = val;
        await updateQty(id, val);
      });
    });

    document.querySelectorAll('.btn-remove').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.dataset.id;
        await removeItem(id);
      });
    });
  }

  async function updateQty(itemId, qty) {
    try {
      await WarungioAPI.updateCartItem(itemId, { qty });
      showToast('Jumlah berhasil diubah');
      await loadCart();
    } catch (err) {
      showToast('Gagal mengubah jumlah: ' + (err.message || 'Coba lagi'), 'error');
    }
  }

  async function removeItem(itemId) {
    try {
      await WarungioAPI.removeCartItem(itemId);
      showToast('Item berhasil dihapus');
      await loadCart();
    } catch (err) {
      showToast('Gagal menghapus item: ' + (err.message || 'Coba lagi'), 'error');
    }
  }

  // ── Update Summary ──
  function updateSummary(items) {
    const count = items.reduce((sum, i) => sum + i.qty, 0);
    const subtotal = items.reduce((sum, i) => sum + (Number(i.product_price || i.price || 0) * i.qty), 0);
    summaryCount.textContent = count;
    summarySubtotal.textContent = toRupiah(subtotal);
    summaryTotal.textContent = toRupiah(subtotal);
  }

  // ── Clear Cart ──
  clearCartBtn.addEventListener('click', async () => {
    if (!confirm('Kosongkan semua item di keranjang?')) return;
    try {
      await WarungioAPI.clearCart();
      showToast('Keranjang berhasil dikosongkan');
      await loadCart();
    } catch (err) {
      showToast('Gagal mengosongkan: ' + (err.message || 'Coba lagi'), 'error');
    }
  });

  // ── Checkout ──
  checkoutBtn.addEventListener('click', () => {
    const ids = cartData.map(i => i.id);
    if (ids.length === 0) return;
    window.location.href = '/buyer/checkout/?items=' + encodeURIComponent(ids.join(','));
  });

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ── Init ──
  await loadCart();
});
