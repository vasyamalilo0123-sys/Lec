# ДНК: подвійна спіраль, зразок оформлення сцени.
import math


def build(C):
    C.set_world((0.004, 0.006, 0.012))
    back = C.mat('backbone', (0.55, 0.62, 0.75), rough=0.25, coat=0.6, sss=0.3, sss_radius=(0.4, 0.5, 1.0))
    cols = {'A': (0.9, 0.25, 0.2), 'T': (0.95, 0.7, 0.2), 'G': (0.2, 0.75, 0.55), 'C': (0.25, 0.5, 0.95)}
    mats = {k: C.mat('base' + k, v, rough=0.3, coat=0.4, emission=v, emission_strength=0.25) for k, v in cols.items()}
    pair = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G'}
    seq = 'ATGCGTACCGTTAGCATGGCATCGATTGCAAGCTTAGGCATC'
    R, rise, turn = 1.0, 0.34, math.radians(36)      # B-форма: 10 пар на оберт; тут довільний масштаб
    s1, s2 = [], []
    for i, ch in enumerate(seq):
        a = i * turn; x = (i - len(seq) / 2) * rise
        p1 = (x, R * math.cos(a), R * math.sin(a)); p2 = (x, R * math.cos(a + 2.4), R * math.sin(a + 2.4))   # зсув ниток дає велику й малу борозни
        s1.append(p1); s2.append(p2)
        mid = tuple((u + v) / 2 for u, v in zip(p1, p2))
        C.tube(f'b{i}a', [p1, mid], 0.085, mats[ch], smooth=False)
        C.tube(f'b{i}b', [mid, p2], 0.085, mats[pair[ch]], smooth=False)
        C.prim('sphere', f's{i}a', back, loc=p1, scale=(0.19,) * 3, u=24, v=12)
        C.prim('sphere', f's{i}b', back, loc=p2, scale=(0.19,) * 3, u=24, v=12)
    C.tube('strand1', s1, 0.12, back); C.tube('strand2', s2, 0.12, back)
    from mathutils import Quaternion
    c = C.cam(50, (1.2, -11.0, 2.6), (0.2, 0, -0.1), fstop=0.35)
    c.rotation_euler = (c.rotation_euler.to_quaternion() @ Quaternion((0, 0, 1), math.radians(-22))).to_euler()   # спіраль іде діагоналлю кадру
    C.area('key', (-3, -7, 6), (0, 0, 0), 6, 1500, (1.0, 0.95, 0.9))
    C.area('rim', (6, 6, 3), (0, 0, 0), 5, 4000, (0.4, 0.6, 1.0))
    C.area('fill', (-7, 2, -4), (0, 0, 0), 6, 500, (1.0, 0.5, 0.4))
    return {
        'kicker': 'Клітина · ядро', 'title': 'ДНК', 'sub': 'Дві нитки, чотири літери:\nA — T, G — C', 'scrim': 'left', 'title_at': [96, 96],
        'labels': [{'text': 'цукрово-фосфатний остов', 'p': s1[26], 'at': [1290, 900], 'align': 'left'},
                   {'text': 'пара основ', 'sub': 'A — T або G — C', 'p': [(a + b) / 2 for a, b in zip(s1[16], s2[16])], 'at': [830, 930], 'align': 'left'}],
    }
