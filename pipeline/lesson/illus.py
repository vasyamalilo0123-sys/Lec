"""Buffers of an anatomical model -> a clean 2D illustration: smooth shaded fill (PNG) + vector line work (JSON)."""
import json, math
import numpy as np, cv2
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

rng = np.random.default_rng(5)
import sys
SC = json.load(open(sys.argv[1])); OUT = 'out/' + SC['name'] + '/'
GIDS = sorted(int(k) for k in SC['parts'])
KIND = {int(k): v for k, v in SC['parts'].items()}
MERGE = {int(k): v for k, v in SC.get('merge', {}).items()}
THIN = set(SC.get('thin', []))
KINDS = sorted(set(KIND.values()) - THIN)
COL = {k: '#b0503c' for k in KIND.values()}; COL['line'] = '#efe6d6'
rgb = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255
tint = lambda h, k: '#%02x%02x%02x' % tuple(int(v * 255 + (255 - v * 255) * k) for v in rgb(h))
sstep = lambda a, b, x: (lambda t: t * t * (3 - 2 * t))(np.clip((x - a) / (b - a), 0, 1))

id2 = cv2.imread(OUT + 'id.png')[:, :, 2].astype(np.int32)
n2 = cv2.imread(OUT + 'normal.png')[:, :, ::-1].astype(np.float32) / 255 * 2 - 1
d2 = cv2.imread(OUT + 'depth.png').astype(np.float32)
depth2 = (d2[:, :, 2] + d2[:, :, 1] / 255.0) / 255.0
gid2 = np.zeros_like(id2)
for i, g in enumerate(GIDS):
    gid2[id2 == i + 1] = MERGE.get(g, g)
VES = [g for g in GIDS if KIND[g] in THIN]
ves2 = np.isin(gid2, VES)
iy, ix = (ndi.distance_transform_edt(ves2, return_indices=True)[1] if ves2.any() else np.indices(ves2.shape))
base2 = gid2[iy, ix]
fg2 = base2 > 0
Lv = np.array([-0.45, 0.55, 0.70]); Lv /= np.linalg.norm(Lv)

# ---------- smooth shaded fill at 2x ----------
nf = n2[iy, ix] * fg2[:, :, None]                       # normals of the underlying surface, background zeroed
wgt = cv2.GaussianBlur(fg2.astype(np.float32), (0, 0), 5) + 1e-4
nf = cv2.GaussianBlur(nf, (0, 0), 5) / wgt[:, :, None]
nf /= np.linalg.norm(nf, axis=2, keepdims=True) + 1e-6
tone2 = np.clip((nf * Lv).sum(2), 0, 1)
nz = np.clip(nf[:, :, 2], 0, 1)
img = np.zeros(gid2.shape + (3,), np.float32)
for g in np.unique(base2):
    if g == 0:
        continue
    m = base2 == g; c = rgb(COL[KIND[int(g)]])
    s = sstep(0.02, 0.92, tone2[m])[:, None]
    deep = c * np.array([0.13, 0.11, 0.16], np.float32) / max(c.mean(), 0.2) * 0.9      # cool, near-black shadow
    col = deep + (c - deep) * s
    col *= (0.50 + 0.50 * sstep(0.0, 0.55, nz[m]))[:, None]                               # edges roll off into the dark
    col += (1 - col) * (0.26 * sstep(0.78, 1.0, tone2[m]))[:, None]                        # soft highlight
    img[m] = col
# contact shadows where one structure passes in front of another
dj = np.maximum(0, cv2.GaussianBlur(depth2, (0, 0), 7) - depth2)
occ = 1 - np.clip(cv2.GaussianBlur((np.maximum(0, depth2 - cv2.erode(depth2, np.ones((25, 25), np.uint8))) > 0.02).astype(np.float32), (0, 0), 9) * 0.55, 0, 0.55)
img *= occ[:, :, None]
out = np.dstack([img[:, :, ::-1], fg2.astype(np.float32)])
out = cv2.GaussianBlur(out, (0, 0), 0.8)
cv2.imwrite(OUT + 'fill2x.png', (np.clip(out, 0, 1) * 255).astype(np.uint8))

# ---------- line work at 1x ----------
gid = gid2[::2, ::2]; base = base2[::2, ::2]; fg = base > 0; ves = np.isin(gid, VES)
nrm = cv2.resize(n2, None, fx=.5, fy=.5, interpolation=cv2.INTER_AREA)
depth = cv2.resize(depth2, None, fx=.5, fy=.5, interpolation=cv2.INTER_AREA)
tone = cv2.resize(tone2, None, fx=.5, fy=.5, interpolation=cv2.INTER_AREA)
nfs = cv2.resize(nf, None, fx=.5, fy=.5, interpolation=cv2.INTER_AREA)
H, W = gid.shape
near_ves = cv2.dilate(ves.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0


def diff(a):
    e = np.zeros(a.shape[:2], bool)
    e[:, :-1] |= a[:, :-1] != a[:, 1:]; e[:-1, :] |= a[:-1, :] != a[1:, :]
    return e


e_lab = diff(base)
dj = np.zeros((H, W), bool)
dj[:, :-1] |= np.abs(depth[:, :-1] - depth[:, 1:]) > 0.014; dj[:-1, :] |= np.abs(depth[:-1, :] - depth[1:, :]) > 0.014
cr = np.zeros((H, W), bool)
cr[:, :-1] |= (nrm[:, :-1] * nrm[:, 1:]).sum(2) < math.cos(math.radians(42)); cr[:-1, :] |= (nrm[:-1, :] * nrm[1:, :]).sum(2) < math.cos(math.radians(42))
inner = (dj | cr) & fg & ~near_ves & ~cv2.dilate(e_lab.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
edge = cv2.morphologyEx((e_lab | inner).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)) > 0
bg_near = cv2.dilate((~fg).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0


def trace(mask):
    sk = skeletonize(mask); pts = set(zip(*np.nonzero(sk)))
    nb = lambda p: [(p[0] + dy, p[1] + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy or dx) and (p[0] + dy, p[1] + dx) in pts]
    nodes = {p for p in pts if len(nb(p)) != 2}; seen, paths = set(), []
    def walk(start, nxt):
        path = [start, nxt]; seen.add((start, nxt)); seen.add((nxt, start)); prev, cur = start, nxt
        while cur not in nodes:
            cand = [q for q in nb(cur) if q != prev and (cur, q) not in seen]
            if not cand:
                break
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
        if q:
            path = walk(p, q[0]); paths.append(path); rest -= set(path)
    return [np.array(p, np.float32)[:, ::-1] for p in paths]


def smooth(p, sigma=3.0, step=3.0):
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
    return np.stack([np.interp(t, s, q[:, 0]), np.interp(t, s, q[:, 1])], 1)


length = lambda p: float(np.hypot(*np.diff(p, axis=0).T).sum())
strokes = []
def add(p, w, c, a, layer, grp=''):
    if len(p) >= 2:
        strokes.append({'p': [round(float(v), 1) for v in p.reshape(-1)], 'w': round(w, 2), 'c': c, 'a': round(a, 3), 'l': layer, 'g': grp})


for p in trace(edge):
    if len(p) < 14:
        continue
    sil = bg_near[np.clip(p[:, 1].astype(int), 0, H - 1), np.clip(p[:, 0].astype(int), 0, W - 1)].mean() > 0.5
    q = smooth(p, 4.0)
    if sil:
        add(q, 2.0, COL['line'], 0.95, 'outline')
    elif length(q) >= 26:
        add(q, 1.3, COL['line'], 0.7, 'outline')

# direction field that wraps around the form
A = np.array([0.55, 0.78, 0.30]); A /= np.linalg.norm(A)
fx = nfs[:, :, 1] * A[2] - nfs[:, :, 2] * A[1]; fy = -(nfs[:, :, 2] * A[0] - nfs[:, :, 0] * A[2])
ang = np.arctan2(fy, fx)
ang = 0.5 * np.arctan2(cv2.GaussianBlur(np.sin(2 * ang).astype(np.float32), (0, 0), 8), cv2.GaussianBlur(np.cos(2 * ang).astype(np.float32), (0, 0), 8))


def streamlines(mask, sep, lmin, lmax, prob):
    occ = np.zeros((H, W), np.uint8); ys, xs = np.nonzero(mask[::sep, ::sep]); res = []
    for i in rng.permutation(len(ys)):
        y0, x0 = ys[i] * sep + rng.uniform(0, sep), xs[i] * sep + rng.uniform(0, sep)
        if not (0 <= int(y0) < H and 0 <= int(x0) < W) or not mask[int(y0), int(x0)] or occ[int(y0), int(x0)] or rng.uniform() > prob[int(y0), int(x0)]:
            continue
        lab = base[int(y0), int(x0)]; half = rng.uniform(lmin, lmax) / 2; parts = []
        for sgn in (1, -1):
            x, y = x0, y0; pts = []; pa = None; d = 0
            while d < half:
                xi, yi = int(x), int(y)
                if not (0 <= xi < W and 0 <= yi < H) or not mask[yi, xi] or base[yi, xi] != lab or (occ[yi, xi] and d > 2):
                    break
                vx, vy = math.cos(ang[yi, xi]), math.sin(ang[yi, xi])
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
        res.append(p)
    return res


# fine engraving in the light, tinted with the colour of the structure
body = fg & ~near_ves
m = cv2.erode((body & (tone > 0.34)).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
for p in streamlines(m, 6, 30, 170, np.clip((tone - 0.34) / 0.66 * 1.9, 0, 1) ** 1.2):
    mid = p[len(p) // 2]; k = KIND[int(base[int(mid[1]), int(mid[0])])]
    t = float(tone[np.clip(p[:, 1].astype(int), 0, H - 1), np.clip(p[:, 0].astype(int), 0, W - 1)].mean())
    add(smooth(p, 2.0, 4.0), 0.9, tint(COL[k], 0.55), 0.10 + 0.42 * t ** 1.5, 'engrave', k)

vcent = {}
import os as _os
for kind in sorted(THIN):
    vis = np.isin(gid, [g for g in GIDS if KIND[g] == kind])
    f = OUT + 'solok_%s.png' % kind
    vm = (cv2.imread(f)[::2, ::2, 2] > 0) if _os.path.exists(f) else vis
    visd = cv2.dilate(vis.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    dist = ndi.distance_transform_edt(vm)
    for p in sorted([p for p in trace(vm) if len(p) >= 9], key=lambda p: -len(p)):
        wv = float(np.median(dist[p[:, 1].astype(int), p[:, 0].astype(int)])) * 2
        q = smooth(p, 2.2, 2.5)
        v = visd[np.clip(q[:, 1].astype(int), 0, H - 1), np.clip(q[:, 0].astype(int), 0, W - 1)]
        v = ndi.median_filter(v.astype(np.uint8), 7).astype(bool); i0 = 0
        for i in range(1, len(q) + 1):
            if i == len(q) or v[i] != v[i0]:
                add(q[max(0, i0 - 1):i], min(9.0, max(2.4, wv * 0.9)), '#ffffff', 1.0, 'vessel' if v[i0] else 'vhidden', kind); i0 = i

# ---------- flat variants: region map, per-region contours, uniform hatch ----------
KIDX = {k: i + 1 for i, k in enumerate(KINDS)}
reg = np.zeros(base2.shape, np.uint8)
for g in np.unique(base2):
    if g:
        reg[base2 == g] = KIDX[KIND[int(g)]] * 20
cv2.imwrite(OUT + 'regions2x.png', reg)
for g in np.unique(base):
    if g == 0:
        continue
    cs, _ = cv2.findContours((base == g).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    for c in cs:
        if len(c) >= 40:
            p = c[:, 0, :].astype(np.float32); add(smooth(np.vstack([p, p[:1]]), 4.0), 1.6, '#ffffff', 1, 'rcontour', KIND[int(g)])
mh = cv2.erode(body.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
for p in streamlines(mh, 6, 40, 280, np.ones((H, W), np.float32)):
    mid = p[len(p) // 2]; add(smooth(p, 2.0, 4.0), 1.0, '#ffffff', 1, 'hatch', KIND[int(base[int(mid[1]), int(mid[0])])])

# ---------- extras for the art-directed styles ----------
from skimage import measure
REGS = [int(g) for g in np.unique(base2) if g]
regid = np.zeros(base2.shape, np.uint8)
for i, g in enumerate(REGS):
    m2 = base2 == g
    cv2.imwrite(OUT + 'reg_%d.png' % g, np.dstack([np.full(m2.shape + (3,), 255, np.uint8), (cv2.GaussianBlur(m2.astype(np.float32), (0, 0), 1.0) * 255).astype(np.uint8)]))
import os
for g in REGS:
    f = OUT + 'solo_%d.png' % g
    if not os.path.exists(f):
        continue
    sm2 = cv2.imread(f)[:, :, 2] > 0
    cv2.imwrite(OUT + 'solo_%d_a.png' % g, np.dstack([np.full(sm2.shape + (3,), 255, np.uint8), (cv2.GaussianBlur(sm2.astype(np.float32), (0, 0), 1.0) * 255).astype(np.uint8)]))
    cs, _ = cv2.findContours(sm2[::2, ::2].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    for c in cs:
        if len(c) >= 40:
            p = c[:, 0, :].astype(np.float32); add(smooth(np.vstack([p, p[:1]]), 4.0), 1.2, '#ffffff', 1, 'solo', str(g))
# depth iso-lines, region by region
if ves.any():
    jy, jx = ndi.distance_transform_edt(ves, return_indices=True)[1]; dsurf = depth[jy, jx]
else:
    dsurf = depth
dmin, dmax = float(dsurf[fg].min()), float(dsurf[fg].max()); NL = 56
for g in REGS:
    m = base == g
    if m.sum() < 200:
        continue
    w_ = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 3) + 1e-4
    dr = cv2.GaussianBlur(dsurf * m, (0, 0), 3) / w_
    me = cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    for li in range(1, NL):
        lv = dmin + (dmax - dmin) * li / NL
        for c in measure.find_contours(dr, lv, mask=me):
            if len(c) >= 14:
                add(smooth(c[:, ::-1].astype(np.float32), 2.5, 3.0), 1.0, '#ffffff', 1, 'topo', '%.3f|%s' % (li / NL, KIND[g]))
regions = []
for g in REGS:
    yy, xx = np.nonzero(base == g)
    regions.append({'gid': g, 'kind': KIND[g], 'bb': [int(xx.min()), int(yy.min()), int(xx.max()), int(yy.max())]})

anch = {}
for g in [int(k) for k in SC['labels']]:
    g = MERGE.get(g, g); mm = (base == g) & ~near_ves
    if KIND.get(g) in THIN:
        mm = gid == g
    if mm.sum() >= 30:
        d = ndi.distance_transform_edt(mm); y, x = np.unravel_index(d.argmax(), d.shape); anch[str(g)] = [int(x), int(y)]
ys, xs = np.nonzero(fg)
json.dump({'w': W, 'h': H, 'bbox': [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())], 'anchors': anch, 'kinds': KINDS, 'regions': regions, 'labels': SC['labels'], 'title': SC['title'], 'strokes': strokes},
          open(OUT + 'ink.json', 'w'), separators=(',', ':'))
from collections import Counter
print(Counter(s['l'] for s in strokes), anch)
