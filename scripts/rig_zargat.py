#!/usr/bin/env python3
"""Build a separate humanoid/wing/tail rig for source.glb; never overwrite source."""
import bpy, json, os, sys
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(args) != 2:
    raise SystemExit("usage: blender --background --python rig_zargat.py -- source.glb output_dir")
source, out_dir = args
os.makedirs(out_dir, exist_ok=True)
if not os.path.isfile(source):
    raise SystemExit("Source GLB not found: " + source)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(source))
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not meshes:
    raise SystemExit("No mesh objects found in source GLB")

depsgraph = bpy.context.evaluated_depsgraph_get()
points = []
for obj in meshes:
    evaluated = obj.evaluated_get(depsgraph)
    points.extend(evaluated.matrix_world @ Vector(c) for c in evaluated.bound_box)
mins = [min(p[i] for p in points) for i in range(3)]
maxs = [max(p[i] for p in points) for i in range(3)]
dims = [maxs[i] - mins[i] for i in range(3)]
height = max(dims[2], 1e-4)
cx, cy = (mins[0] + maxs[0]) * .5, (mins[1] + maxs[1]) * .5
zmin = mins[2]
def z_at(t): return zmin + height * t

arm_data = bpy.data.armatures.new("DemonKnight_Armature")
arm_obj = bpy.data.objects.new("DemonKnight_Rig", arm_data)
bpy.context.scene.collection.objects.link(arm_obj)
arm_obj.location = (0, 0, 0)
bpy.context.view_layer.objects.active = arm_obj
arm_obj.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
edit = arm_data.edit_bones
for old in list(edit): edit.remove(old)

def add_bone(name, head, tail, parent=None, connected=False):
    bone = edit.new(name)
    bone.head, bone.tail = Vector(head), Vector(tail)
    if parent:
        bone.parent, bone.use_connect = parent, connected
    return bone

pelvis = add_bone("Pelvis", (cx, cy, z_at(.48)), (cx, cy, z_at(.55)))
spine1 = add_bone("Spine_01", pelvis.tail, (cx, cy, z_at(.64)), pelvis, True)
spine2 = add_bone("Spine_02", spine1.tail, (cx, cy, z_at(.75)), spine1, True)
neck = add_bone("Neck", spine2.tail, (cx, cy, z_at(.83)), spine2, True)
add_bone("Head", neck.tail, (cx, cy, z_at(.96)), neck, True)

for side, sign in (("L", 1.0), ("R", -1.0)):
    hip = add_bone("Thigh_" + side, (cx+sign*height*.075,cy,z_at(.49)), (cx+sign*height*.085,cy,z_at(.27)), pelvis)
    shin = add_bone("Shin_" + side, hip.tail, (cx+sign*height*.085,cy-height*.02,z_at(.07)), hip, True)
    add_bone("Foot_" + side, shin.tail, (cx+sign*height*.085,cy-height*.11,z_at(.015)), shin, True)

for side, sign in (("L", 1.0), ("R", -1.0)):
    clav = add_bone("Clavicle_"+side, (cx+sign*height*.045,cy,z_at(.75)), (cx+sign*height*.14,cy,z_at(.74)), spine2)
    upper = add_bone("UpperArm_"+side, clav.tail, (cx+sign*height*.28,cy,z_at(.57)), clav, True)
    fore = add_bone("Forearm_"+side, upper.tail, (cx+sign*height*.36,cy-height*.05,z_at(.41)), upper, True)
    add_bone("Hand_"+side, fore.tail, (cx+sign*height*.40,cy-height*.09,z_at(.34)), fore, True)

tail_parent = pelvis
for i, (zt, yd) in enumerate([(.48,.12),(.43,.26),(.36,.40),(.28,.52)], 1):
    head = tail_parent.tail if i > 1 else (cx,cy+height*.04,z_at(.50))
    tail_parent = add_bone("Tail_%02d" % i, head, (cx,cy+height*yd,z_at(zt)), tail_parent, i > 1)

for side, sign in (("L", 1.0), ("R", -1.0)):
    root = add_bone("Wing_Root_"+side, (cx+sign*height*.07,cy+height*.03,z_at(.73)), (cx+sign*height*.35,cy+height*.06,z_at(.86)), spine2)
    mid = add_bone("Wing_Mid_"+side, root.tail, (cx+sign*height*.62,cy+height*.08,z_at(.78)), root, True)
    add_bone("Wing_Tip_"+side, mid.tail, (cx+sign*height*.78,cy+height*.10,z_at(.64)), mid, True)

bpy.ops.object.mode_set(mode="OBJECT")
# First attempt the user's automatic heat-weight workflow. Blender can fail on
# intersecting/isolated demon armor parts; in that case use deterministic
# nearest-bone-segment weights so every vertex is bound to the skeleton.
for obj in meshes:
    obj.select_set(False)
arm_obj.select_set(False)
try:
    for obj in meshes:
        obj.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
except Exception as exc:
    print("Automatic weights operator raised:", repr(exc))

def has_complete_weights(obj):
    if not any(m.type == "ARMATURE" and m.object == arm_obj for m in obj.modifiers):
        return False
    return all(len(v.groups) > 0 for v in obj.data.vertices)

if not all(has_complete_weights(obj) for obj in meshes):
    print("Automatic weights incomplete; applying nearest-segment fallback weights")
    import numpy as np
    bone_list = list(arm_data.bones)
    bone_names = [b.name for b in bone_list]
    bone_groups = {}
    for obj in meshes:
        # Keep the source mesh transform unchanged; weights are calculated in armature space.
        for group in list(obj.vertex_groups):
            obj.vertex_groups.remove(group)
        for mod in list(obj.modifiers):
            if mod.type == "ARMATURE":
                obj.modifiers.remove(mod)
        mod = obj.modifiers.new(name="DemonKnight_Armature", type="ARMATURE")
        mod.object = arm_obj
        groups = {name: obj.vertex_groups.new(name=name) for name in bone_names}
        coords = np.asarray([tuple(obj.matrix_world @ v.co) for v in obj.data.vertices], dtype=np.float64)
        if len(coords) == 0:
            continue
        dist2 = np.empty((len(bone_list), len(coords)), dtype=np.float64)
        for bi, bone in enumerate(bone_list):
            a = np.asarray(tuple(bone.head_local), dtype=np.float64)
            b = np.asarray(tuple(bone.tail_local), dtype=np.float64)
            ab = b - a
            denom = float(np.dot(ab, ab))
            if denom < 1.0e-12:
                delta = coords - a
                dist2[bi] = np.einsum("ij,ij->i", delta, delta)
            else:
                t = np.clip(((coords - a) @ ab) / denom, 0.0, 1.0)
                closest = a[None, :] + t[:, None] * ab[None, :]
                delta = coords - closest
                dist2[bi] = np.einsum("ij,ij->i", delta, delta)
        k = min(4, len(bone_list))
        nearest = np.argpartition(dist2, kth=k-1, axis=0)[:k, :]
        nearest_d2 = np.take_along_axis(dist2, nearest, axis=0)
        inv = 1.0 / np.maximum(nearest_d2, 1.0e-10)
        weights = inv / np.sum(inv, axis=0, keepdims=True)
        vertex_ids = np.arange(len(coords), dtype=np.int32)
        for slot in range(k):
            for bi in range(len(bone_list)):
                mask = nearest[slot] == bi
                ids = vertex_ids[mask]
                vals = weights[slot, mask]
                group = groups[bone_names[bi]]
                for vid, weight in zip(ids, vals):
                    group.add([int(vid)], float(weight), "REPLACE")

validation = []
for obj in meshes:
    mods = [m for m in obj.modifiers if m.type == "ARMATURE" and m.object == arm_obj]
    weighted = sum(1 for v in obj.data.vertices if any(g.weight > 0 for g in v.groups))
    validation.append({"mesh":obj.name,"vertices":len(obj.data.vertices),"vertex_groups":len(obj.vertex_groups),"weighted_vertices":weighted,"armature_modifiers":len(mods)})
if not all(r["weighted_vertices"] == r["vertices"] and r["armature_modifiers"] > 0 for r in validation):
    raise SystemExit("Skin weights/modifier validation failed after automatic and fallback weighting")
bpy.ops.object.select_all(action="DESELECT")
for obj in meshes: obj.select_set(True)
arm_obj.select_set(True)
bpy.context.view_layer.objects.active = arm_obj
out_glb = os.path.join(out_dir,"zargat-rigged.glb")
bpy.ops.export_scene.gltf(filepath=out_glb,export_format="GLB",use_selection=True)
report = {"source":os.path.basename(source),"output":os.path.basename(out_glb),"blender_version":bpy.app.version_string,"bone_count":len(arm_data.bones),"bones":[b.name for b in arm_data.bones],"bounds_dimensions":dims,"mesh_validation":validation,"animation_count":len(bpy.data.actions),"note":"First-pass automatic-weight rig; visual deformation review and animation tests are still required."}
with open(os.path.join(out_dir,"zargat-rig-report.json"),"w",encoding="utf-8") as f:
    json.dump(report,f,ensure_ascii=False,indent=2)
print("ZARGAT_RIGGING_OK")
print(json.dumps({"bones":len(arm_data.bones),"meshes":len(meshes),"output":out_glb}))
