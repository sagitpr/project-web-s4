/**
 * Warungio Marketplace - Progressive Web App Service Worker
 * Version: 1.0.0
 * 
 * Handles offline caching, push notifications, and background sync.
 */

const CACHE_NAME = 'warungio-cache-v1';
const STATIC_CACHE = 'warungio-static-v1';
const API_CACHE = 'warungio-api-v1';
const DYNAMIC_CACHE = 'warungio-dynamic-v1';

// Assets to pre-cache on install
const PRECACHE_URLS = [
  '/',
  '/home/',
  '/auth/login/',
  '/auth/register/',
  '/static/css/style.css',
  '/static/css/components.css',
  '/static/css/responsive.css',
  '/static/css/tokens.css',
  '/static/js/script.js',
  '/static/js/api.js',
  '/static/js/auth.js',
  '/static/js/nav.js',
  '/static/js/device-detector.js',
  '/assets/pwa/manifest.json',
  '/assets/favicon.ico',
];

// Install event - pre-cache core assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll(PRECACHE_URLS);
    }).then(() => {
      return self.skipWaiting();
    })
  );
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
  const cacheWhitelist = [CACHE_NAME, STATIC_CACHE, API_CACHE, DYNAMIC_CACHE];
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      return self.clients.claim();
    })
  );
});

// Helper: is this a navigation request
function isNavigationRequest(request) {
  return request.mode === 'navigate' ||
    (request.method === 'GET' &&
      request.headers.get('Accept') &&
      request.headers.get('Accept').includes('text/html'));
}

// Helper: is this an API request
function isApiRequest(url) {
  return url.pathname.startsWith('/api/');
}

// Helper: is this a static asset
function isStaticAsset(url) {
  const extensions = ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg',
    '.webp', '.ico', '.woff', '.woff2', '.ttf', '.eot', '.json'];
  return extensions.some(ext => url.pathname.endsWith(ext)) ||
    url.pathname.startsWith('/static/') ||
    url.pathname.startsWith('/assets/') ||
    url.pathname.startsWith('/media/');
}

// Fetch event - serve from cache or network
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Skip chrome-extension and other non-http(s) requests
  if (!url.protocol.startsWith('http')) return;

  // API requests: Network First with cache fallback
  if (isApiRequest(url)) {
    event.respondWith(networkFirstWithCache(request, API_CACHE));
    return;
  }

  // Static assets: Cache First
  if (isStaticAsset(url)) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // Navigation/HTML: Network First
  if (isNavigationRequest(request)) {
    event.respondWith(networkFirstWithCache(request, DYNAMIC_CACHE));
    return;
  }

  // Everything else: Network First
  event.respondWith(networkFirstWithCache(request, DYNAMIC_CACHE));
});

// Cache First strategy
async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) {
    return cached;
  }
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}

// Network First strategy with cache fallback
async function networkFirstWithCache(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }
    // For navigation requests, return offline page
    if (isNavigationRequest(request)) {
      return caches.match('/');
    }
    return new Response(JSON.stringify({
      error: 'Anda sedang offline. Silakan coba lagi saat koneksi tersedia.',
      offline: true,
    }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

// Push notification event
self.addEventListener('push', (event) => {
  if (!event.data) return;

  try {
    const data = event.data.json();
    const options = {
      body: data.description || data.message || 'Notifikasi baru',
      icon: '/assets/pwa/icon-192x192.png',
      badge: '/assets/pwa/icon-72x72.png',
      vibrate: [200, 100, 200],
      data: {
        url: data.action_url || '/',
        notification_id: data.id,
        type: data.notification_type || 'general',
      },
      actions: [
        { action: 'open', title: 'Lihat' },
        { action: 'close', title: 'Tutup' },
      ],
      tag: `warungio-${data.id || Date.now()}`,
      renotify: true,
      requireInteraction: data.priority === 'high' || false,
    };

    event.waitUntil(
      self.registration.showNotification(
        data.title || 'Warungio',
        options
      )
    );
  } catch (error) {
    // Fallback for non-JSON push data
    event.waitUntil(
      self.registration.showNotification('Warungio', {
        body: event.data.text() || 'Notifikasi baru',
        icon: '/assets/pwa/icon-192x192.png',
      })
    );
  }
});

// Notification click event
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const urlToOpen = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // Find existing tab
      for (const client of clientList) {
        if (client.url === urlToOpen && 'focus' in client) {
          return client.focus();
        }
      }
      // Open new tab
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
    })
  );
});

// Background sync for offline orders
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-orders') {
    event.waitUntil(syncOrders());
  } else if (event.tag === 'sync-messages') {
    event.waitUntil(syncMessages());
  }
});

async function syncOrders() {
  // Retrieve pending orders from IndexedDB and send them
  const cache = await caches.open('pending-orders');
  // Implementation depends on IndexedDB setup
  console.log('Syncing pending orders...');
}

async function syncMessages() {
  // Retrieve pending messages from IndexedDB and send them
  console.log('Syncing pending messages...');
}

// Periodic background sync (if supported)
self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'update-orders') {
    event.waitUntil(updateOrders());
  }
});

async function updateOrders() {
  // Periodically check for order updates
  console.log('Checking for order updates...');
}
