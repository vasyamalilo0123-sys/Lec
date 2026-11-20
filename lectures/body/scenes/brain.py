# Головний мозок: дві півкулі зі звивинами й борознами, мозочок із листками, стовбур. Вид збоку-згори (лобова частка праворуч).
# Осі: x — ліво/право, y — перед (−) / зад (+), z — вгору.
import bpy, bmesh, math
from mathutils import Vector


def win(t):
    """Плавне вікно: 1 у центрі, 0 за межами |t| ≥ 1."""
    return math.cos(t * math.pi / 2) ** 2 if abs(t) < 1 else 0.0


def hemisphere(C, side, material, subdiv=7):
    """Півкуля з кулі: плоский медіальний бік, скронева частка, бічна (Сильвієва) й центральна борозни."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1)
    for v in bm.verts:
        x, y, z = v.co
        lat = x                                  # x > 0 — латеральний бік (до дзеркалення)
        X, Y, Z = x * 1.6, y * 2.35, z * 1.5
        if lat < 0:
            X *= 0.22                            # медіальна поверхня майже пласка
        k = 1 - (0.30 if y > 0 else 0.20) * y * y    # потиличний полюс вужчий за лобовий
        X *= k; Z *= k
        if z < 0:
            Z *= 0.72
            lw = max(0.0, lat) ** 0.6
            Z -= 0.62 * win((Y + 0.15) / 1.55) * lw * min(1.0, -z * 2.2)     # скронева частка
            X += 0.10 * win((Y + 0.15) / 1.55) * lw
        Z += 0.12 * win((Y + 0.2) / 2.2)         # тім'я трохи вище
        p = Vector((X, Y, Z))
        n = Vector((x, y / 2.35, z / 1.5)).normalized()
        if lat > 0.15:
            # бічна борозна: від переду навскіс назад-угору, відділяє скроневу частку
            if -1.5 < Y < 0.95:
                zl = -0.42 + 0.20 * (Y + 0.3)
                p -= n * 0.24 * math.exp(-((Z - zl) / 0.085) ** 2) * win((Y + 0.275) / 1.3) ** 0.5
            # центральна борозна: від тім'я донизу-вперед до бічної
            if Z > -0.2:
                yc = 0.30 - 0.36 * (1.55 - Z) / 1.55
                p -= n * 0.13 * math.exp(-((Y - yc) / 0.06) ** 2) * min(1.0, (Z + 0.2) / 0.3)
        v.co = Vector((side * (p.x + 0.39), p.y, p.z))
    if side < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(f'hemi{side}'); bm.to_mesh(me); bm.free()
    o = C.link(bpy.data.objects.new(me.name, me)); me.materials.append(material)
    for i, (scale, strength, lo, hi) in enumerate(((0.36, 0.115, 0.43, 0.57), (0.17, 0.035, 0.45, 0.55))):
        t = bpy.data.textures.new(f'gyri{side}{i}', 'CLOUDS'); t.noise_scale = scale; t.noise_depth = 1; t.noise_basis = 'ORIGINAL_PERLIN'
        t.use_color_ramp = True
        r = t.color_ramp; r.interpolation = 'EASE'
        r.elements[0].position = 0.0; r.elements[0].color = (1, 1, 1, 1)
        r.elements[1].position = 1.0; r.elements[1].color = (1, 1, 1, 1)
        for pos, c in ((lo, 1), (0.5, 0), (hi, 1)):
            e = r.elements.new(pos); e.color = (c, c, c, 1)
        m = o.modifiers.new(f'gyri{i}', 'DISPLACE'); m.texture = t; m.strength = strength; m.mid_level = 1.0; m.texture_coords = 'GLOBAL'
    sm = o.modifiers.new('smooth', 'SMOOTH'); sm.factor = 0.5; sm.iterations = 2
    return o


def cortex(C, name, gyrus, sulcus, lo=0.44, hi=0.52):
    """Волога кора: у борознах темніше (за кривиною поверхні), SSS, блиск."""
    m = C.new_mat(name); nt = m.node_tree; N, L = nt.nodes, nt.links
    geo = N.new('ShaderNodeNewGeometry')
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = lo; mr.inputs['From Max'].default_value = hi
    L.new(geo.outputs['Pointiness'], mr.inputs['Value'])
    tc = N.new('ShaderNodeTexCoord')
    ns = N.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = 14.0; ns.inputs['Detail'].default_value = 5
    L.new(tc.outputs['Object'], ns.inputs['Vector'])
    col = N.new('ShaderNodeMixRGB'); col.inputs['Color1'].default_value = (*sulcus, 1); col.inputs['Color2'].default_value = (*gyrus, 1)
    L.new(mr.outputs[0], col.inputs['Fac'])
    var = N.new('ShaderNodeMixRGB'); var.blend_type = 'MULTIPLY'; var.inputs['Fac'].default_value = 0.35
    cr = N.new('ShaderNodeMapRange'); cr.inputs['To Min'].default_value = 0.55; cr.inputs['To Max'].default_value = 1.25
    L.new(ns.outputs['Fac'], cr.inputs['Value']); L.new(col.outputs[0], var.inputs['Color1']); L.new(cr.outputs[0], var.inputs['Color2'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.12; bump.inputs['Distance'].default_value = 0.03
    L.new(ns.outputs['Fac'], bump.inputs['Height'])
    b = N.new('ShaderNodeBsdfPrincipled')
    L.new(var.outputs[0], b.inputs['Base Color']); L.new(bump.outputs[0], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.33
    b.inputs['Subsurface Weight'].default_value = 0.85; b.inputs['Subsurface Radius'].default_value = (1.0, 0.35, 0.22)
    b.inputs['Subsurface Scale'].default_value = 0.07
    b.inputs['Coat Weight'].default_value = 0.75; b.inputs['Coat Roughness'].default_value = 0.1
    out = N.new('ShaderNodeOutputMaterial'); L.new(b.outputs[0], out.inputs['Surface'])
    return m


def cerebellum(C, material):
    """Мозочок: дві півкулі й черв'як, поверхня — тонкі поперечні листки."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=220, v_segments=320, radius=1)
    for v in bm.verts:
        x, y, z = v.co
        X, Y, Z = x * 1.62, y * 0.98, z * 0.80
        Z -= 0.10 * (1 - abs(x)) ** 2 * (1 if z < 0 else 0.3)       # заглибина по середній лінії
        Y -= 0.18 * math.exp(-(x / 0.22) ** 2) * (1 if y > 0 else 0)  # задня вирізка
        n = Vector((x / 1.62, y / 0.98, z / 0.80)).normalized()
        phi = math.atan2(z, -y)                                     # листки — дуги зліва направо
        fol = math.sin(phi * 46 + 1.5 * math.sin(x * 3.0)) * 0.5 + 0.5
        p = Vector((X, Y, Z)) - n * 0.035 * (1 - fol ** 0.35)
        v.co = p
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new('cerebellum'); bm.to_mesh(me); bm.free()
    o = C.link(bpy.data.objects.new('cerebellum', me)); me.materials.append(material)
    o.location = (0, 1.52, -1.18); o.rotation_euler = (math.radians(-14), 0, 0)
    return o


def build(C):
    C.set_world((0.004, 0.004, 0.006))
    m_cortex = cortex(C, 'cortex', (0.86, 0.60, 0.55), (0.36, 0.10, 0.10))
    m_cbl = cortex(C, 'cbl', (0.80, 0.50, 0.46), (0.33, 0.09, 0.09), 0.46, 0.52)
    m_stem = C.mat('stem', (0.88, 0.72, 0.64), rough=0.35, sss=0.8, sss_radius=(1.0, 0.45, 0.3), sss_scale=0.08, coat=0.6)
    hemisphere(C, -1, m_cortex)
    hemisphere(C, 1, m_cortex)
    cerebellum(C, m_cbl)
    C.tube('stem', [(0, 0.45, -0.55), (0, 0.62, -1.0), (0, 0.72, -1.45), (0, 0.9, -2.0), (0, 1.12, -2.75), (0, 1.3, -3.6)], 0.34, m_stem,
           radii=[1.1, 1.15, 1.55, 1.05, 0.8, 0.7], res=12)
    C.prim('sphere', 'pons', m_stem, loc=(0, 0.60, -1.42), scale=(0.62, 0.50, 0.46), u=48, v=24)

    C.cam(50, (-11.2, -3.6, 4.6), (-0.2, -0.55, -0.55))
    C.area('key', (-8, -7, 9), (-1, 0, 0), 7, 5200, (1.0, 0.94, 0.88))
    C.area('rim', (5, 8, 5), (0, 0.5, 0), 7, 9000, (0.5, 0.68, 1.0))
    C.area('kick', (3, -9, -1), (0, -1, 0), 5, 2600, (1.0, 0.55, 0.42))
    C.area('fill', (-9, 5, -5), (0, 1, -1), 8, 500, (0.6, 0.7, 1.0))
    L = -1.95
    return {
        'kicker': 'Нервова система', 'title': 'Головний мозок', 'sub': 'Звивини й борозни —\nспосіб умістити більше кори',
        'scrim': 'none', 'title_at': [96, 96], 'title_size': 92,
        'labels': [
            {'text': 'лобова частка', 'p': [L + 0.15, -1.45, 0.75], 'at': [1560, 170], 'align': 'left'},
            {'text': 'тім\'яна частка', 'p': [L + 0.25, 0.95, 1.0], 'at': [900, 120], 'align': 'left'},
            {'text': 'потилична частка', 'p': [L + 0.5, 2.0, 0.15], 'at': [470, 520], 'align': 'right'},
            {'text': 'скронева частка', 'p': [L - 0.02, -0.3, -0.95], 'at': [1500, 900], 'align': 'left'},
            {'text': 'мозочок', 'p': [-1.0, 1.75, -1.3], 'at': [470, 800], 'align': 'right'},
            {'text': 'стовбур мозку', 'p': [-0.3, 1.0, -2.3], 'at': [1100, 960], 'align': 'left'},
        ],
    }
