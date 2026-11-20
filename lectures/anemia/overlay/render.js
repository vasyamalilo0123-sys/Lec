// Моушн-графіка поверх 3D: прозорі PNG 1920×1080 на кожен кадр. Часи появи беруться з міток символів голосу.
//   node overlay/render.js            — усі кадри в render/overlay/
//   node overlay/render.js 300 900    — лише вказані кадри (для перевірки) у render/overlay_check/
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '..');
const J = (p) => JSON.parse(fs.readFileSync(path.join(root, p), 'utf8'));
const TL = J('timeline.json'), S = J('script.json'), TRACK = J('overlay/track_sizes.json');
const fps = TL.fps;
const AL = Object.fromEntries(S.shots.map((s) => [s.id, J(`audio/${s.id}.json`)]));
const shot = Object.fromEntries(TL.shots.map((s) => [s.shot, { t0: s.start / fps, t1: (s.start + s.frames) / fps }]));

// час, коли диктор починає вимовляти фрагмент sub репліки id
function cue(id, sub) {
  const a = AL[id]; const i = a.text.indexOf(sub);
  if (i < 0) throw new Error(`немає «${sub}» у ${id}`);
  if (a.chars && a.chars.length === a.text.length) return TL.voice[id] + a.starts[i];
  return TL.voice[id] + TL.dur[id] * i / a.text.length;
}
const vend = (id) => TL.voice[id] + TL.dur[id];

const C = {
  n1_marrow: cue('n1', 'кістковий'), n1_num: cue('n1', 'близько двох'), n1_hb: cue('n1', 'гемоглобін'), n1_out: vend('n1') + 0.5,
  n2_title: cue('n2', 'Анемія'), n2_sub: cue('n2', 'гемоглобіну'), n2_m: cue('n2', 'ста тридцяти'), n2_f: cue('n2', 'ста двадцяти'),
  n2_p: cue('n2', 'ста десяти'), n2_out: shot.flow.t1 - 0.45,
  n3_in: shot.third.t0 + 0.3, n3_num: cue('n3', 'кожна третя'), n3_fe: cue('n3', 'Найчастіша'), n3_out: shot.third.t1 - 0.4,
  n4_in: shot.sizes.t0 + 0.3, n4_size: cue('n4', 'розмір'), n4_small: cue('n4', 'Дрібні'), n4_big: cue('n4', 'Великі'), n4_out: shot.sizes.t1 - 0.4,
  n5_a: cue('n5', 'Втома'), n5_b: cue('n5', 'блідість'), n5_c: cue('n5', 'задишка'), n5_swap: cue('n5', 'Анемія') - 0.25,
  n5_title: cue('n5', 'Анемія'), n5_find: cue('n5', 'знайти'), n5_src: vend('n5') + 0.5, end: TL.total_frames / fps - 0.7,
  sizes_t0: shot.sizes.t0, flow_t1: shot.flow.t1, third: shot.third, sizes: shot.sizes, outro: shot.outro,
};

const fontDir = path.resolve(root, '../../kit/node_modules/@fontsource/geologica');
const fontCss = [200, 300, 400, 500].map((w) => `<link rel="stylesheet" href="file://${fontDir}/${w}.css">`).join('');
const src = (s) => S.sources.find((x) => x.id === s).text;

const html = `<!doctype html><html><head><meta charset="utf-8">${fontCss}<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1920px;height:1080px;background:transparent;overflow:hidden;font-family:Geologica,sans-serif;color:#fff;font-weight:300}
.a{position:absolute;opacity:0;will-change:opacity,transform}
.scrim{position:absolute;inset:0;opacity:0}
.kicker{font-size:25px;font-weight:400;letter-spacing:.16em;text-transform:uppercase;color:rgba(255,255,255,.72)}
.big{font-size:168px;font-weight:200;letter-spacing:-.02em;line-height:1;font-variant-numeric:tabular-nums}
.title{font-size:132px;font-weight:300;letter-spacing:-.015em;line-height:1}
.sub{font-size:42px;font-weight:300;line-height:1.25}
.src{font-size:22px;font-weight:300;color:rgba(255,255,255,.62);left:96px;bottom:60px;max-width:1500px;line-height:1.4}
.row{display:flex;align-items:baseline;gap:28px;font-size:46px;width:640px;justify-content:space-between;border-top:1px solid rgba(255,255,255,.28);padding-top:14px}
.row b{font-weight:500;font-variant-numeric:tabular-nums}
.note{font-size:26px;color:rgba(255,255,255,.72)}
.lab{text-align:center;width:520px;margin-left:-260px}
.lab .n{font-size:38px;font-weight:400}.lab .v{font-size:30px;color:rgba(255,255,255,.75);margin-top:6px}
.lab .c{font-size:32px;font-weight:500;margin-top:16px;opacity:0}
.center{left:0;width:1920px;text-align:center}
</style></head><body>
<div class="scrim" id="scL" style="background:linear-gradient(90deg,rgba(10,0,0,.78) 0%,rgba(10,0,0,.6) 34%,rgba(10,0,0,0) 62%)"></div>
<div class="scrim" id="scC" style="background:radial-gradient(ellipse 62% 52% at 50% 50%,rgba(8,0,0,.8) 0%,rgba(8,0,0,.5) 55%,rgba(8,0,0,0) 100%)"></div>
<div class="scrim" id="scB" style="background:linear-gradient(0deg,rgba(6,0,0,.85) 0%,rgba(6,0,0,0) 34%)"></div>

<div class="a kicker" id="k1" style="left:96px;top:330px">Кістковий мозок · щосекунди</div>
<div class="a big" id="num1" style="left:90px;top:384px">≈ 2 000 000</div>
<div class="a sub" id="s1" style="left:96px;top:574px">нових еритроцитів</div>
<div class="a sub" id="hb" style="left:96px;top:690px;font-size:38px"><span style="font-weight:500">Гемоглобін (Hb)</span> — переносить кисень</div>

<div class="a kicker" id="k2" style="left:96px;top:196px">Визначення</div>
<div class="a title" id="t2" style="left:90px;top:244px">Анемія</div>
<div class="a sub" id="s2" style="left:96px;top:398px">гемоглобіну замало</div>
<div class="a row" id="r1" style="left:96px;top:520px"><span>чоловіки</span><b>&lt; 130 г/л</b></div>
<div class="a row" id="r2" style="left:96px;top:610px"><span>жінки</span><b>&lt; 120 г/л</b></div>
<div class="a row" id="r3" style="left:96px;top:700px"><span>вагітні</span><b>&lt; 110 г/л</b></div>
<div class="a note" id="r3n" style="left:96px;top:790px">у II триместрі — &lt; 105 г/л</div>
<div class="a src" id="src2">${src('s1')}</div>

<div class="a kicker" id="k3" style="left:96px;top:250px">Поширеність у світі</div>
<div class="a big" id="num3" style="left:90px;top:300px">30,7 %</div>
<div class="a sub" id="s3" style="left:96px;top:490px;width:640px">жінок 15–49 років<br>мають анемію</div>
<div class="a sub" id="fe" style="left:96px;top:672px;width:640px;border-top:1px solid rgba(255,255,255,.28);padding-top:22px"><span style="color:rgba(255,255,255,.72)">Найчастіша причина —</span><br><span style="font-weight:500">дефіцит заліза</span></div>
<div class="a src" id="src3">${src('s3')} (дані за 2023 р.) · ${src('s2')}</div>

<div class="a kicker" id="k4" style="left:96px;top:84px">Перша підказка — розмір клітини · MCV, середній об'єм еритроцита</div>
<div class="a lab" id="l0"><div class="n">мікроцитарна</div><div class="v">MCV &lt; 80 фл</div><div class="c" id="l0c">шукайте дефіцит заліза</div></div>
<div class="a lab" id="l1"><div class="n">нормоцитарна</div><div class="v">MCV 80–100 фл</div></div>
<div class="a lab" id="l2"><div class="n">макроцитарна</div><div class="v">MCV &gt; 100 фл</div><div class="c" id="l2c">дефіцит B<sub style="font-size:.6em">12</sub> або фолатів</div></div>

<div class="a sub center" id="sym" style="top:496px;font-size:64px;font-weight:200"><span id="w1">втома</span><span id="d1" style="opacity:.5"> · </span><span id="w2">блідість</span><span id="d2" style="opacity:.5"> · </span><span id="w3">задишка</span></div>
<div class="a title center" id="t5" style="top:412px;font-size:112px">Анемія — це наслідок</div>
<div class="a sub center" id="s5" style="top:566px;font-size:50px">Завдання лікаря — знайти причину</div>
<div class="a center" id="srcs" style="bottom:56px;font-size:21px;line-height:1.5;color:rgba(255,255,255,.66)">${S.sources.map((x) => x.text).join('<br>')}</div>

<script>
const C = ${JSON.stringify(C)}, TRACK = ${JSON.stringify(TRACK)}, FPS = ${fps};
const $ = (id) => document.getElementById(id);
const cl = (x) => Math.max(0, Math.min(1, x));
const ease = (x) => { x = cl(x); return 1 - Math.pow(1 - x, 3); };
// поява з легким підйомом, зникнення без руху
function show(id, t, tin, tout, din = 0.55, dout = 0.35, rise = 26) {
  const a = ease((t - tin) / din), b = 1 - ease((t - tout) / dout);
  const el = $(id); el.style.opacity = (a * b).toFixed(3);
  el.style.transform = 'translateY(' + ((1 - a) * rise).toFixed(1) + 'px)';
  return a * b;
}
function fade(id, t, tin, tout, max = 1, din = 0.6, dout = 0.4) {
  $(id).style.opacity = (max * ease((t - tin) / din) * (1 - ease((t - tout) / dout))).toFixed(3);
}
const fmt = (n) => String(Math.round(n)).replace(/\\B(?=(\\d{3})+$)/g, ' ');
window.seek = (frame) => {
  const t = frame / FPS;
  // ліва затемнена смуга під текст: плани 1–2
  const L1 = ease((t - C.n1_marrow + 0.3) / 0.6) * (1 - ease((t - C.n1_out) / 0.4));
  const L2 = ease((t - C.n2_title + 0.3) / 0.6) * (1 - ease((t - C.n2_out) / 0.35));
  const L3 = ease((t - C.n3_in) / 0.6) * (1 - ease((t - C.n3_out) / 0.35));
  $('scL').style.opacity = Math.max(L1, L2, L3 * 0.0).toFixed(3);
  // 1. гачок
  show('k1', t, C.n1_marrow, C.n1_out);
  show('num1', t, C.n1_num, C.n1_out);
  $('num1').textContent = '≈ ' + fmt(2000000 * ease((t - C.n1_num) / 1.5));
  show('s1', t, C.n1_num + 0.35, C.n1_out);
  show('hb', t, C.n1_hb, C.n1_out);
  // 2. визначення й пороги
  show('k2', t, C.n2_title - 0.2, C.n2_out);
  show('t2', t, C.n2_title, C.n2_out);
  show('s2', t, C.n2_sub, C.n2_out);
  show('r1', t, C.n2_m, C.n2_out); show('r2', t, C.n2_f, C.n2_out); show('r3', t, C.n2_p, C.n2_out);
  show('r3n', t, C.n2_p + 0.7, C.n2_out);
  fade('src2', t, C.n2_m, C.n2_out);
  // 3. кожна третя
  show('k3', t, C.n3_in, C.n3_out);
  show('num3', t, C.n3_num, C.n3_out);
  $('num3').textContent = (30.7 * ease((t - C.n3_num) / 1.3)).toFixed(1).replace('.', ',') + ' %';
  show('s3', t, C.n3_num + 0.35, C.n3_out);
  show('fe', t, C.n3_fe, C.n3_out);
  fade('src3', t, C.n3_num, C.n3_out);
  // 4. розміри: підписи їдуть за клітинами
  show('k4', t, C.n4_in, C.n4_out);
  const fr = Math.max(0, Math.min(TRACK.length - 1, frame - Math.round(C.sizes_t0 * FPS)));
  [0, 1, 2].forEach((i) => {
    const p = TRACK[fr]['size' + i], el = $('l' + i);
    el.style.left = p[0].toFixed(1) + 'px'; el.style.top = '838px';
    show('l' + i, t, C.n4_size + i * 0.22, C.n4_out);
  });
  $('l0c').style.opacity = ease((t - C.n4_small) / 0.5).toFixed(3);
  $('l2c').style.opacity = ease((t - C.n4_big) / 0.5).toFixed(3);
  const sb = ease((t - C.n4_size + 0.3) / 0.6) * (1 - ease((t - C.n4_out) / 0.35));
  // 5. фінал
  const sc5 = ease((t - C.n5_a + 0.4) / 0.7) * (1 - ease((t - C.end) / 0.5));
  $('scC').style.opacity = sc5.toFixed(3);
  show('sym', t, C.n5_a, C.n5_swap, 0.01, 0.3, 0);
  [['w1', C.n5_a], ['d1', C.n5_b], ['w2', C.n5_b], ['d2', C.n5_c], ['w3', C.n5_c]].forEach(([id, tt]) => {
    $(id).style.opacity = ((id[0] === 'd' ? 0.5 : 1) * ease((t - tt) / 0.45)).toFixed(3);
  });
  show('t5', t, C.n5_title, C.end, 0.7, 0.5);
  show('s5', t, C.n5_find, C.end, 0.6, 0.5);
  fade('srcs', t, C.n5_src, C.end, 1);
  $('scB').style.opacity = Math.max(sb, ease((t - C.n5_src) / 0.6) * (1 - ease((t - C.end) / 0.5)), Math.max(L2, L3) * 0.8).toFixed(3);
};
</script></body></html>`;

(async () => {
  const only = process.argv.slice(2).map(Number);
  const out = path.join(root, 'render', only.length ? 'overlay_check' : 'overlay');
  fs.mkdirSync(out, { recursive: true });
  fs.writeFileSync(path.join(root, 'render', 'overlay.html'), html);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto('file://' + path.join(root, 'render', 'overlay.html'));
  if (only.length) await page.addStyleTag({ content: 'html,body{background:#5a1410 !important}' });
  await page.evaluate(() => document.fonts.ready);
  const frames = only.length ? only : [...Array(TL.total_frames).keys()];
  for (const f of frames) {
    await page.evaluate((n) => window.seek(n), f);
    await page.screenshot({ path: path.join(out, String(f).padStart(4, '0') + '.png'), omitBackground: !only.length });
  }
  await browser.close();
  console.log('overlay frames:', frames.length, 'cues:', JSON.stringify(C));
})();
