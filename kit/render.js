#!/usr/bin/env node
/* Рендер і перевірка варіанта лекції.
   node kit/render.js <тека варіанта> qa      — перевірка накладань, полів, розмірів, контрасту + аркуш кадрів out/sheet.jpg
   node kit/render.js <тека варіанта> video   — out/<назва>.mp4
   node kit/render.js <тека варіанта> still 12.4 — один кадр out/still_12.4.jpg */
const path = require('path'), fs = require('fs'), { execFileSync } = require('child_process');
let chromium; try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require(path.join(execFileSync('npm', ['root', '-g']).toString().trim(), 'playwright'))); }
const KIT = __dirname, dir = path.resolve(process.argv[2] || '.'), mode = process.argv[3] || 'qa', FPS = 25;
const { PNG } = require(path.join(KIT, 'node_modules', 'pngjs'));
const out = path.join(dir, 'out'); fs.mkdirSync(out, { recursive: true });
const isScene = fs.existsSync(path.join(dir, 'scene.json'));
const style = JSON.parse(fs.readFileSync(path.join(dir, isScene ? 'scene.json' : 'style.json'), 'utf8'));
const data = { style, scene: style, svg: fs.readFileSync(path.join(dir, 'art.svg'), 'utf8').replace(/<\?xml[^>]*\?>/, ''), css: fs.existsSync(path.join(dir, 'style.css')) ? fs.readFileSync(path.join(dir, 'style.css'), 'utf8') : '' };
const lum = c => { const f = v => { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); }; return .2126 * f(c[0]) + .7152 * f(c[1]) + .0722 * f(c[2]); };
const ratio = (a, b) => (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
const segRect = (a, b, r) => { // відрізок проти прямокутника (Ліанг–Барскі)
  let t0 = 0, t1 = 1; const dx = b[0] - a[0], dy = b[1] - a[1];
  for (const [p, q] of [[-dx, a[0] - r.x], [dx, r.x + r.w - a[0]], [-dy, a[1] - r.y], [dy, r.y + r.h - a[1]]]) {
    if (p === 0) { if (q < 0) return false; } else { const t = q / p; if (p < 0) { if (t > t1) return false; if (t > t0) t0 = t; } else { if (t < t0) return false; if (t < t1) t1 = t; } }
  } return t0 <= t1;
};
const segSeg = (a, b, c, d) => { const o = (p, q, r) => Math.sign((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])); return o(a, b, c) !== o(a, b, d) && o(c, d, a) !== o(c, d, b); };

(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  const errs = []; p.on('pageerror', e => errs.push('JS: ' + e.message));
  await p.goto('file://' + path.join(KIT, isScene ? 'player2.html' : 'player.html'));
  for (const c of style.fontCss || ['fonts/fixel.css']) await p.addStyleTag({ url: 'file://' + path.join(KIT, c) });
  try { await p.evaluate(d => window.init(d), data); } catch (e) { console.log('FAIL контракт: ' + e.message.split('\n')[0]); await b.close(); process.exit(1); }
  await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(300);
  const DUR = await p.evaluate('window.DUR'), CHECK = await p.evaluate('window.CHECK');
  const stage = p.locator('#stage');
  if (mode === 'still') { const t = parseFloat(process.argv[4] || '12'); await p.evaluate(t => window.renderAt(t), t); await stage.screenshot({ path: path.join(out, `still_${t}.jpg`), type: 'jpeg', quality: 92 }); console.log('ok', path.join(out, `still_${t}.jpg`)); }
  else if (mode === 'video') {
    const fr = path.join(out, 'frames'); fs.rmSync(fr, { recursive: true, force: true }); fs.mkdirSync(fr);
    for (let i = 0; i < FPS * DUR; i++) { await p.evaluate(t => window.renderAt(t), i / FPS); await stage.screenshot({ path: path.join(fr, `f${String(i).padStart(5, '0')}.jpg`), type: 'jpeg', quality: 95 }); }
    const mp4 = path.join(out, path.basename(dir) + '.mp4');
    execFileSync('ffmpeg', ['-loglevel', 'error', '-y', '-framerate', String(FPS), '-i', path.join(fr, 'f%05d.jpg'), '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', mp4]);
    fs.rmSync(fr, { recursive: true, force: true }); console.log('ok', mp4);
  } else {
    const fails = [], shots = [];
    const MIN = { label: 30, onart: 28, thesis: 36, title: 60, meta: 18, hook: 40, quiz: 40, note: 26 };
    const times = isScene ? [...new Set([...CHECK, ...Array.from({ length: Math.floor(DUR - 1) }, (_, i) => i + .9)])].sort((a, b) => a - b) : CHECK;
    for (const t of times) {
      await p.evaluate(t => window.renderAt(t), t);
      if (CHECK.includes(t)) { const f = path.join(out, `qa_${t}.jpg`); await stage.screenshot({ path: f, type: 'jpeg', quality: 88 }); shots.push(f); }
      const g = await p.evaluate(() => window.geometry());
      await p.evaluate(() => window.hideText(true)); const bg = PNG.sync.read(await stage.screenshot({ type: 'png' })); await p.evaluate(() => window.hideText(false));
      const tag = `t=${t}`;
      for (const x of g.texts) {
        if (x.kind !== 'meta' && (x.x < 48 || x.y < 36 || x.x + x.w > 1872 || x.y + x.h > 1044)) fails.push(`${tag} «${x.id}» виходить за поля кадру (x ${Math.round(x.x)}…${Math.round(x.x + x.w)}, y ${Math.round(x.y)}…${Math.round(x.y + x.h)})`);
        if (x.size < (MIN[x.kind] || 30)) fails.push(`${tag} «${x.id}» шрифт ${x.size}px менший за мінімум ${MIN[x.kind] || 30}px`);
        for (const s of x.small) if (s < 26) fails.push(`${tag} «${x.id}» пояснення ${s}px менше за 26px`);
        const m = x.color.match(/[\d.]+/g).map(Number), tl = lum(m), ls = [];
        for (let yy = Math.max(0, Math.floor(x.y)); yy < Math.min(1080, x.y + x.h); yy += 3) for (let xx = Math.max(0, Math.floor(x.x)); xx < Math.min(1920, x.x + x.w); xx += 3) { const i = (yy * 1920 + xx) * 4; ls.push(lum([bg.data[i], bg.data[i + 1], bg.data[i + 2]])); }
        ls.sort((a, b) => a - b); const worst = Math.min(ratio(tl, ls[Math.floor(ls.length * .08)]), ratio(tl, ls[Math.floor(ls.length * .92)])), need = x.size >= 36 ? 3 : 4.5;
        if (worst < need) fails.push(`${tag} «${x.id}» контраст із тлом ${worst.toFixed(1)}:1, потрібно ≥ ${need}:1 (текст лежить на строкатому або надто близькому за тоном тлі)`);
      }
      for (let i = 0; i < g.texts.length; i++) for (let j = i + 1; j < g.texts.length; j++) { const a = g.texts[i], c = g.texts[j]; if (a.x < c.x + c.w + 8 && c.x < a.x + a.w + 8 && a.y < c.y + c.h + 8 && c.y < a.y + a.h + 8) fails.push(`${tag} тексти «${a.id}» і «${c.id}» накладаються`); }
      for (const l of g.lines) for (const x of g.texts) if (segRect(l.a, l.b, { x: x.x - 4, y: x.y - 4, w: x.w + 8, h: x.h + 8 })) fails.push(`${tag} виноска «${l.id}» проходить крізь текст «${x.id}»`);
      for (let i = 0; i < g.lines.length; i++) for (let j = i + 1; j < g.lines.length; j++) if (g.lines[i].id !== g.lines[j].id && segSeg(g.lines[i].a, g.lines[i].b, g.lines[j].a, g.lines[j].b)) fails.push(`${tag} виноски «${g.lines[i].id}» і «${g.lines[j].id}» перетинаються`);
      for (const l of g.lines) { const len = Math.hypot(l.b[0] - l.a[0], l.b[1] - l.a[1]); if (len > 520) fails.push(`${tag} виноска «${l.id}» задовга (${Math.round(len)}px): підпис має стояти поруч зі структурою`); }
    }
    const n = shots.length, lay = shots.map((_, i) => `${i % 4 ? 'w0'.concat('+w0'.repeat(i % 4 - 1)) : '0'}_${Math.floor(i / 4) ? 'h0'.concat('+h0'.repeat(Math.floor(i / 4) - 1)) : '0'}`).join('|');
    try { execFileSync('ffmpeg', ['-loglevel', 'error', '-y', ...shots.flatMap(s => ['-i', s]), '-filter_complex', `${shots.map((_, i) => `[${i}]`).join('')}xstack=inputs=${n}:layout=${lay}:fill=black,scale=2560:-1`, '-frames:v', '1', path.join(out, 'sheet.jpg')]); } catch (e) { errs.push('аркуш кадрів не зібрано'); }
    shots.forEach(s => fs.rmSync(s, { force: true }));
    const uniq = [...new Set([...errs, ...fails])]; fs.writeFileSync(path.join(out, 'qa.json'), JSON.stringify({ pass: !uniq.length, fails: uniq }, null, 1));
    console.log(uniq.length ? 'FAIL (' + uniq.length + ')\n' + uniq.join('\n') : 'PASS'); console.log('аркуш кадрів:', path.join(out, 'sheet.jpg'));
    await b.close(); process.exit(uniq.length ? 1 : 0);
  }
  await b.close();
})();
