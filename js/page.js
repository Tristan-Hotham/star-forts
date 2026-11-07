/* The star fort belt: the page's map. Every star fort on The Inked World basemap, with a decade slider.
 * Dr Tristan Hotham, Independent researcher, 2026. MIT licence. */
(function () {
  'use strict';
  const qs = new URLSearchParams(location.search);
  const BASE = window.INKBASE;
  const V = '?v=20261104r7';
  const ENGINE = ['js/curated.js', 'js/ink-palette.js', 'js/ink-icons.js', 'js/ink-houses.js', 'js/ink-map.js', 'js/ink-extras.js'];
  const REGIONS = ['Italy and Malta', 'Iberia', 'France', 'Low Countries', 'German lands and Central Europe', 'Scandinavia and the Baltic', 'British Isles',
    'Eastern Europe, Balkans and Turkey', 'Africa', 'Americas', 'Asia and Oceania'];
  const SRC = { p: 'English Wikipedia (dated by hand)', i: 'Wikidata (inception)', s: 'Wikidata (start or opening)', m: 'OpenStreetMap (start_date)' };
  const KIND = { o: 'Outline traced in OpenStreetMap', c: 'Catalogued in Wikidata, no traced outline', h: 'Added from English Wikipedia, no traced outline',
    b: 'Bavarian monument list: earthwork "Schanze" of uncertain form and age', l: 'Shape look-alike: the outline passes the star test but is probably a towered wall of another tradition' };
  const PRESETS = [['World', [[-150, -45], [160, 65]]], ['Europe', [[-12, 35], [32, 61]]], ['Low Countries', [[2.2, 50.4], [7.4, 53.6]]],
    ['Caribbean', [[-90, 9], [-59, 27]]], ['Indian Ocean', [[30, -28], [125, 26]]], ['Japan', [[128, 30], [146, 45]]]];
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const norm = s => String(s).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

  // dark mode for the page around the map (the map itself stays parchment)
  const th = document.getElementById('theme');
  th.addEventListener('click', () => {
    const r = document.documentElement, dark = r.dataset.theme ? r.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    r.dataset.theme = dark ? 'light' : 'dark';
  });
  // the title folds away on phones and after the first touch of the map
  const ct = document.getElementById('cartouche');
  const fold = f => ct.classList.toggle('folded', f);
  if (matchMedia('(max-width:600px)').matches) fold(true);
  document.getElementById('ctToggle').addEventListener('click', () => fold(!ct.classList.contains('folded')));
  document.getElementById('ctFold').addEventListener('click', () => fold(true));

  function loadScripts(list) {
    return list.reduce((p, src) => p.then(() => new Promise((res, rej) => {
      const el = document.createElement('script'); el.src = BASE + src + V; el.onload = res; el.onerror = () => rej(new Error('script ' + src)); document.head.appendChild(el);
    })), Promise.resolve());
  }

  // ---------------- pen-drawn star symbols: The Inked World's star fort, inked again in black, vermilion and faded sepia
  const ICONS = {};
  function makeIcons() {
    const k = (window.InkPalette && InkPalette.SCALE) || 3;
    let base = window.InkIcons ? InkIcons.draw('h-starfort') : null;
    if (!base) { base = document.createElement('canvas'); base.width = base.height = 60 * k / 2; }
    const tint = (col, alpha, scale) => {
      const c = document.createElement('canvas'); const s = scale || 1;
      c.width = Math.round(base.width * s); c.height = Math.round(base.height * s);
      const x = c.getContext('2d'); x.globalAlpha = alpha; x.drawImage(base, 0, 0, c.width, c.height);
      if (col) { x.globalAlpha = 1; x.globalCompositeOperation = 'source-atop'; x.fillStyle = col; x.fillRect(0, 0, c.width, c.height); }
      return c;
    };
    ICONS['sf-old'] = base;
    ICONS['sf-new'] = tint('rgba(163,38,27,0.62)', 1);
    ICONS['sf-und'] = tint('rgba(176,150,112,0.7)', 0.6, 0.78);
    ICONS['sf-oth'] = tint('rgba(120,120,120,0.55)', 0.55, 0.7);
    return k;
  }
  function addIcons(map, k) {
    for (const [id, c] of Object.entries(ICONS)) {
      if (map.hasImage(id)) continue;
      map.addImage(id, c.getContext('2d').getImageData(0, 0, c.width, c.height), { pixelRatio: k });
    }
    document.querySelectorAll('canvas[data-icon]').forEach(cv => {
      const src = ICONS[cv.dataset.icon]; if (!src) return;
      cv.width = src.width; cv.height = src.height; cv.getContext('2d').drawImage(src, 0, 0);
    });
    const kr = document.getElementById('keyrow');
    if (kr && !kr.childNodes.length) {
      for (const [id, lab] of [['sf-new', 'Built in the 30 years before the slider date'], ['sf-old', 'Built earlier'], ['sf-und', 'No date'], ['sf-oth', 'Uncertain (off by default)']]) {
        const sp = document.createElement('span'); const cv = document.createElement('canvas'); const src = ICONS[id];
        cv.width = src.width; cv.height = src.height; cv.getContext('2d').drawImage(src, 0, 0); sp.appendChild(cv); sp.append(lab); kr.appendChild(sp);
      }
    }
  }

  // ---------------- state
  const S = { year: 3000, und: true, dated: true, undLayer: true, outline: true, names: true, bav: false, look: false };
  let DATA = null, BYID = new Map();
  const iz = (...a) => { const e = ['interpolate', ['linear'], ['zoom']]; for (let i = 0; i < a.length; i += 2) e.push(a[i], a[i + 1]); return e; };

  function filters() {
    const main = ['in', ['get', 'k'], ['literal', ['o', 'c', 'h']]];
    const dated = ['all', main, ['has', 'y'], ['<=', ['get', 'y'], S.year]];
    return {
      newer: ['all', dated, ['>', ['get', 'y'], S.year - 30]],
      older: ['all', dated, ['<=', ['get', 'y'], S.year - 30]],
      und: ['all', main, ['!', ['has', 'y']]],
      oth: ['any', ['all', ['==', ['get', 'k'], 'b'], ['literal', S.bav]], ['all', ['==', ['get', 'k'], 'l'], ['literal', S.look]]],
      outline: ['any', ['all', ['has', 'y'], ['<=', ['get', 'y'], S.year], ['literal', S.dated]], ['all', ['!', ['has', 'y']], ['literal', S.und && S.undLayer]]],
    };
  }
  function vis(map, id, on) { if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', on ? 'visible' : 'none'); }
  function apply(map) {
    const F = filters();
    map.setFilter('sf-und', F.und); map.setFilter('sf-old', F.older); map.setFilter('sf-new', F.newer); map.setFilter('sf-oth', F.oth);
    // the smoothed outline only where a fort has no mapped walls of its own (or while far out); the real walls and moats closer in
    for (const id of ['sfo-moat', 'sfo-rampart']) map.setFilter(id, ['all', ['==', ['get', 'k'], 'm'], ['!', ['has', 'd']], F.outline]);
    map.setFilter('sfo-line', ['all', ['==', ['get', 'k'], 'm'], F.outline]);
    const DK = (t, look) => ['all', ['==', ['get', 'k'], t], look ? ['all', ['==', ['get', 'kk'], 'l'], ['literal', S.look]] : ['all', ['==', ['get', 'kk'], 'm'], F.outline]];
    map.setFilter('sfd-moat', ['any', DK('m'), DK('m', 1)]); map.setFilter('sfd-edge', ['any', DK('e'), DK('e', 1)]);
    map.setFilter('sfd-rampart', DK('w')); map.setFilter('sfd-wall', ['any', DK('w'), DK('w', 1)]);
    map.setFilter('sfo-other', ['all', ['!=', ['get', 'k'], 'm'], ['any', ['all', ['==', ['get', 'k'], 'l'], ['literal', S.look]]]]);
    vis(map, 'sf-und', S.und && S.undLayer); vis(map, 'sf-old', S.dated); vis(map, 'sf-new', S.dated); vis(map, 'sf-oth', S.bav || S.look);
    for (const id of ['sfo-moat', 'sfo-rampart', 'sfo-line', 'sfo-other', 'sfd-moat', 'sfd-edge', 'sfd-rampart', 'sfd-wall']) vis(map, id, S.outline);
    vis(map, 'sf-names', S.names);
    const lab = document.getElementById('yrLab'); lab.textContent = S.year >= 1910 ? 'Today' : S.year;
    if (DATA) {
      let n = 0, nn = 0;
      for (const f of DATA.features) { const p = f.properties; if ('och'.includes(p.k) && p.y && p.y <= S.year) { n++; if (p.y > S.year - 30) nn++; } }
      document.getElementById('cnt').textContent = S.year >= 1910 ? `${n.toLocaleString('en-GB')} dated forts, ${DATA.nUnd.toLocaleString('en-GB')} undated` : `${n.toLocaleString('en-GB')} dated forts by ${S.year}, ${nn} in the last 30 years`;
    }
  }

  function addLayers(map) {
    // the engine's own star forts give way to this study's
    for (const id of ['fort-moat', 'fort-moat-edge', 'fort-rampart', 'fort-line', 'fort-icons']) if (map.getLayer(id)) map.removeLayer(id);
    map.addSource('sf', { type: 'geojson', data: DATA, attribution: 'Star forts: <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> (ODbL), <a href="https://www.wikidata.org/" target="_blank">Wikidata</a> (CC0), English Wikipedia' });
    map.addSource('sfo', { type: 'geojson', data: { type: 'FeatureCollection', features: [] }, tolerance: 0.15 });
    const INK = map.INK || { ink: '#2B2119', red: '#A3261B', blue: '#3D6E9E' };
    const HALO = 'rgba(246,238,216,0.92)';
    // the real outlines, close in: moat outside, hachured rampart inside, an ink line along the trace
    map.addLayer({ id: 'sfo-moat', type: 'line', source: 'sfo', minzoom: 10.5, layout: { 'line-join': 'miter', 'line-miter-limit': 4 },
      paint: { 'line-color': '#9DBBD6', 'line-width': iz(10.5, 2, 14, 12, 17, 44), 'line-offset': iz(10.5, -1, 14, -6, 17, -22), 'line-opacity': iz(10.5, 0, 11.2, 0.85) } });
    map.addLayer({ id: 'sfo-rampart', type: 'line', source: 'sfo', minzoom: 11.5, layout: { 'line-join': 'miter', 'line-miter-limit': 4 },
      paint: { 'line-pattern': 'rampart', 'line-width': iz(11.5, 3, 14, 7, 17, 18), 'line-offset': iz(11.5, 1.5, 14, 3.5, 17, 9), 'line-opacity': iz(11.5, 0, 12, 1) } });
    map.addLayer({ id: 'sfo-line', type: 'line', source: 'sfo', minzoom: 10.5, layout: { 'line-join': 'miter', 'line-miter-limit': 4 },
      paint: { 'line-color': ['case', ['>', ['coalesce', ['get', 'y'], 0], S.year - 30], INK.red, INK.ink], 'line-width': iz(10.5, 1, 15, 2.2, 17, 3),
        'line-opacity': iz(10.5, 0, 11.2, 1, 11.8, 1, 12.4, ['case', ['has', 'd'], 0, 1]) } });
    // the real walls, ramparts and moats as mapped in OpenStreetMap (data/forts_detail.geojson), from zoom 11.3
    map.addSource('sfd', { type: 'geojson', data: { type: 'FeatureCollection', features: [] }, tolerance: 0.05, buffer: 64 });
    map.addLayer({ id: 'sfd-moat', type: 'fill', source: 'sfd', minzoom: 11.3, paint: { 'fill-color': '#9DBBD6', 'fill-outline-color': INK.blue, 'fill-opacity': iz(11.3, 0, 12, 0.9) } });
    map.addLayer({ id: 'sfd-edge', type: 'line', source: 'sfd', minzoom: 11.3, paint: { 'line-color': INK.blue, 'line-width': iz(12, 0.8, 16, 1.4), 'line-opacity': iz(11.3, 0, 12, 0.9) } });
    map.addLayer({ id: 'sfd-rampart', type: 'line', source: 'sfd', minzoom: 12.4, layout: { 'line-join': 'miter', 'line-miter-limit': 4 },
      paint: { 'line-pattern': 'rampart', 'line-width': iz(12.4, 3, 14, 6, 17, 14), 'line-opacity': iz(12.4, 0, 13, 0.9) } });
    map.addLayer({ id: 'sfd-wall', type: 'line', source: 'sfd', minzoom: 11.3, layout: { 'line-join': 'miter', 'line-miter-limit': 4, 'line-cap': 'round' },
      paint: { 'line-color': ['case', ['>', ['coalesce', ['get', 'y'], 0], S.year - 30], INK.red, INK.ink], 'line-width': iz(11.3, 1, 14, 1.8, 17, 3), 'line-opacity': iz(11.3, 0, 12, 1) } });
    map.addLayer({ id: 'sfo-other', type: 'line', source: 'sfo', minzoom: 10.5, paint: { 'line-color': '#8A8A80', 'line-width': 1.4, 'line-dasharray': [2, 2] } });
    const size = big => iz(1, big ? 0.32 : 0.26, 4, big ? 0.48 : 0.4, 8, big ? 0.85 : 0.7, 11, 1.0);
    const sym = (id, icon, filter, big, op) => map.addLayer({ id, type: 'symbol', source: 'sf', filter, maxzoom: 12.2,
      layout: { 'icon-image': icon, 'icon-size': size(big), 'icon-allow-overlap': true, 'icon-ignore-placement': true, 'symbol-sort-key': ['coalesce', ['get', 'y'], 3000] },
      paint: { 'icon-opacity': ['interpolate', ['linear'], ['zoom'], 10.8, op || 1, 12.0, 0] } });
    const F = filters();
    sym('sf-oth', 'sf-oth', F.oth, false, 0.8);
    sym('sf-und', 'sf-und', F.und, false, 0.9);
    sym('sf-old', 'sf-old', F.older, true);
    sym('sf-new', 'sf-new', F.newer, true);
    map.addLayer({ id: 'sf-names', type: 'symbol', source: 'sf', minzoom: 5.5, filter: ['all', ['in', ['get', 'k'], ['literal', ['o', 'c', 'h']]], ['!', ['has', 'u']]],
      layout: { 'text-field': ['get', 'n'], 'text-font': ['Ink Italic'], 'text-size': iz(5.5, 11, 12, 14), 'text-variable-anchor': ['top', 'bottom', 'right', 'left'],
        'text-radial-offset': 1.1, 'text-optional': true, 'symbol-sort-key': ['-', 0, ['coalesce', ['get', 'a'], 0]], 'text-max-width': 9 },
      paint: { 'text-color': ['case', ['all', ['has', 'y'], ['>', ['get', 'y'], S.year - 30], ['<=', ['get', 'y'], S.year]], INK.red, INK.ink], 'text-halo-color': HALO, 'text-halo-width': 1.4 } });
    // the outlines (about 0.9 MB) come in when the map first gets close
    let got = false;
    const lazy = () => { if (got || map.getZoom() < 8.5) return; got = true;
      Promise.all([fetch('data/forts_outlines.geojson').then(r => r.json()), fetch('data/forts_detail.geojson').then(r => r.json())]).then(([j, d]) => {
        const walled = new Set();
        for (const f of d.features) { const p = BYID.get(f.properties.id); f.properties.kk = p && p.k === 'l' ? 'l' : 'm'; if (p && p.y) f.properties.y = p.y; if (f.properties.k === 'w') walled.add(f.properties.id); }
        for (const f of j.features) { const p = BYID.get(f.properties.id); f.properties.k = p && p.k === 'l' ? 'l' : 'm'; if (p && p.y) f.properties.y = p.y; if (walled.has(f.properties.id)) f.properties.d = 1; }
        map.getSource('sfo').setData(j); map.getSource('sfd').setData(d); apply(map);
      }).catch(e => console.warn('outlines', e)); };
    map.on('zoomend', lazy); lazy();
  }
  function recolour(map) {
    const INK = map.INK || { ink: '#2B2119', red: '#A3261B' };
    map.setPaintProperty('sfd-wall', 'line-color', ['case', ['all', ['>', ['coalesce', ['get', 'y'], 0], S.year - 30], ['<=', ['coalesce', ['get', 'y'], 0], S.year]], INK.red, INK.ink]);
    map.setPaintProperty('sfo-line', 'line-color', ['case', ['all', ['>', ['coalesce', ['get', 'y'], 0], S.year - 30], ['<=', ['coalesce', ['get', 'y'], 0], S.year]], INK.red, INK.ink]);
    map.setPaintProperty('sf-names', 'text-color', ['case', ['all', ['has', 'y'], ['>', ['get', 'y'], S.year - 30], ['<=', ['get', 'y'], S.year]], INK.red, INK.ink]);
  }

  // ---------------- popups
  function popupHTML(p) {
    const rows = [];
    rows.push(['Country', esc(p.c || '')]);
    if (p.r >= 0) rows.push(['Region', esc(REGIONS[p.r])]);
    if (p.y) rows.push(['Begun', `<b>${p.y}</b>`], ['Date from', esc(SRC[p.s] || '')]);
    else rows.push(['Begun', p.md ? `no date for the bastions (the site goes back to ${esc(p.md)})` : 'no date in the data']);
    if (p.b) rows.push(['Built by', esc(p.b)]);
    if (p.a) rows.push(['Area', `${Number(p.a).toFixed(1)} ha inside the outline`], ['Points', `${p.p} salient corners (bastions)`]);
    if (p.v) rows.push(['Today', 'largely demolished']);
    let h = `<b class="t">${esc(p.n)}</b><table>${rows.map(r => `<tr><td>${r[0]}</td><td>${r[1]}</td></tr>`).join('')}</table>`;
    if (p.t) h += `<div>${esc(p.t)}.</div>`;
    h += `<p class="nt">${esc(KIND[p.k] || '')}${p.u ? '. Unnamed in the sources: named after the nearest town' : ''}.</p>`;
    const L = [];
    if (p.w) L.push(`<a href="https://en.wikipedia.org/wiki/${p.w}" target="_blank" rel="noopener">Wikipedia</a>`);
    if (p.q) L.push(`<a href="https://www.wikidata.org/wiki/${esc(p.q)}" target="_blank" rel="noopener">Wikidata ${esc(p.q)}</a>`);
    if (p.o) for (const o of String(p.o).split(';').slice(0, 1)) L.push(`<a href="https://www.openstreetmap.org/${o[0] === 'w' ? 'way' : 'relation'}/${o.slice(1)}" target="_blank" rel="noopener">OpenStreetMap</a>`);
    const photoQ = p.u ? '' : p.n;
    if (photoQ) L.push(`<a href="https://commons.wikimedia.org/w/index.php?title=Special:MediaSearch&type=image&search=${encodeURIComponent(photoQ)}" target="_blank" rel="noopener">Photos</a>`);
    return h + (L.length ? `<div class="lk">${L.join('')}</div>` : '');
  }
  function setupPopups(map) {
    const LAY = ['sf-new', 'sf-old', 'sf-und', 'sf-oth', 'sf-names', 'sfo-line', 'sfo-other', 'sfd-wall', 'sfd-moat'];
    let pop = null;
    map.on('click', e => {
      const pad = 8, bb = [[e.point.x - pad, e.point.y - pad], [e.point.x + pad, e.point.y + pad]];
      const fs = map.queryRenderedFeatures(bb, { layers: LAY.filter(id => map.getLayer(id) && map.getLayoutProperty(id, 'visibility') !== 'none') });
      if (!fs.length) return;
      const p = BYID.get(fs[0].properties.id); if (!p) return;
      if (pop) pop.remove();
      const f = DATA.features.find(x => x.properties.id === p.id);
      pop = new maplibregl.Popup({ maxWidth: small ? '270px' : '320px', offset: 10 }).setLngLat(fs[0].geometry.type === 'Point' ? fs[0].geometry.coordinates : f.geometry.coordinates).setHTML(popupHTML(p)).addTo(map);
    });
    for (const id of LAY) { map.on('mouseenter', id, () => map.getCanvas().style.cursor = 'pointer'); map.on('mouseleave', id, () => map.getCanvas().style.cursor = ''); }
  }

  // ---------------- search: named forts and countries
  function setupSearch(map) {
    const q = document.getElementById('q'), sug = document.getElementById('sug');
    let G = null, items = [], sel = -1;
    const load = () => G || (G = fetch('data/search.json').then(r => r.json()).then(a => {
      const out = a.map(r => ({ n: r[0], k: norm(r[0]), lon: r[1], lat: r[2], id: r[3], ctx: r[4], z: 13.2 }));
      const cs = new Map();
      for (const f of DATA.features) { const p = f.properties; if (!p.c || !'och'.includes(p.k)) continue; const c = cs.get(p.c) || { n: p.c, k: norm(p.c), xs: [], ys: [], ctx: 'country', z: 5 }; c.xs.push(f.geometry.coordinates[0]); c.ys.push(f.geometry.coordinates[1]); cs.set(p.c, c); }
      for (const c of cs.values()) { c.bb = [[Math.min(...c.xs), Math.min(...c.ys)], [Math.max(...c.xs), Math.max(...c.ys)]]; out.push(c); }
      return out;
    }));
    q.addEventListener('focus', load);
    async function run() {
      const t = norm(q.value.trim());
      if (t.length < 2) { sug.style.display = 'none'; return; }
      const g = await load(); const sc = [];
      for (const r of g) { const i = r.k.indexOf(t); if (i < 0) continue; sc.push([(i === 0 ? 0 : 10) + (r.ctx === 'country' ? -2 : 0) + r.k.length / 40, r]); }
      sc.sort((a, b) => a[0] - b[0]); items = sc.slice(0, 9).map(s => s[1]); sel = -1;
      sug.innerHTML = items.length ? items.map((r, i) => `<li role="option" data-i="${i}">${esc(r.n)} <span>${esc(r.ctx)}</span></li>`).join('') : '<li>No match</li>';
      sug.style.display = 'block';
    }
    function go(r) {
      if (!r) return; sug.style.display = 'none'; q.value = r.n; q.blur();
      if (r.bb) { map.fitBounds(r.bb, { padding: 60, maxZoom: 8, duration: 2200 }); return; }
      map.flyTo({ center: [r.lon, r.lat], zoom: r.z, duration: 2600, essential: true });
      map.once('moveend', () => { const p = BYID.get(r.id); if (p) new maplibregl.Popup({ maxWidth: '320px', offset: 10 }).setLngLat([r.lon, r.lat]).setHTML(popupHTML(p)).addTo(map); });
    }
    q.addEventListener('input', run);
    q.addEventListener('keydown', e => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); sel = Math.max(0, Math.min(items.length - 1, sel + (e.key === 'ArrowDown' ? 1 : -1))); [...sug.children].forEach((li, i) => li.setAttribute('aria-selected', i === sel)); }
      else if (e.key === 'Enter') { e.preventDefault(); go(items[sel < 0 ? 0 : sel]); }
      else if (e.key === 'Escape') sug.style.display = 'none';
    });
    sug.addEventListener('click', e => { const li = e.target.closest('li[data-i]'); if (li) go(items[+li.dataset.i]); });
    document.addEventListener('click', e => { if (!e.target.closest('.srch')) sug.style.display = 'none'; });
  }

  // ---------------- layers panel
  function setupLayers(map) {
    const lp = document.getElementById('lp'), btn = document.getElementById('lyrBtn');
    btn.addEventListener('click', e => { e.stopPropagation(); const o = lp.classList.toggle('open'); btn.setAttribute('aria-expanded', o); });
    document.addEventListener('click', e => { if (!lp.contains(e.target) && e.target !== btn) { lp.classList.remove('open'); btn.setAttribute('aria-expanded', false); } });
    const bind = (id, key) => { const el = document.getElementById(id); el.checked = S[key]; el.addEventListener('change', () => { S[key] = el.checked; apply(map); }); };
    bind('lyDated', 'dated'); bind('lyUndated', 'undLayer'); bind('lyOutline', 'outline'); bind('lyNames', 'names'); bind('lyBav', 'bav'); bind('lyLook', 'look');
    const boxes = [...lp.querySelectorAll('input[data-g]')], modern = document.getElementById('modern'), wb = document.getElementById('winterBox');
    const NAME_LAYERS = map.getStyle().layers.filter(l => l.type === 'symbol' && l.metadata && ['names', 'rivers'].includes(l.metadata.group)).map(l => l.id);
    const saved = {}; NAME_LAYERS.forEach(id => saved[id] = { c: map.getPaintProperty(id, 'text-color'), h: map.getPaintProperty(id, 'text-halo-color') });
    function base() {
      const m = modern.checked;
      boxes.forEach(b => { const g = b.dataset.g; const inkOnly = ['mountains', 'forests', 'biomes', 'sea', 'tint'].includes(g); InkMap.setGroup(map, g, b.checked && !(m && inkOnly)); });
      InkMap.setGroup(map, 'paper', !m); InkMap.setGroup(map, 'modern', m); InkMap.setGroup(map, 'coast', !m);
      if (m) InkMap.setGroup(map, 'roads', false);
      NAME_LAYERS.forEach(id => { map.setPaintProperty(id, 'text-color', m ? '#333333' : saved[id].c); map.setPaintProperty(id, 'text-halo-color', m ? 'rgba(255,255,255,0.9)' : saved[id].h); });
    }
    boxes.forEach(b => b.addEventListener('change', base)); modern.addEventListener('change', base);
    wb.checked = false;
    wb.addEventListener('change', () => {   // the winter look, without changing The Inked World's own remembered choice
      let keep = null; try { keep = localStorage.getItem('ink-winter'); } catch (e) {}
      InkMap.setWinter(map, wb.checked && !modern.checked);
      try { if (keep === null) localStorage.removeItem('ink-winter'); else localStorage.setItem('ink-winter', keep); } catch (e) {}
    });
    const rose = document.getElementById('rose'), cb = document.getElementById('compassBox');
    cb.addEventListener('change', () => { rose.style.display = cb.checked ? '' : 'none'; });
    base();
  }

  // ---------------- the timeline
  function setupTimeline(map) {
    const r = document.getElementById('yr'), pb = document.getElementById('play'), ub = document.getElementById('undBox');
    let timer = null;
    const set = y => { y = +y; r.value = Math.min(y, 1910); S.year = y >= 1910 ? 3000 : y; apply(map); recolour(map); };
    r.addEventListener('input', () => set(r.value));
    ub.addEventListener('change', () => { S.und = ub.checked; apply(map); });
    const stop = () => { clearInterval(timer); timer = null; pb.textContent = '▶'; pb.setAttribute('aria-label', 'Play the spread through the decades'); };
    pb.addEventListener('click', () => {
      if (timer) { stop(); return; }
      if (S.year >= 1910) { set(1480); }
      if (ub.checked) { ub.checked = false; S.und = false; }
      pb.textContent = '❚❚'; pb.setAttribute('aria-label', 'Pause');
      timer = setInterval(() => { if (S.year >= 1910) { stop(); ub.checked = true; S.und = true; apply(map); return; } set(S.year + 10); }, 700);
    });
  }

  // ---------------- start
  const opts = { base: BASE, winter: false };
  if (qs.get('tj')) opts.tilejson = qs.get('tj');
  if (qs.get('dem')) opts.dem = qs.get('dem');
  if (qs.get('demmax')) opts.demMax = +qs.get('demmax');
  const start = qs.get('at') ? qs.get('at').split(',').map(Number) : null;
  const small = matchMedia('(max-width:600px)').matches;
  opts.mapOptions = start ? { center: [start[1], start[0]], zoom: start[2] } : { bounds: small ? [[-20, 20], [40, 62]] : PRESETS[0][1], fitBoundsOptions: { padding: 10 } };
  const dataP = fetch('data/forts_points.geojson').then(r => r.json()).then(j => {
    DATA = j; DATA.nUnd = 0;
    for (const f of j.features) { BYID.set(f.properties.id, f.properties); if ('och'.includes(f.properties.k) && !f.properties.y) DATA.nUnd++; }
    return j;
  });
  Promise.all([loadScripts(ENGINE), dataP]).then(() => InkMap.create('map', opts)).then(map => {
    map.__inkWinter = false;
    window.__map = map;
    document.getElementById('nojs').remove();
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right');
    // the attribution starts folded (the (i) button opens it), so it never sits under the timeline
    const foldAt = () => { const at = document.querySelector('.maplibregl-ctrl-attrib.maplibregl-compact'); if (at) { at.classList.remove('maplibregl-compact-show'); at.removeAttribute('open'); } };
    map.once('idle', foldAt); map.on('resize', () => setTimeout(foldAt, 50)); foldAt(); setTimeout(foldAt, 1500);
    if (window.InkExtras) { try { InkExtras.scaleBar(map, document.getElementById('scalebar')); document.getElementById('rose').innerHTML = InkExtras.compassSVG(54); } catch (e) { console.warn(e); } }
    const k = makeIcons(); addIcons(map, k);
    map.on('styleimagemissing', e => { if (ICONS[e.id]) addIcons(map, k); });
    addLayers(map); apply(map);
    setupLayers(map); setupSearch(map); setupPopups(map); setupTimeline(map);
    const pre = document.getElementById('presets');
    PRESETS.forEach(([n, b]) => { const btn = document.createElement('button'); btn.className = 'chip'; btn.textContent = n;
      btn.addEventListener('click', () => map.fitBounds(b, { padding: 20, duration: 2200, essential: true })); pre.appendChild(btn); });
    const mapEl = document.getElementById('map');
    const first = e => { if (e.target.closest && e.target.closest('.cartouche,.ov,.lp,.tl,.mfs-btn,.maplibregl-ctrl')) return; fold(true); };
    mapEl.addEventListener('pointerdown', first, { capture: true, passive: true, once: true });
  }).catch(e => { console.error(e); const n = document.getElementById('nojs'); if (n) n.textContent = 'The map could not load: ' + e.message; });
})();
