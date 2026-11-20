# Спільне для кадрів черевної порожнини: палітра живих тканин, камера за габаритами, розкладка підписів без перетинів.
import bpy, sys, os, math
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bp3d

# (темніший відтінок, світліший відтінок, шорсткість, SSS, рельєф, масштаб шуму)
PAL = {
    'liver': ((0.24, 0.045, 0.035), (0.36, 0.09, 0.06), 0.34, 0.8, 0.12, 22),
    'gallbladder': ((0.12, 0.22, 0.07), (0.22, 0.32, 0.11), 0.30, 0.8, 0.10, 40),
    'stomach': ((0.66, 0.32, 0.29), (0.78, 0.47, 0.41), 0.40, 0.9, 0.22, 26),
    'esophagus': ((0.62, 0.30, 0.28), (0.72, 0.42, 0.37), 0.42, 0.9, 0.2, 40),
    'duodenum': ((0.70, 0.40, 0.33), (0.79, 0.52, 0.42), 0.40, 0.9, 0.25, 34),
    'jejunum': ((0.70, 0.27, 0.25), (0.80, 0.40, 0.36), 0.38, 0.9, 0.28, 34),
    'ileum': ((0.76, 0.47, 0.41), (0.85, 0.60, 0.52), 0.38, 0.9, 0.28, 34),
    'colon': ((0.56, 0.36, 0.34), (0.68, 0.48, 0.44), 0.42, 0.9, 0.3, 24),
    'rectum': ((0.58, 0.30, 0.29), (0.68, 0.40, 0.36), 0.42, 0.9, 0.25, 30),
    'pancreas': ((0.74, 0.52, 0.30), (0.84, 0.66, 0.42), 0.46, 0.8, 0.45, 70),
    'spleen': ((0.20, 0.035, 0.08), (0.32, 0.07, 0.13), 0.33, 0.8, 0.12, 26),
    'kidney': ((0.34, 0.075, 0.055), (0.46, 0.13, 0.09), 0.32, 0.85, 0.12, 30),
    'adrenal': ((0.70, 0.46, 0.16), (0.80, 0.58, 0.26), 0.45, 0.7, 0.4, 70),
    'ureter': ((0.76, 0.56, 0.46), (0.84, 0.68, 0.58), 0.40, 0.8, 0.15, 60),
    'bladder': ((0.72, 0.44, 0.36), (0.82, 0.58, 0.48), 0.40, 0.9, 0.2, 30),
    'artery': ((0.50, 0.03, 0.025), (0.62, 0.06, 0.04), 0.30, 0.9, 0.1, 60),
    'vein': ((0.10, 0.06, 0.16), (0.16, 0.08, 0.20), 0.32, 0.9, 0.1, 60),
    'aorta': ((0.56, 0.16, 0.13), (0.68, 0.28, 0.22), 0.38, 0.7, 0.15, 40),
    'cava': ((0.14, 0.09, 0.22), (0.22, 0.13, 0.28), 0.38, 0.7, 0.15, 40),
}


def tissue(C, key, dim=1.0):
    c1, c2, rough, sss, bump, noise = PAL[key]
    return bp3d.flesh(C, key, tuple(v * dim for v in c1), tuple(v * dim for v in c2), rough=rough, sss=sss, bump=bump, noise=noise)


def load(C, parts, subsurf=1):
    """parts: {ідентифікатор FMA: ключ палітри або (ключ, приглушення)}. Центрує за спільними габаритами, згладжує грубі сітки."""
    mats = {}
    def m(v):
        key, dim = (v, 1.0) if isinstance(v, str) else v
        if (key, dim) not in mats: mats[(key, dim)] = tissue(C, key, dim)
        return mats[(key, dim)]
    objs = bp3d.load_many({k: m(v) for k, v in parts.items()})
    if subsurf:
        for o in objs.values():
            if len(o.data.polygons) < 25000:
                s = o.modifiers.new('sub', 'SUBSURF'); s.levels = subsurf; s.render_levels = subsurf
    bpy.context.view_layer.update()
    return objs


def bounds(objs):
    los, his = zip(*[bp3d.bbox(o) for o in objs])
    return (Vector((min(v.x for v in los), min(v.y for v in los), min(v.z for v in los))),
            Vector((max(v.x for v in his), max(v.y for v in his), max(v.z for v in his))))


def front_cam(C, objs, lens=85, frame_objs=None, fill=0.80, shift=0.17, fstop=2.0, yaw=0.0, pitch=0.0, focus_obj=None, dz=0.0):
    """Камера спереду (з боку −Y): об'єкти займають частку fill висоти кадру і зсунуті праворуч на shift ширини кадру.
    yaw/pitch (градуси) — невеликий обхід довкола центру."""
    lo, hi = bounds(frame_objs or objs); c = (lo + hi) / 2; H = hi.z - lo.z; W = hi.x - lo.x
    half_v = math.atan(18 * 9 / 16 / lens); half_h = math.atan(18 / lens)
    d = max(H / 2 / fill / math.tan(half_v), W / 2 / (fill * 0.62) / math.tan(half_h)) + (hi.y - lo.y) / 2
    fw = 2 * d * math.tan(half_h)
    ya, pa = math.radians(yaw), math.radians(pitch)
    dirv = Vector((math.sin(ya) * math.cos(pa), -math.cos(ya) * math.cos(pa), math.sin(pa)))
    right = Vector((math.cos(ya), math.sin(ya), 0))
    tgt = c - right * (shift * fw) + Vector((0, 0, dz))
    eye = tgt + dirv * d
    fp = None
    cam = C.cam(lens, tuple(eye), tuple(tgt), fstop=fstop)
    bpy.context.view_layer.update()
    if focus_obj is not None:
        fp = Vector(bp3d.front_point(focus_obj, cam))
        cam.data.dof.focus_distance = (fp - eye).dot(-dirv)
    else:
        cam.data.dof.focus_distance = d - (hi.y - lo.y) * 0.30
    return cam, c, d


def lights(C, c, size, key=1.0, rim=1.0, fill=1.0):
    """Ключове зліва-згори спереду, холодний контровий справа ззаду, теплий контровий зліва ззаду, слабке заповнення."""
    s = size; k = s * s
    C.area('key', (c.x - 1.3 * s, c.y - 1.5 * s, c.z + 1.3 * s), tuple(c), 0.8 * s, 60 * k * key, (1.0, 0.93, 0.86))
    C.area('rim', (c.x + 1.4 * s, c.y + 1.3 * s, c.z + 0.9 * s), tuple(c), 0.7 * s, 300 * k * rim, (0.7, 0.82, 1.0))
    C.area('rim2', (c.x - 1.2 * s, c.y + 1.4 * s, c.z - 0.5 * s), tuple(c), 0.8 * s, 130 * k * rim, (1.0, 0.5, 0.35))
    C.area('fill', (c.x + 1.0 * s, c.y - 1.5 * s, c.z - 1.0 * s), tuple(c), 1.4 * s, 4 * k * fill, (0.6, 0.7, 1.0))


def px(p):
    sc = bpy.context.scene
    v = world_to_camera_view(sc, sc.camera, Vector(p))
    return v.x * 1920, (1 - v.y) * 1080


def layout(items, x_left=820, x_right=1690, y_min=150, y_max=930, gap=74):
    """items: [(текст, точка 3D, 'L' | 'R', sub або None)]. Підписи стають стовпцями ліворуч і праворуч від об'єкта
    в порядку висоти своїх точок — так виноски не перетинаються."""
    out = []
    for side, x, align in (('L', x_left, 'right'), ('R', x_right, 'left')):
        col = sorted([it for it in items if it[2] == side], key=lambda it: px(it[1])[1])
        if not col: continue
        ys = [px(it[1])[1] - 18 for it in col]
        for i in range(1, len(ys)): ys[i] = max(ys[i], ys[i - 1] + gap)      # розсунути вниз
        over = ys[-1] - y_max
        if over > 0: ys = [y - over for y in ys]
        for i in range(len(ys) - 2, -1, -1): ys[i] = min(ys[i], ys[i + 1] - gap)
        if ys[0] < y_min:
            ys = [y + (y_min - ys[0]) for y in ys]
        for it, y in zip(col, ys):
            lb = {'text': it[0], 'p': tuple(it[1]), 'at': [x, round(y)], 'align': align}
            if len(it) > 3 and it[3]: lb['sub'] = it[3]
            out.append(lb)
    return out


def visible_point(obj, bias=None, samples=900):
    """Точка поверхні obj, яку справді видно з камери (перевірка променем). Без bias — біля середини видимої частини органа,
    з bias — найближча в кадрі до центру габаритів + bias. Повертає None, якщо орган повністю закритий іншими."""
    sc = bpy.context.scene; cam = sc.camera; dg = bpy.context.evaluated_depsgraph_get()
    eye = cam.matrix_world.translation
    mw = obj.matrix_world; vs = obj.data.vertices; step = max(1, len(vs) // samples)
    vis = []
    for i in range(0, len(vs), step):
        w = mw @ vs[i].co; x, y = px(w)
        if not (40 < x < 1880 and 40 < y < 1040): continue
        dvec = (w - eye); dist = dvec.length
        hit, loc, nor, idx, hobj, _ = sc.ray_cast(dg, eye, dvec / dist, distance=dist + 1.0)
        if hit and hobj.name == obj.name and (loc - w).length < 0.03: vis.append((x, y, w))
    if not vis: return None
    if bias is None:
        tx = sum(v[0] for v in vis) / len(vis); ty = sum(v[1] for v in vis) / len(vis)
    else:
        lo, hi = bp3d.bbox(obj); tx, ty = px((lo + hi) / 2 + Vector(bias))
    return tuple(min(vis, key=lambda v: (v[0] - tx) ** 2 + (v[1] - ty) ** 2)[2])


def labels(specs, objs, **kw):
    """specs: [(текст, ідентифікатор FMA, 'L' | 'R', bias)] → підписи лише для видимих органів. Друкує, що куди стало."""
    items = []
    for text, k, side, *rest in specs:
        p = visible_point(objs[k], rest[0] if rest else None)
        print('LABEL', text, k, 'ok' if p else 'ПРИХОВАНО')
        if p: items.append((text, p, side, None))
    return layout(items, **kw)
