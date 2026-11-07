// QA: renders the page against local test tiles (OpenFreeMap and Terrarium tiles saved for The Inked World) and records
// console errors, screenshots and a few interactions. Usage: node code/qa.js  (needs a file server at http://localhost:8765/
// serving the file system root, playwright, and maplibre-gl 4.7.1 in MAPLIBRE_DIST)
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const ML = process.env.MAPLIBRE_DIST || '/tmp/ml/node_modules/maplibre-gl/dist';
const ROOT = path.join(__dirname, '..');
const BASE = 'http://localhost:8765' + ROOT + '/index.html';
const TJ = process.env.TJ || 'http://localhost:8765/tmp/claude-0/-home-claude/9791f396-0812-550b-8fd1-2ad33918f115/scratchpad/tj_local.json';
const DEM = 'http://localhost:8765/home/claude/newdata/raw9/terrarium/{z}/{x}/{y}.png';
const ONLY = process.env.ONLY ? process.env.ONLY.split(',') : null;
const shots0 = [
  { out: 'desk_world', w: 1280, h: 860 },
  { out: 'desk_europe', w: 1280, h: 860, at: '50.5,7,4.6' },
  { out: 'desk_1600', w: 1280, h: 860, at: '45,0,3.2', year: 1600 },
  { out: 'desk_palmanova', w: 1280, h: 860, at: '45.9055,13.3097,14.2', click: true },
  { out: 'desk_naarden', w: 1280, h: 860, at: '52.2955,5.1625,13.6' },
  { out: 'phone_world', w: 390, h: 844, dpr: 2 },
  { out: 'phone_popup', w: 390, h: 844, dpr: 2, at: '53.0067,7.1917,14.5', click: true },
  { out: 'page_full', w: 1280, h: 860, full: true },
  { out: 'phone_full', w: 390, h: 844, full: true },
];
const shots = ONLY ? shots0.filter(s => ONLY.includes(s.out)) : shots0;
(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const errors = [], info = {};
  fs.mkdirSync(path.join(ROOT, 'qa'), { recursive: true });
  for (const s of shots) {
    const ctx = await browser.newContext({ viewport: { width: s.w, height: s.h }, deviceScaleFactor: s.dpr || 1 });
    const page = await ctx.newPage();
    await page.route(/cdn\.jsdelivr\.net\/npm\/maplibre-gl@4\.7\.1\/dist\/(.*)/, (route, req) => {
      const f = path.join(ML, req.url().split('/dist/')[1]);
      route.fulfill({ body: fs.readFileSync(f), contentType: f.endsWith('.css') ? 'text/css' : 'application/javascript' });
    });
    await page.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
    page.on('console', m => { if (m.type() === 'error') errors.push(`[${s.out}] ${m.text().slice(0, 200)} ${(m.location() || {}).url || ''}`); });
    page.on('pageerror', e => errors.push(`[${s.out}] pageerror: ${e.message}`));
    const q = new URLSearchParams({ tj: TJ, dem: DEM, demmax: '12' }); if (s.at) q.set('at', s.at);
    await page.goto(`${BASE}?${q}`, { waitUntil: 'load' });
    await page.waitForFunction(() => window.__map, null, { timeout: 90000 });
    const idle = () => page.evaluate(() => new Promise(res => { const m = window.__map; m.once('idle', () => setTimeout(res, 800)); m.triggerRepaint(); setTimeout(res, 40000); }));
    await idle();
    if (s.year) { await page.evaluate(y => { const r = document.getElementById('yr'); r.value = y; r.dispatchEvent(new Event('input')); }, s.year); await idle(); }
    if (s.click) {
      const pt = await page.evaluate(() => { const m = window.__map; const fs = m.queryRenderedFeatures({ layers: ['sfo-line', 'sf-old', 'sf-new', 'sf-und'].filter(l => m.getLayer(l)) }); if (!fs.length) return null;
        const g = fs[0].geometry; let c = g.coordinates; while (Array.isArray(c[0])) c = c[0]; const q = m.project(c), r = m.getContainer().getBoundingClientRect(); return { x: q.x + r.left, y: q.y + r.top }; });
      if (pt) { await page.mouse.click(pt.x, pt.y + (s.w < 500 ? 0 : 0)); await page.waitForTimeout(800); }
      info[s.out + '_popup'] = await page.evaluate(() => { const p = document.querySelector('.maplibregl-popup-content'); return p ? p.innerText : null; });
    }
    info[s.out] = await page.evaluate(() => ({ cnt: document.getElementById('cnt').textContent, zoom: window.__map.getZoom().toFixed(2), scrollW: document.documentElement.scrollWidth,
      fsBtn: !!document.querySelector('.mfs-btn'), rendered: window.__map.queryRenderedFeatures({ layers: ['sf-old', 'sf-new', 'sf-und'] }).length }));
    await page.screenshot({ path: path.join(ROOT, 'qa', s.out + '.png'), fullPage: !!s.full, timeout: 120000 });
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(path.join(ROOT, 'qa', 'qa.json'), JSON.stringify({ errors, info }, null, 1));
  console.log(JSON.stringify({ errors, info }, null, 1));
})();
