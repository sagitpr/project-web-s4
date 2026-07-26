/**
 * My Products page - Warungio (Seller)
 * Manage products via Django REST API with optimistic UI checks.
 */
document.addEventListener('DOMContentLoaded', async () => {
  // Auth check
  if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
    window.location.href = '/?next=' + encodeURIComponent(window.location.pathname);
    return;
  }

  const tbody = document.getElementById('product-tbody');
  const emptyState = document.getElementById('product-empty-state');
  const searchInput = document.getElementById('search-product');
  const categoryFilter = document.getElementById('category-filter');
  
  // Modal DOM Elements
  const editModal = document.getElementById('edit-modal');
  const productForm = document.getElementById('product-form');
  const modalTitle = document.getElementById('modal-title');
  const btnAddProduct = document.getElementById('btn-add-product');
  
  // Delete confirm modal DOM
  const confirmModal = document.getElementById('confirm-modal');
  const confirmModalText = document.getElementById('confirm-modal-text');
  const btnConfirmCancel = document.getElementById('btn-confirm-cancel');
  const btnConfirmDelete = document.getElementById('btn-confirm-delete');

  let productsData = [];
  let deleteTargetId = null;

  function toRupiah(num) {
    return 'Rp ' + Number(num).toLocaleString('id-ID');
  }

  // Load and render products from backend
  async function fetchProducts() {
    try {
      const params = {};
      const search = searchInput?.value.trim();
      const category = categoryFilter?.value;
      
      if (search) params.search = search;
      if (category) params.category = category;

      const res = await WarungioAPI.getMyProducts(params);
      productsData = Array.isArray(res) ? res : (res.results || []);
      
      updateMetrics();
      renderTable();
    } catch (err) {
      console.warn('Failed to fetch products:', err);
      productsData = [];
      renderTable();
    }
  }

  // Calculate statistics metrics
  function updateMetrics() {
    const metrics = { total: 0, passedQC: 0, sufficientStock: 0, autoSelected: 0, failedChecks: 0 };
    
    productsData.forEach(p => {
      metrics.total++;
      
      // QC passed logic
      const score = p.quality_score || 85;
      if (score >= 70) {
        metrics.passedQC++;
      } else {
        metrics.failedChecks++;
      }
      
      // Stock logic
      const stock = Number(p.stock || 0);
      if (stock > 10) {
        metrics.sufficientStock++;
      } else {
        metrics.failedChecks++;
      }
      
      // Auto selected eligibility
      if (score >= 80 && stock > 5) {
        metrics.autoSelected++;
      }
    });

    const setMetricText = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };

    setMetricText('metric-total', metrics.total);
    setMetricText('metric-passed-qc', metrics.passedQC);
    setMetricText('metric-sufficient-stock', metrics.sufficientStock);
    setMetricText('metric-auto-selected', metrics.autoSelected);
    setMetricText('metric-failed-checks', metrics.failedChecks);
  }

  // Render products inside table
  function renderTable() {
    if (!tbody) return;
    tbody.innerHTML = '';

    if (productsData.length === 0) {
      if (emptyState) emptyState.style.display = 'block';
      return;
    }

    if (emptyState) emptyState.style.display = 'none';

    productsData.forEach(p => {
      const id = p.id;
      const sku = `WRG-PROD-${id}`;
      const name = p.product_name || p.name || 'Produk';
      const category = p.category_name || p.category || '-';
      const photo = p.product_photo || p.image || WarungioAssets.img('vega-fresh.png');
      const price = toRupiah(p.price || 0);
      const stock = Number(p.stock || 0);
      const score = p.quality_score || 85;

      // Quality badge
      let qualityBadge = `<span style="color:#b45309;font-weight:700;">Cukup (${score}/100)</span>`;
      if (score >= 90) {
        qualityBadge = `<span style="color:#15803d;font-weight:700;">Sangat Baik (${score}/100)</span>`;
      } else if (score >= 75) {
        qualityBadge = `<span style="color:#16a34a;font-weight:700;">Baik (${score}/100)</span>`;
      } else if (score < 50) {
        qualityBadge = `<span style="color:#b91c1c;font-weight:700;">Buruk (${score}/100)</span>`;
      }

      // Stock status pill
      let stockPill = `<span class="status-pill status-green" style="cursor: pointer;" title="Klik untuk tambah stok">${stock} Pcs</span>`;
      if (stock <= 0) {
        stockPill = `<span class="status-pill status-red" style="cursor: pointer;" title="Klik untuk tambah stok">Habis (0)</span>`;
      } else if (stock <= 5) {
        stockPill = `<span class="status-pill status-yellow" style="cursor: pointer;" title="Klik untuk tambah stok">Kritis (${stock})</span>`;
      }

      // Pipeline status mapping
      let pipelineText = '4. Auto Seleksi';
      let pipelineClass = 'status-blue';
      if (score < 50) {
        pipelineText = 'QC Gagal';
        pipelineClass = 'status-red';
      } else if (stock <= 0) {
        pipelineText = 'Stok Kosong';
        pipelineClass = 'status-red';
      } else if (score >= 90 && stock > 20) {
        pipelineText = '5. Tayang';
        pipelineClass = 'status-green';
      }

      // Auto selected badge
      const autoSelected = (score >= 80 && stock > 5) 
        ? '<span class="status-pill status-green">Lolos</span>' 
        : '<span class="status-pill status-yellow">Tertunda</span>';

      const tr = document.createElement('tr');
      tr.style.borderBottom = '1px solid var(--line)';
      tr.innerHTML = `
        <td style="padding: 14px 16px;"><img src="${photo}" style="width: 48px; height: 48px; border-radius: 8px; object-fit: cover;" alt="" /></td>
        <td style="padding: 14px 16px;">
          <div style="font-weight: 700; color: var(--text);">${name}</div>
          <div style="font-size: 11px; color: var(--muted);">${sku}</div>
        </td>
        <td style="padding: 14px 16px; color: var(--text); font-weight: 600;">${category}</td>
        <td style="padding: 14px 16px;">${qualityBadge}</td>
        <td style="padding: 14px 16px;">${stockPill}</td>
        <td style="padding: 14px 16px;"><span class="status-pill ${pipelineClass}" style="padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 700;">${pipelineText}</span></td>
        <td style="padding: 14px 16px;">${autoSelected}</td>
        <td style="padding: 14px 16px; text-align: right;">
          <button class="btn-edit" style="background: none; border: none; font-size: 14px; color: var(--muted); cursor: pointer; margin-right: 12px;" title="Ubah Produk"><i class="fa-solid fa-pen"></i></button>
          <button class="btn-delete" style="background: none; border: none; font-size: 14px; color: #ef4444; cursor: pointer;" title="Hapus Produk"><i class="fa-solid fa-trash"></i></button>
        </td>
      `;

      tbody.appendChild(tr);

      // Event binds
      tr.querySelector('.btn-edit')?.addEventListener('click', () => openEditModal(p));
      tr.querySelector('.btn-delete')?.addEventListener('click', () => openDeleteConfirm(p));
      
      // Direct stock clicking action
      tr.querySelector('.status-pill')?.addEventListener('click', () => promptRestock(p));
    });
  }

  // Prompt seller to add stock directly
  async function promptRestock(product) {
    const amountStr = prompt(`Masukkan jumlah stok baru untuk "${product.product_name || product.name}":`, product.stock || 0);
    if (amountStr === null) return;
    
    const amount = parseInt(amountStr);
    if (isNaN(amount) || amount < 0) {
      alert('Jumlah stok harus berupa angka positif.');
      return;
    }

    // Wait for backend validation (optimistic UI flow constraints)
    try {
      await WarungioAPI.updateProduct(product.id, { stock: amount });
      window.WarungioToast?.show('Stok produk berhasil diperbarui.', 'success');
      fetchProducts();
    } catch (err) {
      window.WarungioToast?.show(err.message || 'Gagal memperbarui stok.', 'error');
    }
  }

  // Open edit product details modal
  function openEditModal(product = null) {
    if (!editModal) return;
    editModal.style.display = 'flex';
    
    if (product) {
      modalTitle.textContent = 'Edit Informasi Produk';
      document.getElementById('edit-id').value = product.id;
      document.getElementById('edit-name').value = product.product_name || product.name;
      document.getElementById('edit-category').value = product.category_name || product.category || '';
      document.getElementById('edit-price').value = Math.round(product.price || 0);
      document.getElementById('edit-stock').value = product.stock || 0;
      document.getElementById('edit-unit').value = product.unit || 'kg';
      document.getElementById('edit-description').value = product.description || '';
    } else {
      modalTitle.textContent = 'Tambah Produk Baru';
      productForm.reset();
      document.getElementById('edit-id').value = '';
    }
  }

  // Close modals handles
  const closeModals = () => {
    if (editModal) editModal.style.display = 'none';
    if (confirmModal) confirmModal.style.display = 'none';
    deleteTargetId = null;
  };

  document.querySelectorAll('.modal-close').forEach(btn => btn.addEventListener('click', closeModals));

  // Edit / Add form submits
  productForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('edit-id').value;
    const isEdit = !!id;

    const data = {
      product_name: document.getElementById('edit-name').value.trim(),
      category: document.getElementById('edit-category').value.trim(),
      price: parseFloat(document.getElementById('edit-price').value),
      stock: parseInt(document.getElementById('edit-stock').value) || 0,
      unit: document.getElementById('edit-unit').value.trim(),
      description: document.getElementById('edit-description').value.trim()
    };

    const submitBtn = productForm.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Menyimpan...';

    try {
      if (isEdit) {
        await WarungioAPI.updateProduct(Number(id), data);
        window.WarungioToast?.show('Informasi produk berhasil diperbarui.', 'success');
      } else {
        await WarungioAPI.createProduct(data);
        window.WarungioToast?.show('Produk baru berhasil ditambahkan.', 'success');
      }
      closeModals();
      fetchProducts();
    } catch (err) {
      window.WarungioToast?.show(err.message || 'Gagal menyimpan produk.', 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Simpan';
    }
  });

  // Delete workflow controls (Wait for backend confirmation constraint)
  function openDeleteConfirm(product) {
    deleteTargetId = product.id;
    if (confirmModalText) {
      confirmModalText.textContent = `Apakah Anda yakin ingin menghapus produk "${product.product_name || product.name}"? Tindakan ini tidak dapat dibatalkan.`;
    }
    if (confirmModal) confirmModal.style.display = 'flex';
  }

  btnConfirmCancel?.addEventListener('click', closeModals);

  btnConfirmDelete?.addEventListener('click', async () => {
    if (!deleteTargetId) return;

    btnConfirmDelete.disabled = true;
    btnConfirmDelete.textContent = 'Menghapus...';

    try {
      await WarungioAPI.deleteProduct(deleteTargetId);
      window.WarungioToast?.show('Produk berhasil dihapus.', 'success');
      closeModals();
      fetchProducts();
    } catch (err) {
      window.WarungioToast?.show(err.message || 'Gagal menghapus produk.', 'error');
    } finally {
      btnConfirmDelete.disabled = false;
      btnConfirmDelete.textContent = 'Hapus';
    }
  });

  btnAddProduct?.addEventListener('click', () => openEditModal(null));

  // Category and query event search binds
  categoryFilter?.addEventListener('change', fetchProducts);
  searchInput?.addEventListener('input', fetchProducts);

  // Initialize data load
  fetchProducts();
});
