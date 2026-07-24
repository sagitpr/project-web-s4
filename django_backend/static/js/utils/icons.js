/**
 * Warungio Custom Icon System v2
 * 
 * Replaces all small PNG UI icons with inline SVGs for:
 *   - Zero HTTP requests for icons
 *   - Sharp at any resolution (retina, 4K)
 *   - CSS-colorable (supports dark mode, hover states)
 *   - Smaller payload (SVGs are 30-60% smaller than equivalent PNGs)
 *   - Consistent design language across all pages
 * 
 * Design System:
 *   - viewBox: 0 0 24 24
 *   - stroke-width: 1.8 (semi-bold, friendly)
 *   - stroke-linecap: round | stroke-linejoin: round
 *   - Color: currentColor (inherit from parent CSS)
 *   - Semi-flat modern style with rounded corners
 * 
 * Usage (auto-replace):
 *   Add class="icon-replace" to any container, and img tags with matching
 *   alt text or data-icon attribute will be auto-replaced on DOMContentLoaded.
 *   
 *   Or manually:
 *     document.getElementById('myContainer').innerHTML = WarungioIcons.store({ size: 24, color: '#108d35' });
 */

(function() {
  'use strict';

  /**
   * Create an SVG string with consistent attributes.
   */
  function svg(pathHtml, opts) {
    opts = opts || {};
    var size = opts.size || 24;
    var color = opts.color || 'currentColor';
    var fill = opts.fill !== undefined ? opts.fill : 'none';
    var ariaHidden = opts.ariaHidden !== false ? 'aria-hidden="true"' : '';
    var extra = opts.extra || '';
    var className = opts.className ? 'class="' + opts.className + '"' : '';

    return '<svg ' +
      className + ' ' +
      'width="' + size + '" ' +
      'height="' + size + '" ' +
      'viewBox="0 0 24 24" ' +
      'fill="' + fill + '" ' +
      'stroke="' + color + '" ' +
      'stroke-width="' + (opts.strokeWidth || 1.8) + '" ' +
      'stroke-linecap="round" ' +
      'stroke-linejoin="round" ' +
      ariaHidden + ' ' +
      extra + '>' +
      pathHtml +
      '</svg>';
  }

  var ICONS = {};

  // Helper to add icons
  function addIcon(name, paths) {
    ICONS[name] = function(opts) {
      var p = Array.isArray(paths) ? paths.join('\n      ') : paths;
      return svg(p, opts);
    };
  }

  // ── Navigation & Actions ──
  addIcon('store', [
    '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    '<polyline points="9 22 9 12 15 12 15 22"/>'
  ]);

  addIcon('location', [
    '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>',
    '<circle cx="12" cy="10" r="3"/>'
  ]);

  addIcon('shield', [
    '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    '<polyline points="9 12 11 14 15 10"/>'
  ]);

  addIcon('verified', [
    '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>',
    '<polyline points="22 4 12 14.01 9 11.01"/>'
  ]);

  addIcon('star', [
    '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>'
  ]);

  addIcon('kilat', [
    '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>'
  ]);

  addIcon('list', [
    '<line x1="8" y1="6" x2="21" y2="6"/>',
    '<line x1="8" y1="12" x2="21" y2="12"/>',
    '<line x1="8" y1="18" x2="21" y2="18"/>',
    '<line x1="3" y1="6" x2="3.01" y2="6"/>',
    '<line x1="3" y1="12" x2="3.01" y2="12"/>',
    '<line x1="3" y1="18" x2="3.01" y2="18"/>'
  ]);

  addIcon('discount', [
    '<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/>',
    '<line x1="7" y1="7" x2="7.01" y2="7"/>'
  ]);

  addIcon('pengiriman', [
    '<rect x="1" y="3" width="15" height="13" rx="2" ry="2"/>',
    '<polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/>',
    '<circle cx="5.5" cy="18.5" r="2.5"/>',
    '<circle cx="18.5" cy="18.5" r="2.5"/>'
  ]);

  addIcon('keranjang', [
    '<circle cx="9" cy="21" r="1"/>',
    '<circle cx="20" cy="21" r="1"/>',
    '<path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>'
  ]);

  addIcon('call', [
    '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>'
  ]);

  addIcon('chat', [
    '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>'
  ]);

  addIcon('notifikasi', [
    '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>',
    '<path d="M13.73 21a2 2 0 0 1-3.46 0"/>'
  ]);

  addIcon('wallet', [
    '<rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>',
    '<line x1="1" y1="10" x2="23" y2="10"/>'
  ]);

  addIcon('clock', [
    '<circle cx="12" cy="12" r="10"/>',
    '<polyline points="12 6 12 12 16 14"/>'
  ]);

  addIcon('user', [
    '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>',
    '<circle cx="12" cy="7" r="4"/>'
  ]);

  addIcon('search', [
    '<circle cx="11" cy="11" r="8"/>',
    '<line x1="21" y1="21" x2="16.65" y2="16.65"/>'
  ]);

  addIcon('heart', [
    '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>'
  ]);

  addIcon('home', [
    '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    '<polyline points="9 22 9 12 15 12 15 22"/>'
  ]);

  addIcon('package', [
    '<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/>',
    '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>',
    '<polyline points="3.27 6.96 12 12.01 20.73 6.96"/>',
    '<line x1="12" y1="22.08" x2="12" y2="12"/>'
  ]);

  addIcon('creditCard', [
    '<rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>',
    '<line x1="1" y1="10" x2="23" y2="10"/>'
  ]);

  addIcon('settings', [
    '<circle cx="12" cy="12" r="3"/>',
    '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>'
  ]);

  addIcon('info', [
    '<circle cx="12" cy="12" r="10"/>',
    '<line x1="12" y1="16" x2="12" y2="12"/>',
    '<line x1="12" y1="8" x2="12.01" y2="8"/>'
  ]);

  addIcon('close', [
    '<line x1="18" y1="6" x2="6" y2="18"/>',
    '<line x1="6" y1="6" x2="18" y2="18"/>'
  ]);

  addIcon('menu', [
    '<line x1="3" y1="12" x2="21" y2="12"/>',
    '<line x1="3" y1="6" x2="21" y2="6"/>',
    '<line x1="3" y1="18" x2="21" y2="18"/>'
  ]);

  addIcon('arrowRight', [
    '<line x1="5" y1="12" x2="19" y2="12"/>',
    '<polyline points="12 5 19 12 12 19"/>'
  ]);

  addIcon('arrowLeft', [
    '<line x1="19" y1="12" x2="5" y2="12"/>',
    '<polyline points="12 19 5 12 12 5"/>'
  ]);

  addIcon('check', [
    '<polyline points="20 6 9 17 4 12"/>'
  ]);

  addIcon('plus', [
    '<line x1="12" y1="5" x2="12" y2="19"/>',
    '<line x1="5" y1="12" x2="19" y2="12"/>'
  ]);

  addIcon('eye', [
    '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>',
    '<circle cx="12" cy="12" r="3"/>'
  ]);

  addIcon('eyeOff', [
    '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>',
    '<path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>',
    '<line x1="1" y1="1" x2="23" y2="23"/>',
    '<circle cx="9.9" cy="9.9" r="3"/>'
  ]);

  addIcon('lock', [
    '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>',
    '<path d="M7 11V7a5 5 0 0 1 10 0v4"/>'
  ]);

  addIcon('mail', [
    '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>',
    '<polyline points="22,6 12,13 2,6"/>'
  ]);

  addIcon('truck', [
    '<rect x="1" y="3" width="15" height="13" rx="2" ry="2"/>',
    '<polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/>',
    '<circle cx="5.5" cy="18.5" r="2.5"/>',
    '<circle cx="18.5" cy="18.5" r="2.5"/>'
  ]);

  addIcon('food', [
    '<path d="M18 8h1a4 4 0 0 1 0 8h-1"/>',
    '<path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"/>',
    '<line x1="6" y1="1" x2="6" y2="4"/>',
    '<line x1="10" y1="1" x2="10" y2="4"/>',
    '<line x1="14" y1="1" x2="14" y2="4"/>'
  ]);

  addIcon('vegetable', [
    '<path d="M12 2v4M6 8c0-3.3 2.7-6 6-6s6 2.7 6 6v6c0 3.3-2.7 6-6 6s-6-2.7-6-6V8z"/>',
    '<path d="M6 12a6 6 0 0 0 6 6"/>',
    '<path d="M18 12a6 6 0 0 1-6 6"/>'
  ]);

  addIcon('fruit', [
    '<circle cx="12" cy="12" r="8"/>',
    '<path d="M12 4a8 8 0 0 0-8 8h16a8 8 0 0 0-8-8z"/>',
    '<path d="M12 4V2M8 6l-1-2M16 6l1-2"/>'
  ]);

  addIcon('meat', [
    '<path d="M17 2a3 3 0 0 1 3 3c0 1.1-.9 3-2 5s-2 3-2 5a3 3 0 0 0 3 3"/>',
    '<path d="M7 2a3 3 0 0 0-3 3c0 1.1.9 3 2 5s2 3 2 5a3 3 0 0 1-3 3"/>',
    '<path d="M12 4c-2.5 2-4 5-4 8s1.5 6 4 8c2.5-2 4-5 4-8s-1.5-6-4-8z"/>'
  ]);

  addIcon('beverage', [
    '<path d="M6 2h12l-1.5 15H7.5L6 2z"/>',
    '<path d="M9 17v3a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2v-3"/>',
    '<line x1="8" y1="9" x2="16" y2="9"/>'
  ]);

  addIcon('support', [
    '<path d="M21 12a9 9 0 0 0-9-9 9 9 0 0 0-9 9v3a4 4 0 0 0 4 4h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H5.1A7 7 0 0 1 12 5a7 7 0 0 1 6.9 5H17a2 2 0 0 0-2 2v3a2 2 0 0 0 2 2h1a4 4 0 0 0 4-4v-3z"/>'
  ]);

  addIcon('increase', [
    '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>',
    '<polyline points="17 6 23 6 23 12"/>'
  ]);

  addIcon('group', [
    '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>',
    '<circle cx="9" cy="7" r="4"/>',
    '<path d="M23 21v-2a4 4 0 0 0-3-3.87"/>',
    '<path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
  ]);

  addIcon('document', [
    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>',
    '<polyline points="14 2 14 8 20 8"/>',
    '<line x1="16" y1="13" x2="8" y2="13"/>',
    '<line x1="16" y1="17" x2="8" y2="17"/>',
    '<polyline points="10 9 9 9 8 9"/>'
  ]);

  addIcon('analytics', [
    '<line x1="18" y1="20" x2="18" y2="10"/>',
    '<line x1="12" y1="20" x2="12" y2="4"/>',
    '<line x1="6" y1="20" x2="6" y2="14"/>',
    '<line x1="2" y1="20" x2="22" y2="20"/>'
  ]);

  addIcon('refresh', [
    '<polyline points="23 4 23 10 17 10"/>',
    '<path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>'
  ]);

  addIcon('sparkles', [
    '<path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5L12 3z"/>',
    '<path d="M18.5 14.5L16 16l2.5 1.5L20 20l1.5-2.5L24 16l-2.5-1.5L20 12l-1.5 2.5z"/>',
    '<path d="M6 14l-1.5 2.5L2 18l2.5 1.5L6 22l1.5-2.5L10 18l-2.5-1.5L6 14z"/>'
  ]);

  addIcon('leaf', [
    '<path d="M11 20A7 7 0 0 1 9.8 6.9C15.5 4.9 17 3.5 19 2c1 2 2 4.5 2 8 0 5.5-4.78 10-10 10z"/>',
    '<path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>'
  ]);

  addIcon('storefront', [
    '<path d="M2 7l1-3h18l1 3"/>',
    '<path d="M22 7v11a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7"/>',
    '<path d="M16 21V13H8v8"/>',
    '<circle cx="12" cy="10" r="1.5"/>'
  ]);

  addIcon('percent', [
    '<line x1="19" y1="5" x2="5" y2="19"/>',
    '<circle cx="6.5" cy="6.5" r="2.5"/>',
    '<circle cx="17.5" cy="17.5" r="2.5"/>'
  ]);

  /**
   * Icon Name → alt text mapping for auto-replace.
   * Matches image alt text to icon names.
   */
  var ALT_MAP = {
    'marketplace': 'location',
    'lokasi': 'location',
    'terdekat': 'location',
    'bisnis': 'store',
    'warung': 'store',
    'toko': 'store',
    'aman': 'shield',
    'keamanan': 'shield',
    'verifikasi': 'verified',
    'kualitas': 'star',
    'selesai': 'star',
    'penilaian': 'star',
    'favorit': 'star',
    'rating': 'star',
    'cepat': 'kilat',
    'praktis': 'kilat',
    'produk': 'list',
    'inventaris': 'list',
    'menu': 'list',
    'stok': 'list',
    'promo': 'discount',
    'diskon': 'discount',
    'voucher': 'discount',
    'murah': 'discount',
    'pengiriman': 'pengiriman',
    'tracking': 'pengiriman',
    'diantar': 'pengiriman',
    'dikirim': 'pengiriman',
    'keranjang': 'keranjang',
    'cart': 'keranjang',
    'belanja': 'keranjang',
    'telepon': 'call',
    'email': 'call',
    'kontak': 'call',
    'chat': 'chat',
    'pesan': 'chat',
    'notifikasi': 'notifikasi',
    'dompet': 'wallet',
    'waktu': 'clock',
    'laporan': 'document',
    'profil': 'user',
    'pengaturan': 'settings',
    'supplier': 'group',
    'pelanggan': 'user',
    'pertumbuhan': 'increase',
    'bantuan': 'support',
    'sayuran': 'vegetable',
    'buah': 'fruit',
    'daging': 'meat',
    'minuman': 'beverage',
    'makanan': 'food',
  };

  /**
   * Auto-replace: finds all <img> tags with matching alt text
   * inside elements with class 'icon-replace' and replaces them
   * with inline SVGs.
   * 
   * Also supports data-icon attribute for explicit mapping.
   */
  function autoReplace() {
    var containers = document.querySelectorAll('.icon-replace');
    if (containers.length === 0) return;

    var size = 24;
    var color = 'currentColor';

    containers.forEach(function(container) {
      // Check container for data attributes
      if (container.dataset.iconSize) size = parseInt(container.dataset.iconSize) || 24;
      if (container.dataset.iconColor) color = container.dataset.iconColor;

      var images = container.querySelectorAll('img');
      images.forEach(function(img) {
        var iconName = null;

        // Priority 1: data-icon attribute
        if (img.dataset.icon && ICONS[img.dataset.icon]) {
          iconName = img.dataset.icon;
        }

        // Priority 2: alt text match
        if (!iconName && img.alt) {
          var altLower = img.alt.toLowerCase().trim();
          iconName = ALT_MAP[altLower];
        }

        // Priority 3: src filename match
        if (!iconName && img.src) {
          var srcMatch = img.src.match(/\/([a-z_-]+)\.png/i);
          if (srcMatch) {
            var nameFromSrc = srcMatch[1].toLowerCase().replace(/[_-]/g, '');
            for (var key in ALT_MAP) {
              if (key === nameFromSrc || ALT_MAP[key] === nameFromSrc) {
                iconName = ALT_MAP[key];
                break;
              }
            }
            // Direct check
            if (!iconName && ICONS[nameFromSrc]) {
              iconName = nameFromSrc;
            }
          }
        }

        if (iconName && ICONS[iconName]) {
          var svgHtml = ICONS[iconName]({ size: size, color: color, ariaHidden: true });
          var wrapper = document.createElement('span');
          wrapper.className = 'icon-svg-replace';
          wrapper.innerHTML = svgHtml;
          img.parentNode.replaceChild(wrapper, img);
        }
      });
    });
  }

  // ── Expose ──
  window.WarungioIcons = ICONS;
  window.autoReplaceIcons = autoReplace;
  window.renderIcon = function(iconName, target, opts) {
    var iconFn = ICONS[iconName];
    if (!iconFn) { console.warn('[WarungioIcons] Unknown:', iconName); return; }
    var el = typeof target === 'string' ? document.getElementById(target) : target;
    if (!el) return;
    el.innerHTML = iconFn(opts || {});
  };
  window.renderIcons = function(items) {
    if (!items) return;
    items.forEach(function(item) { window.renderIcon(item.icon, item.target, item.opts); });
  };

  // ── Auto-init on DOMContentLoaded ──
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoReplace);
  } else {
    autoReplace();
  }

  console.log('[WarungioIcons] Loaded — ' + Object.keys(ICONS).length + ' icons ready');

})();
