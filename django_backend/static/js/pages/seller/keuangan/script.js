/* Warungio Seller — Keuangan (Finance) Script
   Dashboard with balance overview, income chart (Chart.js),
   bank account management, withdrawal flow, transaction log.
   ============================================================ */

/* ── State ─────────────────────────────────────────────────── */
const state = {
  transactions: [],
  bankAccounts: [],
  currentPage: 1,
  pageSize: 15,
  currentTab: 'all',
  searchQuery: '',
  chartInstance: null,
};

/* ──── DOM refs ────────────────────────────────────────────── */
const $ = (id) => document.getElementById(id);
const dom = {
  totalBalance: $('finance-total-balance'),
  totalIncome: $('finance-total-income'),
  incomeTrend: $('income-trend-pct'),
  totalWithdrawal: $('finance-total-withdrawal'),
  withdrawalTrend: $('withdrawal-trend-pct'),
  heldBalance: $('finance-held-balance'),
  totalTransactions: $('finance-total-transactions'),
  breakdownAvailable: $('breakdown-available'),
  breakdownHeld: $('breakdown-held'),
  breakdownPending: $('breakdown-pending'),
  breakdownTotal: $('breakdown-total'),
  transactionsTbody: $('transactions-tbody'),
  emptyState: $('transactions-empty-state'),
  skeleton: $('transactions-skeleton'),
  paginationInfo: $('pagination-info'),
  paginationControls: $('pagination-controls'),
  bankAccountsList: $('bank-accounts-list'),
  manageBanksList: $('manage-banks-list'),
  periodSelect: $('finance-period-select'),
  searchInput: $('search-transaction'),
  chartCanvas: $('financeChart'),
};

/* ──── Initialize ─────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', async () => {
  await loadDashboard();
  await loadTransactions();
  await loadBankAccounts();

  // Event listeners
  dom.periodSelect?.addEventListener('change', loadDashboard);
  dom.searchInput?.addEventListener('input', debounce((e) => {
    state.searchQuery = e.target.value.trim().toLowerCase();
    state.currentPage = 1;
    renderTransactions();
  }, 300));

  // Modals
  $('btn-open-withdraw')?.addEventListener('click', () => openModal('withdraw-modal'));
  $('btn-close-withdraw-modal')?.addEventListener('click', () => closeModal('withdraw-modal'));
  $('btn-cancel-withdraw')?.addEventListener('click', () => closeModal('withdraw-modal'));
  $('btn-manage-bank')?.addEventListener('click', () => { renderManageBanks(); openModal('manage-banks-modal'); });
  $('btn-close-manage-modal')?.addEventListener('click', () => closeModal('manage-banks-modal'));
  $('btn-close-bank-modal')?.addEventListener('click', () => closeModal('bank-modal'));
  $('btn-cancel-bank-form')?.addEventListener('click', () => closeModal('bank-modal'));
  $('add-bank-link')?.addEventListener('click', () => openBankForm());
  $('btn-add-bank-from-manage')?.addEventListener('click', () => { closeModal('manage-banks-modal'); openBankForm(); });

  // Tabs
  document.querySelectorAll('#finance-tabs .tab-btn').forEach(btn => {
    btn.addEventListener('click', function () {
      document.querySelectorAll('#finance-tabs .tab-btn').forEach(b => b.classList.remove('active'));
      this.classList.add('active');
      state.currentTab = this.dataset.tab;
      state.currentPage = 1;
      renderTransactions();
    });
  });

  // Bank form submit
  $('bank-form')?.addEventListener('submit', saveBankAccount);
  // Withdraw form submit
  $('withdraw-form')?.addEventListener('submit', submitWithdraw);

  // Withdraw amount validation
  $('withdraw-amount-input')?.addEventListener('input', function () {
    const max = parseFloat(this.getAttribute('data-max') || '0');
    if (parseFloat(this.value) > max) this.value = max;
  });

  document.addEventListener('warungio:auth_ready', async () => {
    await loadDashboard();
    await loadTransactions();
    await loadBankAccounts();
  });
});

/* ──── Dashboard Data ─────────────────────────────────────── */
async function loadDashboard() {
  showSkeleton(true);
  try {
    const days = dom.periodSelect?.value || 30;
    const finance = await WarungioAPI.getFinanceSummary(days);
    updateDashboardUI(finance);
  } catch (e) {
    console.warn('Finance dashboard load failed:', e);
    // Show empty dashboard with zeros
    updateDashboardUI({});
  }
  showSkeleton(false);
}

function updateDashboardUI(data) {
  const fmt = (v) => WarungioAPI?.formatCurrency ? WarungioAPI.formatCurrency(v || 0) : `Rp ${(v || 0).toLocaleString('id-ID')}`;
  const pct = (v) => (v || 0).toFixed(1);

  if (dom.totalBalance) dom.totalBalance.textContent = fmt(data.total_balance);
  if (dom.totalIncome) dom.totalIncome.textContent = fmt(data.total_income);
  // income_trend may not be present from backend — compute from chart data if available
  if (dom.incomeTrend) {
    var trend = data.income_trend;
    if (trend === undefined && data.chart_data && Array.isArray(data.chart_data.income) && data.chart_data.income.length >= 2) {
      var inc = data.chart_data.income;
      var firstHalf = inc.slice(0, Math.floor(inc.length / 2)).reduce(function(s, v) { return s + v; }, 0);
      var secondHalf = inc.slice(Math.floor(inc.length / 2)).reduce(function(s, v) { return s + v; }, 0);
      trend = firstHalf > 0 ? ((secondHalf - firstHalf) / firstHalf) * 100 : 0;
    }
    dom.incomeTrend.innerHTML = '<i class="fa-solid fa-arrow-' + (trend >= 0 ? 'up' : 'down') + '"></i> ' + pct(trend) + '% dari periode sebelumnya';
  }
  if (dom.totalWithdrawal) dom.totalWithdrawal.textContent = fmt(data.total_withdrawals || data.total_withdrawal);
  if (dom.withdrawalTrend) {
    var wTrend = data.withdrawal_trend;
    if (wTrend === undefined) wTrend = 0;
    dom.withdrawalTrend.innerHTML = '<i class="fa-solid fa-arrow-' + (wTrend >= 0 ? 'up' : 'down') + '"></i> ' + pct(wTrend) + '% dari periode sebelumnya';
  }
  if (dom.heldBalance) dom.heldBalance.textContent = fmt(data.held_balance);
  if (dom.totalTransactions) dom.totalTransactions.textContent = (data.total_transactions || 0).toLocaleString('id-ID');
  if (dom.breakdownAvailable) dom.breakdownAvailable.textContent = fmt(data.available_balance);
  if (dom.breakdownHeld) dom.breakdownHeld.textContent = fmt(data.held_balance);
  if (dom.breakdownPending) dom.breakdownPending.textContent = fmt(data.total_pending_withdrawals || data.pending_withdrawal);
  if (dom.breakdownTotal) dom.breakdownTotal.textContent = fmt(data.total_balance);

  // Update withdraw modal
  const wInput = $('withdraw-amount-input');
  if (wInput) {
    wInput.max = data.available_balance || 0;
    wInput.setAttribute('max', data.available_balance || 0);
  }
  const wAvail = $('withdraw-available-info');
  if (wAvail) wAvail.textContent = 'Saldo tersedia: ' + fmt(data.available_balance);

  // Render chart
  renderChart(data.chart_data);
}

/* ──── Chart.js ────────────────────────────────────────────── */
function renderChart(chartData) {
  if (!dom.chartCanvas || !window.Chart) return;

  if (state.chartInstance) {
    state.chartInstance.destroy();
    state.chartInstance = null;
  }

  // Support both formats:
  // Backend format: { labels: [...], income: [...], withdrawal: [...] }
  // Old mock format: [{ date: ..., amount: ... }, ...]
  var labels, values;
  if (Array.isArray(chartData)) {
    // Old mock format (array of objects)
    labels = chartData.map(function(d) { return d.date || d.label || ''; });
    values = chartData.map(function(d) { return d.amount || d.value || 0; });
  } else if (chartData && chartData.labels) {
    // Real backend format
    labels = chartData.labels;
    values = chartData.income || [];
  } else {
    labels = [];
    values = [];
  }

  state.chartInstance = new Chart(dom.chartCanvas, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Pemasukan',
        data: values,
        borderColor: '#059669',
        backgroundColor: 'rgba(5, 150, 105, 0.08)',
        borderWidth: 2,
        fill: true,
        tension: 0.35,
        pointRadius: 3,
        pointBackgroundColor: '#059669',
        pointHoverRadius: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `Rp ${ctx.parsed.y.toLocaleString('id-ID')}`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { font: { size: 10 }, maxTicksLimit: 10 },
        },
        y: {
          beginAtZero: true,
          ticks: {
            font: { size: 10 },
            callback: (v) => `Rp${(v / 1000).toFixed(0)}k`,
          },
          grid: { color: 'rgba(0,0,0,0.05)' },
        },
      },
    },
  });
}

/* ──── Transactions ────────────────────────────────────────── */
async function loadTransactions() {
  try {
    const data = await WarungioAPI.getFinanceTransactions({
      page: state.currentPage,
      page_size: state.pageSize,
    });
    state.transactions = data.results || data || [];
  } catch (e) {
    console.warn('Transactions load failed:', e);
    state.transactions = [];
  }
  renderTransactions();
}

function renderTransactions() {
  let filtered = [...state.transactions];

  // Filter by tab
  if (state.currentTab !== 'all') {
    filtered = filtered.filter(t => t.type === state.currentTab);
  }

  // Filter by search
  if (state.searchQuery) {
    const q = state.searchQuery;
    filtered = filtered.filter(t =>
      (t.description || '').toLowerCase().includes(q) ||
      (t.category || '').toLowerCase().includes(q) ||
      (t.id || '').toString().includes(q)
    );
  }

  // Paginate
  const total = filtered.length;
  const totalPages = Math.max(1, Math.ceil(total / state.pageSize));
  const start = (state.currentPage - 1) * state.pageSize;
  const pageData = filtered.slice(start, start + state.pageSize);

  // Update UI
  if (dom.emptyState) dom.emptyState.style.display = pageData.length ? 'none' : 'block';
  if (dom.transactionsTbody) {
    if (pageData.length) {
      dom.transactionsTbody.innerHTML = pageData.map(t => {
        const statusClass = t.status === 'success' ? 'success' : t.status === 'pending' ? 'pending' : 'failed';
        // Handle both 'date' (mock) and 'created_at' (backend) field names
        var txDate = (t.date || t.created_at || '').slice(0, 10);
        // Handle negative amounts for withdrawals (backend returns signed amounts)
        var absAmount = Math.abs(t.amount || 0);
        var formattedAmount = (WarungioAPI?.formatCurrency ? WarungioAPI.formatCurrency(absAmount) : 'Rp ' + absAmount.toLocaleString('id-ID'));
        if (t.type === 'withdrawal' && t.amount < 0) {
          formattedAmount = '-' + formattedAmount;
        }
        return `<tr>
          <td>${txDate || '-'}</td>
          <td>${t.type_label || t.type || '-'}</td>
          <td>${t.description || '-'}</td>
          <td>${t.category || '-'}</td>
          <td>${t.method || '-'}</td>
          <td><strong>${formattedAmount}</strong></td>
          <td><span class="status-badge ${statusClass}">${t.status_label || t.status || '-'}</span></td>
          <td style="text-align:right"><button class="action-btn" onclick="viewTransaction(${t.id})">Detail</button></td>
        </tr>`;
      }).join('');
    } else {
      dom.transactionsTbody.innerHTML = '';
    }
  }

  // Pagination info
  if (dom.paginationInfo) {
    dom.paginationInfo.textContent = `Menampilkan ${total ? start + 1 : 0} - ${Math.min(start + state.pageSize, total)} dari ${total} transaksi`;
  }
  renderPagination(totalPages);
}

function renderPagination(totalPages) {
  if (!dom.paginationControls) return;
  let html = '';
  if (state.currentPage > 1) {
    html += `<button onclick="goToPage(${state.currentPage - 1})"><i class="fa-solid fa-chevron-left"></i></button>`;
  }
  for (let i = Math.max(1, state.currentPage - 2); i <= Math.min(totalPages, state.currentPage + 2); i++) {
    html += `<button class="${i === state.currentPage ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
  }
  if (state.currentPage < totalPages) {
    html += `<button onclick="goToPage(${state.currentPage + 1})"><i class="fa-solid fa-chevron-right"></i></button>`;
  }
  dom.paginationControls.innerHTML = html;
}

window.goToPage = (page) => {
  state.currentPage = page;
  loadTransactions();
};

function viewTransaction(id) {
  showToast(`Transaksi #${id} - Lihat detail lengkap di halaman laporan.`, 'info');
}

/* ──── Bank Accounts ───────────────────────────────────────── */
async function loadBankAccounts() {
  try {
    const data = await WarungioAPI.getBankAccounts();
    state.bankAccounts = data.results || data || [];
  } catch (e) {
    console.warn('Bank accounts load failed:', e);
    state.bankAccounts = [];
  }
  renderBankAccounts();
}

function renderBankAccounts() {
  if (!dom.bankAccountsList) return;
  if (state.bankAccounts.length) {
    dom.bankAccountsList.innerHTML = state.bankAccounts.map(acc => `
      <div class="bank-account-card">
        <div class="bank-icon">${(acc.bank_name || 'BNK').substring(0, 3).toUpperCase()}</div>
        <div class="bank-detail">
          <div class="bank-name">${acc.bank_name || '-'} ${acc.is_primary ? '<span class="bank-primary-badge">Utama</span>' : ''}</div>
          <div class="bank-account-number">${acc.account_number || '-'} a.n. ${acc.account_holder || '-'}</div>
        </div>
        <div class="bank-status ${acc.is_primary ? 'active' : ''}"></div>
      </div>
    `).join('');
  } else {
    dom.bankAccountsList.innerHTML = '<p style="text-align:center;padding:20px;color:var(--color-text-tertiary);font-size:13px">Belum ada rekening bank. Tambahkan untuk mulai menarik saldo.</p>';
  }

  // Update withdraw modal
  const primary = state.bankAccounts.find(a => a.is_primary) || state.bankAccounts[0];
  const destInfo = $('withdraw-destination-info');
  if (destInfo) {
    if (primary) {
      destInfo.innerHTML = `<div class="bank-account-card"><div class="bank-icon">${(primary.bank_name || 'BNK').substring(0, 3).toUpperCase()}</div><div class="bank-detail"><div class="bank-name">${primary.bank_name || '-'}</div><div class="bank-account-number">${primary.account_number || '-'} a.n. ${primary.account_holder || '-'}</div></div></div>`;
    } else {
      destInfo.innerHTML = '<p style="color:var(--color-text-tertiary);font-size:13px">Belum ada rekening tujuan. Tambahkan rekening terlebih dahulu.</p>';
    }
  }
}

function renderManageBanks() {
  if (!dom.manageBanksList) return;
  if (state.bankAccounts.length) {
    dom.manageBanksList.innerHTML = state.bankAccounts.map(acc => `
      <div class="bank-account-card">
        <div class="bank-icon">${(acc.bank_name || 'BNK').substring(0, 3).toUpperCase()}</div>
        <div class="bank-detail">
          <div class="bank-name">${acc.bank_name || '-'} ${acc.is_primary ? '<span class="bank-primary-badge">Utama</span>' : ''}</div>
          <div class="bank-account-number">${acc.account_number || '-'} a.n. ${acc.account_holder || '-'}</div>
        </div>
        <button class="btn-delete-bank" onclick="deleteBankAccount(${acc.id})"><i class="fa-solid fa-trash-can"></i></button>
      </div>
    `).join('');
  } else {
    dom.manageBanksList.innerHTML = '<p style="text-align:center;padding:20px;color:var(--color-text-tertiary);font-size:13px">Belum ada rekening bank.</p>';
  }
}

function openBankForm(account) {
  $('bank-modal-title').textContent = account ? 'Edit Rekening Bank' : 'Tambah Rekening Bank';
  $('bank-account-id').value = account?.id || '';
  $('bank-select').value = account?.bank_name || '';
  $('account-number-input').value = account?.account_number || '';
  $('account-holder-input').value = account?.account_holder || '';
  $('is-primary-checkbox').checked = account?.is_primary || false;
  openModal('bank-modal');
}

async function saveBankAccount(e) {
  e.preventDefault();
  const data = {
    bank_name: $('bank-select').value,
    account_number: $('account-number-input').value,
    account_holder: $('account-holder-input').value,
    is_primary: $('is-primary-checkbox').checked,
  };

  if (!data.bank_name || !data.account_number || !data.account_holder) {
    showToast('Harap isi semua field rekening bank.', 'error');
    return;
  }

  try {
    const id = $('bank-account-id').value;
    if (id) {
      await WarungioAPI.updateBankAccount(id, data);
      showToast('Rekening berhasil diperbarui.', 'success');
    } else {
      await WarungioAPI.createBankAccount(data);
      showToast('Rekening berhasil ditambahkan.', 'success');
    }
    closeModal('bank-modal');
    await loadBankAccounts();
  } catch (e) {
    showToast('Gagal menyimpan rekening. Silakan coba lagi.', 'error');
  }
}

async function deleteBankAccount(id) {
  if (!confirm('Hapus rekening ini?')) return;
  try {
    await WarungioAPI.deleteBankAccount(id);
    showToast('Rekening berhasil dihapus.', 'success');
    await loadBankAccounts();
    renderManageBanks();
  } catch (e) {
    showToast('Gagal menghapus rekening.', 'error');
  }
}

/* ──── Withdraw ────────────────────────────────────────────── */
async function submitWithdraw(e) {
  e.preventDefault();
  const amount = parseFloat($('withdraw-amount-input')?.value || 0);
  if (amount < 10000) {
    showToast('Minimal penarikan Rp 10.000.', 'error');
    return;
  }
  try {
    await WarungioAPI.submitWithdrawal({ amount });
    showToast('Permintaan penarikan berhasil dikirim.', 'success');
    closeModal('withdraw-modal');
    await loadDashboard();
    await loadTransactions();
  } catch (e) {
    showToast('Gagal mengirim permintaan penarikan.', 'error');
  }
}

/* ──── Utility ─────────────────────────────────────────────── */
function openModal(id) {
  const el = $(id);
  if (el) el.style.display = 'flex';
}

function closeModal(id) {
  const el = $(id);
  if (el) el.style.display = 'none';
}

function showSkeleton(show) {
  if (dom.skeleton) dom.skeleton.style.display = show ? 'block' : 'none';
  if (dom.transactionsTbody) dom.transactionsTbody.style.display = show ? 'none' : '';
}

function showToast(msg, type = 'success') {
  if (window.WarungioToast) {
    if (type === 'error') WarungioToast.error(msg);
    else if (type === 'info') WarungioToast.info(msg);
    else WarungioToast.success(msg);
    return;
  }
  // Fallback if WarungioToast not loaded
  const toast = $('toast-notification');
  if (!toast) return;
  toast.textContent = msg;
  toast.className = 'toast ' + type;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3000);
}

function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}
