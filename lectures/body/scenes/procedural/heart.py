# Серце: вид спереду (лівий бік пацієнта — праворуч у кадрі). Камера дивиться вздовж +Y, вісь Z — угору.
# make_heart() використовують також сцени ecg і body.
import math
import bpy
from mathutils import Vector


def bump_mat(C, m, scale=6.0, strength=0.25, detail=4.0, stretch=(1, 1, 1)):
    """Додає матеріалу дрібний рельєф (волокна, вологість)."""
    nt = m.node_tree; N, L = nt.nodes, nt.links
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = stretch
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    n = N.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail
    L.new(mp.outputs[0], n.inputs['Vector'])
    b = N.new('ShaderNodeBump'); b.inputs['Strength'].default_value = strength; b.inputs['Distance'].default_value = 0.05
    L.new(n.outputs['Fac'], b.inputs['Height']); L.new(b.outputs[0], N['P'].inputs['Normal'])
    return m


def mottle(C, m, c2, scale=2.5):
    """Плямистість кольору: домішує другий відтінок за шумом."""
    nt = m.node_tree; N, L = nt.nodes, nt.links
    tc = N.new('ShaderNodeTexCoord'); n = N.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = 5
    L.new(tc.outputs['Object'], n.inputs['Vector'])
    mix = N.new('ShaderNodeMixRGB'); mix.inputs['Color1'].default_value = N['P'].inputs['Base Color'].default_value
    mix.inputs['Color2'].default_value = (*c2, 1); L.new(n.outputs['Fac'], mix.inputs['Fac'])
    L.new(mix.outputs[0], N['P'].inputs['Base Color'])
    return m


def chain(a, b, ra, rb, n):
    """Ряд метакуль від a до b з радіусом від ra до rb."""
    a, b = Vector(a), Vector(b)
    return [(*a.lerp(b, i / (n - 1)), ra + (rb - ra) * i / (n - 1)) for i in range(n)]


# опорні точки (для підписів і провідної системи)
P = {
    'apex': (0.95, -0.25, -1.75), 'lv': (0.75, -0.55, -0.55), 'rv': (-0.45, -0.85, -0.45),
    'ra': (-1.15, -0.35, 0.55), 'la_aur': (1.05, -0.55, 0.78), 'ra_aur': (-0.55, -0.85, 0.82),
    'aorta': (-0.18, -0.35, 1.75), 'arch': (0.15, 0.1, 2.42), 'pt': (0.42, -0.62, 1.25), 'svc': (-1.0, 0.05, 2.0),
    'sa': (-1.0, -0.15, 1.05), 'av': (-0.2, 0.0, 0.35),
}


def heart_balls():
    balls = []
    balls += chain((0.45, 0.05, 0.2), (0.95, -0.25, -1.55), 1.6, 0.72, 7)          # лівий шлуночок до верхівки
    balls += chain((-0.55, -0.45, 0.1), (0.4, -0.55, -1.2), 1.35, 0.68, 6)       # правий шлуночок, спереду
    balls += [(-1.05, 0.0, 0.62, 0.95), (-0.95, 0.05, 1.0, 0.75)]                  # праве передсердя
    balls += [(0.45, 0.75, 0.8, 1.0), (0.95, 0.55, 0.75, 0.8)]                     # ліве передсердя (ззаду)
    balls += chain((-0.85, -0.45, 0.8), (-0.4, -0.78, 0.9), 0.55, 0.38, 3)        # праве вушко
    balls += chain((1.05, 0.1, 0.85), (1.0, -0.5, 0.82), 0.55, 0.36, 3)           # ліве вушко
    balls += [(0.2, -0.55, 0.55, 0.7)]                                             # артеріальний конус
    return balls


def aorta_path():
    return [(0.02, -0.2, 0.55), (-0.12, -0.35, 1.1), (-0.2, -0.33, 1.7), (-0.1, -0.15, 2.2), (0.2, 0.2, 2.45), (0.55, 0.6, 2.3),
            (0.72, 0.95, 1.8), (0.72, 1.1, 1.0), (0.65, 1.15, 0.0), (0.55, 1.15, -1.2), (0.5, 1.15, -4.5)]


def make_heart(C, muscle, artery, vein, pulm, coronary=None, cor_vein=None, res=0.07, vessels=True):
    """Будує серце довкола початку координат (висота ≈ 4.5). Повертає список об'єктів; перший — міокард."""
    objs = []
    body = C.metaballs('heart', heart_balls(), muscle, resolution=res, threshold=0.6)
    C.displace(body, 0.05, 0.35)
    objs.append(body)
    if not vessels:
        return objs
    ao = aorta_path()
    objs.append(C.tube('aorta', ao, 0.36, artery, radii=[1.1, 1.05, 1.0, 1.0, 1.0, 0.97, 0.92, 0.88, 0.85, 0.82, 0.8], res=12))
    for nm, a, b, r in (('brachioceph', (-0.02, -0.05, 2.3), (-0.6, -0.1, 5.0), 0.17),
                        ('carotid_l', (0.28, 0.25, 2.5), (0.3, 0.2, 5.0), 0.13),
                        ('subclav_l', (0.55, 0.55, 2.4), (1.25, 0.55, 5.0), 0.14)):
        a, b = Vector(a), Vector(b); mid = a.lerp(b, 0.5) + Vector((0, 0.05, 0.08))
        objs.append(C.tube(nm, [a - (b - a).normalized() * 0.2, a, mid, b], r, artery, res=10))
    # легеневий стовбур і його гілки
    objs.append(C.tube('pulm_trunk', [(0.15, -0.55, 0.5), (0.3, -0.68, 0.95), (0.48, -0.55, 1.4), (0.6, -0.15, 1.72), (0.62, 0.15, 1.78)], 0.36, pulm, res=12))
    objs.append(C.tube('pulm_l', [(0.55, 0.0, 1.72), (0.95, 0.3, 1.8), (1.6, 0.45, 1.85), (2.3, 0.5, 1.95)], 0.24, pulm, res=10))
    objs.append(C.tube('pulm_r', [(0.62, 0.1, 1.72), (0.2, 0.4, 1.62), (-0.7, 0.5, 1.6), (-1.6, 0.45, 1.65), (-2.2, 0.45, 1.7)], 0.24, pulm, res=10))
    # порожнисті вени
    objs.append(C.tube('svc', [(-1.0, 0.05, 0.9), (-1.02, 0.05, 1.6), (-1.0, 0.08, 2.4), (-0.95, 0.1, 5.0)], 0.3, vein, res=12))
    objs.append(C.tube('ivc', [(-0.95, 0.25, 0.3), (-0.95, 0.35, -0.6), (-0.9, 0.45, -1.6), (-0.85, 0.5, -4.5)], 0.3, vein, res=12))
    # легеневі вени (ззаду, ледь видно)
    for i, (x, z) in enumerate(((1.9, 1.0), (1.9, 0.55), (-1.9, 1.05), (-1.9, 0.6))):
        objs.append(C.tube(f'pv{i}', [(0.5 if x > 0 else 0.2, 0.9, 0.8), (x * 0.6, 0.95, z), (x, 0.9, z + 0.05)], 0.15, artery, res=8))
    if coronary:
        objs += coronaries(C, body, coronary, cor_vein)
    return objs


def snap(body, pts, lift=0.035):
    """Кладе ламану на поверхню серця (трохи над нею)."""
    out = []
    inv = body.matrix_world.inverted()
    for p in pts:
        ok, co, no, _ = body.closest_point_on_mesh(inv @ Vector(p))
        out.append(tuple(body.matrix_world @ (co + no * lift)))
    return out


def dense(pts, k=5):
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        a, b = Vector(a), Vector(b)
        out += [tuple(a.lerp(b, i / k)) for i in range(k)]
    return out + [tuple(pts[-1])]


def coronaries(C, body, art, vein=None):
    bpy.context.view_layer.update()
    objs = []

    def vessel(name, pts, r, m, taper=0.45):
        d = snap(body, dense(pts)); n = len(d)
        objs.append(C.tube(name, d, r, m, radii=[1 - (1 - taper) * i / (n - 1) for i in range(n)], res=6))

    # передня міжшлуночкова гілка лівої вінцевої артерії — по борозні між шлуночками до верхівки
    lad = [(0.72, -0.85, 0.62), (0.55, -1.2, 0.3), (0.45, -1.4, -0.15), (0.48, -1.35, -0.65), (0.62, -1.1, -1.15), (0.85, -0.7, -1.6)]
    vessel('lad', lad, 0.07, art)
    vessel('diag1', [(0.5, -1.3, 0.1), (0.85, -1.1, -0.2), (1.2, -0.75, -0.6), (1.35, -0.4, -1.0)], 0.045, art)
    vessel('diag2', [(0.47, -1.35, -0.5), (0.8, -1.1, -0.85), (1.05, -0.8, -1.25)], 0.035, art)
    vessel('sept', [(0.5, -1.3, -0.2), (0.2, -1.4, -0.5), (0.0, -1.3, -0.85)], 0.03, art)
    # огинаюча гілка — під лівим вушком уліво
    vessel('cx', [(0.72, -0.85, 0.62), (1.1, -0.6, 0.45), (1.5, -0.2, 0.35), (1.65, 0.3, 0.25)], 0.055, art)
    vessel('marg_l', [(1.4, -0.35, 0.38), (1.55, -0.3, -0.2), (1.5, -0.3, -0.8)], 0.035, art)
    # права вінцева артерія — по вінцевій борозні праворуч і вниз
    rca = [(-0.25, -0.95, 0.72), (-0.7, -1.05, 0.45), (-1.15, -0.9, 0.2), (-1.45, -0.55, -0.1), (-1.4, -0.3, -0.45), (-1.0, -0.2, -0.85)]
    vessel('rca', rca, 0.065, art)
    vessel('marg_r', [(-1.3, -0.75, 0.05), (-0.9, -1.1, -0.45), (-0.4, -1.2, -0.9), (0.1, -1.0, -1.3)], 0.04, art)
    vessel('conus', [(-0.5, -1.05, 0.55), (-0.3, -1.3, 0.2), (-0.1, -1.4, -0.2)], 0.03, art)
    if vein:
        vessel('great_vein', [(0.82, -0.75, -1.5), (0.7, -1.05, -1.0), (0.6, -1.3, -0.4), (0.62, -1.25, 0.15), (0.95, -0.8, 0.5), (1.45, -0.3, 0.42)], 0.055, vein, 1.4)
    return objs


def materials(C):
    muscle = C.mat('myocard', (0.30, 0.028, 0.024), rough=0.3, sss=0.6, sss_radius=(1.0, 0.25, 0.12), sss_scale=0.12, coat=0.7)
    mottle(C, muscle, (0.50, 0.09, 0.055), 1.8); bump_mat(C, muscle, 11.0, 0.6, 6.0, (1.0, 1.0, 0.3))
    artery = C.mat('artery', (0.58, 0.09, 0.06), rough=0.32, sss=0.5, sss_radius=(1.0, 0.3, 0.2), sss_scale=0.08, coat=0.6)
    bump_mat(C, artery, 5.0, 0.15)
    vein = C.mat('vein', (0.07, 0.12, 0.36), rough=0.32, sss=0.5, sss_radius=(0.3, 0.4, 1.0), sss_scale=0.08, coat=0.6)
    bump_mat(C, vein, 5.0, 0.15)
    pulm = C.mat('pulm', (0.10, 0.17, 0.42), rough=0.32, sss=0.5, sss_radius=(0.3, 0.4, 1.0), sss_scale=0.08, coat=0.6)
    bump_mat(C, pulm, 5.0, 0.15)
    cor = C.mat('coronary', (0.75, 0.10, 0.06), rough=0.3, coat=0.6, sss=0.3, sss_scale=0.03)
    corv = C.mat('cor_vein', (0.08, 0.12, 0.36), rough=0.3, coat=0.6, sss=0.3, sss_scale=0.03)
    return muscle, artery, vein, pulm, cor, corv


def build(C):
    C.set_world((0.004, 0.003, 0.004))
    muscle, artery, vein, pulm, cor, corv = materials(C)
    make_heart(C, muscle, artery, vein, pulm, cor, corv)
    C.cam(50, (0.05, -17.0, 0.95), (0.05, 0, 0.8), fstop=1.6, focus=15.9)
    C.area('key', (-5, -7, 6), (0, 0, 0.5), 6, 1500, (1.0, 0.95, 0.9))
    C.area('rim', (6, 5, 4), (0, 0, 0.5), 5, 4200, (1.0, 0.62, 0.48))
    C.area('rim2', (-6, 5, -1), (0, 0, 0.3), 5, 2600, (0.45, 0.6, 1.0))
    C.area('fill', (4, -8, -4), (0, 0, 0), 8, 420, (0.7, 0.8, 1.0))
    return {
        'kicker': 'Серцево-судинна система', 'title': 'Серце', 'sub': 'Вид спереду', 'scrim': 'none', 'title_at': [96, 96],
        'labels': [
            {'text': 'верхня порожниста вена', 'p': (-1.25, -0.15, 2.5), 'at': [560, 330], 'align': 'right'},
            {'text': 'праве передсердя', 'p': (-1.5, -0.5, 0.75), 'at': [560, 520], 'align': 'right'},
            {'text': 'права вінцева артерія', 'p': (-1.2, -0.95, 0.2), 'at': [560, 640], 'align': 'right'},
            {'text': 'правий шлуночок', 'p': (-0.55, -1.25, -0.4), 'at': [560, 760], 'align': 'right'},
            {'text': 'дуга аорти', 'p': (0.3, -0.1, 2.75), 'at': [1360, 180], 'align': 'left'},
            {'text': 'легеневий стовбур', 'p': (0.6, -0.8, 1.3), 'at': [1360, 420], 'align': 'left'},
            {'text': 'ліве вушко', 'p': (1.25, -0.7, 0.85), 'at': [1360, 530], 'align': 'left'},
            {'text': 'передня міжшлуночкова гілка', 'p': (0.47, -1.5, -0.4), 'at': [1360, 650], 'align': 'left'},
            {'text': 'лівий шлуночок', 'p': (1.3, -0.9, -0.7), 'at': [1360, 760], 'align': 'left'},
            {'text': 'верхівка', 'p': (0.98, -0.6, -1.9), 'at': [1360, 870], 'align': 'left'},
        ],
    }
