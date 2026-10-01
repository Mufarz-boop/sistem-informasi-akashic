/* Akashic Admin: sesi, CSRF, tabel, form dialog, konfirmasi, paginasi. */
(function () {
  'use strict';

  const { api, h, fmt, label, toast, setBusy } = window.Akashic;

  const STATUS_CLASS = {
    PUBLISHED: 'success', APPROVED: 'success', ACTIVE: 'success',
    DRAFT: 'muted', PENDING: 'amber', INACTIVE: 'muted',
    EXPIRED: 'muted', ARCHIVED: 'muted', CANCELLED: 'danger', REJECTED: 'danger',
    HIGH: 'amber', CRITICAL: 'danger', NORMAL: 'muted', LOW: 'muted',
  };
  const STATUS_TEXT = {
    PUBLISHED: 'Terbit', APPROVED: 'Disetujui', ACTIVE: 'Aktif', DRAFT: 'Draf',
    PENDING: 'Menunggu', INACTIVE: 'Nonaktif', EXPIRED: 'Kedaluwarsa',
    ARCHIVED: 'Arsip', CANCELLED: 'Dibatalkan', REJECTED: 'Ditolak',
    LOW: 'Rendah', NORMAL: 'Normal', HIGH: 'Tinggi', CRITICAL: 'Kritis',
  };

  let currentAdmin = null;
  const cache = {};

  function handleAuthError(err) {
    if (err && err.status === 401) {
      location.replace(`/auth/login?next=${encodeURIComponent(location.pathname)}`);
      return true;
    }
    return false;
  }

  /* Menjalankan aksi API dengan toast error standar. */
  async function run(promise, { success } = {}) {
    try {
      const res = await promise;
      if (success) toast(success === true ? res.message : success, 'success');
      return res;
    } catch (err) {
      if (!handleAuthError(err)) toast(err.message, 'error');
      throw err;
    }
  }

  async function init() {
    const sidebar = document.getElementById('sidebar');
    const menu = document.getElementById('admin-menu');
    if (menu && sidebar) {
      menu.addEventListener('click', () => {
        const open = sidebar.classList.toggle('open');
        menu.setAttribute('aria-expanded', String(open));
      });
      document.addEventListener('keydown', (e) => { if (e.key === 'Escape') sidebar.classList.remove('open'); });
    }
    const logout = document.getElementById('logout-btn');
    if (logout) {
      logout.addEventListener('click', async () => {
        setBusy(logout, true, 'Keluar...');
        try { await api.post('/api/auth/logout'); } catch (_) { /* tetap keluar */ }
        location.replace('/auth/login');
      });
    }
    try {
      const me = await api.get('/api/auth/me');
      api.setCsrf(me.csrf_token);
      currentAdmin = me.admin;
      document.querySelectorAll('[data-admin-name]').forEach((n) => { n.textContent = me.admin.full_name || me.admin.username; });
      return me.admin;
    } catch (err) {
      handleAuthError(err);
      throw err;
    }
  }

  function badge(status) {
    if (!status) return h('span', 'badge muted', '-');
    return h('span', `badge ${STATUS_CLASS[status] || 'muted'}`, STATUS_TEXT[status] || status);
  }

  function statusOptions(values) {
    return values.map((v) => ({ value: v, label: STATUS_TEXT[v] || v }));
  }

  /* ----- Opsi referensi (kategori/wilayah) ----- */
  async function categories(force) {
    if (!cache.categories || force) cache.categories = await api.get('/api/categories');
    return cache.categories;
  }
  async function regions(force) {
    if (!cache.regions || force) cache.regions = await api.get('/api/regions');
    return cache.regions;
  }
  const categoryOptions = async () => (await categories()).map((c) => ({ value: c.id, label: c.status === 'INACTIVE' ? `${c.name} (nonaktif)` : c.name }));
  const regionOptions = async () => (await regions()).map((r) => ({ value: r.id, label: `${r.name} — ${label(r.type)}${r.status === 'INACTIVE' ? ' (nonaktif)' : ''}` }));

  function fillSelect(select, options, placeholder) {
    select.replaceChildren();
    if (placeholder !== undefined) select.append(h('option', { value: '' }, placeholder));
    options.forEach((o) => select.append(h('option', { value: o.value }, o.label)));
  }

  /* ----- Tabel ----- */
  function renderRows(tbody, rows, renderRow, emptyText) {
    const cols = tbody.closest('table').querySelectorAll('thead th').length || 1;
    if (!rows.length) {
      tbody.replaceChildren(h('tr', 'empty-row', h('td', { colspan: cols }, emptyText || 'Belum ada data.')));
      return;
    }
    tbody.replaceChildren(...rows.map(renderRow));
  }

  function loadingRow(tbody) {
    const cols = tbody.closest('table').querySelectorAll('thead th').length || 1;
    tbody.replaceChildren(h('tr', 'empty-row', h('td', { colspan: cols }, 'Memuat data...')));
  }

  function actions(...buttons) {
    return h('td', null, h('div', 'row-actions', buttons.filter(Boolean)));
  }

  function actionBtn(text, onClick, cls = 'btn ghost xs') {
    return h('button', { class: cls, type: 'button', onclick: onClick }, text);
  }

  function titleCell(title, sub) {
    return h('td', 'title-cell', h('strong', null, title), sub ? h('small', null, sub) : null);
  }

  function pager(container, data, onPage) {
    container.replaceChildren();
    const info = h('span', null, data.total ? `Menampilkan halaman ${data.page} dari ${data.pages} · ${data.total} data` : '0 data');
    const nav = h('div', 'pager');
    if (data.pages > 1) {
      nav.append(
        h('button', { type: 'button', disabled: data.page <= 1, onclick: () => onPage(data.page - 1) }, '← Sebelumnya'),
        h('button', { type: 'button', disabled: data.page >= data.pages, onclick: () => onPage(data.page + 1) }, 'Berikutnya →'),
      );
    }
    container.append(info, nav);
  }

  /* ----- Dialog konfirmasi ----- */
  function confirm(message, { title = 'Konfirmasi', okText = 'Ya, lanjutkan', danger = true } = {}) {
    return new Promise((resolve) => {
      const dialog = h('dialog', { 'aria-labelledby': 'confirm-title' });
      const ok = h('button', { class: danger ? 'btn danger sm' : 'btn sm', type: 'button' }, okText);
      const cancel = h('button', { class: 'btn ghost sm', type: 'button' }, 'Batal');
      dialog.append(h('div', 'dialog-in',
        h('h2', { id: 'confirm-title' }, title),
        h('p', null, message),
        h('div', 'form-actions', cancel, ok)));
      let result = false;
      ok.addEventListener('click', () => { result = true; dialog.close(); });
      cancel.addEventListener('click', () => dialog.close());
      dialog.addEventListener('close', () => { dialog.remove(); resolve(result); });
      document.body.append(dialog);
      dialog.showModal();
      cancel.focus();
    });
  }

  /* ----- Form dialog generik -----
   * fields: [{ name, label, type, required, options, numeric, full, hint, placeholder, maxlength, min, max, step, rows }]
   * type: text | textarea | select | datetime | number | url | email | password | date
   */
  function fieldControl(field, value) {
    const id = `f-${field.name}`;
    const common = { id, name: field.name, required: !!field.required, maxlength: field.maxlength, placeholder: field.placeholder };
    let control;
    if (field.type === 'textarea') {
      control = h('textarea', { ...common, rows: field.rows || 5 });
      control.value = value ?? '';
    } else if (field.type === 'select') {
      control = h('select', { id, name: field.name, required: !!field.required });
      if (!field.required || field.placeholder) control.append(h('option', { value: '' }, field.placeholder || '— Tidak ada —'));
      (field.options || []).forEach((o) => control.append(h('option', { value: o.value }, o.label)));
      control.value = value === null || value === undefined ? (field.default ?? '') : String(value);
    } else if (field.type === 'datetime') {
      control = h('input', { ...common, type: 'datetime-local' });
      control.value = fmt.toLocalInput(value);
    } else {
      control = h('input', { ...common, type: field.type || 'text', min: field.min, max: field.max, step: field.step });
      control.value = value ?? (field.default ?? '');
    }
    return h('div', { class: `field${field.full ? ' full' : ''}` },
      h('label', { for: id }, field.label + (field.required ? ' *' : '')),
      control,
      field.hint ? h('span', 'hint', field.hint) : null);
  }

  function readValue(form, field) {
    const el = form.elements[field.name];
    const raw = el.value;
    if (field.type === 'datetime') return fmt.fromLocalInput(raw);
    if (field.type === 'number') return raw === '' ? null : Number(raw);
    if (field.numeric) return raw === '' ? null : parseInt(raw, 10);
    if (field.type === 'password') return raw;
    const text = raw.trim();
    return text === '' ? null : text;
  }

  async function formDialog({ title, fields, values = {}, submitText = 'Simpan', onSubmit, extra }) {
    const resolved = await Promise.all(fields.map(async (f) => ({ ...f, options: typeof f.options === 'function' ? await f.options() : f.options })));
    return new Promise((resolve) => {
      const dialog = h('dialog', { class: 'form-dialog', 'aria-labelledby': 'form-title' });
      const alertBox = h('div', { role: 'alert', hidden: true });
      const submit = h('button', { class: 'btn sm', type: 'submit' }, submitText);
      const cancel = h('button', { class: 'btn ghost sm', type: 'button', onclick: () => dialog.close() }, 'Batal');
      const form = h('form', { novalidate: true },
        alertBox,
        h('div', 'form-grid', resolved.map((f) => fieldControl(f, values[f.name]))),
        h('div', 'form-actions', cancel, submit));
      dialog.append(h('div', 'dialog-in',
        h('button', { class: 'dialog-close', type: 'button', 'aria-label': 'Tutup', onclick: () => dialog.close() }, '×'),
        h('h2', { id: 'form-title' }, title),
        form));
      if (extra) extra(form, dialog);
      let saved = null;
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const missing = resolved.filter((f) => f.required && !form.elements[f.name].value.trim());
        if (missing.length) {
          alertBox.className = 'alert error';
          alertBox.textContent = `Wajib diisi: ${missing.map((f) => f.label).join(', ')}.`;
          alertBox.hidden = false;
          form.elements[missing[0].name].focus();
          return;
        }
        const data = {};
        resolved.forEach((f) => { data[f.name] = readValue(form, f); });
        setBusy(submit, true, 'Menyimpan...');
        try {
          saved = await onSubmit(data, form);
          dialog.close();
        } catch (err) {
          if (handleAuthError(err)) return;
          alertBox.className = 'alert error';
          alertBox.textContent = err.message;
          alertBox.hidden = false;
          setBusy(submit, false);
        }
      });
      dialog.addEventListener('close', () => { dialog.remove(); resolve(saved); });
      document.body.append(dialog);
      dialog.showModal();
      const first = form.querySelector('input, textarea, select');
      if (first) first.focus();
    });
  }

  window.Admin = {
    init, run, badge, statusOptions, categories, regions, categoryOptions, regionOptions, fillSelect,
    renderRows, loadingRow, actions, actionBtn, titleCell, pager, confirm, formDialog,
    STATUS_TEXT, get admin() { return currentAdmin; }, handleAuthError,
  };
})();
