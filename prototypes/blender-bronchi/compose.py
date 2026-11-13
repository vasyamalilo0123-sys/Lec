"""Збирання відео: перехресні переходи між станами, повільне наближення, горошина, накладення, голос.

python3 compose.py <тека рендеру> <тека накладень> <вихід.mp4> [кадр_від кадр_до]
"""
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageFilter

import timeline as TL

R, OV, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
F0 = int(sys.argv[4]) if len(sys.argv) > 4 else 0
F1 = int(sys.argv[5]) if len(sys.argv) > 5 else TL.NFRAMES
W, H = TL.W, TL.H

_cache = {}


def still(name):
    if name not in _cache:
        _cache[name] = Image.open(os.path.join(R, f"still_{name}.png")).convert("RGB")
    return _cache[name]


_bp = os.path.join(R, "pea", "boxes.json")
boxes = json.load(open(_bp)) if os.path.exists(_bp) else {}
mask = Image.new("L", (240, 240), 0)
mask.paste(255, (26, 26, 214, 214))
mask = mask.filter(ImageFilter.GaussianBlur(11))
BLACK = Image.new("RGB", (W, H), (0, 0, 0))
ovmap = json.load(open(os.path.join(OV, "map.json")))


def layer(name, f, t):
    """Картинка стану в координатах кадру 1920×1080."""
    if name == "black":
        return BLACK
    if name == "hook":
        return Image.open(os.path.join(R, "hook", f"{min(f, TL.HOOK_FRAMES - 1):05d}.png")).convert("RGB")
    img = still(name)
    if name == "cut" and str(f) in boxes and TL.PEA_VISIBLE[0] <= t:
        b = boxes[str(f)]
        patch = Image.open(os.path.join(R, "pea", f"{b['src']:05d}.png")).convert("RGB")
        a = min(1.0, (t - TL.PEA_VISIBLE[0]) / 0.25, (TL.PEA_VISIBLE[1] - t) / 0.3)
        x0, y0, x1, y1 = b["box"]
        top = 240 - (y1 - y0) if y0 == 0 else 0  # обрізана верхнім краєм кадру ділянка
        m = mask.crop((0, top, x1 - x0, top + (y1 - y0))).point(lambda v: int(v * max(a, 0)))
        if m.size != patch.size:  # Blender округлює межі ділянки по-своєму
            m = m.resize(patch.size)
        img = img.copy()
        img.paste(patch, tuple(b["box"][:2]), m)
    cam = TL.CAM_OF.get(name, "close")
    z = TL.zoom(cam, t)
    cw, ch = TL.SW / z, TL.SH / z
    box = ((TL.SW - cw) / 2, (TL.SH - ch) / 2, (TL.SW + cw) / 2, (TL.SH + ch) / 2)
    return img.resize((W, H), Image.LANCZOS, box=box)


def frame(f):
    t = f / TL.FPS
    img = None
    for i, (t0, name, dur) in enumerate(TL.KEYS):
        if t < t0:
            break
        nxt = TL.KEYS[i + 1] if i + 1 < len(TL.KEYS) else None
        if nxt and t >= nxt[0] + nxt[2]:
            continue  # цей шар уже повністю перекрито наступним
        cur = layer(name, f, t)
        w = TL.smooth((t - t0) / dur) if dur > 0 else 1.0
        img = cur if img is None or w >= 1 else Image.blend(img, cur, w)
    ov = ovmap[f]
    if ov:
        o = Image.open(os.path.join(OV, ov)).convert("RGBA")
        img = Image.alpha_composite(img.convert("RGBA"), o).convert("RGB")
    return img


def audio_args():
    args, filt = [], []
    for i, n in enumerate(TL.SCENE["narration"]):
        args += ["-i", os.path.join(TL.LECTURE, "audio", "01-tree", n["id"] + ".mp3")]
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
        if f % 250 == 0:
            print("кадр", f, flush=True)
    p.stdin.close()
    if p.wait() != 0:
        sys.exit("ffmpeg завершився з помилкою")
    print("готово:", OUT)
