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

# The uploaded sculpt has ~225k vertices. Reduce it before skinning so the
# mobile client draws a compact mesh while retaining UVs, materials and shape.
decimate = body.modifiers.new("Zargat_Mobile_Decimate", "DECIMATE")
decimate.decimate_type = "COLLAPSE"
decimate.ratio = 0.35
bpy.context.view_layer.objects.active = body
bpy.ops.object.modifier_apply(modifier=decimate.name)
print("Zargat mobile mesh:", len(body.data.vertices), "vertices")
if len(body.data.vertices) > 100000:
    raise RuntimeError("Zargat mesh exceeds the 100k mobile vertex budget")

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
# The supplied mesh is authored toward +Z after glTF Y-up conversion; OMOBA
# characters face -Z. Keep this correction on the rig root so every clip agrees.
rig.rotation_mode = "XYZ"
rig.rotation_euler.z = math.pi
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

def assign_chain(vertex_index, point, candidates):
    # Blend only within one anatomical chain: wings cannot pull the torso,
    # tail, arms or legs; left/right limbs cannot deform one another.
    ranked=sorted(((point-bone_points[name]).length,name)
                  for name in candidates if name in bone_points)
    if not ranked:
        ranked=sorted(((point-bone_points[name]).length,name)
                      for name in ("root","pelvis","spine","chest") if name in bone_points)
    if len(ranked)==1:
        groups[ranked[0][1]].add([vertex_index],1.0,"REPLACE")
        return
    d0=max(ranked[0][0],.0001); d1=max(ranked[1][0],.0001)
    total=d0+d1
    groups[ranked[0][1]].add([vertex_index],d1/total,"REPLACE")
    groups[ranked[1][1]].add([vertex_index],d0/total,"REPLACE")

for i,v in enumerate(body.data.vertices):
    p=v.co
    dx=p.x-cx
    side="L" if dx < 0 else "R"
    lateral=abs(dx)
    rear=p.y > cy+depth*.08
    # Tail: back-facing, low central vertices follow only the tail chain.
    if p.y > cy+depth*.16 and p.z < 1.05 and lateral < width*.34:
        assign_chain(i,p,["tail.01","tail.02","tail.03","tail.tip"])
    # Wings: elevated rear/outer geometry follows its own side's wing pivot.
    elif rear and p.z > 1.12 and lateral > width*.16:
        assign_chain(i,p,["wing."+side])
    # Legs: each side is restricted to its own hip/knee/ankle chain.
    elif p.z < .88:
        assign_chain(i,p,["pelvis","thigh."+side,"shin."+side,"foot."+side])
    # Arms and hands: only the matching shoulder/elbow/hand/finger chain.
    elif .78 < p.z < 1.72 and lateral > width*.22 and not rear:
        assign_chain(i,p,["upper_arm."+side,"forearm."+side,"hand."+side,
                          "finger.1."+side,"finger.2."+side,"finger.3."+side])
    # Head/neck stay separate from torso and limb chains.
    elif p.z > 1.68 and lateral < width*.22:
        assign_chain(i,p,["neck","head","jaw"])
    else:
        assign_chain(i,p,["root","pelvis","spine","chest","neck"])
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
def locomotion(f,amount,cycle_frames=24):
    t=(f-1)/cycle_frames*math.tau
    for suf,phase in [("L",0),("R",math.pi)]:
        a=math.sin(t+phase)
        # Swing limbs in their sagittal plane, not around the bone's roll axis.
        rot("thigh."+suf,x=.55*amount*a)
        rot("shin."+suf,x=.45*amount*max(0,-a))
        rot("upper_arm."+suf,x=-.30*amount*a)
    rot("spine",.04*amount*math.sin(2*t)); rot("chest",.025*amount*math.sin(2*t+1))
    for suf,s in [("L",1),("R",-1)]: rot("wing."+suf,s*.12*amount*math.sin(2*t))
    for n,k in [("tail.01",.08),("tail.02",.12),("tail.03",.16),("tail.tip",.20)]:
        rot(n,k*math.sin(t+.5))
def smooth(v):
    v=max(0.0,min(1.0,v))
    return v*v*(3.0-2.0*v)
def attack(f):
    t=(f-1)/30
    anticipation=math.sin(math.pi*min(1.0,t/.24)) if t<.24 else 0.0
    impact=smooth((t-.24)/.18)*(1.0-smooth((t-.42)/.50))
    rot("spine",-.10*anticipation-.22*impact)
    rot("chest",-.16*anticipation-.35*impact)
    rot("upper_arm.R",x=-.9*impact)
    rot("forearm.R",x=-.7*impact)
    rot("sword",x=-.8*impact)
    rot("wing.L",.2*impact); rot("wing.R",-.2*impact)
def cast(f):
    p=math.sin((f-1)/24*math.pi)
    rot("upper_arm.L",x=.65*p); rot("upper_arm.R",x=-.65*p)
    rot("wing.L",.35*p); rot("wing.R",-.35*p)
    rot("tail.01",.18*p); rot("tail.02",.24*p); rot("tail.03",.30*p)
def death(f):
    p=smooth((f-1)/30)
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
    rot("tail.01",.30*p); rot("tail.02",-.35*p); rot("tail.03",.40*p)
def two_hand_push(f):
    p=math.sin((f-1)/30*math.pi)
    rot("spine",-.16*p); rot("chest",-.24*p)
    rot("upper_arm.L",x=.78*p); rot("upper_arm.R",x=-.78*p)
    rot("forearm.L",x=.34*p); rot("forearm.R",x=-.34*p)
    rot("wing.L",.14*p); rot("wing.R",-.14*p)
def rally_raise(f):
    p=math.sin((f-1)/30*math.pi)
    rot("chest",-.18*p); rot("head",.08*p)
    rot("upper_arm.L",x=-.72*p); rot("upper_arm.R",x=.72*p)
    rot("forearm.L",x=-.28*p); rot("forearm.R",x=.28*p)
    rot("wing.L",.32*p); rot("wing.R",-.32*p)
    rot("tail.02",.12*p); rot("tail.03",.18*p)
def slash_down(f):
    p=math.sin((f-1)/30*math.pi)
    rot("spine",-.18*p); rot("chest",-.24*p)
    rot("upper_arm.R",x=-1.0*p); rot("forearm.R",x=-.82*p); rot("sword",x=-.95*p)
    rot("wing.L",.12*p); rot("wing.R",-.18*p)
def slash_rising(f):
    p=math.sin((f-1)/30*math.pi)
    rot("spine",.10*p); rot("chest",.18*p)
    rot("upper_arm.R",x=.78*p); rot("forearm.R",x=-.52*p); rot("sword",x=.92*p)
    rot("wing.L",.10*p); rot("wing.R",-.14*p)
def spin_cleave(f):
    p=math.sin((f-1)/30*math.pi)
    rot("pelvis",z=.42*p); rot("spine",z=.62*p); rot("chest",z=.48*p)
    rot("upper_arm.R",x=-.72*p); rot("forearm.R",x=-.55*p); rot("sword",x=-.65*p)
    rot("upper_arm.L",x=.40*p); rot("wing.L",.42*p); rot("wing.R",-.42*p)
    rot("tail.01",.22*p); rot("tail.02",-.28*p); rot("tail.03",.34*p)
clip("Idle",[1,8,16,24,31],idle)
clip("Run",[1,4,7,10,13,16,19,22,25],lambda f:locomotion(f,1.0,24))
clip("Walk",[1,5,9,13,17,21,25,29,33],lambda f:locomotion(f,.65,32))
clip("Attack",[1,4,7,10,13,16,19,22,25,28,31],attack)
clip("Cast",[1,4,7,10,13,16,19,22,25],cast)
clip("Death",[1,8,16,24,31],death)
clip("Hit",[1,3,5,7,9,11,13],hit)
clip("TurnLeft",[1,5,9,13,17],lambda f:turn(f,1))
clip("TurnRight",[1,5,9,13,17],lambda f:turn(f,-1))
clip("Stop",[1,4,7,11],stop)
clip("Ultimate",[1,6,11,16,21,26,31],ultimate)
# Warrior skill IDs resolve to these distinct clips through skills.skillfx releases.
clip("two_hand_push",[1,4,8,12,16,20,24,28,31],two_hand_push)
clip("rally_raise",[1,4,8,12,16,20,24,28,31],rally_raise)
clip("slash_down",[1,4,8,12,16,20,24,28,31],slash_down)
clip("slash_rising",[1,4,8,12,16,20,24,28,31],slash_rising)
clip("spin_cleave",[1,4,8,12,16,20,24,28,31],spin_cleave)
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
