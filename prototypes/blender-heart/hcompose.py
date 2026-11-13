"""Збирання відео «Серце»: python3 hcompose.py <тека рендеру> <тека накладень> <вихід.mp4|кадр.png> [від до]"""
import functools
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image

import htimeline as TL

R, OV, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
F0 = int(sys.argv[4]) if len(sys.argv) > 4 else 0
F1 = int(sys.argv[5]) if len(sys.argv) > 5 else TL.NFRAMES
W, H = TL.W, TL.H
BLACK = Image.new("RGB", (W, H), (0, 0, 0))
ovmap = json.load(open(os.path.join(OV, "map.json")))


@functools.lru_cache(maxsize=48)
def load(rel):
    im = Image.open(os.path.join(R, rel)).convert("RGB")
    return im if im.size == (W, H) else im.resize((W, H), Image.LANCZOS)


def layer(name, f):
    spec = [(p, w) for p, w in TL.layer_spec(name, f) if w > 1e-3]
    if not spec:
        return BLACK
    img = load(spec[0][0])
    if len(spec) > 1:
        img = Image.blend(img, load(spec[1][0]), spec[1][1] / (spec[0][1] + spec[1][1]))
    return img


def frame(f):
    t = f / TL.FPS
    img = None
    for i, (t0, name, dur) in enumerate(TL.KEYS):
        if t < t0:
            break
        nxt = TL.KEYS[i + 1] if i + 1 < len(TL.KEYS) else None
        if nxt and t >= nxt[0] + nxt[2]:
            continue
        cur = layer(name, f)
        w = TL.smooth((t - t0) / dur) if dur > 0 else 1.0
        img = cur if img is None or w >= 1 else Image.blend(img, cur, w)
    ov = ovmap[f]
    if ov:
        img = Image.alpha_composite(img.convert("RGBA"), Image.open(os.path.join(OV, ov)).convert("RGBA")).convert("RGB")
    return img


def audio_args():
    args, filt = [], []
    for i, n in enumerate(TL.SCENE["narration"]):
        args += ["-i", os.path.join(TL.LECTURE, "audio", "01-heart", n["id"] + ".mp3")]
        ms = int(n["start"] * 1000)
        filt.append(f"[{i + 1}:a]adelay={ms}|{ms}[a{i}]")
    k = len(filt)
    filt.append("".join(f"[a{i}]" for i in range(k)) + f"amix=inputs={k}:normalize=0,apad=whole_dur={TL.TOTAL}[a]")
    return args, ";".join(filt)


if __name__ == "__main__":
    if OUT.endswith(".png"):
        frame(F0).save(OUT)
        sys.exit()
    aargs, filt = audio_args()
    full = F0 == 0 and F1 == TL.NFRAMES
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(TL.FPS), "-i", "-"]
    if full:
        cmd += aargs + ["-filter_complex", filt, "-map", "0:v", "-map", "[a]", "-c:a", "aac", "-b:a", "160k"]
    cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-t", str((F1 - F0) / TL.FPS), OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(F0, F1):
        p.stdin.write(np.asarray(frame(f)).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        sys.exit("ffmpeg завершився з помилкою")
    print("готово:", OUT, F1 - F0, "кадрів")
