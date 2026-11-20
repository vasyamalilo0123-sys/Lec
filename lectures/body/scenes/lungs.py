# Легені: трахея з хрящовими півкільцями, головні бронхи й бронхіальне дерево, вирощене алгоритмом
# «колонізації простору» в об'ємі кожної легені. Оболонка легень — прозора, поділена на частки.
# Вид спереду: правий бік пацієнта — ліворуч у кадрі (x < 0).
import bpy, bmesh, math, random
import numpy as np
from mathutils import Vector

CARINA = Vector((0.0, 0.0, 2.0))
HILUM = {-1: Vector((-0.95, 0.0, 0.72)), 1: Vector((1.62, 0.0, 0.78))}    # кінець правого (коротший, крутіший) і лівого головного бронха
HEART = Vector((0.35, -0.5, -1.5))


def deform(u, s, push=True):
    """Точка одиничної кулі → точка легені (s = -1 права, +1 ліва)."""
    x, y, z = u[0] * 1.9, u[1] * 1.45, u[2] * 3.3
    if -s * x > 0:                      # медіальний бік плоскіший
        x *= 0.55
    if z > 0:                           # верхівка вужча
        k = 1 - 0.45 * (z / 3.3) ** 2
        x *= k; y *= k
    else:
        z *= 0.85
    floor = -2.75 + 0.75 * (1 - min(1.0, (x / 1.9) ** 2 + (y / 1.45) ** 2))    # увігнута діафрагмальна поверхня
    z = max(z, floor)
    p = Vector((x + s * 2.45, y, z - 0.2))
    d = p - HEART
    R = 1.78 if s > 0 else 1.5          # серцеве вдавлення; ліворуч глибше — серцева вирізка
    dd = math.sqrt(d.x ** 2 + (0.4 * d.y) ** 2 + d.z ** 2)     # вдавлення витягнуте спереду назад, тому видно й у силуеті
    if dd < R:
        if not push:
            return None
        k = R / max(dd, 1e-6)
        p = Vector((HEART.x + d.x * k, p.y, HEART.z + d.z * k))
    return p


def lung_shell(C, s, material):
    """Оболонка легені, розрізана щілинами на частки. Повертає {назва частки: центр}."""
    def base():
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=72, v_segments=48, radius=1)
        for v in bm.verts:
            v.co = deform(v.co, s)
        return bm

    c = Vector((s * 2.45, 0, -0.2))
    obl_co, obl_no = c + Vector((0, 0.1, -0.1)), Vector((0, -0.72, 0.69)).normalized()    # коса щілина: згори-ззаду донизу-вперед
    hor_co, hor_no = c + Vector((0, 0, 0.35)), Vector((0, 0.12, 1)).normalized()          # горизонтальна щілина правої легені
    lobes = {'upper': [(obl_co, obl_no, +1)] + ([(hor_co, hor_no, +1)] if s < 0 else []),
             'lower': [(obl_co, obl_no, -1)]}
    if s < 0:
        lobes['middle'] = [(obl_co, obl_no, +1), (hor_co, hor_no, -1)]
    centers = {}
    for name, cuts in lobes.items():
        bm = base()
        shift = Vector((0, 0, 0))
        for co, no, side in cuts:
            r = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                       clear_inner=side > 0, clear_outer=side < 0)
            edges = [e for e in r['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
            bmesh.ops.edgeloop_fill(bm, edges=edges)
            shift += no * side * 0.035      # щілина між частками
        for v in bm.verts:
            v.co += shift
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
        for f in bm.faces:
            f.smooth = True
        me = bpy.data.meshes.new(f'lobe_{s}_{name}'); bm.to_mesh(me)
        cen = sum((v.co for v in bm.verts), Vector()) / len(bm.verts)
        bm.free()
        o = C.link(bpy.data.objects.new(me.name, me)); me.materials.append(material)
        o.visible_shadow = False
        centers[name] = cen
    return centers


def grow(s, rnd, n_attr=2800, step=0.11, kill=0.16):
    """Колонізація простору: гілки тягнуться до ще не «провентильованих» точок об'єму. Повертає (точки, батьки)."""
    attr = []
    while len(attr) < n_attr:
        u = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
        if u.length < 0.93:
            q = deform(u * 0.97, s, push=False)
            if q is not None:
                attr.append(q)
    A = np.array(attr)
    root = HILUM[s]
    d0 = (HILUM[s] - CARINA).normalized()
    pts = [np.array(root), np.array(root + d0 * step)]
    par = [-1, 0]
    for _ in range(220):
        if len(A) == 0:
            break
        P = np.array(pts)
        D = np.linalg.norm(A[:, None, :] - P[None, :, :], axis=2)
        near = D.argmin(1)
        A = A[D.min(1) > kill]
        near = near[D.min(1) > kill]
        if len(A) == 0:
            break
        new = []
        for i in np.unique(near):
            v = (A[near == i] - P[i]); v = (v / np.linalg.norm(v, axis=1)[:, None]).sum(0)
            n = np.linalg.norm(v)
            if n < 1e-6:
                continue
            q = P[i] + v / n * step
            if np.min(np.linalg.norm(P - q, axis=1)) > step * 0.45:
                new.append((q, i))
        if not new:
            break
        for q, i in new:
            pts.append(q); par.append(int(i))
    return pts, par


def tree_curve(C, name, pts, par, mat_big, mat_small, r_leaf=0.011, expo=2.6, r_root=0.27):
    """Радіуси за законом Мюррея (r³ батька ≈ сума r³ гілок), дерево — одна крива з багатьох сплайнів."""
    n = len(pts)
    kids = [[] for _ in range(n)]
    for i, p in enumerate(par):
        if p >= 0:
            kids[p].append(i)
    r = [0.0] * n
    for i in range(n - 1, -1, -1):          # діти завжди мають більший індекс
        r[i] = r_leaf if not kids[i] else sum(r[k] ** expo for k in kids[i]) ** (1 / expo)
    k = r_root / r[0]
    r = [min(r_root, x * k ** 0.6) if x * k ** 0.6 > r_leaf else max(x, r_leaf) for x in r]
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    cu.bevel_depth = 1.0; cu.bevel_resolution = 4; cu.use_fill_caps = True
    cu.materials.append(mat_big); cu.materials.append(mat_small)
    starts = [0] + [i for i in range(n) if par[i] >= 0 and len(kids[par[i]]) > 1]
    for st in starts:
        chain = [par[st]] if par[st] >= 0 else []
        i = st
        while True:
            chain.append(i)
            if len(kids[i]) != 1:
                break
            i = kids[i][0]
        if len(chain) < 2:
            continue
        sp = cu.splines.new('NURBS' if len(chain) > 2 else 'POLY'); sp.points.add(len(chain) - 1)
        for j, idx in enumerate(chain):
            rad = r[idx] if not (j == 0 and par[st] >= 0) else min(r[idx], r[st] * 1.15)
            sp.points[j].co = (*pts[idx], 1); sp.points[j].radius = rad
        if sp.type == 'NURBS':
            sp.use_endpoint_u = True; sp.order_u = min(4, len(chain)); sp.resolution_u = 3
        sp.material_index = 0 if r[st] > 0.07 else 1
    leaves = [pts[i] for i in range(n) if not kids[i]]
    return C.link(bpy.data.objects.new(name, cu)), leaves


def rings(C, a, b, n, radius, thick, material, back=Vector((0, 1, 0)), gap=math.radians(80)):
    """Хрящові півкільця вздовж відрізка a→b, розімкнені ззаду."""
    axis = (b - a).normalized()
    bk = (back - axis * back.dot(axis)).normalized(); side = axis.cross(bk)
    for i in range(n):
        c = a.lerp(b, (i + 0.5) / n)
        pts = []
        for j in range(17):
            ang = gap / 2 + (2 * math.pi - gap) * j / 16
            pts.append(c + (bk * math.cos(ang) + side * math.sin(ang)) * radius)
        C.tube('ring', pts, thick, material, res=4)


def build(C):
    rnd = random.Random(5)
    C.set_world((0.004, 0.005, 0.008))
    m_big = C.mat('airway', (0.86, 0.62, 0.55), rough=0.35, sss=0.6, sss_radius=(1.0, 0.4, 0.25), sss_scale=0.08, coat=0.5)
    m_small = C.mat('bronchiole', (0.85, 0.36, 0.30), rough=0.4, sss=0.5, sss_radius=(1.0, 0.3, 0.2), sss_scale=0.04, coat=0.3)
    m_cart = C.mat('cartilage', (0.90, 0.86, 0.78), rough=0.3, sss=0.5, sss_radius=(0.8, 0.7, 0.5), sss_scale=0.05, coat=0.6)
    m_shell = C.mat_xray('pleura', (0.42, 0.62, 1.0), strength=1.7, power=2.8, base=0.006)
    m_acin = C.mat('acinus', (0.92, 0.50, 0.46), rough=0.5, sss=0.8, sss_radius=(1.0, 0.4, 0.3), sss_scale=0.05)
    acinus = C.prim('ico', 'acinus_src', m_acin, loc=(0, 0, 60), subdiv=2)

    top = Vector((0.0, 0.05, 4.9))
    C.tube('trachea', [top, Vector((0, 0.03, 3.4)), CARINA + Vector((0, 0, 0.12))], 0.37, m_big, res=10, smooth=False)
    rings(C, top, CARINA + Vector((0, 0, 0.25)), 13, 0.375, 0.07, m_cart)
    for s, rad in ((-1, 0.30), (1, 0.25)):
        C.tube(f'main{s}', [CARINA + Vector((0, 0, 0.1)), CARINA.lerp(HILUM[s], 0.5), HILUM[s]], rad, m_big,
               radii=[1.15, 1.0, 0.95], res=10)
        rings(C, CARINA.lerp(HILUM[s], 0.22), CARINA.lerp(HILUM[s], 0.97), 4 if s < 0 else 6, rad * 1.04, 0.04, m_cart)
    C.prim('sphere', 'carina', m_big, loc=CARINA + Vector((0, 0, 0.05)), scale=(0.4, 0.37, 0.33), u=32, v=16)

    lob = {}
    for s in (-1, 1):
        pts, par = grow(s, rnd)
        _, leaves = tree_curve(C, f'tree{s}', pts, par, m_big, m_small)
        print('lung', s, 'nodes', len(pts), 'leaves', len(leaves))
        for q in leaves:                 # ацинуси: грона альвеол на кінцях бронхіол
            for _ in range(3):
                C.instance(acinus, 'acinus', [q[i] + rnd.uniform(-0.07, 0.07) for i in range(3)], scale=rnd.uniform(0.032, 0.062))
        lob[s] = lung_shell(C, s, m_shell)

    C.cam(50, (-0.75, -22.6, 0.6), (-0.75, 0, 0.6))
    C.area('key', (-8, -11, 10), (0, 0, 0.5), 7, 6000, (1.0, 0.93, 0.86))
    C.area('rimL', (10, 9, 4), (0, 0, 0), 8, 9000, (0.45, 0.65, 1.0))
    C.area('rimR', (-10, 9, -2), (0, 0, 0), 8, 6000, (1.0, 0.5, 0.4))
    C.area('fill', (4, -10, -7), (0, 0, -1), 10, 500, (0.6, 0.7, 1.0))

    return {
        'kicker': 'Дихальна система', 'title': 'Легені', 'sub': 'Бронхіальне дерево',
        'scrim': 'none', 'title_at': [96, 96], 'title_size': 104,
        'labels': [
            {'text': 'трахея', 'sub': 'хрящові півкільця', 'p': [0.38, -0.1, 3.9], 'at': [1250, 110], 'align': 'left'},
            {'text': 'правий головний бронх', 'sub': 'коротший, ширший, крутіший', 'p': list(CARINA.lerp(HILUM[-1], 0.55) + Vector((-0.2, -0.25, 0.12))), 'at': [925, 110], 'align': 'right'},
            {'text': 'лівий головний бронх', 'sub': 'довший і пологіший', 'p': list(CARINA.lerp(HILUM[1], 0.7) + Vector((0, -0.25, -0.2))), 'at': [1190, 640], 'align': 'right'},
            {'text': 'серцева вирізка', 'p': [2.08, -0.4, -1.6], 'at': [1190, 830], 'align': 'right'},
            {'text': 'верхня частка', 'p': [-3.1, -1.1, 1.5], 'at': [470, 500], 'align': 'right'},
            {'text': 'середня частка', 'p': [-3.2, -1.1, -0.7], 'at': [470, 700], 'align': 'right'},
            {'text': 'нижня частка', 'p': [-3.1, -0.9, -2.1], 'at': [470, 900], 'align': 'right'},
            {'text': 'верхня частка', 'p': [3.3, -1.1, 0.9], 'at': [1610, 500], 'align': 'left'},
            {'text': 'нижня частка', 'p': [3.4, -0.9, -2.1], 'at': [1610, 900], 'align': 'left'},
        ],
    }
