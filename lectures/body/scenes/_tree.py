# Помічники сцен body_real / skeleton_real / muscles_real: ієрархія атласу, завантаження зі спрощенням, авторозкладка підписів.
import bpy, os, collections
from mathutils import Vector
import bp3d

_ch = collections.defaultdict(list)
for _l in open(os.path.join(bp3d.ROOT, 'conventional_part_of.txt'), encoding='utf-8'):
    _a = _l.rstrip('\n').split('\t')
    if len(_a) >= 4 and _a[0] != '"id"': _ch[_a[0]].append(_a[2])
HAVE = {f[:-4] for f in os.listdir(os.path.join(bp3d.ROOT, 'stl'))}


def leaves(fma, seen=None):
    """Усі частини з власною сіткою, що входять до структури fma (наприклад, FMA23881 — скелет)."""
    seen = seen if seen is not None else set()
    if fma in seen: return set()
    seen.add(fma); r = {fma} if fma in HAVE else set()
    for c in _ch.get(fma, []): r |= leaves(c, seen)
    return r


def load(fma, material, max_faces=60000):
    """Як bp3d.load, але важкі сітки спрощує до max_faces граней."""
    o = bp3d.load(fma, material)
    n = len(o.data.polygons)
    if max_faces and n > max_faces:
        m = o.modifiers.new('dec', 'DECIMATE'); m.ratio = max_faces / n
        dg = bpy.context.evaluated_depsgraph_get(); dg.update()
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg)); old = o.data
        o.modifiers.clear(); o.data = me; bpy.data.meshes.remove(old)
        for p in me.polygons: p.use_smooth = True
    return o


def shift_all(objs, center):
    for o in objs: o.location -= Vector(center)
    bpy.context.view_layer.update()


def px(p):
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    v = world_to_camera_view(sc, sc.camera, Vector(p))
    return v.x * 1920, (1 - v.y) * 1080


def auto_labels(items, left_x, right_x, y0=150, y1=960, gap=58):
    """items: [(текст, точка 3D, 'L' | 'R')]. Розставляє тексти стовпчиком з кожного боку в порядку висоти точок,
    тож виноски не перетинаються. left_x — правий край лівих текстів, right_x — лівий край правих."""
    out = []
    for side in 'LR':
        grp = sorted([(px(p)[1], t, p) for t, p, s in items if s == side])
        if not grp: continue
        ys = [g[0] - 18 for g in grp]
        for i in range(1, len(ys)): ys[i] = max(ys[i], ys[i - 1] + gap)           # розсунути вниз
        over = ys[-1] - y1
        if over > 0: ys = [y - over for y in ys]
        for i in range(len(ys) - 2, -1, -1): ys[i] = min(ys[i], ys[i + 1] - gap)   # і назад угору, якщо вперлися в низ
        if ys[0] < y0:
            d = y0 - ys[0]; ys = [y + d for y in ys]
        for (py, t, p), y in zip(grp, ys):
            out.append({'text': t, 'p': tuple(p), 'at': [left_x if side == 'L' else right_x, round(y)], 'align': 'right' if side == 'L' else 'left'})
    return out
