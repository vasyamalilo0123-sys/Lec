"""Процедурна геометрія серця: шлуночки, передсердя з вушками, магістральні судини,
вінцеві артерії на поверхні, провідна система всередині. Усе — неявні поверхні → marching cubes.

Координати (мм): x — ліворуч пацієнта, y — дозаду, z — догори.
Запуск: python3 heart_geometry.py <тека виводу>
"""
import json
import os
import sys

import numpy as np
from scipy import ndimage
from skimage import measure

OUT = sys.argv[1] if len(sys.argv) > 1 else "out/geo"
os.makedirs(OUT, exist_ok=True)
VOX = 0.6
LO = np.array([-72.0, -56.0, -66.0])
HI = np.array([82.0, 66.0, 150.0])
DIMS = np.ceil((HI - LO) / VOX).astype(int) + 1
AX = [LO[d] + VOX * np.arange(DIMS[d]) for d in range(3)]


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b + (a - b) * h - k * h * (1 - h)


def resample(pts, n=24):
    """Гладка ламана через опорні точки (Catmull–Rom)."""
    p = np.asarray(pts, float)
    if len(p) < 3:
        t = np.linspace(0, 1, n)[:, None]
        return p[0] * (1 - t) + p[-1] * t
    q = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    out = []
    per = max(2, n // (len(p) - 1))
    for i in range(len(p) - 1):
        p0, p1, p2, p3 = q[i], q[i + 1], q[i + 2], q[i + 3]
        for t in np.linspace(0, 1, per, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(p[-1])
    return np.array(out)


def tube_eval(P, pts, radii):
    """Відстань до «заокругленого конуса» вздовж ламаної; повертає (поле, параметр 0..1)."""
    pts = np.asarray(pts, float)
    radii = np.broadcast_to(np.asarray(radii, float), (len(pts),)) if np.ndim(radii) else np.full(len(pts), radii)
    seg = np.diff(pts, axis=0)
    L = np.linalg.norm(seg, axis=1)
    s0 = np.concatenate([[0], np.cumsum(L)])
    best = np.full(len(P), 1e9, np.float32)
    sb = np.zeros(len(P), np.float32)
    for k in range(len(seg)):
        t = seg[k] / L[k]
        v = P - pts[k]
        u = np.clip(v @ t, 0, L[k])
        w = v - u[:, None] * t
        d = np.sqrt(np.einsum("ij,ij->i", w, w)) - (radii[k] + (radii[k + 1] - radii[k]) * u / L[k])
        m = d < best
        best[m] = d[m]
        sb[m] = (s0[k] + u[m]) / s0[-1]
    return best, sb


def paint(grid, pts, radii, k=0.0, margin=8.0, cut_end=False, cut_start=False):
    """Додає трубку до сітки поля (у межах її габаритів)."""
    pts = np.asarray(pts, float)
    rmax = float(np.max(radii)) + margin
    i0 = np.maximum(np.floor((pts.min(0) - rmax - LO) / VOX).astype(int), 0)
    i1 = np.minimum(np.ceil((pts.max(0) + rmax - LO) / VOX).astype(int) + 1, DIMS)
    sl = tuple(slice(a, b) for a, b in zip(i0, i1))
    g = np.stack(np.meshgrid(*[AX[d][i0[d]:i1[d]] for d in range(3)], indexing="ij"), -1)
    Pn = g.reshape(-1, 3)
    f, _ = tube_eval(Pn, pts, radii)
    if cut_end:
        f = np.maximum(f, (Pn - pts[-1]) @ unit(pts[-1] - pts[-2]))
    if cut_start:
        f = np.maximum(f, (Pn - pts[0]) @ unit(pts[0] - pts[1]))
    f = f.reshape(g.shape[:3])
    grid[sl] = smin(grid[sl], f, k) if k > 0 else np.minimum(grid[sl], f)


def ellipsoid(grid, c, r, k=0.0):
    c, r = np.asarray(c, float), np.asarray(r, float)
    i0 = np.maximum(np.floor((c - r - 10 - LO) / VOX).astype(int), 0)
    i1 = np.minimum(np.ceil((c + r + 10 - LO) / VOX).astype(int) + 1, DIMS)
    sl = tuple(slice(a, b) for a, b in zip(i0, i1))
    x, y, z = np.meshgrid(*[AX[d][i0[d]:i1[d]] for d in range(3)], indexing="ij")
    q = np.sqrt(((x - c[0]) / r[0]) ** 2 + ((y - c[1]) / r[1]) ** 2 + ((z - c[2]) / r[2]) ** 2)
    f = ((q - 1) * r.min()).astype(np.float32)
    grid[sl] = smin(grid[sl], f, k) if k > 0 else np.minimum(grid[sl], f)


def new():
    return np.full(DIMS, 40.0, np.float32)


def sample(grid, P, order=1):
    idx = ((np.asarray(P) - LO) / VOX).T
    return ndimage.map_coordinates(grid, idx, order=order, mode="nearest")


# ------------------------------------------------------------------ анатомія
LV_B, APEX = np.array([4.0, 16.0, 30.0]), np.array([50.0, -26.0, -38.0])
RV_B, RV_E = np.array([-25.0, -8.0, 30.0]), np.array([36.0, -32.0, -33.0])
LV_AX = unit(APEX - LV_B)
LV_LEN = np.linalg.norm(APEX - LV_B)
LV_S = np.array([0, 0.25, 0.5, 0.75, 1.0])
LV_R = np.array([33.0, 35.0, 32.0, 24.0, 12.0])
RV_R = np.array([29.0, 31.0, 28.0, 20.0, 9.0])
lv_pts = LV_B + (APEX - LV_B) * LV_S[:, None]
rv_pts = RV_B + (RV_E - RV_B) * LV_S[:, None]
RA_C, LA_C = np.array([-39.0, 6.0, 49.0]), np.array([10.0, 36.0, 50.0])

AORTA = resample([(-5, -3, 40), (-13, -10, 72), (-9, -9, 98), (6, 3, 113), (21, 20, 106), (27, 33, 82), (27, 37, 44)], 40)
ARCH = [[(-8, -8, 104), (-16, -8, 124), (-20, -6, 146)],      # плечоголовний стовбур
        [(6, 3, 112), (6, 2, 130), (5, 2, 146)],              # ліва загальна сонна
        [(18, 16, 108), (22, 18, 126), (25, 19, 146)]]        # ліва підключична
PULM = resample([(4, -22, 36), (10, -24, 54), (15, -14, 76), (17, -2, 84)], 20)
PA_L = resample([(17, -2, 84), (34, 12, 86), (56, 22, 82)], 12)
PA_R = resample([(17, -2, 84), (-4, 12, 82), (-34, 16, 78), (-56, 18, 76)], 16)
SVC = resample([(-38, 8, 62), (-37, 6, 100), (-35, 5, 146)], 12)
IVC = resample([(-36, 16, 30), (-35, 18, 8), (-34, 20, -12)], 8)
PV = [[(30, 40, 56), (52, 40, 60), (66, 38, 62)], [(30, 42, 42), (52, 44, 40), (66, 44, 38)],
      [(-12, 42, 56), (-34, 40, 60), (-52, 36, 62)], [(-12, 44, 42), (-34, 44, 40), (-52, 40, 38)]]

GROUPS = ["vent", "atria", "aorta", "pulm", "veins"]


def build_fields():
    G = {g: new() for g in GROUPS}
    paint(G["vent"], lv_pts, LV_R, margin=12)
    paint(G["vent"], rv_pts, RV_R, k=8.0, margin=12)
    paint(G["vent"], [(-6, -20, 22), (4, -23, 40)], [17, 15], k=7.0)       # артеріальний конус
    ellipsoid(G["atria"], RA_C, (23, 25, 29))
    ellipsoid(G["atria"], (-22, -22, 50), (14, 10, 12), k=5.0)              # праве вушко
    ellipsoid(G["atria"], (-30, -24, 44), (9, 7, 8), k=4.0)
    ellipsoid(G["atria"], LA_C, (31, 19, 22), k=4.0)
    ellipsoid(G["atria"], (36, -2, 54), (13, 10, 10), k=5.0)                # ліве вушко
    ellipsoid(G["atria"], (40, -12, 48), (8, 7, 8), k=4.0)
    paint(G["aorta"], AORTA, np.linspace(14.5, 11.5, len(AORTA)), cut_end=True)
    for a in ARCH:
        paint(G["aorta"], resample(a, 8), 5.6, k=3.0, cut_end=True)
    paint(G["pulm"], PULM, 13.5)
    paint(G["pulm"], PA_L, np.linspace(10.5, 9, len(PA_L)), k=4.0, cut_end=True)
    paint(G["pulm"], PA_R, np.linspace(10.5, 9, len(PA_R)), k=4.0, cut_end=True)
    paint(G["veins"], SVC, 10.5, cut_end=True)
    paint(G["veins"], IVC, 11.5, cut_end=True)
    for a in PV:
        paint(G["veins"], resample(a, 6), 6.0, k=3.0, cut_end=True)
    F = smin(G["vent"], G["atria"], 4.0)
    for g in ("aorta", "pulm", "veins"):
        F = smin(F, G[g], 4.5)
    # просвіти судин на відкритих зрізах
    lum = new()
    paint(lum, AORTA[16:], np.linspace(12, 9.6, len(AORTA))[16:])
    for a in ARCH:
        paint(lum, resample(a, 8), 4.2, k=2.0)
    paint(lum, PA_L[3:], 8.0)
    paint(lum, PA_R[4:], 8.0)
    paint(lum, SVC[4:], 8.6)
    paint(lum, IVC[3:], 9.4)
    for a in PV:
        paint(lum, resample(a, 6)[2:], 4.6)
    return G, F, lum


def weights(G, P, tau=3.0):
    f = np.stack([sample(G[g], P) for g in GROUPS], 1)
    w = np.exp(-(f - f.min(1, keepdims=True)) / tau)
    return w / w.sum(1, keepdims=True)


def project(F, pts, lift=0.9, iters=30):
    """Покласти точки на поверхню серця (вінцеві артерії йдуть під епікардом)."""
    P = np.array(pts, float)
    e = 0.8
    for _ in range(iters):
        f = sample(F, P)
        g = np.stack([sample(F, P + d) - sample(F, P - d) for d in np.eye(3) * e], 1) / (2 * e)
        g /= np.linalg.norm(g, axis=1, keepdims=True) + 1e-9
        P -= g * (f - lift)[:, None] * 0.7
    return P


CORONARY = {
    "rca": ([(-17, -19, 47), (-33, -24, 39), (-46, -17, 27), (-53, -3, 13), (-50, 12, 0)], 2.3, 1.5),
    "rmarg": ([(-46, -17, 27), (-30, -31, 2), (-2, -37, -22), (22, -37, -32)], 1.5, 0.8),
    "lm": ([(7, -8, 50), (16, -4, 52), (25, -15, 48)], 2.5, 2.3),
    "lad": ([(25, -15, 48), (30, -28, 31), (36, -36, 10), (42, -38, -12), (46, -36, -28), (50, -29, -38)], 2.2, 1.0),
    "diag": ([(32, -31, 22), (48, -25, 2), (59, -15, -17)], 1.4, 0.7),
    "diag2": ([(38, -37, 2), (50, -32, -16), (58, -24, -30)], 1.1, 0.6),
    "lcx": ([(25, -15, 48), (38, -6, 45), (47, 8, 37), (47, 22, 27)], 2.0, 1.4),
    "om": ([(43, 1, 41), (58, 2, 12), (62, -4, -12)], 1.4, 0.7),
    "conus": ([(-24, -22, 43), (-12, -30, 30), (2, -36, 14)], 1.0, 0.6),
}


def deform(G, P):
    """Зміщення вершин для систоли шлуночків і систоли передсердь (ключі форми)."""
    P = np.asarray(P, float)
    w = weights(G, P, 5.0)
    wv, wa = w[:, 0], w[:, 1]
    rel = P - LV_B
    s_raw = (rel @ LV_AX) / LV_LEN
    s = np.clip(s_raw, 0, 1)
    c = LV_B + np.outer(s * LV_LEN, LV_AX)
    rho = P - c
    rho -= np.outer(rho @ LV_AX, LV_AX)
    above = np.clip(-s_raw * LV_LEN, 0, None)
    follow = wv + (1 - wv) * np.exp(-above / 30.0)
    dv = -0.15 * rho * (wv * (0.55 + 0.45 * np.sin(np.pi * np.clip(s, 0, 1) ** 0.8)))[:, None]
    dv += np.outer(7.0 * (1 - s) * follow, LV_AX)
    tw = np.radians(7.0) * s * wv
    dv += np.cross(LV_AX, rho) * tw[:, None]
    cen = np.where((P[:, 0] < -8)[:, None], RA_C, LA_C)
    da = -0.085 * (P - cen) * wa[:, None]
    return dv.astype(np.float32), da.astype(np.float32)


def act_times(G, P, w):
    """Час збудження (частка серцевого циклу); -1 — тканина, що не збуджується (судини)."""
    sa = np.array(SA_NODE)
    d = np.linalg.norm(P - sa, axis=1)
    ta = 0.015 + 0.085 * np.clip(d / 95.0, 0, 1)
    s = np.clip(((P - LV_B) @ LV_AX) / LV_LEN, 0, 1)
    tv = 0.255 + 0.05 * (1 - s)
    t = np.where(w[:, 0] > w[:, 1], tv, ta)
    t = np.where(w[:, 0] + w[:, 1] > 0.5, t, -1.0)
    return t.astype(np.float32)


SA_NODE = (-44.0, -8.0, 66.0)
AV_NODE = (-9.0, 8.0, 33.0)


def septum(s):
    L = LV_B + (APEX - LV_B) * s
    R = RV_B + (RV_E - RV_B) * s
    rl, rr = np.interp(s, LV_S, LV_R), np.interp(s, LV_S, RV_R)
    return L + (R - L) * rl / (rl + rr)


def wall(base, end, radii, s, th, frac, ref):
    """Точка на внутрішній стінці шлуночка: вздовж осі s, кут th довкола осі."""
    ax = unit(end - base)
    c = base + (end - base) * s
    e1 = unit(ref - (ref @ ax) * ax)
    e2 = np.cross(ax, e1)
    return c + (np.cos(th) * e1 + np.sin(th) * e2) * np.interp(s, LV_S, radii) * frac


def conduction():
    """Провідна система: гілки з радіусом і часом проходження імпульсу (частка циклу)."""
    rng = np.random.default_rng(3)
    br = []
    his_end = septum(0.14)
    br.append(("av", [AV_NODE, np.array(AV_NODE) + (np.array(his_end) - AV_NODE) * 0.25], 3.0, 2.2, 0.10, 0.19))
    br.append(("his", resample([np.array(AV_NODE) + (his_end - np.array(AV_NODE)) * 0.25, his_end], 6), 1.8, 1.7, 0.19, 0.205))
    toL = unit(LV_B - RV_B)
    for side, name, (base, end, radii, frac, ths) in (
            (+1, "lbb", (LV_B, APEX, LV_R, 0.66, np.radians([20, 70, 120, 170, 220, 275, 330]))),
            (-1, "rbb", (RV_B, RV_E, RV_R, 0.70, np.radians([150, 195, 240, 290])))):
        trunk = resample([septum(s) + toL * side * 2.6 for s in (0.14, 0.3, 0.5, 0.7, 0.86)], 20)
        br.append((name, trunk, 1.5, 1.1, 0.205, 0.235))
        ref = -toL * side if side > 0 else np.array([0.0, -1.0, 0.2])
        ref = np.array([0.0, 0.0, 1.0]) if side > 0 else ref
        for th in ths:
            th = th + rng.uniform(-0.15, 0.15)
            top = rng.uniform(0.3, 0.45)
            ss = np.linspace(0.88, top, 7)
            path = [trunk[-1]] + [wall(base, end, radii, s, th + 0.25 * np.sin(6 * s + th), frac, ref) for s in ss]
            path = resample(path, 18)
            br.append(("purk", path, 0.95, 0.6, 0.235, 0.27))
            for k in (7, 12):
                q = path[k]
                dirn = unit(np.cross(unit(end - base), q - (base + (end - base) * 0.5))) * rng.choice([-1, 1])
                tip = q + dirn * rng.uniform(7, 11) - unit(end - base) * rng.uniform(2, 6)
                tk = 0.235 + 0.035 * k / 18
                br.append(("purk", resample([q, (q + tip) / 2 + rng.normal(size=3), tip], 6), 0.6, 0.45, tk, tk + 0.012))
    return br


def save(name, V, F, **attrs):
    np.savez(os.path.join(OUT, name + ".npz"), v=V.astype(np.float32), f=F.astype(np.int32),
             **{k: np.asarray(a, np.float32) for k, a in attrs.items()})
    print(f"{name}: {len(V) / 1e3:.0f} тис. вершин", flush=True)


def mesh(field, lo=LO, vox=VOX):
    v, f, _, _ = measure.marching_cubes(field, 0.0, spacing=(vox,) * 3)
    return v + lo, f


def fine_tubes(tubes, vox, pad=4.0):
    """Сітка з тонких трубок у власній дрібній ґратці; повертає вершини, грані, індекс найближчої трубки, параметр."""
    allp = np.vstack([t[0] for t in tubes])
    lo = allp.min(0) - pad
    dims = np.ceil((allp.max(0) + pad - lo) / vox).astype(int) + 1
    grid = np.full(dims, 20.0, np.float32)
    ax = [lo[d] + vox * np.arange(dims[d]) for d in range(3)]
    for pts, r0, r1 in tubes:
        pts = np.asarray(pts, float)
        rad = np.linspace(r0, r1, len(pts))
        i0 = np.maximum(np.floor((pts.min(0) - r0 - 3 - lo) / vox).astype(int), 0)
        i1 = np.minimum(np.ceil((pts.max(0) + r0 + 3 - lo) / vox).astype(int) + 1, dims)
        sl = tuple(slice(a, b) for a, b in zip(i0, i1))
        g = np.stack(np.meshgrid(*[ax[d][i0[d]:i1[d]] for d in range(3)], indexing="ij"), -1)
        f, _ = tube_eval(g.reshape(-1, 3), pts, rad)
        grid[sl] = smin(grid[sl], f.reshape(g.shape[:3]), 0.5)
    v, f = mesh(grid, lo, vox)
    best = np.full(len(v), 1e9)
    idx = np.zeros(len(v), int)
    par = np.zeros(len(v), np.float32)
    for i, (pts, r0, r1) in enumerate(tubes):
        d, s = tube_eval(v, np.asarray(pts, float), np.linspace(r0, r1, len(pts)))
        m = d < best
        best[m], idx[m], par[m] = d[m], i, s[m]
    return v, f, idx, par


if __name__ == "__main__":
    G, F, lum = build_fields()
    # вінцеві артерії лягають на поверхню; під ними — борозни з жировою клітковиною
    cor = {k: (project(F, resample(p, 30)), r0, r1) for k, (p, r0, r1) in CORONARY.items()}
    groove = new()
    for k, (p, r0, r1) in cor.items():
        paint(groove, p, r0 + 3.5, margin=10)
    # неглибока борозна вздовж артерій
    F = np.maximum(F, 1.3 * smoothstep(5.5, 1.0, groove + 3.5) - 1.3 + F) if False else F + 1.2 * smoothstep(5.5, 0.5, groove + 3.5)
    shell = np.maximum(F, -lum)
    shell = ndimage.gaussian_filter(shell, 0.6)
    V, Fc = mesh(shell)
    w = weights(G, V)
    dv, da = deform(G, V)
    fat = smoothstep(4.2, 0.8, sample(groove, V) + 3.5)
    inner = smoothstep(-0.8, -2.0, sample(F, V))
    save("heart", V, Fc, w=w, dv=dv, da=da, act=act_times(G, V, w), fat=fat, inner=inner)

    tubes = [(p, r0, r1) for p, r0, r1 in cor.values()]
    v, f, idx, par = fine_tubes(tubes, 0.3)
    dv, da = deform(G, v)
    save("coronary", v, f, dv=dv, da=da)

    br = conduction()
    tubes = [(np.asarray(p, float), r0, r1) for _, p, r0, r1, _, _ in br]
    # синусовий вузол — веретено під епікардом біля устя верхньої порожнистої вени
    sa = project(F, [SA_NODE, np.array(SA_NODE) + [2, 4, -9]], lift=-2.0)
    tubes.append((resample(list(sa), 6), 3.2, 2.2))
    v, f, idx, par = fine_tubes(tubes, 0.28)
    t0 = np.array([b[4] for b in br] + [0.0])
    t1 = np.array([b[5] for b in br] + [0.02])
    kind = np.array([{"av": 1, "his": 2, "lbb": 3, "rbb": 3, "purk": 4}[b[0]] for b in br] + [0])
    dv, da = deform(G, v)
    save("conduction", v, f, act=t0[idx] + (t1[idx] - t0[idx]) * par, kind=kind[idx], dv=dv, da=da)

    lm = {"sa": sa[0].tolist(), "av": list(AV_NODE), "his": septum(0.2).tolist(), "purk": wall(LV_B, APEX, LV_R, 0.6, 2.0, 0.66, np.array([0, 0, 1.0])).tolist(),
          "apex": APEX.tolist(), "lad": cor["lad"][0][12].tolist(), "rca": cor["rca"][0][10].tolist(),
          "ra": [-50, -14, 48], "la": [38, -6, 56], "lv": [40, -30, -10], "rv": [-8, -34, 4],
          "aorta": [-10, -22, 96], "pulm": [14, -30, 62], "center": [2, 0, 36]}
    json.dump(lm, open(os.path.join(OUT, "landmarks.json"), "w"), indent=1)
