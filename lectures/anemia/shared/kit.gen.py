#!/usr/bin/env python3
"""Генератор аркуша наскрізних об'єктів лекції «Анемія» -> shared/kit.svg"""
import math, colorsys, sys

OUT = '/home/user/Lec/lectures/anemia/shared/kit.svg'

# ---------------- палітра ----------------
INK = '#f2e6d3'      # світлий контур (теплий білий)
BLOOD = '#c8322f'    # кров / крапля
RBC = '#d1453b'      # еритроцит
PALE = '#e9a397'     # центральна блідість; мікро-дорога
MACRO = '#8c2233'    # макроцит
AMBER = '#efb84a'    # мітка чоловіка (лише вона)
SKY = '#8cc8ec'      # мітка жінки (лише вона)
SKIN = '#b9a59a'     # сіро-тілесний
FE = '#7a4a2a'       # залізо
NERVE = '#f1d04b'
MESH = '#24479f'     # сіточка ретикулоцита (зсунуто темніше від #3b6fd1 — див. palette.md)
VEIN = '#3d63b8'

def lighten(hexc, d):
    r, g, b = (int(hexc[i:i+2], 16)/255 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    r, g, b = colorsys.hls_to_rgb(h, min(1, l+d), s)
    return '#%02x%02x%02x' % tuple(round(v*255) for v in (r, g, b))

RBC_LINE = lighten(RBC, .15)
RBC_BAND = '#dd6a5d'
MICRO_FILL, MICRO_PALE, MICRO_LINE = PALE, '#f6d8d0', lighten(PALE, .10)
MACRO_LINE, MACRO_PALE, MACRO_BAND = lighten(MACRO, .30), '#c0596a', '#a3384a'
SPHERO, SPHERO_LINE = '#b52c2b', lighten('#b52c2b', .15)

W1, W2 = 3, 1.4   # силует / внутрішні межі

def f(v):
    s = ('%.1f' % v)
    return s[:-2] if s.endswith('.0') else ('-0' if s == '-0' else s)

def catmull(pts, closed=True, t=1.0):
    """Криві Безьє через точки (Catmull-Rom -> cubic)."""
    n = len(pts)
    d = 'M%s,%s' % (f(pts[0][0]), f(pts[0][1]))
    rng = range(n) if closed else range(n-1)
    for i in rng:
        p0 = pts[(i-1) % n] if (closed or i > 0) else pts[0]
        p1 = pts[i]; p2 = pts[(i+1) % n]
        p3 = pts[(i+2) % n] if (closed or i+2 < n) else p2
        c1 = (p1[0]+(p2[0]-p0[0])/6*t, p1[1]+(p2[1]-p0[1])/6*t)
        c2 = (p2[0]-(p3[0]-p1[0])/6*t, p2[1]-(p3[1]-p1[1])/6*t)
        d += 'C%s,%s %s,%s %s,%s' % tuple(f(v) for v in (*c1, *c2, *p2))
    return d + ('Z' if closed else '')

def wobble_circle(cx, cy, rx, ry=None, n=12, amp=.012, seed=1, rot=0):
    ry = ry or rx
    pts = []
    for i in range(n):
        a = 2*math.pi*i/n
        k = 1 + amp*math.sin(3*a+seed) + amp*.6*math.cos(5*a+2*seed)
        x, y = rx*k*math.cos(a), ry*k*math.sin(a)
        c, s = math.cos(rot), math.sin(rot)
        pts.append((cx+x*c-y*s, cy+x*s+y*c))
    return catmull(pts)

def P(d, fill='none', stroke=None, sw=None, extra=''):
    s = '<path d="%s" fill="%s"' % (d, fill)
    if stroke: s += ' stroke="%s" stroke-width="%s"' % (stroke, sw)
    return s + extra + '/>'

def anchor(id_, x, y):
    return '<circle id="%s" cx="%s" cy="%s" r="0"/>' % (id_, f(x), f(y))

RJ = ' stroke-linejoin="round" stroke-linecap="round"'

# ---------------- клітини (Ø нормального = 160) ----------------
D = 160.0; R = D/2

def rbc_face(id_, r=R, seed=1):
    return ('<g id="%s">' % id_ +
            P(wobble_circle(0, 0, r, seed=seed), RBC, RBC_LINE, W1) +
            P(wobble_circle(1.5, 1.5, r*.47, seed=seed+2, amp=.03), RBC_BAND) +
            P(wobble_circle(2, 2, r/3, seed=seed+4, amp=.04), PALE, '#e98a7d', 1.1) +
            anchor(id_+'-lab', r+18, -r*.35) + '</g>')

def rbc_profile(id_):
    C0, C2, C4 = .207161, 2.002558, -1.122762      # Evans & Fung 1972
    def h(x): return math.sqrt(max(0, 1-x*x))*(C0+C2*x*x+C4*x**4)
    hmax = max(h(i/1000) for i in range(1000))
    k = .33*D/2/hmax                                    # макс. товщина = 0,33 D
    xs = [math.copysign(abs(math.sin(math.pi/2*i/20)), i) for i in range(-20, 21)]
    top = [(x*R, -h(x)*k) for x in xs]
    bot = [(x*R, h(x)*k) for x in reversed(xs)][1:-1]
    pts = top + bot
    STATS['profile_center_ratio'] = 2*h(0)*k/D
    STATS['profile_max_ratio'] = 2*hmax*k/D
    return ('<g id="%s">' % id_ + P(catmull(pts), RBC, RBC_LINE, W1, RJ) +
            anchor(id_+'-lab', R+18, 0) + '</g>')

def micro(id_):
    r = .8*R
    STATS['micro_d'] = 2*r; STATS['micro_pallor'] = .62
    return ('<g id="%s">' % id_ + P(wobble_circle(0, 0, r, seed=3), MICRO_FILL, MICRO_LINE, W1) +
            P(wobble_circle(1, 1, r*.62, seed=5, amp=.025), MICRO_PALE, '#f2bfb3', 1.1) +
            anchor(id_+'-lab', r+18, -r*.35) + '</g>')

def macro(id_):
    rx, ry, rot = 1.35*R, 1.15*R, math.radians(-8)
    STATS['macro_axes'] = (2*rx, 2*ry)
    return ('<g id="%s">' % id_ + P(wobble_circle(0, 0, rx, ry, seed=2, rot=rot), MACRO, MACRO_LINE, W1) +
            P(wobble_circle(1, 1, rx*.34, ry*.34, seed=6, amp=.03, rot=rot), MACRO_BAND) +
            P(wobble_circle(1.5, 1.5, rx*.24, ry*.24, seed=7, amp=.03, rot=rot), MACRO_PALE, '#cf7383', 1.1) +
            anchor(id_+'-lab', rx+16, -ry*.4) + '</g>')

def retic(id_):
    r = 1.05*R; rm = .8*r
    import random
    rnd = random.Random(7)
    nodes = []
    while len(nodes) < 30:
        a = rnd.uniform(0, 2*math.pi); q = rm*math.sqrt(rnd.uniform(0, 1))
        p = (q*math.cos(a), q*math.sin(a))
        if all(math.dist(p, o) > 17 for o in nodes): nodes.append(p)
    edges = set()
    for i, p in enumerate(nodes):
        near = sorted(range(len(nodes)), key=lambda j: math.dist(p, nodes[j]))[1:3]
        for j in near: edges.add(tuple(sorted((i, j))))
    mesh = ''
    for i, j in sorted(edges):
        a, b = nodes[i], nodes[j]
        mx, my = (a[0]+b[0])/2, (a[1]+b[1])/2
        nx, ny = -(b[1]-a[1]), b[0]-a[0]; L = math.hypot(nx, ny)
        bend = rnd.choice((-1, 1))*rnd.uniform(.12, .3)*L
        mesh += 'M%s,%s Q%s,%s %s,%s' % (f(a[0]), f(a[1]), f(mx+nx/L*bend), f(my+ny/L*bend), f(b[0]), f(b[1]))
    dots = ''.join('<circle cx="%s" cy="%s" r="2.6"/>' % (f(x), f(y)) for x, y in nodes[::3])
    STATS['retic_d'] = 2*r; STATS['retic_mesh_r'] = max(math.hypot(*p) for p in nodes)/r
    return ('<g id="%s">' % id_ + P(wobble_circle(0, 0, r, seed=4), RBC, RBC_LINE, W1) +
            P(wobble_circle(1, 1, r*.36, seed=8, amp=.04), RBC_BAND) +
            '<g id="%s-mesh">' % id_ + P(mesh, 'none', MESH, 2.2, RJ) + '<g fill="%s">%s</g></g>' % (MESH, dots) +
            anchor(id_+'-lab', r+18, -r*.35) + '</g>')

def sphero(id_):
    r = .8*R
    STATS['sphero_d'] = 2*r
    return ('<g id="%s">' % id_ + P(wobble_circle(0, 0, r, seed=9, amp=.008), SPHERO, SPHERO_LINE, W1) +
            anchor(id_+'-lab', r+18, -r*.35) + '</g>')

def schisto(id_):
    # «шолом»: купол + увігнутий зріз із двома ріжками
    pts = [(-66, 16), (-60, -14), (-40, -40), (-8, -52), (26, -48), (52, -30), (66, -2), (70, 20),
           (52, 8), (28, 2), (0, 2), (-28, 6), (-50, 14)]
    d = catmull(pts, t=.9)
    tri = catmull([(96, 30), (128, 18), (134, 46), (112, 58)], t=.7)
    return ('<g id="%s">' % id_ + P(d, RBC, RBC_LINE, W1, RJ) +
            P('M-44,-6C-20,-26 18,-30 46,-12', 'none', RBC_BAND, 1.4, RJ) +
            '<g id="%s-frag">' % id_ + P(tri, RBC, RBC_LINE, 2.4, RJ) + '</g>' +
            anchor(id_+'-lab', 0, -72) + '</g>')

def target(id_):
    r = R
    return ('<g id="%s">' % id_ + P(wobble_circle(0, 0, r, seed=11), RBC, RBC_LINE, W1) +
            P(wobble_circle(1, 1, r*.64, seed=12, amp=.02), PALE, '#e98a7d', 1.1) +
            P(wobble_circle(2, 1, r*.31, seed=13, amp=.03), RBC, '#e98a7d', 1.1) +
            anchor(id_+'-lab', r+18, -r*.35) + '</g>')

def neutro(id_):
    import random
    rnd = random.Random(3)
    r = 1.75*R
    STATS['neutro_d'] = 2*r
    CYTO, GRAN, NUC, NUC_D, NUC_L = '#dcc0cc', '#b88aa3', '#5a3c86', '#3e2763', '#9a82c4'
    gran = ''
    for _ in range(140):
        a = rnd.uniform(0, 2*math.pi); q = r*.9*math.sqrt(rnd.uniform(0, 1))
        gran += '<circle cx="%s" cy="%s" r="%s"/>' % (f(q*math.cos(a)), f(q*math.sin(a)), f(rnd.uniform(1.3, 2.1)))
    # 6 часток ядра по дузі
    lobes, centers = '', []
    for i in range(6):
        a = math.radians(-160 + i*58)
        cx, cy = .5*r*math.cos(a)*1.05, .5*r*math.sin(a)*.95 + 8
        centers.append((cx, cy))
        rx, ry = rnd.uniform(25, 31), rnd.uniform(20, 25)
        lobes += P(wobble_circle(cx, cy, rx, ry, n=10, amp=.07, seed=i*1.7, rot=a+math.pi/2), NUC, NUC_L, 1.6)
        for k in range(3):
            ox, oy = rnd.uniform(-12, 12), rnd.uniform(-9, 9)
            lobes += P(wobble_circle(cx+ox, cy+oy, rnd.uniform(4, 7), rnd.uniform(3, 5), n=7, amp=.15, seed=k+i), NUC_D)
    fil = ''
    for (ax, ay), (bx, by) in zip(centers, centers[1:]):
        mx, my = (ax+bx)/2*1.12, (ay+by)/2*1.12
        fil += 'M%s,%s Q%s,%s %s,%s' % (f(ax), f(ay), f(mx), f(my), f(bx), f(by))
    return ('<g id="%s">' % id_ + P(wobble_circle(0, 0, r, n=14, amp=.02, seed=5), CYTO, INK, W1) +
            '<g fill="%s">%s</g>' % (GRAN, gran) +
            '<g id="%s-nuc">' % id_ + P(fil, 'none', NUC, 3.2, RJ) + lobes + '</g>' +
            ''.join(anchor('%s-lobe%d' % (id_, i+1), x, y) for i, (x, y) in enumerate(centers)) +
            anchor(id_+'-lab', r+18, -r*.35) + '</g>')

# ---------------- крапля ----------------
def drop_pts(n=90):
    """Точки контуру краплі: ширина 150, висота 200 (3:4), центр рамки в (0,0)."""
    segs = [((6, -100), (20, -58), (75, -52), (75, 25)),     # права щока
            ((75, 25), (75, 66.4), (41.4, 100), (0, 100)),
            ((0, 100), (-41.4, 100), (-75, 66.4), (-75, 25)),
            ((-75, 25), (-75, -40), (-8, -56), (6, -100))]   # ліва щока, кінчик трохи вигнутий
    pts = []
    for p0, p1, p2, p3 in segs:
        for i in range(n//4):
            t = i/(n//4); u = 1-t
            pts.append(tuple(u**3*a+3*u*u*t*b+3*u*t*t*c+t**3*d for a, b, c, d in zip(p0, p1, p2, p3)))
    return segs, pts

def drop_body_d():
    segs, _ = drop_pts()
    d = 'M%s,%s' % segs[0][0]
    for s in segs: d += 'C%s,%s %s,%s %s,%s' % (*s[1], *s[2], *s[3])
    return d + 'Z'

def ring_d(off):
    _, pts = drop_pts(160)
    n = len(pts); out = []
    for i in range(1, n):     # без самого кінчика
        a, b = pts[i-1], pts[(i+1) % n]
        tx, ty = b[0]-a[0], b[1]-a[1]; L = math.hypot(tx, ty)
        out.append((pts[i][0]+ty/L*off, pts[i][1]-tx/L*off))
    # кінчик: укорочена фаска замість гострого клина
    tip = (6, -100 - off*1.9)
    sel = out[::5]
    return catmull([tip] + sel, t=1)

def drop(id_, ring, cells):
    xs = [p[0] for p in drop_pts()[1]]; ys = [p[1] for p in drop_pts()[1]]
    STATS['drop_wh'] = (max(xs)-min(xs), max(ys)-min(ys))
    g = '<g id="%s">' % id_
    g += '<g id="%s-ring">' % id_ + P(ring_d(10+W1/2+1), 'none', ring, 2, RJ) + '</g>'
    g += '<g id="%s-body">' % id_ + P(drop_body_d(), BLOOD, INK, W1, RJ) + '</g>'
    g += '<g id="%s-cells" fill="none" stroke="#f0a092" stroke-width="1.4">' % id_ + cells + '</g>'
    # бирка
    tx, ty = 205, -150
    g += ('<g id="%s-tag">' % id_ +
          P('M28,-84C52,-112 74,-118 %s,-118' % f(tx-110), 'none', ring, 1.4, RJ) +
          '<rect x="%s" y="%s" width="220" height="64" rx="16" fill="#000" stroke="%s" stroke-width="2"/>' % (f(tx-110), f(ty-32), ring) +
          anchor(id_+'-tag-num', tx, ty) + '</g>')
    g += anchor(id_+'-lab', -100, 0) + anchor(id_+'-tip', 6, -100) + anchor(id_+'-base', 0, 100)
    return g + '</g>'

def cell_outlines(spec):
    s = ''
    for cx, cy, rx, ry, rot, pr in spec:
        s += P(wobble_circle(cx, cy, rx, ry, n=10, amp=.02, seed=cx, rot=math.radians(rot)))
        s += P(wobble_circle(cx+.5, cy+.5, rx*pr, ry*pr, n=8, amp=.03, seed=cy, rot=math.radians(rot)))
    return s

NEUTRAL_R = 17.5
CELLS0 = cell_outlines([(-30, 22, 17.5, 17.5, 0, 1/3), (14, 50, 17.5, 17.5, 0, 1/3), (30, 6, 17.5, 17.5, 0, 1/3), (-20, 66, 17.5, 17.5, 0, 1/3)])
CELLS_M = cell_outlines([(-36, 20, 14, 14, 0, .62), (-2, 40, 14, 14, 0, .62), (32, 18, 14, 14, 0, .62), (-26, 64, 14, 14, 0, .62), (20, 66, 14, 14, 0, .62)])
CELLS_F = cell_outlines([(-24, 24, 23.6, 20.1, -8, .24), (26, 38, 23.6, 20.1, -8, .24), (-14, 70, 23.6, 20.1, -8, .24)])

# ---------------- предмети ----------------
def tube(id_, cap):
    w, h = 56, 280     # 1:5
    STATS['tube_ratio'] = h/w
    top, bot = -h/2+16, h/2
    body = 'M%s,%s L%s,%s C%s,%s %s,%s 0,%s C%s,%s %s,%s %s,%s L%s,%s' % (
        f(-w/2), f(top), f(-w/2), f(bot-w/2), f(-w/2), f(bot-w/2+w*.3), f(-w*.28), f(bot), f(bot),
        f(w*.28), f(bot), f(w/2), f(bot-w/2+w*.3), f(w/2), f(bot-w/2), f(w/2), f(top))
    lvl = bot - .7*(bot-top)
    bw = w/2-W1/2-1.5
    blood = 'M%s,%s Q0,%s %s,%s L%s,%s C%s,%s %s,%s 0,%s C%s,%s %s,%s %s,%s Z' % (
        f(-bw), f(lvl), f(lvl+5), f(bw), f(lvl), f(bw), f(bot-w/2), f(bw), f(bot-w/2+bw*.6), f(bw*.55), f(bot-1.5-W1/2), f(bot-1.5-W1/2),
        f(-bw*.55), f(bot-1.5-W1/2), f(-bw), f(bot-w/2+bw*.6), f(-bw), f(bot-w/2))
    capd = 'M-34,%s L-34,%s Q-34,%s -28,%s L28,%s Q34,%s 34,%s L34,%s Z' % (f(top+14), f(-h/2-26), f(-h/2-32), f(-h/2-32), f(-h/2-32), f(-h/2-32), f(-h/2-26), f(top+14))
    ribs = ''.join('M%s,%s L%s,%s' % (f(x), f(-h/2-24), f(x), f(top+8)) for x in (-20, -10, 0, 10, 20))
    label = 'M%s,%s L%s,%s M%s,%s L%s,%s' % (f(-w/2+7), f(top+40), f(w/2-7), f(top+40), f(-w/2+7), f(top+56), f(w/2-14), f(top+56))
    return ('<g id="%s">' % id_ +
            '<g id="%s-blood">' % id_ + P(blood, BLOOD) + P('M%s,%s Q0,%s %s,%s' % (f(-bw), f(lvl), f(lvl+5), f(bw), f(lvl)), 'none', '#e8786c', 1.4) + '</g>' +
            P(body, 'none', INK, W1, RJ) + P(label, 'none', INK, 1.2, RJ) +
            '<g id="%s-cap">' % id_ + P(capd, cap, INK, W1, RJ) + P(ribs, 'none', '#00000055', 1.2) + '</g>' +
            anchor(id_+'-lab', w/2+20, 0) + anchor(id_+'-level', 0, lvl) + '</g>')

def arm(id_):
    sil = catmull([(-300, -64), (-200, -60), (-80, -52), (40, -44), (118, -40), (150, -50), (184, -64), (224, -66),
                   (256, -56), (276, -38), (286, -16), (290, 8), (286, 32), (272, 50), (248, 60), (212, 62), (176, 58), (140, 50), (100, 50),
                   (0, 56), (-120, 64), (-220, 70), (-300, 72)], closed=False, t=1)
    hand_lines = ('M168,-58C180,-34 206,-26 238,-30'          # великий палець
                  'M246,-6C262,-4 276,2 282,10 M238,18C256,22 270,28 278,32 M226,40C242,44 254,50 262,54'  # зігнуті пальці
                  'M150,-40C146,-8 146,22 142,48'             # зап'ясткова складка
                  'M-252,-20C-246,-4 -246,10 -254,26')        # ліктьова складка
    veins = ('M-300,-36C-200,-34 -120,-30 -40,-28C40,-26 100,-24 140,-22'   # головна (cephalic)
             'M-300,44C-200,42 -120,40 -40,38C40,36 100,30 140,24'             # основна (basilic)
             'M-226,-34C-206,-8 -196,16 -176,40')                             # серединна ліктьова
    return ('<g id="%s">' % id_ + P(sil + 'L-300,-64Z', SKIN, None, None) +
            P(sil, 'none', INK, W1, RJ) +
            '<g id="%s-veins">' % id_ + P(veins, 'none', VEIN, 7, RJ) + P(veins, 'none', '#7f9ad6', 1.4, RJ) + '</g>' +
            P(hand_lines, 'none', '#6e5f57', W2, RJ) +
            anchor(id_+'-site', -200, 4) + anchor(id_+'-lab', -200, -96) + '</g>')

def man(id_):
    body = catmull([(10, -152), (-14, -142), (-38, -120), (-52, -86), (-52, -40), (-46, 0), (-42, 40), (-36, 100),
                    (-38, 150), (-32, 196), (-34, 214), (-22, 220), (40, 220), (42, 212), (24, 204), (12, 192),
                    (6, 150), (14, 106), (26, 60), (36, 16), (46, -26), (50, -70), (48, -106), (40, -128), (32, -144)], t=1)
    head = wobble_circle(34, -170, 26, 30, n=10, amp=.02, seed=2, rot=math.radians(20))
    inner = ('M-12,-112C-2,-76 4,-40 8,-6C10,10 14,18 20,22'     # рука
             'M-8,60C-8,110 -10,160 -6,204')                     # межа ніг
    return ('<g id="%s">' % id_ + P(body, SKIN, AMBER, W1, RJ) + P(head, SKIN, AMBER, W1) +
            P(inner, 'none', '#6e5f57', W2, RJ) + P('M20,22C26,28 24,36 16,36', 'none', '#6e5f57', W2, RJ) +
            anchor(id_+'-head', 34, -170) + anchor(id_+'-lab', 70, -120) + anchor(id_+'-foot', 10, 220) + '</g>')

def woman(id_):
    # обличчям ліворуч; нижча (0,9), сутула, з паличкою
    body = catmull([(-2, -130), (20, -116), (34, -88), (40, -50), (36, -12), (46, 40), (56, 96), (60, 136),
                    (30, 140), (24, 176), (26, 194), (22, 198), (-26, 198), (-24, 190), (-8, 184), (-6, 140),
                    (-50, 136), (-44, 92), (-34, 40), (-30, -10), (-36, -52), (-34, -90), (-24, -116), (-16, -126)], t=1)
    head = wobble_circle(-20, -152, 24, 27, n=10, amp=.02, seed=4, rot=math.radians(-25))
    bun = wobble_circle(6, -170, 10, 9, n=8, amp=.03, seed=1)
    inner = 'M-10,-92C-22,-60 -34,-30 -44,-6C-48,4 -52,8 -58,10 M16,140L16,190'
    cane = 'M-62,8L-70,198 M-62,8C-62,-2 -52,-4 -48,4'
    return ('<g id="%s">' % id_ + P(cane, 'none', INK, W1, RJ) + P(body, SKIN, SKY, W1, RJ) +
            P(bun, SKIN, SKY, 2) + P(head, SKIN, SKY, W1) + P(inner, 'none', '#6e5f57', W2, RJ) +
            anchor(id_+'-head', -20, -152) + anchor(id_+'-lab', -100, -110) + anchor(id_+'-foot', 0, 198) + '</g>')

def badge(id_, ring, fem):
    head = wobble_circle(0, -10, 14, 16, n=10, amp=.02, seed=3)
    bust = 'M-30,32C-28,14 -16,8 0,8C16,8 28,14 30,32Z'
    extra = P(wobble_circle(11, -22, 6, 5.5, n=8, seed=2), SKIN, ring, 1.6) if fem else ''
    clip = '<clipPath id="%s-clip"><circle r="38"/></clipPath>' % id_
    return ('<g id="%s">' % id_ + clip + '<circle r="40" fill="#000" stroke="%s" stroke-width="3"/>' % ring +
            '<g clip-path="url(#%s-clip)">' % id_ + extra + P(head, SKIN, ring, 2) + P(bust + 'M-30,32L-30,60L30,60L30,32', SKIN, ring, 2) + '</g>' +
            anchor(id_+'-lab', 52, 0) + '</g>')

def stairs(id_):
    d = 'M-80,60L-80,30L-40,30L-40,0L0,0L0,-30L40,-30L40,-60L80,-60L80,60Z'
    return ('<g id="%s">' % id_ + P(d, '#4a4440', INK, W1, ' stroke-linejoin="round"') +
            P('M-80,30L80,30M-40,0L80,0M0,-30L80,-30', 'none', '#8a8079', W2) + anchor(id_+'-lab', 0, -82) + '</g>')

def foot(id_):
    sil = catmull([(-60, -110), (-26, -110), (-22, -40), (-14, 2), (20, 18), (70, 26), (106, 34), (118, 46), (110, 58),
                   (40, 60), (-30, 58), (-62, 54), (-74, 40), (-72, 10), (-66, -40)], t=1)
    nerve = 'M-44,-110C-48,-60 -54,-10 -50,22C-46,40 -30,46 -6,46C30,46 70,44 104,44 M-6,46C14,38 40,34 70,36 M-50,22C-58,34 -64,40 -66,44'
    return ('<g id="%s">' % id_ + P(sil, SKIN, INK, W1, RJ) +
            P('M70,26C72,36 72,44 70,52 M90,30C92,38 92,46 90,52', 'none', '#6e5f57', W2, RJ) +
            '<g id="%s-nerve">' % id_ + P(nerve, 'none', NERVE, 3, RJ) + '</g>' +
            anchor(id_+'-lab', 20, -40) + '</g>')

def fe(id_):
    return '<g id="%s"><circle r="4" fill="%s" stroke="#c08a5c" stroke-width="1"/></g>' % (id_, FE)

def granules(cx, cy, rx, ry, n, seed, ytop=None):
    import random
    rnd = random.Random(seed); out = []; s = ''
    tries = 0
    while len(out) < n and tries < 5000:
        tries += 1
        a = rnd.uniform(0, 2*math.pi); q = math.sqrt(rnd.uniform(0, 1))
        p = (cx+rx*q*math.cos(a), cy+ry*q*math.sin(a))
        if ytop is not None and p[1] < ytop: continue
        if all(math.dist(p, o) > 9.5 for o in out):
            out.append(p); s += '<circle cx="%s" cy="%s" r="%s"/>' % (f(p[0]), f(p[1]), f(rnd.choice((3, 3.5, 4))))
    return s

def ferritin(id_):
    sub = ''
    for i in range(12):
        a0, a1 = math.radians(i*30+3), math.radians(i*30+27)
        r0, r1 = 40, 58
        pts = [(r0*math.cos(a0), r0*math.sin(a0)), (r1*math.cos(a0), r1*math.sin(a0)), (r1*math.cos((a0+a1)/2)*1.02, r1*math.sin((a0+a1)/2)*1.02),
               (r1*math.cos(a1), r1*math.sin(a1)), (r0*math.cos(a1), r0*math.sin(a1))]
        sub += P(catmull(pts, t=.6), '#d6b98c', '#f2e2c4', 1.2, RJ)
    return ('<g id="%s">' % id_ + '<circle r="61" fill="none" stroke="%s" stroke-width="%s"/>' % (INK, W1) + sub +
            '<g id="%s-core" fill="%s" stroke="#c08a5c" stroke-width="1">' % (id_, FE) + granules(0, 0, 30, 30, 9, 4) + '</g>' +
            anchor(id_+'-lab', 76, -30) + '</g>')

def flask(id_):
    R0 = 92
    # кругла колба: куля R0 з центром (0,10), шийка 52 завширшки
    k = .5523*R0; cy = 10
    import math as m
    a = m.asin(26/R0); yj = cy - R0*m.cos(a)      # точка, де шийка входить у кулю
    d = (f'M-26,-170L-26,{f(yj-6)}C-26,{f(yj+2)} -{f(R0)},{f(cy-R0*.62)} -{f(R0)},{f(cy)}'
         f'C-{f(R0)},{f(cy+k)} -{f(k)},{f(cy+R0)} 0,{f(cy+R0)}C{f(k)},{f(cy+R0)} {f(R0)},{f(cy+k)} {f(R0)},{f(cy)}'
         f'C{f(R0)},{f(cy-R0*.62)} 26,{f(yj+2)} 26,{f(yj-6)}L26,-170')
    rim = 'M-34,-170L34,-170'
    ticks = 'M-70,-10L-56,-10M-80,20L-64,20M-76,50L-60,50'
    a = granules(0, 50, 80, 38, 22, 11, ytop=58)
    b = granules(0, 10, 80, 72, 120, 12)
    return ('<g id="%s">' % id_ +
            '<g id="%s-fe-b" fill="%s" stroke="#c08a5c" stroke-width="1">' % (id_, FE) + b + '</g>' +
            '<g id="%s-fe-a" fill="%s" stroke="#c08a5c" stroke-width="1">' % (id_, FE) + a + '</g>' +
            P(d, 'none', INK, W1, RJ) + P(rim, 'none', INK, W1, RJ) + P(ticks, 'none', INK, W2, RJ) +
            anchor(id_+'-lab', 110, -40) + anchor(id_+'-mouth', 0, -170) + '</g>')

def hepcidin(id_):
    # шпилька з 25 амінокислот, 4 дисульфідні містки
    pts = []
    for i in range(25):
        if i < 11: pts.append((-22 + 2.5*math.sin(i*1.3), -75.5 + i*12.5))
        elif i < 14:
            a = math.pi*(i-10)/4; pts.append((-22*math.cos(a), 49.5 + 22*math.sin(a)))
        else: pts.append((22 + 2.5*math.sin(i*1.3), 62 - (i-13)*12.5))
    chain = catmull(pts, closed=False, t=.8)
    bridges = ''.join('M%s,%s L%s,%s' % (f(pts[i][0]+6), f(pts[i][1]), f(pts[24-i][0]-6), f(pts[24-i][1])) for i in (2, 4, 6, 8))
    beads = ''.join('<circle cx="%s" cy="%s" r="7.5"/>' % (f(x), f(y)) for x, y in pts)
    return ('<g id="%s">' % id_ + P(chain, 'none', '#3e8a7a', 4, RJ) + P(bridges, 'none', NERVE, 2.2, RJ) +
            '<g fill="#5fbfa8" stroke="#c7eee4" stroke-width="1.4">%s</g>' % beads + anchor(id_+'-lab', 34, -60) + '</g>')

def ferroportin(id_):
    mem = 'M-150,-22L150,-22M-150,22L150,22'
    heads = ''.join('<circle cx="%s" cy="%s" r="5"/>' % (f(x), f(y)) for x in range(-146, 151, 12) for y in (-22, 22) if abs(x) > 44)
    lobe = catmull([(-46, -40), (-14, -44), (-10, -12), (-12, 12), (-10, 44), (-46, 42), (-52, 0)], t=.9)
    lobe2 = lobe.replace('-', '~').replace('~', '-')
    lobe2 = catmull([(46, -40), (14, -44), (10, -12), (12, 12), (10, 44), (46, 42), (52, 0)], t=.9)
    return ('<g id="%s">' % id_ + '<rect x="-150" y="-22" width="300" height="44" fill="#3a302b"/>' +
            '<g fill="#8a7a6c">%s</g>' % heads + P(mem, 'none', INK, W2) +
            P(lobe, '#9c84c4', INK, W1, RJ) + P(lobe2, '#9c84c4', INK, W1, RJ) +
            anchor(id_+'-pore', 0, 0) + anchor(id_+'-lab', 0, -64) + '</g>')

def pill(id_):
    side = 'M-50,0L-50,12C-50,30 -28,40 0,40C28,40 50,30 50,12L50,0Z'
    top = wobble_circle(0, 0, 50, 28, n=12, amp=.004, seed=1)
    return ('<g id="%s" transform-origin="0 0">' % id_ + P(side, '#7f4229', INK, W1, RJ) + P(top, '#a65a3a', INK, W1) +
            P('M-34,-6C-12,2 12,2 34,-6', 'none', '#e9c3a8', W2, RJ) + anchor(id_+'-lab', 66, -10) + '</g>')

def ampoule(id_):
    s = catmull([(0, -100), (12, -92), (12, -78), (6, -66), (8, -56), (22, -36), (22, 70), (18, 92), (0, 98),
                 (-18, 92), (-22, 70), (-22, -36), (-8, -56), (-6, -66), (-12, -78), (-12, -92)], t=.8)
    liquid = 'M-19,-10Q0,-6 19,-10L19,70C19,84 14,94 0,94C-14,94 -19,84 -19,70Z'
    return ('<g id="%s">' % id_ + '<g id="%s-liquid">' % id_ + P(liquid, '#d4486a') + '</g>' +
            P(s, 'none', INK, W1, RJ) + P('M-7,-61L7,-61', 'none', NERVE, 2.4, RJ) +
            P('M-22,20L22,20M-22,40L22,40', 'none', INK, W2) + anchor(id_+'-lab', 36, 0) + '</g>')

def bag(id_, fillc, w, h, drip):
    x0, y0 = -w/2, -h/2
    body = 'M%s,%s L%s,%s Q%s,%s %s,%s L%s,%s Q%s,%s %s,%s L%s,%s Q%s,%s %s,%s L%s,%s Q%s,%s %s,%s Z' % (
        f(x0+16), f(y0), f(-x0-16), f(y0), f(-x0), f(y0), f(-x0), f(y0+16), f(-x0), f(-y0-30), f(-x0), f(-y0), f(-x0-30), f(-y0),
        f(x0+30), f(-y0), f(x0), f(-y0), f(x0), f(-y0-30), f(x0), f(y0+16), f(x0), f(y0), f(x0+16), f(y0))
    lvl = y0 + h*.22
    liq = 'M%s,%s L%s,%s L%s,%s Q%s,%s %s,%s L%s,%s Q%s,%s %s,%s Z' % (
        f(x0+3), f(lvl), f(-x0-3), f(lvl), f(-x0-3), f(-y0-30), f(-x0-3), f(-y0-3), f(-x0-30), f(-y0-3), f(x0+30), f(-y0-3), f(x0+3), f(-y0-3), f(x0+3), f(-y0-30))
    hole = '<rect x="-14" y="%s" width="28" height="10" rx="5" fill="#000" stroke="%s" stroke-width="%s"/>' % (f(y0+10), INK, W2)
    ticks = ''.join('M%s,%s L%s,%s' % (f(-x0-22), f(lvl+k*28), f(-x0-8), f(lvl+k*28)) for k in range(1, 5))
    s = '<g id="%s">' % id_ + '<g id="%s-liquid">' % id_ + P(liq, fillc) + '</g>' + P(body, 'none', INK, W1, RJ) + hole + P(ticks, 'none', INK, W2)
    if drip:
        yb = -y0
        s += P('M-6,%sL-6,%sM6,%sL6,%s' % (f(yb), f(yb+16), f(yb), f(yb+16)), 'none', INK, W2)
        s += P('M-12,%sL-12,%s Q-12,%s 0,%s Q12,%s 12,%s L12,%s Z' % (f(yb+16), f(yb+66), f(yb+76), f(yb+76), f(yb+76), f(yb+66), f(yb+16)), '#00000000', INK, 2.2, RJ)
        s += P('M-10,%s L10,%s L10,%s Q0,%s -10,%s Z' % (f(yb+56), f(yb+56), f(yb+66), f(yb+74), f(yb+66)), fillc)
        s += '<g id="%s-dropl">' % id_ + P('M0,%sC4,%s 5,%s 0,%s C-5,%s -4,%s 0,%s Z' % (f(yb+28), f(yb+34), f(yb+40), f(yb+42), f(yb+40), f(yb+34), f(yb+28)), fillc, INK, 1) + '</g>'
        s += P('M0,%sC0,%s 0,%s 0,%s' % (f(yb+76), f(yb+120), f(yb+160), f(yb+200)), 'none', INK, 2.2, RJ)
        s += '<rect x="-10" y="%s" width="20" height="28" rx="4" fill="#4a4440" stroke="%s" stroke-width="%s"/>' % (f(yb+120), INK, W2)
        s += '<path id="%s-flow" d="M0,%sL0,%sL0,%s" fill="none" stroke="none"/>' % (id_, f(yb+28), f(yb+76), f(yb+200))
    else:
        yb = -y0
        s += P('M-20,%sL-20,%sM0,%sL0,%sM20,%sL20,%s' % (f(yb), f(yb+18), f(yb), f(yb+26), f(yb), f(yb+18)), 'none', INK, 4, RJ)
        s += '<rect x="%s" y="%s" width="%s" height="54" rx="6" fill="#000" stroke="%s" stroke-width="%s"/>' % (f(x0+18), f(lvl+22), f(w-36), INK, W2)
    s += anchor(id_+'-lab', -x0+22, 0) + anchor(id_+'-hang', 0, y0+15) + '</g>'
    return s

def flag(id_):
    return ('<g id="%s">' % id_ + P('M-30,70L-30,-70', 'none', INK, W1, RJ) +
            P('M-28,-68L42,-48L-28,-26Z', RBC, INK, 2, RJ) + anchor(id_+'-base', -30, 70) + anchor(id_+'-lab', 56, -48) + '</g>')

def ruler(id_):
    s = '<g id="%s">' % id_ + P('M-480,0L480,0', 'none', INK, 2)
    t = ''
    for v in range(60, 141, 5):
        x = (v-100)*12
        t += 'M%s,0L%s,%s' % (f(x), f(x), f(-18 if v % 10 == 0 else -10))
    s += P(t, 'none', INK, 2)
    s += ''.join(anchor('%s-n%d' % (id_, v), (v-100)*12, 34) for v in range(60, 141, 10))
    return s + '</g>'

def road(id_, col):
    L = 180
    return ('<g id="%s">' % id_ + P('M-%d,-11L%d,-11M-%d,11L%d,11' % (L, L, L, L), 'none', INK, 1.4) +
            P('M-%d,0L%d,0' % (L, L), 'none', col, 4, ' stroke-dasharray="14 10"') +
            '<path id="%s-axis" d="M-%d,0L%d,0" fill="none" stroke="none"/>' % (id_, L, L) + '</g>')

def stop(id_):
    return ('<g id="%s"><rect x="-100" y="-28" width="200" height="56" rx="14" fill="#000" stroke="%s" stroke-width="2"/>' % (id_, INK) +
            anchor(id_+'-text', 0, 0) + '</g>')

def vessel(id_):
    L = 320
    wall_o, wall_i = 70, 52
    s = '<g id="%s">' % id_
    s += P('M-%d,-%dL%d,-%dL%d,%dL-%d,%dZ' % (L, wall_o, L, wall_o, L, wall_o, L, wall_o), '#a8433d')
    s += P('M-%d,-%dL%d,-%dL%d,%dL-%d,%dZ' % (L, wall_i, L, wall_i, L, wall_i, L, wall_i), '#e6c98e')
    s += P('M-%d,-%dC-100,-%d 100,-%d %d,-%d M-%d,%dC-100,%d 100,%d %d,%d' % (L, wall_o, wall_o+3, wall_o-3, L, wall_o, L, wall_o, wall_o-3, wall_o+3, L, wall_o), 'none', INK, W1, RJ)
    s += P('M-%d,-%dL%d,-%dM-%d,%dL%d,%d' % (L, wall_i, L, wall_i, L, wall_i, L, wall_i), 'none', '#f0d5c8', W2)
    cells = ''
    for (x, y, rot) in [(-250, -14, 10), (-160, 18, -15), (-70, -20, 20), (30, 10, -5), (120, -16, 30), (220, 16, -20)]:
        cells += '<g transform="translate(%d,%d) rotate(%d) scale(.3)">' % (x, y, rot) + \
                 P(wobble_circle(0, 0, R, seed=x), RBC, RBC_LINE, 6) + P(wobble_circle(0, 0, R/3, seed=y), PALE) + '</g>'
    s += '<g id="%s-cells">' % id_ + cells + '</g>'
    s += '<path id="%s-axis" d="M-%d,0L%d,0" fill="none" stroke="none"/>' % (id_, L, L)
    return s + anchor(id_+'-lab', 0, -wall_o-24) + '</g>'

# ---------------- аркуш ----------------
STATS = {}
items = [  # (x, y, svg)
    (180, 250, drop('k-drop-m', AMBER, CELLS_M)), (620, 250, drop('k-drop-f', SKY, CELLS_F)),
    (1010, 270, '<g id="k-drop-cells0" fill="none" stroke="#f0a092" stroke-width="1.4">' + P(drop_body_d(), BLOOD, INK, W1, RJ) + CELLS0 + '</g>'),
    (1250, 250, rbc_face('k-rbc')), (1500, 250, rbc_profile('k-rbc-side')), (1740, 250, micro('k-micro')),
    (2000, 250, macro('k-macro')), (2290, 250, retic('k-retic')),
    (180, 620, sphero('k-sphero')), (430, 620, schisto('k-schisto')), (720, 620, target('k-target')),
    (1050, 620, neutro('k-neutro')),
    (1360, 620, tube('k-tube-m', AMBER)), (1470, 620, tube('k-tube-f', SKY)),
    (1640, 620, fe('k-fe')), (1800, 620, ferritin('k-ferritin')), (2020, 620, hepcidin('k-hepcidin')),
    (2270, 620, pill('k-pill')),
    (200, 1020, man('k-man')), (420, 1040, woman('k-woman')), (600, 940, badge('k-badge-m', AMBER, False)),
    (600, 1080, badge('k-badge-f', SKY, True)), (790, 1000, stairs('k-stairs')), (1040, 1040, foot('k-foot')),
    (1440, 1000, arm('k-arm')), (1830, 1000, flask('k-flask')), (2060, 990, ferroportin('k-ferroportin')),
    (2300, 980, ampoule('k-ampoule')),
    (190, 1440, bag('k-drip', '#6b3f24', 140, 190, True)), (430, 1400, bag('k-bag', '#a5262b', 160, 220, False)),
    (620, 1400, flag('k-flag')), (1250, 1330, ruler('k-ruler')),
    (900, 1520, road('k-road-micro', PALE)), (1300, 1520, road('k-road-normo', RBC)), (1700, 1520, road('k-road-macro', MACRO)),
    (2100, 1400, stop('k-stop')), (1650, 1700, vessel('k-vessel')),
]
body = ''.join('<g transform="translate(%d,%d)">%s</g>' % (x, y, s) for x, y, s in items)
svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2480 1840" width="2480" height="1840">'
       '<rect width="2480" height="1840" fill="#000"/>' + body + '</svg>')
open(OUT, 'w').write(svg)
print(len(svg), 'bytes')
for k, v in STATS.items(): print(k, v)
print('RBC_LINE', RBC_LINE, 'MICRO_LINE', MICRO_LINE, 'MACRO_LINE', MACRO_LINE, 'SPHERO_LINE', SPHERO_LINE)
