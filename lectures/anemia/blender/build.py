# Сцени ролика «Анемія за одну хвилину» для Blender (Cycles). Усе будується кодом, готових моделей немає.
# build(shot, nframes) створює одну з чотирьох сцен: flow, third, sizes, outro.
import bpy, bmesh, math, random
from mathutils import Vector

FPS = 24
R_VESSEL = 11.0
WALL_GLOW = 1.0


# ---------- основа ----------
def reset(nframes):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 0, nframes - 1
    sc.render.fps = FPS
    sc.render.engine = 'CYCLES'
    c = sc.cycles
    c.device = 'CPU'
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.1
    c.use_denoising = True
    c.denoiser = 'OPENIMAGEDENOISE'
    c.max_bounces = 4
    c.diffuse_bounces = 2
    c.glossy_bounces = 2
    c.transmission_bounces = 2
    c.volume_bounces = 0
    c.caustics_reflective = False
    c.caustics_refractive = False
    sc.render.use_persistent_data = True
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = 0.5
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Punchy'
    except Exception:
        pass
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.image_settings.compression = 15
    w = bpy.data.worlds.new('World')
    sc.world = w
    w.use_nodes = True
    return sc


def set_world(color, strength=1.0):
    bg = bpy.context.scene.world.node_tree.nodes['Background']
    bg.inputs[0].default_value = (*color, 1)
    bg.inputs[1].default_value = strength


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def linear_keys(on=True):
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR' if on else 'BEZIER'


# ---------- геометрія ----------
def rbc_mesh(name, segs=48, rings=14):
    """Двоввігнутий диск за профілем Еванса–Фанга, радіус 1."""
    def z(rho):
        return 0.5 * math.sqrt(max(0.0, 1 - rho * rho)) * (0.81 + 7.83 * rho ** 2 - 4.39 * rho ** 4) / 3.91
    bm = bmesh.new()
    top = bm.verts.new((0, 0, z(0)))
    bot = bm.verts.new((0, 0, -z(0)))
    loops = []
    order = [(k, 1) for k in range(1, rings + 1)] + [(k, -1) for k in range(rings - 1, 0, -1)]
    for k, sgn in order:
        rho = math.sin(math.pi / 2 * k / rings)
        loops.append([bm.verts.new((rho * math.cos(2 * math.pi * s / segs), rho * math.sin(2 * math.pi * s / segs), sgn * z(rho)))
                      for s in range(segs)])
    for s in range(segs):
        s2 = (s + 1) % segs
        bm.faces.new((top, loops[0][s], loops[0][s2]))
        for a, b in zip(loops[:-1], loops[1:]):
            bm.faces.new((a[s], b[s], b[s2], a[s2]))
        bm.faces.new((loops[-1][s], bot, loops[-1][s2]))
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def blob_mesh(name, radius, subdiv=3, bump=0.12, seed=0):
    rnd = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    ph = [(rnd.uniform(1.5, 4), rnd.uniform(0, 6.28), Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).normalized())
          for _ in range(7)]
    for v in bm.verts:
        n = v.co.normalized()
        d = sum(math.sin(f * 3 * n.dot(ax) + p) for f, p, ax in ph) / len(ph)
        v.co = n * radius * (1 + bump * d)
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def vessel_mesh(name, length, y0=-30.0, segs=72, step=1.2):
    """Стінка судини зсередини: труба вздовж +Y з нерівним радіусом."""
    bm = bmesh.new()
    n = int(length / step)
    prev = None
    for i in range(n + 1):
        y = y0 + i * step
        ring = []
        for s in range(segs):
            a = 2 * math.pi * s / segs
            r = R_VESSEL * (1 + 0.035 * math.sin(y * 0.21 + 2.0 * math.sin(a * 2)) + 0.03 * math.sin(a * 3 + y * 0.09)
                            + 0.018 * math.sin(a * 7 - y * 0.5) + 0.012 * math.sin(a * 13 + y * 1.3))
            ring.append(bm.verts.new((r * math.cos(a), y, r * math.sin(a))))
        if prev:
            for s in range(segs):
                s2 = (s + 1) % segs
                bm.faces.new((prev[s], ring[s], ring[s2], prev[s2]))
        prev = ring
    for f in bm.faces:
        f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


# ---------- матеріали ----------
def fogged(nt, bsdf_out, fog_color, fog_strength, k, d0=0.0):
    """Глибина плазми: що далі від камери, то більше поверхня тоне в кольорі тла."""
    N, L = nt.nodes, nt.links
    cam = N.new('ShaderNodeCameraData')
    sub = N.new('ShaderNodeMath'); sub.operation = 'SUBTRACT'; sub.inputs[1].default_value = d0
    mx = N.new('ShaderNodeMath'); mx.operation = 'MAXIMUM'; mx.inputs[1].default_value = 0.0
    mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = -k
    ex = N.new('ShaderNodeMath'); ex.operation = 'EXPONENT'
    inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    L.new(cam.outputs['View Distance'], sub.inputs[0]); L.new(sub.outputs[0], mx.inputs[0])
    L.new(mx.outputs[0], mul.inputs[0]); L.new(mul.outputs[0], ex.inputs[0]); L.new(ex.outputs[0], inv.inputs[1])
    em = N.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*fog_color, 1); em.inputs['Strength'].default_value = fog_strength
    mix = N.new('ShaderNodeMixShader')
    L.new(inv.outputs[0], mix.inputs[0]); L.new(bsdf_out, mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2])
    out = N.new('ShaderNodeOutputMaterial')
    L.new(mix.outputs[0], out.inputs['Surface'])


def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    return m


def mat_cell(fog, sss=1.0):
    """Еритроцит: властивість об'єкта pale (0 — здоровий, 1 — гіпохромний) керує кольором і центральним просвітленням."""
    m = new_mat('Cell'); nt = m.node_tree; N, L = nt.nodes, nt.links
    pale = N.new('ShaderNodeAttribute'); pale.attribute_type = 'OBJECT'; pale.attribute_name = 'pale'
    info = N.new('ShaderNodeObjectInfo')
    tc = N.new('ShaderNodeTexCoord')
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])
    comb = N.new('ShaderNodeCombineXYZ'); L.new(sep.outputs['X'], comb.inputs['X']); L.new(sep.outputs['Y'], comb.inputs['Y'])
    ln = N.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'; L.new(comb.outputs[0], ln.inputs[0])
    # центральне просвітлення: 1 у центрі диска, 0 від ~0.6 радіуса
    ramp = N.new('ShaderNodeMapRange'); ramp.inputs['From Min'].default_value = 0.15; ramp.inputs['From Max'].default_value = 0.62
    ramp.inputs['To Min'].default_value = 1.0; ramp.inputs['To Max'].default_value = 0.0
    L.new(ln.outputs['Value'], ramp.inputs['Value'])
    cen = N.new('ShaderNodeMath'); cen.operation = 'MULTIPLY'
    L.new(ramp.outputs[0], cen.inputs[0]); L.new(pale.outputs['Fac'], cen.inputs[1])
    red = N.new('ShaderNodeMixRGB'); red.blend_type = 'MIX'
    red.inputs['Color1'].default_value = (0.46, 0.012, 0.012, 1); red.inputs['Color2'].default_value = (0.62, 0.03, 0.02, 1)
    L.new(info.outputs['Random'], red.inputs['Fac'])
    c1 = N.new('ShaderNodeMixRGB'); c1.inputs['Color2'].default_value = (0.80, 0.30, 0.26, 1)
    sc = N.new('ShaderNodeMath'); sc.operation = 'MULTIPLY'; sc.inputs[1].default_value = 0.8
    L.new(pale.outputs['Fac'], sc.inputs[0]); L.new(sc.outputs[0], c1.inputs['Fac']); L.new(red.outputs[0], c1.inputs['Color1'])
    c2 = N.new('ShaderNodeMixRGB'); c2.inputs['Color2'].default_value = (0.95, 0.66, 0.60, 1)
    L.new(cen.outputs[0], c2.inputs['Fac']); L.new(c1.outputs[0], c2.inputs['Color1'])
    b = N.new('ShaderNodeBsdfPrincipled')
    L.new(c2.outputs[0], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.34
    b.inputs['Subsurface Weight'].default_value = sss
    b.inputs['Subsurface Radius'].default_value = (1.0, 0.25, 0.12)
    b.inputs['Subsurface Scale'].default_value = 0.22
    b.inputs['Coat Weight'].default_value = 0.35
    b.inputs['Coat Roughness'].default_value = 0.18
    fogged(nt, b.outputs[0], *fog)
    return m


def mat_simple(name, color, fog, rough=0.4, sss=0.0):
    m = new_mat(name); nt = m.node_tree
    b = nt.nodes.new('ShaderNodeBsdfPrincipled')
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    if sss:
        b.inputs['Subsurface Weight'].default_value = sss
        b.inputs['Subsurface Radius'].default_value = (1.0, 0.6, 0.4)
        b.inputs['Subsurface Scale'].default_value = 0.3
    fogged(nt, b.outputs[0], *fog)
    return m


def mat_wall(fog):
    """Стінка судини світиться сама (без відбиттів світла) — інакше промені блукають у замкненій трубі й рендер стає в рази довшим.
    Об'єм дає псевдоосвітлення: що крутіше поверхня до погляду, то світліша (волога плівка)."""
    m = new_mat('Wall'); nt = m.node_tree; N, L = nt.nodes, nt.links
    tc = N.new('ShaderNodeTexCoord')
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.0, 0.22, 1.0)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    n1 = N.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = 0.55; n1.inputs['Detail'].default_value = 3
    L.new(mp.outputs[0], n1.inputs['Vector'])
    n2 = N.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 2.2; n2.inputs['Detail'].default_value = 2
    L.new(mp.outputs[0], n2.inputs['Vector'])
    h = N.new('ShaderNodeMath'); h.operation = 'MULTIPLY_ADD'; h.inputs[1].default_value = 0.35
    L.new(n2.outputs['Fac'], h.inputs[0]); L.new(n1.outputs['Fac'], h.inputs[2])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 1.0; bump.inputs['Distance'].default_value = 0.9
    L.new(h.outputs[0], bump.inputs['Height'])
    lw = N.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.42
    L.new(bump.outputs[0], lw.inputs['Normal'])
    col = N.new('ShaderNodeMixRGB')
    col.inputs['Color1'].default_value = (0.07, 0.002, 0.003, 1); col.inputs['Color2'].default_value = (0.30, 0.016, 0.012, 1)
    L.new(n1.outputs['Fac'], col.inputs['Fac'])
    sheen = N.new('ShaderNodeMixRGB'); sheen.blend_type = 'ADD'
    sheen.inputs['Color2'].default_value = (0.75, 0.10, 0.06, 1)
    pw = N.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 2.2
    L.new(lw.outputs['Facing'], pw.inputs[0]); L.new(pw.outputs[0], sheen.inputs['Fac']); L.new(col.outputs[0], sheen.inputs['Color1'])
    em = N.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = WALL_GLOW
    L.new(sheen.outputs[0], em.inputs['Color'])
    fogged(nt, em.outputs[0], *fog)
    return m


# ---------- світло й камера ----------
def area(name, loc, target, size, power, color=(1, 1, 1)):
    d = bpy.data.lights.new(name, 'AREA'); d.size = size; d.energy = power; d.color = color
    o = link(bpy.data.objects.new(name, d)); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o


def point(name, loc, power, color=(1, 1, 1), radius=1.0):
    d = bpy.data.lights.new(name, 'POINT'); d.energy = power; d.color = color; d.shadow_soft_size = radius
    o = link(bpy.data.objects.new(name, d)); o.location = loc
    return o


def camera(lens, loc, rot, focus, fstop):
    d = bpy.data.cameras.new('Cam'); d.lens = lens; d.sensor_width = 36
    d.dof.use_dof = True; d.dof.focus_distance = focus; d.dof.aperture_fstop = fstop; d.dof.aperture_blades = 7
    d.clip_start = 0.05; d.clip_end = 600
    o = link(bpy.data.objects.new('Cam', d)); o.location = loc; o.rotation_euler = rot
    bpy.context.scene.camera = o
    return o


def handheld(cam, nframes, amp_loc=0.05, amp_rot=0.004, seed=1, drift=None):
    """Жива камера: сума повільних синусоїд (а не шум по кадрах), плюс рівномірний рух drift за весь план."""
    rnd = random.Random(seed)
    ph = [[(rnd.uniform(0.15, 0.7), rnd.uniform(0, 6.28)) for _ in range(3)] for _ in range(6)]
    base_l, base_r = cam.location.copy(), cam.rotation_euler.copy()
    linear_keys(False)
    for f in range(0, nframes + 4, 4):
        t = f / FPS
        w = [sum(math.sin(2 * math.pi * fr * t + p) for fr, p in ch) / 3 for ch in ph]
        u = f / max(1, nframes - 1)
        dr = Vector(drift) * u if drift else Vector((0, 0, 0))
        cam.location = base_l + Vector((w[0], w[1] * 0.4, w[2])) * amp_loc + dr
        cam.rotation_euler = (base_r.x + w[3] * amp_rot, base_r.y + w[4] * amp_rot * 0.6, base_r.z + w[5] * amp_rot)
        cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f)


# ---------- плани ----------
def stream(nframes, vmax, t_anemia, dens, seed, r_min=1.7, depth=95.0, anemic_keep=0.4, with_white=True, fog=None, sss=0.0):
    """Потік у судині. Профіль швидкості параболічний (Пуазейль): у центрі швидше, біля стінки повільніше.
    Клітини, що дійдуть до камери після t_anemia, — рідші, дрібніші й блідіші."""
    rnd = random.Random(seed)
    T = nframes / FPS
    me = rbc_mesh('RBC')
    mcell = mat_cell(fog, sss); me.materials.append(mcell)
    plt = blob_mesh('Platelet', 0.22, 2, 0.25, 3)
    plt.materials.append(mat_simple('Platelet', (0.62, 0.34, 0.2), fog, 0.5, 0.0))
    wbc = blob_mesh('WBC', 1.55, 4, 0.045, 5)
    wbc.materials.append(mat_simple('WBC', (0.82, 0.72, 0.68), fog, 0.55, 0.8))
    wall = link(bpy.data.objects.new('Wall', vessel_mesh('Wall', depth + vmax * T + 80)))
    wall.data.materials.append(mat_wall(fog))
    y_max = depth + vmax * T
    bm = bmesh.new(); bmesh.ops.create_circle(bm, cap_ends=True, radius=R_VESSEL * 1.3, segments=32)
    capm = bpy.data.meshes.new('Cap'); bm.to_mesh(capm); bm.free()
    cap = link(bpy.data.objects.new('Cap', capm)); cap.location = (0, y_max + 70, 0); cap.rotation_euler = (math.radians(90), 0, 0)
    capm.materials.append(mat_simple('CapM', (0.3, 0.02, 0.02), fog))
    linear_keys(True)
    count = 0

    def spawn(mesh, kind):
        nonlocal count
        r = math.sqrt(rnd.uniform((r_min / (R_VESSEL - 1.4)) ** 2, 1)) * (R_VESSEL - 1.4)
        a = rnd.uniform(0, 2 * math.pi)
        y0 = rnd.uniform(-6, y_max)
        v = vmax * (1 - 0.62 * (r / R_VESSEL) ** 2) * rnd.uniform(0.92, 1.08)
        anemic = t_anemia is not None and (y0 / v) > t_anemia
        if kind == 'rbc' and anemic and rnd.random() > anemic_keep:
            return
        o = bpy.data.objects.new(kind, mesh)
        if kind == 'rbc':
            o['pale'] = rnd.uniform(0.55, 1.0) if anemic else rnd.uniform(0.0, 0.08)
            s = rnd.uniform(0.76, 0.9) if anemic else rnd.uniform(0.95, 1.05)
            o.scale = (s, s, s)
        link(o)
        rot = Vector((rnd.uniform(0, 6.28), rnd.uniform(0, 6.28), rnd.uniform(0, 6.28)))
        spin = Vector((rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5))) * (0.5 + v / vmax)
        dx, dz = rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4)
        for f, t in ((0, 0.0), (nframes, T)):
            o.location = (r * math.cos(a) + dx * t / T, y0 - v * t, r * math.sin(a) + dz * t / T)
            o.rotation_euler = rot + spin * t
            o.keyframe_insert('location', frame=f); o.keyframe_insert('rotation_euler', frame=f)
        count += 1

    n = int(dens * (y_max + 6))
    for _ in range(n):
        spawn(me, 'rbc')
    for _ in range(int(n * 0.10)):
        spawn(plt, 'plt')
    if with_white:
        for _ in range(max(2, int(n * 0.004))):
            spawn(wbc, 'wbc')
    return count


def build_flow(nframes):
    sc = reset(nframes)
    fog = ((1.0, 0.085, 0.02), 1.7, 0.021, 8.0)
    set_world((0.03, 0.002, 0.002))
    n = stream(nframes, vmax=6.0, t_anemia=10.5, dens=4.6, seed=7, fog=fog)
    cam = camera(21, (0.3, 0, -0.4), (math.radians(90), 0, 0), 9.0, 0.045)
    handheld(cam, nframes, 0.10, 0.006, seed=2)
    area('Key', (3.5, -3, 5), (0, 30, 0), 5, 7000, (1.0, 0.92, 0.86))
    point('Rim1', (7, 14, 6), 2500, (1.0, 0.55, 0.4), 2)
    point('Rim2', (-8, 30, -5), 4000, (1.0, 0.45, 0.3), 2)
    point('Rim3', (5, 52, -7), 6000, (1.0, 0.5, 0.3), 3)
    print('flow objects', n)
    return sc


def build_outro(nframes):
    sc = reset(nframes)
    fog = ((0.42, 0.035, 0.02), 1.0, 0.024, 6.0)
    set_world((0.03, 0.003, 0.003))
    n = stream(nframes, vmax=2.2, t_anemia=-1.0, dens=4.2, seed=21, r_min=4.6, anemic_keep=0.34, with_white=False, fog=fog)
    cam = camera(24, (0, 0, 0), (math.radians(90), 0, 0), 12.0, 0.05)
    handheld(cam, nframes, 0.08, 0.004, seed=5, drift=(0, 5.0, 0))
    area('Key', (0, -3, 3), (0, 30, 0), 6, 5000, (1.0, 0.9, 0.85))
    point('Rim1', (7, 16, 6), 2000, (1.0, 0.6, 0.5), 2)
    point('Rim2', (-8, 34, -5), 3500, (1.0, 0.5, 0.4), 2)
    print('outro objects', n)
    return sc


def float_anim(o, nframes, rnd, amp=0.12, spin=0.25, rock=0.16):
    """Клітина зависла в плазмі: повільно погойдується й обертається."""
    linear_keys(False)
    base_l, base_r = o.location.copy(), o.rotation_euler.copy()
    p = [rnd.uniform(0, 6.28) for _ in range(6)]
    fr = [rnd.uniform(0.08, 0.2) for _ in range(6)]
    for f in range(0, nframes + 8, 8):
        t = f / FPS
        o.location = base_l + Vector((math.sin(2 * math.pi * fr[0] * t + p[0]), math.sin(2 * math.pi * fr[1] * t + p[1]),
                                      math.sin(2 * math.pi * fr[2] * t + p[2]))) * amp
        o.rotation_euler = (base_r.x + rock * math.sin(2 * math.pi * fr[3] * t + p[3]),
                            base_r.y + rock * math.sin(2 * math.pi * fr[4] * t + p[4]), base_r.z + spin * t)
        o.keyframe_insert('location', frame=f); o.keyframe_insert('rotation_euler', frame=f)


def build_third(nframes):
    """Три колони клітин ідуть у глибину; права колона блідне хвилею від камери: «кожна третя»."""
    sc = reset(nframes)
    fog = ((0.05, 0.004, 0.004), 1.0, 0.055, 6.0)
    set_world((0.012, 0.001, 0.001))
    rnd = random.Random(11)
    me = rbc_mesh('RBC', 72, 18); me.materials.append(mat_cell(fog))
    rows = 14
    for row in range(rows):
        for col in range(3):
            o = link(bpy.data.objects.new(f'c{row}_{col}', me))
            o.location = ((col - 1) * 2.75, row * 3.3, 0)
            o.rotation_euler = (math.radians(rnd.uniform(22, 34)), rnd.uniform(-0.12, 0.12), 0)
            float_anim(o, nframes, rnd, 0.10, 0.0, 0.12)
            o['pale'] = 0.0
            if col == 2:
                linear_keys(False)
                f0 = int((1.9 + row * 0.13) * FPS)
                o.keyframe_insert('["pale"]', frame=f0)
                o['pale'] = 0.95
                o.keyframe_insert('["pale"]', frame=f0 + 16)
    cam = camera(32, (0.0, -9.5, 8.2), (0, 0, 0), 14.5, 0.3)
    cam.rotation_euler = (Vector((0.0, 4.3, 0.0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.shift_x = -0.15
    handheld(cam, nframes, 0.03, 0.002, seed=9, drift=(0.0, 2.4, -0.5))
    area('Top', (0, 14, 12), (0, 12, 0), 26, 9000, (1.0, 0.93, 0.9))
    area('Rim', (9, 30, 3), (0, 8, 0), 10, 16000, (1.0, 0.5, 0.4))
    area('Fill', (-8, -8, 2), (0, 4, 0), 6, 900, (0.8, 0.85, 1.0))
    return sc


SIZES = [(-3.15, 0.78, 0.95, 1.0), (0.05, 1.0, 0.0, 1.0), (3.2, 1.27, 0.0, 1.12)]   # x, масштаб, блідість, овальність


def build_sizes(nframes):
    """Три клітини поруч: мікроцит (дрібний, блідий), нормоцит, макроцит (великий, овальний)."""
    sc = reset(nframes)
    fog = ((0.04, 0.003, 0.003), 1.0, 0.05, 8.0)
    set_world((0.010, 0.001, 0.001))
    rnd = random.Random(4)
    me = rbc_mesh('RBC', 128, 28); me.materials.append(mat_cell(fog))
    for i, (x, s, pale, oval) in enumerate(SIZES):
        o = link(bpy.data.objects.new(f'size{i}', me))
        o.location = (x, 0, 0.55)
        o.scale = (s * oval, s, s)
        o.rotation_euler = (math.radians(66), (i - 1) * 0.16, 0)
        o['pale'] = pale
        float_anim(o, nframes, rnd, 0.05, 0.0, 0.3)
    # розмите тло з далеких клітин
    me2 = rbc_mesh('RBCfar', 32, 10); me2.materials.append(me.materials[0])
    for _ in range(46):
        o = link(bpy.data.objects.new('far', me2))
        o.location = (rnd.uniform(-22, 22), rnd.uniform(14, 44), rnd.uniform(-9, 11))
        o.rotation_euler = (rnd.uniform(0, 6.28), rnd.uniform(0, 6.28), rnd.uniform(0, 6.28))
        o['pale'] = rnd.choice([0.0, 0.0, 0.8])
        float_anim(o, nframes, rnd, 0.3, rnd.uniform(-0.2, 0.2))
    cam = camera(50, (0.15, -13.6, 0.55), (math.radians(90), 0, 0), 13.6, 0.5)
    handheld(cam, nframes, 0.02, 0.0012, seed=3, drift=(0, 0.6, 0))
    area('Key', (-6, -7, 9), (0, 0, 0), 9, 5200, (1.0, 0.95, 0.92))
    area('Rim', (7, 9, 5), (0, 0, 0.3), 7, 9000, (1.0, 0.55, 0.42))
    area('Fill', (6, -9, -3), (0, 0, 0), 8, 700, (0.75, 0.82, 1.0))
    point('Back', (0, 30, 2), 30000, (1.0, 0.35, 0.25), 6)
    return sc


BUILD = {'flow': build_flow, 'third': build_third, 'sizes': build_sizes, 'outro': build_outro}


def build(shot, nframes):
    return BUILD[shot](nframes)
