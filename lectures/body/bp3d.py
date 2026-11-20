# Справжня анатомія: сітки BodyParts3D (DBCLS, CC BY-SA 2.1 Japan), зняті з томографії. Самі файли в репозиторій не кладемо:
#   git clone --depth 1 https://github.com/Kevin-Mattheus-Moerman/BodyParts3D  і вказати BP3D=<шлях>/assets/BodyParts3D_data
import bpy, bmesh, os
from mathutils import Vector
ROOT = os.environ.get('BP3D', '/tmp/claude-0/-home-user-Lec/c994ffbc-a2cd-5240-99d0-10fbc375d8fd/scratchpad/assets/bp3d/assets/BodyParts3D_data')
CREDIT = 'Анатомічні моделі: BodyParts3D, © The Database Center for Life Science, CC BY-SA 2.1 Japan'
SCALE = 0.01   # міліметри атласу → одиниця сцени = 10 см


def load(fma, material=None, name=None, smooth_angle=None):
    """Завантажує частину тіла за ідентифікатором FMA. Зварює вершини, щоб згладжування працювало."""
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=os.path.join(ROOT, 'stl', fma + '.stl'), global_scale=SCALE)
    o = (set(bpy.data.objects) - before).pop(); o.name = name or fma
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    for f in bm.faces: f.smooth = True
    bm.to_mesh(o.data); bm.free()
    o.data.materials.clear()
    if material: o.data.materials.append(material)
    o.select_set(False)
    return o


def recenter(objs, anchor):
    """Зсуває всі об'єкти так, щоб центр anchor опинився в нулі. Повертає зсув."""
    bb = [anchor.matrix_world @ Vector(c) for c in anchor.bound_box]
    c = sum(bb, Vector()) / 8
    for o in objs: o.location -= c
    bpy.context.view_layer.update()
    return c


def bbox(o):
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb))), Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
