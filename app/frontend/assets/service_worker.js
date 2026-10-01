/* Akashic Service Worker: menerima Web Push dan membuka tautan notifikasi. */
'use strict';

const DEFAULT_ICON = '/static/img/icon.svg';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));

self.addEventListener('push', (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (_) {
    data = { title: 'Akashic', body: event.data ? event.data.text() : '' };
  }
  const title = data.title || 'Akashic';
  const options = {
    body: data.body || 'Ada informasi baru di wilayah Anda.',
    icon: data.icon || DEFAULT_ICON,
    badge: DEFAULT_ICON,
    tag: data.tag || undefined,
    data: { url: data.url || '/' },
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const target = new URL(event.notification.data && event.notification.data.url ? event.notification.data.url : '/', self.location.origin);
  if (target.origin !== self.location.origin) return;
  event.waitUntil((async () => {
    const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const client of windows) {
      if (new URL(client.url).origin === target.origin && 'focus' in client) {
        await client.navigate(target.href);
        return client.focus();
      }
    }
    return self.clients.openWindow(target.href);
  })());
});
