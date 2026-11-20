# Легені на справжній анатомії (BodyParts3D): напівпрозорі частки, всередині трахея й бронхіальне дерево, знизу діафрагма.
import bpy, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bp3d, _layout as LY


def build(C):
    C.set_world((0.0015, 0.0012, 0.0015))
    F = bp3d.flesh
    def lobe(name, c1, c2):
        return LY.see_through(F(C, name, c1, c2, rough=0.45, sss=0.8, scale=0.02, bump=0.35, noise=22, coat=0.35), power=1.5, base=0.07, top=0.95)
    ru = lobe('ru', (0.62, 0.30, 0.30), (0.74, 0.44, 0.42)); rm = lobe('rm', (0.66, 0.36, 0.30), (0.78, 0.50, 0.42))
    rl = lobe('rl', (0.56, 0.26, 0.28), (0.68, 0.38, 0.38)); lu = lobe('lu', (0.62, 0.30, 0.30), (0.74, 0.44, 0.42))
    ll = lobe('ll', (0.56, 0.26, 0.28), (0.68, 0.38, 0.38))
    airway = F(C, 'airway', (0.80, 0.66, 0.52), (0.90, 0.80, 0.68), rough=0.4, sss=0.5, scale=0.01, bump=0.3, noise=50, coat=0.3)
    dia = F(C, 'dia', (0.30, 0.05, 0.04), (0.45, 0.10, 0.08), rough=0.45, bump=0.3, noise=18)
    parts = {'FMA7333': ru, 'FMA7383': rm, 'FMA7337': rl, 'FMA7370': lu, 'FMA7371': ll, 'FMA7409': airway, 'FMA7394': airway, 'FMA13295': dia}
    objs = bp3d.load_many(parts, anchor='FMA7409')
    lo, hi = bp3d.bbox(objs['FMA7333']); print('RU lobe bbox', tuple(round(v, 2) for v in lo), tuple(round(v, 2) for v in hi))
    C.cam(85, (1.6, -16.5, 1.4), (-0.95, 0, -0.1), fstop=2.0, focus=16.2)
    vp = LY.visible_point
    items = [('трахея', vp(objs['FMA7394'], (0, 0, 0.3)), 'R'),
             ('бронхи', vp(objs['FMA7409'], (0.45, 0, -0.2)), 'R'),
             (('верхня частка', 'права легеня'), vp(objs['FMA7333']), 'L'),
             (('середня частка', 'права легеня'), vp(objs['FMA7383']), 'L'),
             (('нижня частка', 'права легеня'), vp(objs['FMA7337'], (-0.35, 0, -0.55)), 'L'),
             (('верхня частка', 'ліва легеня'), vp(objs['FMA7370']), 'R'),
             (('нижня частка', 'ліва легеня'), vp(objs['FMA7371'], (0, 0, -0.3)), 'R'),
             ('діафрагма', vp(objs['FMA13295'], (-0.8, 0, 0)), 'L')]
    labels = LY.columns(items, 1050, 740, 1580, left_y=(400, 900), right_y=(150, 900), min_gap=90)
    LY.lights(C, 1.8, target=(0, 0, 0))
    return {'kicker': 'Дихальна система', 'title': 'Легені', 'sub': 'Вид спереду', 'scrim': 'left', 'source': bp3d.CREDIT, 'labels': labels}
