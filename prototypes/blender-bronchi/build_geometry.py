"""Процедурна геометрія: трахея, бронхіальне дерево (до субсегментарних бронхів) і легені.

Усе будується з нуля як неявні поверхні (поля відстаней) і перетворюється на сітки
алгоритмом marching cubes. Жодних готових 3D-моделей.

Система координат (мм): x — ліворуч пацієнта, y — дозаду, z — догори.
Початок координат — точка сходження осей трахеї й головних бронхів.

Запуск:  python3 build_geometry.py <тека виводу> [воксель_мм]
"""
import json
import os
import sys

import numpy as np
from scipy import ndimage
from skimage import measure

OUT = sys.argv[1] if len(sys.argv) > 1 else "out/geo"
VOX = float(sys.argv[2]) if len(sys.argv) > 2 else 0.35
os.makedirs(OUT, exist_ok=True)

P = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "anatomy.json")))


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# Вісь трахеї: донизу й трохи дозаду.
TILT = np.radians(P["trachea"]["tilt_back_deg"])
A = unit([0, np.sin(TILT), -np.cos(TILT)])
X = np.array([1.0, 0, 0])
PLANE_N = unit(np.cross(A, X))  # нормаль трахеобронхіальної площини (допереду)


def in_plane(deg, side):
    """Напрям у трахеобронхіальній площині під кутом deg від осі трахеї."""
    a = np.radians(deg)
    return unit(np.cos(a) * A + side * np.sin(a) * X)


class Branch:
    def __init__(self, name, group, pts, r0, r1, wall, kind, pitch=4.5, dshape=False, leaf=False, gen=0):
        self.name, self.group, self.kind = name, group, kind
        self.pts = np.asarray(pts, float)
        self.r0, self.r1, self.wall, self.pitch = r0, r1, wall, pitch
        self.dshape, self.leaf, self.gen = dshape, leaf, gen
        seg = np.diff(self.pts, axis=0)
        self.seglen = np.linalg.norm(seg, axis=1)
        self.segdir = seg / self.seglen[:, None]
        self.s0 = np.concatenate([[0], np.cumsum(self.seglen)])
        self.L = self.s0[-1]
        self.phase = (abs(hash(name)) % 1000) / 1000.0 * 6.28 if False else (sum(map(ord, name)) % 628) / 100.0

    @property
    def end(self):
        return self.pts[-1]

    @property
    def enddir(self):
        return self.segdir[-1]

    def at(self, s):
        s = np.clip(s, 0, self.L)
        i = min(np.searchsorted(self.s0, s, side="right") - 1, len(self.seglen) - 1)
        return self.pts[i] + self.segdir[i] * (s - self.s0[i])

    def bbox(self, margin):
        r = max(self.r0, self.r1) + margin
        return self.pts.min(0) - r, self.pts.max(0) + r

    def evaluate(self, Q):
        """Q: (n,3). Повертає зовнішнє поле, поле просвіту, частку хряща."""
        n = len(Q)
        best = np.full(n, 1e9, np.float32)
        s = np.zeros(n, np.float32)
        ap = np.zeros(n, np.float32)
        la = np.zeros(n, np.float32)
        ax = np.zeros(n, np.float32)
        Y = np.array([0, 1.0, 0])
        for k in range(len(self.seglen)):
            t = self.segdir[k]
            v = Q - self.pts[k]
            u = v @ t
            uc = np.clip(u, 0, self.seglen[k])
            w = v - uc[:, None] * t
            d2 = np.einsum("ij,ij->i", w, w)
            m = d2 < best
            if not m.any():
                continue
            post = unit(Y - (Y @ t) * t)
            lat = np.cross(t, post)
            best[m] = d2[m]
            s[m] = self.s0[k] + uc[m]
            ap[m] = w[m] @ post
            la[m] = w[m] @ lat
            ax[m] = (u - uc)[m]
        r = self.r0 + (self.r1 - self.r0) * (s / self.L)
        ang = np.arctan2(ap, la)
        if self.kind == "ring":
            sw = s + 0.45 * np.sin(2.0 * ang + 0.9 * s / self.pitch + self.phase)
            ring = smoothstep(-0.25, 0.45, np.cos(2 * np.pi * sw / self.pitch))
            bump = 0.42
        else:
            w1 = np.sin(2 * np.pi * s / self.pitch + self.phase)
            w2 = np.sin(2.0 * ang + 0.45 * s + 2 * self.phase)
            ring = smoothstep(-0.05, 0.35, w1 * w2 + 0.12)
            bump = 0.3 if self.gen < 3 else 0.18
        if self.dshape:
            e = 1.0
            h = 0.84 * r
            ant = smoothstep(h - 0.6, h - 2.6, ap)
        else:
            e = 1.0
            h = None
            ant = 1.0
        de = np.sqrt(la * la + (ap / e) ** 2 + ax * ax)
        cartzone = ring * ant
        fo = de - (r + bump * cartzone)
        rl = r - self.wall
        fl = de - (rl - 0.18 * cartzone)
        if self.dshape:
            fo = np.maximum(fo, ap - h)
            fl = np.maximum(fl, ap - (h - 0.8 * self.wall))
        if self.leaf:
            fo = np.maximum(fo, (Q - self.end) @ self.enddir + 0.2)
        band = smoothstep(rl + 0.3, rl + 0.6, de)
        cart = cartzone * band
        return fo.astype(np.float32), fl.astype(np.float32), cart.astype(np.float32), np.asarray(cartzone, np.float32)


def poly(p0, d0, L, d1=None, n=8):
    """Плавна вісь гілки: від p0 у напрямі d0, наприкінці — у напрямі d1."""
    d0 = unit(d0)
    d1 = d0 if d1 is None else unit(d1)
    pts = [np.asarray(p0, float)]
    for i in range(n):
        t = (i + 0.5) / n
        d = unit((1 - t) * d0 + t * d1)
        pts.append(pts[-1] + d * L / n)
    return np.array(pts)


branches = []
SEG = P["segmental"]
rng = np.random.default_rng(7)


def add(name, group, p0, d0, L, r0, r1, wall, kind="plate", d1=None, **kw):
    b = Branch(name, group, poly(p0, d0, L, d1), r0, r1, wall, kind, **kw)
    branches.append(b)
    return b


def perp(d):
    a = np.cross(d, [0, 0, 1.0])
    if np.linalg.norm(a) < 0.2:
        a = np.cross(d, [1.0, 0, 0])
    return unit(a)


def rot(v, axis, deg):
    a = np.radians(deg)
    axis = unit(axis)
    return v * np.cos(a) + np.cross(axis, v) * np.sin(a) + axis * (axis @ v) * (1 - np.cos(a))


def segmental(name, group, p0, d, L=None):
    """Сегментний бронх і два субсегментарні."""
    L = L or SEG["length"]
    d = unit(d)
    b = add(name, group, p0, d, L, SEG["r0"], SEG["r1"], SEG["wall"], pitch=5.0, gen=3,
            d1=unit(d + 0.25 * rng.normal(size=3)))
    ax0 = rot(perp(b.enddir), b.enddir, rng.uniform(0, 180))
    for j, sgn in enumerate((1, -1)):
        dd = rot(b.enddir, ax0, sgn * rng.uniform(22, 32))
        add(f"{name}{'ab'[j]}", group, b.end, dd, rng.uniform(15, 20), SEG["r1"] * 0.78, SEG["r1"] * 0.6,
            0.75, pitch=4.0, gen=4, leaf=True, d1=unit(dd + 0.3 * rng.normal(size=3)))
    return b


T = P["trachea"]
R, Lm = P["right_main"], P["left_main"]

# Трахея: згори до точки сходження осей, з ледь помітним вигином.
top = -A * T["length"]
tp = [top + A * T["length"] * t + X * 1.2 * np.sin(np.pi * t) for t in np.linspace(0, 1, 13)]
trachea = Branch("trachea", "trachea", tp, T["r"], T["r"] * 1.02, T["wall"], "ring",
                 pitch=T["length"] / T["rings"], dshape=True)
branches.append(trachea)

O = np.zeros(3)
dR = in_plane(R["angle_deg"], -1)
dL = in_plane(Lm["angle_deg"], +1)

# Права сторона
rmb = add("rmb", "br_r", O, dR, R["length"], R["r"], R["r"] * 0.96, R["wall"], "ring", pitch=4.6, dshape=True)
rul = add("rul", "lob_r", rmb.end - dR * 3, [-0.92, 0.05, 0.38], 14, 5.0, 4.8, 1.3, pitch=5.5, gen=2)
segmental("rb1", "lob_r", rul.end, [-0.35, 0.0, 0.94])
segmental("rb2", "lob_r", rul.end, [-0.6, 0.65, 0.45])
segmental("rb3", "lob_r", rul.end, [-0.6, -0.75, 0.05])
bi = add("bi", "lob_r", rmb.end, dR, P["intermedius"]["length"], 6.0, 5.6, 1.6, "ring", pitch=4.4, dshape=True,
         d1=[-0.33, 0.22, -0.92])
rml = add("rml", "lob_r", bi.end - bi.enddir * 3, [-0.5, -0.72, -0.48], 17, 3.9, 3.6, 1.1, pitch=5.0, gen=2)
segmental("rb4", "lob_r", rml.end, [-0.8, -0.45, -0.4])
segmental("rb5", "lob_r", rml.end, [-0.25, -0.8, -0.55])
rll = add("rll", "lob_r", bi.end, [-0.33, 0.3, -0.89], 16, 5.3, 4.7, 1.4, pitch=5.5, gen=2)
segmental("rb6", "lob_r", bi.end + rll.segdir[0] * 3, [-0.35, 0.9, 0.1])
segmental("rb7", "lob_r", rll.end - rll.enddir * 5, [0.3, -0.3, -0.9])
segmental("rb8", "lob_r", rll.end, [-0.45, -0.6, -0.66])
segmental("rb9", "lob_r", rll.end, [-0.75, 0.05, -0.66])
segmental("rb10", "lob_r", rll.end, [-0.2, 0.55, -0.81], 32)

# Ліва сторона
lmb = add("lmb", "br_l", O, dL, Lm["length"], Lm["r"], Lm["r"] * 0.95, Lm["wall"], "ring", pitch=4.4, dshape=True,
          d1=unit(dL + np.array([-0.1, 0.05, -0.25])))
lul = add("lul", "lob_l", lmb.end - lmb.enddir * 3, [0.72, -0.5, 0.45], 12, 5.2, 5.0, 1.3, pitch=5.5, gen=2)
lsup = add("lsup", "lob_l", lul.end, [0.45, -0.1, 0.89], 10, 4.1, 3.8, 1.1, pitch=5.0, gen=2)
segmental("lb1+2", "lob_l", lsup.end, [0.3, 0.4, 0.87])
segmental("lb3", "lob_l", lsup.end, [0.6, -0.78, 0.15])
ling = add("ling", "lob_l", lul.end, [0.5, -0.65, -0.57], 16, 3.7, 3.4, 1.0, pitch=5.0, gen=2)
segmental("lb4", "lob_l", ling.end, [0.75, -0.5, -0.42])
segmental("lb5", "lob_l", ling.end, [0.35, -0.65, -0.68])
lll = add("lll", "lob_l", lmb.end, [0.42, 0.3, -0.86], 16, 5.1, 4.6, 1.4, pitch=5.5, gen=2)
segmental("lb6", "lob_l", lmb.end + lll.segdir[0] * 3, [0.35, 0.9, 0.1])
segmental("lb7+8", "lob_l", lll.end, [0.2, -0.5, -0.84])
segmental("lb9", "lob_l", lll.end, [0.72, 0.05, -0.69])
segmental("lb10", "lob_l", lll.end, [0.25, 0.55, -0.8], 32)

MAIN = {"trachea", "rmb", "lmb", "bi"}
GROUPS = ["trachea", "br_r", "br_l", "lob_r", "lob_l"]


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b + (a - b) * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def build_airway():
    lo = np.min([b.bbox(3)[0] for b in branches], axis=0)
    hi = np.max([b.bbox(3)[1] for b in branches], axis=0)
    hi[2] = top[2] + 4
    dims = np.ceil((hi - lo) / VOX).astype(int) + 1
    print("сітка дихальних шляхів", dims, f"{dims.prod() / 1e6:.0f} млн вокселів", flush=True)
    Fo = np.full(dims, 50.0, np.float32)
    Fl = np.full(dims, 50.0, np.float32)
    Fm = np.full(dims, 50.0, np.float32)  # лише трахея, головні й проміжний бронхи (їх розтинаємо)
    Fr = np.full(dims, 50.0, np.float32)
    for b in branches:
        blo, bhi = b.bbox(3)
        i0 = np.maximum(np.floor((blo - lo) / VOX).astype(int), 0)
        i1 = np.minimum(np.ceil((bhi - lo) / VOX).astype(int) + 1, dims)
        sl = tuple(slice(a, c) for a, c in zip(i0, i1))
        g = np.stack(np.meshgrid(*[lo[d] + VOX * np.arange(i0[d], i1[d]) for d in range(3)], indexing="ij"), -1)
        shp = g.shape[:3]
        fo, fl, _, _ = b.evaluate(g.reshape(-1, 3))
        Fx = Fm if b.name in MAIN else Fr
        Fx[sl] = np.minimum(Fx[sl], fo.reshape(shp))
        Fo[sl] = smin(Fo[sl], fo.reshape(shp), 1.4)
        Fl[sl] = smin(Fl[sl], fl.reshape(shp), 0.5)
    shell = np.maximum(Fo, -Fl)
    del Fo, Fl
    Fr -= Fm
    del Fm
    # відкритий верхній зріз трахеї
    zs = lo[2] + VOX * np.arange(dims[2])
    ys = lo[1] + VOX * np.arange(dims[1])
    capf = -((ys[:, None] - top[1]) * A[1] + (zs[None, :] - top[2]) * A[2]) + 1.5
    shell = np.maximum(shell, capf[None, :, :].astype(np.float32))
    return shell, lo, dims, Fr


def attributes(V):
    """Атрибути вершин: хрящ, ваги груп (для кольору «у фокусі»), внутрішня поверхня."""
    n = len(V)
    cart = np.zeros(n, np.float32)
    ring = np.zeros(n, np.float32)
    fbest = np.full(n, 1e9, np.float32)
    gmin = np.full((n, len(GROUPS)), 1e9, np.float32)
    inner = np.zeros(n, np.float32)
    fo_all = np.full(n, 1e9, np.float32)
    for b in branches:
        blo, bhi = b.bbox(4)
        m = np.all((V > blo) & (V < bhi), axis=1)
        if not m.any():
            continue
        fo, fl, c, rz = b.evaluate(V[m])
        idx = np.where(m)[0]
        gi = GROUPS.index(b.group)
        gmin[idx, gi] = np.minimum(gmin[idx, gi], fo)
        better = fo < fbest[idx]
        cart[idx[better]] = c[better]
        ring[idx[better]] = rz[better]
        fbest[idx[better]] = fo[better]
    w = np.exp(-(gmin - gmin.min(1, keepdims=True)) / 1.2)
    w /= w.sum(1, keepdims=True)
    inner = smoothstep(-0.25, -0.6, fbest)  # 1 — слизова просвіту й зріз стінки
    return cart, w.astype(np.float32), inner.astype(np.float32), ring


def mesh_from(field, lo, level=0.0, vox=None):
    vox = vox or VOX
    v, f, _, _ = measure.marching_cubes(field, level, spacing=(vox,) * 3)
    return (v + lo).astype(np.float32), f.astype(np.int32)


def save(name, V, F, **attrs):
    np.savez(os.path.join(OUT, name + ".npz"), v=V, f=F, **attrs)
    print(f"{name}: {len(V) / 1e6:.2f} млн вершин, {len(F) / 1e6:.2f} млн трикутників", flush=True)


def airway():
    shell, lo, dims, own = build_airway()
    V, F = mesh_from(shell, lo)
    cart, w, inner, ring = attributes(V)
    save("airway", V, F, cart=cart, w=w, inner=inner, ring=ring)
    # Фронтальний розтин по трахеобронхіальній площині: передню половину знято.
    g = [lo[d] + VOX * np.arange(dims[d]) for d in range(3)]
    cut = (g[0][:, None, None] * PLANE_N[0] + g[1][None, :, None] * PLANE_N[1]
           + g[2][None, None, :] * PLANE_N[2]).astype(np.float32)
    shell = np.maximum(shell, np.minimum(cut, own + 0.6))
    del own
    V, F = mesh_from(shell, lo)
    cart, w, inner, ring = attributes(V)
    onplane = (np.abs(V @ PLANE_N) < VOX * 0.6).astype(np.float32)
    save("airway_cut", V, F, cart=cart, w=w, inner=np.maximum(inner, onplane), cutface=onplane, ring=ring)


# ---------------------------------------------------------------- легені
def lung(side):
    """side = -1 права, +1 ліва. Неявна форма: грудна порожнина мінус середостіння, серце, купол діафрагми."""
    Lp = P["lungs"]
    vox = 1.0
    lo = np.array([-140.0 if side < 0 else 0.0, -95.0, -200.0])
    hi = np.array([0.0 if side < 0 else 140.0, 105.0, Lp["apex_z"] + 12])
    g = [np.arange(lo[d], hi[d] + vox, vox, dtype=np.float32) for d in range(3)]
    x, y, z = np.meshgrid(*g, indexing="ij")
    zc, az = -45.0, Lp["apex_z"] + 45.0
    up = smoothstep(-30, Lp["apex_z"], z)
    ax_ = 122.0 * (1 - 0.30 * up)
    ay_ = 90.0 * (1 - 0.30 * up)
    yc = 8.0 + 16.0 * up
    xc = side * 22.0 * up  # верхівка зміщена до середини
    k = (np.abs(x) / ax_) ** 2.3 + (np.abs(y - yc) / ay_) ** 2.2 + (np.abs(z - zc) / az) ** 2.7
    f = (k ** (1 / 2.1) - 1) * 80.0
    # середостіння
    med = 11.0 if side < 0 else 13.0
    f = smax(f, med - side * x, 14.0)
    # хребет і заднє середостіння
    f = np.maximum(f, 30.0 - np.sqrt(x ** 2 + (y - 88.0) ** 2))
    # серце
    if side < 0:
        hc, hr = (-4.0, -30.0, -80.0), (34.0, 44.0, 60.0)
    else:
        hc, hr = (10.0, -26.0, -88.0), (52.0, 46.0, 64.0)
    kh = ((x - hc[0]) / hr[0]) ** 2 + ((y - hc[1]) / hr[1]) ** 2 + ((z - hc[2]) / hr[2]) ** 2
    f = smax(f, (1 - np.sqrt(kh)) * 45.0, 8.0)
    # купол діафрагми (правий вищий)
    dc = (-62.0, -8.0, -202.0) if side < 0 else (64.0, -8.0, -212.0)
    dr = (98.0, 104.0, 88.0)
    kd = ((x - dc[0]) / dr[0]) ** 2 + ((y - dc[1]) / dr[1]) ** 2 + ((z - dc[2]) / dr[2]) ** 2
    f = smax(f, (1 - np.sqrt(kd)) * 80.0, 5.0)
    # ворота: заглибина довкола кореня легені
    hx = -30.0 if side < 0 else 38.0
    khl = ((x - hx * 0.45) / 16.0) ** 2 + ((y - 6.0) / 24.0) ** 2 + ((z + 28.0) / 32.0) ** 2
    f = np.maximum(f, (1 - np.sqrt(khl)) * 12.0)
    f = ndimage.gaussian_filter(f, 1.6)
    # щілини
    gob = 0.764 * (y - 78.0) - 0.645 * (z - 38.0) + 0.05 * side * x
    depth = np.clip(1 + f / 14.0, 0, 1)
    f = np.maximum(f, 1.3 * depth - np.abs(gob))
    lobe = (gob > 0).astype(np.float32)  # 1 — нижня частка
    if side < 0:
        zh = Lp["horizontal_fissure_z"] + 0.06 * y
        ghz = z - zh
        m = gob < 0
        f = np.where(m, np.maximum(f, 1.3 * depth - np.abs(ghz)), f)
        lobe = np.where(m & (ghz < 0), 2.0, lobe).astype(np.float32)  # 2 — середня
    f = ndimage.gaussian_filter(f, 0.7)
    V, F = mesh_from(f, lo, vox=vox)
    idx = np.clip(np.round((V - lo) / vox).astype(int), 0, np.array(f.shape) - 1)
    lb = lobe[idx[:, 0], idx[:, 1], idx[:, 2]]
    save("lung_r" if side < 0 else "lung_l", V, F, lobe=lb)
    return V, lb


def landmarks(lung_r, lung_l):
    Vr, _ = lung_r
    Vl, _ = lung_l
    keel = None
    # кіль трахеї: найвища точка, де осі бронхів розходяться далі, ніж сума радіусів просвітів
    for t in np.linspace(0, 30, 301):
        a, b = rmb.at(t), lmb.at(t)
        if np.linalg.norm(a - b) >= (R["r"] - R["wall"]) + (Lm["r"] - Lm["wall"]) + 1.0:
            keel = (a + b) / 2
            break
    lm = {
        "axis": A.tolist(), "plane_n": PLANE_N.tolist(), "dR": dR.tolist(), "dL": dL.tolist(),
        "top": top.tolist(), "trachea_mid": trachea.at(T["length"] * 0.42).tolist(),
        "carina": keel.tolist(), "origin": [0, 0, 0],
        "rmb_mid": rmb.at(R["length"] * 0.62).tolist(), "rmb_end": rmb.end.tolist(),
        "lmb_mid": lmb.at(Lm["length"] * 0.6).tolist(), "lmb_end": lmb.end.tolist(),
        "bi_end": bi.end.tolist(),
        "lung_r": [float(Vr[:, 0].min() * 0.6), float(Vr[:, 1].min()), -10.0],
        "lung_l": [float(Vl[:, 0].max() * 0.6), float(Vl[:, 1].min()), -10.0],
        "pea_path": [trachea.at(s).tolist() for s in np.linspace(T["length"] * 0.12, T["length"], 12)]
                    + [rmb.at(s).tolist() for s in np.linspace(3, R["length"], 8)]
                    + [bi.at(s).tolist() for s in np.linspace(2, 7, 3)],
        "branches": {b.name: {"group": b.group, "L": float(b.L), "r0": b.r0, "r1": b.r1,
                              "p0": b.pts[0].tolist(), "p1": b.end.tolist()} for b in branches},
    }
    json.dump(lm, open(os.path.join(OUT, "landmarks.json"), "w"), ensure_ascii=False, indent=1)
    print("кіль трахеї:", np.round(keel, 1))


if __name__ == "__main__":
    what = sys.argv[3] if len(sys.argv) > 3 else "all"
    if what in ("all", "airway"):
        airway()
    if what in ("all", "lungs"):
        landmarks(lung(-1), lung(+1))
