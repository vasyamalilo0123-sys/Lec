# Нирка у фронтальному розрізі: кіркова речовина, піраміди, чашечки, миска, сечовід, артерія й вена.
# Площина розрізу — y = 0, камера дивиться з боку −y. Ворота нирки звернені праворуч (+x).
import bpy, bmesh, math, random

AX, BZ, INDENT, W = 1.6, 2.65, 0.9, 0.5
SX = 0.38                                    # центр ниркової пазухи
PYR = [54, 96, 138, 180, 222, 264, 306]      # напрямки пірамід від центру пазухи, градуси (180 — латерально)
COL = [75, 117, 159, 201, 243, 285]          # ниркові стовпи між пірамідами


def outline(n=160):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = AX * math.cos(t) + INDENT * math.exp(-((t - math.pi) / W) ** 2) + 0.08 * math.sin(2 * t)
        pts.append((-x, BZ * math.sin(t) * (1 + 0.04 * math.cos(t))))
    return pts


OUT = outline()
_POL = sorted((math.atan2(z, x - SX) % (2 * math.pi), math.hypot(x - SX, z)) for x, z in OUT)


def D(deg):
    """Відстань від центру пазухи до контуру нирки в напрямку deg."""
    a = math.radians(deg) % (2 * math.pi)
    for (a0, d0), (a1, d1) in zip(_POL, _POL[1:] + [(_POL[0][0] + 2 * math.pi, _POL[0][1])]):
        if a0 <= a <= a1:
            return d0 + (d1 - d0) * (a - a0) / max(1e-9, a1 - a0)
    return _POL[0][1]


def at(deg, f, y=0.0):
    """Точка на частці f шляху від центру пазухи до контуру."""
    a = math.radians(deg); d = D(deg) * f
    return (SX + d * math.cos(a), y, d * math.sin(a))


def flat(name, pts2, y, mat, C, thick=0.0):
    """Плоска фігура в площині розрізу (x, z) на глибині y; thick — виступ у бік камери."""
    bm = bmesh.new()
    front = [bm.verts.new((x, y - thick, z)) for x, z in pts2]
    bm.faces.new(front)
    if thick:
        back = [bm.verts.new((x, y, z)) for x, z in pts2]
        n = len(pts2)
        for i in range(n):
            bm.faces.new((front[i], back[i], back[(i + 1) % n], front[(i + 1) % n]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    return C.link(bpy.data.objects.new(name, me))


def granular(C, name, c1, c2, scale=60.0, dots=True):
    """Зерниста паренхіма: дрібний шум і темні цятки (ниркові тільця в корі)."""
    m = C.mat(name, c1, rough=0.45, sss=0.4, sss_radius=(1.0, 0.3, 0.2), sss_scale=0.05, coat=0.5)
    nt = m.node_tree; N, L = nt.nodes, nt.links; b = N['P']
    tc = N.new('ShaderNodeTexCoord')
    n1 = N.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = scale * 0.15; n1.inputs['Detail'].default_value = 6
    L.new(tc.outputs['Object'], n1.inputs['Vector'])
    col = N.new('ShaderNodeMixRGB'); col.inputs['Color1'].default_value = (*c1, 1); col.inputs['Color2'].default_value = (*c2, 1)
    L.new(n1.outputs['Fac'], col.inputs['Fac'])
    last = col
    if dots:
        vor = N.new('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = scale; L.new(tc.outputs['Object'], vor.inputs['Vector'])
        mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.10; mr.inputs['From Max'].default_value = 0.22
        L.new(vor.outputs['Distance'], mr.inputs['Value'])
        dk = N.new('ShaderNodeMixRGB'); dk.inputs['Color1'].default_value = (c1[0] * 0.45, c1[1] * 0.3, c1[2] * 0.3, 1)
        L.new(mr.outputs[0], dk.inputs['Fac']); L.new(col.outputs[0], dk.inputs['Color2']); last = dk
    L.new(last.outputs[0], b.inputs['Base Color'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.3; bump.inputs['Distance'].default_value = 0.02
    L.new(n1.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs[0], b.inputs['Normal'])
    return m


def pyramid_mat(C, name):
    """Мозкова речовина: смуги, що сходяться до сосочка (локальний початок координат — верхівка, вісь X — до основи)."""
    m = C.mat(name, (0.5, 0.1, 0.1), rough=0.4, sss=0.4, sss_radius=(1.0, 0.3, 0.2), sss_scale=0.05, coat=0.55)
    nt = m.node_tree; N, L = nt.nodes, nt.links; b = N['P']
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])
    ang = N.new('ShaderNodeMath'); ang.operation = 'ARCTAN2'; L.new(sep.outputs['Z'], ang.inputs[0]); L.new(sep.outputs['X'], ang.inputs[1])
    noise = N.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 3.0; L.new(tc.outputs['Object'], noise.inputs['Vector'])
    ma = N.new('ShaderNodeMath'); ma.operation = 'MULTIPLY_ADD'; ma.inputs[1].default_value = 140.0
    na = N.new('ShaderNodeMath'); na.operation = 'MULTIPLY'; na.inputs[1].default_value = 5.0; L.new(noise.outputs['Fac'], na.inputs[0])
    L.new(ang.outputs[0], ma.inputs[0]); L.new(na.outputs[0], ma.inputs[2])
    sn = N.new('ShaderNodeMath'); sn.operation = 'SINE'; L.new(ma.outputs[0], sn.inputs[0])
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -1; mr.inputs['From Max'].default_value = 1; L.new(sn.outputs[0], mr.inputs['Value'])
    st = N.new('ShaderNodeMixRGB'); st.inputs['Color1'].default_value = (0.33, 0.04, 0.05, 1); st.inputs['Color2'].default_value = (0.70, 0.22, 0.18, 1)
    L.new(mr.outputs[0], st.inputs['Fac'])
    # до сосочка блідіше
    ln = N.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'; L.new(tc.outputs['Object'], ln.inputs[0])
    pr = N.new('ShaderNodeMapRange'); pr.inputs['From Min'].default_value = 0.0; pr.inputs['From Max'].default_value = 0.75
    pr.inputs['To Min'].default_value = 0.55; pr.inputs['To Max'].default_value = 0.0; L.new(ln.outputs['Value'], pr.inputs['Value'])
    pal = N.new('ShaderNodeMixRGB'); pal.inputs['Color2'].default_value = (0.86, 0.50, 0.42, 1)
    L.new(pr.outputs[0], pal.inputs['Fac']); L.new(st.outputs[0], pal.inputs['Color1']); L.new(pal.outputs[0], b.inputs['Base Color'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.35; bump.inputs['Distance'].default_value = 0.02
    L.new(mr.outputs[0], bump.inputs['Height']); L.new(bump.outputs[0], b.inputs['Normal'])
    return m


def build(C):
    rnd = random.Random(2)
    C.set_world((0.006, 0.004, 0.005))
    m_cortex = granular(C, 'cortex', (0.62, 0.20, 0.14), (0.50, 0.13, 0.10))
    m_caps = C.mat('capsule', (0.40, 0.09, 0.07), rough=0.28, sss=0.3, coat=0.8)
    m_rim = C.mat('capsule_rim', (0.88, 0.74, 0.66), rough=0.4, sss=0.4)
    m_pyr = pyramid_mat(C, 'pyramid')
    m_fat = granular(C, 'sinus_fat', (0.90, 0.72, 0.36), (0.80, 0.58, 0.26), scale=25.0, dots=False)
    m_pel = C.mat('pelvis', (0.93, 0.84, 0.70), rough=0.3, sss=0.7, sss_radius=(1.0, 0.7, 0.5), sss_scale=0.08, coat=0.6)
    m_art = C.mat('artery', (0.78, 0.03, 0.03), rough=0.25, sss=0.3, coat=0.8)
    m_ven = C.mat('vein', (0.10, 0.16, 0.62), rough=0.25, sss=0.3, sss_radius=(0.3, 0.4, 1.0), coat=0.8)

    # тіло нирки позаду площини розрізу: контур, що звужується куполом
    bm = bmesh.new(); rows = []; depth, K = 1.45, 14
    for k in range(K + 1):
        a = math.pi / 2 * k / K; s = math.cos(a) * 0.999 + 0.001
        rows.append([bm.verts.new((0.1 + (x - 0.1) * s, depth * math.sin(a), z * s)) for x, z in OUT])
    n = len(OUT)
    for r0, r1 in zip(rows[:-1], rows[1:]):
        for i in range(n):
            bm.faces.new((r0[i], r0[(i + 1) % n], r1[(i + 1) % n], r1[i]))
    for f in bm.faces:
        f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new('body'); bm.to_mesh(me); bm.free(); me.materials.append(m_caps)
    C.link(bpy.data.objects.new('body', me))
    # зріз: кора
    flat('cut', OUT, 0.0, m_cortex, C)
    C.tube('rim', [(x, -0.005, z) for x, z in OUT], 0.035, m_rim, cyclic=True, res=6)

    # пазуха з жировою клітковиною: відкрита до воріт
    sinus = []
    for i in range(72):
        deg = i * 5; d = min(abs(deg), abs(deg - 360)) / 57.3
        f = 0.30 + 0.72 * math.exp(-(d / 0.55) ** 2)
        p = at(deg, min(f, 1.0)); sinus.append((p[0], p[2]))
    flat('sinus', sinus, -0.004, m_fat, C)

    # піраміди
    apex = {}
    for deg in PYR:
        ap = at(deg, 0.33); apex[deg] = ap
        th = math.radians(deg)
        loc = [(0.0, -0.035), (0.04, -0.06)]                      # заокруглений сосочок
        for j in range(11):
            d2 = deg - 17 + 34 * j / 10
            p = at(d2, 0.775)
            dx, dz = p[0] - ap[0], p[2] - ap[2]
            loc.append((dx * math.cos(th) + dz * math.sin(th), -dx * math.sin(th) + dz * math.cos(th)))
        loc += [(0.04, 0.06), (0.0, 0.035)]
        o = flat(f'pyr{deg}', loc, -0.002, m_pyr, C, thick=0.03)
        o.location = (ap[0], 0, ap[2]); o.rotation_euler = (0, -th, 0)

    # чашечки, миска, сечовід
    YP = -0.05
    node = {'u': (SX + 0.22, YP, 0.78), 'm': (SX - 0.05, YP, 0.0), 'l': (SX + 0.22, YP, -0.78)}
    grp = {54: 'u', 96: 'u', 138: 'm', 180: 'm', 222: 'm', 264: 'l', 306: 'l'}
    PV = (SX + 0.52, YP, -0.05)
    for deg in PYR:
        a = apex[deg]; nd = node[grp[deg]]
        tip = at(deg, 0.36, YP)
        mid = tuple((u + v) / 2 for u, v in zip(tip, nd))
        C.tube(f'minor{deg}', [tip, at(deg, 0.30, YP), mid, nd], 0.10, m_pel, radii=[1.75, 1.35, 0.95, 1.1], res=10)
    for k in 'uml':
        C.tube(f'major{k}', [node[k], tuple((u + v) / 2 for u, v in zip(node[k], PV)), PV], 0.15, m_pel, radii=[0.95, 1.1, 1.5], res=10)
        C.prim('sphere', f'node{k}', m_pel, loc=node[k], scale=(0.15,) * 3, u=20, v=12)
    ureter = [PV, (SX + 0.78, YP, -0.35), (SX + 0.98, YP - 0.05, -1.05), (SX + 1.10, YP - 0.1, -2.0), (SX + 1.12, YP - 0.1, -3.4), (SX + 1.05, YP - 0.1, -6.5)]
    C.tube('pelvis', ureter, 0.11, m_pel, radii=[3.3, 3.0, 1.9, 1.15, 1.0, 1.0], res=12)
    C.prim('sphere', 'pelvis_body', m_pel, loc=PV, scale=(0.37, 0.3, 0.42), u=28, v=16)

    # судини: вена спереду, артерія за нею
    YA, YV = -0.34, -0.50
    A0 = (SX + 0.40, YA, 0.30); V0 = (SX + 0.48, YV, -0.02)
    C.tube('renal_artery', [(9.0, YA, 0.85), (3.4, YA, 0.72), (2.0, YA, 0.52), A0], 0.15, m_art, radii=[1.0, 1.0, 0.95, 0.8], res=12)
    C.tube('renal_vein', [(9.0, YV, 0.18), (3.4, YV, 0.12), (2.0, YV, 0.04), V0], 0.20, m_ven, radii=[1.0, 1.0, 0.95, 0.8], res=12)
    for deg in COL + [33, 327]:
        edge = deg in (33, 327)
        for mat, root, y, off, r in ((m_art, A0, YA, -2.2, 0.050), (m_ven, V0, YV, 2.2, 0.060)):
            d = deg + off
            j = at(d, 0.76 if not edge else 0.62, y * 0.45)
            C.tube('interlobar', [root, at(d, 0.20, y), at(d, 0.42, y * 0.8), j], r, mat, radii=[1.3, 1.1, 0.9, 0.7], res=6)
            if edge:
                continue
            for sgn in (-1, 1):                         # дугові судини над основами пірамід
                arc = [at(d + sgn * k * 3.0, 0.775 + 0.012 * math.sin(k), y * 0.45) for k in range(0, 6)]
                C.tube('arcuate', arc, r * 0.62, mat, radii=[1.0, 0.95, 0.9, 0.8, 0.7, 0.55], res=5)
                for k in (1, 3, 5):                     # міжчасточкові гілочки в кору
                    C.tube('interlobular', [at(d + sgn * k * 3.0, 0.78, y * 0.45), at(d + sgn * k * 3.0 + rnd.uniform(-1, 1), 0.90, y * 0.3)],
                           r * 0.32, mat, smooth=False, res=4)

    C.cam(50, (-3.0, -17.5, 1.5), (-1.2, 0, -0.3))
    C.area('key', (-7, -11, 8), (0, 0, 0), 9, 5200, (1.0, 0.95, 0.9))
    C.area('rim', (7, 7, 5), (0, 0.5, 0), 8, 9000, (1.0, 0.55, 0.4))
    C.area('rim2', (-8, 6, -3), (0, 0.5, 0), 8, 4000, (0.55, 0.7, 1.0))
    C.area('fill', (5, -12, -4), (0, 0, 0), 9, 700, (0.8, 0.85, 1.0))

    out_pt = lambda deg, f=1.0: at(deg, f, -0.02)
    return {
        'kicker': 'Органи · сечова система', 'title': 'Нирка', 'sub': 'Фронтальний розріз', 'scrim': 'none', 'title_at': [96, 96],
        'labels': [
            {'text': 'кіркова речовина', 'p': out_pt(159, 0.90), 'at': [560, 430], 'align': 'right'},
            {'text': 'мозкова речовина', 'sub': 'ниркова піраміда', 'p': out_pt(180, 0.60), 'at': [560, 570], 'align': 'right'},
            {'text': 'фіброзна капсула', 'p': out_pt(215, 1.0), 'at': [560, 760], 'align': 'right'},
            {'text': 'ниркова чашечка', 'p': at(54, 0.25, YP - 0.1), 'at': [1420, 170], 'align': 'left'},
            {'text': 'ниркова артерія', 'p': (2.9, YA - 0.15, 0.67), 'at': [1480, 330], 'align': 'left'},
            {'text': 'ниркова вена', 'p': (3.3, YV - 0.2, 0.12), 'at': [1560, 640], 'align': 'left'},
            {'text': 'ниркова миска', 'p': (PV[0] + 0.1, YP - 0.3, PV[2] - 0.12), 'at': [1420, 780], 'align': 'left'},
            {'text': 'сечовід', 'p': (SX + 1.11, YP - 0.2, -2.6), 'at': [1420, 930], 'align': 'left'},
        ],
    }
