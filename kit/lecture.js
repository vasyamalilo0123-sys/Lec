#!/usr/bin/env node
/* Рушій відеолекцій. Специфікація: kit/ENGINE.md.
   node kit/lecture.js <тека лекції> plan | tts | qa [сцена] | render [сцена] | still <сцена> <час> | status | motion
   Параметри: --jobs N, --force, --no-audio */
const path = require('path'), fs = require('fs'), crypto = require('crypto'), { execFileSync, spawn } = require('child_process');
const KIT = __dirname, FPS = 25;
let tts = null; try { tts = require('./tts.js'); } catch (e) { tts = null; }

/* ---------- аргументи ---------- */
const flags = { jobs: 3, force: false, noAudio: false }, pos = [], argv = process.argv.slice(2);
for (let i = 0; i < argv.length; i++) { const a = argv[i]; if (a === '--jobs') flags.jobs = Math.max(1, +argv[++i] || 3); else if (a === '--force') flags.force = true; else if (a === '--no-audio') flags.noAudio = true; else pos.push(a); }
const [dirArg, action, ...rest] = pos;
if (!dirArg || !action) { console.log('Використання: node kit/lecture.js <тека лекції> plan|tts|qa [сцена]|render [сцена]|still <сцена> <час>|status|motion [--jobs N] [--force] [--no-audio]'); process.exit(2); }
const dir = path.resolve(dirArg), OUT = path.join(dir, 'out');
const die = (m, code = 1) => { console.error(m); process.exit(code); };

/* ---------- типові параметри вигляду (сцена може перевизначити полями leader / grey / motion) ---------- */
const DEF = { leader: { type: 'elbow', width: 1.3, color: '#efe9df', marker: 'ring', gap: 14, elbow: 36 }, grey: { brightness: 0.42 }, motion: { text: 'wipe' } };
const readJson = f => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch (e) { die(`Не вдалося прочитати ${path.relative(process.cwd(), f)}: ${e.message}`); } };
const sha = s => crypto.createHash('sha1').update(s).digest('hex');
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const noAcc = x => String(x).replace(/\u0301/g, ''), MARK = /\[\[(\w+)\]\]/g, strip = s => s.replace(MARK, '');
const readIf = f => fs.existsSync(f) ? fs.readFileSync(f, 'utf8') : '';
const hasId = (svg, id) => new RegExp(`\\bid\\s*=\\s*["']${id.replace(/[^\w-]/g, '')}["']`).test(svg);

/* ---------- тривалість і позначки репліки ---------- */
function measure(voice, sceneId, n) {
  if (tts && tts.measure) { try { const m = tts.measure(dir, voice, sceneId, { id: n.id, text: n.text, spoken: n.spoken }); if (m && m.duration > 0) return m; } catch (e) { /* запасна оцінка */ } }
  const plain = strip(n.spoken), acc = k => (plain.slice(0, k).match(/\u0301/g) || []).length, len = plain.length - acc(plain.length), duration = Math.max(1.2, len / (voice.rate || 14.5)), markers = {};
  let removed = 0; for (const m of n.spoken.matchAll(MARK)) { const pos = m.index - removed; markers[m[1]] = +((pos - acc(pos)) / Math.max(1, len) * duration).toFixed(3); removed += m[0].length; }
  return { duration: +duration.toFixed(3), markers, estimated: true };
}

/* ---------- читання лекції, перевірка формату, розрахунок часу ---------- */
function load() {
  const errors = [], warns = [], lj = readJson(path.join(dir, 'lecture.json')), voice = lj.voice || { provider: 'estimate', rate: 14.5 };
  const srcById = {}; for (const s of lj.sources || []) { if (srcById[s.id]) errors.push(`lecture.json: повторний id джерела «${s.id}»`); srcById[s.id] = s; }
  const pron = Object.entries(lj.pronounce || {}).sort((a, b) => b[0].length - a[0].length);
  const facts = fs.existsSync(path.join(dir, 'facts.json')) ? readJson(path.join(dir, 'facts.json')) : [];
  for (const f of facts) if (f.verdict === 'помилка' || f.verdict === 'не підтверджено') errors.push(`facts.json: твердження ${f.id} має вердикт «${f.verdict}»: ${f.claim}`);
  const center = lj.layout === 'center', css0 = readIf(path.join(KIT, 'theme', 'base.css')) + (center ? readIf(path.join(KIT, 'theme', 'center.css')) : ''), fonts = readJson(path.join(KIT, 'theme', 'fonts.json'));
  const scenes = [], chapters = lj.chapters || [];
  if (!chapters.length) errors.push('lecture.json: немає розділів (chapters)');
  const seen = new Set(); let start = 0;
  const player = readIf(path.join(KIT, 'player2.html')), hashOf = s => sha(JSON.stringify([s.resolved, s.svg, s.css, fonts, player, FPS, s.prevHash]));
  const addScene = (id, ci, sc, svg, css) => {
    const E = m => errors.push(`сцена ${id}: ${m}`), narr = sc.narration || [], lead = sc.lead ?? .5, gap0 = .35, tail = sc.tail ?? .8, nar = {}, markers = {};
    let t = lead;
    narr.forEach((n, i) => {
      if (!/^[A-Za-z]\w*$/.test(n.id || '')) E(`некоректний id репліки «${n.id}»`); if (nar[n.id]) E(`повторний id репліки «${n.id}»`);
      if (!n.text) E(`репліка ${n.id} без тексту`);
      let spoken = n.text || ''; for (const [k, v] of pron) spoken = spoken.split(k).join(v);
      if (i > 0) t += n.gap ?? gap0;
      const m = measure(voice, id, { id: n.id, text: n.text || '', spoken }), r = { id: n.id, start: +t.toFixed(3), end: +(t + m.duration).toFixed(3), text: noAcc(strip(n.text || '')), spoken, markers: {}, estimated: !!m.estimated };
      for (const k in m.markers || {}) { r.markers[k] = +(t + m.markers[k]).toFixed(3); markers[k] = r.markers[k]; }
      nar[n.id] = r; t = r.end;
    });
    const raw = narr.length ? t + tail : (sc.duration ?? 4), duration = Math.ceil(raw * FPS - 1e-6) / FPS, nlist = Object.values(nar);
    const res = (v, where) => {
      if (v == null) return null; if (typeof v === 'number') return v;
      const s = String(v).trim(); if (/^-?\d+(\.\d+)?$/.test(s)) return +s;
      const m = s.match(/^(start|end|n\w+(?:\.end)?|@\w+)\s*(?:([+-])\s*(\d+(?:\.\d+)?))?$/); if (!m) { E(`${where}: незрозумілий вираз часу «${v}»`); return 0; }
      let base, b = m[1];
      if (b === 'start') base = 0; else if (b === 'end') base = duration;
      else if (b[0] === '@') { base = markers[b.slice(1)]; if (base == null) { E(`${where}: немає позначки ${b} у текстах реплік`); base = 0; } }
      else { const [nid, e] = b.split('.'), r = nar[nid]; if (!r) { E(`${where}: немає репліки «${nid}»`); base = 0; } else base = e ? r.end : r.start; }
      return +(base + (m[2] ? (m[2] === '-' ? -1 : 1) * +m[3] : 0)).toFixed(3);
    };
    const parts = sc.parts || [], needArt = parts.length || (sc.labels || []).length || (sc.grow || []).length || (sc.travel || []).length || (sc.camera || []).length || (sc.move || []).length || (sc.draw || []).length || (sc.loop || []).length;
    if (needArt && !svg) E('є частини чи підписи, але немає art.svg');
    if (svg) {
      if (!/<svg[^>]*\sviewBox=/.test(svg)) E('art.svg: немає viewBox'); if (/<svg[^>]*\s(width|height)=/.test(svg.match(/<svg[^>]*>/)[0])) E('art.svg: кореневий svg не повинен мати width/height');
      if (Buffer.byteLength(svg) > 30 * 1024) E(`art.svg більший за 30 КБ (${Math.round(Buffer.byteLength(svg) / 1024)} КБ)`);
      if (/<(linearGradient|radialGradient)|feGaussianBlur|(xlink:)?href\s*=\s*["']https?:/i.test(svg)) E('art.svg: градієнти, розмиття й зовнішні посилання заборонені');
      for (const p of parts) if (!hasId(svg, p)) E(`art.svg: немає групи #${p}`);
    }
    const chk = (what, idv, list) => { if (!list.includes(idv)) E(`${what}: невідома частина «${idv}»`); };
    const anch = (what, a) => { if (svg && a && !hasId(svg, a)) E(`${what}: у art.svg немає точки #${a}`); };
    const R = { art: svg ? sc.art : null, parts, states: [], grow: [], travel: [], camera: [], move: [], draw: [], loop: [], count: [], carry: null, labels: [], texts: [], duration, checkpoints: [], leader: { ...DEF.leader, ...sc.leader }, grey: { ...DEF.grey, ...sc.grey }, motion: { ...DEF.motion, ...sc.motion }, enter: sc.enter || 'fade', exit: sc.exit || 'fade' };
    if (svg && !sc.art) E('немає поля art (x, y, w, h)');
    const prev = scenes[scenes.length - 1], dfl = (v, d) => v ?? d;
    if (sc.carry) {
      if (!prev) E('carry: сцена перша в лекції, їй нема від чого продовжуватись');
      else { const same = !!(svg && prev.svg === svg && JSON.stringify(sc.art) === JSON.stringify(prev.art)); R.carry = { same }; R.enter = 'cut'; prev.resolved.exit = 'cut'; prev.hash = hashOf(prev);
        if (same) { sc.__init = {}; for (const id of prev.resolved.parts) sc.__init[id] = vcAt(prev, id, prev.duration); } }
    }
    (sc.camera || []).forEach((c, i) => { const w = `camera[${i}]`, v = c.view;
      if (typeof v === 'string') { if (v !== 'camera0' && svg && !hasId(svg, v)) E(`${w}: у art.svg немає прямокутника #${v}`); }
      else if (!v || ![v.x, v.y, v.w, v.h].every(Number.isFinite) || v.w <= 0 || v.h <= 0) E(`${w}: view — це id прямокутника в art.svg або {x, y, w, h}`);
      R.camera.push({ t: res(c.at, w + '.at'), dur: dfl(c.dur, 1.6), view: v }); });
    (sc.move || []).forEach((m, i) => { const w = `move[${i}]`; chk(w, m.id, parts); if (!m.to) E(`${w}: немає to (id точки)`); anch(w, m.to); anch(w, m.from);
      R.move.push({ id: m.id, to: m.to, from: m.from, t: res(m.at, w + '.at'), dur: dfl(m.dur, 1.4), scale: m.scale, rotate: m.rotate, out: res(m.out, w + '.out') }); });
    (sc.draw || []).forEach((d, i) => { chk(`draw[${i}]`, d.id, parts); R.draw.push({ id: d.id, t: res(d.at, `draw[${i}].at`), dur: dfl(d.dur, 1.4) }); });
    (sc.loop || []).forEach((l, i) => { const w = `loop[${i}]`; if (!['float', 'pulse', 'spin', 'flow'].includes(l.kind)) E(`${w}: невідомий kind «${l.kind}» (float, pulse, spin, flow)`);
      if (svg && !hasId(svg, l.id)) E(`${w}: у art.svg немає #${l.id}`); if (l.in == null) E(`${w}: немає in`);
      R.loop.push({ id: l.id, kind: l.kind, in: res(l.in, w + '.in'), out: res(l.out, w + '.out'), amp: l.amp, period: l.period }); });
    (sc.count || []).forEach((c, i) => { const w = `count[${i}]`, tok = '{' + (c.token || 'n') + '}', T = (sc.texts || []).find(x => x.id === c.id), B = (sc.labels || []).find(x => x.id === c.id), src = T ? T.html : B ? (B.text || '') + (B.sub || '') : null;
      if (src == null) E(`${w}: немає тексту чи підпису з id «${c.id}»`); else if (!src.includes(tok)) E(`${w}: у тексті «${c.id}» немає місця для числа ${tok}`);
      if (!Number.isFinite(c.from) || !Number.isFinite(c.to)) E(`${w}: from і to — числа`);
      R.count.push({ id: c.id, from: c.from, to: c.to, t: res(c.at, w + '.at'), dur: dfl(c.dur, 1.2), decimals: c.decimals, suffix: c.suffix, token: c.token }); });
    (sc.states || []).forEach((e, i) => { const w = `states[${i}]`; for (const k in e.set || {}) { chk(w, k, parts); if (!['hidden', 'color', 'grey'].includes(e.set[k])) E(`${w}: невідомий стан «${e.set[k]}»`); } R.states.push({ t: res(e.at, w + '.at'), dur: e.dur, set: e.set }); });
    (sc.grow || []).forEach((g, i) => { chk(`grow[${i}]`, g.id, parts); anch(`grow[${i}]`, g.origin); R.grow.push({ id: g.id, origin: g.origin, t: res(g.at, `grow[${i}].at`), dur: g.dur }); });
    (sc.travel || []).forEach((g, i) => { chk(`travel[${i}]`, g.id, parts); anch(`travel[${i}]`, g.path); R.travel.push({ id: g.id, path: g.path, t: res(g.at, `travel[${i}].at`), dur: g.dur, out: res(g.out, `travel[${i}].out`), rotate: g.rotate, scale: g.scale }); });
    (sc.labels || []).forEach((l, i) => { const w = `labels[${i}]`, o = { ...l, text: noAcc(l.text || ''), sub: l.sub && noAcc(l.sub), in: res(l.in, w + '.in'), out: res(l.out, w + '.out') }; if (l.focus) chk(w, l.focus, parts); if (l.follow) chk(w, l.follow, parts); else if (!l.onArt && l.leader !== false && !l.anchor) E(`${w}: немає anchor (або follow)`); anch(w, l.anchor); if (o.out != null && o.out <= o.in) E(`${w}: out не пізніше за in`); R.labels.push(o); });
    const texts = [];
    if (lj.kicker && sc.kicker !== false && !(sc.texts || []).some(x => x.id === 'kicker')) texts.push({ id: 'kicker', kind: 'meta', html: esc(lj.kicker), in: typeof sc.kicker === 'string' ? res(sc.kicker, 'kicker') : R.carry && prev.resolved.texts.some(x => x.id === 'kicker') ? -1 : .3, out: null });
    (sc.texts || []).forEach((x, i) => { const w = `texts[${i}]`; if (!x.kind) E(`${w}: немає kind`); texts.push({ ...x, html: noAcc(x.html || ''), class: x.band === 'top' ? ((x.class || '') + ' k-top').trim() : x.class, in: res(x.in, w + '.in'), out: res(x.out, w + '.out') }); });
    const srcs = (sc.sources || []).map((s, i) => { const w = `sources[${i}]`, d = srcById[s.ref]; if (!d) E(`${w}: невідоме джерело «${s.ref}»`); return { ref: s.ref, text: d ? d.text : '', in: res(s.in, w + '.in'), out: res(s.out, w + '.out') }; }).sort((a, b) => a.in - b.in);
    srcs.forEach((s, i) => { const e = s.out ?? duration; const k = srcs.slice(0, i).filter(p => (p.out ?? duration) > s.in).length; texts.push({ id: `src-${s.ref}-${i}`, kind: 'source', html: 'Джерело: ' + esc(s.text), in: s.in, out: s.out, enter: 'fade', ...(k ? { y: 996 - 34 * k } : {}) }); });
    for (const x of texts) if (x.kind === 'title' && x.y == null) { const hooks = texts.filter(h => h.kind === 'hook' && h.in < (x.out ?? duration) && x.in < (h.out ?? duration)); if (hooks.length && !/k-low/.test(x.class || '')) x.class = ((x.class || '') + ' k-low').trim(); }
    texts.forEach(x => { if (x.out != null && x.out <= x.in) E(`текст ${x.id}: out не пізніше за in`); }); R.texts = texts;
    R.states.sort((a, b) => a.t - b.t); R.checkpoints = sc.checkpoints ? sc.checkpoints.map((c, i) => res(c, `checkpoints[${i}]`)) : nlist.length ? nlist.map(r => +((r.start + r.end) / 2).toFixed(2)) : [+(duration / 2).toFixed(2)];
    const chars = nlist.reduce((a, r) => a + noAcc(strip(r.spoken)).length, 0), spoken = nlist.reduce((a, r) => a + r.end - r.start, 0);
    const S0 = { id, chapter: ci, start: +start.toFixed(3), duration, narration: nlist, resolved: R, art: sc.art, svg, css: css0 + '\n' + css, init: sc.__init, prevHash: R.carry ? prev.hash : null, tempo: spoken ? chars / spoken : 0, sources: srcs.length };
    S0.hash = hashOf(S0); scenes.push(S0);
    start += duration;
  };
  chapters.forEach((c, ci) => (c.scenes || []).forEach(id => {
    if (seen.has(id)) return errors.push(`сцена ${id} є в кількох розділах`); seen.add(id);
    const sd = path.join(dir, 'scenes', id), sj = path.join(sd, 'scene.json');
    if (!fs.existsSync(sj)) return errors.push(`сцена ${id}: немає scenes/${id}/scene.json`);
    let sc; try { sc = JSON.parse(fs.readFileSync(sj, 'utf8')); } catch (e) { return errors.push(`сцена ${id}: scene.json не читається: ${e.message}`); }
    addScene(id, ci, sc, readIf(path.join(sd, 'art.svg')).replace(/<\?xml[^>]*\?>/, ''), readIf(path.join(sd, 'style.css')));
  }));
  if (lj.credits && lj.sources && lj.sources.length) {
    // Титри: рядок до 85 символів (2 рядки, далі «…»), сторінки по висоті 330…1000 px, кожна сторінка ≥3 с
    const wrap = t => { const L = []; let r = t; while (r && L.length < 2) { if (r.length <= 85) { L.push(r); r = ''; break; } let k = r.lastIndexOf(' ', 85); if (k < 40) k = 85; L.push(r.slice(0, k).trim()); r = r.slice(k).trim(); } if (r) L[1] = L[1].slice(0, 84).replace(/[\s,;.]+$/, '') + '…'; return L; };
    const pages = []; let cur = null;
    lj.sources.forEach(s => { const ls = wrap(s.text), h = ls.length * 36 + 14; if (!cur || cur.h + h > 670) pages.push(cur = { h: 0, items: [] }); cur.items.push({ s, ls, y: 330 + cur.h }); cur.h += h; });
    let t0 = 1.3; const texts = [{ id: 'cr-title', kind: 'title', html: 'Джерела', y: 140, in: .3 }];
    pages.forEach((p, pi) => { const d = Math.max(3, 1.5 + 1.2 * p.items.length), last = pi === pages.length - 1; p.items.forEach((it, i) => texts.push({ id: 'cr-' + it.s.id, kind: 'note', html: it.ls.map(esc).join('<br>'), y: it.y, in: pi ? t0 - 1.3 + .3 + .15 * i : .3 + .15 * i, out: last ? null : t0 - 1.3 + d - .2 })); t0 += d; });
    addScene('99-credits', chapters.length, { kicker: false, lead: .5, tail: .8, duration: t0, texts }, '', '');
    chapters.push({ title: 'Джерела', scenes: ['99-credits'] });
  }
  const total = start, slug = path.basename(dir);
  const chapDur = chapters.map((c, i) => scenes.filter(s => s.chapter === i).reduce((a, s) => a + s.duration, 0));
  chapDur.forEach((d, i) => { if (d > 360) warns.push(`розділ «${chapters[i].title}» триває ${(d / 60).toFixed(1)} хв (понад 6)`); });
  if (total < 600 || total > 1200) warns.push(`лекція триває ${(total / 60).toFixed(1)} хв (потрібно 10–20)`);
  scenes.forEach(s => { if (s.tempo && (s.tempo < 12 || s.tempo > 17)) warns.push(`сцена ${s.id}: темп мовлення ${s.tempo.toFixed(1)} символів/с (потрібно 12–17)`); });
  return { center, lj, voice, scenes, chapters, chapDur, errors, warns, total, slug, facts, fonts };
}

/* ---------- рух і порожні кадри (без браузера) ---------- */
const clampN = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x)), eioN = x => { x = clampN(x); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2 };
const VALS = { hidden: [0, 1], color: [1, 1], grey: [1, 0] };
function vcAt(s, id, t) { let v = (s.init && s.init[id]) || [0, 1];
  for (const e of s.resolved.states) { if (!(id in e.set)) continue; if (t < e.t) break; const k = eioN((t - e.t) / (e.dur ?? .7)), w = VALS[e.set[id]]; v = [v[0] + (w[0] - v[0]) * k, v[1] + (w[1] - v[1]) * k]; } return v; }
function analyze(s) {
  const R = s.resolved, D = s.duration, iv = [], big = ['hook', 'title', 'thesis', 'quiz']; let ev = 0, loops = 0;
  const add = (a, b) => { if (a != null) iv.push([a, Math.max(a, b)]); };
  R.states.forEach(e => { add(e.t, e.t + (e.dur ?? .7)); ev++; });
  R.texts.forEach(x => { add(x.in, x.in + .6); ev++; if (x.out != null) { add(x.out, x.out + .4); ev++; } });
  R.labels.forEach(x => { add(x.in, x.in + .7); ev++; if (x.out != null) { add(x.out, x.out + .4); ev++; } });
  for (const k of ['grow', 'travel', 'move', 'draw', 'count', 'camera']) R[k].forEach(e => { add(e.t, e.t + (e.dur || 1.4)); ev++; });
  R.loop.forEach(l => { add(l.in, l.out ?? D); loops++; });
  const gaps = []; let cur = 0;
  for (const [a, b] of iv.map(([a, b]) => [Math.max(0, a), Math.min(D, b)]).filter(([a, b]) => b > a).sort((x, y) => x[0] - y[0])) { if (a > cur) gaps.push([cur, a]); cur = Math.max(cur, b); }
  if (D > cur) gaps.push([cur, D]);
  const partVis = t => R.parts.some(id => { const [v, c] = vcAt(s, id, t); if (v <= .5 || c <= .5) return false;
    for (const k of ['draw', 'grow']) { const l = R[k].filter(d => d.id === id); if (l.length && !l.some(d => t >= d.t + .15 * d.dur)) return false; }
    return !R.move.some(m => m.id === id && m.out != null && t >= m.out); });
  const bigText = t => R.texts.some(x => big.includes(x.kind) && t >= x.in + .2 && (x.out == null || t < x.out));
  const empty = []; let a = null; const t0 = R.carry ? 0 : .6, step = .04;
  for (let t = t0; t <= D + 1e-9; t += step) { const e = !(bigText(t) || (R.art && partVis(t))); if (e && a == null) a = t; if ((!e || t + step > D) && a != null) { empty.push([a, e ? D : t]); a = null; } }
  return { events: ev, loops, longest: Math.max(0, ...gaps.map(g => g[1] - g[0])), gaps, empty, emptyTotal: empty.reduce((x, g) => x + g[1] - g[0], 0) };
}
const warnsOf = (s, an) => s.id === '99-credits' ? [] : an.gaps.filter(g => g[1] - g[0] > 5).map(g => `${s.id} t=${g[0].toFixed(1)}–${g[1].toFixed(1)} застиглий кадр: ${(g[1] - g[0]).toFixed(1)} с без жодної події чи руху (додайте рух камери, loop чи зміну стану)`);
const emptyFails = (s, an) => an.empty.filter(g => g[1] - g[0] > 1.2).map(g => `${s.id} t=${g[0].toFixed(1)}–${g[1].toFixed(1)} порожній кадр: ${(g[1] - g[0]).toFixed(1)} с немає ні кольорової частини малюнка, ні великого тексту`);

function plan(L, quiet) {
  if (L.errors.length) { console.error('ПОМИЛКИ:\n' + L.errors.map(e => ' - ' + e).join('\n')); process.exit(1); }
  fs.mkdirSync(OUT, { recursive: true });
  const timing = { fps: FPS, duration: +L.total.toFixed(3), scenes: L.scenes.map(s => ({ id: s.id, chapter: s.chapter, start: s.start, duration: s.duration, narration: s.narration, resolved: s.resolved })) };
  fs.writeFileSync(path.join(OUT, 'timing.json'), JSON.stringify(timing, null, 1));
  if (!quiet) {
    console.log(`Лекція «${L.lj.title}», голос: ${L.voice.provider}`);
    console.log(['Розділ', 'Сцена', 'Тривалість', 'Темп, сим/с'].map((h, i) => h.padEnd([30, 16, 12, 12][i])).join(''));
    for (const s of L.scenes) console.log([L.chapters[s.chapter].title, s.id, s.duration.toFixed(1) + ' с', s.tempo ? s.tempo.toFixed(1) : '—'].map((h, i) => String(h).padEnd([30, 16, 12, 12][i])).join(''));
    console.log(`Разом: ${L.total.toFixed(1)} с (${(L.total / 60).toFixed(1)} хв). Записано out/timing.json`);
  }
  L.warns.forEach(w => console.log('Увага: ' + w));
  return timing;
}

/* ---------- Playwright ---------- */
function pw() { try { return require('playwright'); } catch (e) { return require(path.join(execFileSync('npm', ['root', '-g']).toString().trim(), 'playwright')); } }
/* Безшовний стик: кінцевий стан попередньої сцени (той самий малюнок) або її останній кадр (різні малюнки) */
async function carryData(b, L, s) {
  if (!s.resolved.carry) return null; const prev = L.scenes[L.scenes.indexOf(s) - 1], p = await openScene(b, L, prev, await carryData(b, L, prev));
  await p.evaluate(t => window.renderAt(t), prev.duration); const end = await p.evaluate(() => window.endState()), same = s.resolved.carry.same;
  const img = same ? null : 'data:image/jpeg;base64,' + (await p.locator('#stage').screenshot({ type: 'jpeg', quality: 92 })).toString('base64'); await p.close(); return { same, end, img };
}
async function openScene(b, L, s, carry) {
  if (carry === undefined) carry = await carryData(b, L, s);
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } }); p.errs = []; p.on('pageerror', e => p.errs.push('JS: ' + e.message));
  await p.goto('file://' + path.join(KIT, 'player2.html'));
  for (const c of L.fonts) await p.addStyleTag({ url: 'file://' + path.join(KIT, c) });
  try { await p.evaluate(d => window.init(d), { scene: s.resolved, svg: s.svg, css: s.css, carry }); } catch (e) { throw new Error(`сцена ${s.id}: ${e.message.split('\n')[0]}`); }
  await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(250); return p;
}
async function pool(items, n, fn) { const q = [...items], out = []; await Promise.all(Array.from({ length: Math.min(n, q.length) }, async () => { while (q.length) out.push(await fn(q.shift())); })); return out; }
const pick = (L, name) => { if (!name) return L.scenes; const r = L.scenes.filter(s => s.id === name || s.id.startsWith(name)); if (!r.length) die(`Немає сцени «${name}». Є: ${L.scenes.map(s => s.id).join(', ')}`); return r; };

/* ---------- перевірка кадрів ---------- */
const lum = c => { const f = v => { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); }; return .2126 * f(c[0]) + .7152 * f(c[1]) + .0722 * f(c[2]); };
const ratio = (a, b) => (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
const segRect = (a, b, r) => { let t0 = 0, t1 = 1; const dx = b[0] - a[0], dy = b[1] - a[1];
  for (const [p, q] of [[-dx, a[0] - r.x], [dx, r.x + r.w - a[0]], [-dy, a[1] - r.y], [dy, r.y + r.h - a[1]]]) { if (p === 0) { if (q < 0) return false; } else { const t = q / p; if (p < 0) { if (t > t1) return false; if (t > t0) t0 = t; } else { if (t < t0) return false; if (t < t1) t1 = t; } } } return t0 <= t1; };
const segSeg = (a, b, c, d) => { const o = (p, q, r) => Math.sign((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])); return o(a, b, c) !== o(a, b, d) && o(c, d, a) !== o(c, d, b); };
const MIN = { label: 30, onart: 28, thesis: 36, title: 60, meta: 18, hook: 40, quiz: 40, note: 26, source: 18 };

async function qaScene(b, L, s) {
  const { PNG } = require(path.join(KIT, 'node_modules', 'pngjs')), qd = path.join(OUT, 'qa', s.id), tmp = path.join(qd, 'tmp'); fs.rmSync(tmp, { recursive: true, force: true }); fs.mkdirSync(tmp, { recursive: true });
  const p = await openScene(b, L, s), stage = p.locator('#stage'), an = analyze(s), fails = emptyFails(s, an), shots = [], CH = s.resolved.checkpoints;
  const times = [...new Set([...CH, ...Array.from({ length: Math.max(0, Math.floor(s.duration - 1)) }, (_, i) => i + .9)])].sort((a, c) => a - c);
  for (const t of times) {
    await p.evaluate(t => window.renderAt(t), t);
    if (CH.includes(t)) { const f = path.join(tmp, `q${String(shots.length + 1).padStart(2, '0')}.jpg`); await stage.screenshot({ path: f, type: 'jpeg', quality: 88 }); shots.push(f); }
    const g = await p.evaluate(() => window.geometry());
    if (L.center && !s.resolved.camera.some(c => t >= c.t && t < c.t + c.dur)) { const f = PNG.sync.read(await stage.screenshot({ type: 'png' })); let sx = 0, n = 0;
      for (let yy = 0; yy < 1080; yy += 4) for (let xx = 0; xx < 1920; xx += 4) { const i = (yy * 1920 + xx) * 4; if (Math.max(f.data[i], f.data[i + 1], f.data[i + 2]) > 40) { sx += xx; n++; } }
      if (n > 150 && Math.abs(sx / n - 960) > 192) fails.push(`${s.id} t=${t} кадр зміщений: центр мас вмісту x=${Math.round(sx / n)} px, а має бути в межах ±10 % ширини (768…1152 px) від центру кадру`); }
    await p.evaluate(() => window.hideText(true)); const bg = PNG.sync.read(await stage.screenshot({ type: 'png' })); await p.evaluate(() => window.hideText(false));
    const tag = `${s.id} t=${t}`;
    for (const x of g.texts) {
      if (x.kind !== 'meta' && (x.x < 48 || x.y < 36 || x.x + x.w > 1872 || x.y + x.h > 1044)) fails.push(`${tag} «${x.id}» виходить за поля кадру (x ${Math.round(x.x)}…${Math.round(x.x + x.w)}, y ${Math.round(x.y)}…${Math.round(x.y + x.h)})`);
      if (x.size < (MIN[x.kind] || 30)) fails.push(`${tag} «${x.id}» шрифт ${x.size}px менший за мінімум ${MIN[x.kind] || 30}px`);
      for (const sm of x.small) if (sm < 26) fails.push(`${tag} «${x.id}» пояснення ${sm}px менше за 26px`);
      const m = x.color.match(/[\d.]+/g).map(Number), al = m.length > 3 ? m[3] : 1, tl = lum(m.slice(0, 3).map(v => v * al)), ls = [];
      for (let yy = Math.max(0, Math.floor(x.y)); yy < Math.min(1080, x.y + x.h); yy += 3) for (let xx = Math.max(0, Math.floor(x.x)); xx < Math.min(1920, x.x + x.w); xx += 3) { const i = (yy * 1920 + xx) * 4; ls.push(lum([bg.data[i], bg.data[i + 1], bg.data[i + 2]])); }
      if (ls.length) { ls.sort((a, c) => a - c); const worst = Math.min(ratio(tl, ls[Math.floor(ls.length * .08)]), ratio(tl, ls[Math.floor(ls.length * .92)])), need = x.size >= 36 ? 3 : 4.5;
        if (worst < need) fails.push(`${tag} «${x.id}» контраст із тлом ${worst.toFixed(1)}:1, потрібно ≥ ${need}:1 (текст лежить на строкатому або надто близькому за тоном тлі)`); }
    }
    for (let i = 0; i < g.texts.length; i++) for (let j = i + 1; j < g.texts.length; j++) { const a = g.texts[i], c = g.texts[j]; if (a.x < c.x + c.w + 8 && c.x < a.x + a.w + 8 && a.y < c.y + c.h + 8 && c.y < a.y + a.h + 8) fails.push(`${tag} тексти «${a.id}» і «${c.id}» накладаються`); }
    for (const l of g.lines) for (const x of g.texts) if (segRect(l.a, l.b, { x: x.x - 4, y: x.y - 4, w: x.w + 8, h: x.h + 8 })) fails.push(`${tag} виноска «${l.id}» проходить крізь текст «${x.id}»`);
    for (let i = 0; i < g.lines.length; i++) for (let j = i + 1; j < g.lines.length; j++) if (g.lines[i].id !== g.lines[j].id && segSeg(g.lines[i].a, g.lines[i].b, g.lines[j].a, g.lines[j].b)) fails.push(`${tag} виноски «${g.lines[i].id}» і «${g.lines[j].id}» перетинаються`);
    for (const l of g.lines) { const len = Math.hypot(l.b[0] - l.a[0], l.b[1] - l.a[1]); if (len > 520) fails.push(`${tag} виноска «${l.id}» задовга (${Math.round(len)}px): підпис має стояти поруч зі структурою`); }
  }
  let sheet = path.join(qd, 'sheet.jpg');
  try { execFileSync('ffmpeg', ['-loglevel', 'error', '-y', '-start_number', '1', '-framerate', '1', '-i', path.join(tmp, 'q%02d.jpg'), '-vf', `scale=640:360,tile=4x${Math.ceil(shots.length / 4)}`, '-frames:v', '1', sheet]); } catch (e) { p.errs.push('аркуш кадрів не зібрано'); sheet = null; }
  fs.rmSync(tmp, { recursive: true, force: true }); await p.close();
  return { id: s.id, hash: s.hash, fails: [...new Set([...p.errs, ...fails])], warns: warnsOf(s, an), sheet };
}

/* ---------- субтитри ---------- */
const tc = t => { const ms = Math.round(t * 1000), h = Math.floor(ms / 3.6e6), m = Math.floor(ms % 3.6e6 / 6e4), s = Math.floor(ms % 6e4 / 1e3); return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(ms % 1000).padStart(3, '0')}`; };
function wrap2(txt, lim = 42) { // не більше двох рядків; розрив на пробілі, найближчому до середини
  if (txt.length <= lim) return txt; const w = txt.split(' '); let best = 1, bv = 1e9;
  for (let i = 1; i < w.length; i++) { const v = Math.max(w.slice(0, i).join(' ').length, w.slice(i).join(' ').length); if (v < bv) { bv = v; best = i; } }
  return w.slice(0, best).join(' ') + '\n' + w.slice(best).join(' ');
}
function chunks(text, lim = 80) { // шматки до двох рядків: за реченнями, довгі — за словами
  const sents = text.split(/(?<=[.!?…])\s+/), out = []; let cur = '';
  const push = s => { if (s) out.push(s); };
  for (const s of sents) {
    if (s.length > lim) { push(cur); cur = ''; let line = ''; for (const w of s.split(' ')) { if ((line + ' ' + w).trim().length > lim) { push(line); line = w; } else line = (line + ' ' + w).trim(); } cur = line; continue; }
    if ((cur + ' ' + s).trim().length > lim) { push(cur); cur = s; } else cur = (cur + ' ' + s).trim();
  } push(cur); return out;
}
function srt(L) {
  let i = 1, o = '';
  for (const s of L.scenes) for (const n of s.narration) {
    const cs = chunks(n.text), tot = cs.reduce((a, c) => a + c.length, 0); let t = s.start + n.start;
    for (const c of cs) { const d = (n.end - n.start) * c.length / tot; o += `${i++}\n${tc(t)} --> ${tc(t + d)}\n${wrap2(c)}\n\n`; t += d; }
  }
  return o;
}

/* ---------- дії ---------- */
async function main() {
  const L = load();
  if (action === 'plan') { plan(L); process.exit(0); }
  if (action === 'status') {
    plan(L, true); const qr = fs.existsSync(path.join(OUT, 'qa', 'report.json')) ? readJson(path.join(OUT, 'qa', 'report.json')) : { scenes: {} };
    console.log(`Лекція «${L.lj.title}», голос: ${L.voice.provider}`);
    const nrep = L.scenes.reduce((a, s) => a + s.narration.length, 0), real = L.scenes.reduce((a, s) => a + s.narration.filter(n => !n.estimated).length, 0);
    console.log(`Голос: ${real}/${nrep} реплік синтезовано` + (L.voice.provider === 'estimate' ? ' (provider estimate: звуку не буде)' : ''));
    console.log(['Сцена', 'Тривалість', 'Перевірка', 'Кеш відео'].map((h, i) => h.padEnd([16, 12, 20, 12][i])).join(''));
    for (const s of L.scenes) { const q = qr.scenes[s.id], qs = !q ? 'не проводилась' : q.hash !== s.hash ? 'застаріла' : q.fails.length ? `${q.fails.length} зауваж.` : 'без зауважень', h = path.join(OUT, 'scenes', s.id + '.hash'), cached = fs.existsSync(h) && fs.readFileSync(h, 'utf8') === s.hash && fs.existsSync(path.join(OUT, 'scenes', s.id + '.mp4'));
      console.log([s.id, s.duration.toFixed(1) + ' с', qs, cached ? 'є' : 'немає'].map((h, i) => String(h).padEnd([16, 12, 20, 12][i])).join('')); }
    console.log('Готове відео: ' + (fs.existsSync(path.join(OUT, L.slug + '.mp4')) ? `out/${L.slug}.mp4` : 'ще немає')); return;
  }
  if (action === 'motion') {
    plan(L, true); const W = [18, 12, 8, 7, 22, 12]; console.log(['Сцена', 'Тривалість', 'Подій', 'Loop', 'Найдовше без подій', 'Порожні, с'].map((h, i) => h.padEnd(W[i])).join(''));
    for (const s of L.scenes) { const a = analyze(s); console.log([s.id, s.duration.toFixed(1) + ' с', a.events, a.loops, a.longest.toFixed(1) + ' с' + (a.longest > 5 ? ' !' : ''), a.emptyTotal.toFixed(1) + (a.empty.some(g => g[1] - g[0] > 1.2) ? ' !' : '')].map((h, i) => String(h).padEnd(W[i])).join('')); }
    return console.log('«!»: найдовший відрізок без подій > 5 с (застиглий кадр) або порожній відрізок > 1,2 с (помилка qa).');
  }
  if (action === 'tts') {
    if (L.errors.length) plan(L, true);
    if (L.voice.provider === 'estimate') return console.log('Голос «estimate»: синтез не потрібен (оцінка тривалості).');
    if (!tts) die('kit/tts.js недоступний: синтез неможливий.');
    const m = await tts.synthesize(dir, L.voice, L.scenes.map(s => ({ id: s.id, narration: s.narration.map(n => ({ id: n.id, spoken: n.spoken })) })), { force: flags.force });
    return console.log(`Голос готовий: ${Object.keys((m && m.items) || {}).length} реплік у audio/manifest.json`);
  }
  if (action === 'qa') {
    if (L.errors.length) plan(L, true); const sel = pick(L, rest[0]), { chromium } = pw(), b = await chromium.launch();
    const results = await pool(sel, flags.jobs, s => qaScene(b, L, s)); await b.close(); results.sort((a, c) => L.scenes.findIndex(s => s.id === a.id) - L.scenes.findIndex(s => s.id === c.id));
    const rf = path.join(OUT, 'qa', 'report.json'), old = fs.existsSync(rf) ? readJson(rf).scenes : {}, scenes = {};
    for (const s of L.scenes) if (old[s.id]) scenes[s.id] = old[s.id]; for (const r of results) scenes[r.id] = { hash: r.hash, pass: !r.fails.length, fails: r.fails, warns: r.warns, sheet: r.sheet && path.relative(dir, r.sheet) };
    const pass = L.scenes.every(s => scenes[s.id] && scenes[s.id].pass && scenes[s.id].hash === s.hash); fs.writeFileSync(rf, JSON.stringify({ pass, scenes }, null, 1));
    for (const r of results) { console.log(`${r.id}: ${r.fails.length ? 'FAIL (' + r.fails.length + ')\n' + r.fails.slice(0, 40).join('\n') : 'PASS'}`); r.warns.forEach(w => console.log('Увага: ' + w)); if (r.sheet) console.log('  аркуш кадрів: ' + r.sheet); }
    process.exit(results.some(r => r.fails.length) ? 1 : 0);
  }
  if (action === 'still') {
    plan(L, true); if (rest.length < 2) die('Використання: still <сцена> <час>'); const s = pick(L, rest[0])[0], ex = rest[1];
    let t; if (/^-?\d+(\.\d+)?$/.test(ex)) t = +ex; else { // вираз часу тим самим розбором: тимчасова сцена з одним підписом
      const m = ex.match(/^(start|end|n\w+(?:\.end)?|@\w+)\s*(?:([+-])\s*(\d+(?:\.\d+)?))?$/); if (!m) die(`Незрозумілий час «${ex}»`);
      const b0 = m[1], n = b0.startsWith('@') ? null : s.narration.find(r => r.id === b0.split('.')[0]); let base;
      if (b0 === 'start') base = 0; else if (b0 === 'end') base = s.duration; else if (b0[0] === '@') base = s.narration.map(r => r.markers[b0.slice(1)]).find(v => v != null); else base = n && (b0.includes('.') ? n.end : n.start);
      if (base == null) die(`Не знайдено «${b0}» у сцені ${s.id}`); t = base + (m[2] ? (m[2] === '-' ? -1 : 1) * +m[3] : 0); }
    const { chromium } = pw(), b = await chromium.launch(), p = await openScene(b, L, s), qd = path.join(OUT, 'qa', s.id); fs.mkdirSync(qd, { recursive: true });
    await p.evaluate(t => window.renderAt(t), t); const f = path.join(qd, `still_${ex.replace(/[^\w.+-]/g, '_')}.jpg`); await p.locator('#stage').screenshot({ path: f, type: 'jpeg', quality: 92 }); await b.close(); return console.log(`ok (t=${t.toFixed(2)} с) ${f}`);
  }
  if (action === 'render') {
    const timing = plan(L, true); const sel = pick(L, rest[0]), sd = path.join(OUT, 'scenes'); fs.mkdirSync(sd, { recursive: true });
    const todo = sel.filter(s => flags.force || !(fs.existsSync(path.join(sd, s.id + '.hash')) && fs.readFileSync(path.join(sd, s.id + '.hash'), 'utf8') === s.hash && fs.existsSync(path.join(sd, s.id + '.mp4'))));
    for (const s of sel) if (!todo.includes(s)) console.log(`${s.id}: з кешу`);
    if (todo.length) {
      const { chromium } = pw(), b = await chromium.launch();
      await pool(todo, flags.jobs, async s => {
        const p = await openScene(b, L, s), N = Math.round(s.duration * FPS), file = path.join(sd, s.id + '.mp4'), tmp = path.join(sd, s.id + '.tmp.mp4');
        const ff = spawn('ffmpeg', ['-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', String(FPS), '-f', 'mp4', tmp], { stdio: ['pipe', 'inherit', 'inherit'] });
        const done = new Promise((res, rej) => { ff.on('exit', c => c ? rej(new Error('ffmpeg: код ' + c)) : res()); ff.stdin.on('error', () => { }); });
        for (let i = 0; i < N; i++) { await p.evaluate(t => window.renderAt(t), i / FPS); const buf = await p.locator('#stage').screenshot({ type: 'jpeg', quality: 95 }); if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r)); }
        ff.stdin.end(); await done; await p.close(); if (p.errs.length) die(`${s.id}: ${p.errs[0]}`);
        fs.renameSync(tmp, file); fs.writeFileSync(path.join(sd, s.id + '.hash'), s.hash); console.log(`${s.id}: відрендерено (${s.duration.toFixed(1)} с)`);
      }); await b.close();
    }
    if (rest[0]) return console.log('Одну сцену відрендерено: out/scenes/. Повне відео — без назви сцени.');
    const list = path.join(OUT, 'concat.txt'); fs.writeFileSync(list, L.scenes.map(s => `file '${path.join(sd, s.id + '.mp4')}'`).join('\n'));
    fs.writeFileSync(path.join(OUT, L.slug + '.uk.srt'), srt(L));
    let audio = null; if (!flags.noAudio && tts) { try { audio = await tts.buildAudio(dir, timing); } catch (e) { console.log('Звук не зібрано: ' + e.message); } }
    const mp4 = path.join(OUT, L.slug + '.mp4'), inp = ['-i', list], maps = ['-map', '0:v'];
    const a = ['-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list]; let k = 1;
    if (audio) { a.push('-i', audio); maps.push('-map', k++ + ':a'); } a.push('-i', path.join(OUT, L.slug + '.uk.srt')); maps.push('-map', k + ':s');
    execFileSync('ffmpeg', [...a, ...maps, '-c:v', 'copy', ...(audio ? ['-c:a', 'aac', '-b:a', '192k'] : []), '-c:s', 'mov_text', '-metadata:s:s:0', 'language=ukr', '-movflags', '+faststart', mp4]);
    fs.rmSync(list, { force: true }); console.log(`Готово: ${mp4}` + (audio ? '' : ' (без звуку)')); return;
  }
  die(`Невідома дія «${action}». Є: plan, tts, qa, render, still, status, motion`, 2);
}
main().catch(e => die('Помилка: ' + (e.stack || e.message)));
