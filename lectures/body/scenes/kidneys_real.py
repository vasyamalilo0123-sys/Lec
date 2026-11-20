# Сечова система на справжній анатомії (BodyParts3D): нирки, надниркові залози, сечоводи, сечовий міхур, судини.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import abd_common as A
import bp3d


def build(C):
    C.set_world((0.0015, 0.0012, 0.0015))
    parts = {'FMA7204': 'kidney', 'FMA7205': 'kidney', 'FMA15629': 'adrenal', 'FMA15630': 'adrenal', 'FMA15571': 'ureter', 'FMA15572': 'ureter',
             'FMA15900': 'bladder', 'FMA14752': 'artery', 'FMA14753': 'artery', 'FMA14335': 'vein', 'FMA14336': 'vein',
             'FMA3784': 'aorta', 'FMA10951': 'cava', 'FMA14765': 'aorta', 'FMA14766': 'aorta', 'FMA21387': 'cava', 'FMA21388': 'cava',
             'FMA18806': 'aorta', 'FMA18807': 'aorta', 'FMA18809': 'aorta', 'FMA18810': 'aorta',
             'FMA18885': 'cava', 'FMA18886': 'cava', 'FMA18887': 'cava', 'FMA18888': 'cava'}
    o = A.load(C, parts)
    body = [o[k] for k in ('FMA7204', 'FMA7205', 'FMA15629', 'FMA15630', 'FMA15900')]      # аорта й порожниста вена йдуть за верхній край
    cam, c, d = A.front_cam(C, list(o.values()), frame_objs=body, lens=85, fill=0.80, shift=0.15, fstop=2.4, pitch=3, focus_obj=o['FMA7205'])
    A.lights(C, c, 2.6, key=1.5, rim=1.3, fill=2.0)
    specs = [('надниркова залоза', 'FMA15629', 'L'), ('права нирка', 'FMA7204', 'L', (-0.1, 0, 0)), ('ниркова вена', 'FMA14335', 'L'),
             ('нижня порожниста вена', 'FMA10951', 'L', (0, 0, -1.0)), ('сечовід', 'FMA15571', 'L', (0, 0, -0.3)),
             ('аорта', 'FMA3784', 'R', (0, 0, -1.55)), ('ліва нирка', 'FMA7205', 'R', (0.1, 0, 0)), ('ниркова артерія', 'FMA14753', 'R'),
             ('спільна клубова артерія', 'FMA14766', 'R'), ('сечовий міхур', 'FMA15900', 'R')]
    return {'kicker': 'Сечова система', 'title': 'Нирки', 'sub': 'Нирки, сечоводи, сечовий міхур\nі судини, що їх живлять', 'scrim': 'left',
            'source': bp3d.CREDIT, 'labels': A.labels(specs, o, x_left=900, x_right=1520)}
