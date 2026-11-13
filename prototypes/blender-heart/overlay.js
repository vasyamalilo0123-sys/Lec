// Рендер накладень (тексти, виноски, кути) у прозорі PNG і перевірка перекриттів на кожному кадрі.
// node overlay.js <timeline.json> <тека виводу> [check]
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const data = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const out = process.argv[3];
  const checkOnly = process.argv[4] === 'check';
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto('file://' + path.join(__dirname, 'overlay.html'));
  await page.evaluate((d) => init(d), data);
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(async () => { await Promise.all(['200 40px Geologica', '300 40px Geologica', '400 40px Geologica'].map((f) => document.fonts.load(f, 'Жї'))); });
  const map = [];
  const problems = {};
  let lastSig = null, lastFile = null;
  for (let f = 0; f < data.n; f++) {
    const r = await page.evaluate((k) => render(k), f);
    for (const b of r.bad) (problems[b] = problems[b] || []).push(f);
    if (!r.any) { map.push(null); lastSig = null; continue; }
    if (r.sig !== lastSig) {
      lastFile = String(f).padStart(5, '0') + '.png';
      if (!checkOnly) await page.locator('#stage').screenshot({ path: path.join(out, lastFile), omitBackground: true });
      lastSig = r.sig;
    }
    map.push(lastFile);
  }
  fs.writeFileSync(path.join(out, 'map.json'), JSON.stringify(map));
  const keys = Object.keys(problems);
  console.log(keys.length ? 'ПОРУШЕННЯ:' : 'Перевірка накладень: порушень немає (' + data.n + ' кадрів)');
  for (const k of keys) console.log('  ' + k + ' — кадри ' + problems[k][0] + '…' + problems[k][problems[k].length - 1]);
  await browser.close();
  process.exit(keys.length ? 1 : 0);
})();
