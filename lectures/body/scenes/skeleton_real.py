# Скелет: кістки, хрящі й зуби атласу BodyParts3D, верхня половина тіла в три чверті.
import bpy, sys, os, math, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bp3d, _tree as T
from mathutils import Vector


def build(C):
    C.set_world((0.0012, 0.0012, 0.0016))
    bone = bp3d.flesh(C, 'bone', (0.52, 0.41, 0.28), (0.74, 0.65, 0.50), rough=0.6, sss=0.35, scale=0.02, bump=0.55, noise=110, coat=0.06)
    cart = bp3d.flesh(C, 'cartilage', (0.62, 0.70, 0.74), (0.78, 0.84, 0.86), rough=0.4, sss=0.7, scale=0.03, bump=0.15, noise=60, coat=0.3)
    tooth = bp3d.flesh(C, 'tooth', (0.86, 0.84, 0.76), (0.94, 0.92, 0.86), rough=0.2, sss=0.5, bump=0.05, coat=0.6)
    ids = T.leaves('FMA23881')
    O = {}
    for k in sorted(ids):
        n = bp3d.NAMES.get(k, '')
        if re.search('eyeball|gingiva|membrane|ligament', n): continue     # не кістки
        O[k] = T.load(k, cart if re.search('cartilage|intervertebral dis', n) else bone, 40000)
    for k, n, _ in bp3d.find('tooth'):
        O[k] = T.load(k, tooth, 8000)
    T.shift_all(list(O.values()), (0.0, -0.96, 12.15))
    a = math.radians(27); d = 41.0; tgt = Vector((-1.55, 0, 0.0))
    C.cam(85, tgt + Vector((-math.sin(a) * d, -math.cos(a) * d, 2.2)), tgt, fstop=None)
    bpy.context.view_layer.update()
    C.area('key', (-16, -5, 10), (0, 0, 1), 5, 6500, (1.0, 0.93, 0.85))
    C.area('rim', (9, 11, 5), (0, 0, 0.5), 7, 30000, (0.5, 0.72, 1.0))
    C.area('rim2', (-12, 9, -2), (0, 0, 0), 7, 12000, (1.0, 0.5, 0.32))
    C.area('fill', (8, -12, -6), (0, 0, -1), 10, 220, (0.6, 0.7, 1.0))
    by = {bp3d.NAMES.get(k, ''): k for k in O}
    fp = lambda name, **kw: bp3d.front_point(O[by[name]], **kw)
    items = [('лобова кістка', fp('frontal bone'), 'R'), ('нижня щелепа', fp('mandible', bias=(0, -0.3, -0.2)), 'R'),
             ('ключиця', fp('left clavicle'), 'R'), ('плечова кістка', fp('left humerus'), 'R'),
             ('ребра', fp('left eighth rib', bias=(0.2, -0.5, 0)), 'R'), ('тазова кістка', fp('left hip bone'), 'R'),
             ('грудина', fp('body of sternum'), 'L'), ('поперекові хребці', fp('third lumbar vertebra'), 'L'),
             ('променева кістка', fp('right radius', bias=(0, 0, -0.2)), 'L'), ('ліктьова кістка', fp('right ulna', bias=(0, 0, 0.7)), 'L'), ('крижова кістка', fp('sacrum'), 'L')]
    for t, p, s in items: print('LBL', t, [round(v) for v in T.px(p)], s)
    L = T.auto_labels([i for i in items if i[2] == 'L'], 800, 1560, y0=420) + T.auto_labels([i for i in items if i[2] == 'R'], 800, 1560, y0=96)
    return {'kicker': 'Опорно-рухова система', 'title': 'Скелет', 'sub': 'Кістки, хрящі й зуби —\nкожна деталь окремою сіткою атласу', 'scrim': 'none',
            'source': bp3d.CREDIT, 'labels': L}
