# Усі органи: напівпрозорий «рентген»-торс і кольорові органи всередині. Вид спереду: лівий бік пацієнта — праворуч.
import math, os, random, importlib.util
import bpy
from mathutils import Vector

_spec = importlib.util.spec_from_file_location('heart_scene', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'heart.py'))
H = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(H)


def organ(C, name, color, c2=None, bump=6.0, bstr=0.3, rough=0.32, sss_radius=(1.0, 0.35, 0.2)):
    m = C.mat(name, color, rough=rough, sss=0.5, sss_radius=sss_radius, sss_scale=0.06, coat=0.55)
    if c2: H.mottle(C, m, c2, 3.0)
    H.bump_mat(C, m, bump, bstr)
    return m


def torso_balls():
    b = [(0, 0, 4.55, 2.0, (0.82, 0.95, 1.05)), (0, -0.2, 3.85, 1.35, (0.8, 0.9, 0.9)),      # голова, щелепа
         (0, 0.05, 3.05, 1.05), (0, 0.05, 2.75, 1.15)]                                           # шия
    for s in (-1, 1):
        b += [(s * 0.8, 0, 1.75, 2.35), (s * 0.75, 0, 0.75, 2.2), (s * 1.75, 0, 2.3, 1.45),    # грудна клітка, плече
              (s * 0.65, 0, -0.35, 2.05), (s * 0.7, 0, -1.4, 2.05), (s * 0.85, 0, -2.4, 2.2),      # живіт, таз
              (s * 1.0, 0, -3.6, 1.75), (s * 1.05, 0, -4.8, 1.6)]                                   # стегна
    b += [(0, 0, 2.1, 2.2), (0, 0, 0.2, 2.0)]
    return b


def bumpy_tube(C, name, pts, r, m, period=7, amp=0.16, res=10, k=6):
    """Трубка з перетяжками (гаустри товстої кишки)."""
    d = H.dense(pts, k); n = len(d)
    radii = [1 + amp * math.sin(2 * math.pi * i / period) for i in range(n)]
    return C.tube(name, d, r, m, radii=radii, res=res)


def build(C):
    C.set_world((0.002, 0.004, 0.008))
    rnd = random.Random(5)
    shell = C.mat_xray('skin', (0.3, 0.6, 1.0), strength=1.5, power=2.6, base=0.006)
    C.metaballs('torso', torso_balls(), shell, resolution=0.14, threshold=0.6)
    for sd in (-1, 1):       # руки окремими оболонками, щоб не зливалися з тулубом
        C.metaballs(f'arm{sd}', [(sd * (2.5 + 0.75 * i / 15), -0.3 * i / 15, 2.05 - 6.9 * i / 15, 1.12 - 0.34 * i / 15) for i in range(16)],
                    shell, resolution=0.14, threshold=0.6)

    # мозок
    brain_m = organ(C, 'brain', (0.62, 0.42, 0.40), (0.5, 0.3, 0.3), 3.0, 0.2)
    for s in (-1, 1):
        hemi = C.prim('ico', f'brain{s}', brain_m, loc=(s * 0.4, 0.0, 4.82), scale=(0.44, 0.88, 0.62), subdiv=5)
        C.displace(hemi, 0.14, 0.2, 'VORONOI')
    C.prim('ico', 'cerebellum', brain_m, loc=(0, 0.55, 4.25), scale=(0.5, 0.32, 0.22), subdiv=4)
    C.tube('brainstem', [(0, 0.2, 4.45), (0, 0.22, 4.15), (0, 0.25, 3.9)], 0.11, brain_m)

    # трахея, бронхи, легені
    air = organ(C, 'airway', (0.7, 0.62, 0.55), None, 14.0, 0.5)
    bumpy_tube(C, 'trachea', [(0, -0.1, 3.3), (0, -0.05, 2.9), (0, 0.05, 2.45), (0, 0.1, 2.15)], 0.14, air, period=4, amp=0.1, k=10)
    C.prim('sphere', 'larynx', air, loc=(0, -0.12, 3.36), scale=(0.19, 0.17, 0.2), u=24, v=12)
    C.tube('bronch_r', [(0, 0.1, 2.2), (-0.3, 0.1, 1.95), (-0.6, 0.1, 1.75)], 0.1, air)
    C.tube('bronch_l', [(0, 0.1, 2.2), (0.35, 0.1, 1.95), (0.65, 0.1, 1.7)], 0.1, air)
    lung_m = organ(C, 'lung', (0.60, 0.40, 0.46), (0.45, 0.28, 0.36), 10.0, 0.35)
    r_lung = [(-0.95, 0.1, 2.35, 0.95), (-1.1, 0.1, 1.75, 1.25), (-1.15, 0.1, 1.1, 1.35), (-1.1, 0.1, 0.8, 1.15)]
    l_lung = [(0.95, 0.1, 2.35, 0.95), (1.15, 0.1, 1.75, 1.2), (1.3, 0.15, 1.1, 1.2), (1.3, 0.15, 0.8, 1.05)]     # лівою серцева вирізка
    for nm, balls in (('lung_r', r_lung), ('lung_l', l_lung)):
        o = C.metaballs(nm, balls, lung_m, resolution=0.07)
        C.displace(o, 0.03, 0.2)

    # серце (зменшена модель із сцени heart)
    muscle, artery, vein, pulm, cor, corv = H.materials(C)
    hobjs = H.make_heart(C, muscle, artery, vein, pulm, vessels=True)
    emp = C.link(bpy.data.objects.new('heart_root', None))
    for o in hobjs:
        if o.name.startswith(('pulm_l', 'pulm_r', 'pv', 'ivc')):
            bpy.data.objects.remove(o); continue
        o.parent = emp
    emp.location = (0.22, -0.55, 1.2); emp.scale = (0.33,) * 3

    # стравохід і шлунок
    gut = organ(C, 'stomach', (0.72, 0.5, 0.3), (0.6, 0.36, 0.22), 8.0, 0.3)
    C.tube('esoph', [(0, 0.25, 3.25), (0.02, 0.3, 2.2), (0.1, 0.3, 1.0), (0.3, 0.1, 0.45)], 0.07, gut)
    st = [(0.3, 0.05, 0.5), (0.62, 0.0, 0.52), (1.0, -0.05, 0.3), (1.08, -0.05, -0.1), (0.85, -0.05, -0.42), (0.45, -0.05, -0.5), (0.1, -0.05, -0.42)]
    C.tube('stomach', st, 0.26, gut, radii=[0.45, 1.0, 1.35, 1.35, 1.1, 0.75, 0.45], res=12)
    # печінка
    liver_m = organ(C, 'liver', (0.17, 0.028, 0.02), (0.24, 0.05, 0.03), 12.0, 0.2, rough=0.25)
    C.metaballs('liver', [(-1.05, -0.1, 0.1, 1.25), (-0.6, -0.15, 0.12, 1.1), (-0.15, -0.2, 0.15, 0.85), (0.25, -0.2, 0.22, 0.6),
                          (-1.15, -0.05, -0.3, 0.85)], liver_m, resolution=0.06)
    gb = organ(C, 'gallbladder', (0.25, 0.42, 0.18))
    C.prim('sphere', 'gallbladder', gb, loc=(-0.62, -0.42, -0.36), scale=(0.1, 0.1, 0.17), u=24, v=12)
    # селезінка
    C.prim('ico', 'spleen', organ(C, 'spleen', (0.2, 0.03, 0.14), (0.3, 0.06, 0.2)), loc=(1.52, 0.05, 0.12), scale=(0.24, 0.3, 0.42),
           rot=(0, math.radians(-20), 0), subdiv=4)
    # нирки й сечоводи
    kid = organ(C, 'kidney', (0.30, 0.06, 0.04), (0.4, 0.1, 0.07), 9.0, 0.2)
    ur = organ(C, 'ureter', (0.75, 0.62, 0.4))
    for s, z in ((-1, -0.95), (1, -0.85)):
        C.metaballs(f'kidney{s}', [(s * 1.12, 0.35, z + 0.2, 0.5), (s * 1.18, 0.35, z, 0.5), (s * 1.12, 0.35, z - 0.2, 0.5)], kid, resolution=0.05)
        C.tube(f'ureter{s}', [(s * 0.98, 0.35, z), (s * 0.8, 0.35, z - 0.5), (s * 0.55, 0.2, z - 1.4), (s * 0.15, 0.0, -2.95)], 0.035, ur)
    # товста кишка: сліпа, висхідна, поперечна, низхідна, сигмоподібна, пряма
    colon_m = organ(C, 'colon', (0.56, 0.30, 0.25), (0.45, 0.22, 0.2), 7.0, 0.3)
    colon = [(-1.25, -0.1, -2.45), (-1.3, -0.1, -2.0), (-1.3, -0.1, -1.5), (-1.25, -0.15, -1.2), (-0.9, -0.3, -1.15), (-0.3, -0.35, -1.35), (0.35, -0.35, -1.35),
             (0.95, -0.3, -1.15), (1.3, -0.15, -1.15), (1.35, -0.1, -1.6), (1.33, -0.1, -2.1), (1.1, -0.05, -2.5), (0.6, 0.0, -2.6), (0.25, 0.1, -2.75), (0.05, 0.25, -3.2)]
    bumpy_tube(C, 'colon', colon, 0.2, colon_m)
    # тонка кишка: петлі всередині рамки товстої
    small_m = organ(C, 'small', (0.78, 0.52, 0.42), (0.68, 0.4, 0.34), 9.0, 0.25)
    pts = []; x, z, d = -0.85, -1.62, 1
    while z > -2.55:
        for i in range(5):
            u = i / 4
            pts.append((x + d * 1.7 * u, -0.28 + 0.12 * math.sin(u * 9 + z * 5) + rnd.uniform(-0.03, 0.03), z - 0.02 * i + 0.07 * math.sin(u * 12 + z * 3)))
        x += d * 1.7; d = -d; z -= 0.185
    C.tube('small', [(0.2, -0.1, -0.5)] + pts + [(-1.2, -0.1, -2.3)], 0.105, small_m, res=8)
    # сечовий міхур
    C.prim('sphere', 'bladder', organ(C, 'bladder', (0.78, 0.62, 0.3), None, 5.0, 0.15), loc=(0, -0.25, -3.05), scale=(0.33, 0.28, 0.26), u=32, v=16)

    C.cam(50, (0.0, -24.0, 1.1), (0.0, 0, 1.1), fstop=None)
    C.area('key', (-6, -10, 8), (0, 0, 0.5), 8, 3400, (1.0, 0.96, 0.92))
    C.area('rim', (7, 4, 5), (0, 0, 0.5), 6, 6500, (0.5, 0.7, 1.0))
    C.area('fill', (5, -10, -4), (0, 0, 0), 9, 1300, (1.0, 0.8, 0.7))

    L, R = 640, 1280
    return {
        'kicker': 'Анатомія', 'title': 'Тіло людини', 'sub': 'Органи голови, грудної\nта черевної порожнин', 'scrim': 'none', 'title_at': [96, 96],
        'labels': [
            {'text': 'легені', 'p': (-1.45, -0.6, 1.5), 'at': [L, 430], 'align': 'right'},
            {'text': 'печінка', 'p': (-1.3, -0.75, 0.1), 'at': [L, 560], 'align': 'right'},
            {'text': 'жовчний міхур', 'p': (-0.62, -0.52, -0.42), 'at': [L, 650], 'align': 'right'},
            {'text': 'нирки', 'p': (-1.25, 0.1, -0.95), 'at': [L, 740], 'align': 'right'},
            {'text': 'товста кишка', 'p': (-1.38, -0.3, -1.8), 'at': [L, 830], 'align': 'right'},
            {'text': 'сечовий міхур', 'p': (-0.15, -0.5, -3.05), 'at': [L, 960], 'align': 'right'},
            {'text': 'головний мозок', 'p': (0.6, -0.7, 4.9), 'at': [R, 150], 'align': 'left'},
            {'text': 'трахея', 'p': (0.1, -0.25, 3.05), 'at': [R, 330], 'align': 'left'},
            {'text': 'серце', 'p': (0.5, -0.9, 1.05), 'at': [R, 470], 'align': 'left'},
            {'text': 'шлунок', 'p': (1.05, -0.4, 0.1), 'at': [R, 580], 'align': 'left'},
            {'text': 'селезінка', 'p': (1.68, -0.15, 0.1), 'at': [R, 670], 'align': 'left'},
            {'text': 'тонка кишка', 'p': (0.6, -0.4, -2.0), 'at': [R, 830], 'align': 'left'},
        ],
    }
