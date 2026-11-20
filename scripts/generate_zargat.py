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

MAT_SKIN = mat("Zargat | Obsidian armor", (0.012, 0.015, 0.022), 0.72, 0.3)
MAT_ARMOR = mat("Zargat | Black forged steel", (0.018, 0.022, 0.032), 0.82, 0.26)
MAT_RED = mat("Zargat | Crimson enamel", (0.30, 0.006, 0.018), 0.58, 0.27)
MAT_GOLD = mat("Zargat | Antique gold trim", (0.52, 0.24, 0.055), 0.82, 0.24)
MAT_EMBER = mat("Zargat | Molten core", (1.0, 0.12, 0.015), 0.0, 0.24, (1.0, 0.045, 0.004))
MAT_WING = mat("Zargat | Infernal wing membrane", (0.19, 0.004, 0.012), 0.18, 0.42)
MAT_HAIR = mat("Zargat | Charred helmet recess", (0.012, 0.014, 0.02), 0.72, 0.3)
MAT_EYE = mat("Zargat | Burning eyes", (1.0, 0.34, 0.018), 0.0, 0.16, (1.0, 0.18, 0.004))


# Layered procedural surface detail: living scaled hide, keratin ridges and molten fissures.
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

add_surface_detail(MAT_SKIN, 13.0, 0.34, 0.18)
add_surface_detail(MAT_ARMOR, 22.0, 0.28, 0.14)
add_surface_detail(MAT_RED, 17.0, 0.30, 0.16)
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


def curve_tube(name, points, radius, material, bone_name, resolution=3):
    # Build a real beveled tube mesh from a polyline, then bind it to the named bone.
    curve = bpy.data.curves.new(name + "_Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 12
    curve.bevel_depth = radius
    curve.bevel_resolution = max(1, int(resolution))
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, co in zip(spline.points, points):
        point.co = (co[0], co[1], co[2], 1.0)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return finish_part(obj, name, material, bone_name)


def wing_mesh(side, suffix):
    # Dense, curved bat membrane with a scalloped trailing edge (not flat triangles).
    # The surface is tessellated so lighting and the membrane normal read smoothly.
    span_steps, chord_steps = 32, 20
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

# Rebuilt from the supplied Zaragat concept: armored demon-knight, not a pile of primitives.
def mesh_part(name, verts, faces, material, bone_name, smooth=False):
    me=bpy.data.meshes.new(name+"_Mesh"); me.from_pydata(verts,[],faces); me.materials.append(material); me.update()
    ob=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(ob)
    if smooth:
        for p in me.polygons: p.use_smooth=True
    return finish_part(ob,name,material,bone_name)

def loft(name, rings, material, bone_name, sides=16):
    verts=[]; faces=[]
    for z,cx,cy,rx,ry in rings:
        for j in range(sides):
            t=2*math.pi*j/sides
            verts.append((cx+rx*math.cos(t),cy+ry*math.sin(t),z))
    for i in range(len(rings)-1):
        for j in range(sides):
            a=i*sides+j; b=i*sides+(j+1)%sides
            faces.append((a,b,b+sides,a+sides))
    faces += [tuple(reversed(range(sides))),tuple((len(rings)-1)*sides+j for j in range(sides))]
    return mesh_part(name,verts,faces,material,bone_name,True)

def plate(name, outline, y, material, bone_name, depth=0.045):
    # Sculpted hard-surface plate, curved to the body, with a raised bevel.
    verts=[(x,y,z) for x,z in outline]+[(x,y+depth,z) for x,z in outline]
    n=len(outline); faces=[tuple(range(n)),tuple(range(n,2*n))]
    for i in range(n): faces.append((i,(i+1)%n,(i+1)%n+n,i+n))
    ob=mesh_part(name,verts,faces,material,bone_name)
    bevel=ob.modifiers.new("Crisp forged plate edges","BEVEL"); bevel.width=0.018; bevel.segments=2
    bpy.context.view_layer.objects.active=ob; bpy.ops.object.modifier_apply(modifier=bevel.name)
    return ob

def blade_mesh(name, points, y_front, y_back, material, bone_name):
    n=len(points); verts=[(x,y_front,z) for x,z in points]+[(x,y_back,z) for x,z in points]
    faces=[tuple(range(n)),tuple(reversed(range(n,2*n)))]
    for i in range(n): faces.append((i,(i+1)%n,(i+1)%n+n,i+n))
    return mesh_part(name,verts,faces,material,bone_name)

# Main body is a single tapered armored silhouette with broad shoulders and narrow waist.
loft("Zargat armored body",[
 (0.78,0,0,0.29,0.23),(0.94,0,0,0.34,0.25),(1.10,0,0,0.30,0.22),
 (1.28,0,0,0.39,0.27),(1.48,0,0,0.53,0.30),(1.62,0,0,0.45,0.25),
 (1.72,0,0,0.23,0.19)],MAT_SKIN,"spine",24)
# Front breastplate: broad angular silhouette, layered crimson panels and gold piping.
plate("Main obsidian breastplate",[(-.43,1.60),(-.34,1.76),(-.12,1.79),(0,1.72),(.12,1.79),(.34,1.76),(.43,1.60),(.29,1.38),(0,1.29),(-.29,1.38)],-.285,MAT_ARMOR,"chest")
plate("Crimson chest inset",[(-.30,1.64),(-.22,1.71),(0,1.67),(.22,1.71),(.30,1.64),(.20,1.48),(0,1.40),(-.20,1.48)],-.338,MAT_RED,"chest",.025)
plate("Central molten crest",[(-.10,1.65),(0,1.72),(.10,1.65),(.075,1.48),(0,1.42),(-.075,1.48)],-.37,MAT_GOLD,"chest",.018)
for side in (-1,1):
    plate("Chest lower lames",[(side*.04,1.36),(side*.25,1.40),(side*.31,1.25),(side*.20,1.16),(side*.03,1.20)],-.30,MAT_ARMOR,"spine")
    curve_tube("Chest magma seam",[(side*.04,-.395,1.61),(side*.13,-.402,1.52),(side*.09,-.39,1.43)],.012,MAT_EMBER,"chest",3)
# Waist, hanging red tabard and hip armor.
plate("Waist cuirass",[(-.30,1.02),(-.25,1.17),(0,1.22),(.25,1.17),(.30,1.02),(.18,.91),(0,.88),(-.18,.91)],-.255,MAT_ARMOR,"pelvis")
for side in (-1,1):
    plate("Hip tasset",[(side*.12,1.02),(side*.31,1.08),(side*.39,.91),(side*.34,.72),(side*.20,.78)],-.29,MAT_RED,"pelvis")
# Cloth panel with pointed hem.
mesh_part("Crimson hanging tabard",[(-.20,-.285,.98),(.20,-.285,.98),(.16,-.31,.57),(0,-.32,.49),(-.16,-.31,.57)],
          [(0,1,2,3,4)],MAT_RED,"pelvis")
# Helmeted head and brow, matching the horned armored silhouette.
loft("Helmet core",[(1.72,0,-.01,.18,.16),(1.82,0,-.015,.25,.20),(1.98,0,0,.27,.21),(2.10,0,.01,.22,.18),(2.15,0,.02,.12,.12)],MAT_ARMOR,"head",20)
plate("Helmet face mask",[(-.20,1.94),(-.16,2.05),(0,2.09),(.16,2.05),(.20,1.94),(.12,1.79),(0,1.74),(-.12,1.79)],-.205,MAT_RED,"head",.035)
plate("Helmet central ridge",[(-.045,2.08),(0,2.13),(.045,2.08),(.035,1.83),(0,1.79),(-.035,1.83)],-.247,MAT_GOLD,"head",.018)
for side in (-1,1):
    # Eye slits burn beneath the angular brow.
    plate("Eye socket",[(side*.035,1.94),(side*.17,1.97),(side*.13,1.91),(side*.045,1.90)],-.252,MAT_ARMOR,"head",.018)
    sphere("Burning eye",(side*.095,-.278,1.93),(.032,.018,.018),MAT_EYE,"head",12,8)
    curve_tube("Swept crown horn",[(side*.16,.0,2.04),(side*.25,.02,2.19),(side*.32,.08,2.36),(side*.27,.16,2.48)],.072,MAT_ARMOR,"head",4)
    curve_tube("Horn molten edge",[(side*.20,-.01,2.13),(side*.27,.04,2.27),(side*.30,.10,2.38)],.012,MAT_GOLD,"head",3)
    plate("Helmet temple guard",[(side*.15,1.98),(side*.25,2.02),(side*.27,1.84),(side*.17,1.75)],-.17,MAT_ARMOR,"head")
# Shoulder pauldrons with layered red shells, gold edging and backward spikes.
for side,suf in [(-1,"L"),(1,"R")]:
    loft("Armored upper arm "+suf,[(.90,side*.70,0,.12,.12),(1.10,side*.62,0,.15,.15),(1.30,side*.49,0,.17,.16),(1.48,side*.40,0,.16,.16)],MAT_SKIN,"upper_arm."+suf,16)
    plate("Massive shoulder pauldron "+suf,[(side*.31,1.70),(side*.50,1.82),(side*.72,1.73),(side*.75,1.57),(side*.58,1.47),(side*.38,1.53)],-.20,MAT_ARMOR,"chest")
    plate("Pauldron crimson inset "+suf,[(side*.39,1.70),(side*.52,1.77),(side*.67,1.70),(side*.62,1.58),(side*.46,1.57)],-.25,MAT_RED,"chest",.02)
    cone_between("Pauldron spike "+suf,(side*.62,-.12,1.68),(side*.89,-.10,1.94),.105,MAT_GOLD,"chest",8,.004)
    loft("Armored forearm "+suf,[(.76,side*.72,-.01,.105,.11),(.92,side*.72,-.01,.14,.13),(1.10,side*.67,0,.16,.15),(1.24,side*.62,0,.13,.13)],MAT_SKIN,"forearm."+suf,16)
    plate("Forearm bracer "+suf,[(side*.56,1.20),(side*.78,1.22),(side*.84,.96),(side*.70,.84),(side*.56,.98)],-.18,MAT_ARMOR,"forearm."+suf)
    plate("Bracer red inlay "+suf,[(side*.61,1.15),(side*.76,1.16),(side*.77,1.02),(side*.68,.95)],-.225,MAT_RED,"forearm."+suf,.018)
    for k in range(3):
        cone_between("Gauntlet claw "+suf,(side*(.66+k*.07),-.22,.88),(side*(.69+k*.07),-.29,.73),.035,MAT_GOLD,"hand."+suf,8,.002)
    # Thigh and greave are long tapered armored forms, not round toy limbs.
    loft("Armored thigh "+suf,[(.48,side*.23,0,.14,.16),(.64,side*.23,0,.18,.19),(.82,side*.21,0,.17,.17),(.94,side*.20,0,.13,.14)],MAT_SKIN,"thigh."+suf,16)
    plate("Thigh armor "+suf,[(side*.09,.82),(side*.34,.86),(side*.39,.66),(side*.30,.52),(side*.13,.57)],-.19,MAT_ARMOR,"thigh."+suf)
    plate("Knee shield "+suf,[(side*.12,.55),(side*.31,.58),(side*.34,.43),(side*.23,.36),(side*.12,.43)],-.22,MAT_RED,"shin."+suf)
    loft("Greave "+suf,[(.12,side*.23,-.02,.10,.12),(.27,side*.23,-.02,.14,.15),(.43,side*.23,0,.13,.15),(.51,side*.23,0,.12,.13)],MAT_SKIN,"shin."+suf,16)
    plate("Greave front "+suf,[(side*.13,.43),(side*.33,.45),(side*.34,.22),(side*.23,.14),(side*.13,.22)],-.18,MAT_ARMOR,"shin."+suf)
    plate("Boot toe "+suf,[(side*.10,.16),(side*.35,.16),(side*.39,.06),(side*.30,.015),(side*.14,.02)],-.25,MAT_RED,"foot."+suf)
# Broad, bat-like wings: red membranes, scalloped lower edge, thick black fingers and gold tips.
def concept_wing(side,suf):
    # Wing spans outward and upward, with five long finger tips and scalloped webbing.
    tips=[(1.48,2.38),(1.28,2.18),(1.45,1.92),(1.30,1.52),(1.02,1.12),(.66,1.18)]
    root=(.37,1.55)
    outline=[root,(.63,1.82),tips[0],tips[1],tips[2],tips[3],tips[4],tips[5],(.42,1.40)]
    verts=[(side*x,.12,z) for x,z in outline]+[(side*x,.16,z) for x,z in outline]
    n=len(outline); faces=[tuple(range(n)),tuple(reversed(range(n,2*n)))]
    for i in range(n): faces.append((i,(i+1)%n,(i+1)%n+n,i+n))
    mesh_part("Infernal bat wing membrane "+suf,verts,faces,MAT_WING,"wing."+suf)
    # Fan ribs reach each horned tip, with a narrow molten channel.
    for j,(x,z) in enumerate(tips[:5]):
        curve_tube("Wing black rib "+suf+str(j),[(side*.40,.08,1.55),(side*(.68+x*.18),.055,1.72),(side*x,.10,z)],.025,MAT_ARMOR,"wing."+suf,3)
        curve_tube("Wing ember vein "+suf+str(j),[(side*.46,.055,1.55),(side*(.72+x*.12),.04,1.69),(side*(x*.96),.10,z*.98)],.008,MAT_EMBER,"wing."+suf,2)
    for x,z in tips[:4]:
        cone_between("Wing claw tip "+suf,(side*x,.10,z),(side*(x+.10),.10,z+.12),.045,MAT_GOLD,"wing."+suf,7,.001)
for side,suf in [(-1,"L"),(1,"R")]: concept_wing(side,suf)
# Segmented spiked tail, sweeping behind the legs.
curve_tube("Armored tail",[(0,.16,.84),(0,.43,.73),(0,.70,.60),(.08,.94,.48),(.20,1.14,.43)],.075,MAT_ARMOR,"tail.01",4)
for i,(x,y,z) in enumerate([(0,.40,.73),(0,.66,.61),(.08,.90,.49)]):
    cone_between("Tail dorsal spike "+str(i),(x,y,z+.04),(x+.03,y+.10,z+.18),.055,MAT_GOLD,"tail."+("01" if i==0 else "02" if i==1 else "03"),8,.002)
cone_between("Tail blade tip",(.20,1.12,.43),(.34,1.34,.42),.095,MAT_RED,"tail.tip",8,.002)
# Huge broad greatsword held on the right, matching the reference diagonal silhouette.
cube("Greatsword grip",(.76,-.08,.91),(.075,.075,.30),MAT_ARMOR,"sword",.012)
cube("Greatsword crossguard",(.76,-.10,1.08),(.40,.10,.075),MAT_GOLD,"sword",.018)
blade_mesh("Broad infernal greatsword",[(.76,1.10),(.58,1.34),(.53,1.68),(.64,1.94),(.76,2.03),(.88,1.94),(.99,1.68),(.94,1.34)],-.17,-.08,MAT_RED,"sword")
curve_tube("Sword molten fuller",[(.76,-.19,1.18),(.76,-.20,1.48),(.76,-.19,1.78),(.76,-.15,1.98)],.022,MAT_EMBER,"sword",4)
for side in (-1,1):
    curve_tube("Sword gold edge "+str(side),[(.76+side*.12,-.18,1.30),(.76+side*.20,-.16,1.66),(.76+side*.12,-.15,1.91)],.012,MAT_GOLD,"sword",3)

bpy.ops.object.select_all(action="DESELECT")
for obj in parts: obj.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
bpy.ops.object.join()
body=bpy.context.object
body.name="Zargat_Skinned_Mesh"
body.parent=arm
body["character_id"]="zargat"
body["rig_type"]="independent_modular_armature"
POLYGON_BUDGET = 245000
current_polys = len(body.data.polygons)
if current_polys > POLYGON_BUDGET:
    decimate = body.modifiers.new("Mobile polygon budget", "DECIMATE")
    decimate.ratio = POLYGON_BUDGET / float(current_polys)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.modifier_apply(modifier=decimate.name)
final_polys = len(body.data.polygons)
if final_polys > 300000:
    raise RuntimeError(f"Zargat mesh exceeds 300k polygon limit: {final_polys}")
body["polygon_count"] = final_polys
print("Zargat polygon count", final_polys)

# Global hero scale: add the requested final 5% (19% previous increase + 5% = 24% total target).
arm.scale = (1.05, 1.05, 1.05)

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
            if pb.name == "pelvis":
                pb.keyframe_insert(data_path="location",frame=frame,group=pb.name)
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

def setloc(name, x=0, y=0, z=0):
    pb=arm.pose.bones.get(name)
    if pb:
        pb.location=(x,y,z)

def reset_pose():
    for pb in arm.pose.bones:
        pb.rotation_mode="XYZ"
        pb.rotation_euler=(0,0,0)
        pb.location=(0,0,0)

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
    left=math.sin(phase)
    right=math.sin(phase+math.pi)
    # Alternating stride, bent-knee recovery and a counter-swinging upper body.
    setrot("thigh.L",0,0,0.66*left)
    setrot("thigh.R",0,0,0.66*right)
    setrot("shin.L",0,0,max(0,-left)*0.82)
    setrot("shin.R",0,0,max(0,-right)*0.82)
    setrot("foot.L",0,0,-0.16*max(0,left))
    setrot("foot.R",0,0,-0.16*max(0,right))
    setrot("upper_arm.L",0,0,-0.54*left)
    setrot("upper_arm.R",0,0,-0.54*right)
    setrot("forearm.L",0,0,0.22*max(0,left))
    setrot("forearm.R",0,0,0.22*max(0,right))
    setrot("pelvis",0,0,0.045*math.sin(phase))
    setrot("spine",0.075*math.sin(phase*2),0, -0.035*math.sin(phase))
    setrot("chest",-0.035*math.sin(phase*2),0,0.025*math.sin(phase))
    setrot("head",0,0,-0.018*math.sin(phase))
    setloc("pelvis",0,0,0.045*(1-math.cos(phase*2)))
    setrot("wing.L",0,0,0.25*math.sin(phase*2))
    setrot("wing.R",0,0,-0.25*math.sin(phase*2))
    setrot("tail.01",0.12*math.sin(phase+0.4),0,0)
    setrot("tail.02",0.18*math.sin(phase+0.8),0,0)
    setrot("tail.03",0.22*math.sin(phase+1.2),0,0)
    setrot("tail.tip",0.27*math.sin(phase+1.6),0,0)
make_action("Run", [1,6,11,16,21], run_pose)

def walk_pose(f):
    reset_pose()
    phase=(f-1)/24*2*math.pi
    left=math.sin(phase)
    right=math.sin(phase+math.pi)
    setrot("thigh.L",0,0,0.43*left)
    setrot("thigh.R",0,0,0.43*right)
    setrot("shin.L",0,0,max(0,-left)*0.50)
    setrot("shin.R",0,0,max(0,-right)*0.50)
    setrot("foot.L",0,0,-0.10*max(0,left))
    setrot("foot.R",0,0,-0.10*max(0,right))
    setrot("upper_arm.L",0,0,-0.32*left)
    setrot("upper_arm.R",0,0,-0.32*right)
    setrot("forearm.L",0,0,0.10*max(0,left))
    setrot("forearm.R",0,0,0.10*max(0,right))
    setrot("pelvis",0,0,0.035*math.sin(phase))
    setrot("spine",0.035*math.sin(phase*2),0,-0.025*math.sin(phase))
    setrot("chest",-0.018*math.sin(phase*2),0,0.02*math.sin(phase))
    setrot("head",0,0,-0.012*math.sin(phase))
    setloc("pelvis",0,0,0.025*(1-math.cos(phase*2)))
    setrot("wing.L",0,0,0.12*math.sin(phase))
    setrot("wing.R",0,0,-0.12*math.sin(phase))
    setrot("tail.01",0.06*math.sin(phase+0.3),0,0)
    setrot("tail.02",0.10*math.sin(phase+0.6),0,0)
    setrot("tail.03",0.14*math.sin(phase+1.0),0,0)
    setrot("tail.tip",0.18*math.sin(phase+1.4),0,0)
make_action("Walk", [1,7,13,19,25], walk_pose)

def attack_pose(f):
    reset_pose()
    # Four readable phases: anticipation, committed slash, follow-through, recovery.
    u=(f-1)/26.0
    if u < 0.28:
        p=math.sin((u/0.28)*math.pi*0.5)
        setrot("pelvis",0,0,-0.22*p)
        setrot("spine",0.10*p,0,-0.32*p)
        setrot("chest",0.16*p,0,-0.42*p)
        setrot("upper_arm.R",0,0,-1.18*p)
        setrot("forearm.R",0,0,-0.72*p)
        setrot("sword",0,0,-0.95*p)
        setrot("upper_arm.L",0,0,0.28*p)
        setrot("wing.L",0,0,0.16*p)
        setrot("wing.R",0,0,-0.16*p)
        setrot("tail.02",0,0,0.12*p)
        setrot("tail.03",0,0,0.20*p)
    elif u < 0.62:
        p=math.sin(((u-0.28)/0.34)*math.pi*0.5)
        setrot("pelvis",0,0,-0.22+0.62*p)
        setrot("spine",-0.12*p,0,0.30*p)
        setrot("chest",-0.18*p,0,0.62*p)
        setrot("upper_arm.R",0,0,-1.18+1.78*p)
        setrot("forearm.R",0,0,-0.72+1.20*p)
        setrot("sword",0,0,-0.95+1.65*p)
        setrot("upper_arm.L",0,0,0.28-0.48*p)
        setrot("wing.L",0,0,0.16+0.14*p)
        setrot("wing.R",0,0,-0.16-0.14*p)
        setrot("tail.02",0,0,0.12+0.16*p)
        setrot("tail.03",0,0,0.20+0.20*p)
        setrot("head",0,0,-0.10*p)
    else:
        p=1.0-(u-0.62)/0.38
        setrot("pelvis",0,0,0.40*p)
        setrot("spine",0,0,-0.12*p)
        setrot("chest",0,0,-0.18*p)
        setrot("upper_arm.R",0,0,0.60*p)
        setrot("forearm.R",0,0,0.48*p)
        setrot("sword",0,0,0.70*p)
        setrot("upper_arm.L",0,0,-0.20*p)
        setrot("wing.L",0,0,0.30*p)
        setrot("wing.R",0,0,-0.30*p)
        setrot("tail.02",0,0,0.28*p)
        setrot("tail.03",0,0,0.32*p)
        setrot("head",0,0,-0.10*p)
make_action("Attack", [1,4,8,12,17,22,27], attack_pose)

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

area_light("Zargat portrait | warm key", (-3.8, -4.5, 5.2), 650, (1.0, 0.24, 0.10), 4.0)
area_light("Zargat portrait | cool fill", (4.2, -3.0, 3.0), 360, (0.12, 0.24, 0.55), 3.5)
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
