# Субтитри з повним текстом диктора: по реченню на титр, часи з міток символів голосу. Пише anemia.srt.
import json, os, re
here = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.path.join(here, 'timeline.json'))); S = json.load(open(os.path.join(here, 'script.json'), encoding='utf-8'))
def ts(x):
    ms = int(round(x * 1000)); return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'
out = []; k = 1
for s in S['shots']:
    a = json.load(open(os.path.join(here, 'audio', s['id'] + '.json'), encoding='utf-8')); v = TL['voice'][s['id']]
    for m in re.finditer(r'[^.!?]+[.!?]', a['text']):
        i0 = m.start() + len(m.group()) - len(m.group().lstrip()); i1 = m.end() - 1
        txt = m.group().strip().replace('бе-дванадцять', 'B12')
        out.append(f"{k}\n{ts(v + a['starts'][i0])} --> {ts(v + a['ends'][i1] + 0.15)}\n{txt}\n"); k += 1
open(os.path.join(here, 'anemia.srt'), 'w', encoding='utf-8').write('\n'.join(out))
print(len(out), 'titles')
