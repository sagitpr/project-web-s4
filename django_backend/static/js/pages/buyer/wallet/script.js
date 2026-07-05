/**
 * Wallet page - Warungio
 * Menampilkan saldo dompet, riwayat transaksi, dan top-up.
 */
(function () {
  'use strict';

  if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
    window.location.href = '/auth/login/?next=' + encodeURIComponent(window.location.pathname);
    return;
  }

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const balanceEl = $('#walletBalance');
  const balanceFormattedEl = $('#walletBalanceFormatted');
  const transactionsList = $('#transactionsList');
  const loadingState = $('#loadingState');
  const emptyState = $('#emptyState');
  const topUpForm = $('#topUpForm');
  const topUpInput = $('#topUpAmount');
  const topUpBtn = $('#topUpBtn');
  const toastEl = $('#toast');

  function showToast(text, type) {
    // Delegate to shared utility
    if (window.WarungioAuthUI) {
      WarungioAuthUI.showToast(text, type || 'success');
      return;
    }
    // Fallback
    if (!toastEl) return;
    toastEl.textContent = text;
    toastEl.className = 'toast ' + (type || 'success');
    toastEl.classList.add('show');
    clearTimeout(toastEl._hide);
    toastEl._hide = setTimeout(() => toastEl.classList.remove('show'), 3000);
  }

  function toRupiah(num) {
    return 'Rp ' + Number(num).toLocaleString('id-ID');
  }

  function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleDateString('id-ID', {
        day: 'numeric', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      });
    } catch (e) { return dateStr; }
  }

  async function loadBalance() {
    try {
      const data = await WarungioAPI.getWalletBalance();
      if (balanceEl) balanceEl.textContent = data.balance_formatted || toRupiah(data.balance);
      if (balanceFormattedEl) balanceFormattedEl.textContent = data.balance_formatted || toRupiah(data.balance);
    } catch (err) {
      console.warn('Wallet balance load error:', err);
      if (balanceEl) balanceEl.textContent = 'Rp 0';
    }
  }

  async function loadTransactions(page) {
    page = page || 1;
    if (loadingState) loadingState.style.display = 'block';
    if (emptyState) emptyState.style.display = 'none';
    if (transactionsList) transactionsList.innerHTML = '';

    try {
      const data = await WarungioAPI.getWalletTransactions({ page: page, page_size: 20 });
      const transactions = data.results || data || [];

      if (loadingState) loadingState.style.display = 'none';

      if (transactions.length === 0) {
        if (emptyState) emptyState.style.display = 'block';
        return;
      }

      if (!transactionsList) return;
      transactionsList.innerHTML = transactions.map(function (tx) {
        const isCredit = tx.tx_type === 'topup' || tx.tx_type === 'bonus' || tx.tx_type === 'refund';
        const sign = isCredit ? '+' : '-';
        const color = isCredit ? 'text-green-600' : 'text-red-600';
        const typeLabels = {
          topup: 'Top Up', payment: 'Pembayaran', refund: 'Refund',
          withdrawal: 'Penarikan', bonus: 'Bonus', adjustment: 'Penyesuaian',
        };
        return '<div class="transaction-row">' +
          '<div class="tx-info">' +
            '<span class="tx-type">' + (typeLabels[tx.tx_type] || tx.tx_type) + '</span>' +
            '<span class="tx-desc">' + (tx.description || '') + '</span>' +
            '<span class="tx-date">' + formatDate(tx.created_at) + '</span>' +
          '</div>' +
          '<div class="tx-amount ' + color + '">' +
            sign + ' ' + toRupiah(tx.amount) +
          '</div>' +
        '</div>';
      }).join('');
    } catch (err) {
      console.warn('Wallet transactions load error:', err);
      if (loadingState) loadingState.style.display = 'none';
      if (emptyState) emptyState.style.display = 'block';
    }
  }

  // Top-up handler
  topUpForm?.addEventListener('submit', async function (e) {
    e.preventDefault();
    const amount = parseInt(topUpInput?.value);
    if (!amount || amount < 10000) {
      showToast('Minimal top-up Rp 10.000', 'error');
      return;
    }
    if (topUpBtn) { topUpBtn.disabled = true; topUpBtn.textContent = 'Memproses...'; }
    try {
      const data = await WarungioAPI.topUpWallet(amount);
      showToast('Top-up berhasil! Silakan selesaikan pembayaran.', 'success');
      await loadBalance();
      await loadTransactions();
      if (topUpInput) topUpInput.value = '';
    } catch (err) {
      showToast(err.message || 'Gagal top-up', 'error');
    } finally {
      if (topUpBtn) { topUpBtn.disabled = false; topUpBtn.textContent = 'Top Up'; }
    }
  });

  // Init
  loadBalance();
  loadTransactions();
})();
