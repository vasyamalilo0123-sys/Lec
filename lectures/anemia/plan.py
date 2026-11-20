# Розкладка хвилини: час початку кожної репліки й межі кадрів-планів. Пише timeline.json.
import json, os, subprocess
here = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(here, 'script.json'), encoding='utf-8'))
fps = S['fps']
dur = {s['id']: float(subprocess.check_output(['ffprobe', '-v', '0', '-show_entries', 'format=duration', '-of', 'csv=p=0',
       os.path.join(here, 'audio', s['id'] + '.mp3')])) for s in S['shots']}
LEAD, GAP, CUT_PRE, CUT_POST, TAIL = 1.5, 1.0, 1.0, 0.6, 4.5
t = LEAD; voice = {}; cuts = []; prev = None
for s in S['shots']:
    if prev is not None:
        if s['shot'] != prev:
            cut = t + CUT_PRE; cuts.append((s['shot'], cut)); t = cut + CUT_POST
        else:
            t += GAP
    voice[s['id']] = round(t, 3); t += dur[s['id']]; prev = s['shot']
total = t + TAIL
shots = []; a = 0.0; name = S['shots'][0]['shot']
for nm, c in cuts + [(None, total)]:
    f0, f1 = round(a * fps), round(c * fps)
    shots.append({'shot': name, 'start': f0, 'frames': f1 - f0}); a = c; name = nm
json.dump({'fps': fps, 'total_frames': round(total * fps), 'voice': voice, 'dur': dur, 'shots': shots},
          open(os.path.join(here, 'timeline.json'), 'w'), indent=1)
print(open(os.path.join(here, 'timeline.json')).read())
