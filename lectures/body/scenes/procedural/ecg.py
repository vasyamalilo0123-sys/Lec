# ЕКГ: провідна система крізь «рентген»-серце і світна крива PQRST перед ним.
import math, os, importlib.util
from mathutils import Vector

_spec = importlib.util.spec_from_file_location('heart_scene', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'heart.py'))
H = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(H)


def ecg_y(t):
    """Один серцевий цикл, t у [0, 1): ізолінія, P, сегмент PQ, QRS, сегмент ST, T. Висоту дано в частках зубця R."""
    g = lambda c, w, a: a * math.exp(-((t - c) / w) ** 2)
    return (g(0.18, 0.030, 0.13)          # P
            + g(0.335, 0.008, -0.10)      # Q
            + g(0.36, 0.011, 1.0)         # R
            + g(0.386, 0.009, -0.22)      # S
            + g(0.60, 0.055, 0.27))       # T


def build(C):
    C.set_world((0.002, 0.004, 0.007))
    # серце-рентген
    shell = C.mat_xray('shell', (0.9, 0.16, 0.12), strength=1.6, power=2.4, base=0.012)
    vshell = C.mat_xray('vshell', (0.75, 0.2, 0.2), strength=0.4, power=2.6, base=0.003)
    objs = H.make_heart(C, shell, vshell, vshell, vshell, vessels=True)
    import bpy
    for o in list(objs):
        if o.name == 'ivc' or o.name.startswith('pv'):
            bpy.data.objects.remove(o)
    body = objs[0]; bpy.context.view_layer.update()
    # провідна система
    gold = C.mat_emit('conduct', (1.0, 0.55, 0.08), 3.2)
    node = C.mat_emit('node', (1.0, 0.7, 0.2), 7.0)
    sa, av = Vector((-1.0, -0.2, 1.05)), Vector((-0.2, -0.1, 0.42))
    C.prim('sphere', 'sa', node, loc=sa, scale=(0.17, 0.13, 0.2), u=24, v=12)
    C.prim('sphere', 'av', node, loc=av, scale=(0.14,) * 3, u=24, v=12)
    # міжвузлові шляхи через праве передсердя
    for k, bend in enumerate(((-0.25, -0.25, 0.1), (0.1, 0.05, 0.25), (-0.45, 0.1, -0.15))):
        mid = sa.lerp(av, 0.5) + Vector(bend)
        C.tube(f'inter{k}', [sa, sa.lerp(mid, 0.5) + Vector(bend) * 0.3, mid, mid.lerp(av, 0.5) + Vector(bend) * 0.2, av], 0.022, gold)
    his_end = Vector((0.12, -0.3, 0.05))
    C.tube('his', [av, av.lerp(his_end, 0.5), his_end], 0.05, gold)
    # ніжки: ліва — по лівому боці перегородки, права — по правому, до верхівки
    lbb = [his_end, (0.42, -0.3, -0.35), (0.62, -0.3, -0.85), (0.8, -0.3, -1.3), (0.9, -0.3, -1.6)]
    rbb = [his_end, (0.1, -0.6, -0.35), (0.25, -0.72, -0.85), (0.5, -0.7, -1.3), (0.75, -0.55, -1.55)]
    C.tube('lbb', lbb, 0.038, gold); C.tube('rbb', rbb, 0.035, gold)
    # волокна Пуркіньє: віялом від кінців ніжок угору по стінках шлуночків
    import random
    rnd = random.Random(8)

    def purkinje(start, side, n, name, reach):
        """Волокна розходяться від кінця ніжки й піднімаються внутрішньою поверхнею стінки шлуночка."""
        for i in range(n):
            phi = math.radians(rnd.uniform(-80, 60)); top = rnd.uniform(0.45, 1.0) * reach
            guide = [Vector(start)]
            for j in range(1, 6):
                u = j / 5
                guide.append(Vector(start) + Vector((side * math.cos(phi) * (0.4 + 1.5 * u), math.sin(phi) * (0.3 + 1.4 * u), top * u ** 1.3 + rnd.uniform(-0.05, 0.05))))
            pts = [tuple(guide[0])] + H.snap(body, guide[1:], lift=-0.14)
            C.tube(f'{name}{i}', pts, 0.016, gold, radii=[1, 0.95, 0.85, 0.7, 0.55, 0.35], res=4)

    purkinje(lbb[-1], 1.0, 14, 'pl', 1.9); purkinje(lbb[2], 1.0, 5, 'pl2', 1.0)
    purkinje(rbb[-1], -1.0, 13, 'pr', 1.7); purkinje(rbb[2], -1.0, 5, 'pr2', 0.9)

    # крива ЕКГ: світна трубка перед серцем, два цикли
    W, Hh, x0, z0, yy = 8.4, 2.3, -4.2, -3.0, -2.6
    line = C.mat_emit('ecg', (0.03, 1.0, 0.3), 3.0)
    cycles = 2; n = 520
    pts = []
    for i in range(n + 1):
        u = i / n * cycles
        pts.append((x0 + W * i / n, yy, z0 + Hh * ecg_y(u % 1.0)))
    C.tube('ecg', pts, 0.022, line, smooth=False, res=6)
    # сітка паперу: тьмяні лінії
    grid = C.mat_emit('grid', (0.1, 0.5, 0.3), 0.35)
    for k in range(22):
        x = x0 + W * k / 21
        C.tube(f'gv{k}', [(x, yy + 0.02, z0 - 0.75), (x, yy + 0.02, z0 + Hh + 0.35)], 0.004, grid, smooth=False, res=3)
    for k in range(9):
        z = z0 - 0.75 + (Hh + 1.1) * k / 8
        C.tube(f'gh{k}', [(x0, yy + 0.02, z), (x0 + W, yy + 0.02, z)], 0.004, grid, smooth=False, res=3)

    C.cam(50, (0.0, -19.0, -0.6), (0.0, 0, -0.55), fstop=None)
    C.area('rim', (6, 6, 4), (0, 0, 0.5), 5, 1500, (1.0, 0.5, 0.4))

    def on_curve(t, dz=0.0):     # точка кривої в першому циклі
        return (x0 + W * t / cycles, yy, z0 + Hh * ecg_y(t) + dz)

    return {
        'kicker': 'Електрична активність серця', 'title': 'ЕКГ', 'sub': 'Імпульс іде від синусового вузла\nдо волокон Пуркіньє', 'scrim': 'none',
        'title_at': [96, 96],
        'labels': [
            {'text': 'синусовий вузол', 'p': tuple(sa), 'at': [1330, 250], 'align': 'left'},
            {'text': 'атріовентрикулярний вузол', 'p': tuple(av), 'at': [1330, 370], 'align': 'left'},
            {'text': 'пучок Гіса і його ніжки', 'p': (0.42, -0.3, -0.35), 'at': [1330, 490], 'align': 'left'},
            {'text': 'волокна Пуркіньє', 'p': (1.55, -0.3, -0.75), 'at': [1330, 610], 'align': 'left'},
            {'text': 'P', 'sub': 'збудження передсердь', 'p': on_curve(0.18, 0.06), 'at': [372, 790], 'align': 'right'},
            {'text': 'QRS', 'sub': 'збудження шлуночків', 'p': on_curve(0.36, 0.0), 'at': [600, 585], 'align': 'left'},
            {'text': 'T', 'sub': 'реполяризація шлуночків', 'p': on_curve(0.60, 0.06), 'at': [765, 765], 'align': 'left'},
        ],
    }
