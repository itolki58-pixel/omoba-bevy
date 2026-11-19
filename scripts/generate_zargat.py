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
        emission_input = p.inputs.get("Emission Color") or p.inputs.get("Emission")
        if emission_input:
            emission_input.default_value = (*emission, 1.0)
        strength_input = p.inputs.get("Emission Strength")
        if strength_input:
            strength_input.default_value = 2.0
    return m

MAT_SKIN = mat("Zargat | Ashen crimson skin", (0.19, 0.035, 0.055), 0.08, 0.62)
MAT_ARMOR = mat("Zargat | Obsidian armor", (0.025, 0.018, 0.035), 0.82, 0.28)
MAT_RED = mat("Zargat | Infernal steel", (0.32, 0.035, 0.025), 0.68, 0.3)
MAT_GOLD = mat("Zargat | Ancient gold", (0.72, 0.36, 0.07), 0.78, 0.25)
MAT_EMBER = mat("Zargat | Molten core", (1.0, 0.12, 0.015), 0.15, 0.22, (1.0, 0.045, 0.004))
MAT_WING = mat("Zargat | Membrane", (0.075, 0.009, 0.025), 0.12, 0.68)
MAT_HAIR = mat("Zargat | Silver mane", (0.62, 0.64, 0.68), 0.15, 0.38)
MAT_EYE = mat("Zargat | Burning eyes", (1.0, 0.22, 0.015), 0.05, 0.2, (1.0, 0.08, 0.002))


# Layered procedural surface detail: hammered obsidian, ash skin and molten seams.
def add_surface_detail(material, scale, bump_strength, roughness_strength=0.25):
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    shader = nodes.get("Principled BSDF")
    tex = nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = scale
    tex.inputs["Detail"].default_value = 5.0
    tex.inputs["Roughness"].default_value = 0.72
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.035
    links.new(tex.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    rough = nodes.new("ShaderNodeMapRange")
    rough.inputs["From Min"].default_value = 0.0
    rough.inputs["From Max"].default_value = 1.0
    rough.inputs["To Min"].default_value = max(0.12, material.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value - roughness_strength)
    rough.inputs["To Max"].default_value = min(0.9, material.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value + roughness_strength)
    links.new(tex.outputs["Fac"], rough.inputs["Value"])
    links.new(rough.outputs["Result"], shader.inputs["Roughness"])

add_surface_detail(MAT_SKIN, 7.5, 0.22, 0.12)
add_surface_detail(MAT_ARMOR, 38.0, 0.16, 0.10)
add_surface_detail(MAT_RED, 24.0, 0.12, 0.08)
add_surface_detail(MAT_WING, 16.0, 0.18, 0.10)

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
bone("jaw", (0,-0.12,1.70), (0,-0.20,1.58), "head")
for side, suffix in [(-1,"L"), (1,"R")]:
    bone("upper_arm."+suffix, (side*0.34,0,1.48), (side*0.62,0,1.18), "chest")
    bone("forearm."+suffix, (side*0.62,0,1.18), (side*0.72,-0.01,0.88), "upper_arm."+suffix)
    bone("hand."+suffix, (side*0.72,-0.01,0.88), (side*0.73,-0.03,0.72), "forearm."+suffix)
    for finger in range(3):
        spread = (finger - 1) * 0.075
        bone(f"finger.{finger+1}.{suffix}", (side*(0.70+spread),-0.04,0.77), (side*(0.70+spread),-0.10,0.68), "hand."+suffix)
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

def sphere(name, loc, scale, material, bone_name, segments=32, rings=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=1, location=loc)
    o = bpy.context.object
    o.scale = scale
    for poly in o.data.polygons: poly.use_smooth = True
    return finish_part(o, name, material, bone_name)

def cube(name, loc, scale, material, bone_name, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.scale = scale
    if bevel:
        mod=o.modifiers.new("Forged edges","BEVEL"); mod.width=bevel; mod.segments=3
        bpy.context.view_layer.objects.active=o
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return finish_part(o, name, material, bone_name)

def cone_between(name, a, b, radius, material, bone_name, vertices=16, radius2=0.0):
    a,b=Vector(a),Vector(b)
    direction=b-a
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius, radius2=radius2, depth=direction.length, location=(a+b)*0.5)
    o=bpy.context.object
    o.rotation_mode="QUATERNION"
    o.rotation_quaternion=Vector((0,0,1)).rotation_difference(direction)
    for poly in o.data.polygons: poly.use_smooth = True
    return finish_part(o,name,material,bone_name)

def wing_mesh(side, suffix):
    # Dense, curved bat membrane with a scalloped trailing edge (not flat triangles).
    # The surface is tessellated so lighting and the membrane normal read smoothly.
    span_steps, chord_steps = 18, 12
    verts, faces = [], []
    leading = [(0.36,1.53),(0.70,1.83),(1.05,2.02),(1.42,2.13)]
    trailing = [(0.36,1.48),(0.64,1.22),(0.91,1.05),(1.17,1.12),(1.31,1.48)]
    def sample(profile, u):
        q=u*(len(profile)-1); i=min(int(q),len(profile)-2); f=q-i
        return profile[i][0]*(1-f)+profile[i+1][0]*f, profile[i][1]*(1-f)+profile[i+1][1]*f
    for i in range(span_steps+1):
        u=i/span_steps
        lx,lz=sample(leading,u)
        tx,tz=sample(trailing,min(1,u))
        # Distinct scallops between the long wing fingers.
        scallop=math.sin(u*math.pi*4.0)**2 * 0.055
        for j in range(chord_steps+1):
            v=j/chord_steps
            x=lx*(1-v)+tx*v
            z=lz*(1-v)+tz*v-scallop*math.sin(v*math.pi)
            y=0.105 + 0.035*math.sin(u*math.pi)*math.sin(v*math.pi)
            verts.append((side*x,y,z))
    for i in range(span_steps):
        for j in range(chord_steps):
            p=i*(chord_steps+1)+j
            faces.append((p,p+1,p+chord_steps+2,p+chord_steps+1))
    mesh=bpy.data.meshes.new("Zargat_Wing_"+suffix)
    mesh.from_pydata(verts,[],faces); mesh.materials.append(MAT_WING); mesh.update()
    obj=bpy.data.objects.new("Zargat_BatWing_"+suffix,mesh); bpy.context.collection.objects.link(obj)
    for poly in mesh.polygons: poly.use_smooth=True
    solid=obj.modifiers.new("Thin leathery membrane","SOLIDIFY"); solid.thickness=0.012
    return finish_part(obj,obj.name,MAT_WING,"wing."+suffix)

# Core anatomy and plated silhouette.
sphere("Infernal torso",(0,0,1.28),(0.46,0.31,0.48),MAT_SKIN,"spine")
sphere("Broad chest",(0,-0.005,1.49),(0.61,0.34,0.36),MAT_SKIN,"chest")
sphere("Obsidian breastplate",(0,-0.285,1.45),(0.47,0.105,0.30),MAT_ARMOR,"chest")
sphere("Molten heart",(0,-0.386,1.45),(0.105,0.025,0.12),MAT_EMBER,"chest")
for z in (1.30,1.42,1.54):
    for side in (-1,1):
        cone_between("Cuirass molten rune",(side*0.10,-0.36,z),(side*0.17,-0.36,z+0.07),0.025,MAT_GOLD,"chest",6)
sphere("Infernal pelvis",(0,0,0.86),(0.34,0.24,0.22),MAT_ARMOR,"pelvis")
cube("Skull belt",(0,-0.24,0.86),(0.24,0.055,0.16),MAT_GOLD,"pelvis",0.025)

# Head, horns, mane, eyes and jaw.
sphere("Demon skull",(0,-0.025,1.84),(0.285,0.255,0.325),MAT_SKIN,"head")
sphere("Infernal face guard",(0,-0.238,1.785),(0.225,0.055,0.155),MAT_ARMOR,"head")
sphere("Demon jaw",(0,-0.215,1.675),(0.17,0.105,0.13),MAT_RED,"jaw")
for side in (-1,1):
    cone_between("Crown horn",(side*0.16,0.0,1.98),(side*0.29,0.02,2.35),0.105,MAT_GOLD,"head",9,0.006)
    sphere("Burning eye",(side*0.105,-0.245,1.84),(0.045,0.025,0.035),MAT_EYE,"head",10,6)
    cone_between("Shoulder spike",(side*0.40,0,1.62),(side*0.66,0.02,1.91),0.12,MAT_GOLD,"chest",8,0.005)
    sphere("Silver mane",(side*0.17,0.13,1.80),(0.14,0.16,0.28),MAT_HAIR,"head")
    cone_between("Mane lock",(side*0.18,0.16,1.82),(side*0.26,0.50,1.55),0.10,MAT_HAIR,"head",7,0.015)


def curve_tube(name, points, radius, material, bone_name, resolution=3):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 16
    curve.bevel_depth = radius
    curve.bevel_resolution = resolution
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points)-1)
    for bp, point in zip(spline.bezier_points, points):
        bp.co = point
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    return finish_part(obj, name, material, bone_name)

# Major-form sculpt pass: anatomical volumes and layered silhouette.
# The armor follows the body instead of reading as a flat rectangular box.
for side, suffix in [(-1,"L"), (1,"R")]:
    # Pronounced pectoral and deltoid masses visible around the breastplate.
    sphere("Sculpted pectoral "+suffix, (side*0.245,-0.205,1.49),
           (0.245,0.155,0.205), MAT_SKIN, "chest")
    sphere("Deltoid muscle "+suffix, (side*0.48,-0.015,1.43),
           (0.205,0.205,0.205), MAT_SKIN, "upper_arm."+suffix)
    # Layered curved chest armor, clavicle ridge and lower rib plates.
    sphere("Upper chest armor lobe "+suffix, (side*0.205,-0.345,1.55),
           (0.205,0.055,0.145), MAT_RED, "chest")
    curve_tube("Clavicle forged ridge "+suffix,
               [(0,-0.365,1.68),(side*0.17,-0.375,1.69),(side*0.34,-0.33,1.63)],
               0.026, MAT_GOLD, "chest", 4)
    for idx in range(2):
        z = 1.27 - idx*0.105
        sphere("Obsidian rib plate "+suffix+str(idx),
               (side*(0.22-idx*0.025),-0.275,z),
               (0.18,0.065,0.075), MAT_ARMOR, "spine", 20, 14)
    # Muscular forearm silhouette under the armor.
    sphere("Elbow joint "+suffix, (side*0.625,-0.005,1.17),
           (0.145,0.16,0.15), MAT_RED, "forearm."+suffix)
    # Sculpted knee and calf volumes to avoid the blocky toy-leg silhouette.
    sphere("Calf muscle "+suffix, (side*0.23,0.005,0.29),
           (0.145,0.17,0.20), MAT_SKIN, "shin."+suffix)
    sphere("Layered knee shell "+suffix, (side*0.23,-0.275,0.49),
           (0.17,0.075,0.135), MAT_ARMOR, "shin."+suffix)
# Angular cheek planes, muzzle, brow and layered crown give the head a readable face.
for side in (-1,1):
    sphere("Temple armor", (side*0.205,-0.16,1.86),
           (0.09,0.105,0.17), MAT_ARMOR, "head", 24, 16)
    sphere("Muzzle plane", (side*0.065,-0.278,1.735),
           (0.075,0.045,0.055), MAT_RED, "jaw", 20, 12)
    curve_tube("Heavy demonic brow",
               [(side*0.025,-0.292,1.91),(side*0.11,-0.305,1.935),(side*0.205,-0.265,1.89)],
               0.035, MAT_RED, "head", 4)
    curve_tube("Jaw edge armor",
               [(side*0.18,-0.255,1.73),(side*0.13,-0.27,1.65),(side*0.035,-0.27,1.62)],
               0.018, MAT_GOLD, "jaw", 3)
# A central nose ridge and mouth slit replace the featureless mask surface.
sphere("Nose armor ridge", (0,-0.305,1.765), (0.045,0.045,0.075), MAT_GOLD, "head", 20, 12)
curve_tube("Mouth shadow", [(-0.075,-0.312,1.685),(0,-0.322,1.675),(0.075,-0.312,1.685)],
           0.009, MAT_ARMOR, "jaw", 3)
# Add a layered, tapered abdomen rather than a row of floating cubes.
for side in (-1,1):
    for idx,z in enumerate((1.18,1.08,0.98)):
        sphere("Anatomical abdominal plate",
               (side*(0.105 if idx==0 else 0.09),-0.245,z),
               (0.105,0.075,0.075), MAT_RED if idx==0 else MAT_ARMOR, "spine", 20, 14)

# Arms and gauntlets.
for side,suffix in [(-1,"L"),(1,"R")]:
    sphere("Demon bicep "+suffix,(side*0.49,0,1.34),(0.205,0.215,0.29),MAT_SKIN,"upper_arm."+suffix)
    sphere("Obsidian pauldron "+suffix,(side*0.43,-0.03,1.58),(0.27,0.25,0.18),MAT_RED,"chest")
    sphere("Demon forearm "+suffix,(side*0.68,-0.015,1.03),(0.17,0.18,0.265),MAT_SKIN,"forearm."+suffix)
    cube("War gauntlet "+suffix,(side*0.71,-0.15,0.91),(0.28,0.18,0.22),MAT_ARMOR,"forearm."+suffix,0.035)
    for claw in range(3):
        x=side*(0.63+claw*0.075)
        cone_between("Gauntlet talon "+suffix,(x,-0.20,0.86),(x,-0.28,0.73),0.035,MAT_GOLD,"hand."+suffix,6,0.004)
    sphere("Demon thigh "+suffix,(side*0.22,0,0.65),(0.215,0.235,0.30),MAT_SKIN,"thigh."+suffix)
    sphere("Infernal greave "+suffix,(side*0.23,-0.17,0.34),(0.155,0.115,0.235),MAT_ARMOR,"shin."+suffix)
    sphere("Knee plate "+suffix,(side*0.23,-0.29,0.49),(0.15,0.07,0.12),MAT_RED,"shin."+suffix)
    sphere("Clawed boot "+suffix,(side*0.23,-0.25,0.12),(0.17,0.24,0.12),MAT_ARMOR,"foot."+suffix)
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
cone_between("Molten demon sword",(0.76,-0.06,1.10),(0.76,-0.06,1.84),0.105,MAT_RED,"sword",8,0.012)
cone_between("Sword spine",(0.76,-0.115,1.12),(0.76,-0.115,1.78),0.025,MAT_GOLD,"sword",5,0.003)


# Additional sculpted silhouette and layered forged armor details.
# Raised breastplate ridges and molten channels form a readable chest emblem.
for side in (-1, 1):
    curve_tube("Living magma seam", [(side*0.06,-0.352,1.58),(side*0.13,-0.365,1.48),(side*0.08,-0.37,1.37),(side*0.20,-0.35,1.29)], 0.012, MAT_EMBER, "chest")
    curve_tube("Cuirass engraved gold fillet", [(side*0.27,-0.355,1.61),(side*0.34,-0.355,1.47),(side*0.29,-0.355,1.31)], 0.014, MAT_GOLD, "chest")
    # Layered abdominal plates with pointed lower edges.
    for idx, z in enumerate((1.20,1.09,0.99)):
        x=side*(0.13 if idx==0 else 0.12)
        cone_between("Layered abdominal plate", (x,-0.255,z+0.055),(x+side*0.055,-0.265,z-0.045),0.075,MAT_ARMOR,"spine",7,0.018)
    # Forearm armor ridges and luminous inlays.
    for idx in range(3):
        z=1.06-idx*0.09
        curve_tube("Bracer ember inlay",[(side*0.78,-0.17,z),(side*0.86,-0.18,z-0.035),(side*0.78,-0.17,z-0.07)],0.009,MAT_EMBER,"forearm."+("R" if side>0 else "L"))
    # Knee and thigh armor layering.
    sphere("Thigh outer plate",(side*0.31,-0.205,0.66),(0.13,0.075,0.22),MAT_RED,"thigh."+("R" if side>0 else "L"))
    for z in (0.47,0.39,0.31):
        curve_tube("Greave engraved line",[(side*0.12,-0.292,z),(side*0.23,-0.305,z-0.025),(side*0.34,-0.292,z)],0.009,MAT_GOLD,"shin."+("R" if side>0 else "L"))

# Crown silhouette: swept-back hooked horns with a dark keratin base and gold tips.
for side in (-1,1):
    suffix="R" if side>0 else "L"
    cone_between("Horn root collar",(side*0.15,0.0,1.99),(side*0.21,-0.015,2.12),0.12,MAT_ARMOR,"head",10,0.075)
    curve_tube("Swept infernal horn",[(side*0.18,0.02,2.00),(side*0.27,0.06,2.14),(side*0.34,0.12,2.30),(side*0.30,0.16,2.43)],0.075,MAT_RED,"head",4)
    cone_between("Horn gold tip",(side*0.30,0.16,2.37),(side*0.30,0.16,2.46),0.035,MAT_GOLD,"head",8,0.001)
    # Additional layered shoulder plates and rivets.
    sphere("Upper pauldron crest",(side*0.43,-0.17,1.69),(0.25,0.15,0.13),MAT_ARMOR,"chest")
    sphere("Pauldron molten jewel",(side*0.47,-0.285,1.61),(0.045,0.025,0.055),MAT_EMBER,"chest",10,6)

# Wing membrane ribs and branching veins; all follow the animated wing bones.
for side in (-1,1):
    suffix="R" if side>0 else "L"
    for j in range(4):
        t=j/4.0
        curve_tube("Wing finger rib",[(side*(0.42+0.12*t),0.075,1.55),(side*(0.76+0.12*t),0.055,1.72),(side*(1.08+0.10*t),0.07,1.88),(side*(1.38-0.04*t),0.12,2.08-0.13*j)],0.018 if j<2 else 0.012,MAT_RED,"wing."+suffix)
    curve_tube("Wing membrane vein",[(side*0.62,0.055,1.43),(side*0.88,0.045,1.49),(side*1.15,0.07,1.35)],0.009,MAT_EMBER,"wing."+suffix)

# Barbed tail ridges and glowing segments.
for idx,(y,z,bn) in enumerate(((0.43,0.69,"tail.01"),(0.68,0.54,"tail.02"),(0.91,0.40,"tail.03"))):
    curve_tube("Tail molten seam",[(0.0,y-0.07,z+0.04),(0.0,y,z+0.095),(0.0,y+0.07,z+0.04)],0.012,MAT_EMBER,bn)
    cone_between("Tail barb",(0.0,y,z+0.09),(0.0,y+0.10,z+0.19),0.045,MAT_RED,bn,7,0.002)

# Blade fuller and serrated edge details.
curve_tube("Hellblade glowing fuller",[(0.76,-0.19,1.18),(0.76,-0.19,1.42),(0.76,-0.19,1.67),(0.76,-0.19,1.82)],0.018,MAT_EMBER,"sword")
for z in (1.28,1.43,1.58,1.73):
    cone_between("Hellblade serration",(0.64,-0.08,z),(0.58,-0.08,z+0.06),0.035,MAT_GOLD,"sword",6,0.002)


# Fine sculpt pass: facial planes, layered crown, armor fasteners and claw anatomy.
# These details are separate weighted meshes so the same rig drives the complete hero.
for side in (-1, 1):
    suffix = "R" if side > 0 else "L"
    # Brow ridges and cheek guards frame the glowing eyes.
    curve_tube("Infernal brow ridge", [(side*0.035,-0.258,1.91),(side*0.11,-0.278,1.925),(side*0.19,-0.245,1.89)], 0.026, MAT_ARMOR, "head", 4)
    sphere("Demon cheekbone", (side*0.16,-0.205,1.75), (0.085,0.065,0.105), MAT_RED, "head", 20, 14)
    cone_between("Cheek blade", (side*0.18,-0.245,1.75), (side*0.28,-0.22,1.68), 0.055, MAT_GOLD, "head", 12, 0.004)
    # Layered shoulder scales and gold rivets.
    for j in range(3):
        z = 1.57 - j*0.075
        cone_between("Pauldron overlapping scale", (side*(0.34+j*0.035),-0.245,z+0.045),
                     (side*(0.52+j*0.025),-0.22,z-0.035), 0.075, MAT_ARMOR, "chest", 12, 0.018)
    for x in (0.38, 0.49):
        sphere("Gold armor rivet", (side*x,-0.30,1.58), (0.018,0.012,0.018), MAT_GOLD, "chest", 16, 12)
    # Individual hooked finger talons give the gauntlets a more articulated silhouette.
    for j in range(3):
        x = side*(0.65+j*0.065)
        cone_between("Finger claw root", (x,-0.20,0.82), (x,-0.24,0.75), 0.027, MAT_RED, "hand."+suffix, 12, 0.014)
        curve_tube("Curved obsidian claw", [(x,-0.24,0.76),(x,-0.29,0.72),(x,-0.32,0.66)],
                   0.018, MAT_GOLD, "hand."+suffix, 3)
    # Wing spars and small membrane attachment joints.
    for j in range(4):
        x = side*(0.62+j*0.17)
        sphere("Wing knuckle", (x,0.065,1.56+j*0.07), (0.035,0.035,0.04), MAT_GOLD, "wing."+suffix, 16, 12)

# Central facial mask, layered throat gorget and engraved armor studs.
sphere("Nasal bridge", (0,-0.258,1.79), (0.055,0.045,0.105), MAT_RED, "head", 20, 14)
cube("Mouth grille", (0,-0.267,1.675), (0.19,0.045,0.055), MAT_GOLD, "jaw", 0.012)
for x in (-0.055, 0, 0.055):
    cube("Mask vent", (x,-0.294,1.675), (0.012,0.012,0.042), MAT_ARMOR, "jaw", 0.004)
for z in (1.62, 1.56, 1.50):
    curve_tube("Throat gorget edge", [(-0.19,-0.20,z),(0,-0.29,z-0.025),(0.19,-0.20,z)],
               0.018, MAT_GOLD, "chest", 3)
# Additional blade bevel-like edge rails and pommel ornament.
sphere("Hellblade pommel", (0.76,-0.06,0.72), (0.075,0.07,0.075), MAT_GOLD, "sword", 20, 14)
for side in (-1, 1):
    curve_tube("Hellblade edge rail", [(0.76+side*0.095,-0.12,1.18),
               (0.76+side*0.11,-0.12,1.48),(0.76+side*0.075,-0.12,1.78)],
               0.012, MAT_GOLD, "sword", 3)

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
    breath = math.sin(phase * 0.5)
    sway = math.sin(phase * 0.5 + 0.65)
    setrot("pelvis",0,0,0.012*sway)
    setrot("spine",0,0,0.028*sway)
    setrot("chest",0.035*breath,0,0.012*sway)
    setrot("neck",0.012*math.sin(phase+0.3),0,0)
    setrot("head",0,0,0.035*math.sin(phase+0.5))
    setrot("jaw",0,0,0.018*math.sin(phase*1.5+0.4))
    setrot("upper_arm.L",0,0,0.025*math.sin(phase+0.9))
    setrot("upper_arm.R",0,0,-0.025*math.sin(phase+0.9))
    setrot("forearm.L",0,0,0.018*math.sin(phase+1.2))
    setrot("forearm.R",0,0,-0.018*math.sin(phase+1.2))
    setrot("wing.L",0,0,0.12*math.sin(phase*0.5+0.2))
    setrot("wing.R",0,0,-0.12*math.sin(phase*0.5+0.2))
    setrot("tail.01",0.045*math.sin(phase+0.2),0,0)
    setrot("tail.02",0.10*math.sin(phase+0.6),0,0)
    setrot("tail.03",0.14*math.sin(phase+1.0),0,0)
    setrot("tail.tip",0.18*math.sin(phase+1.4),0,0)
    for suffix in ("L", "R"):
        for finger in range(1, 4):
            setrot(f"finger.{finger}.{suffix}",0,0,0.025*math.sin(phase+finger*0.4))
make_action("Idle", [1,16,31], idle_pose)

def run_pose(f):
    reset_pose()
    phase=(f-1)/20*2*math.pi
    setrot("thigh.L",0,0,0.58*math.sin(phase))
    setrot("thigh.R",0,0,0.58*math.sin(phase+math.pi))
    setrot("shin.L",0,0,max(0,-math.sin(phase))*0.65)
    setrot("shin.R",0,0,max(0,-math.sin(phase+math.pi))*0.65)
    setrot("upper_arm.L",0,0,-0.48*math.sin(phase))
    setrot("upper_arm.R",0,0,-0.48*math.sin(phase+math.pi))
    setrot("forearm.L",0,0,0.18*max(0,math.sin(phase)))
    setrot("forearm.R",0,0,0.18*max(0,math.sin(phase+math.pi)))
    setrot("foot.L",0,0,0.08*math.sin(phase+math.pi))
    setrot("foot.R",0,0,0.08*math.sin(phase))
    setrot("wing.L",0,0,0.24*math.sin(phase*2))
    setrot("wing.R",0,0,-0.24*math.sin(phase*2))
    setrot("tail.01",0.12*math.sin(phase+0.4),0,0)
    setrot("tail.02",0.18*math.sin(phase+0.8),0,0)
    setrot("tail.03",0.22*math.sin(phase+1.2),0,0)
    setrot("tail.tip",0.25*math.sin(phase+1.6),0,0)
    setrot("spine",0.06*math.sin(phase*2),0,0)
make_action("Run", [1,6,11,16,21], run_pose)

def walk_pose(f):
    reset_pose()
    phase=(f-1)/24*2*math.pi
    setrot("thigh.L",0,0,0.38*math.sin(phase))
    setrot("thigh.R",0,0,0.38*math.sin(phase+math.pi))
    setrot("shin.L",0,0,max(0,-math.sin(phase))*0.42)
    setrot("shin.R",0,0,max(0,-math.sin(phase+math.pi))*0.42)
    setrot("upper_arm.L",0,0,-0.26*math.sin(phase))
    setrot("upper_arm.R",0,0,-0.26*math.sin(phase+math.pi))
    setrot("chest",0.025*math.sin(phase*2),0,0)
    setrot("wing.L",0,0,0.10*math.sin(phase))
    setrot("wing.R",0,0,-0.10*math.sin(phase))
    setrot("tail.02",0.10*math.sin(phase+0.5),0,0)
    setrot("tail.03",0.14*math.sin(phase+1.0),0,0)
make_action("Walk", [1,7,13,19,25], walk_pose)

def attack_pose(f):
    reset_pose()
    u=(f-1)/18
    swing=math.sin(u*math.pi)
    setrot("upper_arm.R",0,0,-1.15*swing)
    setrot("forearm.R",0,0,-0.55*swing)
    setrot("sword",0,0,-0.85*swing)
    setrot("chest",0,0,0.20*swing)
    setrot("wing.L",0,0,0.18*swing)
    setrot("wing.R",0,0,-0.18*swing)
    setrot("tail.02",0,0.14*swing)
    setrot("tail.03",0,0,0.20*swing)
    setrot("head",0,0,-0.08*swing)
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

def hit_pose(f):
    reset_pose()
    u=(f-1)/12
    recoil=math.sin(u*math.pi)
    setrot("spine",0,0,-0.20*recoil)
    setrot("chest",0,0,-0.16*recoil)
    setrot("head",0,0,0.16*recoil)
    setrot("upper_arm.L",0,0,0.22*recoil)
    setrot("upper_arm.R",0,0,-0.22*recoil)
    setrot("wing.L",0,0,0.20*recoil)
    setrot("wing.R",0,0,-0.20*recoil)
make_action("Hit", [1,4,8,13], hit_pose)

def turn_left_pose(f):
    reset_pose()
    u=(f-1)/16
    weight=math.sin(u*math.pi)
    setrot("pelvis",0,0,0.28*weight)
    setrot("spine",0,0,0.42*weight)
    setrot("chest",0,0,0.22*weight)
    setrot("head",0,0,0.18*weight)
    setrot("tail.02",0,0,-0.22*weight)
    setrot("tail.03",0,0,-0.30*weight)
make_action("TurnLeft", [1,5,9,13,17], turn_left_pose)

def turn_right_pose(f):
    turn_left_pose(f)
    for name in ("pelvis", "spine", "chest", "head", "tail.02", "tail.03"):
        pb=arm.pose.bones.get(name)
        if pb:
            pb.rotation_euler.z *= -1
make_action("TurnRight", [1,5,9,13,17], turn_right_pose)

def stop_pose(f):
    reset_pose()
    u=(f-1)/10
    settle=math.sin(u*math.pi)
    setrot("spine",0,0,-0.08*settle)
    setrot("chest",0.04*settle,0,0)
    setrot("upper_arm.L",0,0,0.08*settle)
    setrot("upper_arm.R",0,0,-0.08*settle)
    setrot("tail.02",0,0,0.16*settle)
    setrot("tail.03",0,0,0.22*settle)
make_action("Stop", [1,4,7,11], stop_pose)

def ultimate_pose(f):
    reset_pose()
    u=(f-1)/30
    rise=math.sin(min(1.0,u)*math.pi*0.5)
    setrot("spine",0,0,-0.18*rise)
    setrot("chest",-0.10*rise,0,0)
    setrot("upper_arm.L",0,0,0.95*rise)
    setrot("upper_arm.R",0,0,-0.95*rise)
    setrot("wing.L",0,0,0.72*rise)
    setrot("wing.R",0,0,-0.72*rise)
    setrot("head",0,0,-0.20*rise)
    setrot("tail.03",0,0,0.24*rise)
make_action("Ultimate", [1,8,16,24,31], ultimate_pose)

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

# Produce the hero-select portrait from the exact shipped model. The portrait
# is rendered separately so the game never needs to render a live 3D preview
# just to show a small roster tile.
THUMB = os.path.join(os.path.dirname(OUT), "zargat.png")
scene = bpy.context.scene
# Blender packages expose different Eevee identifiers across releases.
# Select an engine supported by the installed Blender instead of assuming
# the newer BLENDER_EEVEE_NEXT enum exists.
engine_items = scene.render.bl_rna.properties["engine"].enum_items
available_engines = {item.identifier for item in engine_items}
if "BLENDER_EEVEE_NEXT" in available_engines:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
elif "BLENDER_EEVEE" in available_engines:
    scene.render.engine = "BLENDER_EEVEE"
else:
    scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 640
scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.film_transparent = False
scene.render.filepath = THUMB
scene.view_settings.view_transform = "AgX"
scene.world.color = (0.012, 0.018, 0.032)

# Dark infernal studio backdrop.
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 2.0, 1.2),
                                 rotation=(math.radians(90), 0, 0))
backdrop = bpy.context.object
backdrop.name = "Zargat portrait backdrop"
backdrop_mat = bpy.data.materials.new("Zargat | Midnight studio")
backdrop_mat.diffuse_color = (0.012, 0.022, 0.038, 1)
backdrop_mat.use_nodes = True
backdrop_bsdf = backdrop_mat.node_tree.nodes.get("Principled BSDF")
backdrop_bsdf.inputs["Base Color"].default_value = (0.012, 0.022, 0.038, 1)
backdrop_bsdf.inputs["Roughness"].default_value = 1.0
backdrop.data.materials.append(backdrop_mat)

def area_light(name, location, energy, color, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.color = color
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector((0, 0, 1.25)) - obj.location).to_track_quat("-Z", "Y").to_euler()
    return obj

area_light("Zargat portrait | warm key", (-3.8, -4.5, 5.2), 950, (1.0, 0.42, 0.20), 4.0)
area_light("Zargat portrait | cool fill", (4.2, -3.0, 3.0), 700, (0.22, 0.48, 1.0), 3.5)
area_light("Zargat portrait | ember rim", (0.0, 1.0, 4.4), 1200, (1.0, 0.12, 0.035), 2.5)

camera_data = bpy.data.cameras.new("Zargat portrait camera")
camera = bpy.data.objects.new("Zargat portrait camera", camera_data)
scene.collection.objects.link(camera)
camera.location = (3.0, -7.5, 2.55)
camera.rotation_euler = (Vector((0, 0, 1.22)) - camera.location).to_track_quat("-Z", "Y").to_euler()
camera_data.type = "ORTHO"
camera_data.ortho_scale = 3.8
scene.camera = camera
scene.render.filepath = THUMB
bpy.ops.render.render(write_still=True)
if not os.path.isfile(THUMB) or os.path.getsize(THUMB) < 10000:
    raise RuntimeError("Zargat portrait render failed or produced an unexpectedly small image")
print("Rendered hero-select portrait", THUMB, os.path.getsize(THUMB), "bytes")
