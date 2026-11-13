#!/usr/bin/env bash
# Тимчасова лекція для перевірки однієї сцени з її попередницями (щоб працював carry).
# Використання: kit/one-scene.sh <тека лекції> <сцена>   → друкує шлях до тимчасової теки.
# Далі: node kit/lecture.js <шлях> qa|still|motion|plan ... Не викликайте tts на ній: audio — символічне посилання на кеш лекції.
set -euo pipefail
[ $# -eq 2 ] || { echo "Використання: $0 <тека лекції> <сцена>" >&2; exit 1; }
src=$(cd "$1" && pwd); scene=$2
[ -d "$src/scenes/$scene" ] || { echo "Немає сцени $scene у $src" >&2; exit 1; }
tmp=$(mktemp -d "${TMPDIR:-/tmp}/one-scene.XXXXXX")
node - "$src" "$scene" "$tmp" <<'J'
const fs = require('fs'), path = require('path');
const [src, scene, tmp] = process.argv.slice(2);
const lec = JSON.parse(fs.readFileSync(path.join(src, 'lecture.json'), 'utf8'));
const all = lec.chapters.flatMap(c => c.scenes);
let i = all.indexOf(scene);
if (i < 0) { console.error('Сцени немає в lecture.json'); process.exit(1); }
const carry = s => !!JSON.parse(fs.readFileSync(path.join(src, 'scenes', s, 'scene.json'), 'utf8')).carry;
let from = i;
while (from > 0 && carry(all[from])) from--;
const used = all.slice(from, i + 1);
lec.chapters = [{title: 'tmp', scenes: used}];
lec.credits = false;
fs.writeFileSync(path.join(tmp, 'lecture.json'), JSON.stringify(lec, null, 2));
fs.mkdirSync(path.join(tmp, 'scenes'));
for (const s of used) fs.symlinkSync(path.join(src, 'scenes', s), path.join(tmp, 'scenes', s));
for (const f of ['audio', 'facts.json']) if (fs.existsSync(path.join(src, f))) fs.symlinkSync(path.join(src, f), path.join(tmp, f));
J
echo "$tmp"
