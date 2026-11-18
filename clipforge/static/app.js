/* ClipForge — interface (PC et tablette). Aucune dépendance externe. */
'use strict';

// ---------------------------------------------------------------------------
// Petits outils
// ---------------------------------------------------------------------------
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const store = {
  get(k, d) { try { const v = localStorage.getItem('cf_' + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem('cf_' + k, JSON.stringify(v)); } catch { /* stockage indisponible */ } },
};

async function api(path, opts = {}) {
  const init = { ...opts, headers: { ...(opts.headers || {}) } };
  if (opts.json !== undefined) {
    init.body = JSON.stringify(opts.json);
    init.headers['Content-Type'] = 'application/json';
    delete init.json;
  }
  const res = await fetch(path, init);
  let data = null;
  try { data = await res.json(); } catch { data = null; }
  if (!res.ok) {
    const msg = data && data.detail ? (typeof data.detail === 'string' ? data.detail : 'Requête invalide') : `Erreur ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

function toast(msg, type = '') {
  const el = document.createElement('div');
  el.className = 'toast ' + type;
  el.textContent = msg;
  $('#toasts').appendChild(el);
  setTimeout(() => el.remove(), type === 'err' ? 6000 : 3200);
}

function fmtTime(sec, precise = true) {
  if (sec == null || isNaN(sec)) return '—';
  sec = Math.max(0, sec);
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  const ss = precise ? s.toFixed(1).padStart(4, '0') : String(Math.floor(s)).padStart(2, '0');
  return h ? `${h}:${String(m).padStart(2, '0')}:${ss}` : `${m}:${ss}`;
}
function fmtDur(sec) {
  if (sec == null) return '';
  return sec < 60 ? `${Math.round(sec)} s` : `${Math.floor(sec / 60)} min ${String(Math.round(sec % 60)).padStart(2, '0')}`;
}
function parseTime(str) {
  if (str == null) return null;
  const s = String(str).trim().replace(',', '.');
  if (!s) return null;
  const hms = s.toLowerCase().match(/^(?:(\d+)h)?(?:(\d+)m(?:in)?)?(?:(\d+(?:\.\d+)?)s?)?$/);
  if (hms && /[hms]/.test(s.toLowerCase()) && (hms[1] || hms[2] || hms[3])) {
    return (+hms[1] || 0) * 3600 + (+hms[2] || 0) * 60 + (+hms[3] || 0);
  }
  const parts = s.split(':').map(Number);
  if (parts.some(isNaN)) return null;
  return parts.reduce((acc, p) => acc * 60 + p, 0);
}
function fmtSize(bytes) {
  if (!bytes) return '';
  return bytes > 1e6 ? `${(bytes / 1e6).toFixed(1).replace('.', ',')} Mo` : `${Math.round(bytes / 1e3)} Ko`;
}
function fmtViews(n) {
  if (n == null) return '';
  return n >= 1000 ? `${(n / 1000).toFixed(1).replace('.', ',')} k vues` : `${n} vues`;
}

const ICON = {
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3"><path d="M5 12l5 5L20 7"/></svg>',
  back: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M15 18l-6-6 6-6"/></svg>',
  play: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M7 4v16l13-8z"/></svg>',
  pause: '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>',
  sound: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5L6 9H2v6h4l5 4z" fill="currentColor"/><path d="M15.5 8.5a5 5 0 0 1 0 7M19 5a10 10 0 0 1 0 14"/></svg>',
  mute: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5L6 9H2v6h4l5 4z" fill="currentColor"/><path d="M22 9l-6 6M16 9l6 6"/></svg>',
  magic: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 4V2M15 16v-2M8 9h2M20 9h2M17.8 11.8l1.4 1.4M17.8 6.2l1.4-1.4M12.2 6.2l-1.4-1.4"/><path d="M3 21l9-9"/></svg>',
  download: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 3v12M7 10l5 5 5-5M4 21h16"/></svg>',
  share: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/></svg>',
  copy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4h8v2M6 6l1 15h10l1-15"/></svg>',
  upload: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 16V4M7 9l5-5 5 5M4 20h16"/></svg>',
  film: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="3"/><path d="M7 3v18M17 3v18M3 8h4M3 16h4M17 8h4M17 16h4"/></svg>',
  x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M6 6l12 12M18 6L6 18"/></svg>',
};

let INFO = null;
let SETTINGS = null;
const fontsReady = document.fonts
  ? Promise.all([
    document.fonts.load('40px Anton'),
    document.fonts.load('800 40px Poppins'),
    document.fonts.load('700 40px Poppins'),
  ]).catch(() => null)
  : Promise.resolve();

// ---------------------------------------------------------------------------
// Routeur
// ---------------------------------------------------------------------------
let view = null;
function route() {
  if (view && view.destroy) view.destroy();
  view = null;
  window.scrollTo(0, 0);
  const hash = location.hash || '#/';
  const m = hash.match(/^#\/p\/([a-z0-9]+)/);
  if (m) view = EditorView(m[1]);
  else if (hash.startsWith('#/reglages')) view = SettingsView();
  else if (hash.startsWith('#/bios')) view = BiosView();
  else view = HomeView();
}

// Indicateur global des tâches
async function pollJobs() {
  try {
    const jobs = await api('/api/jobs');
    const active = jobs.filter((j) => j.status === 'en_cours' || j.status === 'attente');
    const pill = $('#jobsPill');
    if (active.length) {
      pill.classList.remove('hidden');
      $('#jobsText').textContent = active.length === 1 ? active[0].label : `${active.length} tâches en cours`;
    } else pill.classList.add('hidden');
  } catch { /* hors ligne */ }
}

// Fenêtre « Tablette »
function openTabletModal() {
  const bg = document.createElement('div');
  bg.className = 'modal-bg';
  const local = INFO && INFO.is_local;
  bg.innerHTML = `<div class="modal" role="dialog" aria-modal="true">
    <div class="row" style="justify-content:space-between"><h2>Ouvrir sur la tablette</h2>
    <button class="btn-ghost icon-btn" data-close aria-label="Fermer">${ICON.x}</button></div>
    ${local && INFO.tablet_url ? `
      <p class="muted small">1. Connecte la tablette au <b>même Wi-Fi</b> que ce PC.<br>
      2. Scanne ce QR code avec l'appareil photo de la tablette.<br>
      3. Astuce : « Ajouter à l'écran d'accueil » pour l'avoir comme une appli.</p>
      <div class="qr"><img src="/api/qr.svg?t=${Date.now()}" alt="QR code"></div>
      <div class="url-box">${esc(INFO.tablet_url)}</div>
      <p class="muted small">Si la page ne s'ouvre pas, autorise ClipForge (Python) dans le pare-feu Windows pour les réseaux privés.</p>`
      : local ? '<p>Aucun réseau Wi-Fi détecté sur ce PC.</p>'
        : '<p>Tu utilises déjà ClipForge depuis un autre appareil 👍</p>'}
  </div>`;
  bg.addEventListener('click', (e) => { if (e.target === bg || e.target.closest('[data-close]')) bg.remove(); });
  document.body.appendChild(bg);
}

// ---------------------------------------------------------------------------
// Accueil
// ---------------------------------------------------------------------------
function HomeView() {
  const app = $('#app');
  let tab = store.get('tab', 'lien');
  let auto = store.get('auto', false);
  let formats = store.get('formats', (SETTINGS && SETTINGS.default_formats) || ['tiktok', 'reels', 'shorts']);
  let clips = [];
  let selected = new Set();
  let timer = null;
  let destroyed = false;

  app.innerHTML = `
    <section class="card hero">
      <div>
        <h1>Tes clips Twitch, prêts pour TikTok, Reels et YouTube</h1>
        <p class="lead">Colle un lien (Twitch anglais ou français) : ClipForge détecte la facecam, recadre en vertical, ajoute des sous-titres animés (en anglais ou dans la langue du clip) et un titre accrocheur, exporte dans tous les formats et te prépare les descriptions avec hashtags.</p>
      </div>
      <div>
        <div class="tabs" id="tabs">
          <button data-tab="lien">Lien d'un clip</button>
          <button data-tab="chaine">Top clips d'une chaîne</button>
          <button data-tab="vod">Passage d'une VOD</button>
          <button data-tab="fichier">Fichier vidéo</button>
        </div>
        <div id="tabBody"></div>
        <div class="auto-box">
          <label class="switch"><span><b>Montage 100 % automatique</b><br><span class="muted small">L'appli fait tout et exporte directement dans les formats choisis.</span></span>
            <input type="checkbox" id="autoChk" ${auto ? 'checked' : ''}><span class="knob"></span></label>
          <div class="fmt-chips" id="fmtChips"></div>
        </div>
      </div>
    </section>
    <section style="margin-top:26px">
      <div class="row" style="justify-content:space-between;margin-bottom:12px"><h2>Mes projets</h2></div>
      <div class="projects" id="projects"><div class="empty">Chargement…</div></div>
    </section>`;

  function renderFormats() {
    $('#fmtChips').innerHTML = Object.entries(INFO.platforms).map(([k, p]) =>
      `<label class="fmt-chip ${formats.includes(k) ? 'on' : ''}"><input type="checkbox" value="${k}" ${formats.includes(k) ? 'checked' : ''}><span class="dot ${k}"></span>${esc(p.label)}</label>`).join('');
  }
  $('#fmtChips').addEventListener('change', (e) => {
    const k = e.target.value;
    formats = e.target.checked ? [...new Set([...formats, k])] : formats.filter((f) => f !== k);
    store.set('formats', formats);
    renderFormats();
  });
  $('#autoChk').addEventListener('change', (e) => { auto = e.target.checked; store.set('auto', auto); });

  function renderTab() {
    $$('#tabs button').forEach((b) => b.classList.toggle('on', b.dataset.tab === tab));
    const body = $('#tabBody');
    if (tab === 'lien') {
      body.innerHTML = `<form class="import-row" id="urlForm">
          <input type="url" id="urlIn" placeholder="https://www.twitch.tv/…/clip/…  ou  https://clips.twitch.tv/…" autocomplete="off" required>
          <button class="btn-primary btn-big" type="submit">Importer</button>
        </form>
        <p class="muted small">Astuce : sur Twitch, ouvre un clip → « Partager » → « Copier le lien ».</p>`;
      $('#urlForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await importUrl($('#urlIn').value.trim(), e.submitter);
      });
      setTimeout(() => $('#urlIn') && !('ontouchstart' in window) && $('#urlIn').focus(), 50);
    } else if (tab === 'chaine') {
      body.innerHTML = `<form class="import-row" id="chForm">
          <input type="text" id="chIn" placeholder="Nom de la chaîne (ex : zerator)" value="${esc(store.get('channel', ''))}" required autocomplete="off">
          <select id="chPeriod" style="width:auto;min-height:54px">
            <option value="24h">24 h</option><option value="7j" selected>7 jours</option><option value="30j">30 jours</option><option value="tout">Depuis toujours</option>
          </select>
          <button class="btn-primary btn-big" type="submit">Voir les clips</button>
        </form>
        <div id="clipRes"></div>`;
      $('#chPeriod').value = store.get('period', '7j');
      $('#chForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = e.submitter;
        const channel = $('#chIn').value.trim();
        const period = $('#chPeriod').value;
        store.set('channel', channel); store.set('period', period);
        btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Recherche…';
        try {
          clips = await api(`/api/channel-clips?channel=${encodeURIComponent(channel)}&period=${period}`);
          selected = new Set();
          renderClips();
        } catch (err) { toast(err.message, 'err'); }
        btn.disabled = false; btn.textContent = 'Voir les clips';
      });
      if (clips.length) renderClips();
    } else if (tab === 'vod') {
      body.innerHTML = `<form class="stack" id="vodForm">
          <input type="url" id="vodUrl" placeholder="https://www.twitch.tv/videos/123456789" required autocomplete="off">
          <div class="row">
            <label class="field grow">Début du passage<input type="text" id="vodStart" placeholder="1:23:00" required></label>
            <label class="field grow">Fin du passage<input type="text" id="vodEnd" placeholder="1:33:00" required></label>
            <button class="btn-primary btn-big" type="submit" style="align-self:flex-end">Récupérer</button>
          </div>
          <p class="muted small">ClipForge télécharge seulement ce passage puis repère tout seul les moments forts (cris, rires, hype).</p>
        </form>`;
      $('#vodForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const s = parseTime($('#vodStart').value), en = parseTime($('#vodEnd').value);
        if (s == null || en == null || en <= s) { toast('Vérifie le début et la fin du passage.', 'err'); return; }
        await importUrl($('#vodUrl').value.trim(), e.submitter, { vod_start: s, vod_end: en });
      });
    } else {
      body.innerHTML = `<label class="dropzone" id="drop">
          ${ICON.upload}<h3>Dépose une vidéo ici</h3>
          <p class="muted small">ou touche pour choisir un fichier (mp4, mov, mkv, webm…)</p>
          <input type="file" id="fileIn" accept="video/*,.mkv" hidden>
        </label>
        <div id="upProg" class="hidden" style="margin-top:12px"><div class="bar"><i style="width:0"></i></div><p class="muted small" id="upTxt"></p></div>`;
      const drop = $('#drop');
      $('#fileIn').addEventListener('change', (e) => e.target.files[0] && upload(e.target.files[0]));
      ['dragenter', 'dragover'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add('over'); }));
      ['dragleave', 'drop'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove('over'); }));
      drop.addEventListener('drop', (e) => e.dataTransfer.files[0] && upload(e.dataTransfer.files[0]));
    }
  }

  function renderClips() {
    const box = $('#clipRes');
    if (!box) return;
    if (!clips.length) { box.innerHTML = '<p class="muted">Aucun clip trouvé sur cette période.</p>'; return; }
    box.innerHTML = `<div class="clip-list">${clips.map((c, i) => `
        <div class="clip-item ${selected.has(i) ? 'on' : ''}" data-i="${i}">
          <span class="check">${ICON.check}</span>
          ${c.duration ? `<span class="dur">${fmtDur(c.duration)}</span>` : ''}
          <img loading="lazy" src="${esc(c.thumbnail || '')}" alt="" onerror="this.style.visibility='hidden'">
          <div class="meta"><b title="${esc(c.title)}">${esc(c.title)}</b><span class="muted">${fmtViews(c.views)}</span></div>
        </div>`).join('')}</div>
      <div class="row" style="margin-top:14px;justify-content:flex-end">
        <span class="muted" id="selCount"></span>
        <button class="btn-primary btn-big" id="importSel" disabled>Importer la sélection</button>
      </div>`;
    const update = () => {
      $('#selCount').textContent = selected.size ? `${selected.size} clip(s) sélectionné(s)` : 'Touche les clips à importer';
      $('#importSel').disabled = !selected.size;
    };
    update();
    box.querySelector('.clip-list').addEventListener('click', (e) => {
      const it = e.target.closest('.clip-item');
      if (!it) return;
      const i = +it.dataset.i;
      selected.has(i) ? selected.delete(i) : selected.add(i);
      it.classList.toggle('on', selected.has(i));
      update();
    });
    $('#importSel').addEventListener('click', async (e) => {
      const btn = e.currentTarget;
      btn.disabled = true;
      const list = [...selected].map((i) => clips[i]);
      let last = null;
      for (const c of list) {
        try {
          last = await api('/api/projects/url', { method: 'POST', json: { url: c.url, title: c.title, auto, formats } });
        } catch (err) { toast(err.message, 'err'); }
      }
      toast(`${list.length} clip(s) ajouté(s)${auto ? ' : montage automatique lancé' : ''}`, 'ok');
      if (list.length === 1 && last && !auto) location.hash = `#/p/${last.id}`;
      else { selected = new Set(); renderClips(); loadProjects(); }
    });
  }

  async function importUrl(url, btn, extra = {}) {
    if (!url) return;
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>'; }
    try {
      const p = await api('/api/projects/url', { method: 'POST', json: { url, auto, formats, ...extra } });
      location.hash = `#/p/${p.id}`;
    } catch (err) {
      toast(err.message, 'err');
      if (btn) { btn.disabled = false; btn.textContent = 'Importer'; }
    }
  }

  function upload(file) {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('auto', auto ? 'true' : 'false');
    fd.append('formats', formats.join(','));
    const xhr = new XMLHttpRequest();
    $('#upProg').classList.remove('hidden');
    xhr.upload.onprogress = (e) => {
      if (!e.lengthComputable) return;
      const pc = (e.loaded / e.total) * 100;
      $('#upProg i').style.width = pc + '%';
      $('#upTxt').textContent = `Envoi… ${Math.round(pc)} %`;
    };
    xhr.onload = () => {
      let data = null;
      try { data = JSON.parse(xhr.responseText); } catch { /* ignore */ }
      if (xhr.status >= 200 && xhr.status < 300 && data) location.hash = `#/p/${data.id}`;
      else { toast((data && data.detail) || 'Envoi impossible', 'err'); $('#upProg').classList.add('hidden'); }
    };
    xhr.onerror = () => { toast('Envoi impossible (connexion perdue)', 'err'); $('#upProg').classList.add('hidden'); };
    xhr.open('POST', '/api/projects/upload');
    xhr.send(fd);
  }

  async function loadProjects() {
    let list = [];
    try { list = await api('/api/projects'); } catch (err) { toast(err.message, 'err'); return; }
    if (destroyed) return;
    const box = $('#projects');
    if (!list.length) {
      box.innerHTML = '<div class="empty card" style="grid-column:1/-1">Aucun projet pour l\'instant. Colle le lien d\'un clip Twitch au-dessus pour commencer !</div>';
    } else {
      box.innerHTML = list.map((p) => {
        const busy = ['import', 'analyse'].includes(p.status);
        const badge = p.status === 'erreur' ? '<span class="badge err">Erreur</span>'
          : busy ? '<span class="badge run"><span class="spinner" style="width:12px;height:12px;border-width:2px"></span>Import</span>'
            : '<span class="badge">Prêt</span>';
        return `<div class="project-card" data-id="${p.id}">
          <div class="thumb" style="background-image:url('${p.has_thumb ? `/api/projects/${p.id}/thumb` : ''}')">${p.duration ? `<span class="dur">${fmtDur(p.duration)}</span>` : ''}</div>
          <div class="body">
            <div class="title">${esc(p.title)}</div>
            ${p.channel ? `<div class="muted small">${esc(p.channel)}</div>` : ''}
            <div class="foot">${badge}${p.exports.map((k) => `<span class="badge ok"><span class="dot ${k}"></span>${esc(INFO.platforms[k].label)}</span>`).join('')}
              <button class="btn-ghost btn-sm icon-btn btn-danger" data-del="${p.id}" title="Supprimer" style="margin-left:auto">${ICON.trash}</button></div>
          </div></div>`;
      }).join('');
    }
    clearTimeout(timer);
    if (list.some((p) => ['import', 'analyse'].includes(p.status))) timer = setTimeout(loadProjects, 2500);
  }

  $('#projects').addEventListener('click', async (e) => {
    const del = e.target.closest('[data-del]');
    if (del) {
      e.stopPropagation();
      if (!confirm('Supprimer ce projet et ses vidéos exportées ?')) return;
      try { await api(`/api/projects/${del.dataset.del}`, { method: 'DELETE' }); loadProjects(); } catch (err) { toast(err.message, 'err'); }
      return;
    }
    const card = e.target.closest('.project-card');
    if (card) location.hash = `#/p/${card.dataset.id}`;
  });
  $('#tabs').addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    tab = b.dataset.tab; store.set('tab', tab); renderTab();
  });

  renderFormats();
  renderTab();
  loadProjects();
  return { destroy() { destroyed = true; clearTimeout(timer); } };
}

// ---------------------------------------------------------------------------
// Géométrie partagée avec le moteur Python (analysis.py / overlays.py)
// ---------------------------------------------------------------------------
function splitHeights(ratio, outH = 1920) {
  const top = Math.round((outH * ratio) / 2) * 2;
  return [top, outH - top];
}
function clampRect(r) {
  const w = clamp(r.w, 0.02, 1), h = clamp(r.h, 0.02, 1);
  return { x: clamp(r.x, 0, 1 - w), y: clamp(r.y, 0, 1 - h), w, h };
}
function fitAspect(r, na, keep) {
  let w = r.w, h = r.h;
  const cx = r.x + w / 2, cy = r.y + h / 2;
  if (keep === 'w') { h = w / na; if (h > 1) { h = 1; w = h * na; } } else { w = h * na; if (w > 1) { w = 1; h = w / na; } }
  return clampRect({ x: cx - w / 2, y: cy - h / 2, w, h });
}

function computePlacement(platformKey, edit) {
  const p = INFO.platforms[platformKey];
  const W = p.width, H = p.height;
  const caps = edit.captions || {};
  const sf = { petit: 0.82, moyen: 1, grand: 1.2 }[caps.size || 'moyen'] || 1;
  const pos = caps.position || 'auto';
  if (p.vertical) {
    const safeBottom = H * (1 - p.safe_bottom);
    const layout = edit.layout || 'blur';
    const ratio = +edit.split_ratio || 0.4;
    let cy;
    if (pos === 'haut') cy = H * 0.3;
    else if (pos === 'milieu') cy = H * 0.5;
    else if (pos === 'bas') cy = safeBottom - H * 0.07;
    else if (layout === 'split') cy = H * (ratio + (1 - ratio) * 0.42);
    else if (layout === 'blur') cy = H * 0.68;
    else cy = H * 0.66;
    cy = Math.min(cy, safeBottom - H * 0.06);
    const onJunction = layout === 'split';
    return {
      W, H, vertical: true,
      title_y: onJunction ? H * ratio : H * (p.safe_top + 0.015), title_centered: onJunction,
      caption_cy: cy, caption_max_w: W * (0.86 - p.safe_right * 0.5), caption_size: Math.floor(92 * sf),
      title_size: 62, title_max_w: W * 0.84, wm_y: safeBottom - H * 0.012, wm_size: 38,
    };
  }
  const cy = { haut: H * 0.18, milieu: H * 0.5 }[pos] || H * 0.84;
  return {
    W, H, vertical: false, title_y: H * 0.06, title_centered: false,
    caption_cy: cy, caption_max_w: W * 0.7, caption_size: Math.floor(74 * sf),
    title_size: 54, title_max_w: W * 0.6, wm_y: H * 0.94, wm_size: 34,
  };
}

function fontSpec(name, size) {
  if (name === 'anton') return `${size}px Anton, Impact, sans-serif`;
  if (name === 'poppins-bold') return `700 ${size}px Poppins, sans-serif`;
  return `800 ${size}px Poppins, sans-serif`;
}
function metrics(name, size) {
  const m = (INFO.font_metrics || {})[name] || [1.05, 0.35];
  return [m[0] * size, m[1] * size];
}
function wrapWords(ctx, words, maxW) {
  const space = ctx.measureText(' ').width;
  const lines = [[]];
  let width = 0;
  words.forEach((w, i) => {
    const wl = ctx.measureText(w).width;
    if (lines[lines.length - 1].length && width + space + wl > maxW) { lines.push([]); width = 0; }
    if (lines[lines.length - 1].length) width += space;
    lines[lines.length - 1].push(i);
    width += wl;
  });
  return lines.filter((l) => l.length);
}
function balancedLines(ctx, words, maxW, maxLines) {
  let lines = wrapWords(ctx, words, maxW);
  if (lines.length === 2 && words.length >= 3) {
    const total = ctx.measureText(words.join(' ')).width;
    const longest = Math.max(...words.map((w) => ctx.measureText(w).width));
    lines = wrapWords(ctx, words, Math.max(total * 0.55, longest) + 1);
    if (lines.length > maxLines) lines = wrapWords(ctx, words, maxW);
  }
  return lines;
}
function rgba(hex, fallback = 'rgba(0,0,0,0)') {
  if (!hex) return fallback;
  const v = hex.replace('#', '');
  const r = parseInt(v.slice(0, 2), 16), g = parseInt(v.slice(2, 4), 16), b = parseInt(v.slice(4, 6), 16);
  const a = v.length === 8 ? parseInt(v.slice(6, 8), 16) / 255 : 1;
  return `rgba(${r},${g},${b},${a})`;
}
function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(x, y, w, h, r);
  else ctx.rect(x, y, w, h);
  ctx.fill();
}

// Comme le moteur Python : pas d'emojis incrustés dans l'image.
const EMOJI_RE = /[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{1F1E6}-\u{1F1FF}\u{2B00}-\u{2BFF}\u{2300}-\u{23FF}\u{FE0F}\u{200D}\u{E0020}-\u{E007F}]/gu;
const stripEmoji = (s) => String(s || '').replace(EMOJI_RE, '').replace(/\s{2,}/g, ' ').trim();

function drawCaption(ctx, pl, rawWords, rawActive, style) {
  const cleaned = rawWords.map(stripEmoji);
  const keep = cleaned.map((w, i) => (w ? i : -1)).filter((i) => i >= 0);
  if (!keep.length) return;
  const words = keep.map((i) => cleaned[i]);
  const active = keep.indexOf(rawActive) >= 0 ? keep.indexOf(rawActive) : null;
  let size = pl.caption_size;
  ctx.font = fontSpec(style.font, size);
  let lines = balancedLines(ctx, words, pl.caption_max_w, 3);
  while (lines.length > 2 && size > 48) {
    size -= 6; ctx.font = fontSpec(style.font, size);
    lines = balancedLines(ctx, words, pl.caption_max_w, 3);
  }
  const [asc, desc] = metrics(style.font, size);
  const lineH = Math.floor((asc + desc) * 1.08);
  const top = pl.caption_cy - (lineH * lines.length) / 2;
  const stroke = style.stroke ? Math.max(4, Math.floor(size / 11)) : 0;
  const pop = !!style.pop;
  const bigSize = Math.floor(size * 1.12);
  const space = ctx.measureText(' ').width + stroke * 1.2;
  const width = (i) => {
    ctx.font = fontSpec(style.font, pop && active === i ? bigSize : size);
    return ctx.measureText(words[i]).width;
  };
  ctx.lineJoin = 'round';
  ctx.textBaseline = 'alphabetic';
  lines.forEach((line, li) => {
    const lineW = line.reduce((a, i) => a + width(i), 0) + space * (line.length - 1);
    let x = pl.W / 2 - lineW / 2;
    const y = top + li * lineH;
    if (style.box) {
      ctx.fillStyle = rgba(style.box);
      roundRect(ctx, x - size * 0.28, y - size * 0.1, lineW + size * 0.56, lineH + size * 0.08, size * 0.25);
    }
    line.forEach((i) => {
      const isA = active === i;
      const wl = width(i);
      if (isA && style.highlight_box) {
        ctx.fillStyle = rgba(style.highlight_box);
        const pad = size * 0.12;
        roundRect(ctx, x - pad, y - pad * 0.3, wl + pad * 2, lineH - pad * 0.3, size * 0.18);
      }
      const fs = isA && pop ? bigSize : size;
      ctx.font = fontSpec(style.font, fs);
      const [a2] = metrics(style.font, fs);
      const by = (isA && pop ? y - size * 0.07 : y) + a2;
      if (stroke) {
        ctx.lineWidth = stroke * 2;
        ctx.strokeStyle = 'rgba(0,0,0,0.45)';
        ctx.strokeText(words[i], x + 4, by + 6);
        ctx.strokeStyle = rgba(style.stroke, '#000');
        ctx.strokeText(words[i], x, by);
      }
      ctx.fillStyle = isA ? rgba(style.highlight) : rgba(style.color);
      ctx.fillText(words[i], x, by);
      x += wl + space;
    });
  });
}

function drawTitle(ctx, pl, text, style) {
  text = stripEmoji(text);
  if (!text) return;
  let size = style.box ? pl.title_size : Math.floor(pl.title_size * 1.35);
  const words = text.split(/\s+/);
  ctx.font = fontSpec(style.font, size);
  let lines = wrapWords(ctx, words, pl.title_max_w);
  while (lines.length > 3 && size > 34) { size -= 4; ctx.font = fontSpec(style.font, size); lines = wrapWords(ctx, words, pl.title_max_w); }
  const [asc, desc] = metrics(style.font, size);
  const lineH = Math.floor((asc + desc) * 1.02);
  const padX = Math.floor(size * 0.55), padY = Math.floor(size * 0.35);
  const lineStr = lines.map((l) => l.map((i) => words[i]).join(' '));
  const lineWs = lineStr.map((s) => ctx.measureText(s).width);
  const boxW = Math.max(...lineWs) + padX * 2;
  const boxH = lineH * lines.length + padY * 2;
  const x0 = pl.vertical ? (pl.W - boxW) / 2 : pl.W * 0.04;
  const y0 = pl.title_centered ? pl.title_y - boxH / 2 : pl.title_y;
  if (style.box) {
    ctx.fillStyle = 'rgba(0,0,0,0.3)';
    roundRect(ctx, x0 + 6, y0 + 10, boxW, boxH, size * 0.45);
    ctx.fillStyle = rgba(style.box);
    roundRect(ctx, x0, y0, boxW, boxH, size * 0.45);
  }
  const stroke = style.stroke ? Math.max(4, Math.floor(size / 10)) : 0;
  ctx.textBaseline = 'alphabetic';
  lineStr.forEach((s, li) => {
    const lx = pl.vertical ? (pl.W - lineWs[li]) / 2 : x0 + padX;
    const ly = y0 + padY + li * lineH - size * 0.04 + asc;
    if (stroke) { ctx.lineWidth = stroke * 2; ctx.strokeStyle = rgba(style.stroke, '#000'); ctx.lineJoin = 'round'; ctx.strokeText(s, lx, ly); }
    ctx.fillStyle = rgba(style.color);
    ctx.fillText(s, lx, ly);
  });
}

function drawWatermark(ctx, pl, text) {
  text = stripEmoji(text);
  if (!text) return;
  const size = pl.wm_size;
  ctx.font = fontSpec('poppins-bold', size);
  const tw = ctx.measureText(text).width;
  const [asc, desc] = metrics('poppins-bold', size);
  const th = asc + desc, dot = th * 0.55, pad = size * 0.45;
  const total = dot + pad * 0.8 + tw;
  const x = pl.vertical ? (pl.W - total) / 2 : pl.W - total - pl.W * 0.03;
  const y = pl.vertical ? pl.wm_y - th : pl.H * 0.05;
  ctx.fillStyle = 'rgba(14,14,16,0.59)';
  roundRect(ctx, x - pad, y - pad * 0.45, total + pad * 2, th + pad * 0.8, th * 0.6);
  ctx.fillStyle = '#9146ff';
  ctx.beginPath(); ctx.arc(x + dot / 2, y + th / 2 + th * 0.04, dot / 2, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = 'rgba(255,255,255,0.92)';
  ctx.textBaseline = 'alphabetic';
  ctx.fillText(text, x + dot + pad * 0.8, y + asc);
}

const STRIP_PUNCT = /[,.;:…]+$/;
function buildGroups(transcript, start, end, maxWords, maxChars, upper) {
  if (!transcript) return [];
  const words = [];
  for (const seg of transcript.segments || []) {
    (seg.words || []).forEach((w, i) => {
      if (w.e <= start || w.s >= end) return;
      let t = w.w.trim().replace(STRIP_PUNCT, '').replace('’', "'");
      if (upper) t = t.toUpperCase();
      if (!t) return;
      words.push({ w: t, s: Math.max(0, w.s - start), e: Math.min(end, w.e) - start, brk: i === seg.words.length - 1 || /[.!?…]$/.test(w.w.trim()) });
    });
  }
  const groups = [];
  let cur = [];
  const flush = () => { if (cur.length) { groups.push({ words: cur, start: cur[0].s, end: cur[cur.length - 1].e }); cur = []; } };
  for (const w of words) {
    if (cur.length) {
      const chars = cur.reduce((a, x) => a + x.w.length + 1, 0) + w.w.length;
      const gap = w.s - cur[cur.length - 1].e;
      if (cur.length >= maxWords || chars > maxChars || gap > 0.7 || cur[cur.length - 1].brk) flush();
    }
    cur.push(w);
  }
  flush();
  for (let i = 0; i < groups.length - 1; i++) {
    const a = groups[i], b = groups[i + 1];
    a.end = b.start - a.end < 0.6 ? b.start : Math.min(a.end + 0.3, b.start);
  }
  if (groups.length) groups[groups.length - 1].end = Math.min(end - start, groups[groups.length - 1].end + 0.4);
  return groups.filter((g) => g.end - g.start > 0.05);
}

// ---------------------------------------------------------------------------
// Éditeur
// ---------------------------------------------------------------------------
function EditorView(id) {
  const app = $('#app');
  let P = null;
  let edit = null;
  let tab = store.get('edTab', 'cadrage');
  let previewKey = store.get('previewKey', 'tiktok');
  let showSafe = false;
  let expFormats = store.get('formats', (SETTINGS && SETTINGS.default_formats) || ['tiktok', 'reels', 'shorts']);
  let destroyed = false;
  let pollTimer = null, saveTimer = null, raf = null;
  let video = null, canvas = null, ctx = null, small = null;
  let jobs = [];
  let groupsCache = { key: '', groups: [] };
  let resultSig = {};
  let rendered = false;
  let pubData = null;
  let pubVariant = 0;
  let pubPlatform = store.get('pubPlatform', 'tiktok');

  app.innerHTML = '<div class="empty">Chargement du projet…</div>';

  // ---- Chargement / rafraîchissement --------------------------------------
  async function load() {
    try { P = await api(`/api/projects/${id}`); } catch (err) {
      app.innerHTML = `<div class="card empty"><p>${esc(err.message)}</p><a class="btn" href="#/">Retour</a></div>`;
      return;
    }
    jobs = P.jobs || [];
    edit = P.edit;
    if (P.source) renderEditor(); else renderWaiting();
    schedulePoll();
  }

  function activeJobs() { return jobs.filter((j) => j.status === 'en_cours' || j.status === 'attente'); }

  function schedulePoll() {
    clearTimeout(pollTimer);
    if (destroyed) return;
    const fast = activeJobs().length || !P.source;
    pollTimer = setTimeout(poll, fast ? 1000 : 4000);
  }

  async function poll() {
    if (destroyed) return;
    let fresh;
    try { fresh = await api(`/api/projects/${id}`); } catch { schedulePoll(); return; }
    if (destroyed) return;
    const before = Object.fromEntries(jobs.map((j) => [j.id, j.status]));
    jobs = fresh.jobs || [];
    const justDone = jobs.filter((j) => j.status === 'fini' && before[j.id] && before[j.id] !== 'fini');
    const justFailed = jobs.filter((j) => j.status === 'erreur' && before[j.id] && before[j.id] !== 'erreur');
    justFailed.forEach((j) => toast(`${j.label} : ${j.error}`, 'err'));

    if (!P.source && fresh.source) { P = fresh; edit = fresh.edit; renderEditor(); schedulePoll(); return; }
    if (!fresh.source) { P = fresh; renderWaiting(); schedulePoll(); return; }

    P.exports = fresh.exports; P.descriptions = fresh.descriptions; P.status = fresh.status;
    for (const j of justDone) {
      if (j.kind === 'sous-titres') {
        P.transcript = fresh.transcript;
        edit.captions.enabled = fresh.edit.captions.enabled;
        groupsCache.key = '';
        toast('Sous-titres prêts ✓', 'ok');
        if (tab === 'soustitres') renderTab();
      } else if (j.kind === 'analyse') {
        ['layout', 'split_ratio', 'cam', 'game', 'crop', 'auto_reason'].forEach((k) => { edit[k] = fresh.edit[k]; });
        renderRects(); renderTab(); draw();
        toast(j.message || 'Cadrage mis à jour', 'ok');
      } else if (j.kind.startsWith('export:')) {
        toast(`${j.label} : vidéo prête ✓`, 'ok');
      }
    }
    updateJobsUI();
    schedulePoll();
  }

  function renderWaiting() {
    const errored = P.status === 'erreur';
    app.innerHTML = `<div class="editor-head"><a class="btn btn-ghost icon-btn" href="#/" aria-label="Retour">${ICON.back}</a><h2 style="margin:0">${esc(P.title)}</h2></div>
      <div class="card stack" style="max-width:640px;margin:30px auto;text-align:center">
        ${errored ? `<h2>Oups, l'import a échoué</h2><div class="err-box">${esc(P.error || 'Erreur inconnue')}</div>
          <div class="row" style="justify-content:center"><a class="btn" href="#/">Retour à l'accueil</a></div>`
        : `<div class="spinner" style="width:42px;height:42px;margin:0 auto;color:var(--accent)"></div>
          <h2>${esc(P.status_text || 'Import en cours…')}</h2>
          <div id="waitJobs" class="stack"></div>`}
      </div>`;
    updateJobsUI();
  }

  // ---- Interface principale -------------------------------------------------
  function renderEditor() {
    rendered = true;
    const src = P.source;
    app.innerHTML = `
      <div class="editor-head">
        <a class="btn btn-ghost icon-btn" href="#/" aria-label="Retour">${ICON.back}</a>
        <input class="title-input" id="titleIn" value="${esc(P.title)}" aria-label="Nom du projet">
        <span class="save-state" id="saveState"></span>
        <button class="btn-primary" id="goExport">${ICON.film} Exporter</button>
      </div>
      <div class="editor">
        <div class="ed-src">
          <div class="panel">
            <div class="stage-wrap"><div class="stage" id="stage" style="aspect-ratio:${src.width}/${src.height}">
              <video id="video" playsinline webkit-playsinline preload="auto" src="/api/projects/${id}/video"></video>
              <div id="rects"></div>
            </div></div>
            <div class="transport">
              <button class="btn-primary icon-btn" id="playBtn" aria-label="Lecture">${ICON.play}</button>
              <span class="time" id="timeLbl">0:00.0</span>
              <button class="btn-sm" id="setStart" title="Raccourci : I">⇤ Début ici</button>
              <button class="btn-sm" id="setEnd" title="Raccourci : O">Fin ici ⇥</button>
              <button class="btn-ghost icon-btn" id="muteBtn" aria-label="Son" style="margin-left:auto">${ICON.sound}</button>
            </div>
            <div class="timeline" id="timeline">
              <div class="track"></div><div id="hlMarks"></div><div class="sel" id="tlSel"></div>
              <div class="knob" id="kStart" aria-label="Début"></div><div class="knob" id="kEnd" aria-label="Fin"></div>
              <div class="play" id="tlPlay"></div>
            </div>
            <div class="trim-fields">
              <label class="field">Début<input type="text" id="startIn" inputmode="decimal"></label>
              <label class="field">Fin<input type="text" id="endIn" inputmode="decimal"></label>
              <div><div class="muted small">Durée du clip</div><div style="font-weight:800;font-size:1.3rem" id="durLbl"></div></div>
            </div>
            <div class="duration-info" id="durInfo"></div>
          </div>
          ${P.highlights && P.highlights.length ? `<div class="panel"><div class="panel-title"><h3>🔥 Moments forts détectés</h3></div>
            <p class="muted small" style="margin-top:-6px">Passages où ça crie, rit ou s'emballe le plus. Touche pour les sélectionner.</p>
            <div class="highlights">${P.highlights.map((h, i) => `<button class="btn-sm" data-hl="${i}">#${i + 1} · ${fmtTime(h.start, false)} → ${fmtTime(h.end, false)}</button>`).join('')}</div></div>` : ''}
        </div>
        <div class="ed-set">
          <div class="panel" id="settingsPanel">
            <div class="tabs-ed" id="edTabs">
              <button data-t="cadrage">Cadrage</button><button data-t="textes">Textes</button>
              <button data-t="soustitres">Sous-titres</button><button data-t="options">Options</button>
              <button data-t="exporter">Exporter</button>
            </div>
            <div id="tabBody"></div>
          </div>
        </div>
        <div class="preview-col">
          <div class="panel">
            <div class="preview-tools">
              <div class="seg" id="pvSeg">${Object.entries(INFO.platforms).map(([k, p]) => `<button data-k="${k}"><span class="dot ${k}"></span>${esc(p.label.replace('Instagram ', '').replace('YouTube Shorts', 'Shorts'))}</button>`).join('')}</div>
            </div>
            <div class="preview-box"><div class="phone" id="phone"><canvas id="cv"></canvas></div></div>
            <label class="switch small" style="margin-top:8px"><span class="muted">Montrer les zones cachées par l'appli</span><input type="checkbox" id="safeChk"><span class="knob"></span></label>
          </div>
        </div>
      </div>`;
    video = $('#video');
    canvas = $('#cv');
    ctx = canvas.getContext('2d');
    small = document.createElement('canvas');
    video.muted = store.get('muted', false);
    updateMuteIcon();

    video.addEventListener('loadedmetadata', () => { video.currentTime = edit.start || 0; sizePreview(); draw(); });
    video.addEventListener('seeked', draw);
    video.addEventListener('loadeddata', draw);
    video.addEventListener('play', () => { $('#playBtn').innerHTML = ICON.pause; loop(); });
    video.addEventListener('pause', () => { $('#playBtn').innerHTML = ICON.play; cancelAnimationFrame(raf); draw(); });
    $('#playBtn').addEventListener('click', togglePlay);
    $('#muteBtn').addEventListener('click', () => { video.muted = !video.muted; store.set('muted', video.muted); updateMuteIcon(); });
    $('#setStart').addEventListener('click', () => setTrim(video.currentTime, null));
    $('#setEnd').addEventListener('click', () => setTrim(null, video.currentTime));
    $('#startIn').addEventListener('change', (e) => { const v = parseTime(e.target.value); if (v != null) setTrim(v, null, true); else renderTrim(); });
    $('#endIn').addEventListener('change', (e) => { const v = parseTime(e.target.value); if (v != null) setTrim(null, v, true); else renderTrim(); });
    $('#titleIn').addEventListener('input', () => scheduleSave());
    $('#goExport').addEventListener('click', () => { tab = 'exporter'; renderTab(); $('#settingsPanel').scrollIntoView({ behavior: 'smooth', block: 'start' }); });
    $('#safeChk').addEventListener('change', (e) => { showSafe = e.target.checked; draw(); });
    $('#pvSeg').addEventListener('click', (e) => {
      const b = e.target.closest('button'); if (!b) return;
      previewKey = b.dataset.k; store.set('previewKey', previewKey); markPreviewSeg(); sizePreview(); draw();
    });
    $$('[data-hl]').forEach((b) => b.addEventListener('click', () => {
      const h = P.highlights[+b.dataset.hl];
      setTrim(h.start, h.end, true);
      video.currentTime = h.start;
    }));
    $('#edTabs').addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) { tab = b.dataset.t; store.set('edTab', tab); renderTab(); } });
    setupTimeline();
    markPreviewSeg();
    renderTrim();
    renderRects();
    renderTab();
    sizePreview();
    fontsReady.then(draw);
  }

  function updateMuteIcon() { $('#muteBtn').innerHTML = video.muted ? ICON.mute : ICON.sound; }
  function markPreviewSeg() { $$('#pvSeg button').forEach((b) => b.classList.toggle('on', b.dataset.k === previewKey)); }

  function togglePlay() {
    if (!video) return;
    if (video.paused) {
      const end = edit.end ?? P.source.duration;
      if (video.currentTime < edit.start || video.currentTime >= end - 0.05) video.currentTime = edit.start;
      video.play().catch(() => { });
    } else video.pause();
  }

  function loop() {
    cancelAnimationFrame(raf);
    const tick = () => {
      if (destroyed || !video) return;
      const end = edit.end ?? P.source.duration;
      if (!video.paused && video.currentTime >= end - 0.02) video.currentTime = edit.start;
      draw();
      if (!video.paused) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
  }

  // ---- Découpe (début / fin) -----------------------------------------------
  function setTrim(s, e, fromField = false) {
    const dur = P.source.duration;
    let start = s != null ? s : edit.start;
    let end = e != null ? e : (edit.end ?? dur);
    start = clamp(start, 0, dur - 0.5);
    end = clamp(end, start + 0.5, dur);
    if (s != null && !fromField && end <= start) end = Math.min(dur, start + 0.5);
    edit.start = +start.toFixed(2);
    edit.end = +end.toFixed(2);
    groupsCache.key = '';
    renderTrim();
    scheduleSave();
    draw();
  }

  function renderTrim() {
    const dur = P.source.duration;
    const s = edit.start || 0, e = edit.end ?? dur;
    const pc = (v) => `${(v / dur) * 100}%`;
    $('#tlSel').style.left = pc(s);
    $('#tlSel').style.width = `${((e - s) / dur) * 100}%`;
    $('#kStart').style.left = pc(s);
    $('#kEnd').style.left = pc(e);
    if (document.activeElement !== $('#startIn')) $('#startIn').value = fmtTime(s);
    if (document.activeElement !== $('#endIn')) $('#endIn').value = fmtTime(e);
    const len = e - s;
    $('#durLbl').textContent = fmtDur(len);
    $('#durInfo').innerHTML = Object.entries(INFO.platforms).map(([k, p]) => {
      const ok = !p.max_duration || len <= p.max_duration;
      return `<span class="badge ${ok ? 'ok' : 'err'}" title="Conseillé : ${esc(p.recommended)}"><span class="dot ${k}"></span>${esc(p.label)} ${ok ? '✓' : `: coupé à ${fmtDur(p.max_duration)}`}</span>`;
    }).join('');
    $('#hlMarks').innerHTML = (P.highlights || []).map((h, i) => `<div class="hl" data-hlm="${i}" style="left:${pc(h.start)};width:${((h.end - h.start) / dur) * 100}%" title="Moment fort #${i + 1}"></div>`).join('');
  }

  function setupTimeline() {
    const tl = $('#timeline');
    const toTime = (clientX) => {
      const r = tl.getBoundingClientRect();
      return clamp((clientX - r.left) / r.width, 0, 1) * P.source.duration;
    };
    const drag = (el, fn) => {
      el.addEventListener('pointerdown', (e) => {
        e.preventDefault(); e.stopPropagation();
        el.setPointerCapture(e.pointerId);
        const move = (ev) => fn(toTime(ev.clientX));
        const up = () => { el.removeEventListener('pointermove', move); el.removeEventListener('pointerup', up); el.removeEventListener('pointercancel', up); };
        el.addEventListener('pointermove', move);
        el.addEventListener('pointerup', up);
        el.addEventListener('pointercancel', up);
      });
    };
    drag($('#kStart'), (t) => { setTrim(Math.min(t, (edit.end ?? P.source.duration) - 0.5), null, true); video.currentTime = edit.start; });
    drag($('#kEnd'), (t) => { setTrim(null, Math.max(t, edit.start + 0.5), true); video.currentTime = Math.max(edit.start, edit.end - 0.05); });
    tl.addEventListener('pointerdown', (e) => {
      const hl = e.target.closest('[data-hlm]');
      if (hl) { const h = P.highlights[+hl.dataset.hlm]; setTrim(h.start, h.end, true); video.currentTime = h.start; return; }
      video.currentTime = toTime(e.clientX);
      tl.setPointerCapture(e.pointerId);
      const move = (ev) => { video.currentTime = toTime(ev.clientX); };
      const up = () => { tl.removeEventListener('pointermove', move); tl.removeEventListener('pointerup', up); };
      tl.addEventListener('pointermove', move);
      tl.addEventListener('pointerup', up);
    });
  }

  // ---- Cadres sur la vidéo source -------------------------------------------
  function rectDefs() {
    const sw = P.source.width, sh = P.source.height;
    const na = (pxAspect) => (pxAspect * sh) / sw;
    if (edit.layout === 'split') {
      const [top, bottom] = splitHeights(edit.split_ratio);
      return [
        { key: 'game', cls: 'game', label: 'Jeu (en bas)', na: na(1080 / bottom) },
        { key: 'cam', cls: '', label: 'Facecam (en haut)', na: na(1080 / top) },
      ];
    }
    if (edit.layout === 'crop') return [{ key: 'crop', cls: 'crop', label: 'Cadre vertical', na: na(9 / 16) }];
    return [{ key: 'main', cls: 'main', label: 'Partie visible', na: null }];
  }

  function placeRect(el, r) {
    el.style.left = `${r.x * 100}%`; el.style.top = `${r.y * 100}%`;
    el.style.width = `${r.w * 100}%`; el.style.height = `${r.h * 100}%`;
    el.classList.toggle('inside', r.y < 0.08);
  }

  function renderRects() {
    const box = $('#rects');
    if (!box) return;
    box.innerHTML = '';
    for (const def of rectDefs()) {
      const el = document.createElement('div');
      el.className = `rect ${def.cls}`;
      el.innerHTML = `<span class="lbl">${def.label}</span><i class="h nw"></i><i class="h ne"></i><i class="h sw"></i><i class="h se"></i>`;
      placeRect(el, edit[def.key]);
      box.appendChild(el);
      el.addEventListener('pointerdown', (e) => startRectDrag(e, el, def));
    }
  }

  function startRectDrag(e, el, def) {
    e.preventDefault(); e.stopPropagation();
    const stage = $('#stage').getBoundingClientRect();
    const handle = e.target.classList.contains('h') ? [...e.target.classList].find((c) => c.length === 2) : null;
    const r0 = { ...edit[def.key] };
    const sx = e.clientX, sy = e.clientY;
    el.setPointerCapture(e.pointerId);
    const move = (ev) => {
      const px = clamp((ev.clientX - stage.left) / stage.width, 0, 1);
      const py = clamp((ev.clientY - stage.top) / stage.height, 0, 1);
      let r;
      if (!handle) {
        const dx = (ev.clientX - sx) / stage.width, dy = (ev.clientY - sy) / stage.height;
        r = { ...r0, x: clamp(r0.x + dx, 0, 1 - r0.w), y: clamp(r0.y + dy, 0, 1 - r0.h) };
      } else {
        const ax = handle.includes('w') ? r0.x + r0.w : r0.x;
        const ay = handle.includes('n') ? r0.y + r0.h : r0.y;
        let w = Math.max(0.04, Math.abs(px - ax)), h = Math.max(0.04, Math.abs(py - ay));
        if (def.na) { if (w / def.na > h) h = w / def.na; else w = h * def.na; }
        const maxW = handle.includes('w') ? ax : 1 - ax;
        const maxH = handle.includes('n') ? ay : 1 - ay;
        if (w > maxW) { w = maxW; if (def.na) h = w / def.na; }
        if (h > maxH) { h = maxH; if (def.na) w = h * def.na; }
        r = { x: handle.includes('w') ? ax - w : ax, y: handle.includes('n') ? ay - h : ay, w, h };
      }
      edit[def.key] = clampRect(r);
      placeRect(el, edit[def.key]);
      draw();
    };
    const up = () => {
      el.removeEventListener('pointermove', move);
      el.removeEventListener('pointerup', up);
      el.removeEventListener('pointercancel', up);
      scheduleSave();
    };
    el.addEventListener('pointermove', move);
    el.addEventListener('pointerup', up);
    el.addEventListener('pointercancel', up);
  }

  function setLayout(layout) {
    edit.layout = layout;
    const sw = P.source.width, sh = P.source.height;
    const na = (px) => (px * sh) / sw;
    if (layout === 'split') {
      const [top, bottom] = splitHeights(edit.split_ratio);
      edit.cam = fitAspect(edit.cam, na(1080 / top), 'w');
      edit.game = fitAspect(edit.game, na(1080 / bottom), 'h');
    } else if (layout === 'crop') {
      edit.crop = fitAspect(edit.crop, na(9 / 16), 'h');
    }
    renderRects(); renderTab(); draw(); scheduleSave();
  }

  // ---- Aperçu en direct -----------------------------------------------------
  function sizePreview() {
    const phone = $('#phone');
    if (!phone) return;
    const p = INFO.platforms[previewKey];
    const box = $('.preview-box');
    const availW = box.clientWidth - 28;
    const narrow = window.innerWidth <= 1020;
    const maxH = narrow ? Math.min(window.innerHeight * 0.62, 640) : Math.min(window.innerHeight - 260, 720);
    let w, h;
    if (p.vertical) { h = maxH; w = (h * 9) / 16; if (w > availW) { w = availW; h = (w * 16) / 9; } }
    else { w = availW; h = (w * 9) / 16; }
    phone.style.width = `${Math.round(w)}px`;
    phone.style.height = `${Math.round(h)}px`;
    phone.style.borderRadius = p.vertical ? '22px' : '10px';
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
  }

  function drawCover(r, dx, dy, dw, dh) {
    const sw = video.videoWidth, sh = video.videoHeight;
    let rx = r.x * sw, ry = r.y * sh, rw = r.w * sw, rh = r.h * sh;
    const da = dw / dh, ra = rw / rh;
    if (ra > da) { const nw = rh * da; rx += (rw - nw) / 2; rw = nw; } else { const nh = rw / da; ry += (rh - nh) / 2; rh = nh; }
    ctx.drawImage(video, rx, ry, rw, rh, dx, dy, dw, dh);
  }

  function captionGroups(platform) {
    const caps = edit.captions || {};
    const style = INFO.caption_styles[caps.style] || INFO.caption_styles.tiktok;
    const key = [platform.vertical, caps.words, style.uppercase, edit.start, edit.end, P.transcript ? P.transcript.segments.length : 0, P.transcriptVersion || 0].join('|');
    if (groupsCache.key !== key) {
      groupsCache = {
        key,
        groups: buildGroups(P.transcript, edit.start || 0, edit.end ?? P.source.duration, +caps.words || 3, platform.vertical ? 22 : 38, style.uppercase !== false),
      };
    }
    return groupsCache.groups;
  }

  function draw() {
    if (!ctx || !video || destroyed) return;
    const p = INFO.platforms[previewKey];
    const W = p.width, H = p.height;
    const s = canvas.width / W;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.setTransform(s, 0, 0, s, 0, 0);
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, W, H);
    const ready = video.readyState >= 2 && video.videoWidth;
    if (ready) {
      const sw = video.videoWidth, sh = video.videoHeight;
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';
      if (!p.vertical) {
        const sc = Math.min(W / sw, H / sh);
        ctx.drawImage(video, (W - sw * sc) / 2, (H - sh * sc) / 2, sw * sc, sh * sc);
      } else if (edit.layout === 'split') {
        const [top, bottom] = splitHeights(edit.split_ratio, H);
        drawCover(edit.cam, 0, 0, W, top);
        drawCover(edit.game, 0, top, W, bottom);
        ctx.fillStyle = 'rgba(0,0,0,0.85)';
        ctx.fillRect(0, top - 3, W, 6);
      } else if (edit.layout === 'crop') {
        drawCover(edit.crop, 0, 0, W, H);
      } else {
        small.width = 45; small.height = 80;
        const sctx = small.getContext('2d');
        const sa = sw / sh, ta = 45 / 80;
        let cx = 0, cy = 0, cw = sw, ch = sh;
        if (sa > ta) { cw = sh * ta; cx = (sw - cw) / 2; } else { ch = sw / ta; cy = (sh - ch) / 2; }
        sctx.drawImage(video, cx, cy, cw, ch, 0, 0, 45, 80);
        ctx.filter = 'blur(18px) brightness(0.85) saturate(1.25)';
        ctx.drawImage(small, -40, -40, W + 80, H + 80);
        ctx.filter = 'none';
        const m = edit.main;
        const zoom = clamp(+edit.blur_zoom || 1, 1, 1.8);
        const fw = W * zoom;
        const fh = fw * ((m.h * sh) / (m.w * sw));
        ctx.drawImage(video, m.x * sw, m.y * sh, m.w * sw, m.h * sh, (W - fw) / 2, (H - fh) / 2 + (+edit.blur_offset || 0) * H, fw, fh);
      }
    }
    // Textes
    const t = (video.currentTime || 0) - (edit.start || 0);
    const clipLen = (edit.end ?? P.source.duration) - (edit.start || 0);
    const pl = computePlacement(previewKey, edit);
    if (edit.watermark && edit.watermark.enabled) drawWatermark(ctx, pl, edit.watermark.text);
    const caps = edit.captions || {};
    if (caps.enabled && P.transcript) {
      const style = INFO.caption_styles[caps.style] || INFO.caption_styles.tiktok;
      const groups = captionGroups(p);
      const g = groups.find((gr) => gr.start <= t && t < gr.end);
      if (g) {
        let wi = 0;
        g.words.forEach((w, j) => { if (w.s <= t) wi = j; });
        drawCaption(ctx, pl, g.words.map((w) => w.w), caps.highlight === false ? null : wi, style);
      }
    }
    const title = edit.title || {};
    if (title.enabled && (title.text || '').trim()) {
      const d = +title.duration || 0;
      if (!d || t < d || video.paused && t < 0.05) drawTitle(ctx, pl, title.text, INFO.title_styles[title.style] || INFO.title_styles.blanc);
    }
    if (edit.progress_bar) {
      const bh = p.vertical ? 12 : 10;
      ctx.fillStyle = '#9146ff';
      ctx.fillRect(0, p.vertical ? 0 : H - bh, W * clamp(t / clipLen, 0, 1), bh);
    }
    if (showSafe && p.vertical) {
      ctx.fillStyle = 'rgba(248,113,113,0.33)';
      ctx.fillRect(0, 0, W, H * p.safe_top);
      ctx.fillRect(0, H * (1 - p.safe_bottom), W, H * p.safe_bottom);
      ctx.fillRect(W * (1 - p.safe_right), H * p.safe_top, W * p.safe_right, H * (1 - p.safe_top - p.safe_bottom));
    }
    // Temps et curseur
    $('#timeLbl').textContent = `${fmtTime(video.currentTime)} / ${fmtTime(P.source.duration)}`;
    $('#tlPlay').style.left = `${((video.currentTime || 0) / P.source.duration) * 100}%`;
  }

  // ---- Enregistrement automatique -------------------------------------------
  function scheduleSave() {
    clearTimeout(saveTimer);
    const st = $('#saveState');
    if (st) st.textContent = 'Modifications…';
    saveTimer = setTimeout(save, 600);
  }
  async function save() {
    try {
      await api(`/api/projects/${id}/edit`, { method: 'PUT', json: { edit, title: $('#titleIn') ? $('#titleIn').value : undefined } });
      const st = $('#saveState');
      if (st) st.textContent = 'Enregistré ✓';
    } catch (err) {
      const st = $('#saveState');
      if (st) st.textContent = 'Non enregistré';
      toast(err.message, 'err');
    }
  }
  async function flushSave() { if (saveTimer) { clearTimeout(saveTimer); saveTimer = null; await save(); } }

  // ---- Onglets de réglages --------------------------------------------------
  const sw = (id2, label, checked, hint = '') => `<label class="switch"><span>${label}${hint ? `<br><span class="muted small">${hint}</span>` : ''}</span><input type="checkbox" id="${id2}" ${checked ? 'checked' : ''}><span class="knob"></span></label>`;
  const seg = (id2, options, current) => `<div class="seg" id="${id2}">${options.map(([v, l]) => `<button data-v="${esc(v)}" class="${String(v) === String(current) ? 'on' : ''}">${l}</button>`).join('')}</div>`;
  const onSeg = (id2, fn) => { const el = $('#' + id2); if (el) el.addEventListener('click', (e) => { const b = e.target.closest('button'); if (!b) return; $$('button', el).forEach((x) => x.classList.toggle('on', x === b)); fn(b.dataset.v); }); };

  function renderTab() {
    $$('#edTabs button').forEach((b) => b.classList.toggle('on', b.dataset.t === tab));
    const body = $('#tabBody');
    if (!body) return;
    resultSig = {};
    if (tab === 'cadrage') {
      const L = edit.layout;
      body.innerHTML = `<div class="layout-choices">
          <button class="layout-choice ${L === 'split' ? 'on' : ''}" data-l="split"><span class="mini"><span class="c" style="flex:0 0 38%"></span><span class="g"></span></span>Facecam + jeu</button>
          <button class="layout-choice ${L === 'blur' ? 'on' : ''}" data-l="blur"><span class="mini blur"><span class="g"></span></span>Vidéo entière<br>fond flou</button>
          <button class="layout-choice ${L === 'crop' ? 'on' : ''}" data-l="crop"><span class="mini crop"></span>Plein écran<br>vertical</button>
        </div>
        <div class="row" style="margin-top:12px"><button id="autoBtn">${ICON.magic} Cadrage automatique</button><span class="muted small" id="autoJob"></span></div>
        ${edit.auto_reason ? `<div class="auto-reason">✨ ${esc(edit.auto_reason)}</div>` : ''}
        <div class="stack" style="margin-top:14px">
          ${L === 'split' ? `<label class="field">Hauteur de la facecam : <b id="ratioLbl">${Math.round(edit.split_ratio * 100)} %</b><input type="range" id="ratioIn" min="0.2" max="0.6" step="0.01" value="${edit.split_ratio}"></label>
            <p class="muted small">Déplace le cadre <b style="color:var(--cam)">violet</b> sur la facecam et le cadre <b style="color:var(--game)">vert</b> sur le jeu, directement sur la vidéo. Tire sur les ronds blancs pour agrandir.</p>` : ''}
          ${L === 'blur' ? `<label class="field">Zoom : <b id="zoomLbl">${Math.round((edit.blur_zoom || 1) * 100)} %</b><input type="range" id="zoomIn" min="1" max="1.8" step="0.02" value="${edit.blur_zoom || 1}"></label>
            <label class="field">Position verticale<input type="range" id="offIn" min="-0.3" max="0.3" step="0.01" value="${edit.blur_offset || 0}"></label>
            <p class="muted small">Le cadre bleu sur la vidéo choisit la partie gardée (par défaut, toute l'image).</p>` : ''}
          ${L === 'crop' ? '<p class="muted small">Fais glisser le cadre jaune sur la vidéo pour choisir ce qui reste dans le format vertical.</p>' : ''}
        </div>`;
      $$('.layout-choice', body).forEach((b) => b.addEventListener('click', () => setLayout(b.dataset.l)));
      $('#autoBtn').addEventListener('click', async () => {
        try { await flushSave(); await api(`/api/projects/${id}/analyze`, { method: 'POST' }); toast('Analyse en cours…'); poll(); } catch (err) { toast(err.message, 'err'); }
      });
      const ratio = $('#ratioIn');
      if (ratio) ratio.addEventListener('input', () => {
        edit.split_ratio = +ratio.value;
        $('#ratioLbl').textContent = `${Math.round(edit.split_ratio * 100)} %`;
        const sh = P.source.height, swd = P.source.width;
        const [top, bottom] = splitHeights(edit.split_ratio);
        edit.cam = fitAspect(edit.cam, ((1080 / top) * sh) / swd, 'w');
        edit.game = fitAspect(edit.game, ((1080 / bottom) * sh) / swd, 'h');
        renderRects(); draw(); scheduleSave();
      });
      const zoom = $('#zoomIn');
      if (zoom) zoom.addEventListener('input', () => { edit.blur_zoom = +zoom.value; $('#zoomLbl').textContent = `${Math.round(edit.blur_zoom * 100)} %`; draw(); scheduleSave(); });
      const off = $('#offIn');
      if (off) off.addEventListener('input', () => { edit.blur_offset = +off.value; draw(); scheduleSave(); });
    } else if (tab === 'textes') {
      const T = edit.title, Wm = edit.watermark;
      body.innerHTML = `<div class="stack">
        ${sw('titleOn', '<b>Titre accrocheur</b>', T.enabled, 'Le texte qui donne envie de regarder jusqu\'au bout.')}
        <input type="text" id="titleText" maxlength="90" placeholder="Ex : Il ne s'attendait PAS à ça" value="${esc(T.text)}">
        <p class="muted small" style="margin:-4px 0 0">Les emojis ne s'affichent pas sur la vidéo, mais ils sont gardés dans la description à coller.</p>
        <div><div class="muted small" style="margin-bottom:6px">Affiché pendant</div>${seg('titleDur', [[3, '3 s'], [5, '5 s'], [8, '8 s'], [0, 'Tout le clip']], T.duration ?? 4)}</div>
        <div><div class="muted small" style="margin-bottom:6px">Style</div>${seg('titleStyle', Object.entries(INFO.title_styles).map(([k, v]) => [k, esc(v.label)]), T.style)}</div>
        <hr style="border:0;border-top:1px solid var(--line);width:100%">
        ${sw('wmOn', '<b>Pseudo / chaîne</b>', Wm.enabled, 'Petit encadré pour créditer le streamer.')}
        <input type="text" id="wmText" maxlength="40" placeholder="twitch.tv/pseudo" value="${esc(Wm.text)}">
      </div>`;
      $('#titleOn').addEventListener('change', (e) => { edit.title.enabled = e.target.checked; draw(); scheduleSave(); });
      $('#titleText').addEventListener('input', (e) => { edit.title.text = e.target.value; edit.title.enabled = true; $('#titleOn').checked = true; draw(); scheduleSave(); });
      onSeg('titleDur', (v) => { edit.title.duration = +v; draw(); scheduleSave(); });
      onSeg('titleStyle', (v) => { edit.title.style = v; draw(); scheduleSave(); });
      $('#wmOn').addEventListener('change', (e) => { edit.watermark.enabled = e.target.checked; draw(); scheduleSave(); });
      $('#wmText').addEventListener('input', (e) => { edit.watermark.text = e.target.value; edit.watermark.enabled = !!e.target.value.trim(); $('#wmOn').checked = edit.watermark.enabled; draw(); scheduleSave(); });
    } else if (tab === 'soustitres') {
      const C = edit.captions;
      const has = P.transcript && P.transcript.segments.length;
      const running = jobs.find((j) => j.kind === 'sous-titres' && (j.status === 'en_cours' || j.status === 'attente'));
      body.innerHTML = `<div class="stack">
        ${sw('capOn', '<b>Sous-titres animés</b>', C.enabled, 'Générés automatiquement à partir de la voix, mot par mot.')}
        ${INFO.whisper ? '' : '<div class="err-box">Le module d\'IA n\'est pas installé : relance le lanceur ClipForge (il l\'installe tout seul) ou tape « pip install faster-whisper ».</div>'}
        <div class="row" style="align-items:flex-end">
          <label class="field grow">Langue parlée dans le clip<select id="capSpoken">${Object.entries(INFO.languages).map(([k, l]) => `<option value="${k}" ${k === (C.spoken || 'auto') ? 'selected' : ''}>${k === 'auto' ? 'Auto (langue de la chaîne Twitch)' : esc(l)}</option>`).join('')}</select></label>
        </div>
        ${sw('capEn', '<b>Sous-titres en anglais</b>', !!C.english, 'Traduit la voix en anglais (si le clip est déjà en anglais, rien ne change).')}
        ${has ? `<div class="auto-reason">Sous-titres actuels : <b>${esc((INFO.languages[P.transcript.language] || P.transcript.language || '').toLowerCase())}</b>${P.transcript.translated ? ` (traduits depuis : ${esc((INFO.languages[P.transcript.spoken] || P.transcript.spoken || '').toLowerCase())})` : ''}${(!!C.english !== !!P.transcript.translated && P.transcript.spoken !== 'en') ? ' · <b style="color:var(--warn)">Regénère pour appliquer le changement de langue.</b>' : ''}</div>` : ''}
        <div class="row"><button class="${has ? '' : 'btn-primary'}" id="genBtn" ${INFO.whisper && !running ? '' : 'disabled'}>${ICON.magic} ${has ? 'Regénérer les sous-titres' : 'Générer les sous-titres (IA)'}</button></div>
        <div id="capJob"></div>
        <div><div class="muted small" style="margin-bottom:6px">Style</div>${seg('capStyle', Object.entries(INFO.caption_styles).map(([k, v]) => [k, esc(v.label)]), C.style)}</div>
        <div class="row" style="align-items:flex-start;gap:18px">
          <div><div class="muted small" style="margin-bottom:6px">Mots par bloc</div>${seg('capWords', [[1, '1'], [2, '2'], [3, '3'], [4, '4'], [5, '5']], C.words)}</div>
          <div><div class="muted small" style="margin-bottom:6px">Taille</div>${seg('capSize', [['petit', 'Petit'], ['moyen', 'Moyen'], ['grand', 'Grand']], C.size)}</div>
        </div>
        <div><div class="muted small" style="margin-bottom:6px">Position</div>${seg('capPos', [['auto', 'Auto'], ['haut', 'Haut'], ['milieu', 'Milieu'], ['bas', 'Bas']], C.position)}</div>
        ${sw('capHl', 'Colorer le mot prononcé', C.highlight !== false)}
        ${has ? `<div><h3 style="margin-top:6px">Corriger le texte</h3><p class="muted small" style="margin-top:-4px">Touche l'heure pour aller au passage. Les changements sont pris en compte à l'export.</p>
          <div class="seg-list" id="segList">${P.transcript.segments.map((s, i) => `<div class="seg-item"><span class="t" data-seek="${s.start}">${fmtTime(s.start, false)}</span><textarea data-i="${i}" rows="2">${esc(s.text)}</textarea></div>`).join('')}</div></div>` : ''}
      </div>`;
      $('#capOn').addEventListener('change', (e) => { edit.captions.enabled = e.target.checked; draw(); scheduleSave(); });
      $('#capSpoken').addEventListener('change', (e) => { edit.captions.spoken = e.target.value; scheduleSave(); });
      $('#capEn').addEventListener('change', (e) => { edit.captions.english = e.target.checked; scheduleSave(); renderTab(); });
      $('#genBtn').addEventListener('click', async () => {
        try { await flushSave(); await api(`/api/projects/${id}/transcribe`, { method: 'POST' }); $('#genBtn').disabled = true; poll(); } catch (err) { toast(err.message, 'err'); }
      });
      onSeg('capStyle', (v) => { edit.captions.style = v; groupsCache.key = ''; draw(); scheduleSave(); });
      onSeg('capWords', (v) => { edit.captions.words = +v; groupsCache.key = ''; draw(); scheduleSave(); });
      onSeg('capSize', (v) => { edit.captions.size = v; draw(); scheduleSave(); });
      onSeg('capPos', (v) => { edit.captions.position = v; draw(); scheduleSave(); });
      $('#capHl').addEventListener('change', (e) => { edit.captions.highlight = e.target.checked; draw(); scheduleSave(); });
      const list = $('#segList');
      if (list) {
        list.addEventListener('click', (e) => { const t = e.target.closest('[data-seek]'); if (t) video.currentTime = +t.dataset.seek; });
        list.addEventListener('change', async (e) => {
          const ta = e.target.closest('textarea'); if (!ta) return;
          const segs = P.transcript.segments.map((s, i) => ({ text: i === +ta.dataset.i ? ta.value : s.text }));
          try {
            P.transcript = await api(`/api/projects/${id}/transcript`, { method: 'PUT', json: { segments: segs } });
            P.transcriptVersion = (P.transcriptVersion || 0) + 1;
            groupsCache.key = '';
            draw();
            $('#saveState').textContent = 'Enregistré ✓';
          } catch (err) { toast(err.message, 'err'); }
        });
      }
    } else if (tab === 'options') {
      body.innerHTML = `<div class="stack">
        ${sw('pbOn', '<b>Barre de progression</b>', edit.progress_bar, 'Une barre violette qui avance en haut de la vidéo : ça pousse à regarder jusqu\'au bout.')}
        ${sw('normOn', '<b>Son optimisé</b>', edit.normalize_audio, 'Volume égalisé au niveau conseillé pour TikTok, Instagram et YouTube.')}
        ${sw('fadeOn', '<b>Fondu au début et à la fin</b>', edit.fade)}
      </div>`;
      $('#pbOn').addEventListener('change', (e) => { edit.progress_bar = e.target.checked; draw(); scheduleSave(); });
      $('#normOn').addEventListener('change', (e) => { edit.normalize_audio = e.target.checked; scheduleSave(); });
      $('#fadeOn').addEventListener('change', (e) => { edit.fade = e.target.checked; scheduleSave(); });
    } else if (tab === 'exporter') {
      const len = (edit.end ?? P.source.duration) - (edit.start || 0);
      body.innerHTML = `<div class="stack">
        <div class="exp-grid" id="expGrid">${Object.entries(INFO.platforms).map(([k, p]) => `
          <label class="exp-option ${expFormats.includes(k) ? 'on' : ''}"><input type="checkbox" value="${k}" ${expFormats.includes(k) ? 'checked' : ''}>
            <span class="dot ${k}"></span><span class="info"><b>${esc(p.label)}</b><span>${p.width}×${p.height}${p.max_duration && len > p.max_duration ? ` · coupé à ${fmtDur(p.max_duration)}` : ''}</span></span></label>`).join('')}</div>
        <button class="btn-primary btn-big" id="renderBtn">${ICON.film} Créer les vidéos</button>
        <div class="row" style="justify-content:space-between">
          <p class="muted small" style="margin:0;flex:1 1 240px">${INFO.gpu_encoder ? `Accélération carte graphique active (${esc(INFO.gpu_encoder)}).` : 'Encodage par le processeur.'} Les vidéos sont aussi rangées dans le dossier du projet sur le PC.</p>
          ${INFO.is_local ? '<button class="btn-sm" id="openFolder">📂 Ouvrir le dossier</button>' : ''}
        </div>
        <div id="results" class="stack"></div>
        <div class="pub">
          <div class="panel-title" style="flex-wrap:wrap"><h3 style="margin:0">📝 Textes pour publier</h3>
            ${seg('pubLang', [['auto', 'Auto'], ['en', 'Anglais'], ['fr', 'Français']], edit.publish_lang || 'auto')}</div>
          <div class="seg" id="pubPlat">${Object.entries(INFO.platforms).map(([k, p]) => `<button data-v="${k}" class="${k === pubPlatform ? 'on' : ''}"><span class="dot ${k}"></span>${esc(p.label.replace('Instagram ', '').replace('YouTube Shorts', 'Shorts'))}</button>`).join('')}</div>
          <div id="pubBody" class="stack" style="margin-top:12px"><span class="muted small">Chargement…</span></div>
        </div>
      </div>`;
      onSeg('pubLang', (v) => { edit.publish_lang = v; pubVariant = 0; scheduleSave(); loadPublish(v); });
      onSeg('pubPlat', (v) => { pubPlatform = v; store.set('pubPlatform', v); renderPublish(); });
      flushSave().then(() => loadPublish());
      $('#expGrid').addEventListener('change', (e) => {
        const k = e.target.value;
        expFormats = e.target.checked ? [...new Set([...expFormats, k])] : expFormats.filter((f) => f !== k);
        store.set('formats', expFormats);
        e.target.closest('.exp-option').classList.toggle('on', e.target.checked);
      });
      const of = $('#openFolder');
      if (of) of.addEventListener('click', () => api(`/api/projects/${id}/open-folder`, { method: 'POST' }).catch((err) => toast(err.message, 'err')));
      $('#renderBtn').addEventListener('click', async () => {
        if (!expFormats.length) { toast('Choisis au moins un format', 'err'); return; }
        try {
          await flushSave();
          await api(`/api/projects/${id}/render`, { method: 'POST', json: { formats: expFormats } });
          toast('Montage lancé !', 'ok');
          poll();
        } catch (err) { toast(err.message, 'err'); }
      });
    }
    updateJobsUI();
  }

  // ---- Textes de publication (description, hashtags, tags) ------------------
  async function loadPublish(lang) {
    try {
      pubData = await api(`/api/projects/${id}/publish?lang=${lang || edit.publish_lang || 'auto'}&variant=${pubVariant}`);
    } catch (err) { pubData = null; toast(err.message, 'err'); }
    renderPublish();
  }

  async function copyText(text, label) {
    try { await navigator.clipboard.writeText(text); } catch {
      const ta = document.createElement('textarea');
      ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove();
    }
    toast(`${label} copié ✓`, 'ok');
  }

  function renderPublish() {
    const box = $('#pubBody');
    if (!box || !pubData) return;
    const e = pubData.platforms[pubPlatform];
    const kinds = { streamer: 'Streamer', jeu: 'Jeu', niche: 'Niche', large: 'Large', format: 'Format' };
    const hasSrt = P.transcript && P.transcript.segments.length && (pubPlatform === 'youtube' || pubPlatform === 'shorts');
    box.innerHTML = `
      ${e.title ? `<label class="field">Titre<input type="text" id="pubTitle" value="${esc(e.title)}" maxlength="100"></label>` : ''}
      <label class="field">Description${pubPlatform === 'shorts' || pubPlatform === 'youtube' ? '' : ' (légende)'}<textarea id="pubText" rows="7">${esc(e.text)}</textarea></label>
      <div><div class="muted small" style="margin-bottom:6px">Hashtags choisis (touche-les pour savoir pourquoi)</div>
        <div class="tags">${e.hashtags.map((h, i) => `<button class="tag ${h.kind}" data-why="${i}">${esc(h.tag)}<small>${kinds[h.kind] || ''}</small></button>`).join('')}</div>
        <p class="muted small" id="pubWhy" style="margin:8px 0 0">${esc(e.hashtags[0] ? `${e.hashtags[0].tag} → ${e.hashtags[0].why}` : '')}</p></div>
      ${e.tags ? `<label class="field">Tags YouTube (champ « Tags » de YouTube Studio)<textarea id="pubTags" rows="3">${esc(e.tags.join(', '))}</textarea></label>` : ''}
      <p class="muted small" style="margin:0">💡 ${esc(e.tip)}</p>
      <div class="row">
        ${e.title ? `<button class="btn-sm" id="cpTitle">${ICON.copy} Copier le titre</button>` : ''}
        <button class="btn-sm btn-primary" id="cpText">${ICON.copy} Copier la description</button>
        ${e.tags ? `<button class="btn-sm" id="cpTags">${ICON.copy} Copier les tags</button>` : ''}
        <button class="btn-sm" id="pubAgain">🔄 Autre version</button>
        ${hasSrt ? `<a class="btn btn-sm" href="/api/projects/${id}/subtitles.srt?platform=${pubPlatform}" download>${ICON.download} Sous-titres .srt</a>` : ''}
      </div>`;
    box.querySelectorAll('[data-why]').forEach((b) => b.addEventListener('click', () => {
      const h = e.hashtags[+b.dataset.why];
      $('#pubWhy').textContent = `${h.tag} → ${h.why}`;
    }));
    const t = $('#cpTitle'); if (t) t.addEventListener('click', () => copyText($('#pubTitle').value, 'Titre'));
    $('#cpText').addEventListener('click', () => copyText($('#pubText').value, 'Description'));
    const tg = $('#cpTags'); if (tg) tg.addEventListener('click', () => copyText($('#pubTags').value, 'Tags'));
    $('#pubAgain').addEventListener('click', () => { pubVariant += 1; loadPublish(); });
  }

  function jobLine(j) {
    return `<div class="job-line"><div class="row"><b class="small">${esc(j.message || j.label)}</b>
      <button class="btn-sm btn-ghost" data-cancel="${j.id}">Annuler</button></div>
      <div class="bar"><i style="width:${Math.round(j.progress * 100)}%"></i></div></div>`;
  }

  function updateJobsUI() {
    const wait = $('#waitJobs');
    if (wait) wait.innerHTML = activeJobs().map(jobLine).join('');
    const autoJob = $('#autoJob');
    if (autoJob) {
      const j = jobs.find((x) => x.kind === 'analyse' && (x.status === 'en_cours' || x.status === 'attente'));
      autoJob.innerHTML = j ? '<span class="spinner" style="display:inline-block;vertical-align:middle"></span> Analyse…' : '';
    }
    const capJob = $('#capJob');
    if (capJob) {
      const j = jobs.find((x) => x.kind === 'sous-titres' && (x.status === 'en_cours' || x.status === 'attente'));
      capJob.innerHTML = j ? jobLine(j) : '';
      const gen = $('#genBtn');
      if (gen) gen.disabled = !!j || !INFO.whisper;
    }
    renderResults();
    $$('[data-cancel]').forEach((b) => { b.onclick = () => api(`/api/jobs/${b.dataset.cancel}/cancel`, { method: 'POST' }).then(poll); });
  }

  function renderResults() {
    const box = $('#results');
    if (!box) return;
    const keys = Object.keys(INFO.platforms).filter((k) => (P.exports || {})[k]);
    if (!keys.length) { box.innerHTML = ''; resultSig = {}; return; }
    if (Object.keys(resultSig).some((k) => !keys.includes(k))) { box.innerHTML = ''; resultSig = {}; }
    for (const k of keys) {
      const ex = P.exports[k];
      const job = jobs.find((j) => j.kind === `export:${k}` && (j.status === 'en_cours' || j.status === 'attente'));
      const status = job ? 'run' : ex.status;
      const sig = `${status}|${ex.finished || ''}|${ex.error || ''}`;
      let card = box.querySelector(`[data-res="${k}"]`);
      if (!card) { card = document.createElement('div'); card.className = 'result'; card.dataset.res = k; box.appendChild(card); }
      if (job) {
        const bar = card.querySelector('.bar i');
        if (resultSig[k] === sig && bar) { bar.style.width = `${Math.round(job.progress * 100)}%`; card.querySelector('.jmsg').textContent = job.message; continue; }
      } else if (resultSig[k] === sig) continue;
      resultSig[k] = sig;
      const p = INFO.platforms[k];
      const head = `<div class="result-head"><span class="dot ${k}"></span><b>${esc(p.label)}</b>`;
      if (job) {
        card.innerHTML = `${head}<span class="badge run">${job.status === 'attente' ? 'En attente' : 'En cours'}</span>
          <button class="btn-sm btn-ghost" data-cancel="${job.id}" style="margin-left:auto">Annuler</button></div>
          <div class="bar"><i style="width:${Math.round(job.progress * 100)}%"></i></div><span class="muted small jmsg">${esc(job.message)}</span>`;
      } else if (ex.status === 'fini') {
        const url = `/api/projects/${id}/exports/${k}?v=${Math.round(ex.finished || 0)}`;
        card.innerHTML = `${head}<span class="badge ok">Prête</span><span class="muted small">${p.width}×${p.height} · ${fmtDur(ex.duration)} · ${fmtSize(ex.size)}</span></div>
          <video controls playsinline preload="metadata" src="${url}"></video>
          <div class="row">
            <a class="btn btn-primary" href="${url}&download=1" download>${ICON.download} Télécharger</a>
            ${navigator.canShare ? `<button data-share="${k}">${ICON.share} Partager</button>` : ''}
            <button class="btn-ghost" data-pub="${k}">📝 Voir la description</button>
          </div>`;
        card.querySelector('[data-pub]').addEventListener('click', () => {
          pubPlatform = k; store.set('pubPlatform', k);
          $$('#pubPlat button').forEach((b) => b.classList.toggle('on', b.dataset.v === k));
          renderPublish();
          $('.pub').scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
        const sh = card.querySelector('[data-share]');
        if (sh) sh.addEventListener('click', () => {
          const text = pubData && pubData.platforms[k] ? pubData.platforms[k].text : '';
          shareVideo(url, `${P.title}_${k}.mp4`, text);
        });
      } else if (ex.status === 'erreur') {
        card.innerHTML = `${head}<span class="badge err">Erreur</span></div><div class="err-box">${esc(ex.error || 'Erreur inconnue')}</div>`;
      } else if (ex.status === 'annule') {
        card.innerHTML = `${head}<span class="badge">Annulé</span></div>`;
      } else {
        card.innerHTML = `${head}<span class="badge run">En attente</span></div>`;
      }
    }
  }

  async function shareVideo(url, name, text) {
    try {
      const blob = await (await fetch(url)).blob();
      const file = new File([blob], name.replace(/[^\w.-]+/g, '_'), { type: 'video/mp4' });
      if (navigator.canShare && navigator.canShare({ files: [file] })) await navigator.share({ files: [file], text });
      else toast('Le partage direct n\'est pas disponible ici : utilise « Télécharger ».', 'err');
    } catch (err) { if (err.name !== 'AbortError') toast('Partage impossible : utilise « Télécharger ».', 'err'); }
  }

  // ---- Raccourcis clavier (PC) ----------------------------------------------
  function onKey(e) {
    if (!video || ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) return;
    if (e.code === 'Space') { e.preventDefault(); togglePlay(); }
    else if (e.key === 'i' || e.key === 'I') setTrim(video.currentTime, null);
    else if (e.key === 'o' || e.key === 'O') setTrim(null, video.currentTime);
    else if (e.key === 'ArrowLeft') video.currentTime = Math.max(0, video.currentTime - (e.shiftKey ? 1 : 1 / 30));
    else if (e.key === 'ArrowRight') video.currentTime = Math.min(P.source.duration, video.currentTime + (e.shiftKey ? 1 : 1 / 30));
  }
  function onResize() { if (rendered) { sizePreview(); draw(); } }
  document.addEventListener('keydown', onKey);
  window.addEventListener('resize', onResize);

  load();
  return {
    destroy() {
      destroyed = true;
      clearTimeout(pollTimer);
      cancelAnimationFrame(raf);
      if (saveTimer) { clearTimeout(saveTimer); save(); }
      document.removeEventListener('keydown', onKey);
      window.removeEventListener('resize', onResize);
      if (video) { video.pause(); video.removeAttribute('src'); video.load(); }
    },
  };
}

// ---------------------------------------------------------------------------
// Bios du compte (TikTok, Instagram, YouTube)
// ---------------------------------------------------------------------------
function BiosView() {
  const app = $('#app');
  app.innerHTML = '<div class="empty">Chargement…</div>';
  let data = null;
  const LABEL = { tiktok: 'TikTok', instagram: 'Instagram', youtube: 'YouTube (description de la chaîne)' };

  async function copy(text, label) {
    try { await navigator.clipboard.writeText(text); } catch {
      const ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove();
    }
    toast(`${label} copié ✓`, 'ok');
  }

  function renderBios(bios) {
    const box = $('#bioRes');
    box.innerHTML = `<div class="bio-grid">${['tiktok', 'instagram', 'youtube'].map((k) => `
        <div class="card stack"><h3><span class="dot ${k === 'instagram' ? 'reels' : k}"></span> ${LABEL[k]}</h3>
          <p class="muted small" style="margin:-6px 0 0">Limite : ${bios.limits[k]} caractères</p>
          ${bios[k].map((txt, i) => `<div class="bio-option"><pre>${esc(txt)}</pre>
            <div class="row"><span class="count ${txt.length > bios.limits[k] ? 'over' : ''}">${txt.length}/${bios.limits[k]}</span>
            <button class="btn-sm" data-copy="${k}:${i}">${ICON.copy} Copier</button></div></div>`).join('')}
        </div>`).join('')}</div>
      <div class="bio-grid" style="margin-top:18px">
        <div class="card stack"><h3>Hashtags pour ton compte</h3>
          <div class="tags">${bios.hashtags.map((t) => `<span class="tag large">${esc(t)}</span>`).join('')}</div>
          <div class="row"><button class="btn-sm" id="cpHash">${ICON.copy} Copier les hashtags</button></div></div>
        <div class="card stack"><h3>Mots-clés de la chaîne YouTube</h3>
          <pre class="url-box" style="margin:0;white-space:pre-wrap;font:inherit">${esc(bios.youtube_keywords.join(', '))}</pre>
          <div class="row"><button class="btn-sm" id="cpKw">${ICON.copy} Copier les mots-clés</button></div></div>
        <div class="card stack"><h3>💡 Conseils</h3>${bios.tips.map((t) => `<p class="muted small" style="margin:0">${esc(t)}</p>`).join('')}</div>
      </div>`;
    box.querySelectorAll('[data-copy]').forEach((b) => b.addEventListener('click', () => {
      const [k, i] = b.dataset.copy.split(':');
      copy(bios[k][+i], 'Bio');
    }));
    $('#cpHash').addEventListener('click', () => copy(bios.hashtags.join(' '), 'Hashtags'));
    $('#cpKw').addEventListener('click', () => copy(bios.youtube_keywords.join(', '), 'Mots-clés'));
  }

  function render() {
    const { profile: pr, stats: st } = data;
    const chips = (list) => list.length ? list.map(([n, c]) => `<span class="badge">${esc(n)} · ${c}</span>`).join('') : '<span class="muted small">Pas encore de données</span>';
    const exp = Object.entries(st.exports || {});
    app.innerHTML = `<div class="editor-head"><a class="btn btn-ghost icon-btn" href="#/">${ICON.back}</a><h1 style="margin:0">Bios & hashtags de ton compte</h1></div>
      <div class="bio-grid">
        <div class="card stack">
          <h2>📊 Tes stats ClipForge</h2>
          <div class="row" style="gap:22px">
            <div><div class="stat-num">${st.projects}</div><div class="muted small">clips importés</div></div>
            <div><div class="stat-num">${exp.reduce((a, [, n]) => a + n, 0)}</div><div class="muted small">vidéos exportées</div></div>
          </div>
          <div><div class="muted small" style="margin-bottom:6px">Streamers que tu clippes le plus</div><div class="stat-list">${chips(st.channels)}</div></div>
          <div><div class="muted small" style="margin-bottom:6px">Jeux les plus présents</div><div class="stat-list">${chips(st.games)}</div></div>
          <p class="muted small" style="margin:0">Les bios sont pré-remplies avec ce que tu clippes le plus. Les stats internes de TikTok et Instagram ne sont pas publiques : les propositions suivent leurs règles (limites, nombre de hashtags) et ta niche.</p>
        </div>
        <form class="card stack" id="bioForm">
          <h2>✍️ Ton compte</h2>
          <label class="field">Nom du compte<input type="text" name="account_name" maxlength="40" value="${esc(pr.account_name || '')}" placeholder="Ex : ClipZone"></label>
          <label class="field">Streamers que tu clippes (séparés par des virgules)<input type="text" name="streamers" value="${esc((pr.streamers || []).join(', '))}" placeholder="Ex : shroud, xQc, Tarik"></label>
          <label class="field">Jeux / thèmes<input type="text" name="games" value="${esc((pr.games || []).join(', '))}" placeholder="Ex : Valorant, Just Chatting"></label>
          <div class="row">
            <label class="field grow">Langue des bios<select name="lang"><option value="en" ${pr.lang !== 'fr' ? 'selected' : ''}>Anglais</option><option value="fr" ${pr.lang === 'fr' ? 'selected' : ''}>Français</option></select></label>
            <label class="field grow">Fréquence de post<input type="text" name="frequency" maxlength="30" value="${esc(pr.frequency || '')}" placeholder="daily / chaque jour"></label>
          </div>
          <label class="field">Lien (Discord, linktree… optionnel)<input type="text" name="link" maxlength="100" value="${esc(pr.link || '')}"></label>
          <button class="btn-primary btn-big" type="submit">${ICON.magic} Générer les bios</button>
        </form>
      </div>
      <div id="bioRes" style="margin-top:18px"></div>`;
    $('#bioForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const f = new FormData(e.target);
      try {
        const res = await api('/api/bios', { method: 'POST', json: { profile: Object.fromEntries(f.entries()) } });
        data.profile = res.profile;
        renderBios(res.bios);
        $('#bioRes').scrollIntoView({ behavior: 'smooth', block: 'start' });
      } catch (err) { toast(err.message, 'err'); }
    });
    renderBios(data.bios);
  }

  api('/api/bios').then((d) => { data = d; render(); }).catch((err) => { app.innerHTML = `<div class="card empty">${esc(err.message)}</div>`; });
  return { destroy() { } };
}

// ---------------------------------------------------------------------------
// Réglages
// ---------------------------------------------------------------------------
function SettingsView() {
  const app = $('#app');
  app.innerHTML = '<div class="empty">Chargement…</div>';
  (async () => {
    const s = await api('/api/settings');
    const opt = (list, cur) => list.map(([v, l]) => `<option value="${v}" ${v === cur ? 'selected' : ''}>${l}</option>`).join('');
    app.innerHTML = `<div class="editor-head"><a class="btn btn-ghost icon-btn" href="#/">${ICON.back}</a><h1 style="margin:0">Réglages</h1></div>
      <div class="settings-grid">
        <div class="card stack">
          <h2>Sous-titres (IA)</h2>
          <label class="field">Précision de la reconnaissance vocale<select id="sModel">${opt([['tiny', 'Très rapide (moins précis)'], ['base', 'Rapide'], ['small', 'Équilibré (conseillé)'], ['medium', 'Très précis (lent)'], ['large-v3', 'Maximum (très lent, gros PC)']], s.whisper_model)}</select></label>
          <label class="field">Langue parlée si Twitch ne l'indique pas (fichiers envoyés…)<select id="sLang">${opt(Object.entries(INFO.languages).map(([k, l]) => [k, l]), s.language)}</select></label>
          <label class="switch"><span><b>Sous-titres en anglais par défaut</b><br><span class="muted small">Les clips en français (ou autre) sont traduits en anglais.</span></span><input type="checkbox" id="sEn" ${s.subtitles_english ? 'checked' : ''}><span class="knob"></span></label>
          <label class="field">Langue des descriptions et hashtags<select id="sPub">${opt([['auto', 'Auto (langue du clip)'], ['en', 'Toujours en anglais'], ['fr', 'Toujours en français']], s.publish_lang || 'auto')}</select></label>
          <p class="muted small">Le modèle d'IA est téléchargé une seule fois (75 Mo à 3 Go selon la précision). ${INFO.whisper ? '✅ Module IA installé.' : '⚠️ Module IA non installé.'}</p>
        </div>
        <div class="card stack">
          <h2>Export vidéo</h2>
          <label class="field">Qualité<select id="sQuality">${opt([['rapide', 'Rapide'], ['equilibre', 'Équilibrée (conseillé)'], ['max', 'Maximale (plus lent)']], s.quality)}</select></label>
          <label class="field">Carte graphique<select id="sGpu">${opt([['auto', 'Utiliser si disponible'], ['off', 'Ne pas utiliser']], s.gpu)}</select></label>
          <p class="muted small">${INFO.gpu_encoder ? `Encodeur détecté : ${esc(INFO.gpu_encoder)}` : 'Aucun encodeur carte graphique détecté : le processeur sera utilisé.'}</p>
        </div>
        <div class="card stack">
          <h2>Par défaut pour les nouveaux clips</h2>
          <label class="field">Pseudo affiché (filigrane)<input type="text" id="sWm" value="${esc(s.default_watermark)}" placeholder="twitch.tv/tonpseudo"></label>
          <label class="field">Style des sous-titres<select id="sCap">${opt(Object.entries(INFO.caption_styles).map(([k, v]) => [k, v.label]), s.default_caption_style)}</select></label>
          <label class="field">Style du titre<select id="sTitle">${opt(Object.entries(INFO.title_styles).map(([k, v]) => [k, v.label]), s.default_title_style)}</select></label>
        </div>
        <div class="card stack">
          <h2>Compte Twitch</h2>
          <label class="field">Réutiliser ma connexion Twitch du navigateur<select id="sCookies">${opt([['', 'Non (vidéos publiques seulement)'], ['firefox', 'Firefox (conseillé)'], ['chrome', 'Chrome'], ['edge', 'Edge'], ['brave', 'Brave'], ['opera', 'Opera'], ['safari', 'Safari (Mac)']], s.twitch_cookies || '')}</select></label>
          <p class="muted small">Utile seulement pour les VOD réservées aux abonnés : sois connecté à Twitch dans ce navigateur sur le PC. Rien n'est envoyé ailleurs que vers Twitch.</p>
        </div>
      </div>
      <div class="row" style="margin-top:18px;justify-content:flex-end"><button class="btn-primary btn-big" id="sSave">Enregistrer</button></div>`;
    $('#sSave').addEventListener('click', async () => {
      try {
        SETTINGS = await api('/api/settings', {
          method: 'PUT',
          json: {
            whisper_model: $('#sModel').value, language: $('#sLang').value, quality: $('#sQuality').value, gpu: $('#sGpu').value,
            default_watermark: $('#sWm').value.trim(), default_caption_style: $('#sCap').value, default_title_style: $('#sTitle').value,
            twitch_cookies: $('#sCookies').value,
            subtitles_english: $('#sEn').checked,
            publish_lang: $('#sPub').value,
          },
        });
        toast('Réglages enregistrés ✓', 'ok');
      } catch (err) { toast(err.message, 'err'); }
    });
  })().catch((err) => { app.innerHTML = `<div class="card empty">${esc(err.message)}</div>`; });
  return { destroy() { } };
}

// ---------------------------------------------------------------------------
// Démarrage
// ---------------------------------------------------------------------------
(async function start() {
  try {
    [INFO, SETTINGS] = await Promise.all([api('/api/info'), api('/api/settings')]);
  } catch (err) {
    $('#app').innerHTML = `<div class="card empty"><h2>ClipForge ne répond pas</h2><p>${esc(err.message)}</p><p class="muted">Vérifie que l'appli est bien lancée sur le PC.</p></div>`;
    return;
  }
  if (!INFO.is_local) $('#tabletBtn').classList.add('hidden');
  $('#tabletBtn').addEventListener('click', openTabletModal);
  window.addEventListener('hashchange', route);
  route();
  pollJobs();
  setInterval(pollJobs, 2500);
  if (!INFO.gpu_checked) setTimeout(async () => { try { INFO = { ...INFO, ...(await api('/api/info')) }; } catch { /* ignore */ } }, 15000);
})();
