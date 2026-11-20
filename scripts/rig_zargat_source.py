#!/usr/bin/env python3
"""Rig the user-supplied Zaragat GLB without replacing its source geometry."""
import bpy, math, os
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "client", "assets", "avatars", "demon knight 3d model.glb")
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

# Build the user's DemonKnight bone layout in mesh-local coordinates.
# The armature object stays at the origin: this avoids the double X/Y offset
# present in the pasted script's armature_add(location=(center_x, center_y, 0)).
verts = [v.co.copy() for v in body.data.vertices]
xmin,xmax=min(v.x for v in verts),max(v.x for v in verts)
ymin,ymax=min(v.y for v in verts),max(v.y for v in verts)
zmin,zmax=min(v.z for v in verts),max(v.z for v in verts)
height=max(0.01,zmax-zmin)
center_x=(xmin+xmax)*0.5
center_y=(ymin+ymax)*0.5
def z_at(t):
    return zmin + height*t

ad=bpy.data.armatures.new("DemonKnight_Armature")
rig=bpy.data.objects.new("DemonKnight_Rig",ad)
bpy.context.collection.objects.link(rig)
rig.location=(0,0,0); rig.rotation_euler=(0,0,0); rig.scale=(1,1,1)
bpy.context.view_layer.objects.active=rig
rig.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb={}
def add(name,head,tail,parent=None,connect=False):
    bone=ad.edit_bones.new(name)
    bone.head=Vector(head); bone.tail=Vector(tail)
    if parent:
        bone.parent=eb[parent]
        bone.use_connect=connect
    eb[name]=bone
    return bone
add("Root",(center_x,center_y,zmin),(center_x,center_y,zmin+height*.08))
pelvis=add("Pelvis",(center_x,center_y,z_at(.50)),(center_x,center_y,z_at(.56)),"Root")
spine1=add("Spine_01",pelvis.tail,(center_x,center_y,z_at(.65)),"Pelvis",True)
spine2=add("Spine_02",spine1.tail,(center_x,center_y,z_at(.76)),"Spine_01",True)
neck=add("Neck",spine2.tail,(center_x,center_y,z_at(.83)),"Spine_02",True)
add("Head",neck.tail,(center_x,center_y,z_at(.96)),"Neck",True)
for side,sign in [("L",1.0),("R",-1.0)]:
    hip=add(f"Thigh_{side}",(center_x+sign*height*.08,center_y,z_at(.50)),
            (center_x+sign*height*.09,center_y,z_at(.27)),"Pelvis")
    shin=add(f"Shin_{side}",hip.tail,
             (center_x+sign*height*.09,center_y-height*.02,z_at(.07)),f"Thigh_{side}",True)
    add(f"Foot_{side}",shin.tail,
        (center_x+sign*height*.09,center_y-height*.11,z_at(.01)),f"Shin_{side}",True)
    clav=add(f"Clavicle_{side}",(center_x+sign*height*.04,center_y,z_at(.75)),
             (center_x+sign*height*.14,center_y,z_at(.74)),"Spine_02")
    upper=add(f"UpperArm_{side}",clav.tail,
              (center_x+sign*height*.28,center_y,z_at(.57)),f"Clavicle_{side}",True)
    fore=add(f"Forearm_{side}",upper.tail,
             (center_x+sign*height*.36,center_y-height*.05,z_at(.41)),f"UpperArm_{side}",True)
    add(f"Hand_{side}",fore.tail,
        (center_x+sign*height*.40,center_y-height*.09,z_at(.34)),f"Forearm_{side}",True)
tail_prev="Pelvis"
tail_steps=[(.48,.12),(.43,.26),(.36,.40),(.28,.52)]
for idx,(zt,yd) in enumerate(tail_steps,1):
    head=(center_x,center_y+height*.04,z_at(.50)) if idx==1 else eb[tail_prev].tail
    name=f"Tail_{idx:02d}"
    add(name,head,(center_x,center_y+height*yd,z_at(zt)),tail_prev,idx>1)
    tail_prev=name
for side,sign in [("L",1.0),("R",-1.0)]:
    root=add(f"Wing_Root_{side}",(center_x+sign*height*.07,center_y+height*.03,z_at(.73)),
             (center_x+sign*height*.35,center_y+height*.06,z_at(.86)),"Spine_02")
    mid=add(f"Wing_Mid_{side}",root.tail,
            (center_x+sign*height*.62,center_y+height*.08,z_at(.78)),f"Wing_Root_{side}",True)
    add(f"Wing_Tip_{side}",mid.tail,
        (center_x+sign*height*.78,center_y+height*.10,z_at(.64)),f"Wing_Mid_{side}",True)
bpy.ops.object.mode_set(mode="OBJECT")

# Try Blender's automatic heat-based weights first. If the fused source mesh
# cannot be solved by Blender, fall back to smooth nearest-bone weights.
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True); rig.select_set(True)
bpy.context.view_layer.objects.active=rig
auto_ok=False
try:
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    auto_ok=bool(body.parent==rig and len(body.vertex_groups)>0)
except Exception as exc:
    print("Automatic weights unavailable; using fallback:",exc)
if not auto_ok:
    for mod in list(body.modifiers):
        if mod.type=="ARMATURE": body.modifiers.remove(mod)
    body.parent=None
    for group in list(body.vertex_groups):
        body.vertex_groups.remove(group)
    bone_points={name:(bone.head_local+bone.tail_local)*.5 for name,bone in ad.bones.items()}
    groups={name:body.vertex_groups.new(name=name) for name in bone_points}
    for i,v in enumerate(body.data.vertices):
        ranked=sorted(((v.co-p).length,name) for name,p in bone_points.items())
        first,second=ranked[:2]
        d0=max(first[0],.0001); d1=max(second[0],.0001)
        groups[first[1]].add([i],d1/(d0+d1),"REPLACE")
        groups[second[1]].add([i],d0/(d0+d1),"REPLACE")
    body.parent=rig
    mod=body.modifiers.new("DemonKnight_Armature","ARMATURE")
    mod.object=rig
# Ensure the armature modifier is present and points at the new rig.
if not any(m.type=="ARMATURE" and m.object==rig for m in body.modifiers):
    mod=body.modifiers.new("DemonKnight_Armature","ARMATURE"); mod.object=rig
body["character_id"]="zargat"
body["rig_source"]="DemonKnight custom bone layout"
rig.show_in_front=True
ad.display_type="OCTAHEDRAL"

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
            if p.name=="Pelvis": p.keyframe_insert(data_path="location",frame=f,group=p.name)
    rig.animation_data.action=None
    track=rig.animation_data.nla_tracks.new(); track.name=name
    strip=track.strips.new(name,frames[0],act); strip.name=name; strip.blend_type="REPLACE"
def idle(f):
    t=(f-1)/30*math.tau
    rot("Spine_01",.025*math.sin(t)); rot("Spine_02",.025*math.sin(t+.4),.025*math.sin(t/2))
    rot("Head",.025*math.sin(t+.8))
    for suf,s in [("L",1),("R",-1)]:
        rot("Wing_Root_"+suf,s*.10*math.sin(t/2))
    for n,k in [("Tail_01",.08),("Tail_02",.12),("Tail_03",.16),("Tail_04",.18)]:
        rot(n,k*math.sin(t+.6))
def locomotion(f,amount):
    t=(f-1)/24*math.tau
    for suf,phase in [("L",0),("R",math.pi)]:
        a=math.sin(t+phase)
        rot("Thigh_"+suf,.55*amount*a); rot("Shin_"+suf,.45*amount*max(0,-a))
        rot("UpperArm_"+suf,-.30*amount*a)
    rot("Spine_01",.04*amount*math.sin(2*t)); rot("Spine_02",.025*amount*math.sin(2*t+1))
    for suf,s in [("L",1),("R",-1)]: rot("wing."+suf,s*.12*amount*math.sin(2*t))
    for n,k in [("Tail_01",.08),("Tail_02",.12),("Tail_03",.16),("Tail_04",.20)]:
        rot(n,k*math.sin(t+.5))
def attack(f):
    t=(f-1)/26
    power=math.sin(min(1,max(0,t))*math.pi)
    rot("Spine_01",-.22*power); rot("Spine_02",-.35*power)
    rot("UpperArm_R",-.9*power); rot("Forearm_R",-.7*power)
    rot("Wing_Root_L",.2*power); rot("Wing_Root_R",-.2*power)
def cast(f):
    p=math.sin((f-1)/24*math.pi)
    rot("UpperArm_L",.65*p); rot("UpperArm_R",-.65*p)
    rot("Wing_Root_L",.35*p); rot("Wing_Root_R",-.35*p)
def death(f):
    p=(f-1)/30
    rot("Spine_01",.65*p); rot("Head",-.3*p); rot("Wing_Root_L",.45*p); rot("Wing_Root_R",-.45*p)
def hit(f):
    p=math.sin((f-1)/12*math.pi)
    rot("Spine_01",-.2*p); rot("Spine_02",-.15*p); rot("Head",.12*p)
def turn(f,sign):
    p=math.sin((f-1)/16*math.pi)
    rot("Pelvis",sign*.24*p); rot("Spine_01",sign*.35*p); rot("Head",sign*.12*p)
def stop(f):
    p=math.sin((f-1)/10*math.pi)
    rot("Spine_01",-.08*p); rot("Tail_02",.14*p); rot("Tail_03",.18*p)
def ultimate(f):
    p=math.sin((f-1)/30*math.pi/2)
    rot("UpperArm_L",.8*p); rot("UpperArm_R",-.8*p)
    rot("Wing_Root_L",.7*p); rot("Wing_Root_R",-.7*p); rot("Spine_02",-.1*p)
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
