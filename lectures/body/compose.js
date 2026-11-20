// Кадр із титрами: node compose.js <сцена> → frames/<сцена>.jpg (1920×1080). Бере render/<сцена>.png і render/<сцена>.json.
// Поля опису (повертає build() сцени): kicker, title, sub, source, title_at: [x, y] (лівий верхній кут блоку заголовка, типово [96, 96]),
// title_size (типово 96), scrim: 'left' | 'right' | 'bottom' | 'top' | 'none', grade: false — не чіпати колір,
// labels: [{text, sub, p: [x, y, z], at: [x, y], align: 'left' | 'right'}] — at це місце тексту в кадрі 1920×1080; від нього йде виноска до точки p.
const fs = require('fs'), path = require('path'), { execFileSync } = require('child_process');
const { chromium } = require('playwright');
const here = __dirname, name = process.argv[2];
const R = path.join(here, 'render'), meta = JSON.parse(fs.readFileSync(path.join(R, name + '.json'), 'utf8'));
const graded = path.join(R, name + '.graded.png');
const G = meta.grade === false ? 'scale=1920:1080:flags=lanczos'
  : "scale=1920:1080:flags=lanczos,format=gbrp,split[a][b];[b]gblur=sigma=22,curves=all='0/0 0.4/0.08 1/1'[bl];[a][bl]blend=all_mode=screen:all_opacity=0.2,curves=all='0/0 0.25/0.2 0.75/0.8 1/1',format=yuv444p,vignette=PI/5,noise=alls=4:allf=u";
execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', path.join(R, name + '.png'), '-filter_complex', G, '-frames:v', '1', graded]);
const fontDir = path.resolve(here, '../../kit/node_modules/@fontsource/geologica');
const css = [200, 300, 400, 500].map((w) => `<link rel="stylesheet" href="file://${fontDir}/${w}.css">`).join('');
const esc = (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;');
const [tx, ty] = meta.title_at || [96, 96], ts = meta.title_size || 96;
const SCR = { left: 'linear-gradient(90deg,rgba(0,0,0,.72),rgba(0,0,0,0) 55%)', right: 'linear-gradient(270deg,rgba(0,0,0,.72),rgba(0,0,0,0) 55%)',
  bottom: 'linear-gradient(0deg,rgba(0,0,0,.8),rgba(0,0,0,0) 40%)', top: 'linear-gradient(180deg,rgba(0,0,0,.75),rgba(0,0,0,0) 40%)' };
let lines = '', labs = '';
for (const l of meta.labels || []) {
  const [x, y] = l.at, [px, py] = l.px, right = l.align === 'right';
  const ex = right ? x + 14 : x - 14, ey = y + 18;
  lines += `<path d="M${px} ${py} L${ex} ${ey}" /><circle cx="${px}" cy="${py}" r="5"/>`;
  labs += `<div class="lab" style="${right ? `right:${1920 - x}px;text-align:right` : `left:${x}px`};top:${y}px"><div class="n">${esc(l.text)}</div>${l.sub ? `<div class="v">${esc(l.sub)}</div>` : ''}</div>`;
}
const html = `<!doctype html><html><head><meta charset="utf-8">${css}<style>
*{margin:0;padding:0;box-sizing:border-box}body{width:1920px;height:1080px;overflow:hidden;background:#000;font-family:Geologica,sans-serif;color:#fff;font-weight:300}
img,.scr,svg{position:absolute;left:0;top:0;width:1920px;height:1080px}
.head{position:absolute;left:${tx}px;top:${ty}px;max-width:900px}
.kicker{font-size:24px;font-weight:400;letter-spacing:.16em;text-transform:uppercase;color:rgba(255,255,255,.72);margin-bottom:14px}
.title{font-size:${ts}px;font-weight:200;letter-spacing:-.015em;line-height:1.02}
.sub{font-size:34px;line-height:1.3;margin-top:18px;color:rgba(255,255,255,.88)}
.src{position:absolute;left:96px;bottom:54px;font-size:20px;color:rgba(255,255,255,.55);max-width:1500px}
.lab{position:absolute}.lab .n{font-size:30px;font-weight:400;line-height:1.2;white-space:nowrap}.lab .v{font-size:23px;color:rgba(255,255,255,.72);margin-top:3px;white-space:nowrap}
svg path{stroke:rgba(255,255,255,.75);stroke-width:1.5;fill:none}svg circle{fill:none;stroke:#fff;stroke-width:2}
</style></head><body><img src="file://${graded}"><div class="scr" style="background:${SCR[meta.scrim || 'left'] || 'none'}"></div>
<svg viewBox="0 0 1920 1080">${lines}</svg>${labs}
<div class="head">${meta.kicker ? `<div class="kicker">${esc(meta.kicker)}</div>` : ''}${meta.title ? `<div class="title">${esc(meta.title)}</div>` : ''}${meta.sub ? `<div class="sub">${esc(meta.sub).replace(/\n/g, '<br>')}</div>` : ''}</div>
${meta.source ? `<div class="src">${esc(meta.source)}</div>` : ''}</body></html>`;
(async () => {
  fs.writeFileSync(path.join(R, name + '.html'), html);
  const b = await chromium.launch(), p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  await p.goto('file://' + path.join(R, name + '.html')); await p.evaluate(() => document.fonts.ready);
  fs.mkdirSync(path.join(here, 'frames'), { recursive: true });
  await p.screenshot({ path: path.join(here, 'frames', name + '.jpg'), type: 'jpeg', quality: 93 });
  await b.close(); console.log('frame', path.join(here, 'frames', name + '.jpg'));
})();
