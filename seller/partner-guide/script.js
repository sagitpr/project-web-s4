/**
 * Seller Guide (Panduan Mitra) - Warungio
 * Dynamic content from Django API.
 */
document.addEventListener('DOMContentLoaded', async () => {
  // Load tips and guides from API if available
  const guideContainer = document.getElementById('guide-content') || document.querySelector('.guide-content');
  const tipsList = document.getElementById('tips-list') || document.querySelector('.tips-list');

  async function loadGuides() {
    try {
      // Try fetching general store data to show dynamic stats
      const data = await WarungioAPI.getDashboardSummary('all');
      const statsEl = document.getElementById('mitra-stats') || document.querySelector('.mitra-stats');
      if (statsEl && data) {
        const stores = data.total_stores || '500+';
        const products = data.total_products || '5000+';
        const orders = data.total_orders || '10000+';
        statsEl.innerHTML = `
          <div class="stat-card"><strong>${stores}</strong><span>Mitra Aktif</span></div>
          <div class="stat-card"><strong>${products}</strong><span>Produk Terjual</span></div>
          <div class="stat-card"><strong>${orders}</strong><span>Pesanan Diproses</span></div>`;
      }
    } catch (err) {
      console.warn('Guide stats fallback:', err);
    }
  }

  loadGuides();
});
