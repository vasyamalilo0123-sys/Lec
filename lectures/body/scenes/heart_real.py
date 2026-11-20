# Серце на справжній анатомії (BodyParts3D): стінка серця, вінцеві артерії й вени, великі судини.
import bpy, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bp3d, _layout as LY


def build(C):
    C.set_world((0.0015, 0.0012, 0.0015))
    F = bp3d.flesh
    myo = F(C, 'myocardium', (0.33, 0.035, 0.03), (0.52, 0.11, 0.07))
    art = F(C, 'artery', (0.50, 0.03, 0.025), (0.62, 0.06, 0.04), rough=0.3, bump=0.1, noise=60)
    vein = F(C, 'vein', (0.10, 0.06, 0.16), (0.16, 0.08, 0.20), rough=0.32, bump=0.1, noise=60)
    aorta = F(C, 'aorta', (0.62, 0.30, 0.24), (0.74, 0.46, 0.36), rough=0.42, bump=0.15, noise=40, sss=0.6)
    pulm = F(C, 'pulm', (0.42, 0.33, 0.42), (0.55, 0.45, 0.52), rough=0.42, bump=0.15, noise=40, sss=0.6)
    cava = F(C, 'cava', (0.16, 0.10, 0.22), (0.24, 0.14, 0.28), rough=0.4, bump=0.15, noise=40, sss=0.6)
    AORTA = ['FMA3736', 'FMA3768', 'FMA3784', 'FMA3932nsn', 'FMA4058', 'FMA4694', 'FMA3941', 'FMA3953']
    parts = {'FMA7274': myo, 'FMA66326': pulm, 'FMA66643': cava, 'FMA4720': cava, 'FMA10951': cava,
             'FMA4751': cava, 'FMA4761': cava,
             'FMA3802': art, 'FMA3818': art, 'FMA3840nsn': art, 'FMA3862nsn': art, 'FMA3895': art, 'FMA4685': art, 'FMA76994': art,
             'FMA4707': vein, 'FMA4713': vein, 'FMA71567': vein, 'FMA76751': vein, 'FMA4706': vein}
    parts.update({k: aorta for k in AORTA})
    objs = bp3d.load_many(parts, anchor='FMA7274')
    C.cam(85, (1.3, -9.4, 2.0), (-0.45, 0, 0.42), fstop=1.4, focus=9.0)
    for m in (pulm, cava):
        LY.fade_out(m, (0.0, 0.0, 0.3), 0.85, 1.45)
    vp = LY.visible_point
    items = [('верхня порожниста вена', vp(objs['FMA4720'], (0, 0, 0.1)), 'L'),
             ('висхідна аорта', vp(objs['FMA3736'], (0, 0, 0.12)), 'L'),
             ('дуга аорти', vp(objs['FMA3768']), 'R'),
             (('плечоголовна вена', 'ліва'), vp(objs['FMA4761']), 'L'),
             (('загальна сонна артерія', 'ліва'), vp(objs['FMA4058'], (0, 0, 0.15)), 'R'),
             ('легенева артерія', vp(objs['FMA66326'], (0.05, 0, 0.1)), 'R'),
             ('права вінцева артерія', vp(objs['FMA3802']), 'L'),
             (('передня міжшлуночкова', 'гілка лівої вінцевої артерії'), vp(objs['FMA3862nsn']), 'R'),
             ('велика вена серця', vp(objs['FMA4707']), 'R')]
    labels = LY.columns(items, 1100, 760, 1440, left_y=(400, 900), right_y=(150, 900), min_gap=84)
    LY.fuse(C, [objs[k] for k in AORTA], aorta, 'aorta_all', voxel=0.006)
    C.area('key', (-4.0, -4.5, 4.0), (0, -0.5, 0.2), 2.2, 520, (1.0, 0.93, 0.86))
    C.area('rim', (4.0, 3.5, 2.5), (0, 0, 0.2), 2.0, 2600, (0.7, 0.82, 1.0))
    C.area('rim2', (-3.5, 4.0, -1.5), (0, 0, 0), 2.5, 1100, (1.0, 0.5, 0.35))
    C.area('fill', (3.0, -4, -3.0), (0, 0, 0), 4.0, 35, (0.6, 0.7, 1.0))
    return {'kicker': 'Серцево-судинна система', 'title': 'Серце', 'sub': 'Вид спереду', 'scrim': 'left',
            'source': bp3d.CREDIT, 'labels': labels}
