import bpy, glob, os, sys, math
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = args[0] if args else 'heart_cycles.png'
SAMPLES = int(args[1]) if len(args) > 1 else 96
HERE = os.path.dirname(os.path.abspath(__file__))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.resolution_percentage = int(args[2]) if len(args) > 2 else 100
sc.render.film_transparent = False
sc.view_settings.view_transform = 'AgX'
try:
    sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception as e:
    print('look', e)
world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (0, 0, 0, 1)


def tissue(name, base, base2, sss=0.10, rough=0.36, coat=0.45, bump=0.6, scale=220, fat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord')
    # large mottling
    n1 = N.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = 28; n1.inputs['Detail'].default_value = 6
    L.new(tc.outputs['Object'], n1.inputs['Vector'])
    ramp = N.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[0].color = (*base, 1)
    ramp.color_ramp.elements[1].position = 0.7; ramp.color_ramp.elements[1].color = (*base2, 1)
    L.new(n1.outputs['Fac'], ramp.inputs['Fac'])
    col = ramp.outputs['Color']
    if fat > 0:
        n3 = N.new('ShaderNodeTexNoise'); n3.inputs['Scale'].default_value = 22; n3.inputs['Detail'].default_value = 8
        n3.inputs['Roughness'].default_value = 0.65
        L.new(tc.outputs['Object'], n3.inputs['Vector'])
        fr = N.new('ShaderNodeValToRGB')
        fr.color_ramp.elements[0].position = 0.66 - fat * 0.2; fr.color_ramp.elements[0].color = (0, 0, 0, 1)
        fr.color_ramp.elements[1].position = 0.80 - fat * 0.2; fr.color_ramp.elements[1].color = (1, 1, 1, 1)
        L.new(n3.outputs['Fac'], fr.inputs['Fac'])
        mix = N.new('ShaderNodeMixRGB'); mix.inputs['Color2'].default_value = (0.62, 0.40, 0.14, 1)
        L.new(fr.outputs['Color'], mix.inputs['Fac']); L.new(col, mix.inputs['Color1'])
        col = mix.outputs['Color']
    L.new(col, b.inputs['Base Color'])
    b.inputs['Subsurface Weight'].default_value = sss
    b.inputs['Subsurface Radius'].default_value = (1.0, 0.25, 0.12)
    b.inputs['Subsurface Scale'].default_value = 0.003
    b.inputs['Roughness'].default_value = rough
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Coat Roughness'].default_value = 0.12
    b.inputs['Specular IOR Level'].default_value = 0.6
    # fine fibrous relief
    n2 = N.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = scale; n2.inputs['Detail'].default_value = 10
    n2.inputs['Roughness'].default_value = 0.7
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1, 0.25, 1)
    L.new(tc.outputs['Object'], mp.inputs['Vector']); L.new(mp.outputs['Vector'], n2.inputs['Vector'])
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump; bp.inputs['Distance'].default_value = 0.002
    L.new(n2.outputs['Fac'], bp.inputs['Height']); L.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


MAT = {
    'myo': tissue('myo', (0.20, 0.018, 0.016), (0.33, 0.04, 0.03), fat=0.35),
    'atr': tissue('atr', (0.22, 0.03, 0.028), (0.34, 0.06, 0.05), fat=0.2, scale=160),
    'art': tissue('art', (0.38, 0.012, 0.01), (0.48, 0.025, 0.02), sss=0.1, rough=0.3, bump=0.08, scale=400),
    'aorta': tissue('aorta', (0.42, 0.07, 0.05), (0.55, 0.13, 0.10), sss=0.15, rough=0.32, bump=0.12, scale=120),
    'vein': tissue('vein', (0.04, 0.05, 0.16), (0.08, 0.09, 0.24), sss=0.1, rough=0.33, bump=0.08, scale=300),
    'pa': tissue('pa', (0.09, 0.10, 0.27), (0.15, 0.16, 0.36), sss=0.15, rough=0.34, bump=0.12, scale=120),
    'pv': tissue('pv', (0.38, 0.05, 0.04), (0.48, 0.09, 0.07), sss=0.15, rough=0.34, bump=0.1, scale=140),
}
KIND = {1629: 'art', 1630: 'art', 1631: None, 1632: 'art', 1633: 'art', 1634: 'art', 1635: 'atr', 1636: 'myo', 1638: 'atr', 1639: 'myo',
        1652: 'pa', 1663: 'pa', 1664: 'pa', 1665: 'pa', 1717: 'aorta', 1752: 'aorta', 2073: 'vein', 2075: 'vein', 2076: 'vein',
        2077: 'vein', 2078: 'vein', 2079: 'pv', 2083: 'pv', 2089: 'pv', 2093: 'pv', 2176: 'vein', 2282: 'vein'}

core = []
for f in sorted(glob.glob(os.path.join(HERE, 'obj', '*.obj'))):
    gid = int(os.path.basename(f).split('_')[0])
    kind = KIND.get(gid)
    if not kind:
        continue
    bpy.ops.wm.obj_import(filepath=f)
    o = bpy.context.selected_objects[0]
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.00005); bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.shade_smooth()
    sub = o.modifiers.new('sub', 'SUBSURF'); sub.levels = 2; sub.render_levels = 2
    o.data.materials.clear(); o.data.materials.append(MAT[kind])
    if gid in (1635, 1636, 1638, 1639):
        core.append(o)

bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in core for c in o.bound_box]
c = sum(pts, Vector()) / len(pts)
c.z += 0.02

tgt = bpy.data.objects.new('tgt', None); tgt.location = c; sc.collection.objects.link(tgt)
cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
cd.lens = 90; cd.dof.use_dof = True; cd.dof.focus_object = tgt; cd.dof.aperture_fstop = 11
cam.location = c + Vector((0.11, -0.80, 0.05))
tr = cam.constraints.new('TRACK_TO'); tr.target = tgt; tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'


def area(name, loc, size, power, color):
    d = bpy.data.lights.new(name, 'AREA'); d.size = size; d.energy = power; d.color = color
    o = bpy.data.objects.new(name, d); o.location = c + Vector(loc); sc.collection.objects.link(o)
    t = o.constraints.new('TRACK_TO'); t.target = tgt; t.track_axis = 'TRACK_NEGATIVE_Z'; t.up_axis = 'UP_Y'


area('key', (-0.35, -0.45, 0.40), 0.5, 14, (1.0, 0.95, 0.9))
area('rim', (0.40, 0.35, 0.25), 0.3, 22, (0.75, 0.85, 1.0))
area('fill', (0.45, -0.35, -0.15), 0.6, 2, (1.0, 0.85, 0.8))

sc.render.filepath = os.path.abspath(OUT)
sc.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(write_still=True)
print('RENDERED', sc.render.filepath)
