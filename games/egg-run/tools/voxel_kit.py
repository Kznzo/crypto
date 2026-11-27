"""Egg Run voxel kit: props and zone landmarks as voxel meshes with vertex colours.

Run: blender --background --factory-startup --python voxel_kit.py -- <out_dir> <lihfolk_scripts_dir>
Each piece is a set of voxels; only exposed faces are emitted and shared vertices are
merged, so every piece is one closed mesh (no internal faces). 1 unit = 1 stud,
origin at the bottom centre. Writes EggRunKit.glb, kit_preview.png, kit_report.json.
"""
import colorsys
import json
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
OUT = argv[0]
sys.path.append(argv[1])
import lihfolk_bpy as lf  # noqa: E402

os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
lf.setup_scene()


def C(r, g, b):
    return (r / 255, g / 255, b / 255)


GREEN, GREEN_D, GREEN_L = C(90, 190, 70), C(62, 150, 52), C(130, 215, 95)
TRUNK, TRUNK_D = C(140, 92, 56), C(110, 70, 44)
PINE, SNOW = C(46, 125, 84), C(245, 250, 255)
STONE, STONE_D = C(160, 160, 168), C(125, 125, 135)
HAY, HAY_D = C(236, 196, 92), C(190, 145, 60)
HONEY, HONEY_D = C(255, 190, 40), C(120, 80, 30)
BASALT, EMBER = C(70, 60, 60), C(255, 110, 30)
WHITE, LIGHT = C(255, 255, 255), C(225, 225, 232)
GOLD, GOLD_D = C(255, 205, 60), C(225, 165, 40)
RED, RED_D = C(205, 60, 50), C(160, 45, 40)
ORANGE_NOSE = C(255, 140, 30)
BLACK = C(35, 35, 40)
PINK, YELLOW = C(255, 120, 170), C(255, 220, 60)
RAINBOW = [C(240, 70, 70), C(255, 150, 50), C(255, 220, 60), C(90, 200, 90), C(70, 150, 255), C(150, 90, 230)]

DIRS = [((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]),
        ((-1, 0, 0), [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)]),
        ((0, 1, 0), [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)]),
        ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
        ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]),
        ((0, 0, -1), [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)])]


class Vox:
    """Voxel grid; (x, y, z) integer cells, z up."""

    def __init__(self, name, unit=1.0, seed=0):
        self.name, self.unit = name, unit
        self.cells = {}
        self.rng = random.Random(seed)

    def box(self, x0, y0, z0, x1, y1, z1, color, shade=0.06):
        for x in range(x0, x1):
            for y in range(y0, y1):
                for z in range(z0, z1):
                    self.set(x, y, z, color, shade)

    def set(self, x, y, z, color, shade=0.06):
        h, s, v = colorsys.rgb_to_hsv(*color)
        v = max(0, min(1, v * (1 + self.rng.uniform(-shade, shade))))
        self.cells[(x, y, z)] = colorsys.hsv_to_rgb(h, s, v)

    def clear(self, x0, y0, z0, x1, y1, z1):
        for x in range(x0, x1):
            for y in range(y0, y1):
                for z in range(z0, z1):
                    self.cells.pop((x, y, z), None)

    def build(self):
        xs = [c[0] for c in self.cells]
        ys = [c[1] for c in self.cells]
        zs = [c[2] for c in self.cells]
        cx = (min(xs) + max(xs) + 1) / 2
        cy = (min(ys) + max(ys) + 1) / 2
        z0 = min(zs)
        bm = bmesh.new()
        col = bm.loops.layers.color.new("Col")
        verts = {}

        def vert(p):
            v = verts.get(p)
            if v is None:
                v = bm.verts.new(((p[0] - cx) * self.unit, (p[1] - cy) * self.unit, (p[2] - z0) * self.unit))
                verts[p] = v
            return v

        for (x, y, z), c in self.cells.items():
            for (dx, dy, dz), quad in DIRS:
                if (x + dx, y + dy, z + dz) in self.cells:
                    continue
                f = bm.faces.new([vert((x + a, y + b, z + d)) for a, b, d in quad])
                f.smooth = False
                for loop in f.loops:
                    loop[col] = (c[0], c[1], c[2], 1.0)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(ob)
        try:
            me.color_attributes.active_color = me.color_attributes["Col"]
        except Exception:
            pass
        ob.data.materials.append(MAT)
        return ob


def make_material():
    mat = bpy.data.materials.new("MAT_EggRunVoxel")
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    vc = nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Col"
    nt.links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.85
    return mat


MAT = make_material()
pieces = {}  # name -> (object, class, tintable)


def add(v, cls="small", tint=False):
    pieces[v.name] = (v.build(), cls, tint)


# ---- small props (1-stud voxels) -------------------------------------------------
v = Vox("VBush", 1.0, 1)  # chunky stacked bush like the reference
v.box(0, 0, 0, 7, 4, 3, GREEN)
v.box(1, 0, 3, 5, 4, 5, GREEN_L)
v.box(5, 1, 0, 9, 4, 2, GREEN_D)
add(v)

v = Vox("VBushSmall", 1.0, 2)
v.box(0, 0, 0, 4, 3, 2, GREEN)
v.box(1, 0, 2, 3, 3, 3, GREEN_L)
add(v, "tiny")

v = Vox("VCactus", 1.0, 3)
v.box(0, 0, 0, 1, 1, 8, GREEN_D, 0.03)
v.box(1, 0, 3, 2, 1, 4, GREEN_D, 0.03)
v.box(2, 0, 3, 3, 1, 6, GREEN_D, 0.03)
v.box(-1, 0, 2, 0, 1, 3, GREEN_D, 0.03)
v.box(-2, 0, 2, -1, 1, 5, GREEN_D, 0.03)
add(v, "tiny")

v = Vox("VRock", 1.0, 4)
v.box(0, 0, 0, 4, 3, 2, LIGHT)
v.box(1, 0, 2, 3, 3, 3, LIGHT)
v.box(4, 1, 0, 5, 3, 1, LIGHT)
add(v, "rock", True)

v = Vox("VTree", 1.0, 5)
v.box(0, 0, 0, 2, 2, 6, TRUNK, 0.04)
v.box(-3, -3, 6, 5, 5, 11, GREEN)
v.clear(-3, -3, 10, -2, -2, 11); v.clear(4, -3, 10, 5, -2, 11); v.clear(-3, 4, 10, -2, 5, 11); v.clear(4, 4, 10, 5, 5, 11)
v.box(-1, -1, 11, 3, 3, 13, GREEN_L)
add(v, "tree")

v = Vox("VPalm", 1.0, 6)
for i in range(7):
    x = i // 3
    v.box(x, 0, i * 2, x + 1, 1, i * 2 + 2, TRUNK if i % 2 == 0 else TRUNK_D, 0.02)
    if i in (3, 6):
        v.set(x, 0, i * 2 - 1, TRUNK_D, 0.02)  # bridge the lean so faces touch, not edges
top = (2, 0, 14)
for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
    for k in range(1, 5):
        v.set(top[0] + dx * k, top[1] + dy * k, top[2], GREEN)
    v.set(top[0] + dx * 4, top[1] + dy * 4, top[2] - 1, GREEN_D)  # drooping tip
v.box(1, -1, 14, 4, 2, 15, GREEN_D)
add(v, "tree")

v = Vox("VPine", 1.0, 7)
v.box(0, 0, 0, 1, 1, 3, TRUNK_D, 0.02)
for i, r in enumerate((4, 3, 2, 1)):
    v.box(-r, -r, 3 + i * 3, r + 1, r + 1, 5 + i * 3, PINE)
    v.box(-r, -r, 5 + i * 3, r + 1, r + 1, 6 + i * 3, SNOW if i == 3 else PINE)
add(v, "tree")

v = Vox("VHay", 1.0, 8)
v.box(0, 0, 0, 4, 3, 3, HAY)
v.box(1, 0, 0, 2, 3, 3, HAY_D, 0.02)
v.box(3, 0, 0, 4, 3, 3, HAY_D, 0.02)
add(v, "tiny")

v = Vox("VFlower", 1.0, 9)
v.box(0, 0, 0, 1, 1, 2, GREEN_D, 0.0)
for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
    v.set(dx, dy, 2, PINK, 0.02)
v.set(0, 0, 2, YELLOW, 0.0)
add(v, "tiny")

v = Vox("VIce", 1.0, 10)
v.box(0, 0, 0, 2, 2, 7, LIGHT, 0.03)
v.box(2, 0, 0, 3, 2, 4, LIGHT, 0.03)
v.box(-1, 1, 0, 0, 2, 5, LIGHT, 0.03)
add(v, "tiny", True)

v = Vox("VLavaRock", 1.0, 11)
v.box(0, 0, 0, 5, 4, 2, BASALT)
v.box(1, 1, 2, 4, 3, 3, BASALT)
v.box(2, 1, 3, 3, 2, 4, EMBER, 0.0)
v.box(4, 3, 1, 5, 4, 2, EMBER, 0.0)
add(v, "rock")

v = Vox("VCloud", 1.0, 12)
v.box(0, 0, 0, 10, 4, 2, WHITE, 0.02)
v.box(2, 0, 2, 7, 4, 4, WHITE, 0.02)
v.box(7, 1, 2, 9, 3, 3, WHITE, 0.02)
add(v)

v = Vox("VCrystal", 1.0, 13)
v.box(0, 0, 0, 2, 2, 8, LIGHT, 0.03)
v.box(0, 0, 8, 1, 1, 10, WHITE, 0.0)
v.box(2, 0, 0, 3, 2, 3, LIGHT, 0.03)
v.box(3, 0, 2, 4, 2, 5, LIGHT, 0.03)
v.box(-1, 1, 0, 0, 2, 4, LIGHT, 0.03)
v.box(-2, 1, 3, -1, 2, 6, LIGHT, 0.03)
add(v, "small", True)

v = Vox("VPillar", 1.0, 14)
v.box(-2, -2, 0, 3, 3, 1, WHITE, 0.02)
v.box(-1, -1, 1, 2, 2, 12, GOLD, 0.03)
v.box(-2, -2, 12, 3, 3, 13, WHITE, 0.02)
v.box(0, 0, 13, 1, 1, 15, GOLD_D, 0.0)
add(v)

# ---- zone landmarks (2-stud voxels) -----------------------------------------------
v = Vox("LBarn", 2.0, 20)
v.box(0, 0, 0, 12, 9, 7, RED)
for i in range(5):
    v.box(-1 + i, -1, 7 + i, 13 - i, 10, 8 + i, RED_D, 0.03)
v.box(4, -1, 0, 8, 0, 5, WHITE, 0.0)
v.box(5, -1, 1, 7, 0, 4, TRUNK_D, 0.0)
add(v, "medium")

v = Vox("LBeehive", 2.0, 21)
for i, r in enumerate((6, 7, 7, 6, 5, 3, 1)):
    color = HONEY if i % 2 == 0 else HONEY_D
    v.box(-r, -r, i * 2, r + 1, r + 1, i * 2 + 2, color, 0.04)
v.clear(-1, -8, 1, 2, -6, 3)
add(v, "medium")

v = Vox("LRainbow", 2.0, 22)
R = 14
for k, c in enumerate(RAINBOW):
    rad = R - k
    for a in range(0, 181, 2):
        x = round(rad * math.cos(math.radians(a)))
        z = round(rad * math.sin(math.radians(a)))
        v.set(x, 0, z, c, 0.0)
        v.set(x, 1, z, c, 0.0)
v.box(-16, -1, 0, -10, 3, 2, WHITE, 0.02)
v.box(10, -1, 0, 16, 3, 2, WHITE, 0.02)
add(v, "medium")

v = Vox("LSnowman", 2.0, 23)
v.box(-4, -4, 0, 5, 5, 8, SNOW, 0.03)
v.box(-3, -3, 8, 4, 4, 14, SNOW, 0.03)
v.box(-2, -2, 14, 3, 3, 19, SNOW, 0.03)
v.box(0, -4, 16, 1, -2, 17, ORANGE_NOSE, 0.0)
v.set(-1, -3, 18, BLACK, 0.0)
v.set(1, -3, 18, BLACK, 0.0)
v.box(-3, -3, 19, 4, 4, 20, BLACK, 0.0)
v.box(-2, -2, 20, 3, 3, 23, BLACK, 0.0)
add(v, "medium")

v = Vox("LVolcano", 2.6, 24)
for i, r in enumerate((11, 9, 7, 5)):
    v.box(-r, -r, i * 3, r + 1, r + 1, i * 3 + 3, BASALT, 0.08)
v.clear(-2, -2, 10, 3, 3, 12)
v.box(-2, -2, 10, 3, 3, 11, EMBER, 0.0)
for i in range(4):
    v.box(3 + i * 2, -1, 10 - i * 3, 4 + i * 2, 1, 11 - i * 3, EMBER, 0.0)
add(v, "medium")

v = Vox("LPyramid", 2.0, 25)
for i, r in enumerate(range(12, -1, -2)):
    v.box(-r, -r, i * 2, r + 1, r + 1, i * 2 + 2, GOLD if i % 2 == 0 else GOLD_D, 0.04)
add(v, "medium")

# ---- gate every piece ---------------------------------------------------------------
report = {}
for name, (ob, cls, tint) in pieces.items():
    passed, fails, r = lf.gate(ob, cls, surface_checks=True)
    report[name] = {"class": cls, "tris": r["tris"], "dims": [round(d, 2) for d in ob.dimensions],
                    "passed": passed, "fails": fails, "tintable": tint}

# ---- layout + preview render (Cycles CPU) -----------------------------------------
names = list(pieces)
small = [n for n in names if not n.startswith("L")]
big = [n for n in names if n.startswith("L")]
for i, n in enumerate(small):
    pieces[n][0].location = ((i % 7) * 16 - 48, (i // 7) * 16 - 40, 0)
for i, n in enumerate(big):
    pieces[n][0].location = ((i % 3) * 48 - 48, 20 + (i // 3) * 50, 0)
for n in ("VCloud",):
    pieces[n][0].location.z = 4

s = bpy.context.scene
s.render.engine = "CYCLES"
s.cycles.device = "CPU"
s.cycles.samples = 24
s.cycles.use_denoising = True
s.render.resolution_x, s.render.resolution_y = 1600, 1000
world = bpy.data.worlds.new("W")
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (0.45, 0.7, 1.0, 1)
bg.inputs["Strength"].default_value = 1.0
s.world = world
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
sun.data.energy = 3.5
sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(35))
s.collection.objects.link(sun)
gme = bpy.data.meshes.new("Ground")
gbm = bmesh.new()
bmesh.ops.create_grid(gbm, x_segments=1, y_segments=1, size=200)
gbm.to_mesh(gme)
gbm.free()
ground = bpy.data.objects.new("Ground", gme)
s.collection.objects.link(ground)
gmat = bpy.data.materials.new("GroundMat")
next(n for n in gmat.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.3, 0.62, 0.22, 1)
ground.data.materials.append(gmat)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
cam.data.lens = 30
s.collection.objects.link(cam)
s.camera = cam
target = Vector((0, 15, 10))
cam.location = target + Vector((30, -150, 95))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
s.render.filepath = os.path.join(OUT, "kit_preview.png")
bpy.ops.render.render(write_still=True)
for helper in (cam, sun, ground):
    bpy.data.objects.remove(helper, do_unlink=True)

bpy.ops.object.select_all(action="DESELECT")
for n in names:
    pieces[n][0].select_set(True)
bpy.context.view_layer.objects.active = pieces[names[0]][0]
# Keep exactly one colour attribute ("Col") so it exports as COLOR_0 (Roblox reads only COLOR_0).
attr_log = {}
for n in names:
    me = pieces[n][0].data
    attr_log[n] = [a.name for a in me.color_attributes]
    for a in [a for a in me.color_attributes if a.name != "Col"]:
        me.color_attributes.remove(a)
    me.color_attributes.active_color = me.color_attributes["Col"]
    me.color_attributes.render_color_index = me.color_attributes.find("Col")
print("COLOR_ATTRS_BEFORE", attr_log.get("VBush"))
glb = os.path.join(OUT, "EggRunKit.glb")
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=True, export_apply=True,
                          export_yup=True, export_normals=True, export_vertex_color="ACTIVE",
                          export_draco_mesh_compression_enable=False)
report["_export"] = {"glb": glb, "bytes": os.path.getsize(glb)}
with open(os.path.join(OUT, "kit_report.json"), "w") as f:
    json.dump(report, f, indent=1)
print("KIT_DONE")
