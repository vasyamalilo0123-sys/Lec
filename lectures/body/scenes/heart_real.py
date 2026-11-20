# Серце на справжній анатомії (BodyParts3D): стінка серця, вінцеві артерії й вени, великі судини.
import bpy, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bp3d


def flesh(C, name, c1, c2, rough=0.38, sss=0.9, scale=0.012, bump=0.25, noise=28.0, coat=0.45):
    """Жива тканина: два відтінки за шумом, дрібний рельєф, підповерхневе розсіювання, волога плівка."""
    m = C.mat(name, c1, rough=rough, sss=sss, sss_radius=(1.0, 0.25, 0.12), sss_scale=scale, coat=coat)
    nt = m.node_tree; N, L = nt.nodes, nt.links; P = N['P']
    tc = N.new('ShaderNodeTexCoord')
    n1 = N.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = noise * 0.25; n1.inputs['Detail'].default_value = 8
    n2 = N.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = noise * 4; n2.inputs['Detail'].default_value = 6
    L.new(tc.outputs['Object'], n1.inputs['Vector']); L.new(tc.outputs['Object'], n2.inputs['Vector'])
    mix = N.new('ShaderNodeMixRGB'); mix.inputs['Color1'].default_value = (*c1, 1); mix.inputs['Color2'].default_value = (*c2, 1)
    cr = N.new('ShaderNodeMapRange'); cr.inputs['From Min'].default_value = 0.35; cr.inputs['From Max'].default_value = 0.7
    L.new(n1.outputs['Fac'], cr.inputs['Value']); L.new(cr.outputs[0], mix.inputs['Fac']); L.new(mix.outputs[0], P.inputs['Base Color'])
    h = N.new('ShaderNodeMath'); h.operation = 'MULTIPLY_ADD'; h.inputs[1].default_value = 0.4
    L.new(n2.outputs['Fac'], h.inputs[0]); L.new(n1.outputs['Fac'], h.inputs[2])
    b = N.new('ShaderNodeBump'); b.inputs['Strength'].default_value = bump; b.inputs['Distance'].default_value = 0.02
    L.new(h.outputs[0], b.inputs['Height']); L.new(b.outputs[0], P.inputs['Normal'])
    rr = N.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = rough - 0.12; rr.inputs['To Max'].default_value = rough + 0.15
    L.new(n2.outputs['Fac'], rr.inputs['Value']); L.new(rr.outputs[0], P.inputs['Roughness'])
    return m


def build(C):
    C.set_world((0.0015, 0.0012, 0.0015))
    myo = flesh(C, 'myocardium', (0.33, 0.035, 0.03), (0.52, 0.11, 0.07))
    art = flesh(C, 'artery', (0.50, 0.03, 0.025), (0.62, 0.06, 0.04), rough=0.3, bump=0.1, noise=60)
    vein = flesh(C, 'vein', (0.10, 0.06, 0.16), (0.16, 0.08, 0.20), rough=0.32, bump=0.1, noise=60)
    aorta = flesh(C, 'aorta', (0.62, 0.30, 0.24), (0.74, 0.46, 0.36), rough=0.42, bump=0.15, noise=40, sss=0.6)
    pulm = flesh(C, 'pulm', (0.42, 0.33, 0.42), (0.55, 0.45, 0.52), rough=0.42, bump=0.15, noise=40, sss=0.6)
    cava = flesh(C, 'cava', (0.16, 0.10, 0.22), (0.24, 0.14, 0.28), rough=0.4, bump=0.15, noise=40, sss=0.6)
    parts = {'FMA7274': myo, 'FMA3736': aorta, 'FMA3768': aorta, 'FMA3784': aorta, 'FMA66326': pulm, 'FMA66643': cava, 'FMA4720': cava, 'FMA10951': cava,
             'FMA3802': art, 'FMA3818': art, 'FMA3840nsn': art, 'FMA3862nsn': art, 'FMA3895': art, 'FMA4685': art, 'FMA76994': art,
             'FMA4707': vein, 'FMA4713': vein, 'FMA71567': vein, 'FMA76751': vein, 'FMA4706': vein}
    objs = {k: bp3d.load(k, m) for k, m in parts.items()}
    bp3d.recenter(list(objs.values()), objs['FMA7274'])
    lo, hi = bp3d.bbox(objs['FMA7274'])
    print('HEART bbox', tuple(round(v, 2) for v in lo), tuple(round(v, 2) for v in hi))
    c = C.cam(85, (0.9, -9.6, 0.6), (-0.75, 0, 0.18), fstop=1.1, focus=8.9)
    C.area('key', (-4.0, -4.5, 4.0), (0, -0.5, 0.2), 2.2, 520, (1.0, 0.93, 0.86))
    C.area('rim', (4.0, 3.5, 2.5), (0, 0, 0.2), 2.0, 2600, (0.7, 0.82, 1.0))
    C.area('rim2', (-3.5, 4.0, -1.5), (0, 0, 0), 2.5, 1100, (1.0, 0.5, 0.35))
    C.area('fill', (3.0, -4, -3.0), (0, 0, 0), 4.0, 35, (0.6, 0.7, 1.0))
    return {'kicker': 'Серцево-судинна система', 'title': 'Серце', 'sub': 'Справжня анатомія:\nстінка, вінцеві судини, аорта, легеневі судини', 'scrim': 'left', 'source': bp3d.CREDIT, 'labels': []}
