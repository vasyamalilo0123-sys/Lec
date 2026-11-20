# М'язова тканина: пучок посмугованих волокон, розкритий сходинками — перимізій → ендомізій → волокно → міофібрили.
import bpy, math, random


def striated(C, name, freq, c_dark, c_light, cap_scale=16.0, sss=0.35):
    """Посмугованість уздовж осі циліндра (локальна Z); на торцях — зріз міофібрил (комірки Вороного)."""
    m = C.new_mat(name); nt = m.node_tree; N, L = nt.nodes, nt.links
    tc = N.new('ShaderNodeTexCoord')
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])
    noise = N.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 1.6; noise.inputs['Detail'].default_value = 3
    L.new(tc.outputs['Object'], noise.inputs['Vector'])
    wob = N.new('ShaderNodeMath'); wob.operation = 'MULTIPLY_ADD'; wob.inputs[1].default_value = 0.05
    L.new(noise.outputs['Fac'], wob.inputs[0]); L.new(sep.outputs['Z'], wob.inputs[2])
    fr = N.new('ShaderNodeMath'); fr.operation = 'MULTIPLY'; fr.inputs[1].default_value = freq; L.new(wob.outputs[0], fr.inputs[0])
    sn = N.new('ShaderNodeMath'); sn.operation = 'SINE'; L.new(fr.outputs[0], sn.inputs[0])
    mr = N.new('ShaderNodeMapRange'); mr.interpolation_type = 'SMOOTHSTEP'
    mr.inputs['From Min'].default_value = -0.35; mr.inputs['From Max'].default_value = 0.35
    L.new(sn.outputs[0], mr.inputs['Value'])
    band = N.new('ShaderNodeMixRGB'); band.inputs['Color1'].default_value = (*c_dark, 1); band.inputs['Color2'].default_value = (*c_light, 1)
    L.new(mr.outputs[0], band.inputs['Fac'])
    # торець
    vor = N.new('ShaderNodeTexVoronoi'); vor.feature = 'DISTANCE_TO_EDGE'; vor.inputs['Scale'].default_value = cap_scale
    L.new(tc.outputs['Object'], vor.inputs['Vector'])
    vr = N.new('ShaderNodeMapRange'); vr.inputs['From Min'].default_value = 0.0; vr.inputs['From Max'].default_value = 0.09
    L.new(vor.outputs['Distance'], vr.inputs['Value'])
    capc = N.new('ShaderNodeMixRGB'); capc.inputs['Color1'].default_value = (0.20, 0.02, 0.025, 1); capc.inputs['Color2'].default_value = (0.72, 0.16, 0.14, 1)
    L.new(vr.outputs[0], capc.inputs['Fac'])
    sn2 = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Normal'], sn2.inputs[0])
    ab = N.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'; L.new(sn2.outputs['Z'], ab.inputs[0])
    gt = N.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.8; L.new(ab.outputs[0], gt.inputs[0])
    col = N.new('ShaderNodeMixRGB'); L.new(gt.outputs[0], col.inputs['Fac']); L.new(band.outputs[0], col.inputs['Color1']); L.new(capc.outputs[0], col.inputs['Color2'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.25; bump.inputs['Distance'].default_value = 0.05
    L.new(mr.outputs[0], bump.inputs['Height'])
    b = N.new('ShaderNodeBsdfPrincipled')
    L.new(col.outputs[0], b.inputs['Base Color']); L.new(bump.outputs[0], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.38
    b.inputs['Subsurface Weight'].default_value = sss; b.inputs['Subsurface Radius'].default_value = (1.0, 0.3, 0.2)
    b.inputs['Subsurface Scale'].default_value = 0.12
    b.inputs['Coat Weight'].default_value = 0.45; b.inputs['Coat Roughness'].default_value = 0.2
    out = N.new('ShaderNodeOutputMaterial'); L.new(b.outputs[0], out.inputs['Surface'])
    return m


def sheath_mat(C, name, color, fiber_scale=7.0, rough=0.5):
    """Сполучнотканинна оболонка: бліда, волокниста (шум, розтягнутий уздовж осі)."""
    m = C.mat(name, color, rough=rough, sss=0.5, sss_radius=(1.0, 0.6, 0.45), sss_scale=0.08, coat=0.25)
    nt = m.node_tree; N, L = nt.nodes, nt.links; b = N['P']
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (fiber_scale, fiber_scale, 0.35)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    n = N.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 2.0; n.inputs['Detail'].default_value = 5; L.new(mp.outputs[0], n.inputs['Vector'])
    mix = N.new('ShaderNodeMixRGB'); mix.inputs['Color1'].default_value = (*[c * 0.55 for c in color], 1); mix.inputs['Color2'].default_value = (*color, 1)
    L.new(n.outputs['Fac'], mix.inputs['Fac']); L.new(mix.outputs[0], b.inputs['Base Color'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.5; bump.inputs['Distance'].default_value = 0.06
    L.new(n.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs[0], b.inputs['Normal'])
    return m


def xcyl(C, name, mat, x0, x1, y, z, r, segs=48):
    """Циліндр уздовж осі X від x0 до x1."""
    return C.prim('cyl', name, mat, loc=((x0 + x1) / 2, y, z), rot=(0, math.pi / 2, 0), segs=segs, r1=r, r2=r, depth=x1 - x0)


def build(C):
    rnd = random.Random(8)
    C.set_world((0.010, 0.004, 0.004))
    X0 = -22.0
    S, RF = 1.07, 0.5
    m_fiber = striated(C, 'fiber', 62.0, (0.40, 0.04, 0.045), (0.66, 0.15, 0.13))
    m_fibril = striated(C, 'fibril', 62.0, (0.40, 0.04, 0.045), (0.86, 0.36, 0.30), cap_scale=40.0, sss=0.2)
    m_endo = sheath_mat(C, 'endo', (0.90, 0.66, 0.60))
    m_peri = sheath_mat(C, 'peri', (0.86, 0.74, 0.66), fiber_scale=3.0, rough=0.55)
    m_nuc = C.mat('nucleus', (0.16, 0.10, 0.42), rough=0.35, sss=0.3, sss_radius=(0.4, 0.3, 1.0), coat=0.5)
    m_art = C.mat('cap_red', (0.75, 0.03, 0.03), rough=0.3, sss=0.4, coat=0.6)
    m_ven = C.mat('cap_blue', (0.10, 0.14, 0.55), rough=0.3, sss=0.4, sss_radius=(0.3, 0.4, 1.0), coat=0.6)

    # гексагональне пакування волокон у пучку
    cells = [(q, r) for q in range(-2, 3) for r in range(-2, 3) if max(abs(q), abs(r), abs(q + r)) <= 2]
    pos = {(q, r): (S * (q + r / 2), S * math.sqrt(3) / 2 * r) for q, r in cells}
    ring = {c: max(abs(c[0]), abs(c[1]), abs(c[0] + c[1])) for c in cells}
    end = {}
    for c in cells:
        end[c] = 5.2 if ring[c] == 0 else (rnd.uniform(2.0, 3.0) if ring[c] == 1 else rnd.uniform(-0.8, 0.6))
    toward = math.radians(128)          # бік волокна, звернений до камери
    nuc_label = None
    for c in cells:
        y, z = pos[c]
        r = RF * rnd.uniform(0.95, 1.0)
        xcyl(C, f'fiber{c}', m_fiber, X0, end[c], y, z, r)
        e_end = end[c] - (2.2 if ring[c] == 0 else rnd.uniform(1.5, 2.2))
        xcyl(C, f'endo{c}', m_endo, X0, e_end, y, z, r + 0.035)
        # периферійні ядра на оголеній ділянці волокна
        for k in range(3 if ring[c] < 2 else 2):
            a = toward + rnd.uniform(-1.0, 1.0)
            x = rnd.uniform(e_end + 0.25, end[c] - 0.3)
            if c == (0, 0) and k == 0:
                a, x = toward + 0.1, 4.2
            p = (x, y + (r + 0.012) * math.cos(a), z + (r + 0.012) * math.sin(a))
            C.prim('sphere', f'nuc{c}{k}', m_nuc, loc=p, scale=(0.17, 0.062, 0.03), rot=(a - math.pi / 2, 0, 0), u=24, v=12)
            if c == (0, 0) and k == 0:
                nuc_label = p
    # міофібрили виходять із центрального волокна
    tips = []
    for i in range(46):
        rr = 0.43 * math.sqrt((i + 0.5) / 46); a = i * 2.39996
        y, z = rr * math.cos(a), rr * math.sin(a)
        x1 = 5.2 + rnd.uniform(0.9, 2.3) * (1.0 - 0.35 * rr / 0.43)
        xcyl(C, f'fibril{i}', m_fibril, 4.6, x1, y, z, 0.048, segs=14)
        tips.append((x1, y, z))
    # капіляри в проміжках між волокнами
    cap_label = None; k = 0
    for q, r in cells:
        for tri in (((q, r), (q + 1, r), (q, r + 1)), ((q + 1, r), (q, r + 1), (q + 1, r + 1))):
            if not all(t in pos for t in tri):
                continue
            k += 1
            cy = sum(pos[t][0] for t in tri) / 3; cz = sum(pos[t][1] for t in tri) / 3
            ends = sorted(end[t] for t in tri)
            x1 = ends[1] + rnd.uniform(0.2, 0.7)
            pts = []
            n = 40
            for j in range(n + 1):
                x = X0 + (x1 - X0) * j / n
                pts.append((x, cy + 0.035 * math.sin(x * 2.1 + k), cz + 0.035 * math.cos(x * 1.7 + k * 2)))
            C.tube(f'cap{k}', pts, 0.07, m_art if k % 3 else m_ven, res=5)
            if k == 7:                      # капіляр, добре видний камері
                cap_label = pts[37]
    # перимізій довкола пучка
    C.tube('peri', [(X0, 0, 0), (-12, 0, 0), (-3.6, 0, 0)], 2.95, m_peri, res=24, smooth=False, caps=False)
    C.tube('peri_in', [(X0, 0, 0), (-12, 0, 0), (-3.55, 0, 0)], 2.82, m_peri, res=24, smooth=False, caps=False)
    # сусідні пучки — розмите тло
    m_far = sheath_mat(C, 'far', (0.36, 0.17, 0.15), fiber_scale=3.0)
    for i, (y, z) in enumerate(((1.5, -6.3), (7.6, -5.2), (-4.6, -6.0), (12.5, -2.5))):
        xcyl(C, f'bundle{i}', m_far, -40, 40, y, z, 3.0)

    C.cam(42, (12.0, -17.0, 9.5), (-1.8, 0, 2.0), fstop=0.5, focus=21.0)
    C.area('key', (2, -10, 12), (2, 0, 0), 10, 5200, (1.0, 0.95, 0.9))
    C.area('rim', (14, 9, 5), (4, 0, 0), 7, 9000, (1.0, 0.62, 0.45))
    C.area('fill', (-6, -12, -4), (0, 0, 0), 9, 900, (0.7, 0.8, 1.0))

    hero_top = lambda x: (x, RF * math.cos(toward), RF * math.sin(toward))
    tip = max(tips)
    c1 = (0, 1)   # волокно першого кільця, звернене до камери
    y1, z1 = pos[(-1, 1)]
    return {
        'kicker': 'Тканини · м\'язова', 'title': 'Посмугований м\'яз', 'sub': 'Від пучка до скоротливих ниток',
        'scrim': 'left', 'title_at': [96, 96],
        'labels': [
            {'text': 'міофібрили', 'p': (tip[0] - 0.5, tip[1], tip[2]), 'at': [1500, 300], 'align': 'left'},
            {'text': 'м\'язове волокно', 'p': hero_top(3.6), 'at': [1180, 170], 'align': 'left'},
            {'text': 'ядро', 'p': nuc_label, 'at': [1560, 750], 'align': 'left'},
            {'text': 'капіляр', 'p': cap_label or (2, -0.5, 0.9), 'at': [1010, 990], 'align': 'left'},
            {'text': 'ендомізій', 'p': (end[(-1, 1)] - 2.6, y1 + (RF + 0.04) * math.cos(toward), z1 + (RF + 0.04) * math.sin(toward)), 'at': [560, 900], 'align': 'right'},
            {'text': 'перимізій', 'p': (-4.6, 2.95 * math.cos(toward), 2.95 * math.sin(toward)), 'at': [330, 440], 'align': 'right'},
        ],
    }
