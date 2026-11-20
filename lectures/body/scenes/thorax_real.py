# Грудна клітка на справжній анатомії (BodyParts3D): ребра, хрящі, груднина, хребет — темна «клітка»; всередині світяться легені й серце.
import bpy, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bp3d, _layout as LY


def build(C):
    C.set_world((0.0012, 0.0012, 0.0016))
    F = bp3d.flesh
    bone = F(C, 'bone', (0.62, 0.55, 0.44), (0.78, 0.72, 0.60), rough=0.55, sss=0.25, scale=0.006, bump=0.35, noise=45, coat=0.08)
    cart = F(C, 'cartilage', (0.60, 0.66, 0.70), (0.74, 0.80, 0.84), rough=0.35, sss=0.6, scale=0.012, bump=0.15, noise=40, coat=0.35)
    lung = F(C, 'lung', (0.60, 0.27, 0.28), (0.74, 0.42, 0.40), rough=0.45, sss=0.8, scale=0.02, bump=0.35, noise=22, coat=0.35)
    myo = F(C, 'myocardium', (0.33, 0.035, 0.03), (0.52, 0.11, 0.07))
    aorta = F(C, 'aorta', (0.62, 0.30, 0.24), (0.74, 0.46, 0.36), rough=0.42, bump=0.15, noise=40, sss=0.6)
    vein = F(C, 'cava', (0.16, 0.10, 0.22), (0.24, 0.14, 0.28), rough=0.4, bump=0.15, noise=40, sss=0.6)
    airway = F(C, 'airway', (0.80, 0.66, 0.52), (0.90, 0.80, 0.68), rough=0.4, sss=0.5, scale=0.01, bump=0.3, noise=50, coat=0.3)
    parts = {}
    for k, n, _ in bp3d.find(r'^(right|left) \w+ rib$') + bp3d.find(r'thoracic vertebra$') + bp3d.find(r'^(right|left) clavicle$'):
        parts[k] = bone
    for k in ('FMA7486', 'FMA7487', 'FMA7488'): parts[k] = bone
    for k, n, _ in bp3d.find(r'intervertebral disk of \w+ thoracic'): parts[k] = cart
    for k in ('BP24', 'BP28'): parts[k] = cart
    for k in ('FMA7333', 'FMA7383', 'FMA7337', 'FMA7370', 'FMA7371'): parts[k] = lung
    parts.update({'FMA7274': myo, 'FMA3736': aorta, 'FMA3768': aorta, 'FMA66326': aorta, 'FMA4720': vein, 'FMA7394': airway})
    objs = bp3d.load_many(parts, anchor='FMA7487')
    C.cam(85, (5.0, -18.5, 1.6), (-1.55, 0, -0.55), fstop=2.4, focus=18.2)
    vp = LY.visible_point
    items = [('ключиця', vp(objs['FMA13322']), 'L'),
             ('ребра', vp(objs['FMA7957'], (-0.5, 0, 0)), 'L'),
             ('реберні хрящі', vp(objs['BP28'], (0, 0, -0.5)), 'L'),
             ('ручка груднини', vp(objs['FMA7486']), 'R'),
             ('тіло груднини', vp(objs['FMA7487']), 'R'),
             ('мечоподібний відросток', vp(objs['FMA7488']), 'R'),
             ('легеня', vp(objs['FMA7370'], (0.3, 0, 0.2)), 'R')]
    labels = LY.columns(items, 1100, 740, 1500, left_y=(400, 900), right_y=(180, 900), min_gap=84)
    # клітка — у контровому світлі, органи підсвічені зсередини теплим
    C.area('key', (-7, -8, 7), (0, 0, 0), 4.0, 900, (1.0, 0.93, 0.86))
    C.area('rim', (8, 6, 4), (0, 0, 0), 4.0, 9000, (0.65, 0.8, 1.0))
    C.area('rim2', (-7, 7, -2), (0, 0, 0), 4.0, 4500, (1.0, 0.5, 0.35))
    C.point('inner', (0.0, 0.45, -0.3), 60, (1.0, 0.55, 0.4), 0.3)
    return {'kicker': 'Опорно-рухова система', 'title': 'Грудна клітка', 'sub': 'Ребра, груднина й хребет\nзахищають серце та легені', 'scrim': 'left',
            'source': bp3d.CREDIT, 'labels': labels}
