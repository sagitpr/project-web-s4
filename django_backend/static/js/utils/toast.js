/**
 * Warungio Toast Notification System
 * Global toast/alert utility that works on any page.
 * Auto-creates the toast container if not present in the DOM.
 *
 * Usage:
 *   WarungioToast.show('Pesan berhasil!', 'success');
 *   WarungioToast.success('Berhasil!');
 *   WarungioToast.error('Gagal!');
 *   WarungioToast.info('Informasi');
 */
(function() {
  'use strict';

  var COLORS = {
    success: { bg: '#108d35', icon: '\u2713' },
    error:   { bg: '#ef4444', icon: '\u2717' },
    warning: { bg: '#f59e0b', icon: '\u26a0' },
    info:    { bg: '#3b82f6', icon: '\u2139' },
  };

  function getContainer() {
    var c = document.getElementById('warungioToastContainer');
    if (!c) {
      c = document.createElement('div');
      c.id = 'warungioToastContainer';
      c.style.cssText = 'position:fixed;top:20px;right:20px;z-index:99999;display:flex;flex-direction:column;gap:8px;pointer-events:none';
      document.body.appendChild(c);
    }
    return c;
  }

  function createToast(message, type) {
    var cfg = COLORS[type] || COLORS.info;
    var container = getContainer();

    var el = document.createElement('div');
    el.style.cssText = ['display:flex;align-items:center;gap:10px;padding:14px 20px;',
      'border-radius:12px;background:', cfg.bg, ';color:white;font-weight:600;',
      'font-size:0.95rem;box-shadow:0 8px 32px rgba(0,0,0,0.18);',
      'pointer-events:auto;max-width:420px;',
      'transform:translateX(120%);opacity:0;',
      'transition:all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1)'].join('');

    var closeBtn = document.createElement('button');
    closeBtn.innerHTML = '&times;';
    closeBtn.style.cssText = 'background:none;border:none;color:rgba(255,255,255,0.8);cursor:pointer;font-size:1.2rem;padding:0;line-height:1';
    closeBtn.onclick = function() { dismiss(el); };

    var iconSpan = document.createElement('span');
    iconSpan.style.cssText = 'font-size:1.15rem;line-height:1;flex-shrink:0';
    iconSpan.textContent = cfg.icon;

    var msgSpan = document.createElement('span');
    msgSpan.style.cssText = 'flex:1;line-height:1.4';
    msgSpan.textContent = message;

    el.appendChild(iconSpan);
    el.appendChild(msgSpan);
    el.appendChild(closeBtn);
    container.appendChild(el);

    // Trigger enter animation
    requestAnimationFrame(function() {
      el.style.transform = 'translateX(0)';
      el.style.opacity = '1';
    });

    // Auto-dismiss after 4 seconds
    var timer = setTimeout(function() {
      dismiss(el);
    }, 4000);

    // Pause timer on hover
    el.addEventListener('mouseenter', function() { clearTimeout(timer); });
    el.addEventListener('mouseleave', function() {
      timer = setTimeout(function() { dismiss(el); }, 2000);
    });

    return el;
  }

  function dismiss(el) {
    if (!el || !el.parentNode) return;
    el.style.transform = 'translateX(120%)';
    el.style.opacity = '0';
    setTimeout(function() {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, 350);
  }

  var Toast = {
    show: function(message, type) {
      return createToast(message, type || 'info');
    },
    success: function(message) {
      return createToast(message, 'success');
    },
    error: function(message) {
      return createToast(message, 'error');
    },
    warning: function(message) {
      return createToast(message, 'warning');
    },
    info: function(message) {
      return createToast(message, 'info');
    },
  };

  window.WarungioToast = Toast;
})();
