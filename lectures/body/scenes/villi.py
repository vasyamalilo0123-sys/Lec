# Тонка кишка: поле ворсинок, одна — у розрізі (одношаровий епітелій, капілярна сітка, центральна лімфатична судина).
import bpy, bmesh, math, random


def profile(H, R, n=90):
    """Твірна ворсинки: (радіус, висота) від основи до верхівки. Основа розширюється, верхівка заокруглена."""
    Rt = R * 0.88
    pts = []
    for i in range(n + 1):
        u = i / n
        if u < 0.8:
            h = (H - Rt) * u / 0.8
            r = R * (1 - 0.12 * h / H) + 0.30 * math.exp(-h / 0.28)
            top = R * (1 - 0.12 * (H - Rt) / H)
        else:
            a = (u - 0.8) / 0.2 * math.pi / 2
            h = (H - Rt) + Rt * math.sin(a)
            r = max(0.0, top * math.cos(a))
        pts.append((r, h))
    return pts


def revolve(name, prof, a0, a1, segs, inset=0.0, bend=0.0, link=None):
    """Поверхня обертання твірної навколо осі Z на кут [a0, a1]; inset зменшує радіус (внутрішня стінка)."""
    bm = bmesh.new(); rows = []
    for r, h in prof:
        r = max(0.0, r - inset)
        rows.append([bm.verts.new((r * math.cos(a0 + (a1 - a0) * s / segs) + bend * h * h, r * math.sin(a0 + (a1 - a0) * s / segs), h))
                     for s in range(segs + 1)])
    for a, b in zip(rows[:-1], rows[1:]):
        for s in range(segs):
            try:
                bm.faces.new((a[s], a[s + 1], b[s + 1], b[s]))
            except ValueError:
                pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return me


def velvet(C, name, c1, c2, cell_scale=38.0):
    """Оксамитова слизова: мозаїка клітин (Вороний), підповерхневе розсіювання, ворс (sheen)."""
    m = C.mat(name, c1, rough=0.55, sss=0.7, sss_radius=(1.0, 0.35, 0.25), sss_scale=0.12, coat=0.15)
    nt = m.node_tree; N, L = nt.nodes, nt.links; b = N['P']
    b.inputs['Sheen Weight'].default_value = 0.6; b.inputs['Sheen Roughness'].default_value = 0.4
    tc = N.new('ShaderNodeTexCoord')
    vor = N.new('ShaderNodeTexVoronoi'); vor.feature = 'DISTANCE_TO_EDGE'; vor.inputs['Scale'].default_value = cell_scale
    L.new(tc.outputs['Object'], vor.inputs['Vector'])
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Max'].default_value = 0.08; L.new(vor.outputs['Distance'], mr.inputs['Value'])
    noise = N.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 1.4; L.new(tc.outputs['Object'], noise.inputs['Vector'])
    col = N.new('ShaderNodeMixRGB'); col.inputs['Color1'].default_value = (*c1, 1); col.inputs['Color2'].default_value = (*c2, 1)
    L.new(noise.outputs['Fac'], col.inputs['Fac'])
    dark = N.new('ShaderNodeMixRGB'); dark.blend_type = 'MULTIPLY'; dark.inputs['Color2'].default_value = (0.62, 0.42, 0.42, 1)
    inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; L.new(mr.outputs[0], inv.inputs[1])
    L.new(inv.outputs[0], dark.inputs['Fac']); L.new(col.outputs[0], dark.inputs['Color1']); L.new(dark.outputs[0], b.inputs['Base Color'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.5; bump.inputs['Distance'].default_value = 0.03
    L.new(mr.outputs[0], bump.inputs['Height']); L.new(bump.outputs[0], b.inputs['Normal'])
    return m


def resample(prof, step):
    """Точки твірної через рівні відрізки довжини: (r, h, кут дотичної)."""
    out = []; acc = 0.0; nxt = step / 2
    for (r0, h0), (r1, h1) in zip(prof[:-1], prof[1:]):
        d = math.hypot(r1 - r0, h1 - h0)
        while d > 0 and acc + d >= nxt:
            t = (nxt - acc) / d
            out.append((r0 + (r1 - r0) * t, h0 + (h1 - h0) * t, math.atan2(h1 - h0, r1 - r0)))
            nxt += step
        acc += d
    return out


def build(C):
    rnd = random.Random(5)
    C.set_world((0.012, 0.004, 0.004))
    m_vil = velvet(C, 'villus', (0.86, 0.42, 0.40), (0.74, 0.30, 0.30))
    m_base = velvet(C, 'mucosa', (0.66, 0.26, 0.27), (0.52, 0.18, 0.20), cell_scale=22.0)
    m_inner = C.mat('lamina', (0.93, 0.66, 0.60), rough=0.6, sss=0.6, sss_radius=(1.0, 0.4, 0.3), sss_scale=0.1)
    m_cell = [C.mat('ep_a', (0.90, 0.50, 0.50), rough=0.35, sss=0.6, coat=0.5), C.mat('ep_b', (0.80, 0.40, 0.44), rough=0.35, sss=0.6, coat=0.5)]
    m_nuc = C.mat('nucleus', (0.20, 0.10, 0.42), rough=0.3, coat=0.5)
    m_art = C.mat('artery', (0.78, 0.03, 0.03), rough=0.28, sss=0.3, coat=0.7)
    m_ven = C.mat('vein', (0.10, 0.15, 0.60), rough=0.28, sss=0.3, sss_radius=(0.3, 0.4, 1.0), coat=0.7)
    m_mid = C.mat('capmid', (0.45, 0.08, 0.35), rough=0.28, sss=0.3, coat=0.7)
    m_lymph = C.mat('lacteal', (0.95, 0.90, 0.66), rough=0.25, sss=0.8, sss_radius=(1.0, 0.9, 0.6), sss_scale=0.15, coat=0.6)
    m_pit = C.mat('pit', (0.10, 0.02, 0.025), rough=0.7)

    # основа слизової
    base = C.prim('cube', 'base', m_base, loc=(0, 8, -0.5), scale=(40, 30, 0.5))

    # --- ворсинка в розрізі ---
    H, R, HX, HY = 4.0, 0.62, 0.9, 0.0
    T = 0.15                                            # товщина епітелію
    prof = profile(H, R)
    for nm, me, mt in (('hero_out', revolve('hero_out', prof, 0, math.pi, 40), m_vil),
                       ('hero_in', revolve('hero_in', prof, 0, math.pi, 40, inset=T), m_inner)):
        o = C.link(bpy.data.objects.new(nm, me)); o.location = (HX, HY, 0); me.materials.append(mt)
    # одношаровий епітелій на зрізі: ряд клітин уздовж обох країв, у кожній ядро біля основи
    ep_label = None
    cells = resample(prof, 0.118)
    for side in (-1, 1):
        for j, (r, h, ang) in enumerate(cells):
            if r < 0.09:
                continue
            nx, nz = math.sin(ang), -math.cos(ang)       # нормаль назовні в площині зрізу
            cx, cz = r - nx * T / 2, h - nz * T / 2
            rot = (0, -(ang - math.pi / 2) * side, 0)
            C.prim('sphere', f'ep{side}{j}', m_cell[j % 2], loc=(HX + side * cx, HY - 0.01, cz), scale=(T / 2 * 1.05, 0.055, 0.066), rot=rot, u=16, v=10)
            bx, bz = r - nx * T * 0.72, h - nz * T * 0.72
            C.prim('sphere', f'nu{side}{j}', m_nuc, loc=(HX + side * bx, HY - 0.05, bz), scale=(0.026, 0.026, 0.034), rot=rot, u=12, v=8)
            if side == -1 and ep_label is None and h > 2.0:
                ep_label = (HX - cx, HY - 0.06, cz)
    # центральна лімфатична судина: сліпо закінчується під верхівкою
    lac = [(HX + 0.03 * math.sin(h * 2.0), HY + 0.16, h) for h in [-0.4 + i * 0.25 for i in range(15)]]
    C.tube('lacteal', lac, 0.115, m_lymph, radii=[1.0] * 12 + [1.08, 1.12, 0.95], res=10)
    # артеріола піднімається, венула спускається; між ними під епітелієм — капілярна сітка
    rin = lambda h: max(0.05, R * (1 - 0.12 * h / H) + 0.30 * math.exp(-h / 0.28) - T - 0.09)
    hs = [-0.4 + i * 0.2 for i in range(20)]
    art = [(HX - 0.62 * rin(h) + 0.02 * math.sin(h * 5), HY + 0.10, h) for h in hs]
    ven = [(HX + 0.62 * rin(h) + 0.02 * math.cos(h * 5), HY + 0.10, h) for h in hs]
    C.tube('arteriole', art, 0.05, m_art, radii=[1.25 - 0.4 * i / 19 for i in range(20)], res=8)
    C.tube('venule', ven, 0.058, m_ven, radii=[1.25 - 0.4 * i / 19 for i in range(20)], res=8)
    cap_label = None
    n_arc = 13
    for k in range(n_arc):
        h0 = 0.55 + k * (3.35 - 0.55) / (n_arc - 1)
        rr = rin(h0) * 0.92
        arc = []
        for i in range(25):
            a = math.pi * (1 - i / 24)                    # від артеріоли (ліворуч) позаду просвіту до венули
            x0 = 0.62 * rin(h0)
            ex = (x0 + (rr - x0) * math.sin(a) ** 0.5) * math.cos(a) / max(1e-6, abs(math.cos(a))) if abs(math.cos(a)) > 1e-6 else 0.0
            x = math.cos(a) * (0.62 * rin(h0) * (1 - math.sin(a)) + rr * math.sin(a))
            y = 0.10 + (rr - 0.02) * math.sin(a) * 0.95
            z = h0 + 0.07 * math.sin(a * 3 + k * 1.7) + 0.10 * math.sin(a) * (1 if k % 2 else -1)
            arc.append((HX + x, HY + y, z))
        C.tube(f'capA{k}', arc[:10], 0.022, m_art, res=5)
        C.tube(f'capM{k}', arc[9:16], 0.022, m_mid, res=5)
        C.tube(f'capV{k}', arc[15:], 0.022, m_ven, res=5)
        if k == 8:
            cap_label = arc[5]
    # дуга над верхівкою лімфатичної судини
    top = [(HX + 0.62 * rin(3.4) * math.cos(math.pi * (1 - i / 12)), HY + 0.10, 3.4 + 0.22 * math.sin(math.pi * i / 12)) for i in range(13)]
    C.tube('topA', top[:7], 0.035, m_art, res=6); C.tube('topV', top[6:], 0.035, m_ven, res=6)

    # --- поле ворсинок ---
    variants = []
    for v, (h, r, bend) in enumerate(((3.9, 0.60, 0.012), (3.5, 0.66, -0.016), (4.3, 0.56, 0.008), (3.2, 0.62, 0.02))):
        me = revolve(f'villus{v}', profile(h, r, 60), 0, 2 * math.pi, 32, bend=bend); me.materials.append(m_vil)
        variants.append((me, h))
    whole_label = None; spots = []
    sx, sy = 1.95, 1.7
    for iy in range(-3, 22):
        for ix in range(-14, 15):
            x = ix * sx + (sx / 2 if iy % 2 else 0) + rnd.uniform(-0.3, 0.3)
            y = iy * sy + rnd.uniform(-0.3, 0.3)
            # перед зрізом — вільний простір, щоб його було видно
            if y < HY + 0.9 and abs(x - HX) < 2.9 - 0.25 * min(0, y):
                continue
            if math.hypot(x - HX, y - HY) < 1.5:
                continue
            me, h = variants[rnd.randrange(len(variants))]
            o = C.link(bpy.data.objects.new('villus', me)); o.location = (x, y, 0)
            o.rotation_euler = (rnd.uniform(-0.07, 0.07), rnd.uniform(-0.07, 0.07), rnd.uniform(0, 6.28))
            s = rnd.uniform(0.9, 1.08); o.scale = (s, s, s * rnd.uniform(0.92, 1.08))
            spots.append((x, y))
            if whole_label is None and 2.6 < x - HX < 3.6 and 0.9 < y < 2.6:
                whole_label = (x, y - 0.5, h * s * 0.72)
    # устя крипт між основами ворсинок
    crypt_label = None
    for iy in range(-4, 20):
        for ix in range(-12, 13):
            x = ix * sx + (0 if iy % 2 else sx / 2) + rnd.uniform(-0.15, 0.15)
            y = iy * sy + sy * 0.5 + rnd.uniform(-0.15, 0.15)
            if math.hypot(x - HX, y - HY) < 1.1 or any(math.hypot(x - a, y - b) < 0.95 for a, b in spots):
                continue
            ring = [(x + 0.19 * math.cos(2 * math.pi * i / 16), y + 0.19 * math.sin(2 * math.pi * i / 16), 0.0) for i in range(16)]
            C.tube('crypt', ring, 0.065, m_base, cyclic=True, res=5)
            C.prim('cyl', 'pit', m_pit, loc=(x, y, 0.004), segs=20, r1=0.17, r2=0.17, depth=0.02)
            if crypt_label is None and -1.9 < x - HX < -0.9 and -1.9 < y < -0.6:
                crypt_label = (x, y, 0.02)

    C.cam(55, (0.2, -10.2, 3.5), (0.75, 0, 2.05), fstop=0.3, focus=10.3)
    C.area('key', (-5, -7, 9), (0.9, 0, 2), 7, 2600, (1.0, 0.94, 0.9))
    C.area('rim', (6, 10, 7), (0.9, 0, 2.5), 9, 9000, (1.0, 0.6, 0.45))
    C.area('rim2', (-9, 9, 4), (0, 2, 2), 8, 3500, (1.0, 0.5, 0.5))
    C.area('fill', (4, -9, 1.5), (0.9, 0, 2), 5, 500, (0.75, 0.82, 1.0))

    return {
        'kicker': 'Тканини · епітеліальна', 'title': 'Ворсинки\nтонкої кишки', 'title_size': 84,
        'sub': 'Один шар клітин між їжею і кров\'ю', 'scrim': 'left', 'title_at': [96, 96],
        'labels': [
            {'text': 'епітелій', 'sub': 'один шар клітин', 'p': ep_label, 'at': [520, 560], 'align': 'right'},
            {'text': 'лімфатична судина', 'p': lac[9], 'at': [1420, 250], 'align': 'left'},
            {'text': 'капіляри', 'p': cap_label, 'at': [520, 420], 'align': 'right'},
            {'text': 'ворсинка', 'p': whole_label or (HX + 3, 1.5, 2.8), 'at': [1560, 520], 'align': 'left'},
            {'text': 'крипта', 'p': crypt_label or (HX - 1.4, -1.2, 0), 'at': [520, 900], 'align': 'right'},
        ],
    }
