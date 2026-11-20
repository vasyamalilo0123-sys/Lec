# Синтез реплік через ElevenLabs (ключ підставляє проксі). Кеш: audio/<id>.mp3 + audio/<id>.json; повторний запуск нічого не синтезує.
import json, subprocess, base64, os, sys
here = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(here, 'script.json'), encoding='utf-8'))
v = S['voice']
for sh in S['shots']:
    mp3 = os.path.join(here, 'audio', sh['id'] + '.mp3'); meta = os.path.join(here, 'audio', sh['id'] + '.json')
    if os.path.exists(mp3) and os.path.exists(meta) and json.load(open(meta, encoding='utf-8')).get('text') == sh['text']:
        print('cached', sh['id']); continue
    body = json.dumps({'text': sh['text'], 'model_id': v['model'], 'language_code': v['languageCode']}, ensure_ascii=False)
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{v['voiceId']}/with-timestamps?output_format=mp3_44100_128"
    r = subprocess.run(['curl', '-sS', '-m', '180', '-X', 'POST', '-H', 'xi-api-key: sk_dummy', '-H', 'content-type: application/json',
                        '--data-binary', body.encode('utf-8'), url], capture_output=True)
    try:
        j = json.loads(r.stdout)
        audio = base64.b64decode(j['audio_base64'])
    except Exception:
        print('FAIL', sh['id'], r.stdout[:400], r.stderr[:300]); sys.exit(1)
    open(mp3, 'wb').write(audio)
    al = j.get('alignment') or {}
    json.dump({'text': sh['text'], 'chars': al.get('characters'), 'starts': al.get('character_start_times_seconds'),
               'ends': al.get('character_end_times_seconds')}, open(meta, 'w', encoding='utf-8'), ensure_ascii=False)
    print('ok', sh['id'], len(sh['text']), 'chars')
