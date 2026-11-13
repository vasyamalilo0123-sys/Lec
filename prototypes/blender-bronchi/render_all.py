"""Рендер усіх шарів: нерухомі стани, горошина в розтині (лише ділянка довкола неї), гачок.

python3 render_all.py <geo> <out> [proj|stills|pea|hook ...]   — уже готові файли пропускаються.
"""
import json
import math
import os
import sys

import numpy as np

import scene
import timeline as TL

geo, out = sys.argv[1], sys.argv[2]
what = sys.argv[3:] or ["proj", "stills", "pea", "hook"]
os.makedirs(out, exist_ok=True)
S = scene.build(geo)
lm = S.lm
RES = (TL.SW, TL.SH)


def path_point(u, back=1.5):
    pts = np.array(lm["pea_path"])
    d = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    x = u * d[-1]
    p = np.array([np.interp(x, d, pts[:, i]) for i in range(3)])
    return (p - np.array(TL.PLANE_N) * back).tolist()  # трохи вглиб від площини розтину


if "proj" in what:
    A, dR, dL = np.array(lm["axis"]), np.array(lm["dR"]), np.array(lm["dL"])
    pts = {k: lm[k] for k in ("top", "trachea_mid", "carina", "origin", "rmb_mid", "lmb_mid", "rmb_end", "lmb_end", "lung_r", "lung_l")}
    pts.update({"ax_up": (-A * 46).tolist(), "ax_dn": (A * 62).tolist(), "r_dn": (dR * 58).tolist(), "l_dn": (dL * 58).tolist(),
                "arc_r": [((A * math.cos(a) - np.array([1, 0, 0]) * math.sin(a)) * 44).tolist() for a in np.radians(np.linspace(0, 25, 12))],
                "arc_l": [((A * math.cos(a) + np.array([1, 0, 0]) * math.sin(a)) * 34).tolist() for a in np.radians(np.linspace(0, 45, 16))],
                "num_r": ((A * math.cos(math.radians(11)) - np.array([1, 0, 0]) * math.sin(math.radians(11))) * 54).tolist(),
                "num_l": ((A * math.cos(math.radians(24)) + np.array([1, 0, 0]) * math.sin(math.radians(24))) * 45).tolist()})
    proj = {}
    S.sc.render.resolution_x, S.sc.render.resolution_y = RES
    for cn in ("wide", "close"):
        S.set_camera(TL.CAMS[cn])
        proj[cn] = {k: ([S.project(q) for q in v] if isinstance(v[0], list) else S.project(v)) for k, v in pts.items()}
    json.dump(proj, open(os.path.join(out, "proj.json"), "w"), indent=1)
    print("proj.json", flush=True)

if "stills" in what:
    for name, (cn, st) in TL.STILLS.items():
        p = os.path.join(out, f"still_{name}.png")
        if os.path.exists(p):
            continue
        S.set_camera(TL.CAMS[cn])
        S.set_state(st)
        S.render(p, RES, samples=160, threshold=0.015)
        print("still", name, flush=True)

if "pea" in what:
    os.makedirs(os.path.join(out, "pea"), exist_ok=True)
    S.set_camera(TL.CAMS["close"])
    r = S.sc.render
    r.resolution_x, r.resolution_y = RES
    boxes = {}
    f0, f1 = int(TL.PEA_VISIBLE[0] * TL.FPS), int(TL.PEA_VISIBLE[1] * TL.FPS) + 1
    last = None
    for f in range(f0, f1 + 1):
        t = f / TL.FPS
        u = TL._ease(min(max((t - TL.PEA_T0) / TL.PEA_DUR, 0.0), 1.0))
        pos = path_point(u)
        key = round(u, 5)
        cx, cy = S.project(pos)
        half = 120
        x0, x1 = int(cx * RES[0]) - half, int(cx * RES[0]) + half
        y0, y1 = int(cy * RES[1]) - half, int(cy * RES[1]) + half
        x0, x1 = max(x0, 0), min(x1, RES[0])
        y0, y1 = max(y0, 0), min(y1, RES[1])
        if x1 - x0 < 24 or y1 - y0 < 24:
            continue  # горошина ще за межами кадру
        boxes[f] = {"box": [x0, y0, x1, y1], "src": last[1] if last and last[0] == key else f}
        if last and last[0] == key:
            continue
        last = (key, f)
        p = os.path.join(out, "pea", f"{f:05d}.png")
        if os.path.exists(p):
            continue
        S.set_state({**TL.CUT_STATE, "pea": pos, "pea_rot": (u * 9.0, u * 3.0, 0.4)})
        r.use_border, r.use_crop_to_border = True, True
        r.border_min_x, r.border_max_x = x0 / RES[0], x1 / RES[0]
        r.border_min_y, r.border_max_y = 1 - y1 / RES[1], 1 - y0 / RES[1]
        S.render(p, RES, samples=96, threshold=0.02)
    r.use_border = r.use_crop_to_border = False
    json.dump(boxes, open(os.path.join(out, "pea", "boxes.json"), "w"))
    print("pea", flush=True)

if "hook" in what:
    os.makedirs(os.path.join(out, "hook"), exist_ok=True)
    for f in range(TL.HOOK_FRAMES):
        p = os.path.join(out, "hook", f"{f:05d}.png")
        if os.path.exists(p):
            continue
        t = f / TL.FPS
        cam = dict(TL.CAMS["hook"])
        cam["dist"] = 165 - 3.2 * t
        cam["focus"] = cam["dist"] - 2.5
        S.set_camera(cam)
        S.set_state({"airway": False, "lungs": False, "pea": [0, 0, 0.0], "pea_rot": (0.35 * t, 0.2, 0.22 * t)})
        S.render(p, (TL.W, TL.H), samples=64, threshold=0.03)
    print("hook", flush=True)
