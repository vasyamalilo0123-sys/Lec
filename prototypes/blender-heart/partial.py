"""Відео з уже готових шарів (гачок і провідна система): python3 partial.py <рендер> <накладення> <вихід.mp4>"""
import os
import subprocess
import sys

import numpy as np

import htimeline as TL

_orig = TL.layer_spec


def spec(name, f):
    out = []
    for p, w in _orig(name, f):
        if name == "cond" and not os.path.exists(os.path.join(sys.argv[1], p)):
            p = "cond/000.png"   # фази спокою ще не відрендерено — показуємо початок циклу
        out.append((p, w))
    return out


TL.layer_spec = spec
import hcompose as C  # noqa: E402

END = TL.e("n2") + 0.4
N = round(END * TL.FPS)
args, filt = [], []
for i, nid in enumerate(("n1", "n2")):
    args += ["-i", os.path.join(TL.LECTURE, "audio", "01-heart", nid + ".mp3")]
    ms = int(TL.s(nid) * 1000)
    filt.append(f"[{i + 1}:a]adelay={ms}|{ms}[a{i}]")
filt.append(f"[a0][a1]amix=inputs=2:normalize=0,apad=whole_dur={END}[a]")
cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080", "-r", "25", "-i", "-", *args,
       "-filter_complex", ";".join(filt), "-map", "0:v", "-map", "[a]", "-c:a", "aac", "-b:a", "160k", "-c:v", "libx264", "-preset", "slow",
       "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-t", str(END), sys.argv[3]]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for f in range(N):
    p.stdin.write(np.asarray(C.frame(f)).tobytes())
p.stdin.close()
if p.wait() != 0:
    sys.exit("ffmpeg завершився з помилкою")
print("готово", N, "кадрів")
