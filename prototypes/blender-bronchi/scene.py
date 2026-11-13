"""Сцена Blender (Cycles): матеріали, світло, камери, стани «у фокусі».

Використання як модуля:  import scene; S = scene.build(geo_dir); S.render(shot, state, path, ...)
"""
import json
import math
import os

import bpy
import numpy as np
from mathutils import Vector

SC = 0.01  # 1 одиниця Blender = 100 мм
GROUPS = ["trachea", "br_r", "br_l", "lob_r", "lob_l"]


def V(p):
    return Vector([c * SC for c in p])


def load_mesh(name, path, attrs):
    d = np.load(path)
    v, f = d["v"] * SC, d["f"]
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(v))
    me.vertices.foreach_set("co", v.ravel())
    me.loops.add(len(f) * 3)
    me.loops.foreach_set("vertex_index", f.ravel())
    me.polygons.add(len(f))
    me.polygons.foreach_set("loop_start", np.arange(0, len(f) * 3, 3))
    me.polygons.foreach_set("loop_total", np.full(len(f), 3))
    me.polygons.foreach_set("use_smooth", np.ones(len(f), bool))
    me.update(calc_edges=True)
    for a in attrs:
        arr = d[a]
        if arr.ndim == 2:
            for i in range(arr.shape[1]):
                at = me.attributes.new(f"{a}{i}", "FLOAT", "POINT")
                at.data.foreach_set("value", arr[:, i])
        else:
            at = me.attributes.new(a, "FLOAT", "POINT")
            at.data.foreach_set("value", arr)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


class NT:
    """Невеликий помічник для збирання вузлів матеріалу."""

    def __init__(self, mat):
        self.t = mat.node_tree
        self.t.nodes.clear()

    def n(self, kind, **kw):
        node = self.t.nodes.new(kind)
        for k, v in kw.items():
            if k.startswith("i_"):
                node.inputs[k[2:].replace("_", " ")].default_value = v
            else:
                setattr(node, k, v)
        return node

    def link(self, a, b):
        self.t.links.new(a, b)

    def attr(self, name):
        return self.n("ShaderNodeAttribute", attribute_name=name).outputs["Fac"]

    def val(self, name, v=1.0):
        node = self.n("ShaderNodeValue")
        node.name = node.label = name
        node.outputs[0].default_value = v
        return node.outputs[0]

    def math(self, op, a, b=None, clamp=False):
        node = self.n("ShaderNodeMath", operation=op, use_clamp=clamp)
        for i, x in enumerate((a, b)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                node.inputs[i].default_value = x
            else:
                self.link(x, node.inputs[i])
        return node.outputs[0]

    def mix(self, fac, a, b):
        node = self.n("ShaderNodeMix", data_type="RGBA")
        for sock, x in ((node.inputs[0], fac), (node.inputs[6], a), (node.inputs[7], b)):
            if isinstance(x, (int, float)):
                sock.default_value = x
            elif isinstance(x, tuple):
                sock.default_value = (*x, 1.0)
            else:
                self.link(x, sock)
        return node.outputs[2]

    def ramp(self, fac, stops):
        node = self.n("ShaderNodeValToRGB")
        el = node.color_ramp.elements
        while len(el) < len(stops):
            el.new(0.5)
        for e, (pos, col) in zip(el, stops):
            e.position = pos
            e.color = (*col, 1) if len(col) == 3 else col
        self.link(fac, node.inputs[0])
        return node.outputs[0]

    def noise(self, scale, detail=4, rough=0.55, vec=None, dist=0.0):
        node = self.n("ShaderNodeTexNoise")
        node.inputs["Scale"].default_value = scale
        node.inputs["Detail"].default_value = detail
        node.inputs["Roughness"].default_value = rough
        node.inputs["Distortion"].default_value = dist
        if vec is not None:
            self.link(vec, node.inputs["Vector"])
        return node.outputs["Fac"]

    def voronoi_edge(self, scale, vec=None):
        node = self.n("ShaderNodeTexVoronoi", feature="DISTANCE_TO_EDGE")
        node.inputs["Scale"].default_value = scale
        if vec is not None:
            self.link(vec, node.inputs["Vector"])
        return node.outputs["Distance"]

    def grey(self, col, focus, dim=0.42):
        """Правило стилю: поза фокусом — сіре й темніше."""
        hsv = self.n("ShaderNodeHueSaturation")
        hsv.inputs["Saturation"].default_value = 0.06
        hsv.inputs["Value"].default_value = dim
        self.link(col, hsv.inputs["Color"])
        return self.mix(focus, hsv.outputs[0], col)


def coords(nt):
    return nt.n("ShaderNodeNewGeometry").outputs["Position"]


def airway_material():
    mat = bpy.data.materials.new("airway")
    mat.use_nodes = True
    nt = NT(mat)
    pos = coords(nt)
    cart, inner, cutface = nt.attr("cart"), nt.attr("inner"), nt.attr("cutface")
    focus = None
    for i, g in enumerate(GROUPS):
        term = nt.math("MULTIPLY", nt.attr(f"w{i}"), nt.val("focus_" + g, 1.0))
        focus = term if focus is None else nt.math("ADD", focus, term)
    focus = nt.math("MINIMUM", focus, 1.0)

    # зовнішня поверхня: адвентиція з дрібними судинами, під нею перлинно-білі хрящі
    n1 = nt.noise(55, 5, 0.6, pos)
    n2 = nt.noise(260, 3, 0.6, pos)
    tissue = nt.ramp(n1, [(0.3, (0.56, 0.20, 0.16)), (0.72, (0.76, 0.38, 0.31))])
    cartc = nt.ramp(n2, [(0.3, (0.78, 0.66, 0.54)), (0.75, (0.90, 0.83, 0.72))])
    cm = nt.math("MULTIPLY", cart, nt.math("ADD", 0.72, nt.math("MULTIPLY", n1, 0.3)), clamp=True)
    outer = nt.mix(cm, tissue, cartc)
    # судинний малюнок
    warp = nt.n("ShaderNodeMixRGB", blend_type="ADD")
    warp.inputs[0].default_value = 0.035
    nt.link(pos, warp.inputs[1])
    wn = nt.n("ShaderNodeTexNoise")
    wn.inputs["Scale"].default_value = 22
    nt.link(pos, wn.inputs["Vector"])
    nt.link(wn.outputs["Color"], warp.inputs[2])
    ve = nt.voronoi_edge(34, warp.outputs[0])
    vess = nt.ramp(ve, [(0.0, (1, 1, 1)), (0.035, (0, 0, 0))])
    ve2 = nt.voronoi_edge(95, warp.outputs[0])
    vess2 = nt.ramp(ve2, [(0.0, (0.6, 0.6, 0.6)), (0.05, (0, 0, 0))])
    vmask = nt.math("MULTIPLY", nt.math("MAXIMUM", vess, vess2), nt.math("SUBTRACT", 1.0, nt.math("MULTIPLY", cart, 0.55)))
    vmask = nt.math("MULTIPLY", vmask, nt.ramp(nt.noise(9, 2, 0.5, pos), [(0.4, (0, 0, 0)), (0.62, (1, 1, 1))]))
    outer = nt.mix(nt.math("MULTIPLY", vmask, 0.8), outer, (0.33, 0.03, 0.035))
    # слизова просвіту та зріз стінки
    muc = nt.ramp(n1, [(0.25, (0.50, 0.13, 0.13)), (0.8, (0.70, 0.27, 0.25))])
    ringa = nt.attr("ring")
    muc = nt.mix(nt.math("MULTIPLY", ringa, 0.5), muc, (0.80, 0.50, 0.44))
    mv = nt.ramp(nt.voronoi_edge(48, warp.outputs[0]), [(0.0, (1, 1, 1)), (0.04, (0, 0, 0))])
    muc = nt.mix(nt.math("MULTIPLY", mv, 0.45), muc, (0.36, 0.04, 0.05))
    cutc = nt.mix(nt.math("MULTIPLY", cart, cutface), muc, (0.93, 0.90, 0.84))
    col = nt.mix(inner, outer, cutc)
    col = nt.grey(col, focus)

    bsdf = nt.n("ShaderNodeBsdfPrincipled")
    nt.link(col, bsdf.inputs["Base Color"])
    nt.link(nt.math("MULTIPLY", focus, nt.math("SUBTRACT", 1.0, nt.math("MULTIPLY", inner, 0.65))), bsdf.inputs["Subsurface Weight"])
    bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.32, 0.2)
    bsdf.inputs["Subsurface Scale"].default_value = 1.3 * SC
    rough = nt.math("ADD", 0.26, nt.math("MULTIPLY", n2, 0.22))
    nt.link(rough, bsdf.inputs["Roughness"])
    nt.link(nt.math("ADD", 0.5, nt.math("MULTIPLY", inner, 0.45)), bsdf.inputs["Coat Weight"])
    bsdf.inputs["Coat Roughness"].default_value = 0.12
    bump = nt.n("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.6 * SC
    h = nt.math("ADD", nt.math("MULTIPLY", n2, 0.5), nt.math("MULTIPLY", vmask, 0.9))
    h = nt.math("ADD", h, nt.math("MULTIPLY", nt.math("MULTIPLY", ringa, inner), 1.2))
    nt.link(h, bump.inputs["Height"])
    nt.link(bump.outputs[0], bsdf.inputs["Normal"])
    nt.link(bump.outputs[0], bsdf.inputs["Coat Normal"])
    out = nt.n("ShaderNodeOutputMaterial")
    nt.link(bsdf.outputs[0], out.inputs["Surface"])
    return mat


def lung_material():
    mat = bpy.data.materials.new("lung")
    mat.use_nodes = True
    nt = NT(mat)
    pos = coords(nt)
    lobe = nt.attr("lobe")
    n1 = nt.noise(3.2, 6, 0.62, pos, 0.5)
    n2 = nt.noise(90, 4, 0.6, pos)
    base = nt.ramp(n1, [(0.3, (0.36, 0.17, 0.19)), (0.5, (0.56, 0.27, 0.27)), (0.75, (0.68, 0.38, 0.36))])
    # частки ледь різняться тоном
    tint = nt.n("ShaderNodeHueSaturation")
    nt.link(base, tint.inputs["Color"])
    nt.link(nt.math("ADD", 0.93, nt.math("MULTIPLY", lobe, 0.06)), tint.inputs["Value"])
    nt.link(nt.math("SUBTRACT", 1.03, nt.math("MULTIPLY", lobe, 0.05)), tint.inputs["Saturation"])
    base = tint.outputs[0]
    # малюнок часточок з антракотичним пігментом у перегородках
    warp = nt.n("ShaderNodeMixRGB", blend_type="ADD")
    warp.inputs[0].default_value = 0.16
    nt.link(pos, warp.inputs[1])
    wn = nt.n("ShaderNodeTexNoise")
    wn.inputs["Scale"].default_value = 6
    nt.link(pos, wn.inputs["Vector"])
    nt.link(wn.outputs["Color"], warp.inputs[2])
    ve = nt.voronoi_edge(11, warp.outputs[0])
    septa = nt.ramp(ve, [(0.0, (0.7, 0.7, 0.7)), (0.05, (0, 0, 0))])
    patch = nt.ramp(nt.noise(1.6, 4, 0.6, pos), [(0.4, (0, 0, 0)), (0.68, (1, 1, 1))])
    pig = nt.math("MULTIPLY", septa, nt.math("ADD", 0.05, nt.math("MULTIPLY", patch, 0.9)))
    speck = nt.ramp(nt.noise(60, 3, 0.6, pos), [(0.6, (0, 0, 0)), (0.7, (1, 1, 1))])
    pig = nt.math("MAXIMUM", pig, nt.math("MULTIPLY", speck, nt.math("MULTIPLY", patch, 0.7)))
    col = nt.mix(nt.math("MULTIPLY", pig, 0.72), base, (0.10, 0.09, 0.11))
    focus = nt.val("focus_lungs", 1.0)
    col = nt.grey(col, focus, dim=0.5)

    bsdf = nt.n("ShaderNodeBsdfPrincipled")
    nt.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Subsurface Weight"].default_value = 1.0
    bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.4, 0.3)
    bsdf.inputs["Subsurface Scale"].default_value = 3.0 * SC
    nt.link(nt.math("ADD", 0.3, nt.math("MULTIPLY", n2, 0.2)), bsdf.inputs["Roughness"])
    bsdf.inputs["Coat Weight"].default_value = 0.7
    bsdf.inputs["Coat Roughness"].default_value = 0.1
    bump = nt.n("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.3
    bump.inputs["Distance"].default_value = 1.0 * SC
    h = nt.math("SUBTRACT", nt.math("MULTIPLY", n2, 0.4), nt.math("MULTIPLY", pig, 0.5))
    nt.link(h, bump.inputs["Height"])
    nt.link(bump.outputs[0], bsdf.inputs["Normal"])
    # «прозорий» стан: легеня стає ледь помітною оболонкою, щоб було видно бронхи всередині
    ghost = nt.val("ghost", 0.0)
    lw = nt.n("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.25
    rim = nt.math("ADD", 0.012, nt.math("MULTIPLY", lw.outputs["Facing"], 0.13))
    glass = nt.n("ShaderNodeBsdfPrincipled")
    glass.inputs["Base Color"].default_value = (0.62, 0.66, 0.72, 1)
    glass.inputs["Roughness"].default_value = 0.35
    tr = nt.n("ShaderNodeBsdfTransparent")
    gm = nt.n("ShaderNodeMixShader")
    nt.link(rim, gm.inputs[0])
    nt.link(tr.outputs[0], gm.inputs[1])
    nt.link(glass.outputs[0], gm.inputs[2])
    fin = nt.n("ShaderNodeMixShader")
    nt.link(ghost, fin.inputs[0])
    nt.link(bsdf.outputs[0], fin.inputs[1])
    nt.link(gm.outputs[0], fin.inputs[2])
    out = nt.n("ShaderNodeOutputMaterial")
    nt.link(fin.outputs[0], out.inputs["Surface"])
    return mat


def pea_material():
    mat = bpy.data.materials.new("pea")
    mat.use_nodes = True
    nt = NT(mat)
    tc = nt.n("ShaderNodeTexCoord").outputs["Object"]
    n1 = nt.noise(3.0, 4, 0.55, tc)
    n2 = nt.noise(40, 3, 0.6, tc)
    col = nt.ramp(n1, [(0.3, (0.17, 0.30, 0.03)), (0.7, (0.36, 0.50, 0.09))])
    bsdf = nt.n("ShaderNodeBsdfPrincipled")
    nt.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Subsurface Weight"].default_value = 0.45
    bsdf.inputs["Subsurface Radius"].default_value = (0.5, 1.0, 0.2)
    bsdf.inputs["Subsurface Scale"].default_value = 1.2 * SC
    bsdf.inputs["Roughness"].default_value = 0.38
    bsdf.inputs["Coat Weight"].default_value = 0.25
    bsdf.inputs["Coat Roughness"].default_value = 0.3
    bump = nt.n("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.5 * SC
    nt.link(nt.math("ADD", nt.math("MULTIPLY", n1, 1.0), nt.math("MULTIPLY", n2, 0.04)), bump.inputs["Height"])
    nt.link(bump.outputs[0], bsdf.inputs["Normal"])
    out = nt.n("ShaderNodeOutputMaterial")
    nt.link(bsdf.outputs[0], out.inputs["Surface"])
    return mat


def area(name, loc, target, size, power, color=(1, 1, 1)):
    li = bpy.data.lights.new(name, "AREA")
    li.shape = "DISK"
    li.size = size * SC
    li.energy = power
    li.color = color
    ob = bpy.data.objects.new(name, li)
    ob.location = V(loc)
    d = V(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(ob)
    return ob


class Scene:
    def __init__(self, geo):
        self.geo = geo
        self.lm = json.load(open(os.path.join(geo, "landmarks.json")))
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = self.sc = bpy.context.scene
        sc.render.engine = "CYCLES"
        cy = sc.cycles
        cy.device = "CPU"
        cy.use_adaptive_sampling = True
        cy.adaptive_threshold = 0.03
        cy.use_denoising = True
        cy.denoiser = "OPENIMAGEDENOISE"
        cy.max_bounces = 8
        cy.transparent_max_bounces = 24
        cy.glossy_bounces = 3
        cy.diffuse_bounces = 2
        cy.caustics_reflective = cy.caustics_refractive = False
        sc.render.threads_mode = "AUTO"
        sc.render.use_persistent_data = True
        sc.render.film_transparent = False
        sc.view_settings.view_transform = "AgX"
        try:
            sc.view_settings.look = "AgX - Medium High Contrast"
        except TypeError:
            pass
        sc.render.image_settings.file_format = "PNG"
        world = bpy.data.worlds.new("w")
        world.use_nodes = True
        world.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)
        sc.world = world

        am, lmat = airway_material(), lung_material()
        self.airway = load_mesh("airway", os.path.join(geo, "airway.npz"), ["cart", "w", "inner", "ring"])
        self.cut = load_mesh("airway_cut", os.path.join(geo, "airway_cut.npz"), ["cart", "w", "inner", "cutface", "ring"])
        self.lungs = [load_mesh(n, os.path.join(geo, n + ".npz"), ["lobe"]) for n in ("lung_r", "lung_l")]
        for ob in (self.airway, self.cut):
            ob.data.materials.append(am)
        for ob in self.lungs:
            ob.data.materials.append(lmat)
        self.am, self.lmat = am, lmat

        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5, radius=1.0)
        pea = self.pea = bpy.context.object
        pea.name = "pea"
        r = 3.9 * SC
        pea.scale = (r, r * 0.97, r * 0.94)
        bpy.ops.object.shade_smooth()
        pea.data.materials.append(pea_material())

        # світло: м'який ключовий згори-зліва, холодні контрові, слабке заповнення
        c = (0, 0, -30)
        self.lights = [
            area("key", (-300, -400, 280), c, 420, 400),
            area("fill", (360, -360, -60), c, 380, 60, (0.86, 0.92, 1.0)),
            area("rim_l", (-360, 330, 150), c, 200, 700, (0.78, 0.88, 1.0)),
            area("rim_r", (360, 360, 60), c, 200, 600, (0.78, 0.88, 1.0)),
            area("top", (0, 40, 460), c, 220, 160),
        ]
        cam = bpy.data.cameras.new("cam")
        self.cam = bpy.data.objects.new("cam", cam)
        sc.collection.objects.link(self.cam)
        sc.camera = self.cam
        cam.clip_start, cam.clip_end = 0.05, 100
        cam.sensor_width = 36

    # ---- стан сцени
    def set_state(self, st):
        """st: focus_<група> 0..1, focus_lungs, ghost, cut (0/1), pea (None або [x,y,z] мм), pea_rot."""
        for g in GROUPS:
            self.am.node_tree.nodes["focus_" + g].outputs[0].default_value = st.get("focus_" + g, 1.0)
        self.lmat.node_tree.nodes["focus_lungs"].outputs[0].default_value = st.get("focus_lungs", 1.0)
        ghost = st.get("ghost", 0.0)
        self.lmat.node_tree.nodes["ghost"].outputs[0].default_value = ghost
        hide_l = st.get("lungs", True) is False
        for ob in self.lungs:
            ob.hide_render = hide_l
            ob.visible_shadow = ghost < 0.5
        cut = bool(st.get("cut", 0))
        self.cut.hide_render = not cut
        self.airway.hide_render = cut or st.get("airway", True) is False
        if st.get("airway", True) is False:
            self.cut.hide_render = True
        pea = st.get("pea")
        self.pea.hide_render = pea is None
        if pea is not None:
            self.pea.location = V(pea)
            self.pea.rotation_euler = st.get("pea_rot", (0, 0, 0))

    def set_camera(self, c):
        """c: target (мм), dir (звідки дивимось, одиничний напрям від цілі до камери), dist (мм), lens, shift_x, fstop, focus (мм)."""
        d = Vector(c["dir"]).normalized()
        self.cam.location = V(c["target"]) + d * c["dist"] * SC
        self.cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        cd = self.cam.data
        cd.lens = c.get("lens", 85)
        cd.shift_x = c.get("shift_x", 0.0)
        cd.shift_y = c.get("shift_y", 0.0)
        cd.dof.use_dof = "fstop" in c
        if "fstop" in c:
            cd.dof.aperture_fstop = c["fstop"]
            cd.dof.focus_distance = c.get("focus", c["dist"]) * SC

    def project(self, p):
        """Точка (мм) → координати кадру 0..1 (x праворуч, y донизу)."""
        from bpy_extras.object_utils import world_to_camera_view
        bpy.context.view_layer.update()
        co = world_to_camera_view(self.sc, self.cam, V(p))
        return [co.x, 1 - co.y]

    def render(self, path, res=(1920, 1080), samples=96, threshold=0.03):
        r = self.sc.render
        r.resolution_x, r.resolution_y = res
        r.resolution_percentage = 100
        self.sc.cycles.samples = samples
        self.sc.cycles.adaptive_threshold = threshold
        r.filepath = path
        bpy.ops.render.render(write_still=True)


def build(geo):
    return Scene(geo)
