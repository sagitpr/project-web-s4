/**
 * My Products page - Warungio (Seller)
 * Manage products via Django REST API.
 */
document.addEventListener('DOMContentLoaded', async () => {
  if (window.WarungioAuth && window.WarungioAuth.requireVerified && window.WarungioAuth.requireVerified()) {
    return;
  }

  const productTable = document.getElementById('product-table') || document.querySelector('.product-table tbody');
  const addForm = document.getElementById('add-product-form');
  const editForm = document.getElementById('edit-product-form');
  const searchInput = document.getElementById('search-product');
  const categoryFilter = document.getElementById('category-filter');
  const messageEl = document.getElementById('form-message');
  const modal = document.getElementById('edit-modal');

  function setMsg(text, type = 'error') {
    if (!messageEl) return;
    messageEl.textContent = text;
    messageEl.className = 'form-message ' + type;
    messageEl.style.display = 'block';
    setTimeout(() => { messageEl.style.display = 'none'; }, 5000);
  }

  // ── Category cache (loaded from API) ──
  let categoriesCache = [];

  async function loadCategories() {
    try {
      const data = await WarungioAPI.getCategories();
      categoriesCache = Array.isArray(data) ? data : (data.results || []);
      // Populate category filter dropdown
      const filterEl = document.getElementById('category-filter');
      if (filterEl) {
        filterEl.innerHTML = '<option value="">Semua Kategori</option>';
        categoriesCache.forEach(function(c) {
          filterEl.innerHTML += '<option value="' + c.id + '">' + (c.category_name || c.name) + '</option>';
        });
      }
      // Populate form category select
      const catSelect = document.getElementById('productCategory');
      if (catSelect) {
        catSelect.innerHTML = '<option value="">Pilih kategori</option>';
        categoriesCache.forEach(function(c) {
          catSelect.innerHTML += '<option value="' + c.id + '">' + (c.category_name || c.name) + '</option>';
        });
      }
    } catch (err) {
      console.warn('Load categories fallback:', err);
    }
  }

  // ── Load products ──
  async function loadProducts(search = '', category = '') {
    if (!productTable) return;
    try {
      var params = { page: 1, pageSize: 50 };
      if (search) params.search = search;
      if (category) params.category = category;

      var data = await WarungioAPI.getMyProducts(params);
      productTable.innerHTML = '';

      const results = Array.isArray(data) ? data : (data.results || []);
      if (results.length > 0) {
        results.forEach(function(p) {
          const status = p.stock > 0 ? '<span class="status-green">Tersedia</span>' : '<span class="status-red">Habis</span>';
          const tr = document.createElement('tr');
          const isActiveDisplay = p.is_active !== false;
          var activeBtnClass = isActiveDisplay ? 'btn-toggle' : 'btn-toggle inactive';
          var activeBtnIcon = isActiveDisplay ? '<i class="fa-solid fa-eye"></i>' : '<i class="fa-solid fa-eye-slash"></i>';
          var activeBtnText = isActiveDisplay ? 'Aktif' : 'Nonaktif';
          tr.innerHTML = '\
            <td><img src="' + (p.product_photo_url || p.image || '/static/images/vega-fresh.png') + '" width="50" height="50" style="object-fit:cover;border-radius:8px;" /></td>\
            <td><b>' + (p.product_name || p.name) + '</b></td>\
            <td>' + (p.category_name || p.category || '-') + '</td>\
            <td>Rp ' + Number(p.price).toLocaleString('id-ID') + '</td>\
            <td>' + (p.stock || 0) + '</td>\
            <td>' + status + '</td>\
            <td>' + (p.average_rating ? '\u2605' + Number(p.average_rating).toFixed(1) : '-') + '</td>\
            <td>\
              <button class="' + activeBtnClass + '" data-id="' + p.id + '" data-active="' + isActiveDisplay + '" title="' + (isActiveDisplay ? 'Nonaktifkan' : 'Aktifkan') + ' produk">' + activeBtnIcon + ' ' + activeBtnText + '</button>\
              <button class="btn-edit" data-id="' + p.id + '"><i class="fa-solid fa-pen"></i></button>\
              <button class="btn-delete" data-id="' + p.id + '"><i class="fa-solid fa-trash"></i></button>\
            </td>';
          tr.querySelector('.btn-toggle')?.addEventListener('click', function() { toggleProductActive(p.id, p.product_name || p.name, isActiveDisplay); });
          productTable.appendChild(tr);
          tr.querySelector('.btn-edit')?.addEventListener('click', function() { openEditModal(p); });
          tr.querySelector('.btn-delete')?.addEventListener('click', function() { deleteProduct(p.id, p.product_name || p.name); });
        });
      } else {
        productTable.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:2rem;">Belum ada produk. Tambahkan produk baru!</td></tr>';
      }
    } catch (err) {
      console.warn('Load products fallback:', err);
      productTable.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:2rem;">Gagal memuat produk.</td></tr>';
    }
  }

  // ── Add product — kirim category_id (integer PK) ──
  addForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = addForm.querySelector('button[type="submit"]');
    btn.disabled = true; btn.textContent = 'Menyimpan...';

    try {
      const catId = parseInt(document.getElementById('productCategory')?.value) || null;
      const data = {
        product_name: document.getElementById('productName')?.value || addForm.querySelector('[name="product_name"]')?.value || '',
        description: addForm.querySelector('[name="description"]')?.value || '',
        price: parseFloat(addForm.querySelector('[name="price"]')?.value || 0),
        stock: parseInt(addForm.querySelector('[name="stock"]')?.value) || 0,
        category: catId,
        unit: addForm.querySelector('[name="unit"]')?.value || 'kg',
        is_active: true,
      };
      await WarungioAPI.createProduct(data);
      setMsg('Produk berhasil ditambahkan!', 'success');
      addForm.reset();
      loadProducts();
    } catch (err) {
      setMsg(err.message || 'Gagal menambahkan produk.');
    } finally {
      btn.disabled = false; btn.textContent = 'Tambah Produk';
    }
  });

  // ── Edit modal ──
  function openEditModal(product) {
    if (!modal) return;
    modal.style.display = 'flex';
    modal.querySelector('#edit-id').value = product.id;
    modal.querySelector('#edit-name').value = product.name;
    modal.querySelector('#edit-description').value = product.description || '';
    modal.querySelector('#edit-price').value = product.price;
    modal.querySelector('#edit-stock').value = product.stock || 0;
    modal.querySelector('#edit-category').value = product.category || '';
    modal.querySelector('#edit-unit').value = product.unit || 'kg';
    // Set is_active toggle
    const activeCheckbox = modal.querySelector('#edit-active');
    if (activeCheckbox) {
      activeCheckbox.checked = product.is_active !== false;
    }
  }

  editForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(editForm);
    const id = parseInt(fd.get('id'));
    const btn = editForm.querySelector('button[type="submit"]');
    btn.disabled = true; btn.textContent = 'Menyimpan...';

    try {
      const isActive = fd.get('is_active') === 'on';
      await WarungioAPI.updateProduct(id, {
        name: fd.get('name'),
        description: fd.get('description'),
        price: parseFloat(fd.get('price')),
        stock: parseInt(fd.get('stock')) || 0,
        category: fd.get('category'),
        unit: fd.get('unit') || 'kg',
        is_active: isActive,
      });
      setMsg('Produk berhasil diperbarui!', 'success');
      modal.style.display = 'none';
      loadProducts();
    } catch (err) {
      setMsg(err.message || 'Gagal memperbarui produk.');
    } finally {
      btn.disabled = false; btn.textContent = 'Simpan Perubahan';
    }
  });

  document.querySelector('.modal-close')?.addEventListener('click', () => {
    if (modal) modal.style.display = 'none';
  });
  window.addEventListener('click', (e) => {
    if (e.target === modal) modal.style.display = 'none';
  });

  // ── Toggle product active status ──
  async function toggleProductActive(id, name, currentlyActive) {
    const newActive = !currentlyActive;
    const action = newActive ? 'Aktifkan' : 'Nonaktifkan';
    if (!confirm(`${action} produk "${name}"?`)) return;
    try {
      await WarungioAPI.updateProduct(id, { is_active: newActive });
      setMsg(`Produk "${name}" berhasil ${newActive ? 'diaktifkan' : 'dinonaktifkan'}.`, 'success');
      loadProducts();
    } catch (err) {
      setMsg(err.message || `Gagal ${newActive ? 'mengaktifkan' : 'menonaktifkan'} produk.`);
    }
  }

  // ── Delete product ──
  async function deleteProduct(id, name) {
    if (!confirm('Hapus produk "' + name + '"? Tindakan ini tidak dapat dibatalkan.')) return;
    try {
      await WarungioAPI.deleteProduct(id);
      setMsg('Produk "' + name + '" berhasil dihapus.', 'success');
      loadProducts();
    } catch (err) {
      setMsg(err.message || 'Gagal menghapus produk.');
    }
  }

  // ── Search & filter ──
  searchInput?.addEventListener('input', () => loadProducts(searchInput.value, categoryFilter?.value));
  categoryFilter?.addEventListener('change', () => loadProducts(searchInput?.value, categoryFilter.value));

  // ── Load store profile ──
  async function loadStoreProfile() {
    if (!window.WarungioAPI) return;
    try {
      var store = await WarungioAPI.getMyStore();
      if (!store) return;
      var nameEl = document.getElementById('shopName');
      if (nameEl) nameEl.textContent = store.store_name || 'Warung Saya';
      var userEl = document.getElementById('userName');
      if (userEl) userEl.textContent = store.store_name || 'Seller';
      var avatarEl = document.getElementById('userAvatar');
      if (avatarEl && store.store_logo) avatarEl.src = store.store_logo;
    } catch (e) { /* keep defaults */ }
  }

  // ── Init ──
  loadCategories();
  loadProducts();
  loadStoreProfile();
});
