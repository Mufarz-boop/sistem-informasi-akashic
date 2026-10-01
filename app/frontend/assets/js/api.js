/* Akashic core: Fetch API wrapper, util DOM, format tanggal, toast, navigasi. */
(function () {
  'use strict';

  const state = { csrf: null };

  class ApiError extends Error {
    constructor(message, status, code, data) {
      super(message);
      this.status = status;
      this.code = code;
      this.data = data;
    }
  }

  async function request(method, url, body, options = {}) {
    const headers = { Accept: 'application/json' };
    const init = { method, headers, credentials: 'same-origin' };
    if (body !== undefined && body !== null) {
      headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(body);
    }
    if (method !== 'GET' && state.csrf) headers['X-CSRF-Token'] = state.csrf;
    if (options.signal) init.signal = options.signal;

    let response;
    try {
      response = await fetch(url, init);
    } catch (err) {
      if (err.name === 'AbortError') throw err;
      throw new ApiError('Tidak dapat terhubung ke server. Periksa koneksi Anda.', 0, 'network_error');
    }
    let payload = null;
    try { payload = await response.json(); } catch (_) { payload = null; }
    if (!response.ok || !payload || payload.success === false) {
      const message = (payload && payload.message) || `Permintaan gagal (${response.status}).`;
      throw new ApiError(message, response.status, payload && payload.error, payload && payload.data);
    }
    return payload;
  }

  const api = {
    get: (url, params, options) => request('GET', withQuery(url, params), null, options).then((p) => p.data),
    post: (url, body) => request('POST', url, body || {}),
    put: (url, body) => request('PUT', url, body || {}),
    del: (url, body) => request('DELETE', url, body || null),
    setCsrf: (token) => { state.csrf = token || null; },
  };

  function withQuery(url, params) {
    if (!params) return url;
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') qs.set(k, v);
    });
    const s = qs.toString();
    return s ? `${url}?${s}` : url;
  }

  /* ----- DOM helper ----- */
  function h(tag, attrs, ...children) {
    const node = document.createElement(tag);
    if (typeof attrs === 'string') {
      node.className = attrs;
    } else if (attrs) {
      Object.entries(attrs).forEach(([k, v]) => {
        if (v === undefined || v === null || v === false) return;
        if (k === 'class') node.className = v;
        else if (k === 'text') node.textContent = v;
        else if (k === 'dataset') Object.assign(node.dataset, v);
        else if (k.startsWith('on') && typeof v === 'function') node.addEventListener(k.slice(2), v);
        else if (v === true) node.setAttribute(k, '');
        else node.setAttribute(k, v);
      });
    }
    children.flat().forEach((c) => {
      if (c === undefined || c === null || c === false) return;
      node.append(c instanceof Node ? c : document.createTextNode(String(c)));
    });
    return node;
  }

  /* ----- Format ----- */
  const dateFmt = new Intl.DateTimeFormat('id-ID', { day: 'numeric', month: 'short', year: 'numeric' });
  const dateTimeFmt = new Intl.DateTimeFormat('id-ID', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  const rtf = new Intl.RelativeTimeFormat('id-ID', { numeric: 'auto' });

  function toDate(value) {
    if (!value) return null;
    const d = value instanceof Date ? value : new Date(value);
    return Number.isNaN(d.getTime()) ? null : d;
  }
  const fmt = {
    date: (v) => { const d = toDate(v); return d ? dateFmt.format(d) : '-'; },
    dateTime: (v) => { const d = toDate(v); return d ? dateTimeFmt.format(d) : '-'; },
    ago: (v) => {
      const d = toDate(v);
      if (!d) return '';
      const diffMin = (d.getTime() - Date.now()) / 60000;
      const abs = Math.abs(diffMin);
      if (abs < 1) return 'baru saja';
      if (abs < 60) return rtf.format(Math.round(diffMin), 'minute');
      if (abs < 1440) return rtf.format(Math.round(diffMin / 60), 'hour');
      if (abs < 43200) return rtf.format(Math.round(diffMin / 1440), 'day');
      return dateFmt.format(d);
    },
    /* ISO UTC -> nilai <input type="datetime-local"> waktu lokal. */
    toLocalInput: (v) => {
      const d = toDate(v);
      if (!d) return '';
      const pad = (n) => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    },
    /* Nilai datetime-local (waktu lokal) -> ISO UTC. */
    fromLocalInput: (v) => (v ? new Date(v).toISOString() : null),
  };

  const LABELS = {
    information: 'Informasi', event: 'Event', news: 'Berita',
    country: 'Negara', province: 'Provinsi', regency: 'Kabupaten', city: 'Kota',
    district: 'Kecamatan', village: 'Desa/Kelurahan', local: 'Area lokal',
  };
  const label = (key) => LABELS[String(key || '').toLowerCase()] || key || '';

  /* ----- Toast ----- */
  function toast(message, kind = 'info', timeout = 4200) {
    let stack = document.querySelector('.toast-stack');
    if (!stack) {
      stack = h('div', { class: 'toast-stack', role: 'status', 'aria-live': 'polite' });
      document.body.append(stack);
    }
    const node = h('div', `toast ${kind}`, message);
    stack.append(node);
    setTimeout(() => node.remove(), timeout);
  }

  function setBusy(button, busy, busyText) {
    if (!button) return;
    if (busy) {
      button.dataset.label = button.textContent;
      if (busyText) button.textContent = busyText;
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
    } else {
      if (button.dataset.label) button.textContent = button.dataset.label;
      button.disabled = false;
      button.removeAttribute('aria-busy');
    }
  }

  function debounce(fn, ms) {
    let id;
    return (...args) => { clearTimeout(id); id = setTimeout(() => fn(...args), ms); };
  }

  const REDUCED_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ----- Navigasi publik (header, menu mobile, reveal) ----- */
  function initChrome() {
    document.documentElement.classList.remove('no-js');
    const header = document.querySelector('.site-header');
    const nav = document.getElementById('site-nav');
    const menuBtn = document.getElementById('menu-btn');
    if (header) {
      const onScroll = () => header.classList.toggle('scrolled', window.scrollY > 24);
      window.addEventListener('scroll', onScroll, { passive: true });
      onScroll();
    }
    if (nav && menuBtn) {
      const close = () => { nav.classList.remove('open'); menuBtn.setAttribute('aria-expanded', 'false'); };
      menuBtn.addEventListener('click', () => {
        const open = nav.classList.toggle('open');
        menuBtn.setAttribute('aria-expanded', String(open));
      });
      nav.addEventListener('click', (e) => { if (e.target.closest('a')) close(); });
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && nav.classList.contains('open')) { close(); menuBtn.focus(); }
      });
    }
    const reveal = document.querySelectorAll('.rv');
    if (!('IntersectionObserver' in window) || REDUCED_MOTION) {
      reveal.forEach((n) => n.classList.add('in'));
      return;
    }
    const io = new IntersectionObserver((entries) => entries.forEach((en) => {
      if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
    }), { threshold: 0.12 });
    reveal.forEach((n) => io.observe(n));
  }

  document.addEventListener('DOMContentLoaded', initChrome);

  window.Akashic = { api, ApiError, h, fmt, label, toast, setBusy, debounce, REDUCED_MOTION };
})();
