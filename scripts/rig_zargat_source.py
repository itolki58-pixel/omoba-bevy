#!/usr/bin/env python3
"""Rig the user-supplied Zaragat GLB without replacing its source geometry."""
import bpy, math, os
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "art", "zargat", "demon-knight-source.glb")
OUT = os.path.join(ROOT, "client", "assets", "avatars", "zargat.glb")
PNG = os.path.join(ROOT, "client", "assets", "avatars", "zargat.png")
if not os.path.isfile(SRC):
    raise RuntimeError("Missing user model: " + SRC)

bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=SRC)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not meshes: raise RuntimeError("Source GLB contains no mesh")
# Preserve the imported mesh/materials; join only mesh objects so the exported
# avatar remains a single character asset while retaining original geometry.
bpy.ops.object.select_all(action="DESELECT")
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.join()
body = bpy.context.object
body.name = "Zargat_SourceMesh"
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
# Normalize the model around its ground contact and centerline. Blender's glTF
# importer converts glTF Y-up into Blender Z-up.
coords = [body.matrix_world @ v.co for v in body.data.vertices]
mins = Vector(tuple(min(v[i] for v in coords) for i in range(3)))
maxs = Vector(tuple(max(v[i] for v in coords) for i in range(3)))
center = (mins + maxs) * 0.5
height = maxs.z - mins.z
if height < 0.05: raise RuntimeError("Imported model has no usable vertical extent")
scale = 2.35 / height
for v in body.data.vertices:
    v.co = (v.co - center) * scale
    v.co.z += 1.175
body.data.update()

# Reduce mobile texture memory while preserving the authored skin.
# Base colour is JPEG; normal and packed metallic/roughness maps stay lossless.
for image in bpy.data.images:
    if not image.has_data:
        continue
    width, height = map(int, image.size)
    if width <= 0 or height <= 0:
        continue
    largest = max(width, height)
    if largest > 2048:
        factor = 2048.0 / largest
        image.scale(max(1, round(width * factor)), max(1, round(height * factor)))
    image.file_format = "PNG" if any(
        token in image.name.lower() for token in ("normal", "roughness", "metallic", "_rm")
    ) else "JPEG"
    image.pack()
    if max(map(int, image.size)) > 2048:
        raise RuntimeError("Zargat texture was not reduced to the mobile 2K limit: " + image.name)
    print("Zargat texture prepared:", image.name, tuple(map(int, image.size)), image.file_format)

# Keep the supplied painted base-colour texture intact. The source atlas already
# contains the red plates and dark forged-metal regions; multiplying it by a
# luminance-derived red/orange tint flattened every surface into plastic.
# Use a neutral shader multiplier so the authored texture remains visible.
for material in bpy.data.materials:
    if not material.use_nodes:
        material.use_nodes = True
    bsdf = next((n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        continue
    base = bsdf.inputs.get("Base Color")
    if base:
        base.default_value = (1.0, 1.0, 1.0, 1.0)
    metallic = bsdf.inputs.get("Metallic")
    rough = bsdf.inputs.get("Roughness")
    if metallic:
        metallic.default_value = 0.72
    if rough:
        rough.default_value = 0.48
    # No broad orange emission: only the painted red/orange texture should glow
    # under the warm rim light, leaving the black steel dark and readable.
    emission = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
    strength = bsdf.inputs.get("Emission Strength")
    if emission:
        emission.default_value = (0.0, 0.0, 0.0, 1.0)
    if strength:
        strength.default_value = 0.0

# Bounds after normalization.
verts = [v.co.copy() for v in body.data.vertices]
xmin,xmax=min(v.x for v in verts),max(v.x for v in verts)
ymin,ymax=min(v.y for v in verts),max(v.y for v in verts)
zmin,zmax=min(v.z for v in verts),max(v.z for v in verts)
width=max(0.2,xmax-xmin); depth=max(0.2,ymax-ymin)
cx=(xmin+xmax)*0.5; cy=(ymin+ymax)*0.5

ad = bpy.data.armatures.new("Zargat_Armature")
rig = bpy.data.objects.new("Zargat_Rig", ad)
bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig; rig.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb={}
def add(name, head, tail, parent=None):
    b=ad.edit_bones.new(name); b.head=head; b.tail=tail
    if parent: b.parent=eb[parent]
    eb[name]=b
# Human-like skeleton with separate wing and tail controls.
add("root",(cx,cy,0),(cx,cy,.22))
add("pelvis",(cx,cy,.78),(cx,cy,1.02),"root")
add("spine",(cx,cy,1.02),(cx,cy,1.38),"pelvis")
add("chest",(cx,cy,1.38),(cx,cy,1.62),"spine")
add("neck",(cx,cy,1.62),(cx,cy,1.78),"chest")
add("head",(cx,cy,1.78),(cx,cy,2.08),"neck")
add("jaw",(cx,cy-.05,1.78),(cx,cy-.08,1.68),"head")
for s,suf in [(-1,"L"),(1,"R")]:
    x=cx+s*width*.20
    add("upper_arm."+suf,(x,cy,1.52),(cx+s*width*.39,cy,1.20),"chest")
    add("forearm."+suf,(cx+s*width*.39,cy,1.20),(cx+s*width*.43,cy,.91),"upper_arm."+suf)
    add("hand."+suf,(cx+s*width*.43,cy,.91),(cx+s*width*.44,cy,.76),"forearm."+suf)
    for n in range(1,4):
        xx=cx+s*width*(.40+n*.018)
        add(f"finger.{n}.{suf}",(xx,cy-.025,.78),(xx,cy-.08,.69),"hand."+suf)
    add("thigh."+suf,(cx+s*width*.12,cy,.86),(cx+s*width*.14,cy,.49),"pelvis")
    add("shin."+suf,(cx+s*width*.14,cy,.49),(cx+s*width*.14,cy,.14),"thigh."+suf)
    add("foot."+suf,(cx+s*width*.14,cy,.14),(cx+s*width*.14,cy-.20,.07),"shin."+suf)
    add("wing."+suf,(cx+s*width*.18,cy+.02,1.55),(cx+s*width*.52,cy+.04,1.90),"chest")
add("tail.01",(cx,cy+.08,.85),(cx,cy+depth*.16,.72),"pelvis")
add("tail.02",(cx,cy+depth*.16,.72),(cx,cy+depth*.30,.58),"tail.01")
add("tail.03",(cx,cy+depth*.30,.58),(cx,cy+depth*.43,.45),"tail.02")
add("tail.tip",(cx,cy+depth*.43,.45),(cx,cy+depth*.50,.38),"tail.03")
add("sword",(cx+width*.42,cy,.88),(cx+width*.44,cy,1.48),"hand.R")
bpy.ops.object.mode_set(mode="OBJECT")

# Spatial skinning: blend the two closest anatomical control points. The
# original fused surface/materials remain intact; no procedural replacement.
bone_points={name:Vector((b.head_local+b.tail_local)*.5) for name,b in ad.bones.items()}
groups={name:body.vertex_groups.new(name=name) for name in bone_points}
for i,v in enumerate(body.data.vertices):
    p=v.co
    # Keep torso/helmet vertices anchored to their nearest central controls;
    # limb and wing vertices naturally select their nearest limb controls.
    ranked=sorted(((p-bp).length,name) for name,bp in bone_points.items())
    chosen=ranked[:2]
    d0=max(chosen[0][0],.0001); d1=max(chosen[1][0],.0001)
    w0=d1/(d0+d1); w1=d0/(d0+d1)
    groups[chosen[0][1]].add([i],w0,"REPLACE")
    groups[chosen[1][1]].add([i],w1,"REPLACE")
mod=body.modifiers.new("Zargat skeletal deformation","ARMATURE"); mod.object=rig
body.parent=rig
body["character_id"]="zargat"; body["source_asset"]="demon knight 3d model.glb"
rig.show_in_front=True; ad.display_type="OCTAHEDRAL"

def reset():
    for p in rig.pose.bones:
        p.rotation_mode="XYZ"; p.rotation_euler=(0,0,0); p.location=(0,0,0)
def rot(n,z=0,x=0):
    p=rig.pose.bones.get(n)
    if p: p.rotation_euler=(x,0,z)
def clip(name, frames, fn):
    act=bpy.data.actions.new(name); rig.animation_data_create(); rig.animation_data.action=act
    for f in frames:
        bpy.context.scene.frame_set(f); reset(); fn(f)
        for p in rig.pose.bones:
            p.keyframe_insert(data_path="rotation_euler",frame=f,group=p.name)
            if p.name=="pelvis": p.keyframe_insert(data_path="location",frame=f,group=p.name)
    rig.animation_data.action=None
    track=rig.animation_data.nla_tracks.new(); track.name=name
    strip=track.strips.new(name,frames[0],act); strip.name=name; strip.blend_type="REPLACE"
def idle(f):
    t=(f-1)/30*math.tau
    rot("spine",.025*math.sin(t)); rot("chest",.025*math.sin(t+.4),.025*math.sin(t/2))
    rot("head",.025*math.sin(t+.8))
    for suf,s in [("L",1),("R",-1)]:
        rot("wing."+suf,s*.10*math.sin(t/2))
    for n,k in [("tail.01",.08),("tail.02",.12),("tail.03",.16),("tail.tip",.18)]:
        rot(n,k*math.sin(t+.6))
def locomotion(f,amount):
    t=(f-1)/24*math.tau
    for suf,phase in [("L",0),("R",math.pi)]:
        a=math.sin(t+phase)
        rot("thigh."+suf,.55*amount*a); rot("shin."+suf,.45*amount*max(0,-a))
        rot("upper_arm."+suf,-.30*amount*a)
    rot("spine",.04*amount*math.sin(2*t)); rot("chest",.025*amount*math.sin(2*t+1))
    for suf,s in [("L",1),("R",-1)]: rot("wing."+suf,s*.12*amount*math.sin(2*t))
    for n,k in [("tail.01",.08),("tail.02",.12),("tail.03",.16),("tail.tip",.20)]:
        rot(n,k*math.sin(t+.5))
def attack(f):
    t=(f-1)/26
    power=math.sin(min(1,max(0,t))*math.pi)
    rot("spine",-.22*power); rot("chest",-.35*power)
    rot("upper_arm.R",-.9*power); rot("forearm.R",-.7*power); rot("sword",-.8*power)
    rot("wing.L",.2*power); rot("wing.R",-.2*power)
def cast(f):
    p=math.sin((f-1)/24*math.pi)
    rot("upper_arm.L",.65*p); rot("upper_arm.R",-.65*p)
    rot("wing.L",.35*p); rot("wing.R",-.35*p)
def death(f):
    p=(f-1)/30
    rot("spine",.65*p); rot("head",-.3*p); rot("wing.L",.45*p); rot("wing.R",-.45*p)
def hit(f):
    p=math.sin((f-1)/12*math.pi)
    rot("spine",-.2*p); rot("chest",-.15*p); rot("head",.12*p)
def turn(f,sign):
    p=math.sin((f-1)/16*math.pi)
    rot("pelvis",sign*.24*p); rot("spine",sign*.35*p); rot("head",sign*.12*p)
def stop(f):
    p=math.sin((f-1)/10*math.pi)
    rot("spine",-.08*p); rot("tail.02",.14*p); rot("tail.03",.18*p)
def ultimate(f):
    p=math.sin((f-1)/30*math.pi/2)
    rot("upper_arm.L",.8*p); rot("upper_arm.R",-.8*p)
    rot("wing.L",.7*p); rot("wing.R",-.7*p); rot("chest",-.1*p)
clip("Idle",[1,16,31],idle)
clip("Run",[1,6,11,16,21],lambda f:locomotion(f,1.0))
clip("Walk",[1,7,13,19,25],lambda f:locomotion(f,.65))
clip("Attack",[1,4,8,12,17,22,27],attack)
clip("Cast",[1,8,16,25],cast)
clip("Death",[1,10,20,31],death)
clip("Hit",[1,4,8,13],hit)
clip("TurnLeft",[1,5,9,13,17],lambda f:turn(f,1))
clip("TurnRight",[1,5,9,13,17],lambda f:turn(f,-1))
clip("Stop",[1,4,7,11],stop)
clip("Ultimate",[1,8,16,24,31],ultimate)
bpy.context.scene.frame_set(1)

os.makedirs(os.path.dirname(OUT),exist_ok=True)
bpy.ops.object.select_all(action="DESELECT"); body.select_set(True); rig.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=OUT,export_format="GLB",use_selection=True,
    export_apply=True,export_animations=True,export_nla_strips=True,export_skins=True,export_yup=True)
if not os.path.isfile(OUT) or os.path.getsize(OUT)<100000: raise RuntimeError("Rigged Zaragat export failed")
# Render a true Blender preview of the supplied model.
scene=bpy.context.scene
engines={x.identifier for x in scene.render.bl_rna.properties["engine"].enum_items}
scene.render.engine="BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else ("BLENDER_EEVEE" if "BLENDER_EEVEE" in engines else "BLENDER_WORKBENCH")
scene.render.resolution_x=768; scene.render.resolution_y=768; scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"; scene.render.image_settings.color_mode="RGBA"
scene.render.film_transparent=False; scene.world.color=(.012,.018,.032)
def light(name,loc,power,color,size):
    d=bpy.data.lights.new(name,"AREA"); d.energy=power; d.color=color; d.shape="DISK"; d.size=size
    o=bpy.data.objects.new(name,d); scene.collection.objects.link(o); o.location=loc
    o.rotation_euler=(Vector((cx,cy,1.2))-o.location).to_track_quat("-Z","Y").to_euler()
light("Key", (cx-3,cy-4,4),850,(1.0,.92,.84),4)
light("Fill",(cx+3,cy-3,2.5),320,(.42,.52,.78),3)
light("Rim",(cx,cy+2,3.5),520,(1.0,.16,.055),2)
camd=bpy.data.cameras.new("Zargat_Camera"); cam=bpy.data.objects.new("Zargat_Camera",camd); scene.collection.objects.link(cam)
cam.location=(cx+2.8,cy-6,2.7); cam.rotation_euler=(Vector((cx,cy,1.2))-cam.location).to_track_quat("-Z","Y").to_euler()
camd.type="ORTHO"; camd.ortho_scale=max(width,depth,2.6)*1.45; scene.camera=cam
scene.render.filepath=PNG; bpy.ops.render.render(write_still=True)
if not os.path.isfile(PNG) or os.path.getsize(PNG)<10000: raise RuntimeError("Blender preview render failed")
print("Zargat source rig complete",os.path.getsize(OUT),"bytes; portrait",os.path.getsize(PNG))
