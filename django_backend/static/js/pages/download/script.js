/**
 * Warungio Download Page — Device Detection, Download Tracking, Progress UI
 * 
 * Features:
 * - Client-side device detection (Android/iOS/Desktop)
 * - Auto-start download for detected device
 * - Download progress tracking (via XHR where supported)
 * - Analytics event logging
 * - Toast notifications for download events
 */
(function () {
  'use strict';

  const DOWNLOAD_API_DETECT = '/download/api/detect/';
  const DOWNLOAD_API_VERSION = '/download/api/version/';
  const DOWNLOAD_ANDROID_URL = '/download/android/';

  const toast = document.getElementById('downloadToast');
  const toastMsg = document.getElementById('toastMessage');

  // ── Device Detection ─────────────────────────────────────────────────
  function detectDevice() {
    const ua = navigator.userAgent.toLowerCase();

    if (/android/i.test(ua)) {
      return 'android';
    }

    if (/iphone|ipad|ipod/i.test(ua)) {
      return 'ios';
    }

    // iPad on iOS 13+ detection
    if (/macintosh/i.test(ua) && navigator.maxTouchPoints > 1) {
      return 'ios';
    }

    return 'desktop';
  }

  // ── Toast Notification ──────────────────────────────────────────────
  function showToast(message, duration) {
    if (!toast || !toastMsg) return;
    toastMsg.textContent = message;
    toast.classList.add('show');
    clearTimeout(toast._hideTimer);
    toast._hideTimer = setTimeout(function () {
      toast.classList.remove('show');
    }, duration || 4000);
  }

  // ── Format File Size ─────────────────────────────────────────────────
  function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '-';
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    let size = bytes;
    while (size >= 1024 && i < units.length - 1) {
      size /= 1024;
      i++;
    }
    return size.toFixed(1) + ' ' + units[i];
  }

  // ── Download Progress (via XHR for APK) ─────────────────────────────
  function downloadWithProgress(url) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', url, true);
    xhr.responseType = 'blob';

    var progressWrap = document.getElementById('androidProgress');
    var progressFill = document.getElementById('androidProgressFill');
    var progressText = document.getElementById('androidProgressText');
    var downloadBtn = document.getElementById('androidDownloadBtn');

    if (progressWrap) progressWrap.style.display = 'flex';
    if (downloadBtn) downloadBtn.style.display = 'none';

    xhr.onprogress = function (e) {
      if (e.lengthComputable && progressFill && progressText) {
        var percent = Math.round((e.loaded / e.total) * 100);
        progressFill.style.width = percent + '%';
        progressText.textContent = 'Mengunduh ' + percent + '% (' + formatFileSize(e.loaded) + ' / ' + formatFileSize(e.total) + ')';
      }
    };

    xhr.onload = function () {
      if (xhr.status === 200) {
        var blob = xhr.response;
        var contentDisposition = xhr.getResponseHeader('Content-Disposition');
        var filename = 'Warungio.apk';

        if (contentDisposition) {
          var match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
          if (match && match[1]) {
            filename = match[1].replace(/['"]/g, '').trim();
          }
        }

        // Create download link and trigger it
        var link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Clean up blob URL after a delay
        setTimeout(function () {
          URL.revokeObjectURL(link.href);
        }, 10000);

        if (progressFill) progressFill.style.width = '100%';
        if (progressText) progressText.textContent = 'Download selesai!';

        showToast('Download Warungio berhasil dimulai!', 5000);
      } else {
        if (progressWrap) progressWrap.style.display = 'none';
        if (downloadBtn) downloadBtn.style.display = 'flex';
        showToast('Gagal mengunduh. Silakan coba lagi.', 5000);
      }
    };

    xhr.onerror = function () {
      if (progressWrap) progressWrap.style.display = 'none';
      if (downloadBtn) downloadBtn.style.display = 'flex';
      showToast('Gagal terhubung. Periksa koneksi Anda.', 5000);
    };

    xhr.send();
  }

  // ── Auto-Start Download for Detected Device ─────────────────────────
  function autoStartDownload(device) {
    var banner = document.getElementById('deviceDetectedBanner');
    var bannerText = document.getElementById('deviceDetectedText');

    if (!banner || !bannerText) return;

    var deviceNames = {
      android: 'Perangkat Android terdeteksi — Memulai download APK...',
      ios: 'Perangkat iOS terdeteksi — Mengarahkan ke App Store...',
      desktop: 'Perangkat desktop terdeteksi — Pilih platform download',
    };

    banner.style.display = 'flex';
    bannerText.textContent = deviceNames[device] || deviceNames.desktop;

    if (device === 'android') {
      // Auto-start download with progress
      setTimeout(function () {
        downloadWithProgress(DOWNLOAD_ANDROID_URL);
      }, 600);
    } else if (device === 'ios') {
      // Redirect to iOS distribution after brief delay
      setTimeout(function () {
        window.location.href = '/download/ios/';
      }, 1000);
    }
  }

  // ── Load Version Info from API ──────────────────────────────────────
  function loadVersionInfo() {
    fetch(DOWNLOAD_API_VERSION)
      .then(function (res) { return res.json(); })
      .then(function (data) {
        // Update Android info
        var androidVersionEl = document.getElementById('androidVersion');
        var androidSizeEl = document.getElementById('androidFileSize');
        var androidBtn = document.getElementById('androidDownloadBtn');

        if (androidVersionEl && data.android) {
          androidVersionEl.textContent = data.android.version || '-';
        }
        if (androidSizeEl && data.android) {
          androidSizeEl.textContent = formatFileSize(data.android.file_size);
        }
        if (androidBtn && data.android) {
          var available = data.android.available;
          androidBtn.style.pointerEvents = available ? 'auto' : 'none';
          androidBtn.style.opacity = available ? '1' : '0.5';
          var btnText = androidBtn.querySelector('.btn-text');
          if (btnText) {
            btnText.textContent = available ? 'Download APK' : 'Segera Hadir';
          }
        }

        // Update iOS info
        var iosVersionEl = document.getElementById('iosVersion');
        var iosStatusEl = document.getElementById('iosStatus');
        var iosBtn = document.getElementById('iosDownloadBtn');

        if (iosVersionEl && data.ios) {
          iosVersionEl.textContent = data.ios.version || '-';
        }
        if (iosStatusEl && data.ios) {
          iosStatusEl.textContent = data.ios.distribution_url ? 'Tersedia' : 'Segera';
        }
        if (iosBtn && data.ios) {
          var iosAvail = data.ios.available || !!data.ios.distribution_url;
          iosBtn.style.pointerEvents = iosAvail ? 'auto' : 'none';
          iosBtn.style.opacity = iosAvail ? '1' : '0.5';
          var iosBtnText = iosBtn.querySelector('.btn-text');
          if (iosBtnText) {
            if (data.ios.distribution_url) {
              iosBtnText.textContent = 'Buka App Store';
            } else if (data.ios.ipa_available) {
              iosBtnText.textContent = 'Download IPA';
            } else {
              iosBtnText.textContent = 'Segera Hadir';
            }
          }
        }
      })
      .catch(function (err) {
        console.warn('Failed to load version info:', err);
      });
  }

  // ── Intercept Android Download Click ────────────────────────────────
  function setupDownloadHandlers() {
    var androidBtn = document.getElementById('androidDownloadBtn');
    if (androidBtn) {
      androidBtn.addEventListener('click', function (e) {
        // Check if the download should use XHR progress tracking
        var device = detectDevice();
        if (device === 'android') {
          e.preventDefault();
          downloadWithProgress(DOWNLOAD_ANDROID_URL);
        }
        // For desktop, let the normal link behavior happen (direct download)
      });
    }

    var iosBtn = document.getElementById('iosDownloadBtn');
    if (iosBtn) {
      iosBtn.addEventListener('click', function (e) {
        showToast('Mengarahkan ke App Store...', 3000);
      });
    }
  }

  // ── Error Handling from Query Parameters ────────────────────────────
  function handleErrorParam() {
    var params = new URLSearchParams(window.location.search);
    var error = params.get('error');
    if (!error) return;

    var messages = {
      'disabled': 'Download sedang dinonaktifkan. Silakan coba lagi nanti.',
      'not_found': 'File APK tidak ditemukan. Hubungi admin Warungio.',
      'integrity': 'File APK gagal diverifikasi. Silakan unduh ulang atau hubungi admin.',
      'ios_unavailable': 'Aplikasi iOS belum tersedia. Pantau halaman ini untuk info terbaru.',
      'manifest_unavailable': 'Konfigurasi iOS belum tersedia.',
    };

    var msg = messages[error] || 'Terjadi kesalahan. Silakan coba lagi.';
    showToast(msg, 6000);
  }

  // ── Init ────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    handleErrorParam();
    var device = detectDevice();
    autoStartDownload(device);
    loadVersionInfo();
    setupDownloadHandlers();

    // Update hero badge with version
    var heroBadge = document.querySelector('.download-hero-badge');
    if (heroBadge) {
      fetch(DOWNLOAD_API_VERSION)
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (d.android && d.android.version) {
            heroBadge.textContent = 'v' + d.android.version;
          }
        })
        .catch(function () {});
    }
  });
})();
