/**
 * Warungio Format Utilities
 */
(function () {
  'use strict';

  function formatCurrency(amount) {
    return 'Rp ' + Number(amount || 0).toLocaleString('id-ID');
  }

  function formatDate(dateStr, options) {
    if (!dateStr) return '-';
    var d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('id-ID', options || {
      year: 'numeric', month: 'short', day: 'numeric',
    });
  }

  function formatDateTime(dateStr) {
    if (!dateStr) return '-';
    var d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleString('id-ID', {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  }

  function formatNumber(num) {
    return Number(num || 0).toLocaleString('id-ID');
  }

  function escapeHtml(str) {
    if (str == null) return '';
    var div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
  }

  var ORDER_STATUS_LABELS = {
    pending: 'Menunggu',
    paid: 'Lunas',
    processed: 'Diproses',
    shipped: 'Dikirim',
    on_delivery: 'Dalam Pengiriman',
    completed: 'Selesai',
    cancelled: 'Dibatalkan',
    refunded: 'Dikembalikan',
  };

  function orderStatusLabel(status) {
    return ORDER_STATUS_LABELS[(status || '').toLowerCase()] || status || '-';
  }

  window.WarungioFormat = {
    currency: formatCurrency,
    date: formatDate,
    dateTime: formatDateTime,
    number: formatNumber,
    escapeHtml: escapeHtml,
    orderStatus: orderStatusLabel,
    ORDER_STATUS_LABELS: ORDER_STATUS_LABELS,
  };
})();
