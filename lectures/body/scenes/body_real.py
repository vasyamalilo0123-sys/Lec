# Тіло людини: рентген-оболонка шкіри й органи в кольорі. Справжня анатомія BodyParts3D.
import bpy, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bp3d, _tree as T
from mathutils import Vector


def build(C):
    C.set_world((0.001, 0.0012, 0.002))
    F = lambda *a, **k: bp3d.flesh(C, *a, **k)
    M = {
        'brain': F('brain', (0.55, 0.34, 0.33), (0.72, 0.52, 0.48), rough=0.42, noise=40),
        'lung': F('lung', (0.50, 0.20, 0.22), (0.68, 0.36, 0.36), rough=0.5, noise=60, bump=0.4, coat=0.25),
        'heart': F('heart', (0.36, 0.03, 0.03), (0.55, 0.10, 0.07)),
        'artery': F('artery', (0.55, 0.05, 0.04), (0.68, 0.12, 0.09), rough=0.35, bump=0.1),
        'vein': F('vein', (0.13, 0.10, 0.30), (0.20, 0.14, 0.36), rough=0.35, bump=0.1),
        'airway': F('airway', (0.78, 0.66, 0.60), (0.88, 0.80, 0.74), rough=0.45, sss=0.5),
        'liver': F('liver', (0.22, 0.035, 0.025), (0.34, 0.07, 0.04), rough=0.3, noise=50, bump=0.15, coat=0.6),
        'gall': F('gall', (0.16, 0.26, 0.08), (0.26, 0.36, 0.12), rough=0.3),
        'stomach': F('stomach', (0.62, 0.27, 0.22), (0.76, 0.40, 0.33), rough=0.4),
        'spleen': F('spleen', (0.26, 0.05, 0.10), (0.38, 0.09, 0.14), rough=0.32),
        'pancreas': F('pancreas', (0.80, 0.58, 0.34), (0.88, 0.70, 0.46), rough=0.45, bump=0.4, noise=80),
        'kidney': F('kidney', (0.36, 0.09, 0.06), (0.48, 0.14, 0.09), rough=0.32),
        'small': F('small', (0.60, 0.28, 0.24), (0.76, 0.42, 0.36), rough=0.38),
        'colon': F('colon', (0.48, 0.22, 0.17), (0.62, 0.32, 0.25), rough=0.42),
        'bladder': F('bladder', (0.78, 0.58, 0.36), (0.86, 0.68, 0.46), rough=0.4),
        'eso': F('eso', (0.66, 0.34, 0.30), (0.76, 0.44, 0.38)),
    }
    skin_m = C.mat_xray('skin', (0.30, 0.52, 0.85), strength=1.15, power=2.8, base=0.003)
    parts = {}
    for k in T.leaves('FMA55675'): parts[k] = 'brain'          # нейровісь: головний і спинний мозок
    for k in ('FMA7337', 'FMA7371', 'FMA7370', 'FMA7333', 'FMA7383'): parts[k] = 'lung'
    parts.update({'FMA7394': 'airway', 'FMA7274': 'heart', 'FMA3736': 'artery', 'FMA3768': 'artery', 'FMA3784': 'artery',
                  'FMA4720': 'vein', 'FMA10951': 'vein', 'FMA7197': 'liver', 'FMA7202': 'gall', 'FMA7148': 'stomach', 'FMA7196': 'spleen',
                  'FMA7198nsn': 'pancreas', 'FMA7204': 'kidney', 'FMA7205': 'kidney', 'FMA7206': 'small', 'FMA7207': 'small', 'FMA7208': 'small',
                  'FMA14543nsn': 'colon', 'FMA14544': 'colon', 'FMA14542': 'colon', 'FMA15900': 'bladder', 'FMA7131': 'eso',
                  'FMA15571': 'bladder', 'FMA15572': 'bladder'})
    O = {k: T.load(k, M[m], 80000) for k, m in parts.items()}
    skin = T.load('FMA7163', skin_m, 400000)
    lo, hi = bp3d.bbox(skin)
    print('SKIN bbox', [round(v, 2) for v in lo], [round(v, 2) for v in hi])
    top = hi.z; cx = (lo.x + hi.x) / 2; cy = (lo.y + hi.y) / 2
    T.shift_all(list(O.values()) + [skin], (cx, cy, top - 4.6))     # центр кадру: 4,6 од. нижче маківки
    for k in ('FMA7197', 'FMA7274', 'FMA7333', 'FMA15900'):
        a, b = bp3d.bbox(O[k]); print('BB', k, [round(v, 2) for v in a], [round(v, 2) for v in b])
    C.cam(100, (-1.12, -46.0, 0.0), (-1.12, 0, 0.0), fstop=None)
    bpy.context.view_layer.update()
    C.area('key', (-9, -14, 9), (0, 0, 1), 7, 9000, (1.0, 0.94, 0.88))
    C.area('rim', (10, 10, 4), (0, 0, 0), 8, 22000, (0.6, 0.78, 1.0))
    C.area('rim2', (-10, 10, -3), (0, 0, -1), 8, 9000, (1.0, 0.55, 0.4))
    C.area('fill', (6, -14, -6), (0, 0, -1), 10, 900, (0.6, 0.7, 1.0))
    fp = lambda k, **kw: bp3d.front_point(O[k], **kw)
    items = [('легені', fp('FMA7333'), 'L'), ('печінка', fp('FMA7197', bias=(-0.3, 0, 0)), 'L'),
             ('жовчний міхур', fp('FMA7202'), 'L'), ('товста кишка', fp('FMA14543nsn', bias=(-1.0, 0, 0.3)), 'L'), ('сечовий міхур', fp('FMA15900'), 'L'),
             ('головний мозок', fp('FMA72654'), 'R'), ('трахея', fp('FMA7394', bias=(0, 0, 0.3)), 'R'), ('серце', fp('FMA7274', bias=(0.2, 0, -0.1)), 'R'),
             ('шлунок', fp('FMA7148'), 'R'), ('тонка кишка', fp('FMA7207'), 'R')]
    return {'kicker': 'Анатомія', 'title': 'Тіло людини', 'sub': 'Органи на своїх місцях:\nсправжня анатомія з томографії', 'scrim': 'none',
            'source': bp3d.CREDIT, 'labels': T.auto_labels([i for i in items if i[2] == 'L'], 750, 1570, y0=400) + T.auto_labels([i for i in items if i[2] == 'R'], 750, 1570, y0=96)}
