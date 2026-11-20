# Мозок у серединному (сагітальному) розрізі на справжній анатомії BodyParts3D: права половина, вид з боку зрізу.
import bpy, bmesh, sys, os
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bp3d, brainparts as B


def cut(o, x0, cap=None):
    """Відтинає все, що лівіше (x > x0) серединної площини, і закриває зріз; cap — матеріал площини зрізу."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(x0 - o.location.x, 0, 0), plane_no=(1, 0, 0), clear_outer=True)
    edges = [e for e in res['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
    if edges:
        fill = bmesh.ops.triangle_fill(bm, edges=edges, use_beauty=True)
        if cap:
            o.data.materials.append(cap)
            for f in fill['geom']:
                if isinstance(f, bmesh.types.BMFace): f.material_index = len(o.data.materials) - 1; f.smooth = False
    bm.to_mesh(o.data); bm.free()


def build(C):
    C.set_world((0.0015, 0.0012, 0.0015))
    T = B.tissues(C, bp3d)
    fl = bp3d.flesh
    M = {
        'whitecut': fl(C, 'whitecut', (0.84, 0.76, 0.68), (0.90, 0.84, 0.77), rough=0.5, sss=0.6, scale=0.015, bump=0.08, noise=50, coat=0.25),
        'callosum': fl(C, 'callosum', (0.90, 0.86, 0.80), (0.95, 0.92, 0.87), rough=0.45, sss=0.6, scale=0.015, bump=0.1, noise=50, coat=0.3),
        'thalamus': fl(C, 'thalamus', (0.62, 0.44, 0.42), (0.70, 0.52, 0.48), rough=0.42, sss=0.8, scale=0.015, bump=0.12, noise=45, coat=0.35),
        'hypo': fl(C, 'hypo', (0.70, 0.40, 0.36), (0.78, 0.50, 0.42), rough=0.42, sss=0.8, scale=0.015, bump=0.12, noise=45, coat=0.35),
        'gland': fl(C, 'gland', (0.62, 0.16, 0.12), (0.72, 0.26, 0.18), rough=0.35, sss=0.9, scale=0.012, bump=0.15, noise=60, coat=0.5),
        'nerve': fl(C, 'nerve', (0.88, 0.78, 0.60), (0.94, 0.86, 0.70), rough=0.4, sss=0.6, scale=0.012, bump=0.1, noise=60, coat=0.4),
        'stemcut': fl(C, 'stemcut', (0.80, 0.66, 0.58), (0.87, 0.75, 0.66), rough=0.5, sss=0.6, scale=0.015, bump=0.08, noise=50, coat=0.25),
        'cbcut': fl(C, 'cbcut', (0.70, 0.48, 0.44), (0.86, 0.74, 0.66), rough=0.5, sss=0.6, scale=0.015, bump=0.1, noise=18, coat=0.25),
    }
    D = B.DEEP
    parts = {k: T['cortex'] for k in B.CORTEX['R']}
    parts.update({k: T['cortex'] for k in B.BOTH})
    parts.update({B.WHITE: T['white'], B.CEREBELLUM: T['cerebellum'], B.PONS: T['stem'], B.MEDULLA: T['stem'], B.MIDBRAIN: T['stem'], B.PEDUNCLE: T['stem'],
                  B.CALLOSUM: M['callosum'], D['thalamusR']: M['thalamus'], D['hypothalamus']: M['hypo'], D['pituitary']: M['gland'],
                  D['pineal']: M['gland'], D['fornixR']: M['callosum'], D['mammillary']: M['callosum'], D['chiasm']: M['nerve']})
    O = bp3d.load_many(parts, anchor=B.WHITE)
    X0 = -0.004
    caps = {B.WHITE: M['whitecut'], B.CEREBELLUM: M['cbcut'], B.PONS: M['stemcut'], B.MEDULLA: M['stemcut'], B.MIDBRAIN: M['stemcut'], B.PEDUNCLE: M['stemcut'],
            B.CALLOSUM: M['callosum'], D['hypothalamus']: M['hypo'], D['pituitary']: M['gland'], D['pineal']: M['gland'], D['mammillary']: M['callosum'],
            D['chiasm']: M['nerve'], 'BP51': M['whitecut'], D['thalamusR']: M['thalamus'], D['fornixR']: M['callosum']}
    for k, o in O.items():
        cut(o, X0, caps.get(k, M['whitecut']))
    bpy.context.view_layer.update()
    for k in (B.CALLOSUM, D['thalamusR'], D['pituitary'], D['pineal'], D['chiasm'], D['hypothalamus']):
        lo, hi = bp3d.bbox(O[k]); print('BBOX', bp3d.NAMES.get(k), [round(v, 2) for v in lo], [round(v, 2) for v in hi])
    cam = C.cam(66, (6.4, -1.9, 1.0), (0.0, -0.14, -0.12), fstop=2.8)
    bpy.context.view_layer.update()
    C.area('key', (5.5, -3.0, 3.5), (0, 0, -0.1), 2.5, 640, (1.0, 0.93, 0.86))
    C.area('rim', (-4.0, 4.0, 2.5), (0, 0, 0.2), 2.0, 2400, (0.7, 0.82, 1.0))
    C.area('rim2', (-2.0, -5.0, -1.5), (0, 0, 0), 2.5, 900, (1.0, 0.5, 0.35))
    C.area('fill', (5.0, 2, -3.0), (0, 0, 0), 4.0, 25, (1.0, 0.8, 0.7))
    fp = lambda k, bias=(0, 0, 0): bp3d.front_point(O[k], cam, bias)
    left = [('поясна звивина', fp('FMA72717', (0, -0.25, 0.05))), ('мозолисте тіло', fp(B.CALLOSUM, (0, -0.3, 0.1))), ('склепіння', fp(D['fornixR'], (0, -0.05, 0.09))),
            ('гіпоталамус', fp(D['hypothalamus'])), ('зорове перехрестя', fp(D['chiasm'])), ('гіпофіз', fp(D['pituitary']))]
    right = [('таламус', fp(D['thalamusR'])), ('шишкоподібне тіло', fp(D['pineal'])), ('середній мозок', fp(B.MIDBRAIN)),
             ('мозочок', fp(B.CEREBELLUM)), ('міст', fp(B.PONS)), ('довгастий мозок', fp(B.MEDULLA))]
    labels = B.columns(left, right, xl=560, xr=1516, y0=420, y1=930)
    return {'kicker': 'Нервова система', 'title': 'Мозок у розрізі', 'sub': 'Серединний розріз, права половина', 'scrim': 'none', 'source': bp3d.CREDIT, 'labels': labels}
