"""Спільний хронометраж: час реплік береться з плану рушія (lectures/bronchi/out/timing.json)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LECTURE = os.path.join(HERE, "..", "..", "lectures", "bronchi")
FPS = 25
W, H = 1920, 1080
OVERSCAN = 1.1          # кадри рендеряться з запасом для повільного наближення
SW, SH = 2112, 1188

_t = json.load(open(os.path.join(LECTURE, "out", "timing.json")))
SCENE = _t["scenes"][0]
NAR = {n["id"]: n for n in SCENE["narration"]}
SCENE_END = SCENE["duration"]
TOTAL = _t["duration"]
NFRAMES = round(TOTAL * FPS)


def s(i):
    return NAR[i]["start"]


def e(i):
    return NAR[i]["end"]


def m(k):
    for n in NAR.values():
        if k in n["markers"]:
            return n["markers"][k]
    raise KeyError(k)


# Камери. dir — напрям від цілі до камери; plane — нормаль трахеобронхіальної площини.
PLANE_N = [0.0, -0.9781, -0.2079]
CAMS = {
    "wide": {"target": [0, 0, -32], "dir": [0, -1, 0.04], "dist": 1500, "lens": 85, "shift_x": -0.2},
    "close": {"target": [6, 0, -16], "dir": PLANE_N, "dist": 560, "lens": 85, "shift_x": -0.2},
    "hook": {"target": [0, 0, 0], "dir": [0.25, -1, 0.12], "dist": 150, "lens": 100, "shift_x": -0.3,
             "fstop": 5.6},
}

G0 = {"focus_trachea": 0, "focus_br_r": 0, "focus_br_l": 0, "focus_lob_r": 0, "focus_lob_l": 0, "lungs": False}
STILLS = {
    "wide_open": ("wide", {}),
    "wide_ghost": ("wide", {"ghost": 1, "focus_lob_r": 0, "focus_lob_l": 0}),
    "g_r": ("close", {**G0, "focus_br_r": 1}),
    "g_l": ("close", {**G0, "focus_br_l": 1}),
    "g_rl": ("close", {**G0, "focus_br_r": 1, "focus_br_l": 1}),
    "g_tr_r": ("close", {**G0, "focus_br_r": 1, "focus_trachea": 1}),
    "cut": ("close", {**G0, "focus_br_r": 1, "focus_trachea": 1, "cut": 1}),
    "g_none": ("close", dict(G0)),
}
CUT_STATE = STILLS["cut"][1]

# Послідовність картинок: (час початку переходу, назва, тривалість переходу)
PEA_T0, PEA_DUR = s("n7") + 0.5, 3.8
KEYS = [
    (0.0, "hook", 0.0),
    (s("n2") - 0.5, "wide_open", 1.0),
    (s("n3"), "wide_ghost", 1.0),
    (s("n4") - 0.5, "g_r", 0.9),
    (s("n5"), "g_l", 0.7),
    (s("n6"), "g_rl", 0.7),
    (e("n6") + 0.15, "g_tr_r", 0.4),
    (s("n7") - 0.05, "cut", 0.5),
    (e("n7") + 0.3, "g_none", 0.7),
    (s("n9"), "g_r", 0.6),
    (SCENE_END - 0.3, "black", 0.9),
]
CAM_OF = {"wide_open": "wide", "wide_ghost": "wide", "hook": "hook", "black": None}

# Повільне наближення (масштаб довкола центру кадру)
ZOOMS = {"wide": (s("n2") - 0.5, s("n4") + 0.4, 1.0, 1.07), "close": (s("n4") - 0.5, SCENE_END + 0.6, 1.0, 1.085)}


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def zoom(cam, t):
    if cam not in ZOOMS:
        return 1.0
    a, b, z0, z1 = ZOOMS[cam]
    x = min(max((t - a) / (b - a), 0.0), 1.0)
    return z0 + (z1 - z0) * x


def _ease(x):
    # плавний розгін і м'яка зупинка
    return x * x * (3 - 2 * x) * 0.6 + x * 0.4 if x < 1 else 1.0


PEA_VISIBLE = (PEA_T0 - 0.2, e("n7") + 0.3)
HOOK_FRAMES = round((s("n2") + 0.6) * FPS)


def cam_at(t):
    """Камера кадру, що зараз на екрані (для прив'язки підписів)."""
    cur = "hook"
    for t0, name, dur in KEYS:
        if t >= t0 + dur * 0.5:
            cur = name
    return CAM_OF.get(cur, "close")


if __name__ == "__main__":
    import sys
    src = json.load(open(os.path.join(LECTURE, "lecture.json")))["sources"]
    data = {
        "fps": FPS, "n": NFRAMES, "sceneEnd": SCENE_END, "total": TOTAL,
        "s": {k: v["start"] for k, v in NAR.items()}, "e": {k: v["end"] for k, v in NAR.items()},
        "m": {k: v for n in NAR.values() for k, v in n["markers"].items()},
        "cam": [cam_at(f / FPS) for f in range(NFRAMES)],
        "zoom": [round(zoom(cam_at(f / FPS), f / FPS), 5) for f in range(NFRAMES)],
        "proj": json.load(open(sys.argv[1])), "sources": src,
    }
    json.dump(data, open(sys.argv[2], "w"), ensure_ascii=False)
