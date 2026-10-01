/* Akashic Feed: GET /api/feed dan detail per tipe konten. */
(function () {
  'use strict';

  const { api, h, fmt, label, REDUCED_MOTION } = window.Akashic;
  const DETAIL_URL = { information: '/api/information/', event: '/api/events/', news: '/api/news/' };

  function fetchFeed(params, options) {
    return api.get('/api/feed', params, options);
  }

  function fetchDetail(type, id) {
    if (!DETAIL_URL[type]) return Promise.reject(new Error('Tipe konten tidak dikenal.'));
    return api.get(DETAIL_URL[type] + encodeURIComponent(id));
  }

  function eventWhen(item) {
    if (!item.start_at) return '';
    const start = fmt.dateTime(item.start_at);
    return item.end_at ? `${start} – ${fmt.dateTime(item.end_at)}` : start;
  }

  function metaFor(item) {
    if (item.type === 'event') return [item.region, eventWhen(item), item.location];
    if (item.type === 'news') return [item.source, item.region, fmt.ago(item.published_at || item.created_at)];
    return [item.region, fmt.ago(item.created_at)];
  }

  function badgeClass(type) {
    return { information: 'badge', event: 'badge amber', news: 'badge ink' }[type] || 'badge';
  }

  /* region: wilayah pengguna (opsional) untuk menandai konten paling relevan. */
  function renderCard(item, index, { onOpen, region } = {}) {
    const exact = region && item.region_id === region.id;
    const card = h('article', { class: `card ${item.type}` });
    if (!REDUCED_MOTION) card.style.animationDelay = `${Math.min(index, 8) * 50}ms`;
    const top = h('div', 'top-row',
      h('span', badgeClass(item.type), label(item.type)),
      item.category ? h('span', 'badge muted', item.category) : null);
    const title = h('h3');
    if (onOpen) {
      title.append(h('button', { type: 'button', onclick: (e) => onOpen(item, e.currentTarget) }, item.title));
    } else {
      title.append(h('a', { href: `/information?type=${item.type}&id=${item.id}` }, item.title));
    }
    card.append(top, title);
    if (item.priority === 'HIGH' || item.priority === 'CRITICAL') {
      card.append(h('span', 'rel', item.priority === 'CRITICAL' ? 'PENTING · SEGERA' : 'PRIORITAS TINGGI'));
    } else if (exact) {
      card.append(h('span', 'rel', 'DI WILAYAH ANDA'));
    }
    if (item.description) card.append(h('p', null, item.description));
    card.append(h('div', 'meta', metaFor(item).filter(Boolean).map((t) => h('span', null, t))));
    return card;
  }

  function skeletons(container, count = 6) {
    container.replaceChildren(...Array.from({ length: count }, () => h('div', { class: 'card sk', 'aria-hidden': 'true' },
      ['35%', '90%', '75%', '55%'].map((w) => { const i = h('i'); i.style.width = w; return i; }))));
  }

  function paragraphs(text) {
    return String(text || '').split(/\n{1,}/).map((t) => t.trim()).filter(Boolean).map((t) => h('p', null, t));
  }

  /* Mengisi elemen detail dialog; mengembalikan node konten. */
  function renderDetail(type, item) {
    const nodes = [];
    const meta = [];
    if (item.region_name) meta.push(item.region_name);
    if (type === 'information') {
      meta.push(`Dipublikasikan ${fmt.dateTime(item.published_at || item.created_at)}`);
      if (item.updated_at) meta.push(`Diperbarui ${fmt.dateTime(item.updated_at)}`);
    }
    if (type === 'news') {
      meta.push(item.source_name);
      if (item.published_at) meta.push(fmt.dateTime(item.published_at));
    }
    nodes.push(h('div', 'd-meta', meta.filter(Boolean).map((m) => h('span', null, m))));

    const image = type === 'news' ? item.image_url : item.image;
    if (image && /^https?:\/\//i.test(image)) {
      nodes.push(h('img', { class: 'd-img', src: image, alt: '', loading: 'lazy', referrerpolicy: 'no-referrer' }));
    }

    if (type === 'event') {
      nodes.push(h('dl', 'd-facts',
        h('dt', null, 'Mulai'), h('dd', null, fmt.dateTime(item.start_at)),
        h('dt', null, 'Selesai'), h('dd', null, item.end_at ? fmt.dateTime(item.end_at) : '-'),
        h('dt', null, 'Lokasi'), h('dd', null, item.location_name || '-'),
        h('dt', null, 'Wilayah'), h('dd', null, item.region_name || '-')));
    }

    const body = type === 'information' ? item.content : type === 'event' ? item.description : item.summary;
    nodes.push(h('div', 'd-body', paragraphs(body)));

    if (type === 'news') {
      const relevance = item.region_name
        ? `Dikaitkan dengan ${item.region_name} berdasarkan ${item.relevance_method === 'SOURCE' ? 'cakupan sumber berita' : item.relevance_method === 'MANUAL' ? 'penilaian admin' : 'kata kunci wilayah'}.`
        : 'Berita umum, belum dikaitkan dengan wilayah tertentu.';
      nodes.push(h('p', 'd-foot', 'Berita eksternal dari ', h('strong', null, item.source_name || 'sumber luar'), `. ${relevance} `,
        h('a', { href: item.source_url, target: '_blank', rel: 'noopener noreferrer nofollow' }, 'Baca selengkapnya di sumber ↗')));
    } else {
      nodes.push(h('p', 'd-foot', `Diterbitkan oleh admin Akashic${item.category_name ? ` · ${item.category_name}` : ''}.`));
    }
    return nodes;
  }

  window.AkashicFeed = { fetchFeed, fetchDetail, renderCard, renderDetail, skeletons };
})();
