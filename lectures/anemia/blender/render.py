# Рендер планів. Відновлюваний: готові кадри пропускає.
#   python render.py still <план> <кадр> [ширина] [семпли]     — пробний кадр у render/stills/
#   python render.py shot <план> [ширина] [семпли] [крок]      — усі кадри плану в render/<план>/
#   python render.py track <план>                              — екранні координати клітин (для підписів) у overlay/track_<план>.json
import bpy, sys, os, json, time
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import build as B

root = os.path.dirname(here)
TL = json.load(open(os.path.join(root, 'timeline.json')))
SHOTS = {s['shot']: s for s in TL['shots']}
OUT = os.environ.get('ANEMIA_RENDER', os.path.join(root, 'render'))


def setup(shot, width, samples):
    sc = B.build(shot, SHOTS[shot]['frames'])
    sc.render.resolution_x, sc.render.resolution_y = width, width * 9 // 16
    sc.render.resolution_percentage = 100
    sc.cycles.samples = samples
    sc.render.threads_mode = 'AUTO'
    return sc


def main():
    mode, shot = sys.argv[1], sys.argv[2]
    if mode == 'still':
        frame = int(sys.argv[3]); width = int(sys.argv[4]) if len(sys.argv) > 4 else 960
        samples = int(sys.argv[5]) if len(sys.argv) > 5 else 24
        sc = setup(shot, width, samples)
        sc.frame_set(frame)
        os.makedirs(os.path.join(OUT, 'stills'), exist_ok=True)
        sc.render.filepath = os.path.join(OUT, 'stills', f'{shot}_{frame:04d}.png')
        t = time.time(); bpy.ops.render.render(write_still=True)
        print(f'STILL {shot} {frame} {time.time() - t:.1f}s')
    elif mode == 'shot':
        width = int(sys.argv[3]) if len(sys.argv) > 3 else 1280
        samples = int(sys.argv[4]) if len(sys.argv) > 4 else 24
        step = int(sys.argv[5]) if len(sys.argv) > 5 else 1
        sc = setup(shot, width, samples)
        d = os.path.join(OUT, shot); os.makedirs(d, exist_ok=True)
        t0 = time.time(); done = 0
        for f in range(0, SHOTS[shot]['frames'], step):
            p = os.path.join(d, f'{f:04d}.png')
            if os.path.exists(p):
                continue
            sc.frame_set(f); sc.render.filepath = p
            bpy.ops.render.render(write_still=True)
            done += 1
            json.dump({'shot': shot, 'frame': f, 'of': SHOTS[shot]['frames'], 'sec_per_frame': round((time.time() - t0) / done, 2)},
                      open(os.path.join(OUT, f'status_{shot}.json'), 'w'))
        print(f'SHOT {shot} done, {done} new frames, {time.time() - t0:.0f}s')
    elif mode == 'track':
        from bpy_extras.object_utils import world_to_camera_view
        sc = setup(shot, 1920, 1)
        names = [o.name for o in sc.objects if o.name.startswith('size')]
        data = []
        for f in range(SHOTS[shot]['frames']):
            sc.frame_set(f)
            row = {}
            for n in names:
                o = sc.objects[n]
                c = world_to_camera_view(sc, sc.camera, o.matrix_world.translation)
                e = world_to_camera_view(sc, sc.camera, o.matrix_world.translation + sc.camera.matrix_world.to_3x3().col[0] * o.scale.y)
                row[n] = [round(c.x * 1920, 1), round((1 - c.y) * 1080, 1), round((e.x - c.x) * 1920, 1)]
            data.append(row)
        os.makedirs(os.path.join(root, 'overlay'), exist_ok=True)
        json.dump(data, open(os.path.join(root, 'overlay', f'track_{shot}.json'), 'w'))
        print('TRACK', shot, data[0])


main()
