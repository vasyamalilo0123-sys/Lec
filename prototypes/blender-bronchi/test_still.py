"""Пробний кадр: python3 test_still.py <geo> <out.png> <json стану> <json камери> [ширина] [семпли]"""
import json
import sys
import time

import scene

geo, out = sys.argv[1], sys.argv[2]
st = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
cam = {"target": [0, 0, -20], "dir": [0, -1, 0.05], "dist": 1500, "lens": 85}
if len(sys.argv) > 4:
    cam.update(json.loads(sys.argv[4]))
w = int(sys.argv[5]) if len(sys.argv) > 5 else 960
spp = int(sys.argv[6]) if len(sys.argv) > 6 else 48
S = scene.build(geo)
S.set_state(st)
S.set_camera(cam)
t = time.time()
S.render(out, (w, w * 9 // 16), spp)
print("рендер, с:", round(time.time() - t, 1))
