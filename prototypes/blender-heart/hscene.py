"""Сцена серця (Cycles): матеріали, ключі форми для скорочення, хвиля збудження."""
import json
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "blender-bronchi"))
import scene as base  # noqa: E402  спільні помічники: NT, load_mesh, area, SC

SC = base.SC
NT = base.NT


def sstep(nt, x, a, b):
    n = nt.n("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
    for sock, v in ((n.inputs[0], x), (n.inputs[1], a), (n.inputs[2], b)):
        if isinstance(v, (int, float)):
            sock.default_value = v
        else:
            nt.link(v, sock)
    return n.outputs[0]


def pulse(nt, act, ph, rise, dur, fall):
    """1, поки тканина збуджена: від act до act+dur (частки циклу)."""
    d = nt.math("SUBTRACT", ph, act)
    up = sstep(nt, d, 0.0, rise)
    down = nt.math("SUBTRACT", 1.0, sstep(nt, d, dur, dur + fall))
    valid = nt.math("GREATER_THAN", act, -0.5)
    return nt.math("MULTIPLY", nt.math("MULTIPLY", up, down), valid)


def add_keys(ob, d):
    ob.shape_key_add(name="Basis")
    for name in ("v", "a"):
        k = ob.shape_key_add(name=name)
        co = np.empty(len(ob.data.vertices) * 3, np.float32)
        ob.data.vertices.foreach_get("co", co)
        k.data.foreach_set("co", co + (d["d" + name] * SC).ravel())


def heart_material():
    mat = bpy.data.materials.new("heart")
    mat.use_nodes = True
    nt = NT(mat)
    pos = base.coords(nt)
    w = [nt.attr(f"w{i}") for i in range(5)]
    fat, act, inner = nt.attr("fat"), nt.attr("act"), nt.attr("inner")
    n1 = nt.noise(9, 5, 0.6, pos, 0.6)
    n2 = nt.noise(70, 4, 0.6, pos)
    # волокнистий малюнок міокарда
    wave = nt.n("ShaderNodeTexWave", wave_type="BANDS", bands_direction="DIAGONAL")
    wave.inputs["Scale"].default_value = 26
    wave.inputs["Distortion"].default_value = 5.0
    wave.inputs["Detail"].default_value = 3
    nt.link(pos, wave.inputs["Vector"])
    fib = wave.outputs["Fac"]
    vent = nt.ramp(nt.math("ADD", nt.math("MULTIPLY", n1, 0.88), nt.math("MULTIPLY", fib, 0.12)),
                   [(0.25, (0.23, 0.030, 0.028)), (0.75, (0.47, 0.085, 0.07))])
    atria = nt.ramp(n1, [(0.3, (0.30, 0.055, 0.06)), (0.75, (0.52, 0.13, 0.12))])
    aorta = nt.ramp(n1, [(0.3, (0.70, 0.36, 0.30)), (0.75, (0.86, 0.58, 0.48))])
    pulm = nt.ramp(n1, [(0.3, (0.42, 0.44, 0.60)), (0.75, (0.62, 0.64, 0.78))])
    veins = nt.ramp(n1, [(0.3, (0.16, 0.17, 0.36)), (0.75, (0.30, 0.31, 0.52))])
    col = vent
    acc = w[0]
    for wi, ci in zip(w[1:], (atria, aorta, pulm, veins)):
        acc = nt.math("ADD", acc, wi)
        col = nt.mix(nt.math("DIVIDE", wi, nt.math("MAXIMUM", acc, 1e-4)), col, ci)
    # дрібні судини під епікардом
    warp = nt.n("ShaderNodeMixRGB", blend_type="ADD")
    warp.inputs[0].default_value = 0.05
    nt.link(pos, warp.inputs[1])
    wn = nt.n("ShaderNodeTexNoise")
    wn.inputs["Scale"].default_value = 14
    nt.link(pos, wn.inputs["Vector"])
    nt.link(wn.outputs["Color"], warp.inputs[2])
    ve = nt.ramp(nt.voronoi_edge(22, warp.outputs[0]), [(0.0, (1, 1, 1)), (0.03, (0, 0, 0))])
    vmask = nt.math("MULTIPLY", ve, nt.ramp(nt.noise(5, 2, 0.5, pos), [(0.42, (0, 0, 0)), (0.62, (1, 1, 1))]))
    vmask = nt.math("MULTIPLY", vmask, nt.math("MINIMUM", nt.math("ADD", w[0], w[1]), 1.0))
    col = nt.mix(nt.math("MULTIPLY", vmask, 0.6), col, (0.20, 0.015, 0.03))
    # епікардіальний жир уздовж борозен
    fatn = nt.ramp(nt.math("ADD", fat, nt.math("MULTIPLY", nt.math("SUBTRACT", n1, 0.5), 0.9)), [(0.38, (0, 0, 0)), (0.62, (1, 1, 1))])
    lob = nt.ramp(nt.voronoi_edge(38, warp.outputs[0]), [(0.0, (0.70, 0.50, 0.20)), (0.12, (0.93, 0.78, 0.42))])
    col = nt.mix(nt.math("MULTIPLY", fatn, 0.93), col, lob)
    col = nt.mix(inner, col, (0.35, 0.05, 0.05))
    focus = nt.val("focus", 1.0)
    col = nt.grey(col, focus, dim=0.55)

    bsdf = nt.n("ShaderNodeBsdfPrincipled")
    nt.link(col, bsdf.inputs["Base Color"])
    nt.link(nt.math("MULTIPLY", focus, 0.9), bsdf.inputs["Subsurface Weight"])
    bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.25, 0.15)
    bsdf.subsurface_method = "BURLEY"
    bsdf.inputs["Subsurface Scale"].default_value = 1.6 * SC
    nt.link(nt.math("ADD", 0.22, nt.math("MULTIPLY", n2, 0.2)), bsdf.inputs["Roughness"])
    bsdf.inputs["Coat Weight"].default_value = 0.6
    bsdf.inputs["Coat Roughness"].default_value = 0.1
    bump = nt.n("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.4
    bump.inputs["Distance"].default_value = 0.8 * SC
    h = nt.math("ADD", nt.math("MULTIPLY", n2, 0.35), nt.math("MULTIPLY", fib, nt.math("MULTIPLY", w[0], 0.12)))
    h = nt.math("ADD", h, nt.math("MULTIPLY", fatn, nt.math("MULTIPLY", nt.voronoi_edge(38, warp.outputs[0]), 3.0)))
    h = nt.math("ADD", h, nt.math("MULTIPLY", vmask, 0.15))
    nt.link(h, bump.inputs["Height"])
    nt.link(bump.outputs[0], bsdf.inputs["Normal"])

    # «прозорий» стан із хвилею збудження
    isv = nt.math("GREATER_THAN", w[0], w[1])
    ph = nt.math("ADD", nt.math("MULTIPLY", isv, nt.val("phase_v", 0.0)),
                 nt.math("MULTIPLY", nt.math("SUBTRACT", 1.0, isv), nt.val("phase_a", 0.0)))
    dur = nt.math("ADD", 0.12, nt.math("MULTIPLY", isv, 0.20))
    d = nt.math("SUBTRACT", ph, act)
    active = nt.math("MULTIPLY", nt.math("MULTIPLY", sstep(nt, d, 0.0, 0.03), nt.math("SUBTRACT", 1.0, sstep(nt, nt.math("SUBTRACT", d, dur), 0.0, 0.09))),
                     nt.math("GREATER_THAN", act, -0.5))
    # фібриляція: хаотичні осередки збудження в передсердях
    n4 = nt.n("ShaderNodeTexNoise", noise_dimensions="4D")
    n4.inputs["Scale"].default_value = 13
    n4.inputs["Detail"].default_value = 1.5
    nt.link(pos, n4.inputs["Vector"])
    nt.link(nt.val("afw", 0.0), n4.inputs["W"])
    chaos = nt.math("MULTIPLY", sstep(nt, n4.outputs["Fac"], 0.52, 0.6), nt.math("MULTIPLY", nt.val("af", 0.0), nt.math("GREATER_THAN", w[1], 0.5)))
    active = nt.math("MAXIMUM", active, chaos)

    lw = nt.n("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.3
    rim = nt.math("ADD", 0.02, nt.math("MULTIPLY", lw.outputs["Facing"], 0.2))
    rim = nt.math("ADD", rim, nt.math("MULTIPLY", active, 0.34))
    hot = nt.n("ShaderNodeBsdfPrincipled")
    nt.link(nt.mix(active, (0.55, 0.60, 0.68), (1.0, 0.33, 0.08)), hot.inputs["Base Color"])
    hot.inputs["Roughness"].default_value = 0.4
    nt.link(nt.mix(active, (0, 0, 0), (1.0, 0.25, 0.05)), hot.inputs["Emission Color"])
    hot.inputs["Emission Strength"].default_value = 0.8
    tr = nt.n("ShaderNodeBsdfTransparent")
    gm = nt.n("ShaderNodeMixShader")
    nt.link(rim, gm.inputs[0])
    nt.link(tr.outputs[0], gm.inputs[1])
    nt.link(hot.outputs[0], gm.inputs[2])
    fin = nt.n("ShaderNodeMixShader")
    nt.link(nt.val("ghost", 0.0), fin.inputs[0])
    nt.link(bsdf.outputs[0], fin.inputs[1])
    nt.link(gm.outputs[0], fin.inputs[2])
    out = nt.n("ShaderNodeOutputMaterial")
    nt.link(fin.outputs[0], out.inputs["Surface"])
    return mat


def coronary_material():
    mat = bpy.data.materials.new("coronary")
    mat.use_nodes = True
    nt = NT(mat)
    pos = base.coords(nt)
    n1 = nt.noise(40, 3, 0.6, pos)
    col = nt.ramp(n1, [(0.3, (0.55, 0.02, 0.02)), (0.75, (0.80, 0.07, 0.05))])
    bsdf = nt.n("ShaderNodeBsdfPrincipled")
    nt.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Subsurface Weight"].default_value = 0.6
    bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.2, 0.1)
    bsdf.inputs["Subsurface Scale"].default_value = 0.8 * SC
    bsdf.inputs["Roughness"].default_value = 0.28
    bsdf.inputs["Coat Weight"].default_value = 0.6
    bsdf.inputs["Coat Roughness"].default_value = 0.1
    out = nt.n("ShaderNodeOutputMaterial")
    nt.link(bsdf.outputs[0], out.inputs["Surface"])
    return mat


def conduction_material():
    mat = bpy.data.materials.new("conduction")
    mat.use_nodes = True
    nt = NT(mat)
    act, kind = nt.attr("act"), nt.attr("kind")
    issa = nt.math("LESS_THAN", kind, 0.5)
    ph = nt.math("ADD", nt.math("MULTIPLY", issa, nt.val("phase_a", 0.0)),
                 nt.math("MULTIPLY", nt.math("SUBTRACT", 1.0, issa), nt.val("phase_v", 0.0)))
    d = nt.math("SUBTRACT", ph, act)
    hit = nt.math("MULTIPLY", sstep(nt, d, -0.004, 0.006), nt.math("SUBTRACT", 1.0, sstep(nt, d, 0.03, 0.11)))
    col = nt.mix(hit, (0.60, 0.44, 0.07), (1.0, 0.93, 0.45))
    bsdf = nt.n("ShaderNodeBsdfPrincipled")
    nt.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.35
    nt.link(col, bsdf.inputs["Emission Color"])
    nt.link(nt.math("ADD", 0.25, nt.math("MULTIPLY", hit, 2.6)), bsdf.inputs["Emission Strength"])
    out = nt.n("ShaderNodeOutputMaterial")
    nt.link(bsdf.outputs[0], out.inputs["Surface"])
    return mat


def atrial(ph):
    x = (ph - 0.03) / 0.17
    return float(np.sin(np.pi * x) ** 2) if 0 < x < 1 else 0.0


def ventricular(ph):
    def ss(a, b, x):
        t = min(max((x - a) / (b - a), 0.0), 1.0)
        return t * t * (3 - 2 * t)
    return ss(0.27, 0.41, ph) * (1 - ss(0.50, 0.70, ph))


class HeartScene(base.Scene):
    def __init__(self, geo):  # noqa: поза базовим конструктором: інші об'єкти
        self.geo = geo
        self.lm = json.load(open(os.path.join(geo, "landmarks.json")))
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = self.sc = bpy.context.scene
        sc.render.engine = "CYCLES"
        cy = sc.cycles
        cy.device = "CPU"
        cy.use_adaptive_sampling = True
        cy.use_denoising = True
        cy.denoiser = "OPENIMAGEDENOISE"
        cy.max_bounces = 6
        cy.transparent_max_bounces = 12
        cy.glossy_bounces = 3
        cy.diffuse_bounces = 2
        cy.caustics_reflective = cy.caustics_refractive = False
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

        self.hm, self.cm, self.km = heart_material(), coronary_material(), conduction_material()
        self.heart = base.load_mesh("heart", os.path.join(geo, "heart.npz"), ["w", "fat", "act", "inner"])
        self.cor = base.load_mesh("coronary", os.path.join(geo, "coronary.npz"), [])
        self.con = base.load_mesh("conduction", os.path.join(geo, "conduction.npz"), ["act", "kind"])
        for ob, m, n in ((self.heart, self.hm, "heart"), (self.cor, self.cm, "coronary"), (self.con, self.km, "conduction")):
            ob.data.materials.append(m)
            add_keys(ob, np.load(os.path.join(geo, n + ".npz")))
        c = (0, 0, 40)
        self.lights = [
            base.area("key", (-300, -420, 300), c, 420, 290),
            base.area("fill", (360, -360, -40), c, 380, 60, (0.86, 0.92, 1.0)),
            base.area("rim_l", (-360, 330, 170), c, 200, 520, (0.78, 0.88, 1.0)),
            base.area("rim_r", (360, 360, 80), c, 200, 460, (0.78, 0.88, 1.0)),
            base.area("top", (0, 40, 480), c, 220, 120),
        ]
        cam = bpy.data.cameras.new("cam")
        self.cam = bpy.data.objects.new("cam", cam)
        sc.collection.objects.link(self.cam)
        sc.camera = self.cam
        cam.clip_start, cam.clip_end = 0.05, 100

    def set_state(self, st):
        """st: phase_a, phase_v (частка циклу), ghost, focus, af, afw, cor (показати вінцеві), con (показати провідну)."""
        pa, pv = st.get("phase_a", 0.0), st.get("phase_v", 0.0)
        for m in (self.hm, self.km):
            for k, v in (("phase_a", pa), ("phase_v", pv)):
                m.node_tree.nodes[k].outputs[0].default_value = v
        n = self.hm.node_tree.nodes
        n["ghost"].outputs[0].default_value = st.get("ghost", 0.0)
        n["focus"].outputs[0].default_value = st.get("focus", 1.0)
        n["af"].outputs[0].default_value = st.get("af", 0.0)
        n["afw"].outputs[0].default_value = st.get("afw", 0.0)
        ghost = st.get("ghost", 0.0) > 0.5
        self.con.hide_render = not ghost
        self.cor.hide_render = ghost
        self.heart.visible_shadow = not ghost
        va = st.get("beat_a", atrial(pa) if pa >= 0 else 0.0)
        vv = st.get("beat_v", ventricular(pv))
        for ob in (self.heart, self.cor, self.con):
            ob.data.shape_keys.key_blocks["a"].value = va
            ob.data.shape_keys.key_blocks["v"].value = vv

    def render(self, path, res=(1920, 1080), samples=64, threshold=0.03, border=None):
        r = self.sc.render
        r.use_border = border is not None
        r.use_crop_to_border = False
        if border:
            r.border_min_x, r.border_max_x, r.border_min_y, r.border_max_y = border
        super().render(path, res, samples, threshold)


CAM = {"target": [4, 0, 40], "dir": [0.05, -1, 0.06], "dist": 980, "lens": 85, "shift_x": -0.2}
BORDER = (0.44, 0.97, 0.0, 1.0)

if __name__ == "__main__":
    geo, out = sys.argv[1], sys.argv[2]
    st = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
    S = HeartScene(geo)
    S.set_camera(CAM)
    S.set_state(st)
    import time
    t = time.time()
    S.render(out, (1920, 1080), 48, 0.05, border=BORDER)
    print("рендер, с:", round(time.time() - t, 1))
