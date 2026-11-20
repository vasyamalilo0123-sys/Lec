# Справжня анатомія: сітки BodyParts3D (DBCLS, CC BY-SA 2.1 Japan), зняті з томографії. Самі файли в репозиторій не кладемо:
#   git clone --depth 1 https://github.com/Kevin-Mattheus-Moerman/BodyParts3D  і вказати BP3D=<шлях>/assets/BodyParts3D_data
import bpy, bmesh, os
from mathutils import Vector
ROOT = os.environ.get('BP3D', '/tmp/claude-0/-home-user-Lec/c994ffbc-a2cd-5240-99d0-10fbc375d8fd/scratchpad/assets/bp3d/assets/BodyParts3D_data')
CREDIT = 'Анатомічні моделі: BodyParts3D, © The Database Center for Life Science, CC BY-SA 2.1 Japan'
SCALE = 0.01   # міліметри атласу → одиниця сцени = 10 см


def load(fma, material=None, name=None, smooth_angle=None):
    """Завантажує частину тіла за ідентифікатором FMA. Зварює вершини, щоб згладжування працювало."""
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=os.path.join(ROOT, 'stl', fma + '.stl'), global_scale=SCALE)
    o = (set(bpy.data.objects) - before).pop(); o.name = name or fma
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    for f in bm.faces: f.smooth = True
    bm.to_mesh(o.data); bm.free()
    o.data.materials.clear()
    if material: o.data.materials.append(material)
    o.select_set(False)
    return o


def recenter(objs, anchor):
    """Зсуває всі об'єкти так, щоб центр anchor опинився в нулі. Повертає зсув."""
    bb = [anchor.matrix_world @ Vector(c) for c in anchor.bound_box]
    c = sum(bb, Vector()) / 8
    for o in objs: o.location -= c
    bpy.context.view_layer.update()
    return c


def bbox(o):
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb))), Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))


NAMES = {}
_pl = os.path.join(ROOT, 'parts_list_e.txt')
if os.path.exists(_pl):
    for _l in open(_pl, encoding='utf-8'):
        _a = _l.rstrip('\n').split('\t')
        if len(_a) >= 2: NAMES[_a[0].strip('"')] = _a[1]


def find(pattern, exclude=None):
    """Частини атласу, що мають сітку: [(ідентифікатор, англійська назва FMA, розмір файлу в кБ)], за регулярним виразом у назві."""
    import re
    out = []
    for f in sorted(os.listdir(os.path.join(ROOT, 'stl'))):
        k = f[:-4]; n = NAMES.get(k, '?')
        if re.search(pattern, n) and not (exclude and re.search(exclude, n)):
            out.append((k, n, os.path.getsize(os.path.join(ROOT, 'stl', f)) // 1000))
    return out


def load_many(parts, anchor=None):
    """parts: {ідентифікатор: матеріал}. Завантажує все й центрує за anchor (ідентифікатор) або за спільним центром. Повертає {id: об'єкт}."""
    objs = {k: load(k, m) for k, m in parts.items()}
    if anchor:
        recenter(list(objs.values()), objs[anchor])
    else:
        los, his = zip(*[bbox(o) for o in objs.values()])
        c = (Vector((min(v.x for v in los), min(v.y for v in los), min(v.z for v in los))) + Vector((max(v.x for v in his), max(v.y for v in his), max(v.z for v in his)))) / 2
        for o in objs.values(): o.location -= c
        bpy.context.view_layer.update()
    return objs


def front_point(obj, cam=None, bias=(0, 0, 0)):
    """Точка на поверхні об'єкта, звернена до камери, біля його центру (+bias у одиницях сцени) — якір для виноски підпису."""
    cam = cam or bpy.context.scene.camera
    lo, hi = bbox(obj); c = (lo + hi) / 2 + Vector(bias); eye = cam.matrix_world.translation
    d = (c - eye).normalized(); r = max((hi - lo).length * 0.06, 0.02)
    mw = obj.matrix_world; best = None
    step = max(1, len(obj.data.vertices) // 60000)
    for i in range(0, len(obj.data.vertices), step):
        v = obj.data.vertices[i]
        w = mw @ v.co; t = (w - eye).dot(d); off = ((w - eye) - d * t).length
        if off < r and (best is None or t < best[0]): best = (t, w)
    return tuple(best[1]) if best else tuple(c)


def flesh(C, name, c1, c2, rough=0.38, sss=0.9, scale=0.012, bump=0.25, noise=28.0, coat=0.45):
    """Жива тканина: два відтінки за шумом, дрібний рельєф, підповерхневе розсіювання, волога плівка."""
    m = C.mat(name, c1, rough=rough, sss=sss, sss_radius=(1.0, 0.25, 0.12), sss_scale=scale, coat=coat)
    nt = m.node_tree; N, L = nt.nodes, nt.links; P = N['P']
    tc = N.new('ShaderNodeTexCoord')
    n1 = N.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = noise * 0.25; n1.inputs['Detail'].default_value = 8
    n2 = N.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = noise * 4; n2.inputs['Detail'].default_value = 6
    L.new(tc.outputs['Object'], n1.inputs['Vector']); L.new(tc.outputs['Object'], n2.inputs['Vector'])
    mix = N.new('ShaderNodeMixRGB'); mix.inputs['Color1'].default_value = (*c1, 1); mix.inputs['Color2'].default_value = (*c2, 1)
    cr = N.new('ShaderNodeMapRange'); cr.inputs['From Min'].default_value = 0.35; cr.inputs['From Max'].default_value = 0.7
    L.new(n1.outputs['Fac'], cr.inputs['Value']); L.new(cr.outputs[0], mix.inputs['Fac']); L.new(mix.outputs[0], P.inputs['Base Color'])
    h = N.new('ShaderNodeMath'); h.operation = 'MULTIPLY_ADD'; h.inputs[1].default_value = 0.4
    L.new(n2.outputs['Fac'], h.inputs[0]); L.new(n1.outputs['Fac'], h.inputs[2])
    b = N.new('ShaderNodeBump'); b.inputs['Strength'].default_value = bump; b.inputs['Distance'].default_value = 0.02
    L.new(h.outputs[0], b.inputs['Height']); L.new(b.outputs[0], P.inputs['Normal'])
    rr = N.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = rough - 0.12; rr.inputs['To Max'].default_value = rough + 0.15
    L.new(n2.outputs['Fac'], rr.inputs['Value']); L.new(rr.outputs[0], P.inputs['Roughness'])
    return m
