/**
 * Warungio Navigation — mobile menu + bottom tab bar
 */
(function () {
  'use strict';

  function initMobileMenu() {
    var btn = document.querySelector('.mobile-menu-btn') || document.getElementById('mobileMenuBtn');
    var drawer = document.getElementById('mobileNavDrawer');
    var overlay = document.getElementById('mobileNavOverlay');
    if (!btn || !drawer) return;

    function close() {
      drawer.classList.remove('open');
      if (overlay) overlay.classList.remove('open');
      document.body.style.overflow = '';
    }

    function open() {
      drawer.classList.add('open');
      if (overlay) overlay.classList.add('open');
      document.body.style.overflow = 'hidden';
    }

    btn.addEventListener('click', function () {
      if (drawer.classList.contains('open')) close();
      else open();
    });

    if (overlay) overlay.addEventListener('click', close);
    drawer.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', close);
    });
  }

  function initSidebarToggle() {
    var toggle = document.getElementById('menuToggle');
    var sidebar = document.querySelector('.page-shell .sidebar') || document.querySelector('.sidebar');
    if (!toggle || !sidebar) return;

    toggle.addEventListener('click', function () {
      sidebar.classList.toggle('open');
    });
  }

  function markActiveBottomNav() {
    var path = window.location.pathname;
    document.querySelectorAll('.bottom-nav a').forEach(function (a) {
      var href = a.getAttribute('href');
      if (href && path.indexOf(href.replace(/\/$/, '')) === 0) {
        a.classList.add('active');
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    initMobileMenu();
    initSidebarToggle();
    markActiveBottomNav();
    if (document.querySelector('.bottom-nav')) {
      document.body.classList.add('has-bottom-nav');
    }
  });
})();
