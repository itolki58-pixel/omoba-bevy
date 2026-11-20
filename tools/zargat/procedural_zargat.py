#!/usr/bin/env python3
"""Procedural first-pass Zargat demon-knight. Generates a static, detailed GLB and render."""
import bpy, math, os
from mathutils import Vector

OUT = "dist/zargat-procedural.glb"
PNG = "dist/zargat-procedural-preview.png"
os.makedirs("dist", exist_ok=True)

# Reset scene
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
    pass

def mat(name, color, metallic=0.0, rough=0.45, emission=None, strength=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Roughness"].default_value = rough
    if emission:
        key = "Emission Color" if "Emission Color" in p.inputs else "Emission"
        p.inputs[key].default_value = (*emission, 1)
        p.inputs["Emission Strength"].default_value = strength
    return m

steel = mat("Obsidian forged steel", (0.035,0.045,0.06), .82, .28)
black = mat("Deep black armor", (0.012,0.016,0.023), .68, .34)
red = mat("Crimson enamel", (.32,.012,.025), .62, .26)
red_dark = mat("Dark blood red", (.12,.006,.014), .55, .35)
gold = mat("Aged bronze trim", (.52,.27,.075), .78, .3)
glow = mat("Molten orange", (1,.12,.008), .2, .22, (1,.075,.002), 4.0)
eye = mat("Infernal eyes", (1,.25,.01), .1, .18, (1,.12,.002), 7.0)
leather = mat("Charred leather", (.055,.018,.016), .1, .7)
stone = mat("Basalt", (.075,.085,.10), .15, .8)

def assign(o, m):
    o.data.materials.append(m)
    return o

def uv(name, loc, scale, material, seg=20, rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, location=loc)
    o=bpy.context.object; o.name=name; o.scale=scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return assign(o,material)

def ico(name, loc, scale, material, subdivisions=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1, location=loc)
    o=bpy.context.object; o.name=name; o.scale=scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return assign(o,material)

def cube(name, loc, scale, material, bevel=.08, rotation=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o=bpy.context.object; o.name=name; o.dimensions=scale
    if rotation: o.rotation_euler=rotation
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod=o.modifiers.new("Forged rounded edges","BEVEL"); mod.width=bevel; mod.segments=2
        o.modifiers.new("Weighted corner normals","WEIGHTED_NORMAL")
    return assign(o,material)

def rod(name, a, b, radius, material, vertices=10, r2=None):
    a,b=Vector(a),Vector(b); d=b-a
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius, radius2=(radius if r2 is None else r2), depth=d.length, location=(a+b)/2)
    o=bpy.context.object; o.name=name; o.rotation_mode="QUATERNION"; o.rotation_quaternion=d.to_track_quat("Z","Y")
    return assign(o,material)

def curve(name, points, radius, material):
    c=bpy.data.curves.new(name,"CURVE"); c.dimensions="3D"; c.bevel_depth=radius; c.bevel_resolution=3
    s=c.splines.new("BEZIER"); s.bezier_points.add(len(points)-1)
    for p,co in zip(s.bezier_points,points):
        p.co=co; p.handle_left_type="AUTO"; p.handle_right_type="AUTO"
    o=bpy.data.objects.new(name,c); bpy.context.collection.objects.link(o); return assign(o,material)

# Feet, greaves and clawed boots
for side,x in [("L",-.34),("R",.34)]:
    uv("Armored boot "+side,(x,-.10,.22),(.30,.48,.22),black)
    cube("Crimson greave "+side,(x,-.30,.52),(.40,.22,.48),red,.09)
    rod("Greave center ridge "+side,(x,-.43,.35),(x,-.43,.75),.045,gold,8,.012)
    for j in range(3):
        xx=x+(j-1)*.12
        rod("Boot talon "+side+str(j),(xx,-.39,.20),(xx,-.70,.06),.075,steel,8,.006)
    uv("Knee joint "+side,(x,-.04,.91),(.22,.22,.22),gold)
    ico("Knee spike "+side,(x*1.28,-.10,1.00),(.11,.12,.24),steel)

# Legs and pelvis
uv("Pelvis core",(0,0,1.30),(.52,.34,.34),black)
cube("Front loin armor",(0,-.34,1.25),(.70,.16,.48),red,.12)
for side,x in [("L",-.36),("R",.36)]:
    uv("Thigh armor "+side,(x,0,1.18),(.31,.34,.48),steel)
    cube("Thigh red plate "+side,(x,-.29,1.23),(.34,.12,.38),red,.07, (0,0,(-.10 if x<0 else .10)))
    rod("Thigh gold trim "+side,(x,-.37,1.05),(x,-.37,1.38),.025,gold,8)
    for j in range(2):
        rod("Thigh spike "+side+str(j),(x+(-.16 if x<0 else .16),0,1.27+j*.12),(x+(-.38 if x<0 else .38),.03,1.32+j*.12),.075,steel,8,.005)

# Torso silhouette, layered breastplate, molten seams
uv("Abdomen",(0,0,1.72),(.48,.31,.53),black)
uv("Chest massive core",(0,-.015,2.17),(.69,.39,.52),steel)
for side,x in [("L",-.34),("R",.34)]:
    uv("Pectoral crimson plate "+side,(x,-.31,2.25),(.39,.17,.32),red)
    curve("Pectoral molten seam "+side,[(x*.65,-.48,2.45),(x,-.49,2.26),(x*.95,-.46,2.08)],.018,glow)
    rod("Rib armor "+side,(x*.55,-.32,1.88),(x*1.2,-.34,1.65),.07,black,8,.025)
cube("Central chest crest",(0,-.48,2.18),(.20,.09,.43),gold,.04)
ico("Chest infernal core",(0,-.55,2.19),(.095,.035,.14),glow,2)
for z in [1.83,1.96]:
    curve("Abdominal lava groove", [(-.24,-.31,z),(0,-.36,z-.04),(.24,-.31,z)],.014,glow)

# Neck and horned helmet
uv("Neck",(0,0,2.64),(.25,.24,.28),black)
uv("Helmet skull",(0,-.02,2.91),(.36,.31,.42),steel)
cube("Helmet face mask",(0,-.32,2.83),(.43,.12,.34),black,.08)
for side,x in [("L",-.16),("R",.16)]:
    uv("Burning eye "+side,(x,-.395,2.91),(.075,.025,.035),eye,16,8)
    rod("Helmet cheek "+side,(x*1.25,-.30,2.82),(x*1.35,-.27,2.63),.10,red,8,.025)
    curve("Curved demon horn "+side,[(x*.72,.0,3.18),(x*1.2,.02,3.38),(x*1.55,.01,3.58),(x*1.48,-.02,3.78)],.105,steel)
    rod("Horn gold band "+side,(x*1.20,.02,3.38),(x*1.29,.02,3.43),.11,gold,10)
rod("Helmet crown spike",(0,0,3.22),(0,.02,3.56),.12,red,8,.005)
for x in [-.24,-.12,0,.12,.24]:
    rod("Helmet brow ridge", (x,-.31,3.10),(x*.9,-.36,3.16),.035,gold,8,.008)

# Broad spiked pauldrons and arms
for side,x in [("L",-.82),("R",.82)]:
    uv("Shoulder pauldron "+side,(x,0,2.40),(.43,.39,.34),steel)
    uv("Pauldron crimson face "+side,(x,-.30,2.43),(.31,.14,.24),red)
    for j in range(3):
        sx=x+(j-1)*.18
        rod("Pauldron spike "+side+str(j),(sx,-.02,2.58),(sx*1.35,-.02,2.94+(j%2)*.08),.11,steel,8,.004)
    curve("Pauldron trim "+side,[(x-.30,-.38,2.36),(x,-.45,2.25),(x+.30,-.38,2.36)],.025,gold)
    uv("Upper arm "+side,(x*1.08,0,2.00),(.23,.27,.42),black)
    uv("Forearm armor "+side,(x*1.18,-.06,1.62),(.25,.29,.39),steel)
    cube("Forearm red plate "+side,(x*1.18,-.32,1.65),(.29,.12,.32),red,.06)
    for j in range(2):
        rod("Forearm spikes "+side+str(j),(x*1.2,-.05,1.70+j*.13),(x*1.5,-.04,1.84+j*.13),.07,steel,8,.004)
    uv("Gauntlet "+side,(x*1.2,-.08,1.30),(.24,.25,.20),black)

# Ragged crimson tabard
for side,x in [("L",-.22),("R",.22)]:
    verts=[(x-.16,-.40,1.40),(x+.16,-.40,1.40),(x+.13,-.43,.75),(x,-.45,.90),(x-.14,-.43,.72)]
    faces=[(0,1,2,3,4)]
    me=bpy.data.meshes.new("Tabard mesh"); me.from_pydata(verts,[],faces); me.materials.append(red_dark)
    ob=bpy.data.objects.new("Torn war tabard "+side,me); bpy.context.collection.objects.link(ob)
    sol=ob.modifiers.new("Cloth thickness","SOLIDIFY"); sol.thickness=.035
    bev=ob.modifiers.new("Soft cloth edges","BEVEL"); bev.width=.025; bev.segments=2
    curve("Tabard gold piping "+side,[(x-.14,-.43,1.36),(x-.13,-.45,.95),(x,-.46,.88)],.012,gold)

# Long segmented tail sweeping behind
tail_pts=[(0,.18,1.42),(0,.48,1.30),(.04,.78,1.15),(.16,1.08,1.05),(.36,1.36,1.10),(.55,1.62,1.28)]
for i in range(len(tail_pts)-1):
    rad=.14*(1-i*.13)
    rod("Tail armored segment "+str(i),tail_pts[i],tail_pts[i+1],rad,black,10,rad*.78)
    uv("Tail joint "+str(i),tail_pts[i+1],(rad*.8,rad*.8,rad*.8),red)
for i in range(1,5):
    p=Vector(tail_pts[i])
    rod("Tail dorsal spike "+str(i),p,p+Vector((.02,.02,.22-i*.025)),.075,steel,8,.003)
rod("Tail spear tip",tail_pts[-1],(tail_pts[-1][0]+.10,tail_pts[-1][1]+.28,tail_pts[-1][2]+.24),.17,red,8,.002)

# Wings: swept bat frames and red-orange membranes, behind the body
for side,sgn in [("L",-1),("R",1)]:
    root=(sgn*.30,.26,2.58)
    elbow=(sgn*.95,.40,2.95)
    wrist=(sgn*1.55,.48,2.67)
    tip=(sgn*2.05,.52,2.18)
    lower=(sgn*1.55,.50,1.82)
    anchors=[root,elbow,wrist,tip,lower,root]
    # membrane fan triangles with torn scalloped outer edge
    membrane=[root,elbow,wrist,tip,(sgn*1.86,.50,1.95),lower,(sgn*.92,.42,2.12)]
    faces=[(0,1,6),(1,2,6),(2,4,6),(2,3,4),(4,5,6)]
    me=bpy.data.meshes.new("Wing membrane mesh"); me.from_pydata(membrane,[],faces); me.materials.append(red_dark)
    ob=bpy.data.objects.new("Scalloped infernal wing "+side,me); bpy.context.collection.objects.link(ob)
    sol=ob.modifiers.new("Membrane thickness","SOLIDIFY"); sol.thickness=.025
    for j in range(len(anchors)-1):
        rod("Wing bone "+side+str(j),anchors[j],anchors[j+1],.075,black,9,.035)
    for j,(a,b) in enumerate([(root,tip),(elbow,lower),(wrist,(sgn*1.86,.5,1.95)),(root,(sgn*.92,.42,2.12))]):
        rod("Wing rib "+side+str(j),a,b,.035,gold if j==0 else steel,8,.012)
    curve("Wing molten vein "+side,[root,(sgn*.90,.38,2.54),(sgn*1.42,.43,2.35),(sgn*1.78,.46,2.02)],.022,glow)

# Greatsword held in right hand, diagonal down and outward
grip_a=(.99,-.24,1.40); grip_b=(1.18,-.29,1.02)
rod("Sword wrapped grip",grip_a,grip_b,.075,leather,10)
rod("Sword crossguard",(1.02,-.28,1.48),(1.47,-.28,1.26),.085,gold,8,.045)
rod("Sword pommel",(1.00,-.24,1.42),(.91,-.24,1.55),.10,red,8,.025)
blade_base=(1.18,-.30,1.00); blade_mid=(1.48,-.34,.46); blade_tip=(1.74,-.35,-.04)
rod("Infernal greatsword blade",blade_base,blade_tip,.22,steel,4,.015)
# Broad red blade faces and molten central fuller
rod("Crimson blade core", (1.27,-.48,.83),(1.66,-.48,.10),.105,red,4,.004)
curve("Molten sword fuller",[(1.24,-.53,.91),(1.43,-.55,.55),(1.64,-.51,.15)],.025,glow)
for i in range(3):
    t=.25+i*.22
    p=Vector(blade_base).lerp(Vector(blade_tip),t)
    ico("Sword ember "+str(i),p+Vector((-.06,-.16,.02)),(.045,.025,.07),eye,1)

# Ground plinth for studio preview only
bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1.45, depth=.14, location=(0,0,-.16))
plinth=assign(bpy.context.object,stone); plinth.name="Preview basalt plinth"
bev=plinth.modifiers.new("Plinth bevel","BEVEL"); bev.width=.07; bev.segments=3
plinth.modifiers.new("Plinth normals","WEIGHTED_NORMAL")
for i in range(16):
    a=math.tau*i/16
    uv("Rune glow "+str(i),(1.22*math.cos(a),1.22*math.sin(a),-.075),(.035,.035,.018),glow,12,8)

# Studio setup
world=bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world=world; world.color=(.025,.03,.045)
world.use_nodes=True; world.node_tree.nodes["Background"].inputs[0].default_value=(.018,.025,.04,1)
world.node_tree.nodes["Background"].inputs[1].default_value=.45

def area(name, loc, power, color, size):
    bpy.ops.object.light_add(type="AREA", location=loc)
    o=bpy.context.object; o.name=name; o.data.energy=power; o.data.color=color; o.data.shape="DISK"; o.data.size=size
    o.rotation_euler=(Vector((0,0,1.7))-o.location).to_track_quat("-Z","Y").to_euler()
area("Warm key", (4,-5,6), 1000, (1,.55,.32), 5)
area("Cool fill", (-4,-3,3.5), 850, (.25,.45,1), 4)
area("Infernal rim", (0,3,4.8), 1300, (1,.12,.025), 3)

bpy.ops.object.camera_add(location=(4.4,-7.8,3.65))
cam=bpy.context.object; cam.name="Zargat Preview Camera"
cam.rotation_euler=(Vector((0,0,1.75))-cam.location).to_track_quat("-Z","Y").to_euler()
cam.data.lens=55; bpy.context.scene.camera=cam

scene=bpy.context.scene
scene.render.engine="BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in {e.identifier for e in scene.render.bl_rna.properties["engine"].enum_items} else "BLENDER_EEVEE"
scene.eevee.taa_render_samples=48 if hasattr(scene,"eevee") else 48
scene.render.resolution_x=1100; scene.render.resolution_y=1100; scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"; scene.render.filepath=PNG
scene.view_settings.view_transform="Standard"
scene.camera.data.dof.use_dof=False
scene.render.film_transparent=False
bpy.ops.render.render(write_still=True)

# Export only character geometry (exclude camera, lights, stage and rune plinth)
bpy.ops.object.select_all(action="DESELECT")
for o in list(scene.objects):
    if o.type not in {"CAMERA","LIGHT"} and not o.name.startswith(("Preview basalt plinth","Rune glow")):
        o.select_set(True)
bpy.context.view_layer.objects.active=next(o for o in scene.objects if o.name=="Chest massive core")
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True, export_apply=True)
assert os.path.isfile(OUT) and os.path.getsize(OUT)>50000
assert os.path.isfile(PNG) and os.path.getsize(PNG)>10000
print("ZARGAT_OK", os.path.getsize(OUT), os.path.getsize(PNG))
