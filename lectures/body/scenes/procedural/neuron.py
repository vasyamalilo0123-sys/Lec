# Нервова тканина: нейрон-герой із дендритами, мієлінізованим аксоном, імпульсом на перехваті Ранв'є й синапсами.
import math, random
from mathutils import Vector


def catmull(pts, n=24):
    """Гладка ламана крізь опорні точки."""
    P = [Vector(pts[0])] + [Vector(p) for p in pts] + [Vector(pts[-1])]
    out = []
    for i in range(1, len(P) - 2):
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * P[i]) + (-P[i - 1] + P[i + 1]) * t + (2 * P[i - 1] - 5 * P[i] + 4 * P[i + 1] - P[i + 2]) * t * t
                              + (-P[i - 1] + 3 * P[i] - 3 * P[i + 1] + P[i + 2]) * t ** 3))
    out.append(P[-2])
    return out


def build(C):
    rnd = random.Random(5)
    C.set_world((0.002, 0.004, 0.012))
    m_n = C.mat('neuron', (0.22, 0.34, 0.80), rough=0.42, sss=0.7, sss_radius=(0.3, 0.5, 1.0), sss_scale=0.12, coat=0.35,
                emission=(0.05, 0.12, 0.5), emission_strength=0.12)
    m_bg = C.mat('neuron_bg', (0.05, 0.09, 0.28), rough=0.6, sss=0.3, emission=(0.02, 0.05, 0.3), emission_strength=0.12)
    m_my = C.mat('myelin', (0.92, 0.84, 0.62), rough=0.3, sss=0.6, sss_radius=(1.0, 0.7, 0.4), sss_scale=0.08, coat=0.6)
    m_glow = C.mat_emit('impulse', (1.0, 0.28, 0.02), 6)
    m_glow2 = C.mat_emit('impulse_dim', (1.0, 0.25, 0.02), 1.6)
    m_syn = C.mat_emit('synapse', (1.0, 0.32, 0.03), 5)
    tips = []

    def branch(p, d, L, r, depth, mat, flat=0.45, first=False, wander=0.32):
        p = Vector(p); d = Vector(d).normalized(); pts = [p.copy()]; n = 7
        for i in range(n):
            w = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1) * flat, rnd.uniform(-1, 1))) * wander
            d = (d + w).normalized(); p = p + d * (L / n); pts.append(p.copy())
        radii = [1 - 0.42 * i / n for i in range(n + 1)]
        if first:
            radii[0], radii[1] = 2.6, 1.5
        C.tube('dend', pts, r, mat, radii=radii, res=5)
        if depth > 0:
            perp = d.cross(Vector((0, 1, 0)))
            if perp.length < 0.1: perp = Vector((1, 0, 0))
            perp.normalize()
            for sgn in (-1, 1):
                a = sgn * rnd.uniform(0.35, 0.75)
                nd = (d * math.cos(a) + perp * math.sin(a) + Vector((0, rnd.uniform(-0.3, 0.3), 0))).normalized()
                branch(p, nd, L * rnd.uniform(0.62, 0.85), r * 0.58, depth - 1, mat, flat, wander=wander)
        else:
            tips.append(p.copy())
        return pts

    def soma(center, r, mat, name='soma'):
        c = Vector(center)
        balls = [(c.x, c.y, c.z, r * 1.25)] + [(c.x + rnd.uniform(-.35, .35) * r, c.y + rnd.uniform(-.3, .3) * r, c.z + rnd.uniform(-.35, .35) * r, r * 0.8) for _ in range(4)]
        o = C.metaballs(name, balls, mat, resolution=0.06)
        C.displace(o, 0.05 * r, 0.35 * r)
        return o

    # --- нейрон-герой ---
    S = Vector((-2.75, 0, -1.0))
    soma(S, 0.85, m_n)
    dend_tip = None
    for ang, L in [(100, 2.6), (140, 2.5), (62, 2.7), (185, 2.0), (228, 1.7), (275, 1.3), (30, 1.6)]:
        a = math.radians(ang + rnd.uniform(-8, 8)); d = Vector((math.cos(a), rnd.uniform(-0.25, 0.25), math.sin(a)))
        pts = branch(S + d * 0.55, d, L, 0.085, 3, m_n, first=True)
        if ang == 30: dend_tip = pts[5]

    # --- аксон: мієлінові муфти з перехватами Ранв'є ---
    ctrl = [S + Vector((0.6, 0, -0.25)), (-1.3, 0.1, -1.75), (-0.2, -0.1, -1.95), (1.0, 0.0, -1.45), (2.2, 0.15, -0.55), (3.3, 0.0, 0.1), (4.25, 0.1, 0.35)]
    path = catmull(ctrl, 28)
    n = len(path)
    C.tube('axon', path, 0.062, m_n, radii=[2.4, 1.6] + [1.0] * (n - 2), res=6)
    seg, gap, start = 20, 6, 16
    nodes = []; i = start; k = 0
    while i + seg < n:
        pts = path[i:i + seg + 1]
        rad = [0.55, 0.9] + [1.0] * (len(pts) - 4) + [0.9, 0.55]
        C.tube(f'myelin{k}', pts, 0.19, m_my, radii=rad, res=10)
        nodes.append(path[min(n - 1, i + seg + gap // 2)]); i += seg + gap; k += 1
    hill = path[8]; my_mid = path[start + seg + gap + seg // 2]
    # імпульс: найяскравіший перехват, позаду нього — згасання
    hot = 3 if len(nodes) > 3 else len(nodes) - 1
    for j, p in enumerate(nodes[:hot + 1]):
        age = hot - j
        o = C.prim('sphere', f'pulse{j}', m_glow if age == 0 else m_glow2, loc=p, scale=((0.14 if age == 0 else 0.09),) * 3, u=24, v=12)
        if age < 3:
            C.point(f'pl{j}', p + Vector((0, -0.5, 0.1)), [70, 14, 5][age], (1.0, 0.4, 0.08), 0.2)

    # --- закінчення аксона й синапси на дендриті сусіднього нейрона ---
    S2 = Vector((6.15, 0.9, 1.75))
    soma(S2, 0.8, m_n, 'soma2')
    target = None
    for ang, L in [(205, 2.2), (150, 1.6), (255, 1.8), (95, 1.3), (320, 1.5)]:
        a = math.radians(ang); d = Vector((math.cos(a), -0.12, math.sin(a)))
        pts = branch(S2 + d * 0.5, d, L, 0.08, 2, m_n, first=True, wander=0.2)
        if ang == 205: target = pts
    end = Vector(path[-1]); syn = None
    for j, t in enumerate([3, 4, 5, 6]):
        tp = target[t] + Vector((rnd.uniform(-0.08, 0.08), -0.12, -0.16))
        mid = (end + tp) / 2 + Vector((rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.1), rnd.uniform(-0.25, 0.05)))
        C.tube(f'term{j}', [end, mid, tp], 0.035, m_n, res=4)
        C.prim('sphere', f'bouton{j}', m_syn, loc=tp, scale=(0.075,) * 3, u=20, v=10)
        if j == 1: syn = tp
    C.point('synl', syn + Vector((0, -0.4, -0.1)), 30, (1.0, 0.45, 0.1), 0.2)

    # --- тло: далекі нейрони поза різкістю ---
    for q in range(16):
        c = Vector((rnd.uniform(-11, 13), rnd.uniform(9, 26), rnd.uniform(-7, 7.5)))
        soma(c, rnd.uniform(0.5, 0.8), m_bg, f'bg{q}')
        for _ in range(rnd.randint(4, 6)):
            a = rnd.uniform(0, 6.28); d = Vector((math.cos(a), rnd.uniform(-0.4, 0.4), math.sin(a)))
            branch(c + d * 0.4, d, rnd.uniform(1.8, 3.4), 0.07, 2, m_bg, flat=0.8)
    m_dot = C.mat_emit('spark', (0.3, 0.55, 1.0), 3)
    for _ in range(26):
        C.prim('sphere', 'spark', m_dot, loc=(rnd.uniform(-9, 11), rnd.uniform(3, 18), rnd.uniform(-5, 5)), scale=(rnd.uniform(0.02, 0.05),) * 3, u=8, v=4)
    for _ in range(10):
        C.prim('sphere', 'spark2', m_syn, loc=(rnd.uniform(-9, 11), rnd.uniform(7, 18), rnd.uniform(-5, 5)), scale=(0.07,) * 3, u=8, v=4)

    C.cam(45, (0.2, -13.0, 0.15), (0.2, 0, 0.15), fstop=0.3)
    C.area('key', (-6, -8, 7), (-1, 0, -0.5), 7, 2600, (0.75, 0.85, 1.0))
    C.area('rim', (2, 10, 5), (0, 0, 0), 10, 9000, (0.3, 0.6, 1.0))
    C.area('rim2', (-9, 6, -4), (-2, 0, -1), 6, 3000, (0.5, 0.4, 1.0))
    return {
        'kicker': 'Нервова тканина', 'title': 'Нейрон', 'sub': 'Імпульс стрибає\nвід перехвату до перехвату', 'scrim': 'top', 'title_at': [96, 96],
        'labels': [
            {'text': 'дендрити', 'p': dend_tip, 'at': [720, 470], 'align': 'left'},
            {'text': 'тіло нейрона', 'p': S + Vector((-0.3, -0.9, 0.2)), 'at': [110, 900], 'align': 'left'},
            {'text': 'аксон', 'p': hill, 'at': [500, 950], 'align': 'left'},
            {'text': 'мієлінова оболонка', 'p': my_mid + Vector((0, -0.19, 0)), 'at': [1010, 950], 'align': 'left'},
            {'text': "перехват Ранв'є", 'p': nodes[hot], 'at': [1450, 870], 'align': 'left'},
            {'text': 'синапс', 'p': syn, 'at': [1420, 150], 'align': 'left'},
        ],
    }
