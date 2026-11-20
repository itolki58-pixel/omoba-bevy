#!/usr/bin/env python3
"""Read-only GLB inspection and neutral studio preview for the Zaragat source."""
import bpy, json, os, sys, glob
from mathutils import Vector

# Ubuntu Blender uses its bundled Python; expose matching system site-packages (numpy).
for candidate in glob.glob("/usr/lib/python3/dist-packages"):
    if candidate not in sys.path:
        sys.path.append(candidate)

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(args) != 2:
    raise SystemExit("usage: blender --background --python inspect_avatar_glb.py -- source.glb output_dir")
source, out_dir = args
os.makedirs(out_dir, exist_ok=True)
if not os.path.isfile(source):
    raise SystemExit("Source GLB not found: " + source)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(source))
scene = bpy.context.scene
meshes = [o for o in scene.objects if o.type == "MESH"]
armatures = [o for o in scene.objects if o.type == "ARMATURE"]
actions = list(bpy.data.actions)
materials = list(bpy.data.materials)
images = list(bpy.data.images)

points, mesh_rows = [], []
for obj in meshes:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        points.extend(evaluated.matrix_world @ Vector(c) for c in evaluated.bound_box)
        mesh_rows.append({
            "name": obj.name, "vertices": len(mesh.vertices),
            "edges": len(mesh.edges), "polygons": len(mesh.polygons),
            "has_uv": len(mesh.uv_layers) > 0,
            "materials": [m.name for m in obj.data.materials if m],
        })
    finally:
        evaluated.to_mesh_clear()

if points:
    mins = [min(p[i] for p in points) for i in range(3)]
    maxs = [max(p[i] for p in points) for i in range(3)]
    dims = [maxs[i] - mins[i] for i in range(3)]
    center = Vector([(mins[i] + maxs[i]) / 2 for i in range(3)])
    radius = max(max(dims) / 2, 0.25)
else:
    mins = maxs = dims = None
    center, radius = Vector((0, 0, 0)), 2.0

material_rows = []
for mat in materials:
    row = {"name": mat.name, "use_nodes": mat.use_nodes, "base_color": None, "textures": []}
    if mat.use_nodes and mat.node_tree:
        for node in mat.node_tree.nodes:
            if node.type == "BSDF_PRINCIPLED":
                socket = node.inputs.get("Base Color")
                if socket: row["base_color"] = list(socket.default_value)
            if node.type == "TEX_IMAGE" and node.image:
                row["textures"].append({
                    "name": node.image.name, "filepath": node.image.filepath,
                    "size": list(node.image.size),
                    "colorspace": node.image.colorspace_settings.name,
                })
    material_rows.append(row)

report = {
    "source_file": os.path.basename(source), "source_bytes": os.path.getsize(source),
    "blender_version": bpy.app.version_string,
    "mesh_count": len(meshes), "meshes": mesh_rows,
    "armature_count": len(armatures),
    "armatures": [{"name": a.name, "bones": len(a.data.bones)} for a in armatures],
    "action_count": len(actions),
    "actions": [{"name": a.name, "frame_range": list(a.frame_range)} for a in actions],
    "material_count": len(materials), "materials": material_rows,
    "image_count": len(images),
    "images": [{"name": im.name, "size": list(im.size), "filepath": im.filepath} for im in images],
    "bounds": {"min": mins, "max": maxs, "dimensions": dims},
    "notes": [
        "Source GLB is imported for inspection only and is never overwritten.",
        "A preview does not certify rigging, animation quality, gameplay scale, or licensing."
    ],
}
with open(os.path.join(out_dir, "zargat-report.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
if not meshes:
    raise SystemExit("GLB imported but contains no mesh objects; report was written.")

scene.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys() else "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 1200
scene.render.resolution_y = 1200
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
view_transforms = bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items.keys()\nscene.view_settings.view_transform = "AgX" if "AgX" in view_transforms else "Standard"
scene.world = bpy.data.worlds.new("Zaragat Studio World") if not scene.world else scene.world
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.025, 0.03, 0.045, 1)
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.45

def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()

camera_data = bpy.data.cameras.new("Preview Camera")
camera = bpy.data.objects.new("Preview Camera", camera_data)
scene.collection.objects.link(camera)
camera.location = center + Vector((radius * 2.8, radius * 1.7, radius * 3.2))
aim(camera, center)
camera.data.type = "ORTHO"
camera.data.ortho_scale = max(max(dims) * 1.65, 2.0)
scene.camera = camera

def add_area(name, offset, energy, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.shape, data.size = energy, "DISK", size
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = center + Vector(offset)
    aim(obj, center)

add_area("Key Light", (radius*2, radius*2, radius*2.5), 1800, radius*2.2)
add_area("Fill Light", (-radius*2, radius*.7, radius), 900, radius*2.5)
add_area("Rim Light", (radius*.4, -radius*2.2, radius*2), 2200, radius*1.6)
scene.render.filepath = os.path.join(out_dir, "zargat-preview.png")
bpy.ops.render.render(write_still=True)
print("ZARAGAT_INSPECTION_OK")
print(json.dumps({"meshes":len(meshes),"armatures":len(armatures),"actions":len(actions),"materials":len(materials)}))
