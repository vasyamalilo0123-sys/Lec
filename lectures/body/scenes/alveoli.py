# Альвеоли: гроно тонкостінних мішечків на кінці бронхіоли; головну альвеолу обплітає сітка капілярів,
# у яких еритроцити йдуть по одному. Ліворуч кров венозна (темна), праворуч — уже насичена киснем (яскрава).
import bpy, math, random
from mathutils import Vector

HERO = Vector((0.0, 0.0, 0.0))
R = 1.7


def membrane(C):
    """Стінка альвеоли: майже прозора в центрі, щільніша на краях силуету, волога."""
    m = C.new_mat('membrane'); nt = m.node_tree; N, L = nt.nodes, nt.links
    tc = N.new('ShaderNodeTexCoord')
    vor = N.new('ShaderNodeTexVoronoi'); vor.feature = 'DISTANCE_TO_EDGE'; vor.inputs['Scale'].default_value = 3.2
    L.new(tc.outputs['Object'], vor.inputs['Vector'])
    ns = N.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = 1.6; ns.inputs['Detail'].default_value = 4
    L.new(tc.outputs['Object'], ns.inputs['Vector'])
    mn = N.new('ShaderNodeMath'); mn.operation = 'MINIMUM'; mn.inputs[1].default_value = 0.06
    L.new(vor.outputs['Distance'], mn.inputs[0])
    h = N.new('ShaderNodeMath'); h.operation = 'MULTIPLY_ADD'; h.inputs[1].default_value = 5.0
    L.new(mn.outputs[0], h.inputs[0]); L.new(ns.outputs['Fac'], h.inputs[2])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.35; bump.inputs['Distance'].default_value = 0.08
    L.new(h.outputs[0], bump.inputs['Height'])
    b = N.new('ShaderNodeBsdfPrincipled')
    b.inputs['Base Color'].default_value = (0.93, 0.56, 0.50, 1); b.inputs['Roughness'].default_value = 0.28
    b.inputs['Subsurface Weight'].default_value = 1.0; b.inputs['Subsurface Radius'].default_value = (1.0, 0.45, 0.3)
    b.inputs['Subsurface Scale'].default_value = 0.25
    b.inputs['Coat Weight'].default_value = 0.7; b.inputs['Coat Roughness'].default_value = 0.12
    L.new(bump.outputs[0], b.inputs['Normal']); L.new(bump.outputs[0], b.inputs['Coat Normal'])
    lw = N.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.45
    L.new(bump.outputs[0], lw.inputs['Normal'])
    pw = N.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 1.6
    L.new(lw.outputs['Facing'], pw.inputs[0])
    fac = N.new('ShaderNodeMapRange'); fac.inputs['To Min'].default_value = 0.3; fac.inputs['To Max'].default_value = 1.0
    L.new(pw.outputs[0], fac.inputs['Value'])
    tr = N.new('ShaderNodeBsdfTransparent'); tr.inputs['Color'].default_value = (1.0, 0.86, 0.82, 1)
    mix = N.new('ShaderNodeMixShader')
    L.new(fac.outputs[0], mix.inputs[0]); L.new(tr.outputs[0], mix.inputs[1]); L.new(b.outputs[0], mix.inputs[2])
    out = N.new('ShaderNodeOutputMaterial'); L.new(mix.outputs[0], out.inputs['Surface'])
    return m


def fib_sphere(n):
    g = math.pi * (3 - math.sqrt(5))
    return [Vector((math.cos(g * i) * math.sqrt(1 - (1 - 2 * (i + 0.5) / n) ** 2), math.sin(g * i) * math.sqrt(1 - (1 - 2 * (i + 0.5) / n) ** 2),
                    1 - 2 * (i + 0.5) / n)) for i in range(n)]


def arc(a, b, steps, rnd, wob=0.05):
    """Дуга по сфері між одиничними напрямками a і b, трохи хвиляста."""
    pts = []
    side = a.cross(b).normalized()
    for i in range(steps + 1):
        t = i / steps
        d = a.slerp(b, t)
        d = (d + side * math.sin(t * math.pi) * rnd.uniform(-wob, wob) * 2).normalized()
        pts.append(d)
    return pts


def build(C):
    rnd = random.Random(12)
    C.set_world((0.010, 0.003, 0.003))
    m_mem = membrane(C)
    m_duct = C.mat('duct', (0.85, 0.45, 0.40), rough=0.4, sss=0.8, sss_radius=(1.0, 0.4, 0.3), sss_scale=0.2, coat=0.4)

    # гроно: головна альвеола окремо (щоб сітка лягла на рівну сферу), сусідні зливаються між собою
    balls = []
    core = Vector((0.6, 3.4, 1.0))
    for d in fib_sphere(26):
        p = core + Vector((d.x * 2.9, d.y * 2.3, d.z * 2.7))
        if (p - HERO).length < R + 0.75 or p.y < -0.4:
            continue
        balls.append((p.x, p.y, p.z, rnd.uniform(1.6, 2.1)))
    cl = C.metaballs('cluster', balls, m_mem, resolution=0.09, threshold=0.9)
    hero = C.prim('sphere', 'hero', m_mem, loc=HERO, scale=(R, R, R), u=96, v=48)
    C.displace(hero, 0.05, 1.2)
    C.tube('bronchiole', [core + Vector((-4.5, 5, 9)), core + Vector((-2.2, 3, 5.5)), core + Vector((-0.6, 0.8, 2.6)), core], 0.75, m_duct,
           radii=[1.0, 1.0, 1.1, 1.5], res=10)

    # капілярна сітка на головній альвеолі
    def lerp3(a, b, t):
        return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
    STEPS = 6
    glass = [C.mat(f'cap{i}', lerp3((0.55, 0.60, 1.0), (1.0, 0.60, 0.55), i / (STEPS - 1)), rough=0.08, transmission=1.0, ior=1.12, coat=0.3,
                   emission=lerp3((0.25, 0.30, 1.0), (1.0, 0.25, 0.2), i / (STEPS - 1)), emission_strength=0.12)
             for i in range(STEPS)]
    blood = [C.mat(f'rbc{i}', lerp3((0.13, 0.03, 0.34), (0.90, 0.04, 0.02), i / (STEPS - 1)), rough=0.32, sss=1.0,
                   sss_radius=(1.0, 0.25, 0.12), sss_scale=0.03, coat=0.35,
                   emission=lerp3((0.13, 0.03, 0.34), (0.90, 0.04, 0.02), i / (STEPS - 1)), emission_strength=0.35) for i in range(STEPS)]
    rbcs = []
    for i in range(STEPS):
        me = C.rbc_mesh(f'RBC{i}', 32, 10); me.materials.append(blood[i])
        o = C.link(bpy.data.objects.new(f'rbc_src{i}', me)); o.location = (0, 0, 80); rbcs.append(o)

    def oxy(p):          # 0 — венозна кров (ліворуч), 1 — артеріальна (праворуч)
        return max(0, min(STEPS - 1, int((p.x / R * 0.5 + 0.5) * STEPS)))

    def vessel(pts, radius, n_cells):
        mid = pts[len(pts) // 2]
        t_ = C.tube('cap', pts, radius, glass[oxy(mid)], res=6)
        t_.visible_shadow = False            # скло не затіняє клітини всередині
        for k in range(n_cells):
            t = (k + rnd.uniform(0.25, 0.75)) / n_cells * (len(pts) - 1)
            i = min(int(t), len(pts) - 2)
            p = pts[i].lerp(pts[i + 1], t - i); tan = (pts[i + 1] - pts[i]).normalized()
            q = tan.to_track_quat('Z', 'Y')
            o = C.instance(rbcs[oxy(p)], 'rbc', p, scale=radius * rnd.uniform(0.74, 0.86))
            o.rotation_euler = (q @ Vector((0, 0, 1)).rotation_difference(
                Vector((rnd.uniform(-0.25, 0.25), rnd.uniform(-0.25, 0.25), 1)).normalized())).to_euler()

    nodes = fib_sphere(46)
    edges = set()
    for i, a in enumerate(nodes):
        near = sorted(range(len(nodes)), key=lambda j: (nodes[j] - a).length)[1:4]
        for j in near:
            edges.add((min(i, j), max(i, j)))
    RC = R + 0.085
    for i, j in sorted(edges):
        if nodes[i].y > 0.75 and nodes[j].y > 0.75:      # задню стінку закриває гроно
            continue
        pts = [HERO + d * RC for d in arc(nodes[i], nodes[j], 6, rnd)]
        vessel(pts, 0.085, max(1, int((pts[0] - pts[-1]).length / 0.3)))
    # приносна (венозна кров, ліворуч) і виносна (артеріальна, праворуч) судини
    lp, rp = Vector((-1, -0.25, -0.2)).normalized(), Vector((1, -0.2, -0.15)).normalized()
    vessel([HERO + Vector((-6.5, 0.8, -4.2)), HERO + Vector((-4.2, 0.2, -2.6)), HERO + Vector((-2.7, -0.3, -1.1)), HERO + lp * RC], 0.15, 16)
    vessel([HERO + rp * RC, HERO + Vector((2.8, -0.3, -1.0)), HERO + Vector((4.4, 0.3, -2.4)), HERO + Vector((6.8, 1.0, -3.8))], 0.15, 16)

    # молекули: O₂ (блакитні) з альвеоли до крові, CO₂ (бурштинові) — назустріч
    m_o2 = C.mat_emit('o2', (0.1, 0.55, 1.0), 4.0); m_co2 = C.mat_emit('co2', (1.0, 0.4, 0.05), 3.5)
    dot = [C.prim('ico', 'o2_src', m_o2, loc=(0, 0, 90), subdiv=1), C.prim('ico', 'co2_src', m_co2, loc=(0, 0, 90), subdiv=1)]
    for k in range(70):
        d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 0.1), rnd.uniform(-1, 1))).normalized()
        o2 = d.x > rnd.uniform(-0.5, 0.5)
        rr = R * (rnd.uniform(0.72, 1.0) if o2 else rnd.uniform(0.86, 1.0))
        C.instance(dot[0 if o2 else 1], 'gas', HERO + d * rr, scale=rnd.uniform(0.024, 0.036))

    C.cam(50, (-1.7, -12.5, 0.9), (-1.7, 0, 0.1), fstop=1.1, focus=10.9)
    sc = bpy.context.scene; sc.cycles.max_bounces = 5; sc.cycles.transmission_bounces = 4; sc.cycles.diffuse_bounces = 2
    C.area('back', (2.5, 9, 6), (0, 1.5, 0.5), 7, 16000, (1.0, 0.62, 0.5))
    C.area('key', (-5, -6, 5), HERO, 5, 1500, (1.0, 0.95, 0.9))
    C.area('rim', (7, 2.5, -1), HERO, 4, 4200, (0.55, 0.72, 1.0))
    C.area('kick', (-7, 3, -2), HERO, 4, 2500, (1.0, 0.5, 0.4))
    kn = max(nodes, key=lambda d: d.x * 0.6 - d.z - d.y)
    return {
        'kicker': 'Легені · газообмін', 'title': 'Альвеола', 'sub': 'Повітря і кров розділяє\nлише найтонша стінка',
        'scrim': 'right', 'title_at': [96, 96], 'title_size': 104,
        'labels': [
            {'text': 'альвеола', 'sub': 'повітряний мішечок', 'p': list(HERO + Vector((0.2, -0.8, 0.6)).normalized() * R), 'at': [1560, 110], 'align': 'left'},
            {'text': 'O₂ → у кров', 'p': list(HERO + Vector((0.8, -0.6, 0.05)).normalized() * R), 'at': [1630, 400], 'align': 'left'},
            {'text': 'капіляр', 'sub': 'еритроцити йдуть по одному', 'p': list(HERO + kn * RC), 'at': [1480, 930], 'align': 'left'},
            {'text': 'CO₂ → в альвеолу', 'p': list(HERO + Vector((-0.8, -0.55, 0.1)).normalized() * R), 'at': [640, 700], 'align': 'right'},
        ],
    }
