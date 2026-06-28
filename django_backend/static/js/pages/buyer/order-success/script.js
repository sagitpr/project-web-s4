/**
 * Order Success page - Warungio
 * Displays order confirmation with order numbers, timeline, and payment info.
 */
document.addEventListener('DOMContentLoaded', () => {
  if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
    window.location.href = '../../auth/login/index.html';
    return;
  }

  var params = new URLSearchParams(window.location.search);
  var orderIds = params.get('orders') || '';
  var orderNumbers = params.get('numbers') || '';
  var paymentMethod = params.get('payment') || 'midtrans';
  var paymentStatus = params.get('status') || '';

  // ── DOM refs ──
  const orderNumberEl = document.getElementById('orderNumbers');
  const paymentMethodText = document.getElementById('paymentMethodText');
  const paymentStatusText = document.getElementById('paymentStatusText');
  const midtransInfo = document.getElementById('midtransInfo');
  const codInfo = document.getElementById('codInfo');
  const paymentSection = document.getElementById('paymentSection');

  // ── Display order numbers ──
  var firstOrderId = orderIds ? orderIds.split(',')[0] : null;

  if (orderNumbers) {
    orderNumberEl.textContent = orderNumbers;
  } else if (orderIds) {
    const ids = orderIds.split(',').map(id => '#' + id);
    orderNumberEl.textContent = ids.join(', ');
  } else {
    orderNumberEl.textContent = '-';
  }

  // ── Update "Lihat Pesanan" to link to order detail ──
  var pesananLink = document.querySelector('.actions a[href*="orders"]');
  if (pesananLink && firstOrderId) {
    pesananLink.href = '../order-detail/index.html?id=' + firstOrderId;
    pesananLink.innerHTML = pesananLink.innerHTML.replace('Lihat Pesanan', 'Lihat Detail');
  }

  // ── Payment info ──
  const paymentLabels = {
    midtrans: 'Midtrans (Kartu, QRIS, e-Wallet, Bank Transfer)',
    cod: 'Bayar di Tempat (COD)',
    transfer: 'Transfer Bank',
  };

  const methodLabel = paymentLabels[paymentMethod] || paymentMethod;
  paymentMethodText.innerHTML = 'Metode: <strong>' + methodLabel + '</strong>';

  // ── Payment status ──
  var statusMessage = '';
  if (paymentMethod === 'cod') {
    statusMessage = 'Menunggu pembayaran (COD)';
    midtransInfo.style.display = 'none';
    codInfo.style.display = 'block';
  } else if (paymentStatus === 'success') {
    statusMessage = '<strong style="color:var(--primary)">Lunas</strong>';
    midtransInfo.style.display = 'block';
    codInfo.style.display = 'none';
  } else if (paymentStatus === 'pending') {
    statusMessage = '<strong>Menunggu konfirmasi pembayaran</strong>';
    midtransInfo.style.display = 'block';
    codInfo.style.display = 'none';
  } else {
    statusMessage = '<strong>Menunggu pembayaran</strong>';
    midtransInfo.style.display = 'block';
    codInfo.style.display = 'none';
  }
  paymentStatusText.innerHTML = 'Status: ' + statusMessage;

  // ── Update timeline based on payment status ──
  var steps = document.querySelectorAll('.status-step');
  if (paymentStatus === 'success') {
    // Payment completed via Snap — mark up to step 3 (diproses)
    if (steps.length >= 2) steps[1].classList.add('active');
    if (steps.length >= 3) steps[2].classList.add('active');
  } else if (paymentMethod !== 'cod') {
    // Online payment pending — mark payment step
    if (steps.length >= 2) steps[1].classList.add('active');
  }

  // ── Load order detail to poll payment status (Midtrans notification may arrive later) ──
  if (orderIds && paymentStatus !== 'success') {
    var firstId = orderIds.split(',')[0];
    pollPaymentStatus(firstId);
  }

  async function pollPaymentStatus(orderId) {
    try {
      var data = await WarungioAPI.getPaymentStatus(orderId);
      if (data.payment_status === 'paid' || data.payment_status === 'settlement') {
        paymentStatusText.innerHTML = 'Status: <strong style="color:var(--primary)">Lunas</strong>';
        var s = document.querySelectorAll('.status-step');
        if (s.length >= 2) s[1].classList.add('active');
        if (s.length >= 3) s[2].classList.add('active');
      }
    } catch (err) {
      // Silent — payment may not exist yet
    }
  }
});
