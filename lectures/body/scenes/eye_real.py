# Око й зоровий шлях на справжній анатомії BodyParts3D: очні яблука, зорові нерви, перехрестя, тракти, латеральні колінчасті тіла
# всередині «рентгенівського» черепа. Райдужка й зіниця — процедурний малюнок на справжній сітці очного яблука.
import bpy, bmesh, sys, os, math
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bp3d, brainparts as B

SKULL = ['FMA52734', 'FMA52736', 'FMA52892', 'FMA52893', 'FMA53649', 'FMA53650', 'FMA53647', 'FMA53648', 'FMA53645', 'FMA53646',
         'FMA52738', 'FMA52739', 'FMA52788', 'FMA52789', 'FMA52735', 'FMA52748', 'FMA9710', 'FMA53655', 'FMA53656']


def eye_mat(C):
    """Склера, райдужка, зіниця за кутом від напрямку погляду (вперед, −Y); початок координат об'єкта — центр ока."""
    m = C.mat('eye', (0.9, 0.87, 0.83), rough=0.08, sss=0.5, sss_radius=(1.0, 0.5, 0.4), sss_scale=0.01, coat=1.0)
    nt = m.node_tree; N, L = nt.nodes, nt.links; P = N['P']
    tc = N.new('ShaderNodeTexCoord')
    nrm = N.new('ShaderNodeVectorMath'); nrm.operation = 'NORMALIZE'; L.new(tc.outputs['Object'], nrm.inputs[0])
    dot = N.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'; dot.inputs[1].default_value = (0, -1, 0); L.new(nrm.outputs[0], dot.inputs[0])
    ang = N.new('ShaderNodeMath'); ang.operation = 'ARCCOSINE'; L.new(dot.outputs['Value'], ang.inputs[0])
    # волокна райдужки: шум лише за напрямком у площині райдужки
    flat = N.new('ShaderNodeVectorMath'); flat.operation = 'MULTIPLY'; flat.inputs[1].default_value = (1, 0, 1); L.new(nrm.outputs[0], flat.inputs[0])
    fn = N.new('ShaderNodeVectorMath'); fn.operation = 'NORMALIZE'; L.new(flat.outputs[0], fn.inputs[0])
    fib = N.new('ShaderNodeTexNoise'); fib.inputs['Scale'].default_value = 9.0; fib.inputs['Detail'].default_value = 8; L.new(fn.outputs[0], fib.inputs['Vector'])
    iris = N.new('ShaderNodeMixRGB'); iris.inputs['Color1'].default_value = (0.05, 0.09, 0.07, 1); iris.inputs['Color2'].default_value = (0.42, 0.44, 0.24, 1)
    L.new(fib.outputs['Fac'], iris.inputs['Fac'])
    # тепліше кільце біля зіниці
    ring = N.new('ShaderNodeMapRange'); ring.inputs['From Min'].default_value = 0.2; ring.inputs['From Max'].default_value = 0.34
    ring.inputs['To Min'].default_value = 1.0; ring.inputs['To Max'].default_value = 0.0; L.new(ang.outputs[0], ring.inputs['Value'])
    iris2 = N.new('ShaderNodeMixRGB'); iris2.inputs['Color2'].default_value = (0.5, 0.3, 0.1, 1); L.new(ring.outputs[0], iris2.inputs['Fac']); L.new(iris.outputs[0], iris2.inputs['Color1'])
    # судини склери
    vn = N.new('ShaderNodeTexNoise'); vn.inputs['Scale'].default_value = 14.0; vn.inputs['Detail'].default_value = 10; L.new(tc.outputs['Object'], vn.inputs['Vector'])
    vr = N.new('ShaderNodeMapRange'); vr.inputs['From Min'].default_value = 0.56; vr.inputs['From Max'].default_value = 0.7; L.new(vn.outputs['Fac'], vr.inputs['Value'])
    scl = N.new('ShaderNodeMixRGB'); scl.inputs['Color1'].default_value = (0.9, 0.87, 0.83, 1); scl.inputs['Color2'].default_value = (0.75, 0.42, 0.38, 1)
    L.new(vr.outputs[0], scl.inputs['Fac'])
    def step(edge, w=0.025):
        r = N.new('ShaderNodeMapRange'); r.inputs['From Min'].default_value = edge - w; r.inputs['From Max'].default_value = edge + w
        L.new(ang.outputs[0], r.inputs['Value']); return r
    s_iris, s_pupil, s_limb = step(0.50), step(0.19, 0.015), step(0.47, 0.05)
    limb = N.new('ShaderNodeMixRGB'); limb.inputs['Color2'].default_value = (0.03, 0.04, 0.04, 1)       # темний лімб на краю райдужки
    L.new(s_limb.outputs[0], limb.inputs['Fac']); L.new(iris2.outputs[0], limb.inputs['Color1'])
    c1 = N.new('ShaderNodeMixRGB'); L.new(s_iris.outputs[0], c1.inputs['Fac']); L.new(limb.outputs[0], c1.inputs['Color1']); L.new(scl.outputs[0], c1.inputs['Color2'])
    c2 = N.new('ShaderNodeMixRGB'); c2.inputs['Color1'].default_value = (0.002, 0.002, 0.002, 1)
    L.new(s_pupil.outputs[0], c2.inputs['Fac']); L.new(c1.outputs[0], c2.inputs['Color2'])
    L.new(c2.outputs[0], P.inputs['Base Color'])
    sss = N.new('ShaderNodeMath'); sss.operation = 'MULTIPLY'; sss.inputs[1].default_value = 0.5; L.new(s_iris.outputs[0], sss.inputs[0]); L.new(sss.outputs[0], P.inputs['Subsurface Weight'])
    return m


def split_eyes(o, material):
    """Сітка атласу містить обидва ока; ділить на праве (x < 0) й ліве та ставить початок координат кожного в його центр."""
    out = {}
    for side, keep in (('R', lambda x: x < 0), ('L', lambda x: x >= 0)):
        me = o.data.copy(); bm = bmesh.new(); bm.from_mesh(me)
        xs = [(o.matrix_world @ v.co).x for v in bm.verts]
        mid = (min(xs) + max(xs)) / 2
        bmesh.ops.delete(bm, geom=[v for v, x in zip(bm.verts, xs) if not keep(x - mid)], context='VERTS')
        c = sum((v.co for v in bm.verts), Vector()) / len(bm.verts)
        lo = Vector((min(v.co.x for v in bm.verts), min(v.co.y for v in bm.verts), min(v.co.z for v in bm.verts)))
        hi = Vector((max(v.co.x for v in bm.verts), max(v.co.y for v in bm.verts), max(v.co.z for v in bm.verts)))
        c = (lo + hi) / 2
        for v in bm.verts: v.co -= c
        bm.to_mesh(me); bm.free()
        e = bpy.data.objects.new('eye' + side, me); bpy.context.scene.collection.objects.link(e)
        e.matrix_world = o.matrix_world.copy(); e.location = o.matrix_world @ c
        me.materials.clear(); me.materials.append(material)
        out[side] = e
    bpy.data.objects.remove(o)
    bpy.context.view_layer.update()
    return out


def build(C):
    C.set_world((0.0012, 0.0012, 0.0016))
    nerve = bp3d.flesh(C, 'nerve', (0.92, 0.74, 0.42), (0.98, 0.86, 0.58), rough=0.35, sss=0.7, scale=0.008, bump=0.12, noise=70, coat=0.5)
    nerve.node_tree.nodes['P'].inputs['Emission Color'].default_value = (1.0, 0.72, 0.35, 1)
    nerve.node_tree.nodes['P'].inputs['Emission Strength'].default_value = 0.6
    bone = C.mat_xray('bone', (0.42, 0.58, 0.9), strength=0.55, power=2.4, base=0.012)
    parts = {'FMA12513': None, 'FMA50875': nerve, 'FMA50878': nerve, 'FMA62045': nerve, 'FMA62382': nerve, 'FMA67936': nerve,
             'FMA73303': nerve, 'FMA73304': nerve}
    parts.update({k: bone for k in SKULL})
    O = bp3d.load_many(parts, anchor='FMA62045')
    eyes = split_eyes(O.pop('FMA12513'), eye_mat(C))
    for k, o in list(eyes.items()) + [('LGB', O['FMA73303'])]:
        lo, hi = bp3d.bbox(o); print('BBOX', k, [round(v, 2) for v in lo], [round(v, 2) for v in hi])
    cam = C.cam(70, (2.3, -4.3, 2.3), (-0.04, -0.26, -0.06), fstop=2.4, focus=None)
    bpy.context.view_layer.update()
    C.area('key', (-1.5, -4.5, 3.0), (0, -0.4, 0), 2.0, 260, (1.0, 0.95, 0.9))
    C.area('rim', (-3.0, 3.0, 2.5), (0, 0, 0), 2.0, 900, (0.7, 0.82, 1.0))
    C.area('rim2', (3.5, 2.5, -1.0), (0, 0, 0), 2.0, 500, (1.0, 0.55, 0.35))
    fp = lambda o, bias=(0, 0, 0): bp3d.front_point(o, cam, bias)
    left = [('латеральне колінчасте тіло', fp(O['FMA73303'])), ('зоровий тракт', fp(O['FMA62382'])), ('зорове перехрестя', fp(O['FMA62045'])),
            ('зоровий нерв', fp(O['FMA50875'])), ('очне яблуко', fp(eyes['R'], (-0.05, 0, -0.11)))]
    labels = B.columns(left, [], xl=520, y0=350, y1=790)
    return {'kicker': 'Органи чуття', 'title': 'Зоровий шлях', 'sub': 'Від сітківки до таламуса', 'scrim': 'left', 'source': bp3d.CREDIT, 'labels': labels}
