"""Мікрорівень: артеріола в розтині з еритроцитами та пласт кардіоміоцитів із хвилею збудження.

python3 micro.py vessel|cells <тека виводу> [test]
"""
import math
import os
import sys

import bpy
import bmesh  # noqa: E402  (доступний лише після bpy)
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "blender-bronchi"))
import scene as base  # noqa: E402

NT = base.NT
VES_N, CELL_PH = 50, np.concatenate([np.linspace(0, 0.2, 14, endpoint=False), np.linspace(0.2, 1.0, 16, endpoint=False)])


class Bare(base.Scene):
    def __init__(self):  # noqa
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = self.sc = bpy.context.scene
        sc.render.engine = "CYCLES"
        cy = sc.cycles
        cy.device = "CPU"
        cy.use_adaptive_sampling = True
        cy.use_denoising = True
        cy.denoiser = "OPENIMAGEDENOISE"
        cy.max_bounces = 6
        cy.diffuse_bounces = 2
        cy.glossy_bounces = 3
        cy.caustics_reflective = cy.caustics_refractive = False
        sc.view_settings.view_transform = "AgX"
        try:
            sc.view_settings.look = "AgX - Medium High Contrast"
        except TypeError:
            pass
        sc.render.image_settings.file_format = "PNG"
        w = bpy.data.worlds.new("w")
        w.use_nodes = True
        w.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)
        sc.world = w
        cam = bpy.data.cameras.new("cam")
        self.cam = bpy.data.objects.new("cam", cam)
        sc.collection.objects.link(self.cam)
        sc.camera = self.cam
        cam.clip_start, cam.clip_end = 0.01, 1000

    def render(self, path, res=(1920, 1080), samples=48, threshold=0.05, border=None):
        r = self.sc.render
        r.use_border = border is not None
        r.use_crop_to_border = False
        if border:
            r.border_min_x, r.border_max_x, r.border_min_y, r.border_max_y = border
        super().render(path, res, samples, threshold)


def mesh_obj(name, V, F, attrs=None, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in V], [], [tuple(f) for f in F])
    for p in me.polygons:
        p.use_smooth = smooth
    for k, a in (attrs or {}).items():
        at = me.attributes.new(k, "FLOAT", "POINT")
        at.data.foreach_set("value", np.asarray(a, np.float32))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


# ------------------------------------------------------------------ судина
R_IN, WALL, LEN = 3.3, 0.95, 44.0
TH0, TH1 = math.radians(128), math.radians(322)     # збережений сектор стінки; отвір звернений до камери


def vessel_wall():
    nx, nt_, nr = 120, 72, 8
    xs = np.linspace(-LEN / 2, LEN / 2, nx)
    th = np.linspace(TH0, TH1, nt_)
    rr = np.linspace(R_IN, R_IN + WALL, nr)
    V, layer, cut = [], [], []
    idx = {}

    def vid(i, j, k):
        key = (i, j, k)
        if key not in idx:
            wob = 0.05 * math.sin(xs[i] * 1.3 + th[j] * 3) + 0.04 * math.sin(xs[i] * 0.37)
            r = rr[k] + wob
            idx[key] = len(V)
            V.append((xs[i], -r * math.cos(th[j]), r * math.sin(th[j])))   # камера з боку −y
            layer.append(k / (nr - 1))
            cut.append(1.0 if (j in (0, nt_ - 1) and 0 < k < nr - 1) else 0.0)
        return idx[key]
    F = []
    for i in range(nx - 1):
        for j in range(nt_ - 1):
            F.append((vid(i, j, 0), vid(i + 1, j, 0), vid(i + 1, j + 1, 0), vid(i, j + 1, 0)))
            F.append((vid(i, j, nr - 1), vid(i, j + 1, nr - 1), vid(i + 1, j + 1, nr - 1), vid(i + 1, j, nr - 1)))
        for j in (0, nt_ - 1):
            for k in range(nr - 1):
                q = (vid(i, j, k), vid(i, j, k + 1), vid(i + 1, j, k + 1), vid(i + 1, j, k))
                F.append(q if j == 0 else q[::-1])
    ob = mesh_obj("wall", V, F, {"layer": layer, "cut": cut})
    mat = bpy.data.materials.new("wall")
    mat.use_nodes = True
    nt = NT(mat)
    pos = base.coords(nt)
    layer_a, cut_a = nt.attr("layer"), nt.attr("cut")
    # ендотелій: видовжені вздовж течії клітини
    mp = nt.n("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.55, 2.2, 2.2)
    nt.link(pos, mp.inputs["Vector"])
    ve = nt.voronoi_edge(1.0, mp.outputs[0])
    endo = nt.mix(nt.ramp(ve, [(0.0, (1, 1, 1)), (0.06, (0, 0, 0))]), (0.80, 0.42, 0.38), (0.60, 0.22, 0.22))
    n1 = nt.noise(1.2, 4, 0.6, pos)
    endo = nt.mix(nt.math("MULTIPLY", n1, 0.3), endo, (0.92, 0.60, 0.52))
    # зріз: інтима — медія (гладкі м'язи, колові волокна) — адвентиція
    wave = nt.n("ShaderNodeTexWave", wave_type="RINGS", rings_direction="X")
    wave.inputs["Scale"].default_value = 5.0
    wave.inputs["Distortion"].default_value = 2.0
    nt.link(pos, wave.inputs["Vector"])
    media = nt.mix(wave.outputs["Fac"], (0.50, 0.10, 0.10), (0.72, 0.24, 0.20))
    lay = nt.ramp(layer_a, [(0.0, (0.95, 0.80, 0.72)), (0.14, (0.95, 0.80, 0.72)), (0.2, (0, 0, 0)), (0.7, (0, 0, 0)), (0.78, (0.90, 0.78, 0.60)), (1.0, (0.86, 0.72, 0.52))])
    ismedia = nt.math("MULTIPLY", nt.math("GREATER_THAN", layer_a, 0.17), nt.math("LESS_THAN", layer_a, 0.74))
    cutc = nt.mix(ismedia, lay, media)
    outer = nt.mix(nt.noise(2.5, 4, 0.6, pos), (0.72, 0.52, 0.36), (0.90, 0.76, 0.58))
    col = nt.mix(nt.math("GREATER_THAN", layer_a, 0.5), endo, outer)
    col = nt.mix(cut_a, col, cutc)
    bsdf = nt.n("ShaderNodeBsdfPrincipled")
    nt.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Subsurface Weight"].default_value = 0.8
    bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.3, 0.2)
    bsdf.inputs["Subsurface Scale"].default_value = 0.25
    bsdf.inputs["Roughness"].default_value = 0.3
    bsdf.inputs["Coat Weight"].default_value = 0.7
    bsdf.inputs["Coat Roughness"].default_value = 0.1
    bump = nt.n("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.08
    nt.link(nt.math("ADD", ve, nt.math("MULTIPLY", n1, 0.4)), bump.inputs["Height"])
    nt.link(bump.outputs[0], bsdf.inputs["Normal"])
    out = nt.n("ShaderNodeOutputMaterial")
    nt.link(bsdf.outputs[0], out.inputs["Surface"])
    ob.data.materials.append(mat)
    return ob


def rbc_mesh():
    """Двоввігнутий диск за формулою Еванса–Фунга; діаметр 1 одиниця ≈ 7,8 мкм."""
    R = 0.5
    nr, na = 22, 48
    rho = np.sin(np.linspace(0, np.pi / 2, nr))
    z = 0.5 * R * np.sqrt(np.clip(1 - rho ** 2, 0, 1)) * (0.207161 + 2.002558 * rho ** 2 - 1.122762 * rho ** 4)
    V, F = [], []
    for sgn in (1, -1):
        off = len(V)
        for i in range(nr):
            if sgn < 0 and i == nr - 1:
                continue
            for a in range(na):
                t = 2 * np.pi * a / na
                V.append((R * rho[i] * np.cos(t), R * rho[i] * np.sin(t), sgn * z[i]))
        rows = nr if sgn > 0 else nr - 1
        for i in range(rows - 1):
            for a in range(na):
                q = (off + i * na + a, off + i * na + (a + 1) % na, off + (i + 1) * na + (a + 1) % na, off + (i + 1) * na + a)
                F.append(q if sgn > 0 else q[::-1])
        if sgn < 0:  # зшити нижню половину з обідком верхньої
            for a in range(na):
                q = (off + (rows - 1) * na + a, off + (rows - 1) * na + (a + 1) % na, (nr - 1) * na + (a + 1) % na, (nr - 1) * na + a)
                F.append(q[::-1])
    return V, F


def rbc_material():
    mat = bpy.data.materials.new("rbc")
    mat.use_nodes = True
    nt = NT(mat)
    info = nt.n("ShaderNodeObjectInfo")
    col = nt.ramp(info.outputs["Random"], [(0.0, (0.52, 0.015, 0.02)), (1.0, (0.74, 0.05, 0.04))])
    bsdf = nt.n("ShaderNodeBsdfPrincipled")
    nt.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Subsurface Weight"].default_value = 1.0
    bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.12, 0.06)
    bsdf.inputs["Subsurface Scale"].default_value = 0.22
    bsdf.subsurface_method = "BURLEY"
    bsdf.inputs["Roughness"].default_value = 0.32
    bsdf.inputs["Coat Weight"].default_value = 0.3
    out = nt.n("ShaderNodeOutputMaterial")
    nt.link(bsdf.outputs[0], out.inputs["Surface"])
    return mat


def vessel(out, test):
    S = Bare()
    vessel_wall()
    V, F = rbc_mesh()
    proto = mesh_obj("rbc", V, F)
    proto.data.materials.append(rbc_material())
    rng = np.random.default_rng(5)
    cells, pts = [], []
    while len(cells) < 230:
        x = rng.uniform(-LEN / 2, LEN / 2)
        r = (R_IN - 0.62) * math.sqrt(rng.uniform(0, 1))
        a = rng.uniform(0, 2 * math.pi)
        p = np.array([x, r * math.cos(a), r * math.sin(a)])
        if any(np.linalg.norm(p - q) < 0.86 for q in pts):
            continue
        pts.append(p)
        ob = proto if not cells else proto.copy()
        if cells:
            bpy.context.scene.collection.objects.link(ob)
        ob.rotation_mode = "AXIS_ANGLE"
        ax = rng.normal(size=3)
        cells.append((ob, p, 2 if r < R_IN * 0.55 else 1, ax / np.linalg.norm(ax), rng.uniform(0, 6.28), int(rng.choice([-1, 1]))))
    base.area("key", (-1500, -2200, 2600), (0, 0, 0), 1800, 5200)
    base.area("fill", (1800, -2400, 300), (0, 0, 0), 2400, 1300, (0.86, 0.92, 1.0))
    base.area("rim", (600, 2600, 1800), (0, 0, 0), 1600, 5200, (0.8, 0.9, 1.0))
    S.set_camera({"target": [150, 0, -20], "dir": [-0.2, -1, 0.75], "dist": 5200, "lens": 70, "shift_x": -0.17, "fstop": 4.0, "focus": 5200})
    os.makedirs(out, exist_ok=True)
    for f in ([0] if test else range(VES_N)):
        p = os.path.join(out, f"{f:03d}.png")
        if os.path.exists(p) and not test:
            continue
        for ob, p0, k, ax, a0, spin in cells:
            x = (p0[0] + LEN / 2 + k * LEN * f / VES_N) % LEN - LEN / 2
            ob.location = (x, p0[1], p0[2])
            ang = a0 + spin * 2 * math.pi * f / VES_N
            ob.rotation_axis_angle = (ang, *ax)
        S.render(p, (960, 540) if test else (1920, 1080), 48, 0.05, border=None if test else (0.36, 1.0, 0.08, 0.92))
    print("vessel", flush=True)


# ------------------------------------------------------------------ кардіоміоцити
def cells(out, test):
    S = Bare()
    bm = bmesh.new()
    rng = np.random.default_rng(11)
    Lc, Wc, Hc = 11.0, 1.9, 1.7
    for row in range(-5, 6):
        x = -34 + rng.uniform(0, Lc)
        while x < 34:
            ln = Lc * rng.uniform(0.75, 1.2)
            geom = bmesh.ops.create_cube(bm, size=1.0)
            cx, cy = x + ln / 2, row * (Wc + 0.1)
            for v in geom["verts"]:
                v.co.x = v.co.x * (ln - 0.1) + cx
                v.co.y = v.co.y * Wc + cy
                v.co.z = v.co.z * Hc + rng.uniform(-0.08, 0.08) * 0
            x += ln
    me = bpy.data.meshes.new("cells")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("cells", me)
    bpy.context.scene.collection.objects.link(ob)
    bev = ob.modifiers.new("b", "BEVEL")
    bev.width, bev.segments = 0.78, 8
    for p in me.polygons:
        p.use_smooth = True
    mat = bpy.data.materials.new("myo")
    mat.use_nodes = True
    nt = NT(mat)
    pos = base.coords(nt)
    sep = nt.n("ShaderNodeSeparateXYZ")
    nt.link(pos, sep.inputs[0])
    geo = nt.n("ShaderNodeNewGeometry")
    rnd = geo.outputs["Random Per Island"]
    warp = nt.math("MULTIPLY", nt.noise(0.5, 3, 0.5, pos), 0.5)
    band = nt.math("SINE", nt.math("MULTIPLY", nt.math("ADD", sep.outputs["X"], warp), 2 * math.pi / 0.24))
    stri = nt.ramp(nt.math("ADD", nt.math("MULTIPLY", band, 0.5), 0.5), [(0.25, (0.42, 0.07, 0.09)), (0.75, (0.78, 0.30, 0.28))])
    tint = nt.n("ShaderNodeHueSaturation")
    nt.link(stri, tint.inputs["Color"])
    nt.link(nt.math("ADD", 0.82, nt.math("MULTIPLY", rnd, 0.3)), tint.inputs["Value"])
    col = tint.outputs[0]
    # хвиля збудження біжить уздовж волокон від клітини до клітини
    ph = nt.val("phase", 0.0)
    act = nt.math("ADD", 0.03, nt.math("MULTIPLY", nt.math("ADD", sep.outputs["X"], 30.0), 0.14 / 60.0))
    d = nt.math("SUBTRACT", ph, act)
    up = nt.n("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
    nt.link(d, up.inputs[0])
    up.inputs[1].default_value, up.inputs[2].default_value = 0.0, 0.02
    dn = nt.n("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
    nt.link(d, dn.inputs[0])
    dn.inputs[1].default_value, dn.inputs[2].default_value = 0.36, 0.5
    active = nt.math("MULTIPLY", up.outputs[0], nt.math("SUBTRACT", 1.0, dn.outputs[0]))
    hot = nt.mix(nt.math("ADD", nt.math("MULTIPLY", band, 0.25), 0.5), (0.95, 0.33, 0.04), (1.0, 0.55, 0.14))
    col = nt.mix(nt.math("MULTIPLY", active, 0.55), col, hot)
    bsdf = nt.n("ShaderNodeBsdfPrincipled")
    nt.link(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Subsurface Weight"].default_value = 0.8
    bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.3, 0.2)
    bsdf.inputs["Subsurface Scale"].default_value = 0.3
    bsdf.subsurface_method = "BURLEY"
    bsdf.inputs["Roughness"].default_value = 0.35
    bsdf.inputs["Coat Weight"].default_value = 0.5
    bsdf.inputs["Coat Roughness"].default_value = 0.15
    nt.link(nt.mix(active, (0, 0, 0), (1.0, 0.3, 0.05)), bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 0.2
    bump = nt.n("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    bump.inputs["Distance"].default_value = 0.03
    nt.link(band, bump.inputs["Height"])
    nt.link(bump.outputs[0], bsdf.inputs["Normal"])
    o = nt.n("ShaderNodeOutputMaterial")
    nt.link(bsdf.outputs[0], o.inputs["Surface"])
    me.materials.append(mat)
    base.area("key", (-1800, -2200, 3200), (0, 0, 0), 2200, 9000)
    base.area("fill", (2400, -2000, 800), (0, 0, 0), 2600, 1800, (0.86, 0.92, 1.0))
    base.area("rim", (0, 3000, 1500), (0, 0, 0), 1800, 6000, (0.8, 0.9, 1.0))
    S.set_camera({"target": [300, 0, 0], "dir": [-0.3, -1, 0.7], "dist": 4600, "lens": 70, "shift_x": -0.17, "fstop": 3.2, "focus": 4600})
    os.makedirs(out, exist_ok=True)

    def ss(a, b, x):
        t = min(max((x - a) / (b - a), 0.0), 1.0)
        return t * t * (3 - 2 * t)
    for i in ([8] if test else range(len(CELL_PH))):
        p = os.path.join(out, f"{i:03d}.png")
        if os.path.exists(p) and not test:
            continue
        phv = float(CELL_PH[i])
        mat.node_tree.nodes["phase"].outputs[0].default_value = phv
        ob.scale = (1 - 0.07 * ss(0.12, 0.3, phv) * (1 - ss(0.42, 0.62, phv)), 1, 1)
        S.render(p, (960, 540) if test else (1920, 1080), 48, 0.05, border=None if test else (0.36, 1.0, 0.05, 0.95))
    print("cells", flush=True)


if __name__ == "__main__":
    {"vessel": vessel, "cells": cells}[sys.argv[1]](sys.argv[2], len(sys.argv) > 3)
