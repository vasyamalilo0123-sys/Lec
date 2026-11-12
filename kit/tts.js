// Голос лекції: синтез реплік, кеш (audio/manifest.json), збирання доріжки. Специфікація: ENGINE.md, розділи 2, 3.2, 5.
// Постачальники: estimate (без звуку), beep (тестовий тон), elevenlabs (з мітками символів), piper (локальний).
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execFileSync, spawnSync } = require('child_process');

const DEFAULT_RATE = 14.5;
const ELEVEN_HOST = 'https://api.elevenlabs.io';
// Модель за замовчуванням: eleven_multilingual_v2 (типова модель методу, підтримує українську).
// Для eleven_v3 чи інших задайте voice.model у lecture.json.
const ELEVEN_MODEL = 'eleven_multilingual_v2';
const ELEVEN_FORMAT = 'mp3_44100_128';

const sha1 = (s) => crypto.createHash('sha1').update(s).digest('hex');
const round = (x, n = 3) => Math.round(x * 10 ** n) / 10 ** n;

// Вирізає позначки [[id]]; pos — індекс символу чистого тексту, перед яким стоїть позначка.
function parseMarks(text) {
  const marks = [];
  let plain = '';
  let last = 0;
  for (const m of String(text).matchAll(/\[\[([^\]\s]+)\]\]/g)) {
    plain += text.slice(last, m.index);
    marks.push({ id: m[1], pos: [...plain].length });
    last = m.index + m[0].length;
  }
  plain += text.slice(last);
  return { plain, marks };
}

const manifestPath = (dir) => path.join(dir, 'audio', 'manifest.json');
function readManifest(dir) {
  try { return JSON.parse(fs.readFileSync(manifestPath(dir), 'utf8')); } catch { return { voice: {}, items: {} }; }
}
function writeManifest(dir, m) {
  fs.mkdirSync(path.join(dir, 'audio'), { recursive: true });
  fs.writeFileSync(manifestPath(dir), JSON.stringify(m, null, 1) + '\n');
}

function voiceId(voice) {
  const p = voice.provider || 'estimate';
  if (p === 'elevenlabs') return { provider: p, voiceId: voice.voiceId, model: voice.model || ELEVEN_MODEL };
  if (p === 'piper') return { provider: p, modelPath: voice.modelPath };
  if (p === 'beep') return { provider: p, rate: voice.rate || DEFAULT_RATE };
  return { provider: 'estimate', rate: voice.rate || DEFAULT_RATE };
}
const itemKey = (spoken, voice) => sha1(spoken + '\n' + JSON.stringify(voiceId(voice)) + (voice.languageCode || '') + JSON.stringify(voice.settings || {}));

function estimateDuration(plain, voice) {
  return Math.max(1.2, [...plain.replace(/\u0301/g, '')].length / (voice.rate || DEFAULT_RATE));
}

function probeDuration(file) {
  const out = execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', file]).toString();
  return round(parseFloat(out));
}

// Тривалість і позначки для репліки: з маніфесту (якщо чинний запис) або оцінка.
// item: {id, spoken}. Для estimate звук не синтезується, тож завжди оцінка.
function measure(lectureDir, voice, sceneId, item) {
  const { plain, marks } = parseMarks(item.spoken ?? item.text ?? '');
  const len = [...plain].length, nacc = (n) => [...plain].slice(0, n).filter((c) => c === '\u0301').length; // знак наголосу U+0301 не додає часу в оцінці
  const prov = voice.provider || 'estimate';
  const entry = prov === 'estimate' ? null : readManifest(lectureDir).items[`${sceneId}/${item.id}`];
  const valid = entry && entry.key === itemKey(item.spoken ?? item.text ?? '', voice);
  const duration = valid ? entry.duration : estimateDuration(plain, voice);
  const markers = {};
  for (const m of marks) {
    if (valid && entry.charStarts && len) {
      markers[m.id] = round(m.pos >= entry.charStarts.length ? duration : entry.charStarts[m.pos], 3);
    } else {
      markers[m.id] = round(len ? ((m.pos - nacc(m.pos)) / (len - nacc(len))) * duration : 0, 3);
    }
  }
  return { duration: round(duration), markers, estimated: !valid };
}

// ---------- постачальники ----------

function ffmpeg(args) {
  const r = spawnSync('ffmpeg', ['-v', 'error', '-y', ...args], { encoding: 'utf8' });
  if (r.status !== 0) throw new Error(`ffmpeg завершився з помилкою: ${(r.stderr || '').trim()}`);
}

async function synthBeep(plain, voice, file) {
  const d = estimateDuration(plain, voice);
  ffmpeg(['-f', 'lavfi', '-i', `sine=frequency=440:sample_rate=48000:duration=${d.toFixed(3)}`, '-ac', '1', '-c:a', 'libmp3lame', '-b:a', '64k', file]);
  return {};
}

async function synthEleven(plain, voice, file) {
  if (!voice.voiceId) throw new Error('ElevenLabs: у lecture.json → voice не вказано voiceId.');
  const key = process.env.ELEVENLABS_API_KEY || 'proxy-placeholder';
  const url = `${ELEVEN_HOST}/v1/text-to-speech/${encodeURIComponent(voice.voiceId)}/with-timestamps?output_format=${ELEVEN_FORMAT}`;
  const body = { text: plain, model_id: voice.model || ELEVEN_MODEL };
  if (voice.languageCode) body.language_code = voice.languageCode;
  if (voice.settings) body.voice_settings = voice.settings;
  const hint = 'Дозвольте хост api.elevenlabs.io у налаштуваннях мережі середовища й додайте ключ ElevenLabs (змінна ELEVENLABS_API_KEY або секрет середовища для цього хоста).';
  // Запит через curl: він, на відміну від вбудованого fetch, зважає на проксі та сертифікати середовища.
  const tmp = file + '.req.json', out = file + '.resp.json';
  fs.writeFileSync(tmp, JSON.stringify(body));
  const r = spawnSync('curl', ['-sS', '-m', '180', '-X', 'POST', '-H', `xi-api-key: ${key}`, '-H', 'content-type: application/json', '--data-binary', '@' + tmp, '-o', out, '-w', '%{http_code}', url], { encoding: 'utf8' });
  fs.rmSync(tmp, { force: true });
  const status = parseInt(r.stdout, 10) || 0, text = fs.existsSync(out) ? fs.readFileSync(out, 'utf8') : '';
  fs.rmSync(out, { force: true });
  if (r.status !== 0 || !status) throw new Error(`ElevenLabs: немає зв'язку з api.elevenlabs.io (${(r.stderr || '').trim().slice(0, 160)}). ${hint}`);
  if (status === 401 || status === 403) throw new Error(`ElevenLabs: відмова ${status} (ключ відсутній, хибний або хост заблоковано політикою мережі). ${hint} ${text.slice(0, 200)}`);
  if (status < 200 || status >= 300) throw new Error(`ElevenLabs: помилка ${status}: ${text.slice(0, 300)}`);
  let j; try { j = JSON.parse(text); } catch (e) { throw new Error('ElevenLabs: відповідь не є JSON: ' + text.slice(0, 200)); }
  if (!j.audio_base64) throw new Error('ElevenLabs: у відповіді немає audio_base64.');
  fs.writeFileSync(file, Buffer.from(j.audio_base64, 'base64'));
  const al = j.alignment || {};
  const starts = al.character_start_times_seconds || al.characters_start_times_seconds;
  if (al.characters && starts) return { chars: al.characters, charStarts: starts.map((x) => round(x)) };
  return {};
}

async function synthPiper(plain, voice, file) {
  if (spawnSync('piper', ['--help']).error) throw new Error('Piper: команди `piper` немає в системі. Встановіть Piper або оберіть іншого постачальника.');
  if (!voice.modelPath) throw new Error('Piper: у lecture.json → voice не вказано modelPath (шлях до моделі .onnx).');
  const wav = file + '.wav';
  const r = spawnSync('piper', ['--model', voice.modelPath, '--output_file', wav], { input: plain, encoding: 'utf8' });
  if (r.status !== 0) throw new Error(`Piper: помилка синтезу: ${(r.stderr || '').trim().slice(0, 300)}`);
  ffmpeg(['-i', wav, '-c:a', 'libmp3lame', '-b:a', '96k', file]);
  fs.unlinkSync(wav);
  return {};
}

const SYNTH = { beep: synthBeep, elevenlabs: synthEleven, piper: synthPiper };

// Синтезує відсутні репліки. Повертає маніфест; кількість синтезованих — у властивості synthesized (не зберігається).
async function synthesize(lectureDir, voice, scenes, { force } = {}) {
  const prov = voice.provider || 'estimate';
  const manifest = readManifest(lectureDir);
  Object.defineProperty(manifest, 'synthesized', { value: 0, writable: true, enumerable: false });
  if (prov === 'estimate') return manifest;
  const fn = SYNTH[prov];
  if (!fn) throw new Error(`Невідомий постачальник голосу «${prov}». Дозволені: estimate, beep, elevenlabs, piper.`);
  manifest.voice = voiceId(voice);
  manifest.items = manifest.items || {};
  for (const sc of scenes) {
    for (const n of sc.narration || []) {
      const spoken = n.spoken ?? n.text;
      const id = `${sc.id}/${n.id}`;
      const key = itemKey(spoken, voice);
      const cur = manifest.items[id];
      if (!force && cur && cur.key === key && fs.existsSync(path.join(lectureDir, 'audio', cur.file))) continue;
      const rel = `${id}.mp3`;
      const file = path.join(lectureDir, 'audio', rel);
      fs.mkdirSync(path.dirname(file), { recursive: true });
      const { plain } = parseMarks(spoken);
      const extra = await fn(plain, voice, file);
      manifest.items[id] = { key, file: rel, duration: probeDuration(file), ...extra };
      manifest.synthesized++;
      writeManifest(lectureDir, manifest); // після кожної репліки: збій не втрачає зроблене
    }
  }
  writeManifest(lectureDir, manifest);
  return manifest;
}

// Одна доріжка out/audio.m4a (AAC, 48 кГц, моно) довжиною timing.duration. null, якщо звуку немає (estimate).
async function buildAudio(lectureDir, timing) {
  let prov;
  try { prov = JSON.parse(fs.readFileSync(path.join(lectureDir, 'lecture.json'), 'utf8')).voice?.provider; } catch {}
  const manifest = readManifest(lectureDir);
  prov = prov || manifest.voice?.provider || 'estimate';
  if (prov === 'estimate') return null;

  const clips = [];
  for (const sc of timing.scenes) {
    for (const n of sc.narration) {
      const entry = manifest.items[`${sc.id}/${n.id}`];
      const file = entry && path.join(lectureDir, 'audio', entry.file);
      if (!file || !fs.existsSync(file)) { console.warn(`Попередження: для ${sc.id}/${n.id} немає звукового файлу, репліку пропущено (виконайте tts).`); continue; }
      const planned = n.end - n.start;
      const real = probeDuration(file);
      if (Math.abs(real - planned) > 0.05) {
        console.warn(`Попередження: ${sc.id}/${n.id}: файл ${real.toFixed(2)} с, у хронометражі ${planned.toFixed(2)} с. Перерахуйте план (plan), звук не розтягується.`);
      }
      clips.push({ file, at: sc.start + n.start });
    }
  }
  const D = timing.duration;
  const out = path.join(lectureDir, 'out', 'audio.m4a');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const args = ['-f', 'lavfi', '-t', String(D), '-i', 'anullsrc=r=48000:cl=mono'];
  const parts = [];
  clips.forEach((c, i) => {
    args.push('-i', c.file);
    const ms = Math.round(c.at * 1000);
    parts.push(`[${i + 1}:a]aresample=48000,aformat=channel_layouts=mono,adelay=${ms}:all=1[a${i}]`);
  });
  const labels = ['[0:a]', ...clips.map((_, i) => `[a${i}]`)].join('');
  parts.push(`${labels}amix=inputs=${clips.length + 1}:normalize=0:duration=first,apad=whole_dur=${D},atrim=0:${D}[o]`);
  const script = path.join(lectureDir, 'out', 'audio.filter.txt');
  fs.writeFileSync(script, parts.join(';\n'));
  ffmpeg([...args, '-filter_complex_script', script, '-map', '[o]', '-c:a', 'aac', '-b:a', '128k', '-ar', '48000', '-ac', '1', '-t', String(D), out]);
  fs.unlinkSync(script);
  return out;
}

module.exports = { synthesize, buildAudio, measure };
