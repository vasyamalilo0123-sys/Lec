"""Turn id/normal/depth buffers of an anatomical model into hand-drawing strokes (outline, colour chalk, hatching)."""
import json, math, sys
import numpy as np, cv2
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

rng = np.random.default_rng(11)
GIDS = [1629, 1630, 1631, 1632, 1633, 1634, 1635, 1636, 1638, 1639, 1652, 1663, 1664, 1665, 1717, 1752, 2073, 2075, 2076, 2077, 2078,
        2079, 2083, 2089, 2093, 2176, 2282]
KIND = {1629: 'art', 1630: 'art', 1631: 'art', 1632: 'art', 1633: 'art', 1634: 'art', 1635: 'atr', 1636: 'myo', 1638: 'atr', 1639: 'myo',
        1652: 'pa', 1663: 'pa', 1664: 'pa', 1665: 'pa', 1717: 'aorta', 1752: 'aorta', 2073: 'cvein', 2075: 'cvein', 2076: 'cvein',
        2077: 'cvein', 2078: 'cvein', 2079: 'pv', 2083: 'pv', 2089: 'pv', 2093: 'pv', 2176: 'vein', 2282: 'vein'}
COL = {'myo': '#e2553a', 'atr': '#d9745a', 'aorta': '#f08a6e', 'pa': '#6f97e6', 'pv': '#e89478', 'vein': '#5b82dd',
       'art': '#ff5a44', 'cvein': '#86a6f2', 'line': '#f3eee6'}
# structures that read as one shape share a region, so no seam is drawn between them
MERGE = {1664: 1663, 1752: 1717}

idm = cv2.imread('buf/id.png')[:, :, 2].astype(np.int32)
nrm = cv2.imread('buf/normal.png')[:, :, ::-1].astype(np.float32) / 255 * 2 - 1
dp = cv2.imread('buf/depth.png').astype(np.float32)
depth = (dp[:, :, 2] + dp[:, :, 1] / 255.0) / 255.0
H, W = idm.shape
gid = np.zeros_like(idm)
for i, g in enumerate(GIDS):
    gid[idm == i + 1] = MERGE.get(g, g)
kind_of = lambda g: KIND.get(int(g))
ves = np.isin(gid, [g for g in GIDS if KIND[g] in ('art', 'cvein')])
# base map: vessels replaced by the surface they lie on
_, (iy, ix) = ndi.distance_transform_edt(ves, return_indices=True)
base = gid[iy, ix]
fg = base > 0
near_ves = cv2.dilate(ves.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0

# ---------- outlines ----------
def diff(a):
    e = np.zeros(a.shape[:2], bool)
    e[:, :-1] |= a[:, :-1] != a[:, 1:]
    e[:-1, :] |= a[:-1, :] != a[1:, :]
    return e

e_lab = diff(base)
dj = np.zeros((H, W), bool)
dj[:, :-1] |= np.abs(depth[:, :-1] - depth[:, 1:]) > 0.014
dj[:-1, :] |= np.abs(depth[:-1, :] - depth[1:, :]) > 0.014
cr = np.zeros((H, W), bool)
cr[:, :-1] |= (nrm[:, :-1] * nrm[:, 1:]).sum(2) < math.cos(math.radians(42))
cr[:-1, :] |= (nrm[:-1, :] * nrm[1:, :]).sum(2) < math.cos(math.radians(42))
inner = (dj | cr) & fg & ~near_ves & ~cv2.dilate(e_lab.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
edge = e_lab | inner
edge = cv2.morphologyEx(edge.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)) > 0
bg_near = cv2.dilate((~fg).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0


def trace(mask):
    """Skeleton -> list of pixel paths."""
    sk = skeletonize(mask)
    pts = set(zip(*np.nonzero(sk)))
    nb = lambda p: [(p[0] + dy, p[1] + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy or dx) and (p[0] + dy, p[1] + dx) in pts]
    deg = {p: len(nb(p)) for p in pts}
    nodes = {p for p, d in deg.items() if d != 2}
    seen, paths = set(), []
    def walk(start, nxt):
        path = [start, nxt]; seen.add((start, nxt)); seen.add((nxt, start))
        prev, cur = start, nxt
        while cur not in nodes:
            cand = [q for q in nb(cur) if q != prev and (cur, q) not in seen]
            if not cand:
                break
            # prefer 4-neighbours to avoid corner cutting loops
            cand.sort(key=lambda q: abs(q[0] - cur[0]) + abs(q[1] - cur[1]))
            q = cand[0]; seen.add((cur, q)); seen.add((q, cur)); path.append(q); prev, cur = cur, q
            if cur == start:
                break
        return path
    for n in nodes:
        for q in nb(n):
            if (n, q) not in seen:
                paths.append(walk(n, q))
    rest = {p for p in pts if p not in nodes and not any((p, q) in seen for q in nb(p))}
    while rest:
        p = rest.pop(); q = nb(p)
        if not q:
            continue
        path = walk(p, q[0]); paths.append(path); rest -= set(path)
    return [np.array(p, np.float32)[:, ::-1] for p in paths]  # -> x,y


def smooth(p, sigma=2.5, step=3.0, wob=0.0):
    if len(p) < 4:
        return p
    closed = np.hypot(*(p[0] - p[-1])) < 2.5 and len(p) > 12
    mode = 'wrap' if closed else 'nearest'
    q = np.stack([ndi.gaussian_filter1d(p[:, 0], sigma, mode=mode), ndi.gaussian_filter1d(p[:, 1], sigma, mode=mode)], 1)
    if closed:
        q = np.vstack([q, q[:1]])
    seg = np.hypot(*np.diff(q, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)])
    if s[-1] < step:
        return q
    t = np.linspace(0, s[-1], max(2, int(s[-1] / step)))
    q = np.stack([np.interp(t, s, q[:, 0]), np.interp(t, s, q[:, 1])], 1)
    if wob:
        n = len(q)
        for ax in (0, 1):
            q[:, ax] += ndi.gaussian_filter1d(rng.normal(0, 1, n), 9, mode='nearest') * wob * 3
    return q


def length(p):
    return float(np.hypot(*np.diff(p, axis=0).T).sum())


strokes = []
def add(p, w, c, a, ph, key=0.0):
    if len(p) < 2:
        return
    strokes.append({'p': [round(float(v), 1) for v in p.reshape(-1)], 'w': round(w, 2), 'c': c, 'a': round(a, 3), 'ph': ph, 'k': key, 'L': round(length(p), 1)})


for p in trace(edge):
    if len(p) < 14:
        continue
    xi = np.clip(p[:, 0].astype(int), 0, W - 1); yi = np.clip(p[:, 1].astype(int), 0, H - 1)
    sil = bg_near[yi, xi].mean() > 0.5
    q = smooth(p, 3.0, 3.0, wob=0.55)
    if sil:
        add(q, 3.4, COL['line'], 0.95, 0, -length(q))
    else:
        if length(q) < 26:
            continue
        add(q, 2.3, COL['line'], 0.8, 1, float(q[:, 1].mean()))

# ---------- tone and direction field ----------
Lv = np.array([-0.45, 0.55, 0.70]); Lv /= np.linalg.norm(Lv)
tone = np.clip((nrm * Lv).sum(2), 0, 1)
tone = cv2.GaussianBlur(tone, (0, 0), 3)
A = np.array([0.55, 0.78, 0.30]); A /= np.linalg.norm(A)
cx = nrm[:, :, 1] * A[2] - nrm[:, :, 2] * A[1]
cy = nrm[:, :, 2] * A[0] - nrm[:, :, 0] * A[2]
fx, fy = cx, -cy
# smooth the (sign-free) field through the double-angle trick
ang = np.arctan2(fy, fx)
c2 = cv2.GaussianBlur(np.cos(2 * ang).astype(np.float32), (0, 0), 6); s2 = cv2.GaussianBlur(np.sin(2 * ang).astype(np.float32), (0, 0), 6)
ang = 0.5 * np.arctan2(s2, c2)


def streamlines(mask, sep, lmin, lmax, rot=0.0, jitter=0.25, prob=None):
    occ = np.zeros((H, W), np.uint8)
    ys, xs = np.nonzero(mask[::sep, ::sep])
    order = rng.permutation(len(ys)); out = []
    for i in order:
        y0, x0 = ys[i] * sep + rng.uniform(0, sep), xs[i] * sep + rng.uniform(0, sep)
        if not (0 <= int(y0) < H and 0 <= int(x0) < W) or not mask[int(y0), int(x0)] or occ[int(y0), int(x0)]:
            continue
        if prob is not None and rng.uniform() > prob[int(y0), int(x0)]:
            continue
        lab = base[int(y0), int(x0)]; half = rng.uniform(lmin, lmax) / 2; parts = []
        for sgn in (1, -1):
            x, y = x0, y0; pts = []; pa = None; d = 0
            while d < half:
                xi, yi = int(x), int(y)
                if not (0 <= xi < W and 0 <= yi < H) or not mask[yi, xi] or base[yi, xi] != lab or (occ[yi, xi] and d > 2):
                    break
                a = ang[yi, xi] + rot
                vx, vy = math.cos(a), math.sin(a)
                if pa is None:
                    vx, vy = vx * sgn, vy * sgn
                elif vx * pa[0] + vy * pa[1] < 0:
                    vx, vy = -vx, -vy
                pa = (vx, vy); pts.append((x, y)); x += vx * 2; y += vy * 2; d += 2
            parts.append(pts)
        pts = parts[1][::-1] + parts[0][1:]
        if len(pts) * 2 < lmin:
            continue
        p = np.array(pts, np.float32)
        cv2.polylines(occ, [p.astype(np.int32).reshape(-1, 1, 2)], False, 1, max(1, int(sep * 0.9)))
        n = len(p)
        for ax in (0, 1):
            p[:, ax] += ndi.gaussian_filter1d(rng.normal(0, 1, n), 6, mode='nearest') * jitter * 3
        out.append(p)
    return out


# ---------- colour chalk, region by region ----------
regions = [g for g in np.unique(base) if g > 0]
regions.sort(key=lambda g: np.nonzero(base == g)[0].mean())
for ri, g in enumerate(regions):
    k = kind_of(g); m = (base == g) & (tone > 0.10)
    m = cv2.erode(m.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    ls = streamlines(m, 7, 26, 150)
    ls.sort(key=lambda p: p[:, 1].mean() + 0.35 * p[:, 0].mean())
    for j, p in enumerate(ls):
        t = float(tone[np.clip(p[:, 1].astype(int), 0, H - 1), np.clip(p[:, 0].astype(int), 0, W - 1)].mean())
        add(p, 9.5, COL[k], 0.07 + 0.80 * t ** 1.25, 2, ri * 1e6 + j)

# ---------- coronary vessels as coloured chalk lines ----------
for vk, ph in (('art', 3), ('cvein', 4)):
    vm = np.isin(gid, [g for g in GIDS if KIND[g] == vk])
    dist = ndi.distance_transform_edt(vm)
    ps = [p for p in trace(vm) if len(p) >= 9]
    ps.sort(key=lambda p: -len(p))
    for j, p in enumerate(ps):
        wv = float(np.median(dist[p[:, 1].astype(int), p[:, 0].astype(int)])) * 2
        q = smooth(p, 2.0, 2.5, wob=0.35)
        add(q, min(9.0, max(2.6, wv * 0.95)), COL[vk], 0.95, ph, j)

# ---------- highlights: lighter chalk of the same hue, soft-edged ----------
def tint(hexc, k=0.62):
    r, g_, b_ = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    return '#%02x%02x%02x' % tuple(int(v + (255 - v) * k) for v in (r, g_, b_))

body = fg & ~near_ves
for thr, sep, rot, a, lm in ((0.50, 8, 0.0, 0.50, (20, 70)), (0.74, 6, 0.85, 0.66, (14, 46))):
    m = cv2.erode((body & (tone > thr)).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    pr = np.clip((tone - thr) / (1 - thr) * 2.2, 0, 1) ** 1.3
    ls = streamlines(m, sep, lm[0], lm[1], rot=rot, jitter=0.3, prob=pr)
    ls.sort(key=lambda p: p[:, 1].mean() + 0.5 * p[:, 0].mean())
    for j, p in enumerate(ls):
        mid = p[len(p) // 2]; k = kind_of(base[int(mid[1]), int(mid[0])])
        t = float(tone[np.clip(p[:, 1].astype(int), 0, H - 1), np.clip(p[:, 0].astype(int), 0, W - 1)].mean())
        add(p, 2.1, tint(COL[k]), a * (0.55 + 0.6 * t), 5, rot * 1e6 + j)

# ---------- label anchors ----------
anch = {}
for g in (1717, 1663, 2282, 1638, 1639, 1636, 1635):
    m = (base == g) & ~near_ves
    if m.sum() < 50:
        continue
    d = ndi.distance_transform_edt(m); y, x = np.unravel_index(d.argmax(), d.shape)
    anch[str(g)] = [int(x), int(y)]
ys, xs = np.nonzero(fg)
out = {'w': W, 'h': H, 'bbox': [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())], 'anchors': anch, 'strokes': strokes}
json.dump(out, open('strokes.json', 'w'), separators=(',', ':'))
from collections import Counter
print(Counter(s['ph'] for s in strokes), 'total px', int(sum(s['L'] for s in strokes)), anch, out['bbox'])
