/**
 * Settings page - Warungio
 * Pengaturan akun, notifikasi, dan logout.
 */
(function () {
  'use strict';

  if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
    window.location.href = '/auth/login/?next=' + encodeURIComponent(window.location.pathname);
    return;
  }

  const logoutBtn = document.getElementById('btnLogoutSettings') || document.getElementById('btnLogout');
  const $$ = (sel) => document.querySelectorAll(sel);

  const userNameEl = document.getElementById('userName');
  const userEmailEl = document.getElementById('userEmail');
  const userRoleEl = document.getElementById('userRole');

  // Tampilkan info user
  try {
    const user = window.WarungioAuth.getUser();
    if (user) {
      if (userNameEl) userNameEl.textContent = user.full_name || user.email;
      if (userEmailEl) userEmailEl.textContent = user.email;
      if (userRoleEl) userRoleEl.textContent = user.role === 'seller' ? 'Penjual' : 'Pembeli';
    }
  } catch (e) { /* silent */ }

  // Logout
  logoutBtn?.addEventListener('click', function (e) {
    e.preventDefault();
    if (window.WarungioAuth) {
      window.WarungioAuth.logout();
      window.location.href = '/';
    }
  });

  // Toggle notification preferences
  $$('.notif-toggle').forEach(function (toggle) {
    toggle.addEventListener('change', function () {
      // Save preference to localStorage
      try {
        localStorage.setItem('warungio_notif_' + this.dataset.key, this.checked);
      } catch (e) { /* silent */ }
    });
  });
})();
