# Спільні інструменти кадрів «Тіло людини»: матеріали, світло, трубки, метакулі. Сцени лежать у scenes/<назва>.py.
import bpy, bmesh, math, random, os, sys
from mathutils import Vector, Matrix, Euler
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'anemia', 'blender'))
from build import reset, set_world, link, new_mat, fogged, area, point, camera, rbc_mesh, blob_mesh, mat_simple, mat_cell  # noqa


def scene():
    """Порожня сцена Cycles для одного кадру."""
    sc = reset(1)
    sc.render.use_motion_blur = False
    sc.cycles.adaptive_threshold = 0.03
    sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 3; sc.cycles.glossy_bounces = 3
    sc.cycles.transmission_bounces = 6; sc.cycles.transparent_max_bounces = 12
    return sc


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def cam(lens, loc, target, fstop=None, focus=None):
    """Камера, що дивиться на target; різкість — на target або на відстані focus."""
    loc, target = Vector(loc), Vector(target)
    c = camera(lens, loc, (0, 0, 0), focus or (target - loc).length, fstop or 64)
    look_at(c, target)
    if fstop is None:
        c.data.dof.use_dof = False
    return c


def mat(name, color, rough=0.4, sss=0.0, sss_radius=(1.0, 0.3, 0.15), sss_scale=0.1, coat=0.0, metallic=0.0,
        emission=None, emission_strength=1.0, transmission=0.0, alpha=1.0, ior=1.45):
    """Звичайний Principled. Повертає матеріал; вузол — m.node_tree.nodes['P']."""
    m = new_mat(name); nt = m.node_tree
    b = nt.nodes.new('ShaderNodeBsdfPrincipled'); b.name = 'P'
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metallic; b.inputs['IOR'].default_value = ior
    b.inputs['Subsurface Weight'].default_value = sss; b.inputs['Subsurface Radius'].default_value = sss_radius
    b.inputs['Subsurface Scale'].default_value = sss_scale
    b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = 0.15
    b.inputs['Transmission Weight'].default_value = transmission; b.inputs['Alpha'].default_value = alpha
    if emission:
        b.inputs['Emission Color'].default_value = (*emission, 1); b.inputs['Emission Strength'].default_value = emission_strength
    out = nt.nodes.new('ShaderNodeOutputMaterial'); out.name = 'Out'
    nt.links.new(b.outputs[0], out.inputs['Surface'])
    return m


def mat_emit(name, color, strength=5.0):
    m = new_mat(name); nt = m.node_tree
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs['Color'].default_value = (*color, 1); e.inputs['Strength'].default_value = strength
    out = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(e.outputs[0], out.inputs['Surface'])
    return m


def mat_xray(name, color, strength=2.0, power=2.0, base=0.02):
    """«Рентген»: прозора оболонка, що світиться на краях силуету. Не кидає тіней на вміст."""
    m = new_mat(name); nt = m.node_tree; N, L = nt.nodes, nt.links
    lw = N.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.5
    pw = N.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = power
    ad = N.new('ShaderNodeMath'); ad.operation = 'ADD'; ad.inputs[1].default_value = base; ad.use_clamp = True
    L.new(lw.outputs['Facing'], pw.inputs[0]); L.new(pw.outputs[0], ad.inputs[0])
    tr = N.new('ShaderNodeBsdfTransparent')
    em = N.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*color, 1); em.inputs['Strength'].default_value = strength
    mix = N.new('ShaderNodeMixShader'); L.new(ad.outputs[0], mix.inputs[0]); L.new(tr.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2])
    out = N.new('ShaderNodeOutputMaterial'); L.new(mix.outputs[0], out.inputs['Surface'])
    return m


def tube(name, pts, radius=0.1, material=None, radii=None, res=8, smooth=True, cyclic=False, caps=True):
    """Трубка крізь точки (судина, бронх, нерв, волокно). radii — множник радіуса на кожну точку."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('NURBS' if smooth and len(pts) > 2 else 'POLY')
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (*p, 1); sp.points[i].radius = radii[i] if radii else 1.0
    if sp.type == 'NURBS':
        sp.use_endpoint_u = True; sp.order_u = min(4, len(pts)); sp.resolution_u = 6
    sp.use_cyclic_u = cyclic
    cu.bevel_depth = radius; cu.bevel_resolution = res; cu.use_fill_caps = caps
    o = link(bpy.data.objects.new(name, cu))
    if material: cu.materials.append(material)
    return o


def to_mesh(obj):
    """Перетворює криву чи метакулі на звичайну сітку (щоб застосовувати модифікатори, різати тощо)."""
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    o = link(bpy.data.objects.new(obj.name + '_m', me)); o.matrix_world = obj.matrix_world
    for m in obj.data.materials:
        if m and m.name not in [x.name for x in me.materials if x]: me.materials.append(m)
    bpy.data.objects.remove(obj)
    for p in me.polygons: p.use_smooth = True
    return o


def metaballs(name, balls, material=None, resolution=0.12, threshold=0.6):
    """Органічна форма зі злитих куль. balls: (x, y, z, r) або (x, y, z, r, (sx, sy, sz)) для еліпсоїда. Повертає сітку."""
    mb = bpy.data.metaballs.new(name); mb.resolution = resolution; mb.render_resolution = resolution; mb.threshold = threshold
    for b in balls:
        e = mb.elements.new(); e.co = b[:3]; e.radius = b[3]
        if len(b) > 4:
            e.type = 'ELLIPSOID'; e.size_x, e.size_y, e.size_z = b[4]
    o = link(bpy.data.objects.new(name, mb))
    o = to_mesh(o)
    if material: o.data.materials.append(material)
    return o


def prim(kind, name, material=None, loc=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0), **kw):
    """Примітив через bmesh: 'sphere' (u, v), 'ico' (subdiv), 'cyl' (segs, r1, r2, depth), 'cube', 'torus' недоступний — робіть tube(cyclic=True)."""
    bm = bmesh.new()
    if kind == 'sphere': bmesh.ops.create_uvsphere(bm, u_segments=kw.get('u', 48), v_segments=kw.get('v', 24), radius=1)
    elif kind == 'ico': bmesh.ops.create_icosphere(bm, subdivisions=kw.get('subdiv', 4), radius=1)
    elif kind == 'cyl': bmesh.ops.create_cone(bm, cap_ends=True, segments=kw.get('segs', 48), radius1=kw.get('r1', 1), radius2=kw.get('r2', 1), depth=kw.get('depth', 2))
    elif kind == 'cube': bmesh.ops.create_cube(bm, size=2)
    for f in bm.faces: f.smooth = kind != 'cube'
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); o.location = loc; o.scale = scale; o.rotation_euler = rot
    if material: me.materials.append(material)
    return o


def displace(obj, strength=0.1, size=0.5, kind='CLOUDS', subsurf=0, mid=0.5):
    """Нерівності поверхні: текстурне зміщення (CLOUDS, VORONOI, MUSGRAVE немає у 5.x — беріть CLOUDS/VORONOI/MARBLE/WOOD)."""
    if subsurf:
        s = obj.modifiers.new('sub', 'SUBSURF'); s.levels = subsurf; s.render_levels = subsurf
    t = bpy.data.textures.new(obj.name + '_t', kind)
    if hasattr(t, 'noise_scale'): t.noise_scale = size
    m = obj.modifiers.new('disp', 'DISPLACE'); m.texture = t; m.strength = strength; m.mid_level = mid; m.texture_coords = 'OBJECT'
    return m


def instance(src, name, loc, rot=(0, 0, 0), scale=1.0):
    o = link(bpy.data.objects.new(name, src.data)); o.location = loc; o.rotation_euler = rot
    o.scale = (scale,) * 3 if isinstance(scale, (int, float)) else scale
    return o
