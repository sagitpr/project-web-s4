/**
 * Warungio Marketplace - PWA Registration
 * Register service worker and handle app install prompt.
 */

(function () {
  'use strict';

  // Check if browser supports service workers
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/assets/pwa/service-worker.js')
        .then(function (registration) {
          console.log('✅ PWA Service Worker registered:', registration.scope);

          // Check for updates
          registration.addEventListener('updatefound', function () {
            const newWorker = registration.installing;
            newWorker.addEventListener('statechange', function () {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                // New version available
                showUpdateNotification(registration);
              }
            });
          });
        })
        .catch(function (error) {
          console.log('❌ PWA Service Worker registration failed:', error);
        });

      // Listen for controller change (after update)
      navigator.serviceWorker.addEventListener('controllerchange', function () {
        window.location.reload();
      });
    });
  }

  // Handle BeforeInstallPrompt (Add to Home Screen)
  let deferredPrompt = null;
  const installButton = document.getElementById('pwa-install-btn');

  window.addEventListener('beforeinstallprompt', function (event) {
    // Prevent Chrome 67 and earlier from automatically showing the prompt
    event.preventDefault();
    deferredPrompt = event;

    // Show install button if it exists
    if (installButton) {
      installButton.style.display = 'block';
      installButton.addEventListener('click', function () {
        // Hide the button
        installButton.style.display = 'none';
        // Show the install prompt
        deferredPrompt.prompt();
        // Wait for the user to respond to the prompt
        deferredPrompt.userChoice.then(function (choiceResult) {
          if (choiceResult.outcome === 'accepted') {
            console.log('✅ User accepted PWA install');
            trackPWAEvent('installed');
          } else {
            console.log('❌ User dismissed PWA install');
            trackPWAEvent('dismissed');
          }
          deferredPrompt = null;
        });
      });
    }
  });

  // Track when PWA is successfully installed
  window.addEventListener('appinstalled', function (event) {
    console.log('✅ PWA was installed');
    trackPWAEvent('app_installed');
    if (installButton) {
      installButton.style.display = 'none';
    }
  });

  /**
   * Show notification for new version available
   */
  function showUpdateNotification(registration) {
    const notification = document.createElement('div');
    notification.id = 'pwa-update-notification';
    notification.style.cssText = [
      'position: fixed',
      'bottom: 20px',
      'left: 50%',
      'transform: translateX(-50%)',
      'background: #059669',
      'color: white',
      'padding: 16px 24px',
      'border-radius: 12px',
      'box-shadow: 0 4px 20px rgba(0,0,0,0.2)',
      'z-index: 9999',
      'display: flex',
      'align-items: center',
      'gap: 12px',
      'font-family: system-ui, sans-serif',
      'animation: slideUp 0.3s ease',
    ].join(';');

    notification.innerHTML = `
      <span style="font-size:14px;">📦 Versi baru Warungio tersedia!</span>
      <button id="pwa-update-btn" style="
        background: white;
        color: #059669;
        border: none;
        padding: 8px 16px;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
        font-size: 13px;
      ">Update</button>
    `;

    document.body.appendChild(notification);

    document.getElementById('pwa-update-btn').addEventListener('click', function () {
      registration.waiting.postMessage({ action: 'skipWaiting' });
    });
  }

  /**
   * Track PWA events (placeholder for analytics)
   */
  function trackPWAEvent(action) {
    // Send to analytics
    try {
      if (window.gtag) {
        window.gtag('event', 'pwa_' + action);
      }
    } catch (e) {
      // Silent
    }
  }

  // Add animation styles
  const style = document.createElement('style');
  style.textContent = `
    @keyframes slideUp {
      from { transform: translateX(-50%) translateY(100px); opacity: 0; }
      to { transform: translateX(-50%) translateY(0); opacity: 1; }
    }
  `;
  document.head.appendChild(style);
})();
