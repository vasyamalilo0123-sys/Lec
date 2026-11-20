# Око: макроплан очного яблука — прозора рогівка, райдужка з радіальними волокнами, зіниця, склера з судинами, прямі м'язи, зоровий нерв.
import math, random
import bpy, bmesh
from mathutils import Vector

R = 1.2                      # радіус очного яблука (умовні одиниці)
RC, CY = 0.78, -0.56         # радіус кривини рогівки та зсув її центру вперед (вісь ока — уздовж −Y)
LY = -1.0225                 # площина лімба
LR = 0.628                   # радіус лімба


def plane_cut(o, co, no):
    """Відтинає частину сітки з боку нормалі no від площини через co (локальні координати)."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no, clear_outer=True)
    bm.to_mesh(o.data); bm.free()


def iris_mesh(name, r0, r1, nr=40, na=256):
    bm = bmesh.new(); rings = []
    for i in range(nr + 1):
        t = i / nr; r = r0 + (r1 - r0) * t
        h = 0.075 * (1 - t) ** 1.3 + 0.012 * math.sin(t * 9)          # до зіниці райдужка трохи випинається вперед
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * k / na), r * math.sin(2 * math.pi * k / na), h)) for k in range(na)])
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(na):
            k2 = (k + 1) % na
            bm.faces.new((a[k], a[k2], b[k2], b[k])).smooth = True
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    return o


def mat_iris(C):
    m = C.mat('iris', (0.1, 0.3, 0.4), rough=0.55, sss=0.25, sss_scale=0.02)
    nt = m.node_tree; N, L = nt.nodes, nt.links; b = N['P']
    tc = N.new('ShaderNodeTexCoord'); sp = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sp.inputs[0])
    at = N.new('ShaderNodeMath'); at.operation = 'ARCTAN2'; L.new(sp.outputs['Y'], at.inputs[0]); L.new(sp.outputs['X'], at.inputs[1])
    cs = N.new('ShaderNodeMath'); cs.operation = 'COSINE'; sn = N.new('ShaderNodeMath'); sn.operation = 'SINE'
    L.new(at.outputs[0], cs.inputs[0]); L.new(at.outputs[0], sn.inputs[0])
    xy = N.new('ShaderNodeCombineXYZ'); L.new(sp.outputs['X'], xy.inputs['X']); L.new(sp.outputs['Y'], xy.inputs['Y'])
    ln = N.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'; L.new(xy.outputs[0], ln.inputs[0])
    rn = N.new('ShaderNodeMapRange'); rn.inputs['From Min'].default_value = 0.2; rn.inputs['From Max'].default_value = LR
    L.new(ln.outputs['Value'], rn.inputs['Value'])

    def streak(scale, rstretch, detail):
        v = N.new('ShaderNodeCombineXYZ'); L.new(cs.outputs[0], v.inputs['X']); L.new(sn.outputs[0], v.inputs['Y'])
        rm = N.new('ShaderNodeMath'); rm.operation = 'MULTIPLY'; rm.inputs[1].default_value = rstretch
        L.new(rn.outputs[0], rm.inputs[0]); L.new(rm.outputs[0], v.inputs['Z'])
        n = N.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = 0.65; L.new(v.outputs[0], n.inputs['Vector'])
        return n
    fine = streak(34, 0.035, 6); coarse = streak(9, 0.12, 3)
    ramp = N.new('ShaderNodeValToRGB'); e = ramp.color_ramp.elements
    e[0].position = 0.0; e[0].color = (0.62, 0.30, 0.06, 1)
    e[1].position = 1.0; e[1].color = (0.01, 0.03, 0.06, 1)
    for pos, col in [(0.22, (0.50, 0.36, 0.10, 1)), (0.34, (0.10, 0.34, 0.32, 1)), (0.62, (0.06, 0.24, 0.42, 1)), (0.9, (0.03, 0.10, 0.22, 1))]:
        x = e.new(pos); x.color = col
    L.new(rn.outputs[0], ramp.inputs['Fac'])
    f1 = N.new('ShaderNodeMapRange'); f1.inputs['From Min'].default_value = 0.3; f1.inputs['From Max'].default_value = 0.72
    f1.inputs['To Min'].default_value = 0.25; f1.inputs['To Max'].default_value = 1.9; L.new(fine.outputs['Fac'], f1.inputs['Value'])
    f2 = N.new('ShaderNodeMapRange'); f2.inputs['From Min'].default_value = 0.35; f2.inputs['From Max'].default_value = 0.7
    f2.inputs['To Min'].default_value = 0.45; f2.inputs['To Max'].default_value = 1.4; L.new(coarse.outputs['Fac'], f2.inputs['Value'])
    mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; L.new(f1.outputs[0], mul.inputs[0]); L.new(f2.outputs[0], mul.inputs[1])
    col = N.new('ShaderNodeMixRGB'); col.blend_type = 'MULTIPLY'; col.inputs['Fac'].default_value = 1.0
    L.new(ramp.outputs['Color'], col.inputs['Color1']); L.new(mul.outputs[0], col.inputs['Color2'])
    L.new(col.outputs[0], b.inputs['Base Color'])
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 1.0; bp.inputs['Distance'].default_value = 0.03
    L.new(mul.outputs[0], bp.inputs['Height']); L.new(bp.outputs[0], b.inputs['Normal'])
    return m


def mat_cornea(C):
    """Скло рогівки; для тіньових променів прозоре, щоб світло доходило до райдужки."""
    m = C.new_mat('cornea'); nt = m.node_tree; N, L = nt.nodes, nt.links
    g = N.new('ShaderNodeBsdfGlass'); g.inputs['IOR'].default_value = 1.376; g.inputs['Roughness'].default_value = 0.0
    g.inputs['Color'].default_value = (1, 1, 1, 1)
    tr = N.new('ShaderNodeBsdfTransparent'); lp = N.new('ShaderNodeLightPath')
    mix = N.new('ShaderNodeMixShader'); L.new(lp.outputs['Is Shadow Ray'], mix.inputs[0]); L.new(g.outputs[0], mix.inputs[1]); L.new(tr.outputs[0], mix.inputs[2])
    out = N.new('ShaderNodeOutputMaterial'); L.new(mix.outputs[0], out.inputs['Surface'])
    return m


def strap(name, pts, u, m_muscle, m_tendon, seg=20):
    """М'яз-стрічка: пласка біля прикріплення (сухожилок), товщає до черевця. Переріз — еліпс: ширина по дотичній до ока, товщина по радіусу."""
    bm = bmesh.new(); rings = []; n = len(pts)
    for i, p in enumerate(pts):
        t = i / (n - 1)
        tan = (pts[min(n - 1, i + 1)] - pts[max(0, i - 1)]).normalized()
        nrm = p.normalized() if p.length < R + 0.2 else u
        nrm = (nrm - tan * nrm.dot(tan)).normalized(); w = tan.cross(nrm).normalized()
        belly = math.sin(math.pi * min(1.0, max(0.0, (t - 0.1) / 0.9)) ** 0.8)
        a = 0.20 + 0.10 * belly - 0.12 * max(0, t - 0.75) / 0.25
        b = 0.018 + 0.11 * belly
        rings.append([bm.verts.new(p + nrm * (b * 0.6) + w * (a * math.cos(2 * math.pi * k / seg)) + nrm * (b * math.sin(2 * math.pi * k / seg))) for k in range(seg)])
    for i, (r0, r1) in enumerate(zip(rings[:-1], rings[1:])):
        for k in range(seg):
            f = bm.faces.new((r0[k], r0[(k + 1) % seg], r1[(k + 1) % seg], r1[k])); f.smooth = True
            f.material_index = 1 if i < 2 else 0
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(m_muscle); me.materials.append(m_tendon)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    sub = o.modifiers.new('sub', 'SUBSURF'); sub.levels = 1; sub.render_levels = 2
    return o


def build(C):
    rnd = random.Random(8)
    C.set_world((0.004, 0.004, 0.006))

    # --- склера ---
    m_sc = C.mat('sclera', (0.86, 0.80, 0.74), rough=0.22, sss=0.8, sss_radius=(1.0, 0.45, 0.3), sss_scale=0.06, coat=1.0)
    nt = m_sc.node_tree; n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 3.0; n.inputs['Detail'].default_value = 5
    mx = nt.nodes.new('ShaderNodeMixRGB'); mx.inputs['Color1'].default_value = (0.88, 0.82, 0.76, 1); mx.inputs['Color2'].default_value = (0.80, 0.62, 0.55, 1)
    nt.links.new(n.outputs['Fac'], mx.inputs['Fac']); nt.links.new(mx.outputs[0], nt.nodes['P'].inputs['Base Color'])
    sc = C.prim('sphere', 'sclera', m_sc, scale=(R, R, R), u=128, v=64)
    plane_cut(sc, Vector((0, (LY + 0.01) / R, 0)), Vector((0, -1, 0)))

    # --- рогівка ---
    co = C.prim('sphere', 'cornea', mat_cornea(C), loc=(0, CY, 0), scale=(RC, RC, RC), u=128, v=64)
    plane_cut(co, Vector((0, (LY + 0.03 - CY) / RC, 0)), Vector((0, 1, 0)))
    so = co.modifiers.new('solid', 'SOLIDIFY'); so.thickness = 0.045; so.offset = -1
    m_lim = C.mat('limbus', (0.10, 0.12, 0.16), rough=0.4, sss=0.3)
    C.tube('limbus', [(LR * 1.0 * math.cos(a), LY + 0.012, LR * math.sin(a)) for a in [2 * math.pi * k / 64 for k in range(64)]], 0.03, m_lim, cyclic=True, res=6)

    # --- райдужка й зіниця ---
    ir = iris_mesh('iris', 0.2, LR + 0.02); ir.data.materials.append(mat_iris(C))
    ir.location = (0, LY + 0.07, 0); ir.rotation_euler = (math.radians(90), 0, 0)
    m_pm = C.mat('pupil_margin', (0.10, 0.05, 0.02), rough=0.6)
    C.tube('ruff', [(0.2 * math.cos(a), LY - 0.003, 0.2 * math.sin(a)) for a in [2 * math.pi * k / 48 for k in range(48)]], 0.012, m_pm, cyclic=True, res=4)
    m_black = C.mat('fundus', (0.0, 0.0, 0.0), rough=1.0)
    C.prim('cyl', 'pupil', m_black, loc=(0, LY + 0.14, 0), rot=(math.radians(90), 0, 0), r1=0.45, r2=0.45, depth=0.02)

    # --- судини склери: випадкове блукання по сфері в бік лімба ---
    m_v = C.mat('vessel', (0.45, 0.02, 0.02), rough=0.35, sss=0.3, sss_scale=0.01)

    def vessel(p, d, steps, rad):
        pts = []
        for i in range(steps):
            pts.append(p.normalized() * (R + 0.002))
            w = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * 0.55
            d = (d + w + Vector((0, -0.35, 0))); d = (d - p.normalized() * d.dot(p.normalized())).normalized()
            p = (p + d * 0.055).normalized() * R
            if p.y < LY + 0.09: break
            if i > 3 and rnd.random() < 0.13 and rad > 0.005:
                side = d.cross(p.normalized()) * rnd.choice([-1, 1])
                vessel(p.copy(), (d + side * 0.9).normalized(), steps - i, rad * 0.65)
        if len(pts) > 2:
            C.tube('vessel', pts, rad, m_v, radii=[1 - 0.75 * i / len(pts) for i in range(len(pts))], res=3)
    for k in range(34):
        a = rnd.uniform(0, 2 * math.pi); y = rnd.uniform(-0.25, 0.5); r = math.sqrt(R * R - y * y)
        p = Vector((r * math.cos(a), y, r * math.sin(a)))
        vessel(p, Vector((0, -1, 0)), rnd.randint(16, 30), rnd.uniform(0.007, 0.014))

    # --- прямі м'язи ока ---
    m_mu = C.mat('muscle', (0.48, 0.07, 0.06), rough=0.45, sss=0.5, sss_scale=0.04, coat=0.4)
    nt = m_mu.node_tree; tcn = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (30, 1.2, 30)
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.0; nt.links.new(tcn.outputs['Object'], mp.inputs[0]); nt.links.new(mp.outputs[0], nz.inputs['Vector'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.5; nt.links.new(nz.outputs['Fac'], bp.inputs['Height'])
    nt.links.new(bp.outputs[0], nt.nodes['P'].inputs['Normal'])
    m_te = C.mat('tendon', (0.85, 0.80, 0.72), rough=0.3, sss=0.5, coat=0.6)
    apex = Vector((0.35, 3.6, -0.1)); muscle_pt = {}
    for name, ang in (('sup', 90), ('inf', 270), ('lat', 180), ('med', 0)):
        u = Vector((math.cos(math.radians(ang)), 0, math.sin(math.radians(ang))))
        pts = []
        for t in [i / 20 for i in range(21)]:
            if t < 0.45:                        # лежить на яблуці: від місця прикріплення (попереду екватора) назад
                th = math.radians(-38 + 150 * t / 0.45 * 0.62)
                p = (u * math.cos(th) + Vector((0, 1, 0)) * math.sin(th)) * (R + 0.05)
            else:
                s = (t - 0.45) / 0.55; th = math.radians(-38 + 93)
                p0 = (u * math.cos(th) + Vector((0, 1, 0)) * math.sin(th)) * (R + 0.05)
                p = p0.lerp(apex, s) + u * 0.25 * math.sin(math.pi * s)
            pts.append(p)
        strap('m_' + name, pts, u, m_mu, m_te)
        muscle_pt[name] = pts[8]

    # --- зоровий нерв ---
    m_on = C.mat('optic', (0.86, 0.72, 0.50), rough=0.4, sss=0.6, sss_radius=(1.0, 0.6, 0.3), sss_scale=0.05, coat=0.3)
    on = [Vector((0.28, 1.1, -0.05)), Vector((0.32, 1.7, -0.08)), Vector((0.2, 2.4, -0.15)), Vector((0.3, 3.1, -0.1)), Vector((0.5, 4.2, 0.0))]
    C.tube('optic_nerve', on, 0.2, m_on, radii=[1.25, 1.0, 1.0, 1.0, 1.0], res=10)

    c = C.cam(50, (4.6, -5.6, 1.6), (-0.7, -0.5, 0.05), fstop=0.8, focus=6.0)
    C.area('key', (-0.5, -6.5, 4.5), (0, -1, 0), 3.2, 900, (1.0, 0.97, 0.94))
    C.area('rim', (-4.5, 4.5, 2.5), (0, 0.5, 0), 4, 2600, (1.0, 0.55, 0.35))
    C.area('fill', (6, -1, -3), (0, 0, 0), 5, 220, (0.5, 0.65, 1.0))
    C.area('kick', (3, 6, 4), (0.3, 2, 0), 4, 1200, (0.6, 0.75, 1.0))
    return {
        'kicker': 'Орган зору', 'title': 'Око', 'sub': 'Світло проходить рогівку,\nзіницю — і далі до сітківки', 'scrim': 'left', 'title_at': [96, 96],
        'labels': [
            {'text': 'рогівка', 'p': (0.3, CY - RC * 0.93, 0.25), 'at': [96, 520], 'align': 'right'},
            {'text': 'зіниця', 'p': (0, LY, 0), 'at': [96, 640], 'align': 'right'},
            {'text': 'райдужка', 'p': (0.05, LY + 0.03, -0.42), 'at': [96, 760], 'align': 'right'},
            {'text': 'склера', 'p': (0.75, -0.45, -0.82), 'at': [700, 950], 'align': 'left'},
            {'text': "прямий м'яз", 'p': muscle_pt['sup'] + Vector((0, 0, 0.12)), 'at': [1200, 120], 'align': 'left'},
            {'text': 'зоровий нерв', 'p': on[2] + Vector((0.15, 0, -0.12)), 'at': [1500, 900], 'align': 'left'},
        ],
    }
