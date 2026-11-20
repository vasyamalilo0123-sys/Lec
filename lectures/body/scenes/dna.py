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
    C.cam(60, (2.6, -5.2, 1.5), (0.3, 0, 0), fstop=0.9)
    C.area('key', (-2, -5, 5), (0, 0, 0), 5, 900, (1.0, 0.95, 0.9))
    C.area('rim', (5, 5, 2), (0, 0, 0), 4, 2500, (0.4, 0.6, 1.0))
    C.area('fill', (-6, 2, -3), (0, 0, 0), 6, 300, (1.0, 0.5, 0.4))
    return {
        'kicker': 'Клітина · ядро', 'title': 'ДНК', 'sub': 'Дві нитки, чотири літери:\nA — T, G — C', 'scrim': 'left', 'title_at': [96, 96],
        'labels': [{'text': 'цукрово-фосфатний остов', 'p': s1[22], 'at': [1300, 150], 'align': 'left'},
                   {'text': 'пара основ', 'sub': 'A — T або G — C', 'p': [(a + b) / 2 for a, b in zip(s1[19], s2[19])], 'at': [1340, 880], 'align': 'left'}],
    }
