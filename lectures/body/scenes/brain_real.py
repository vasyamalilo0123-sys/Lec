# Головний мозок цілком на справжній анатомії (BodyParts3D): звивини півкуль, мозочок, стовбур.
import bpy, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bp3d, brainparts as B


def build(C):
    C.set_world((0.0015, 0.0012, 0.0015))
    T = B.tissues(C, bp3d)
    parts = {k: T['cortex'] for side in 'RL' for k in B.CORTEX[side]}
    parts.update({k: T['cortex'] for k in B.BOTH})
    parts.update({B.WHITE: T['white'], B.CEREBELLUM: T['cerebellum'], B.PONS: T['stem'], B.MEDULLA: T['stem'], B.MIDBRAIN: T['stem'], B.PEDUNCLE: T['stem']})
    O = bp3d.load_many(parts, anchor=B.WHITE)
    for k in (B.WHITE, B.CEREBELLUM, 'FMA72662'):
        lo, hi = bp3d.bbox(O[k]); print('BBOX', k, [round(v, 2) for v in lo], [round(v, 2) for v in hi])
    cam = C.cam(75, (5.6, -4.6, 1.6), (-0.50, 0.15, -0.14), fstop=2.2)
    bpy.context.view_layer.update()
    C.area('key', (4.5, -4.0, 4.5), (0, 0, 0), 2.5, 520, (1.0, 0.94, 0.88))
    C.area('rim', (-4.0, 3.5, 2.5), (0, 0, 0.2), 2.0, 2400, (0.7, 0.82, 1.0))
    C.area('rim2', (3.0, 4.5, -1.5), (0, 0, 0), 2.5, 1000, (1.0, 0.5, 0.35))
    C.area('fill', (2.0, -5, -3.0), (0, 0, 0), 4.0, 30, (0.6, 0.7, 1.0))
    fp = lambda k, bias=(0, 0, 0): bp3d.front_point(O[k], cam, bias)
    labels = [
        {'text': 'прецентральна звивина', 'p': fp('FMA72662', (0, 0, 0.12)), 'at': [900, 96], 'align': 'left'},
        {'text': 'постцентральна звивина', 'p': fp('FMA72666', (0, 0, 0.12)), 'at': [1400, 96], 'align': 'left'},
        {'text': 'верхня лобова звивина', 'p': fp('FMA72654'), 'at': [600, 380], 'align': 'right'},
        {'text': 'середня лобова звивина', 'p': fp('FMA72656'), 'at': [600, 520], 'align': 'right'},
        {'text': 'верхня скронева звивина', 'p': fp('FMA72801'), 'at': [600, 700], 'align': 'right'},
        {'text': 'нижня скронева звивина', 'p': fp('FMA72688'), 'at': [760, 900], 'align': 'right'},
        {'text': 'потилична частка', 'p': fp('FMA72976'), 'at': [1560, 520], 'align': 'left'},
        {'text': 'мозочок', 'p': fp(B.CEREBELLUM, (0, 0.2, -0.12)), 'at': [1560, 800], 'align': 'left'},
        {'text': 'довгастий мозок', 'p': fp(B.MEDULLA), 'at': [1560, 940], 'align': 'left'},
    ]
    return {'kicker': 'Нервова система', 'title': 'Головний мозок', 'sub': 'Ліва півкуля, вид збоку', 'scrim': 'left', 'source': bp3d.CREDIT, 'labels': labels}
