# М'язи: усі м'язи атласу BodyParts3D поверх скелета. Волокна йдуть уздовж головної осі кожного м'яза, кінці світлішають у сухожилки.
import bpy, sys, os, math, re
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bp3d, _tree as T
from mathutils import Vector

TENDON = 'tendon|tract|linea alba|aponeurosis|ligament|retinaculum|membrane|tendinous arch'


def mat_muscle(C):
    """Волокнистий м'яз. Властивості об'єкта: ax — напрям волокон, c0 і hl — середина й піввисота вздовж нього."""
    m = C.mat('muscle', (0.3, 0.03, 0.03), rough=0.42, sss=0.6, sss_radius=(1.0, 0.2, 0.1), sss_scale=0.012, coat=0.3)
    nt = m.node_tree; N, L = nt.nodes, nt.links; P = N['P']
    def attr(name):
        a = N.new('ShaderNodeAttribute'); a.attribute_type = 'OBJECT'; a.attribute_name = name; return a
    ax, c0, hl = attr('ax'), attr('c0'), attr('hl')
    tc = N.new('ShaderNodeTexCoord')
    dot = N.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'
    L.new(tc.outputs['Object'], dot.inputs[0]); L.new(ax.outputs['Vector'], dot.inputs[1])
    # стиснути координату вздовж осі → шум витягується у волокна
    sc = N.new('ShaderNodeVectorMath'); sc.operation = 'SCALE'; L.new(ax.outputs['Vector'], sc.inputs[0])
    k = N.new('ShaderNodeMath'); k.operation = 'MULTIPLY'; k.inputs[1].default_value = 0.94
    L.new(dot.outputs['Value'], k.inputs[0]); L.new(k.outputs[0], sc.inputs['Scale'])
    sub = N.new('ShaderNodeVectorMath'); sub.operation = 'SUBTRACT'; L.new(tc.outputs['Object'], sub.inputs[0]); L.new(sc.outputs[0], sub.inputs[1])
    fib = N.new('ShaderNodeTexNoise'); fib.inputs['Scale'].default_value = 55; fib.inputs['Detail'].default_value = 5; fib.inputs['Roughness'].default_value = 0.65
    L.new(sub.outputs[0], fib.inputs['Vector'])
    big = N.new('ShaderNodeTexNoise'); big.inputs['Scale'].default_value = 9; big.inputs['Detail'].default_value = 3
    L.new(sub.outputs[0], big.inputs['Vector'])
    col = N.new('ShaderNodeMixRGB'); col.inputs['Color1'].default_value = (0.20, 0.016, 0.016, 1); col.inputs['Color2'].default_value = (0.50, 0.075, 0.05, 1)
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.3; mr.inputs['From Max'].default_value = 0.7
    mixn = N.new('ShaderNodeMath'); mixn.operation = 'MULTIPLY_ADD'; mixn.inputs[1].default_value = 0.6
    L.new(fib.outputs['Fac'], mixn.inputs[0]); 
    bm = N.new('ShaderNodeMath'); bm.operation = 'MULTIPLY'; bm.inputs[1].default_value = 0.4; L.new(big.outputs['Fac'], bm.inputs[0]); L.new(bm.outputs[0], mixn.inputs[2])
    L.new(mixn.outputs[0], mr.inputs['Value']); L.new(mr.outputs[0], col.inputs['Fac'])
    # сухожилкові кінці
    t = N.new('ShaderNodeMath'); t.operation = 'SUBTRACT'; L.new(dot.outputs['Value'], t.inputs[0]); L.new(c0.outputs['Fac'], t.inputs[1])
    td = N.new('ShaderNodeMath'); td.operation = 'DIVIDE'; L.new(t.outputs[0], td.inputs[0]); L.new(hl.outputs['Fac'], td.inputs[1])
    ta = N.new('ShaderNodeMath'); ta.operation = 'ABSOLUTE'; L.new(td.outputs[0], ta.inputs[0])
    tn = N.new('ShaderNodeMath'); tn.operation = 'MULTIPLY_ADD'; tn.inputs[1].default_value = 0.22; L.new(big.outputs['Fac'], tn.inputs[0]); L.new(ta.outputs[0], tn.inputs[2])
    ts = N.new('ShaderNodeMapRange'); ts.interpolation_type = 'SMOOTHSTEP'; ts.inputs['From Min'].default_value = 0.86; ts.inputs['From Max'].default_value = 1.06
    L.new(tn.outputs[0], ts.inputs['Value'])
    fin = N.new('ShaderNodeMixRGB'); fin.inputs['Color2'].default_value = (0.74, 0.66, 0.56, 1)
    L.new(ts.outputs[0], fin.inputs['Fac']); L.new(col.outputs[0], fin.inputs['Color1']); L.new(fin.outputs[0], P.inputs['Base Color'])
    b = N.new('ShaderNodeBump'); b.inputs['Strength'].default_value = 0.55; b.inputs['Distance'].default_value = 0.012
    L.new(fib.outputs['Fac'], b.inputs['Height']); L.new(b.outputs[0], P.inputs['Normal'])
    return m


def fiber_axis(o):
    """Головна вісь м'яза (перша головна компонента вершин) — наближення напряму волокон."""
    n = len(o.data.vertices); co = np.empty(n * 3, np.float32); o.data.vertices.foreach_get('co', co); co = co.reshape(-1, 3)[::max(1, n // 4000)]
    c = co.mean(0); u, s, vt = np.linalg.svd(co - c, full_matrices=False); ax = vt[0]
    pr = (co - c) @ ax
    o['ax'] = [float(v) for v in ax]; o['c0'] = float(c @ ax + (pr.max() + pr.min()) / 2); o['hl'] = float(max(1e-3, (pr.max() - pr.min()) / 2))


def build(C):
    C.set_world((0.0012, 0.001, 0.0012))
    mus = mat_muscle(C)
    ten = bp3d.flesh(C, 'tendon', (0.62, 0.54, 0.44), (0.80, 0.74, 0.64), rough=0.4, sss=0.5, bump=0.35, noise=90, coat=0.3)
    bone = bp3d.flesh(C, 'bone', (0.50, 0.40, 0.28), (0.70, 0.62, 0.48), rough=0.6, sss=0.3, bump=0.5, noise=110, coat=0.05)
    eye = C.mat('eye', (0.85, 0.83, 0.80), rough=0.12, sss=0.4, coat=0.8)
    O = {}
    for k in sorted(T.leaves('FMA23881')):
        n = bp3d.NAMES.get(k, '')
        if re.search('gingiva|membrane|ligament', n): continue
        O[k] = T.load(k, eye if n == 'eyeball' else bone, 8000)
    for k in sorted(T.leaves('FMA72954')):
        n = bp3d.NAMES.get(k, '')
        if k in O: continue
        if re.search(TENDON, n): O[k] = T.load(k, ten, 25000)
        else:
            O[k] = T.load(k, mus, 25000); fiber_axis(O[k])
    T.shift_all(list(O.values()), (0.0, -0.96, 11.75))
    a = math.radians(-22); d = 43.5; tgt = Vector((-1.75, 0, 0.0))
    C.cam(85, tgt + Vector((-math.sin(a) * d, -math.cos(a) * d, 1.5)), tgt, fstop=None)
    bpy.context.view_layer.update()
    C.area('key', (12, -12, 9), (0, 0, 1), 6, 7500, (1.0, 0.93, 0.86))
    C.area('rim', (-10, 11, 5), (0, 0, 0.5), 7, 30000, (0.5, 0.72, 1.0))
    C.area('rim2', (12, 9, -2), (0, 0, 0), 7, 12000, (1.0, 0.5, 0.32))
    C.area('fill', (-8, -12, -6), (0, 0, -1), 10, 300, (0.6, 0.7, 1.0))
    by = {bp3d.NAMES.get(k, ''): k for k in O}
    def fp(name, **kw):
        if name not in by: print('MISSING', name, [n for n in by if name.split()[-1] in n][:6]); return None
        return bp3d.front_point(O[by[name]], **kw)
    want = [('грудинно-ключично-соскоподібний м\'яз', 'right sternocleidomastoid', {}, 'L'),
            ('дельтоподібний м\'яз', 'acromial part of right deltoid', {}, 'L'),
            ('великий грудний м\'яз', 'sternocostal part of right pectoralis major', {}, 'L'),
            ('двоголовий м\'яз плеча', 'long head of right biceps brachii', {'bias': (0, 0, -0.5)}, 'L'),
            ('зовнішній косий м\'яз живота', 'right external oblique', {'bias': (-0.7, 0, 0.2)}, 'L'),
            ('прямий м\'яз живота', 'left rectus abdominis', {}, 'R'),
            ('трапецієподібний м\'яз', 'descending part of left trapezius', {}, 'R'),
            ('плечо-променевий м\'яз', 'left brachioradialis', {'bias': (0, 0, -0.4)}, 'R'),
            ('триголовий м\'яз плеча', 'lateral head of left triceps brachii', {}, 'R')]
    items = []
    for t, n, kw, s in want:
        p = fp(n, **kw)
        if p: items.append((t, p, s)); print('LBL', t, [round(v) for v in T.px(p)], s)
    L = T.auto_labels([i for i in items if i[2] == 'L'], 800, 1470, y0=420) + T.auto_labels([i for i in items if i[2] == 'R'], 800, 1470, y0=96)
    return {'kicker': 'Опорно-рухова система', 'title': 'М\'язи', 'sub': 'Скелетні м\'язи поверх кісток', 'scrim': 'none',
            'source': bp3d.CREDIT, 'labels': L}
