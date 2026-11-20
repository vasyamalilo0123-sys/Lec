# Спільне для сцен heart_real / lungs_real / thorax_real: розкладка підписів двома колонками й зварювання сіток.
import bpy, bmesh
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


def px(p):
    sc = bpy.context.scene; bpy.context.view_layer.update()
    v = world_to_camera_view(sc, sc.camera, Vector(p))
    return v.x * 1920, (1 - v.y) * 1080


def columns(items, split_x, left_x, right_x, left_y=(420, 960), right_y=(140, 960), min_gap=64):
    """items: [(текст, точка 3D)] або (текст, точка, 'L'|'R'). Підписи стають у ліву (вирівняну праворуч) і праву колонки,
    упорядковані за висотою якоря — виноски в межах колонки не перетинаються."""
    L, R = [], []
    for it in items:
        x, y = px(it[1]); side = it[2] if len(it) > 2 else ('L' if x < split_x else 'R')
        (L if side == 'L' else R).append((y, it[0], it[1]))
    out = []
    for col, cx, (y0, y1), align in ((L, left_x, left_y, 'right'), (R, right_x, right_y, 'left')):
        col.sort(); n = len(col)
        if not n: continue
        ys = [c[0] - 18 for c in col]                      # бажано навпроти якоря
        ys[0] = max(y0, min(ys[0], y1))
        for i in range(1, n): ys[i] = max(ys[i], ys[i - 1] + min_gap)
        over = ys[-1] - y1
        if over > 0:
            ys[-1] = y1
            for i in range(n - 2, -1, -1): ys[i] = min(ys[i], ys[i + 1] - min_gap)
        for (y, text, p), ty in zip(col, ys):
            d = {'text': text, 'p': tuple(p), 'at': [cx, round(ty)], 'align': align}
            if isinstance(text, (tuple, list)): d['text'], d['sub'] = text
            out.append(d)
    return out


def fuse(C, objs, material, name, voxel=0.006, smooth=6):
    """Зливає кілька сіток в одну суцільну поверхню (воксельне об'єднання + згладжування) — прибирає шви між частинами судини."""
    bm = bmesh.new()
    for o in objs:
        t = bmesh.new(); t.from_mesh(o.data); t.transform(o.matrix_world)
        me = bpy.data.meshes.new('tmp'); t.to_mesh(me); t.free(); bm.from_mesh(me); bpy.data.meshes.remove(me)
        bpy.data.objects.remove(o)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = C.link(bpy.data.objects.new(name, me))
    r = o.modifiers.new('rem', 'REMESH'); r.mode = 'VOXEL'; r.voxel_size = voxel; r.use_smooth_shade = True
    o = C.to_mesh(o)
    bm = bmesh.new(); bm.from_mesh(o.data)
    for _ in range(smooth): bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    for f in bm.faces: f.smooth = True
    bm.to_mesh(o.data); bm.free()
    o.data.materials.clear(); o.data.materials.append(material)
    return o


def visible_point(obj, bias=(0, 0, 0), spread=0.08):
    """Точка поверхні obj біля центру (+bias), яку справді видно з камери (перевірка променем). Якщо такої немає — найближча до камери."""
    sc = bpy.context.scene; cam = sc.camera; bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb))); hi = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
    c = (lo + hi) / 2 + Vector(bias); eye = cam.matrix_world.translation; d = (c - eye).normalized()
    r = max((hi - lo).length * spread, 0.03); mw = obj.matrix_world; cand = []
    step = max(1, len(obj.data.vertices) // 40000)
    vs = obj.data.vertices
    for i in range(0, len(vs), step):
        w = mw @ vs[i].co; t = (w - eye).dot(d); off = ((w - eye) - d * t).length
        if off < r: cand.append((off, t, w))
    cand.sort(key=lambda a: a[0])
    for off, t, w in cand[:400]:
        dr = (w - eye); L = dr.length
        hit, loc, nor, idx, ob, _ = sc.ray_cast(dg, eye, dr / L, distance=L + 0.01)
        if hit and ob.name == obj.name and (loc - w).length < 0.02: return tuple(w)
    if cand:
        return tuple(min(cand, key=lambda a: a[1])[2])
    return tuple(c)


def fade_out(mat, center, r0, r1):
    """Матеріал плавно зникає між відстанями r0 і r1 від center (світові координати) — щоб довгі судини танули в темряві, а не обривалися."""
    nt = mat.node_tree; N, L = nt.nodes, nt.links
    out = next(n for n in N if n.type == 'OUTPUT_MATERIAL'); src = out.inputs['Surface'].links[0].from_socket
    geo = N.new('ShaderNodeNewGeometry')
    sub = N.new('ShaderNodeVectorMath'); sub.operation = 'SUBTRACT'; sub.inputs[1].default_value = center
    ln = N.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'
    L.new(geo.outputs['Position'], sub.inputs[0]); L.new(sub.outputs[0], ln.inputs[0])
    mr = N.new('ShaderNodeMapRange'); mr.interpolation_type = 'SMOOTHSTEP'
    mr.inputs['From Min'].default_value = r0; mr.inputs['From Max'].default_value = r1
    L.new(ln.outputs['Value'], mr.inputs['Value'])
    tr = N.new('ShaderNodeBsdfTransparent'); mix = N.new('ShaderNodeMixShader')
    L.new(mr.outputs[0], mix.inputs[0]); L.new(src, mix.inputs[1]); L.new(tr.outputs[0], mix.inputs[2]); L.new(mix.outputs[0], out.inputs['Surface'])
    return mat


def see_through(mat, power=1.6, base=0.06, top=0.92):
    """Робить матеріал прозорим там, де поверхня звернена до камери, і щільним на краях силуету — крізь орган видно вміст."""
    nt = mat.node_tree; N, L = nt.nodes, nt.links
    out = next(n for n in N if n.type == 'OUTPUT_MATERIAL'); src = out.inputs['Surface'].links[0].from_socket
    lw = N.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.5
    pw = N.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = power
    mr = N.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = base; mr.inputs['To Max'].default_value = top
    L.new(lw.outputs['Facing'], pw.inputs[0]); L.new(pw.outputs[0], mr.inputs['Value'])
    tr = N.new('ShaderNodeBsdfTransparent'); mix = N.new('ShaderNodeMixShader')
    L.new(mr.outputs[0], mix.inputs[0]); L.new(tr.outputs[0], mix.inputs[1]); L.new(src, mix.inputs[2]); L.new(mix.outputs[0], out.inputs['Surface'])
    return mat


def lights(C, s=1.0, key=520, rim=2600, rim2=1100, fill=35, target=(0, 0, 0)):
    """Схема світла серії: тепле ключове зліва-спереду, холодний контровий справа-ззаду, теплий контровий зліва-ззаду, слабке заповнення."""
    k = s * s
    C.area('key', (-4.0 * s, -4.5 * s, 4.0 * s), target, 2.2 * s, key * k, (1.0, 0.93, 0.86))
    C.area('rim', (4.0 * s, 3.5 * s, 2.5 * s), target, 2.0 * s, rim * k, (0.7, 0.82, 1.0))
    C.area('rim2', (-3.5 * s, 4.0 * s, -1.5 * s), target, 2.5 * s, rim2 * k, (1.0, 0.5, 0.35))
    C.area('fill', (3.0 * s, -4 * s, -3.0 * s), target, 4.0 * s, fill * k, (0.6, 0.7, 1.0))
