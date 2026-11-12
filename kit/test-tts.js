// Перевірка kit/tts.js на тестовому постачальнику beep, без мережі. Запуск: node kit/test-tts.js
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { synthesize, buildAudio, measure } = require('./tts.js');

const dir = '/tmp/claude-0/-home-user-Lec/d509b92e-57b8-5b90-9788-4f59ceecad87/scratchpad/eng-voice/lecture';
fs.rmSync(dir, { recursive: true, force: true });
fs.mkdirSync(dir, { recursive: true });

const voice = { provider: 'beep', rate: 14.5 };
fs.writeFileSync(path.join(dir, 'lecture.json'), JSON.stringify({ title: 'Тест', voice }));
const raw = [
  { id: 's1', narration: [{ id: 'n1', text: 'Ось дихальні шляхи. Згори — [[tr]]трахея, обабіч неї — легені.' }, { id: 'n2', text: 'Унизу трахея ділиться на два бронхи.' }] },
  { id: 's2', narration: [{ id: 'n1', text: 'Короткий вступ до другої сцени.' }, { id: 'n2', text: 'Права легеня має три частки, а ліва лише дві, бо серце займає місце.' }] },
];
const scenes = raw.map((s) => ({ id: s.id, narration: s.narration.map((n) => ({ id: n.id, spoken: n.text })) }));

let fails = 0;
const check = (name, ok, info = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${info ? '  ' + info : ''}`); if (!ok) fails++; };
const near = (a, b, e) => Math.abs(a - b) <= e;

// timing за правилами 3.2 (lead 0,5; gap 0,35; tail 0,8)
function buildTiming(v) {
  let t0 = 0;
  const out = [];
  for (const s of scenes) {
    let t = 0.5;
    const narration = s.narration.map((n, i) => {
      if (i) t += 0.35;
      const m = measure(dir, v, s.id, n);
      const r = { id: n.id, start: t, end: t + m.duration, spoken: n.spoken, markers: m.markers, estimated: m.estimated };
      t += m.duration;
      return r;
    });
    const duration = t + 0.8;
    out.push({ id: s.id, start: t0, duration, narration });
    t0 += duration;
  }
  return { fps: 25, duration: t0, scenes: out };
}

(async () => {
  // measure до синтезу: оцінка
  const before = measure(dir, voice, 's1', scenes[0].narration[0]);
  check('measure(beep) до синтезу — оцінка', before.estimated === true && before.markers.tr > 0);

  let m = await synthesize(dir, voice, scenes);
  check('перший synthesize синтезує 4 репліки', m.synthesized === 4, `синтезовано ${m.synthesized}`);
  check('маніфест на диску з 4 записами', Object.keys(JSON.parse(fs.readFileSync(path.join(dir, 'audio', 'manifest.json'))).items).length === 4);
  check('звукові файли існують', Object.values(m.items).every((i) => fs.existsSync(path.join(dir, 'audio', i.file))));

  m = await synthesize(dir, voice, scenes);
  check('повторний synthesize нічого не синтезує', m.synthesized === 0, `синтезовано ${m.synthesized}`);

  m = await synthesize(dir, voice, [{ id: 's1', narration: [{ id: 'n1', spoken: 'Змінений текст репліки.' }] }]);
  check('змінений текст синтезується заново', m.synthesized === 1);
  m = await synthesize(dir, voice, scenes); // відновити
  check('після повернення тексту ключ відрізняється: перезапис лише змінених', m.synthesized === 1, `синтезовано ${m.synthesized}`);

  // measure: узгодженість
  const it = scenes[0].narration[0];
  const est = measure(dir, { provider: 'estimate', rate: 14.5 }, 's1', it);
  const bp = measure(dir, voice, 's1', it);
  check('measure(beep) — не оцінка', bp.estimated === false);
  check('measure(estimate) — оцінка', est.estimated === true);
  check('тривалості estimate і beep збігаються (±0,1 с)', near(est.duration, bp.duration, 0.1), `${est.duration} vs ${bp.duration}`);
  check('позначка tr: estimate і beep збігаються (±0,1 с)', near(est.markers.tr, bp.markers.tr, 0.1), `${est.markers.tr} vs ${bp.markers.tr}`);
  check('позначка всередині репліки', bp.markers.tr > 0 && bp.markers.tr < bp.duration);

  const timing = buildTiming(voice);
  const out = await buildAudio(dir, timing);
  check('buildAudio повертає out/audio.m4a', out === path.join(dir, 'out', 'audio.m4a') && fs.existsSync(out));
  const pr = JSON.parse(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration:stream=codec_name,sample_rate', '-of', 'json', out]));
  const d = parseFloat(pr.format.duration);
  check('довжина доріжки = timing.duration (±0,05)', near(d, timing.duration, 0.05), `${d.toFixed(3)} vs ${timing.duration.toFixed(3)}`);
  check('AAC, 48 кГц', pr.streams[0].codec_name === 'aac' && pr.streams[0].sample_rate === '48000');

  // тон стоїть на своєму місці: перед першою реплікою s2 (початок = scene.start + lead) тиша, далі звук
  const s2 = timing.scenes[1];
  const at = s2.start + s2.narration[0].start;
  const volume = (ss, t) => {
    const r = require('child_process').spawnSync('ffmpeg', ['-hide_banner', '-ss', String(ss), '-t', String(t), '-i', out, '-af', 'volumedetect', '-f', 'null', '-'], { encoding: 'utf8' });
    const mm = /mean_volume: (-?[\d.]+) dB/.exec(r.stderr);
    return mm ? parseFloat(mm[1]) : -Infinity;
  };
  check('перед початком репліки s2/n1 — тиша, після — тон', volume(at - 0.3, 0.2) < -60 && volume(at + 0.2, 0.3) > -40, `до ${volume(at - 0.3, 0.2)} дБ, після ${volume(at + 0.2, 0.3)} дБ`);

  // estimate -> null
  fs.writeFileSync(path.join(dir, 'lecture.json'), JSON.stringify({ voice: { provider: 'estimate' } }));
  check('buildAudio для estimate повертає null', (await buildAudio(dir, timing)) === null);

  console.log(fails ? `\nПровалено перевірок: ${fails}` : '\nУсе гаразд');
  process.exit(fails ? 1 : 0);
})().catch((e) => { console.error('FAIL  виняток:', e); process.exit(1); });
