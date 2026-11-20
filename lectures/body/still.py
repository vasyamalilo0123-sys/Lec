# Один кадр сцени: python still.py <сцена> [ширина=1920] [семпли=64] → render/<сцена>.png і render/<сцена>.json (екранні точки підписів)
import bpy, sys, os, json, time, importlib.util
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import common as C
if '--' in sys.argv: sys.argv = sys.argv[:1] + sys.argv[sys.argv.index('--') + 1:]
name = sys.argv[1]; width = int(sys.argv[2]) if len(sys.argv) > 2 else 1920; samples = int(sys.argv[3]) if len(sys.argv) > 3 else 64
spec = importlib.util.spec_from_file_location(name, os.path.join(here, 'scenes', name + '.py')); mod = importlib.util.module_from_spec(spec)
sc = C.scene(); spec.loader.exec_module(mod); meta = mod.build(C) or {}
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = width, width * 9 // 16; sc.cycles.samples = samples
out = os.path.join(here, 'render'); os.makedirs(out, exist_ok=True)
sc.render.filepath = os.path.join(out, name + '.png')
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
bpy.context.view_layer.update()
for lb in meta.get('labels', []):
    v = world_to_camera_view(sc, sc.camera, Vector(lb['p'])); lb['px'] = [round(v.x * 1920, 1), round((1 - v.y) * 1080, 1)]; lb['p'] = list(lb['p'])
json.dump(meta, open(os.path.join(out, name + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
t = time.time(); bpy.ops.render.render(write_still=True); print(f'STILL {name} {time.time() - t:.0f}s')
