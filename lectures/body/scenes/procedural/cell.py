# Клітина в розрізі: «чаша» мембрани зі зрізаним верхом, усередині ядро, ЕПС, Гольджі, мітохондрії, лізосоми, центріолі, цитоскелет.
import math, random
import bpy, bmesh
from mathutils import Vector

CUT = 0.3                      # висота площини зрізу клітини
NUC = Vector((-0.6, 0.95, -0.35))
NUC_R = 1.45


def cut(o, z, fill=False, cap_index=1):
    """Зрізає все вище світової висоти z; fill — закрити зріз пласкою гранню з матеріалом cap_index."""
    bpy.context.view_layer.update()
    inv = o.matrix_world.inverted()
    co = inv @ Vector((0, 0, z)); no = (o.matrix_world.to_3x3().transposed() @ Vector((0, 0, 1))).normalized()
    bm = bmesh.new(); bm.from_mesh(o.data)
    r = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no, clear_outer=True)
    if fill:
        edges = [e for e in r['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
        f = bmesh.ops.edgeloop_fill(bm, edges=edges)
        for face in f['faces']:
            face.material_index = cap_index; face.smooth = False
        bmesh.ops.split_edges(bm, edges=[e for e in bm.edges if e in set(edges)])
    bm.to_mesh(o.data); bm.free()


def solid(o, t, sub=0):
    m = o.modifiers.new('solid', 'SOLIDIFY'); m.thickness = t; m.offset = -1
    if sub:
        s = o.modifiers.new('sub', 'SUBSURF'); s.levels = sub; s.render_levels = sub


def grid_mesh(name, nu, nv, fn, material):
    bm = bmesh.new()
    vs = [[bm.verts.new(fn(i / (nu - 1), j / (nv - 1))) for j in range(nv)] for i in range(nu)]
    for i in range(nu - 1):
        for j in range(nv - 1):
            bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1])).smooth = True
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    me.materials.append(material)
    return o


def noise_mat(C, name, c1, c2, scale=3.0, rough=0.5, sss=0.4, bump=0.3, coat=0.2):
    m = C.mat(name, c1, rough=rough, sss=sss, sss_scale=0.08, coat=coat)
    nt = m.node_tree; N, L = nt.nodes, nt.links; b = N['P']
    tc = N.new('ShaderNodeTexCoord'); n = N.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = 4
    L.new(tc.outputs['Object'], n.inputs['Vector'])
    mix = N.new('ShaderNodeMixRGB'); mix.inputs['Color1'].default_value = (*c1, 1); mix.inputs['Color2'].default_value = (*c2, 1)
    cr = N.new('ShaderNodeMapRange'); cr.inputs['From Min'].default_value = 0.35; cr.inputs['From Max'].default_value = 0.65
    L.new(n.outputs['Fac'], cr.inputs['Value']); L.new(cr.outputs[0], mix.inputs['Fac']); L.new(mix.outputs[0], b.inputs['Base Color'])
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump; bp.inputs['Distance'].default_value = 0.1
    L.new(n.outputs['Fac'], bp.inputs['Height']); L.new(bp.outputs[0], b.inputs['Normal'])
    return m


def build(C):
    rnd = random.Random(12)
    C.set_world((0.004, 0.006, 0.014))
    labels = {}

    # --- мембрана й цитоплазма ---
    m_mem = noise_mat(C, 'membrane', (0.03, 0.20, 0.38), (0.06, 0.32, 0.50), scale=7, rough=0.35, sss=0.6, bump=0.25, coat=0.5)
    mem = C.prim('sphere', 'membrane', m_mem, scale=(4.0, 4.0, 3.3), u=96, v=48)
    cut(mem, CUT); solid(mem, 0.26)
    m_cyto = noise_mat(C, 'cyto', (0.015, 0.07, 0.16), (0.03, 0.13, 0.24), scale=2.5, rough=0.6, sss=0.5, bump=0.5, coat=0.1)
    cyto = C.prim('sphere', 'cyto', m_cyto, scale=(3.72, 3.72, 3.02), u=96, v=48)
    cut(cyto, -1.2, fill=True, cap_index=0)          # «дно» цитоплазми, на якому лежать органели
    labels['mem'] = (3.87 * math.cos(-0.5), 3.87 * math.sin(-0.5), CUT)

    # --- ядро ---
    m_env = C.mat('envelope', (0.42, 0.22, 0.62), rough=0.4, sss=0.5, sss_scale=0.06, coat=0.4)
    m_chr = noise_mat(C, 'chromatin', (0.20, 0.07, 0.36), (0.52, 0.30, 0.72), scale=4.5, rough=0.55, sss=0.5, bump=0.6)
    env = C.prim('sphere', 'envelope', m_env, loc=NUC, scale=(NUC_R,) * 3, u=64, v=32)
    cut(env, CUT - 0.05); solid(env, 0.07)
    chro = C.prim('sphere', 'chromatin', m_chr, loc=NUC, scale=(NUC_R - 0.1,) * 3, u=64, v=32)
    chro.data.materials.append(m_chr); cut(chro, CUT - 0.12, fill=True)
    m_ncl = noise_mat(C, 'nucleolus', (0.12, 0.03, 0.22), (0.30, 0.10, 0.42), scale=14, rough=0.6, bump=1.0)
    ncl = C.prim('ico', 'nucleolus', m_ncl, loc=(NUC.x + 0.3, NUC.y - 0.15, CUT - 0.2), scale=(0.44,) * 3, subdiv=4)
    C.displace(ncl, 0.08, 0.25)
    labels['nucleus'] = (NUC.x - 0.75, NUC.y - 0.1, CUT - 0.12); labels['nucleolus'] = (NUC.x + 0.3, NUC.y - 0.15, CUT + 0.2)
    m_pore = C.mat('pore', (0.10, 0.03, 0.18), rough=0.7)
    pore = C.prim('ico', 'pore', m_pore, loc=(0, 0, -50), scale=(0.045,) * 3, subdiv=1)
    for _ in range(260):
        v = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized() * (NUC_R + 0.005)
        if NUC.z + v.z < CUT - 0.15:
            C.instance(pore, 'p', NUC + v, scale=0.045)
    labels['pore'] = tuple(NUC + Vector((0.35, -0.92, -0.05)).normalized() * NUC_R)

    # --- шорстка ендоплазматична сітка: хвилясті концентричні листки довкола ядра ---
    m_er = C.mat('er', (0.12, 0.16, 0.62), rough=0.4, sss=0.5, sss_radius=(0.3, 0.4, 1.0), sss_scale=0.05, coat=0.3)
    m_rib = C.mat('ribosome', (0.95, 0.75, 0.35), rough=0.5, emission=(0.95, 0.6, 0.2), emission_strength=0.3)
    rib = C.prim('ico', 'rib', m_rib, loc=(0, 0, -50), scale=(0.032,) * 3, subdiv=1)
    P0, P1 = math.radians(72), math.radians(258)
    for k in range(4):
        r0 = 1.78 + k * 0.23; ph = rnd.uniform(0, 6.28)
        a0, a1 = P0 + rnd.uniform(-0.2, 0.2), P1 + rnd.uniform(-0.25, 0.25)

        def fn(u, v, r0=r0, ph=ph, a0=a0, a1=a1):
            phi = a0 + (a1 - a0) * u; th = math.radians(38 + 92 * v)
            r = r0 + 0.07 * math.sin(11 * phi + ph) * math.sin(4 * th + ph) + 0.03 * math.sin(23 * phi)
            return NUC + Vector((r * math.sin(th) * math.cos(phi), r * math.sin(th) * math.sin(phi), r * math.cos(th)))
        sh = grid_mesh(f'er{k}', 150, 36, fn, m_er)
        cut(sh, CUT - 0.3 - 0.07 * k); solid(sh, 0.075)
        for _ in range(420):
            u, v = rnd.random(), rnd.random()
            p = fn(u, v); d = (p - NUC).normalized()
            if -1.2 < p.z < CUT - 0.36 - 0.07 * k:
                C.instance(rib, 'r', p + d * 0.02, scale=0.032)
        if k == 3:
            labels['er'] = tuple(fn(0.93, 0.0) * 1.0 + Vector((0, 0, -0.75)))
            pp = fn(0.9, 0.3); labels['rib'] = tuple(pp)
    pe = NUC + Vector((2.47 * math.cos(math.radians(205)), 2.47 * math.sin(math.radians(205)), 0)); pe.z = CUT - 0.52
    labels['er'] = tuple(pe)

    # --- апарат Гольджі: стос вигнутих цистерн і пухирці ---
    m_g = C.mat('golgi', (0.88, 0.48, 0.10), rough=0.35, sss=0.5, sss_radius=(1.0, 0.5, 0.2), sss_scale=0.05, coat=0.5)
    GC = Vector((2.35, -0.2, -0.55)); ang = math.radians(-8)
    for k in range(6):
        R = 1.35 + k * 0.17; span = 0.72 - k * 0.05; w = 0.62 - 0.05 * abs(k - 2.5)

        def gf(u, v, R=R, span=span, w=w):
            a = (u - 0.5) * 2 * span
            swell = 1 + 0.5 * abs(u - 0.5) ** 3 * 8
            x = -R * math.cos(a) + 1.75; y = R * math.sin(a); z = (v - 0.5) * 2 * w * (1 - 0.3 * (2 * u - 1) ** 2)
            return GC + Vector((x * math.cos(ang) - y * math.sin(ang), x * math.sin(ang) + y * math.cos(ang), z))
        g = grid_mesh(f'golgi{k}', 28, 8, gf, m_g); solid(g, 0.085, 2)
    for _ in range(26):
        a = rnd.choice([-1, 1]) * rnd.uniform(0.7, 1.0); R = rnd.uniform(1.3, 2.1)
        x = -R * math.cos(a) + 1.75; y = R * math.sin(a)
        C.prim('sphere', 'ves', m_g, loc=GC + Vector((x * math.cos(ang) - y * math.sin(ang), x * math.sin(ang) + y * math.cos(ang), rnd.uniform(-0.35, 0.35))),
               scale=(rnd.uniform(0.06, 0.12),) * 3, u=16, v=8)
    labels['golgi'] = tuple(GC + Vector((0.55, -0.1, 0.45)))

    # --- мітохондрії ---
    m_mo = noise_mat(C, 'mito', (0.75, 0.16, 0.08), (0.92, 0.32, 0.12), scale=9, rough=0.4, sss=0.5, bump=0.3, coat=0.5)
    m_mx = C.mat('matrix', (0.42, 0.06, 0.04), rough=0.6, sss=0.3)
    m_cr = C.mat('cristae', (1.0, 0.55, 0.30), rough=0.4, sss=0.5, sss_scale=0.03, coat=0.3)
    for (x, y, z, rz, s) in [(1.95, 2.2, -0.82, 2.4, 0.95), (2.3, -1.9, -0.84, 0.87, 0.9), (-0.1, -3.0, -0.86, 0.05, 0.8)]:
        o = C.prim('sphere', 'mito', m_mo, loc=(x, y, z), scale=(0.95 * s, 0.4 * s, 0.4 * s), rot=(rnd.uniform(-0.3, 0.3), rnd.uniform(-0.25, 0.25), rz), u=40, v=20)
    # одна в розрізі, на передньому плані
    MC = Vector((-1.55, -1.85, -0.72)); mr = 0.5; mzc = MC.z + 0.1
    outer = C.prim('sphere', 'mito_cut', m_mo, loc=MC, scale=(1.15, 0.5, 0.5), rot=(0, 0, mr), u=48, v=24)
    cut(outer, mzc); solid(outer, 0.05)
    inner = C.prim('sphere', 'mito_in', m_mx, loc=MC, scale=(1.07, 0.42, 0.42), rot=(0, 0, mr), u=48, v=24)
    inner.data.materials.append(m_mx); cut(inner, mzc - 0.05, fill=True)
    ex = Vector((math.cos(mr), math.sin(mr), 0)); ey = Vector((-math.sin(mr), math.cos(mr), 0))
    for i in range(9):
        t = -0.84 + i * 0.21; half = 0.42 * math.sqrt(max(0.05, 1 - (t / 1.07) ** 2)); side = 1 if i % 2 else -1
        a = MC + ex * t + ey * (side * half * 0.95); b = MC + ex * (t + 0.03 * side) - ey * (side * half * 0.35)
        a.z = b.z = mzc - 0.03
        cr = C.tube(f'crista{i}', [a, (a + b) / 2 + ex * 0.03, b], 0.045, m_cr)
        cr.scale = (1, 1, 1)
    labels['mito'] = tuple(MC + ex * 0.2 + Vector((0, 0, 0.12)))

    # --- лізосоми ---
    m_ly = noise_mat(C, 'lyso', (0.16, 0.50, 0.22), (0.35, 0.72, 0.30), scale=12, rough=0.45, sss=0.6, bump=0.5, coat=0.4)
    lys = [(0.85, -0.95, -0.86, 0.34), (1.3, -2.8, -0.92, 0.28), (2.75, 1.4, -0.95, 0.24), (0.1, -1.75, -0.98, 0.22)]
    for (x, y, z, r) in lys:
        C.prim('sphere', 'lyso', m_ly, loc=(x, y, z), scale=(r,) * 3, u=32, v=16)
    labels['lyso'] = (0.85, -0.95, -0.86 + 0.3)

    # --- центросома: дві центріолі під прямим кутом, від неї — мікротрубочки ---
    m_ce = C.mat('centriole', (0.95, 0.45, 0.62), rough=0.35, sss=0.3, coat=0.5, emission=(0.9, 0.3, 0.5), emission_strength=0.15)
    CC = Vector((0.75, -2.15, -0.8))
    for axis, off in (('x', Vector((0, 0, 0))), ('y', Vector((0.42, 0.05, 0.02)))):
        for i in range(9):
            a = 2 * math.pi * i / 9
            for t in range(3):
                rr = 0.12 + t * 0.028; aa = a + t * 0.2
                c, s = rr * math.cos(aa), rr * math.sin(aa)
                p0, p1 = (Vector((-0.2, c, s)), Vector((0.2, c, s))) if axis == 'x' else (Vector((c, -0.2, s)), Vector((c, 0.2, s)))
                C.tube('ct', [CC + off + p0, CC + off + p1], 0.016, m_ce, smooth=False, res=3)
    labels['centriole'] = tuple(CC + Vector((0.0, 0, 0.14)))
    m_mt = C.mat('microtubule', (0.55, 0.85, 0.95), rough=0.4, emission=(0.3, 0.7, 0.9), emission_strength=0.5)
    for i in range(34):
        a = rnd.uniform(0, 6.28); R = rnd.uniform(2.6, 3.3); zt = rnd.uniform(-1.1, -0.3)
        end = Vector((R * math.cos(a), R * math.sin(a), zt)); mid = (CC + end) / 2 + Vector((rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), rnd.uniform(-0.25, 0.1)))
        if (mid - NUC).length < NUC_R + 1.5 and (end - CC).length > 3.5:
            continue
        C.tube('mt', [CC, mid, end], 0.012, m_mt, res=2)
    labels['mt'] = tuple((CC + Vector((0.55, 0.95, 0.12))))

    # --- дрібні пухирці та вільні рибосоми ---
    m_v = C.mat('vesicle', (0.75, 0.85, 0.95), rough=0.2, sss=0.6, coat=0.6, transmission=0.3)
    for _ in range(70):
        a = rnd.uniform(0, 6.28); R = rnd.uniform(2.2, 3.5)
        C.prim('sphere', 'v', m_v, loc=(R * math.cos(a), R * math.sin(a), rnd.uniform(-1.15, -0.5)), scale=(rnd.uniform(0.04, 0.1),) * 3, u=12, v=6)
    for _ in range(500):
        a = rnd.uniform(0, 6.28); R = rnd.uniform(1.6, 3.6)
        C.instance(rib, 'fr', (R * math.cos(a), R * math.sin(a), -1.18), scale=0.032)

    c = C.cam(29, (-0.3, -8.6, 11.6), (-0.55, 0.15, -0.9), fstop=1.1)
    C.area('key', (-5, -6, 9), (0, 0, 0), 7, 2600, (1.0, 0.95, 0.9))
    C.area('rim', (3, 9, 5), (0, 0, 0), 8, 4200, (0.45, 0.65, 1.0))
    C.area('side', (9, -3, 2), (0, 0, -0.5), 5, 1100, (1.0, 0.6, 0.45))
    C.point('inner', (0.5, -0.5, 2.6), 160, (1.0, 0.9, 0.85), 1.5)

    L = lambda key, text, at, align='left', sub=None: {'text': text, 'p': labels[key], 'at': at, 'align': align, **({'sub': sub} if sub else {})}
    return {
        'kicker': 'Будова клітини', 'title': 'Клітина', 'sub': 'Кожна органела —\nокремий цех', 'scrim': 'left', 'title_at': [96, 96],
        'labels': [
            L('nucleus', 'ядро', [170, 450], 'right'),
            L('er', 'шорстка ЕПС', [290, 560], 'right'),
            L('mito', 'мітохондрія', [290, 700], 'right', sub='кристи на зрізі'),
            L('nucleolus', 'ядерце', [1700, 130]),
            L('pore', 'ядерні пори', [1640, 230]),
            L('golgi', 'апарат Гольджі', [1580, 330]),
            L('mem', 'клітинна мембрана', [1530, 800]),
            L('mt', 'мікротрубочки', [1600, 900]),
            L('centriole', 'центріолі', [1180, 940]),
            L('lyso', 'лізосома', [780, 940]),
        ],
    }
