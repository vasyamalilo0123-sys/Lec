# Травна система на справжній анатомії (BodyParts3D).
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import abd_common as A
import bp3d


def build(C):
    C.set_world((0.0015, 0.0012, 0.0015))
    parts = {'FMA7131': 'esophagus', 'FMA7148': 'stomach', 'FMA7206': 'duodenum', 'FMA7207': 'jejunum', 'FMA7208': 'ileum',
             'FMA14543nsn': 'colon', 'FMA14544': 'rectum', 'FMA14542': 'colon', 'FMA7197': 'liver', 'FMA7202': 'gallbladder',
             'FMA7198nsn': 'pancreas', 'FMA7196': 'spleen'}
    o = A.load(C, parts)
    body = [v for k, v in o.items() if k != 'FMA7131']          # стравохід іде за верхній край кадру
    cam, c, d = A.front_cam(C, list(o.values()), frame_objs=body, lens=85, fill=0.84, shift=0.16, fstop=2.8, pitch=4, focus_obj=o['FMA7207'])
    A.lights(C, c, 3.0, key=1.6, rim=1.2, fill=2.0)
    specs = [('стравохід', 'FMA7131', 'R', (0, 0, -0.9)), ('шлунок', 'FMA7148', 'R', (0.2, 0, 0.1)), ('селезінка', 'FMA7196', 'R'),
             ('порожня кишка', 'FMA7207', 'R', (0.5, 0, 0.1)), ('ободова кишка', 'FMA14543nsn', 'R', (1.0, 0, -0.3)),
             ('пряма кишка', 'FMA14544', 'R', (0, 0, -0.3)),
             ('печінка', 'FMA7197', 'L', (-0.5, 0, 0.1)), ('жовчний міхур', 'FMA7202', 'L'),
             ('дванадцятипала кишка', 'FMA7206', 'L', (-0.4, 0, 0)), ('підшлункова залоза', 'FMA7198nsn', 'L'),
             ('клубова кишка', 'FMA7208', 'L', (-0.3, 0, -0.2)), ('апендикс', 'FMA14542', 'L')]
    return {'kicker': 'Травна система', 'title': 'Травний тракт', 'sub': 'Від стравоходу до прямої кишки', 'scrim': 'left',
            'source': bp3d.CREDIT, 'labels': A.labels(specs, o, x_left=900, x_right=1610)}
