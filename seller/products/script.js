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

  // ── Load products ──
  async function loadProducts(search = '', category = '') {
    if (!productTable) return;
    try {
      const params = { page: 1, pageSize: 50 };
      if (search) params.search = search;
      if (category) params.category = category;

      const data = await WarungioAPI.getProducts(params);
      productTable.innerHTML = '';

      if (data.results && data.results.length > 0) {
        data.results.forEach(p => {
          const status = p.stock > 0 ? '<span class="status-green">Tersedia</span>' : '<span class="status-red">Habis</span>';
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td><img src="${p.image || WarungioAssets.img('vega-fresh.png')}" width="50" height="50" style="object-fit:cover;border-radius:8px;" /></td>
            <td><b>${p.name}</b></td>
            <td>${p.category_name || p.category || '-'}</td>
            <td>Rp ${Number(p.price).toLocaleString('id-ID')}</td>
            <td>${p.stock || 0}</td>
            <td>${status}</td>
            <td>${p.average_rating ? '★' + Number(p.average_rating).toFixed(1) : '-'}</td>
            <td>
              <button class="btn-edit" data-id="${p.id}"><i class="fa-solid fa-pen"></i></button>
              <button class="btn-delete" data-id="${p.id}"><i class="fa-solid fa-trash"></i></button>
            </td>`;
          productTable.appendChild(tr);

          tr.querySelector('.btn-edit')?.addEventListener('click', () => openEditModal(p));
          tr.querySelector('.btn-delete')?.addEventListener('click', () => deleteProduct(p.id, p.name));
        });
      } else {
        productTable.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:2rem;">Belum ada produk. Tambahkan produk baru!</td></tr>';
      }
    } catch (err) {
      console.warn('Load products fallback:', err);
      productTable.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:2rem;">Gagal memuat produk.</td></tr>';
    }
  }

  // ── Add product ──
  addForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(addForm);
    const btn = addForm.querySelector('button[type="submit"]');
    btn.disabled = true; btn.textContent = 'Menyimpan...';

    try {
      const data = {
        name: fd.get('name'),
        description: fd.get('description'),
        price: parseFloat(fd.get('price')),
        stock: parseInt(fd.get('stock')) || 0,
        category: fd.get('category'),
        unit: fd.get('unit') || 'kg',
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
  }

  editForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(editForm);
    const id = parseInt(fd.get('id'));
    const btn = editForm.querySelector('button[type="submit"]');
    btn.disabled = true; btn.textContent = 'Menyimpan...';

    try {
      await WarungioAPI.updateProduct(id, {
        name: fd.get('name'),
        description: fd.get('description'),
        price: parseFloat(fd.get('price')),
        stock: parseInt(fd.get('stock')) || 0,
        category: fd.get('category'),
        unit: fd.get('unit') || 'kg',
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

  // ── Init ──
  loadProducts();
});
