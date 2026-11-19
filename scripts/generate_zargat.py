#!/usr/bin/env python3
"""Generate OMOBA's standalone, modular-skinned Zaragat avatar with Blender."""
import bpy
import math
import os
from mathutils import Vector

OUT = os.path.join(os.path.dirname(__file__), "..", "client", "assets", "avatars", "zargat.glb")
OUT = os.path.abspath(OUT)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.armatures, bpy.data.actions):
    for block in list(datablocks):
        if block.users == 0:
            datablocks.remove(block)

def mat(name, color, metallic=0.0, rough=0.5, emission=None):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*color, 1.0)
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Roughness"].default_value = rough
    if emission:
        p.inputs["Emission Color"].default_value = (*emission, 1.0)
        p.inputs["Emission Strength"].default_value = 2.0
    return m

MAT_SKIN = mat("Zargat | Ashen crimson skin", (0.19, 0.035, 0.055), 0.08, 0.62)
MAT_ARMOR = mat("Zargat | Obsidian armor", (0.025, 0.018, 0.035), 0.82, 0.28)
MAT_RED = mat("Zargat | Infernal steel", (0.32, 0.035, 0.025), 0.68, 0.3)
MAT_GOLD = mat("Zargat | Ancient gold", (0.72, 0.36, 0.07), 0.78, 0.25)
MAT_EMBER = mat("Zargat | Molten core", (1.0, 0.12, 0.015), 0.15, 0.22, (1.0, 0.045, 0.004))
MAT_WING = mat("Zargat | Membrane", (0.075, 0.009, 0.025), 0.12, 0.68)
MAT_HAIR = mat("Zargat | Silver mane", (0.62, 0.64, 0.68), 0.15, 0.38)
MAT_EYE = mat("Zargat | Burning eyes", (1.0, 0.22, 0.015), 0.05, 0.2, (1.0, 0.08, 0.002))

# Blender-space coordinates: Z up; the demon faces -Y.
arm_data = bpy.data.armatures.new("Zargat_Skeleton")
arm = bpy.data.objects.new("Zargat_Rig", arm_data)
bpy.context.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
bones = {}
def bone(name, head, tail, parent=None):
    b = arm_data.edit_bones.new(name)
    b.head = head
    b.tail = tail
    if parent:
        b.parent = bones[parent]
    bones[name] = b

bone("root", (0,0,0), (0,0,0.25))
bone("pelvis", (0,0,0.78), (0,0,1.02), "root")
bone("spine", (0,0,1.02), (0,0,1.36), "pelvis")
bone("chest", (0,0,1.36), (0,0,1.58), "spine")
bone("neck", (0,0,1.58), (0,0,1.73), "chest")
bone("head", (0,0,1.73), (0,0,1.98), "neck")
for side, suffix in [(-1,"L"), (1,"R")]:
    bone("upper_arm."+suffix, (side*0.34,0,1.48), (side*0.62,0,1.18), "chest")
    bone("forearm."+suffix, (side*0.62,0,1.18), (side*0.72,-0.01,0.88), "upper_arm."+suffix)
    bone("hand."+suffix, (side*0.72,-0.01,0.88), (side*0.73,-0.03,0.72), "forearm."+suffix)
    bone("thigh."+suffix, (side*0.20,0,0.83), (side*0.23,0,0.48), "pelvis")
    bone("shin."+suffix, (side*0.23,0,0.48), (side*0.23,-0.02,0.14), "thigh."+suffix)
    bone("foot."+suffix, (side*0.23,-0.02,0.14), (side*0.23,-0.25,0.08), "shin."+suffix)
    bone("wing."+suffix, (side*0.37,0.08,1.52), (side*1.02,0.12,1.88), "chest")
bone("tail.01", (0,0.18,0.82), (0,0.48,0.70), "pelvis")
bone("tail.02", (0,0.48,0.70), (0,0.72,0.55), "tail.01")
bone("tail.03", (0,0.72,0.55), (0,0.95,0.42), "tail.02")
bone("tail.tip", (0,0.95,0.42), (0,1.12,0.36), "tail.03")
bone("sword", (0.73,-0.02,0.88), (0.78,-0.02,1.48), "hand.R")
bpy.ops.object.mode_set(mode="OBJECT")
arm.show_in_front = True
arm_data.display_type = "OCTAHEDRAL"

parts = []
def finish_part(obj, name, material, bone_name):
    obj.name = name
    obj.data.materials.append(material)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    vg = obj.vertex_groups.new(name=bone_name)
    vg.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
    obj.parent = arm
    mod = obj.modifiers.new("Zargat skeletal deformation", "ARMATURE")
    mod.object = arm
    parts.append(obj)
    return obj

def sphere(name, loc, scale, material, bone_name, segments=12, rings=8):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=1, location=loc)
    o = bpy.context.object
    o.scale = scale
    return finish_part(o, name, material, bone_name)

def cube(name, loc, scale, material, bone_name, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.scale = scale
    if bevel:
        mod=o.modifiers.new("Forged edges","BEVEL"); mod.width=bevel; mod.segments=1
        bpy.context.view_layer.objects.active=o
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return finish_part(o, name, material, bone_name)

def cone_between(name, a, b, radius, material, bone_name, vertices=8, radius2=0.0):
    a,b=Vector(a),Vector(b)
    direction=b-a
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius, radius2=radius2, depth=direction.length, location=(a+b)*0.5)
    o=bpy.context.object
    o.rotation_mode="QUATERNION"
    o.rotation_quaternion=Vector((0,0,1)).rotation_difference(direction)
    return finish_part(o,name,material,bone_name)

def wing_mesh(side, suffix):
    # Angular bat wing membrane, attached to its own animated wing bone.
    pts=[
        (side*0.34,0.10,1.52),
        (side*0.74,0.10,1.92),
        (side*1.42,0.13,2.12),
        (side*1.22,0.12,1.48),
        (side*1.10,0.12,1.08),
        (side*0.83,0.10,1.34),
        (side*0.60,0.10,1.18),
    ]
    faces=[(0,1,5),(1,2,3),(1,3,5),(5,3,4),(0,5,6)]
    mesh=bpy.data.meshes.new("Zargat_Wing_"+suffix)
    mesh.from_pydata(pts,[],faces); mesh.materials.append(MAT_WING); mesh.update()
    obj=bpy.data.objects.new("Zargat_BatWing_"+suffix,mesh); bpy.context.collection.objects.link(obj)
    return finish_part(obj,obj.name,MAT_WING,"wing."+suffix)

# Core anatomy and plated silhouette.
sphere("Infernal torso",(0,0,1.30),(0.43,0.27,0.43),MAT_SKIN,"spine")
sphere("Broad chest",(0,-0.015,1.48),(0.55,0.30,0.32),MAT_SKIN,"chest")
cube("Obsidian breastplate",(0,-0.285,1.43),(0.72,0.12,0.46),MAT_ARMOR,"chest",0.06)
sphere("Molten heart",(0,-0.36,1.43),(0.13,0.035,0.16),MAT_EMBER,"chest")
for z in (1.30,1.42,1.54):
    for side in (-1,1):
        cone_between("Cuirass molten rune",(side*0.10,-0.36,z),(side*0.17,-0.36,z+0.07),0.025,MAT_GOLD,"chest",6)
sphere("Infernal pelvis",(0,0,0.86),(0.34,0.24,0.22),MAT_ARMOR,"pelvis")
cube("Skull belt",(0,-0.24,0.86),(0.24,0.055,0.16),MAT_GOLD,"pelvis",0.025)

# Head, horns, mane, eyes and jaw.
sphere("Demon skull",(0,-0.015,1.83),(0.25,0.23,0.30),MAT_SKIN,"head")
cube("Infernal face guard",(0,-0.22,1.78),(0.40,0.075,0.17),MAT_ARMOR,"head",0.025)
cone_between("Demon jaw",(0,-0.18,1.70),(0,-0.20,1.57),0.13,MAT_RED,"head",8,0.025)
for side in (-1,1):
    cone_between("Crown horn",(side*0.16,0.0,1.98),(side*0.29,0.02,2.35),0.105,MAT_GOLD,"head",9,0.006)
    sphere("Burning eye",(side*0.105,-0.245,1.84),(0.045,0.025,0.035),MAT_EYE,"head",10,6)
    cone_between("Shoulder spike",(side*0.40,0,1.62),(side*0.66,0.02,1.91),0.12,MAT_GOLD,"chest",8,0.005)
    sphere("Silver mane",(side*0.17,0.13,1.80),(0.14,0.16,0.28),MAT_HAIR,"head")
    cone_between("Mane lock",(side*0.18,0.16,1.82),(side*0.26,0.50,1.55),0.10,MAT_HAIR,"head",7,0.015)

# Arms and gauntlets.
for side,suffix in [(-1,"L"),(1,"R")]:
    sphere("Demon bicep "+suffix,(side*0.48,0,1.35),(0.19,0.20,0.27),MAT_SKIN,"upper_arm."+suffix)
    sphere("Obsidian pauldron "+suffix,(side*0.43,-0.03,1.58),(0.27,0.25,0.18),MAT_RED,"chest")
    sphere("Demon forearm "+suffix,(side*0.68,-0.01,1.02),(0.15,0.16,0.25),MAT_SKIN,"forearm."+suffix)
    cube("War gauntlet "+suffix,(side*0.71,-0.15,0.91),(0.28,0.18,0.22),MAT_ARMOR,"forearm."+suffix,0.035)
    for claw in range(3):
        x=side*(0.63+claw*0.075)
        cone_between("Gauntlet talon "+suffix,(x,-0.20,0.86),(x,-0.28,0.73),0.035,MAT_GOLD,"hand."+suffix,6,0.004)
    sphere("Demon thigh "+suffix,(side*0.22,0,0.65),(0.19,0.22,0.28),MAT_SKIN,"thigh."+suffix)
    cube("Infernal greave "+suffix,(side*0.23,-0.16,0.34),(0.25,0.25,0.36),MAT_ARMOR,"shin."+suffix,0.035)
    sphere("Knee plate "+suffix,(side*0.23,-0.29,0.49),(0.15,0.07,0.12),MAT_RED,"shin."+suffix)
    cube("Clawed boot "+suffix,(side*0.23,-0.26,0.12),(0.27,0.42,0.18),MAT_ARMOR,"foot."+suffix,0.025)
    cone_between("Boot spur "+suffix,(side*0.23,-0.43,0.12),(side*0.23,-0.60,0.07),0.06,MAT_GOLD,"foot."+suffix,7,0.003)
    wing_mesh(side,suffix)
    # Wing ribs.
    cone_between("Wing bone "+suffix,(side*0.38,0.08,1.53),(side*1.40,0.13,2.10),0.035,MAT_GOLD,"wing."+suffix,6,0.012)
    cone_between("Wing claw "+suffix,(side*1.40,0.13,2.10),(side*1.52,0.13,2.24),0.05,MAT_RED,"wing."+suffix,7,0.002)

# Segmented tail, each segment animated independently.
sphere("Tail base",(0,0.20,0.82),(0.13,0.16,0.15),MAT_RED,"tail.01")
for name,loc,scale,bn in [
    ("Tail segment 1",(0,0.43,0.69),(0.11,0.13,0.13),"tail.01"),
    ("Tail segment 2",(0,0.68,0.54),(0.09,0.13,0.11),"tail.02"),
    ("Tail segment 3",(0,0.91,0.40),(0.075,0.12,0.09),"tail.03"),
]:
    sphere(name,loc,scale,MAT_ARMOR,bn)
cone_between("Tail blade",(0,1.02,0.34),(0,1.25,0.28),0.11,MAT_GOLD,"tail.tip",8,0.002)

# Hellblade, mounted to the dedicated sword bone.
cube("Hellblade grip",(0.76,-0.06,0.91),(0.075,0.075,0.34),MAT_ARMOR,"sword",0.015)
cube("Hellblade crossguard",(0.76,-0.06,1.09),(0.36,0.09,0.075),MAT_GOLD,"sword",0.02)
cone_between("Molten demon sword",(0.76,-0.06,1.10),(0.76,-0.06,1.84),0.12,MAT_EMBER,"sword",6,0.004)
cone_between("Sword spine",(0.76,-0.115,1.12),(0.76,-0.115,1.78),0.025,MAT_GOLD,"sword",5,0.003)

# Merge the weighted pieces into a single skinned mesh, retaining material slots.
bpy.ops.object.select_all(action="DESELECT")
for obj in parts: obj.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
bpy.ops.object.join()
body=bpy.context.object
body.name="Zargat_Skinned_Mesh"
body.parent=arm
body["character_id"]="zargat"
body["rig_type"]="independent_modular_armature"

# Authored animation clips, each stored as a named NLA strip for glTF export.
def make_action(name, frames, pose_fn):
    action=bpy.data.actions.new(name)
    arm.animation_data_create()
    arm.animation_data.action=action
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        pose_fn(frame)
        for pb in arm.pose.bones:
            pb.keyframe_insert(data_path="rotation_euler",frame=frame,group=pb.name)
    arm.animation_data.action=None
    track=arm.animation_data.nla_tracks.new()
    track.name=name
    strip=track.strips.new(name,frames[0],action)
    strip.name=name
    strip.blend_type="REPLACE"

def setrot(name, x=0, y=0, z=0):
    pb=arm.pose.bones.get(name)
    if pb:
        pb.rotation_mode="XYZ"
        pb.rotation_euler=(x,y,z)

def reset_pose():
    for pb in arm.pose.bones:
        pb.rotation_mode="XYZ"
        pb.rotation_euler=(0,0,0)

def idle_pose(f):
    reset_pose()
    phase=(f-1)/30*2*math.pi
    setrot("spine",0,0,0.018*math.sin(phase))
    setrot("chest",0.018*math.sin(phase),0,0)
    setrot("head",0,0,0.025*math.sin(phase+0.5))
    setrot("wing.L",0,0,0.10*math.sin(phase))
    setrot("wing.R",0,0,-0.10*math.sin(phase))
    setrot("tail.02",0.08*math.sin(phase),0,0)
    setrot("tail.03",0.12*math.sin(phase+0.6),0,0)
make_action("Idle", [1,16,31], idle_pose)

def run_pose(f):
    reset_pose()
    phase=(f-1)/20*2*math.pi
    setrot("thigh.L",0,0,0.58*math.sin(phase))
    setrot("thigh.R",0,0,0.58*math.sin(phase+math.pi))
    setrot("shin.L",0,0,max(0,-math.sin(phase))*0.65)
    setrot("shin.R",0,0,max(0,-math.sin(phase+math.pi))*0.65)
    setrot("upper_arm.L",0,0,-0.40*math.sin(phase))
    setrot("upper_arm.R",0,0,-0.40*math.sin(phase+math.pi))
    setrot("wing.L",0,0,0.18*math.sin(phase*2))
    setrot("wing.R",0,0,-0.18*math.sin(phase*2))
    setrot("spine",0.04*math.sin(phase*2),0,0)
make_action("Run", [1,6,11,16,21], run_pose)

def walk_pose(f):
    run_pose(f)
make_action("Walk", [1,6,11,16,21], walk_pose)

def attack_pose(f):
    reset_pose()
    u=(f-1)/18
    swing=math.sin(u*math.pi)
    setrot("upper_arm.R",0,0,-1.15*swing)
    setrot("forearm.R",0,0,-0.55*swing)
    setrot("sword",0,0,-0.85*swing)
    setrot("chest",0,0,0.20*swing)
    setrot("wing.L",0,0,0.12*swing)
    setrot("wing.R",0,0,-0.12*swing)
make_action("Attack", [1,7,13,19], attack_pose)

def cast_pose(f):
    reset_pose()
    u=(f-1)/24
    pulse=math.sin(u*math.pi)
    setrot("upper_arm.L",0,0,0.85*pulse)
    setrot("upper_arm.R",0,0,-0.85*pulse)
    setrot("wing.L",0,0,0.38*pulse)
    setrot("wing.R",0,0,-0.38*pulse)
    setrot("chest",0,0,-0.12*pulse)
make_action("Cast", [1,8,16,25], cast_pose)

def death_pose(f):
    reset_pose()
    u=(f-1)/30
    setrot("spine",0,0,0.75*u)
    setrot("head",0,0,-0.35*u)
    setrot("upper_arm.L",0,0,0.8*u)
    setrot("upper_arm.R",0,0,-0.8*u)
    setrot("wing.L",0,0,0.5*u)
    setrot("wing.R",0,0,-0.5*u)
make_action("Death", [1,10,20,31], death_pose)

bpy.context.scene.frame_set(1)
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True); body.select_set(True)
bpy.context.view_layer.objects.active=arm
os.makedirs(os.path.dirname(OUT),exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format="GLB",
    use_selection=True,
    export_apply=True,
    export_animations=True,
    export_nla_strips=True,
    export_skins=True,
    export_yup=True,
)
if not os.path.isfile(OUT) or os.path.getsize(OUT) < 20000:
    raise RuntimeError("Zargat GLB export failed or produced an unexpectedly small file")
print("Exported", OUT, os.path.getsize(OUT), "bytes")
