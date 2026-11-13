"""Хронометраж прототипу «Серце»: час реплік — із плану рушія (lectures/heart-demo/out/timing.json)."""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LECTURE = os.path.join(HERE, "..", "..", "lectures", "heart-demo")
FPS, W, H = 25, 1920, 1080
CYCLE = 0.8

_t = json.load(open(os.path.join(LECTURE, "out", "timing.json")))
SCENE = _t["scenes"][0]
NAR = {n["id"]: n for n in SCENE["narration"]}
SCENE_END, TOTAL = SCENE["duration"], _t["duration"]
NFRAMES = round(TOTAL * FPS)
s = lambda i: NAR[i]["start"]  # noqa: E731
e = lambda i: NAR[i]["end"]  # noqa: E731
M = {k: v for n in NAR.values() for k, v in n["markers"].items()}

COND_PH = np.concatenate([np.linspace(0, 0.36, 20, endpoint=False), np.linspace(0.36, 1.0, 10, endpoint=False)])
CELL_PH = np.concatenate([np.linspace(0, 0.2, 14, endpoint=False), np.linspace(0.2, 1.0, 16, endpoint=False)])
AF_N, AF_BEATS, AF_PERIOD = 32, (0.0, 0.52), 1.28
VES_N = 50

# (час початку переходу, шар, тривалість переходу)
KEYS = [
    (0.0, "beat", 0.0),
    (s("n2") - 0.5, "cond", 0.9),
    (s("n4") - 0.2, "af", 0.7),
    (s("n5") - 0.3, "cor", 0.7),
    (M["cor"] + 1.3, "vessel", 0.7),
    (s("n6") - 0.4, "cells", 0.7),
    (s("n7") - 0.4, "beat", 0.8),
    (SCENE_END - 0.3, "black", 0.9),
]

# Уповільнений показ: (час, фаза циклу; ціла частина — номер циклу)
COND_KEYS = [(0, 0.90), (M["sa"], 1.0), (M["av"] - 0.7, 1.10), (M["av"], 1.12), (M["his"] - 0.3, 1.19), (M["his"], 1.20),
             (M["purk"], 1.24), (e("n2"), 1.33), (e("n2") + 1.2, 1.5), (M["p"] - 1.2, 1.94), (M["p"] - 0.7, 2.0), (M["p"], 2.06),
             (M["qrs"], 2.265), (M["t"], 2.60), (e("n3") - 0.4, 2.82), (s("n4") + 0.4, 3.0)]
CELL_KEYS = [(0, 0.0), (M["na"] - 0.4, 0.02), (M["na"] + 1.6, 0.19), (M["ca"], 0.24), (M["k"], 0.40), (e("n6") - 0.3, 0.72), (s("n7") + 0.3, 1.0)]


def interp(keys, t):
    ts, vs = zip(*keys)
    return float(np.interp(t, ts, vs))


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def phase_frames(ph_list, ph):
    """Два сусідні відрендерені кадри й вага другого для довільної фази."""
    ph = ph % 1.0
    n = len(ph_list)
    j = int(np.searchsorted(ph_list, ph, side="right")) - 1
    a, b = ph_list[j], ph_list[(j + 1) % n] + (1.0 if j == n - 1 else 0.0)
    return j, (j + 1) % n, float((ph - a) / (b - a))


def layer_spec(name, f):
    """Які файли кадрів потрібні шару на кадрі f: [(шлях відносно теки рендеру, вага)]."""
    t = f / FPS
    if name == "beat" or name == "cor":
        return [(f"{name}/{f % 20:03d}.png", 1.0)]
    if name == "cond":
        i, j, w = phase_frames(COND_PH, interp(COND_KEYS, t))
        return [(f"cond/{i:03d}.png", 1 - w), (f"cond/{j:03d}.png", w)]
    if name == "af":
        return [(f"af/{f % AF_N:03d}.png", 1.0)]
    if name == "vessel":
        return [(f"vessel/{f % VES_N:03d}.png", 1.0)]
    if name == "cells":
        i, j, w = phase_frames(CELL_PH, interp(CELL_KEYS, t))
        return [(f"cells/{i:03d}.png", 1 - w), (f"cells/{j:03d}.png", w)]
    return []


def shot_at(t):
    cur = "beat"
    for t0, name, dur in KEYS:
        if t >= t0 + dur * 0.5:
            cur = name
    return cur


if __name__ == "__main__":
    import sys
    src = json.load(open(os.path.join(LECTURE, "lecture.json")))["sources"]
    fr = [f / FPS for f in range(NFRAMES)]
    data = {
        "fps": FPS, "n": NFRAMES, "sceneEnd": SCENE_END, "total": TOTAL, "cycle": CYCLE,
        "s": {k: v["start"] for k, v in NAR.items()}, "e": {k: v["end"] for k, v in NAR.items()}, "m": M,
        "shot": [shot_at(t) for t in fr],
        "condPhase": [round(interp(COND_KEYS, t), 4) for t in fr],
        "cellPhase": [round(interp(CELL_KEYS, t), 4) for t in fr],
        "afBeats": AF_BEATS, "afPeriod": AF_PERIOD, "keys": [[a, b, c] for a, b, c in KEYS],
        "proj": json.load(open(sys.argv[1])), "sources": src,
    }
    json.dump(data, open(sys.argv[2], "w"), ensure_ascii=False)
