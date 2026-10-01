/* Akashic Location: Geolocation API -> POST /api/location/detect.
 *
 * Koordinat hanya dikirim satu kali ke server untuk menentukan wilayah
 * dan tidak disimpan di browser. Yang disimpan (sessionStorage, hilang
 * saat tab ditutup) hanya ringkasan wilayah agar halaman lain tidak
 * perlu meminta izin lokasi berulang kali.
 */
(function () {
  'use strict';

  const STORAGE_KEY = 'akashic.region';
  const GEO_OPTIONS = { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 };
  const { api, h, label } = window.Akashic;

  class LocationError extends Error {
    constructor(code, message) { super(message); this.code = code; }
  }
  const ERRORS = {
    unsupported: 'Browser ini tidak mendukung Geolocation.',
    denied: 'Izin lokasi ditolak. Anda tetap dapat menjelajahi informasi umum.',
    unavailable: 'Lokasi tidak dapat ditentukan saat ini.',
    timeout: 'Waktu permintaan lokasi habis. Silakan coba lagi.',
    insecure: 'Geolocation hanya tersedia melalui HTTPS atau localhost.',
  };

  function getCoordinates() {
    return new Promise((resolve, reject) => {
      if (!('geolocation' in navigator)) return reject(new LocationError('unsupported', ERRORS.unsupported));
      if (!window.isSecureContext) return reject(new LocationError('insecure', ERRORS.insecure));
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        }),
        (err) => {
          const code = { 1: 'denied', 2: 'unavailable', 3: 'timeout' }[err.code] || 'unavailable';
          reject(new LocationError(code, ERRORS[code]));
        },
        GEO_OPTIONS,
      );
    });
  }

  async function detectRegion(coords) {
    const res = await api.post('/api/location/detect', {
      latitude: coords.latitude,
      longitude: coords.longitude,
      accuracy: coords.accuracy,
    });
    return { ...res.data, message: res.message };
  }

  function summarize(result) {
    if (!result || !result.region) return null;
    return {
      id: result.region.id,
      name: result.region.name,
      type: result.region.type,
      confidence: result.confidence,
      hierarchy: (result.hierarchy || []).map((r) => ({ id: r.id, name: r.name, type: r.type })),
    };
  }

  function saved() {
    try { return JSON.parse(sessionStorage.getItem(STORAGE_KEY)); } catch (_) { return null; }
  }

  function save(region) {
    try {
      if (region) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(region));
      else sessionStorage.removeItem(STORAGE_KEY);
    } catch (_) { /* storage dapat dinonaktifkan pengguna */ }
    updateChip(region);
    document.dispatchEvent(new CustomEvent('akashic:region', { detail: region }));
  }

  /* Alur lengkap: izin -> koordinat -> wilayah. onStage menerima tahap UI. */
  async function locate(onStage = () => {}) {
    onStage('detecting');
    const coords = await getCoordinates();
    onStage('resolving', coords);
    const result = await detectRegion(coords);
    const region = summarize(result);
    save(region);
    return { region, coords, result };
  }

  function updateChip(region) {
    const chip = document.getElementById('region-chip');
    if (!chip) return;
    chip.classList.toggle('on', !!region);
    chip.querySelector('span').textContent = region ? region.name : 'Lokasi belum aktif';
    chip.title = region ? `${label(region.type)} ${region.name}` : 'Aktifkan lokasi untuk informasi wilayah';
  }

  function crumbs(region) {
    return h('ol', { class: 'crumbs', 'aria-label': 'Hierarki wilayah' },
      (region.hierarchy || []).map((r) => h('li', null, r.name)));
  }

  function confidenceText(confidence) {
    return {
      high: 'Akurasi lokasi berada sepenuhnya di dalam wilayah ini.',
      approximate: 'Lokasi Anda berada di dekat batas wilayah; hasil bersifat perkiraan.',
      unknown: 'Akurasi lokasi tidak diketahui.',
    }[confidence] || '';
  }

  document.addEventListener('DOMContentLoaded', () => updateChip(saved()));

  window.AkashicLocation = { getCoordinates, detectRegion, locate, saved, save, clear: () => save(null), crumbs, confidenceText, LocationError };
})();
