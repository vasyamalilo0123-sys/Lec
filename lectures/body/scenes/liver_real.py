# Верхній поверх черевної порожнини крупним планом (BodyParts3D): печінка, жовчний міхур, шлунок, підшлункова, дванадцятипала, селезінка.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import abd_common as A
import bp3d


def build(C):
    C.set_world((0.0015, 0.0012, 0.0015))
    parts = {'FMA7197': 'liver', 'FMA7202': 'gallbladder', 'FMA7148': 'stomach', 'FMA7198nsn': 'pancreas', 'FMA7206': 'duodenum',
             'FMA7196': 'spleen', 'FMA7131': 'esophagus', 'FMA14771': 'artery', 'FMA14773': 'artery', 'FMA50737': 'artery',
             'FMA14768': 'artery', 'FMA14331': 'vein', 'FMA14332': 'vein', 'FMA14749': 'artery'}
    o = A.load(C, parts)
    body = [o[k] for k in ('FMA7197', 'FMA7148', 'FMA7198nsn', 'FMA7206', 'FMA7196')]
    cam, c, d = A.front_cam(C, list(o.values()), frame_objs=body, lens=100, fill=0.66, shift=0.14, fstop=2.8, yaw=14, pitch=-7,
                            focus_obj=o['FMA7148'])
    A.lights(C, c, 2.0, key=1.5, rim=1.3, fill=2.0)
    specs = [('печінка', 'FMA7197', 'L', (-0.4, 0, 0.2)), ('жовчний міхур', 'FMA7202', 'L'), ('дванадцятипала кишка', 'FMA7206', 'L', (-0.3, 0, -0.2)),
             ('стравохід', 'FMA7131', 'R', (0, 0, -1.0)), ('шлунок', 'FMA7148', 'R', (0.2, 0, 0.1)), ('селезінка', 'FMA7196', 'R'),
             ('селезінкова артерія', 'FMA14773', 'R'), ('підшлункова залоза', 'FMA7198nsn', 'R')]
    return {'kicker': 'Травна система', 'title': 'Печінка', 'sub': 'Верхній поверх\nчеревної порожнини', 'scrim': 'left',
            'source': bp3d.CREDIT, 'labels': A.labels(specs, o, x_left=800, x_right=1570)}
