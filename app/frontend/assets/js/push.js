/* Akashic Web Push: service worker + PushManager + /api/notifications. */
(function () {
  'use strict';

  const { api } = window.Akashic;
  const SW_URL = '/service_worker.js';

  function supported() {
    return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window && window.isSecureContext;
  }

  function urlBase64ToUint8Array(base64) {
    const padding = '='.repeat((4 - (base64.length % 4)) % 4);
    const raw = atob((base64 + padding).replace(/-/g, '+').replace(/_/g, '/'));
    return Uint8Array.from(raw, (c) => c.charCodeAt(0));
  }

  async function registration() {
    const reg = await navigator.serviceWorker.register(SW_URL, { scope: '/' });
    await navigator.serviceWorker.ready;
    return reg;
  }

  async function currentSubscription() {
    if (!supported()) return null;
    const reg = await navigator.serviceWorker.getRegistration('/');
    return reg ? reg.pushManager.getSubscription() : null;
  }

  async function status() {
    if (!supported()) return 'unsupported';
    if (Notification.permission === 'denied') return 'denied';
    const sub = await currentSubscription();
    return sub ? 'subscribed' : 'idle';
  }

  async function subscribe(regionId) {
    if (!supported()) throw new Error('Browser ini belum mendukung Web Push (butuh HTTPS atau localhost).');
    const config = await api.get('/api/notifications/public-key');
    if (!config.enabled || !config.public_key) throw new Error('Notifikasi belum dikonfigurasi oleh pengelola Akashic.');
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') throw new Error('Izin notifikasi tidak diberikan. Anda tetap dapat memakai Akashic.');
    const reg = await registration();
    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(config.public_key),
      });
    }
    await api.post('/api/notifications/subscribe', { subscription: sub.toJSON(), region_id: regionId || null });
    return sub;
  }

  async function unsubscribe() {
    const sub = await currentSubscription();
    if (!sub) return;
    try { await api.del('/api/notifications/unsubscribe', { endpoint: sub.endpoint }); } finally { await sub.unsubscribe(); }
  }

  async function syncRegion(regionId) {
    const sub = await currentSubscription();
    if (sub) await api.put('/api/notifications/region', { endpoint: sub.endpoint, region_id: regionId || null });
  }

  /* Menghubungkan tombol & teks status pada halaman. */
  function bind(button, statusEl, getRegionId) {
    if (!button) return;
    const say = (text) => { if (statusEl) statusEl.textContent = text; };
    const render = async () => {
      const s = await status();
      button.disabled = s === 'unsupported' || s === 'denied';
      button.textContent = s === 'subscribed' ? 'Matikan notifikasi' : 'Aktifkan notifikasi';
      say({
        unsupported: 'Browser ini belum mendukung notifikasi web.',
        denied: 'Notifikasi diblokir di pengaturan browser.',
        subscribed: 'Notifikasi aktif untuk wilayah Anda.',
        idle: 'Dapatkan pemberitahuan saat ada informasi baru di wilayah Anda.',
      }[s]);
    };
    button.addEventListener('click', async () => {
      button.disabled = true;
      try {
        if ((await status()) === 'subscribed') {
          await unsubscribe();
          window.Akashic.toast('Notifikasi dinonaktifkan.');
        } else {
          await subscribe(getRegionId());
          window.Akashic.toast('Notifikasi wilayah diaktifkan.', 'success');
        }
      } catch (err) {
        say(err.message);
        window.Akashic.toast(err.message, 'error');
      }
      button.disabled = false;
      render().catch(() => {});
    });
    document.addEventListener('akashic:region', (e) => { syncRegion(e.detail && e.detail.id).catch(() => {}); });
    render().catch(() => say('Status notifikasi tidak dapat diperiksa.'));
  }

  window.AkashicPush = { supported, status, subscribe, unsubscribe, syncRegion, bind };
})();
