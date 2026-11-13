"""Рендер циклів серця. python3 hrender.py <geo> <out> [beat cond af cor]  — готові кадри пропускаються."""
import os
import sys

import numpy as np

import hscene

geo, out = sys.argv[1], sys.argv[2]
what = sys.argv[3:] or ["beat", "cond", "af", "cor"]
S = hscene.HeartScene(geo)
S.set_camera(hscene.CAM)

# фази нормального циклу для «прозорого» серця: густіше там, де біжить імпульс
COND_PH = np.concatenate([np.linspace(0, 0.36, 20, endpoint=False), np.linspace(0.36, 1.0, 10, endpoint=False)])
AF_N, AF_BEATS, AF_PERIOD = 32, (0.0, 0.52), 1.28


def af_phase(t):
    """Фаза шлуночків при фібриляції: відлік від останнього (нерегулярного) скорочення."""
    last = max([b for b in AF_BEATS if b <= t] + [AF_BEATS[-1] - AF_PERIOD])
    return 0.2 + (t - last) / 0.8


def run(name, n, state, samples, thr):
    os.makedirs(os.path.join(out, name), exist_ok=True)
    for i in range(n):
        p = os.path.join(out, name, f"{i:03d}.png")
        if os.path.exists(p):
            continue
        S.set_state(state(i))
        S.render(p, (1440, 810), samples, thr, border=hscene.BORDER)
    print(name, flush=True)


if __name__ == "__main__":
    if "beat" in what:
        run("beat", 20, lambda i: {"phase_a": i / 20, "phase_v": i / 20}, 48, 0.05)
    if "cond" in what:
        run("cond", len(COND_PH), lambda i: {"ghost": 1, "phase_a": float(COND_PH[i]), "phase_v": float(COND_PH[i])}, 40, 0.06)
    if "af" in what:
        run("af", AF_N, lambda i: {"ghost": 1, "af": 1, "afw": i * 0.22, "phase_a": -1.0, "beat_a": 0.12,
                                   "phase_v": af_phase(i / 25)}, 40, 0.06)
    if "cor" in what:
        run("cor", 20, lambda i: {"phase_a": i / 20, "phase_v": i / 20, "focus": 0.0}, 40, 0.06)
