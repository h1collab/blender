#!/usr/bin/env python3
"""ORIGINAL Blender-generated Backrooms: abandoned hospital POV (single 30s shot).

All pixels are rendered from self-built 3D meshes, Cycles shaders and lamps.
NO stock video, texture downloads, pre-rendered footage, or VSE movie strips.
Designed for headless Blender 3.4+ / GitHub Actions CPU rendering.
"""
import argparse
import math
import os
import random
import sys

import bpy
from mathutils import Vector

SEED = 1701
RNG = random.Random(SEED)
PI = math.pi
TAU = math.tau
CELL = 5.30
NX, NY = 6, 4
CEIL = 3.04
DOOR_H = 2.48
GAP = 3.52
WALL = 0.17

# The virtual person follows one physically contiguous 3D path.
ROUTE = [(0,0),(0,1),(1,1),(2,1),(2,2),(3,2),
         (4,2),(4,1),(5,1),(5,2),(5,3)]
EXTRA_PASSAGES = [
    ((0,1),(0,2)), ((1,1),(1,2)), ((2,1),(3,1)),
    ((2,2),(2,3)), ((3,2),(3,3)), ((4,2),(4,3)),
    ((4,1),(4,0)), ((5,1),(5,0)), ((1,0),(2,0)),
    ((0,2),(1,2)), ((3,0),(3,1)), ((2,0),(3,0)),
]
CONNECTED = set()


def grid(ix, iy):
    return Vector(((ix-(NX-1)*.5)*CELL, (iy-(NY-1)*.5)*CELL, 0.0))


def edge(a, b):
    return tuple(sorted((tuple(a), tuple(b))))


for p, q in zip(ROUTE, ROUTE[1:]):
    CONNECTED.add(edge(p, q))
for p, q in EXTRA_PASSAGES:
    CONNECTED.add(edge(p, q))


def mat_plain(name, color, rough=0.82, metal=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (*color, 1)
    bs.inputs["Roughness"].default_value = rough
    bs.inputs["Metallic"].default_value = metal
    return m


def mat_grime(name, colors, scale, rough=.87, bump=.11):
    """World-space fractal dirt and subtle fine plaster relief."""
    m = mat_plain(name, colors[1], rough)
    tree = m.node_tree
    nodes, links = tree.nodes, tree.links
    bs = nodes.get("Principled BSDF")
    pos = nodes.new("ShaderNodeNewGeometry")
    dirt = nodes.new("ShaderNodeTexNoise")
    dirt.inputs["Scale"].default_value = scale
    dirt.inputs["Detail"].default_value = 4.0
    dirt.inputs["Roughness"].default_value = .69
    links.new(pos.outputs["Position"], dirt.inputs["Vector"])
    ramp = nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements.remove(cr.elements[1])
    cr.elements[0].position = .23
    cr.elements[0].color = (*colors[0], 1)
    for cutoff, col in ((.53, colors[1]), (.81, colors[2])):
        e = cr.elements.new(cutoff)
        e.color = (*col, 1)
    links.new(dirt.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bs.inputs["Base Color"])
    micro = nodes.new("ShaderNodeTexNoise")
    micro.inputs["Scale"].default_value = scale * 12
    micro.inputs["Detail"].default_value = 2
    links.new(pos.outputs["Position"], micro.inputs["Vector"])
    relief = nodes.new("ShaderNodeBump")
    relief.inputs["Strength"].default_value = bump
    relief.inputs["Distance"].default_value = .018
    links.new(micro.outputs["Fac"], relief.inputs["Height"])
    links.new(relief.outputs["Normal"], bs.inputs["Normal"])
    return m


def mat_emission(name, color, power):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    n = m.node_tree.nodes
    n.clear()
    e = n.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1)
    e.inputs["Strength"].default_value = power
    out = n.new("ShaderNodeOutputMaterial")
    m.node_tree.links.new(e.outputs[0], out.inputs["Surface"])
    return m


def box(name, loc, dims, material, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.data.materials.append(material)
    if bevel > 0:
        mod = ob.modifiers.new("Worn manufactured edges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        ob.modifiers.new("Weighted normal", "WEIGHTED_NORMAL")
    return ob


def cylinder(name, loc, radius, depth, mat, sides=12, rotation=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides, radius=radius,
                                        depth=depth, location=loc)
    ob = bpy.context.object
    ob.name = name
    if rotation is not None:
        ob.rotation_euler = rotation
    ob.data.materials.append(mat)
    for face in ob.data.polygons:
        face.use_smooth = True
    return ob


def rod(name, a, b, radius, mat, sides=10):
    va, vb = Vector(a), Vector(b)
    direction = vb-va
    obj = cylinder(name, (va+vb)*.5, radius, direction.length, mat, sides)
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    return obj


def stencil(name, body, pos, size, material, rot=(PI/2, 0, 0)):
    font = bpy.data.curves.new(name+" curves", "FONT")
    font.body = body
    font.size = size
    font.align_x = "CENTER"
    font.align_y = "CENTER"
    font.space_character = 1.18
    obj = bpy.data.objects.new(name, font)
    bpy.context.collection.objects.link(obj)
    obj.location = pos
    obj.rotation_euler = rot
    obj.data.materials.append(material)
    return obj


def wall_piece(axis, constant, a, b, low, high, palette):
    if b-a < .08 or high-low < .06:
        return
    width = b-a
    if axis == "X":  # horizontal run: constant y
        loc = ((a+b)/2, constant, (low+high)/2)
        dims = (width, WALL, high-low)
        rloc = ((a+b)/2,constant,(low+high)/2)
    else:            # vertical run: constant x
        loc = (constant, (a+b)/2, (low+high)/2)
        dims = (WALL, width, high-low)
        rloc = (constant,(a+b)/2,(low+high)/2)
    # Consistent two-tone hospital paint. Upper portion nicotine-stained beige.
    for z0,z1,mt in ((low,min(high,1.19),palette["upper"] if low>=1.19 else palette["lower"]),
                     (max(low,1.19),high,palette["upper"])):
        if z1-z0 < .02:
            continue
        p = (loc[0], loc[1], (z0+z1)*.5)
        d = (dims[0],dims[1],z1-z0)
        box("Real plaster wall / "+axis, p, d, mt)
    if low < .10 and high > 1.0:
        offset = .115
        if axis=="X":
            box("Hospital scuffed skirting", (rloc[0],constant+offset,.105),
                (width,.052,.21),palette["skirt"])
            box("Institutional corridor handrail", (rloc[0],constant+offset,.96),
                (width,.064,.093),palette["rail"],.012)
        else:
            box("Hospital scuffed skirting", (constant+offset,rloc[1],.105),
                (.052,width,.21),palette["skirt"])
            box("Institutional corridor handrail", (constant+offset,rloc[1],.96),
                (.064,width,.093),palette["rail"],.012)


def wall_boundary(axis, constant, midpoint, opening, palette):
    half = CELL*.5
    a, b = midpoint-half, midpoint+half
    if opening:
        left, right = midpoint-GAP*.5, midpoint+GAP*.5
        wall_piece(axis,constant,a,left,0,CEIL,palette)
        wall_piece(axis,constant,right,b,0,CEIL,palette)
        wall_piece(axis,constant,left,right,DOOR_H,CEIL,palette)
        # Aged metal frame around every walkable passage, no invisible walls.
        if axis=="X":
            for pos in (left,right):
                box("Door passage scratched jamb", (pos,constant,DOOR_H*.5),
                    (.083,.24,DOOR_H),palette["iron"],.012)
            box("Passage upper metal lintel",(midpoint,constant,DOOR_H),
                (GAP,.24,.08),palette["iron"],.008)
        else:
            for pos in (left,right):
                box("Door passage scratched jamb",(constant,pos,DOOR_H*.5),
                    (.24,.083,DOOR_H),palette["iron"],.012)
            box("Passage upper metal lintel",(constant,midpoint,DOOR_H),
                (.24,GAP,.08),palette["iron"],.008)
    else:
        wall_piece(axis,constant,a,b,0,CEIL,palette)


def closed_hospital_door(ix,iy,side,palette,number):
    """Photographed-as-built side ward door, intentionally not in walking route."""
    center=grid(ix,iy)
    if side=="north":
        y=center.y+CELL*.5-WALL*.55-.025
        x=center.x+1.0
        door=box("Closed ward steel door", (x,y,1.12),
                 (1.13,.095,2.22),palette["door"],.018)
        box("Door glass wire pane", (x,y-.051,1.63),
            (.46,.014,.54),palette["glass"])
        box("Hospital door kick plate",(x,y-.061,.29),
            (.90,.009,.39),palette["iron"])
        cylinder("Battered door handle", (x+.34,y-.13,1.02),
                 .055,.12,palette["iron"],10,(PI/2,0,0))
        stencil("Faded hospital room number", "W-"+str(number),
                (x,y-.076,1.99),.16,palette["stencil"])
    if side=="east":
        x=center.x+CELL*.5-WALL*.55-.025
        y=center.y-1.12
        door=box("Sealed ward door", (x,y,1.12),
                 (.095,1.12,2.22),palette["door"],.018)
        box("Dark scratched observation glass",(x-.058,y,1.67),
            (.012,.48,.52),palette["glass"])


def ceiling_grid(palette):
    xmin=grid(0,0).x-CELL*.5
    xmax=grid(NX-1,0).x+CELL*.5
    ymin=grid(0,0).y-CELL*.5
    ymax=grid(0,NY-1).y+CELL*.5
    box("Suspended acoustic ceiling",((xmin+xmax)/2,(ymin+ymax)/2,CEIL+.055),
        (xmax-xmin+.24,ymax-ymin+.24,.13),palette["ceiling"])
    for i in range(round((xmax-xmin)/1.06)+1):
        x=xmin+i*1.06
        box("Blackened T-bar ceiling grid", (x,(ymin+ymax)/2,CEIL-.008),
            (.018,ymax-ymin,.013),palette["iron"])
    for i in range(round((ymax-ymin)/1.06)+1):
        y=ymin+i*1.06
        box("Blackened cross ceiling grid",((xmin+xmax)/2,y,CEIL-.008),
            (xmax-xmin,.018,.013),palette["iron"])


def fluorescent(cx,cy,index,palette,has_light=True):
    x = cx+(.38 if index%3==0 else 0.0)
    y = cy
    box("Aged metal fluorescent troffer",(x,y,CEIL-.092),
        (.73,1.48,.065),palette["iron"],.013)
    box("Yellowed fluorescent diffusion lens",(x,y,CEIL-.143),
        (.64,1.34,.021),palette["diffuser"],.007)
    for shift in (-.18,.18):
        box("Fluorescent white light tube",(x+shift,y,CEIL-.169),
            (.055,1.18,.029),palette["tube"],.014)
    if not has_light:
        return None
    bpy.ops.object.light_add(type="AREA",location=(x,y,CEIL-.22))
    l=bpy.context.object
    l.name="TRUE AREA LIGHT: ceiling practical fixture "+str(index)
    l.data.shape="RECTANGLE"
    l.data.size=.72
    l.data.size_y=1.32
    l.data.energy=235 if index%7 else 155
    l.data.color=(1.0,.93,.74) if index%5 else (.75,.86,1.0)
    return l


def tiled_floor(palette):
    cx=(grid(0,0).x+grid(NX-1,0).x)*.5
    cy=(grid(0,0).y+grid(0,NY-1).y)*.5
    w,h=NX*CELL,NY*CELL
    box("Real stained hospital vinyl floor",(cx,cy,-.11),
        (w+.36,h+.36,.22),palette["floor"])
    xmin=cx-w/2
    ymin=cy-h/2
    for i in range(1,int(w/.81)):
        box("Age-darkened vinyl flooring seam",(xmin+i*.81,cy,.002),
            (.007,h,.004),palette["grout"])
    for j in range(1,int(h/.81)):
        box("Age-darkened floor tile joint",(cx,ymin+j*.81,.002),
            (w,.007,.004),palette["grout"])
    for n in range(25):
        ix=RNG.randrange(NX)
        iy=RNG.randrange(NY)
        center=grid(ix,iy)
        dx=RNG.choice((-1,1))*RNG.uniform(1.35,2.1)
        dy=RNG.uniform(-1.6,1.6)
        paper=box("Forgotten wet paper or chart", (center.x+dx,center.y+dy,.013),
                   (RNG.uniform(.16,.34),RNG.uniform(.22,.38),.006),
                   palette["paper"])
        paper.rotation_euler.z=RNG.uniform(-PI,PI)
    for n in range(16):
        ix=RNG.randrange(NX)
        iy=RNG.randrange(NY)
        c=grid(ix,iy)
        x=c.x+RNG.uniform(-2.2,2.2)
        y=c.y+RNG.uniform(-2.2,2.2)
        verts=[(x,y,.012)]
        for j in range(1,7):
            verts.append((x+j*.115, y+math.sin(j*.83+n)*.038,.012))
        curve=bpy.data.curves.new("Uneven broken tile crack","CURVE")
        curve.dimensions="3D"
        curve.bevel_depth=.004
        curve.bevel_resolution=0
        spl=curve.splines.new("POLY")
        spl.points.add(len(verts)-1)
        for point,co in zip(spl.points,verts):
            point.co=(*co,1)
        obj=bpy.data.objects.new("Real irregular vinyl crack",curve)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(palette["grout"])


def abandoned_bed(cx,cy,palette):
    frame=palette["iron"]
    box("Abandoned wheeled hospital bed frame",(cx,cy,.72),
        (1.17,2.16,.10),frame,.03)
    box("Soiled thin hospital mattress",(cx,cy,.83),
        (1.04,1.96,.18),palette["mattress"],.055)
    box("Old sagging blanket",(cx,cy-.44,.944),
        (1.03,1.03,.052),palette["blanket"],.026)
    for x in (-.50,.50):
        for y in (-.93,.93):
            rod("Bed leg", (cx+x,cy+y,.18),(cx+x,cy+y,.68),.035,frame)
            cylinder("Medical bed wheel",(cx+x,cy+y,.15),
                     .11,.055,palette["wheel"],12,(PI/2,0,0))
    for shift in (-.60,.60):
        rod("Hospital bed guardrail",(cx+shift,cy-.63,1.05),
            (cx+shift,cy+.55,1.05),.029,frame)
    box("Upright hospital bed headboard",(cx,cy+1.11,1.16),
        (1.12,.045,.63),palette["door"],.03)


def wheeled_cart(cx,cy,palette):
    frame=palette["iron"]
    for z in (.40,.86):
        box("Empty instrument trolley shelf",(cx,cy,z),
            (.75,1.12,.035),frame,.025)
    for x in (-.34,.34):
        for y in (-.50,.50):
            rod("Hospital instrument trolley upright",(cx+x,cy+y,.18),
                (cx+x,cy+y,1.01),.024,frame)
            cylinder("Cart caster",(cx+x,cy+y,.135),.085,.04,
                     palette["wheel"],10,(PI/2,0,0))
    box("Discarded bandage packet",(cx+.12,cy,.889),
        (.21,.31,.035),palette["paper"],.01)


def wheelchair(cx,cy,palette):
    # A proper 3D prop instead of a 2D silhouette / stock footage.
    box("Wheelchair worn leather seat",(cx,cy,.64),
        (.64,.59,.085),palette["leather"],.06)
    box("Wheelchair back upholstery",(cx,cy+.28,1.09),
        (.64,.09,.84),palette["leather"],.04)
    for x in (-.47,.47):
        cylinder("Wheelchair spoked side wheel",(cx+x,cy-.045,.39),
                 .38,.061,palette["wheel"],20,(0,PI/2,0))
        cylinder("Wheelchair metal wheel hub",(cx+x,cy-.045,.39),
                 .084,.075,palette["iron"],12,(0,PI/2,0))
        rod("Wheelchair arm rest",(cx+x*.81,cy-.15,.90),
            (cx+x*.81,cy+.32,.90),.025,palette["iron"])
        rod("Wheelchair folding leg",(cx+x*.82,cy-.22,.28),
            (cx+x*.82,cy+.20,.68),.027,palette["iron"])


def place_props(palette):
    c=grid(1,2)
    abandoned_bed(c.x-.73,c.y+.45,palette)
    c=grid(3,3)
    wheelchair(c.x-.90,c.y+.42,palette)
    c=grid(4,0)
    wheeled_cart(c.x+.65,c.y+.12,palette)
    c=grid(1,0)
    wheeled_cart(c.x-1.15,c.y+.86,palette)
    # Narrow institutional notice boards and peeling wall markings.
    for idx,(ix,iy) in enumerate(((0,1),(2,2),(4,2),(5,2),(1,3))):
        c=grid(ix,iy)
        y=c.y+CELL*.5-WALL*.52-.028
        x=c.x+.7
        box("Scratched information board",(x,y,1.73),
            (1.27,.045,.74),palette["board"],.013)
        for j in range(2):
            box("Old admission chart",(x-.24+j*.45,y-.028,1.73),
                (.32,.008,.54),palette["paper"],.004)
        stencil("Ward location label","W A R D  "+str(idx+1),
                (x,y-.040,2.19),.15,palette["stencil"])
    # One hanging green EXIT sign becomes a decayed hospital detail.
    c=grid(2,1)
    box("Old exit sign",(c.x,c.y+CELL*.5-.28,2.55),
        (1.03,.18,.31),palette["dark_green"],.014)
    stencil("Exit wayfinding lettering","EXIT",
            (c.x,c.y+CELL*.5-.386,2.54),.23,palette["white"])
    for idx,room in enumerate(((0,2),(2,0),(4,3),(5,0))):
        closed_hospital_door(*room,"north",palette,idx+2)


def catmull_point(points,t):
    # Cubic camera spline: a single continuous shot, never a cut.
    i=int(math.floor(t))
    f=t-i
    i=min(max(i,0),len(points)-2)
    p0=points[max(0,i-1)]
    p1=points[i]
    p2=points[min(i+1,len(points)-1)]
    p3=points[min(i+2,len(points)-1)]
    return .5*((2*p1)+(-p0+p2)*f+
               (2*p0-5*p1+4*p2-p3)*f*f+
               (-p0+3*p1-3*p2+p3)*f*f*f)


def animate_camera(frames,fps):
    bpy.ops.object.camera_add(location=(0,0,1.67))
    cam=bpy.context.object
    cam.name="ONE SINGLE FIRST PERSON CAMERA - 30s unbroken take"
    cam.data.type="PERSP"
    cam.data.lens=22.8
    cam.data.sensor_width=36
    cam.data.clip_end=120
    bpy.context.scene.camera=cam
    route=[grid(i,j) for i,j in ROUTE]
    final=len(route)-1
    for frame in range(1,frames+1):
        seconds=(frame-1)/fps
        t=(frame-1)/max(1,frames-1)*final
        pt=catmull_point(route,t)
        forward=catmull_point(route,min(final-.001,t+.055))-pt
        if forward.length<.001:
            forward=route[-1]-route[-2]
        pt.z=1.67+.025*math.sin(TAU*1.71*seconds)+.008*math.sin(TAU*.37*seconds)
        pt.x+=.012*math.sin(TAU*.72*seconds)
        pt.y+=.010*math.cos(TAU*.63*seconds)
        aim=Vector((forward.x,forward.y,.010*math.sin(TAU*.53*seconds)))
        cam.location=pt
        cam.rotation_euler=aim.to_track_quat("-Z","Y").to_euler()
        cam.rotation_euler.rotate_axis("Z",.003*math.sin(TAU*.91*seconds))
        cam.keyframe_insert(data_path="location",frame=frame)
        cam.keyframe_insert(data_path="rotation_euler",frame=frame)
    if cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation="LINEAR"


def setup_scene(args):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.context.scene.unit_settings.system="METRIC"
    s=bpy.context.scene
    s.render.engine="CYCLES"
    s.cycles.device="CPU"
    s.cycles.samples=args.samples
    s.cycles.max_bounces=4
    s.cycles.diffuse_bounces=3
    s.cycles.glossy_bounces=2
    s.cycles.transparent_max_bounces=3
    if hasattr(s.cycles,"use_denoising"):
        s.cycles.use_denoising=False
    if hasattr(bpy.context.view_layer,"cycles"):
        bpy.context.view_layer.cycles.use_denoising=False
    s.render.resolution_x=args.width
    s.render.resolution_y=args.height
    s.render.resolution_percentage=100
    s.render.fps=args.fps
    s.frame_start=1
    s.frame_end=args.frames
    s.render.image_settings.file_format="PNG"
    s.render.image_settings.color_mode="RGB"
    s.render.image_settings.color_depth="8"
    s.view_settings.view_transform="Standard"
    s.view_settings.look="Medium High Contrast"
    s.view_settings.exposure=-.22
    s.render.film_transparent=False
    s.world.use_nodes=True
    background=s.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value=(.18,.20,.19,1)
    background.inputs["Strength"].default_value=.32

    palette={
        "upper":mat_grime("Nicotine-stained cracked ochre plaster",
            ((.19,.17,.105),(.43,.40,.26),(.59,.54,.35)),2.25,.92,.19),
        "lower":mat_grime("Fading hospital olive enamel w mould",
            ((.105,.135,.10),(.23,.29,.22),(.33,.36,.24)),1.9,.83,.11),
        "ceiling":mat_grime("Acoustic ceiling tile water damage",
            ((.19,.21,.17),(.48,.49,.42),(.65,.63,.52)),3.4,.97,.13),
        "floor":mat_grime("Filthy hospital vinyl and ground-in discoloration",
            ((.115,.135,.117),(.245,.26,.21),(.37,.35,.27)),4.8,.71,.23),
        "grout":mat_plain("Deep black worn tile grout",(.115,.12,.109)),
        "skirt":mat_plain("Grime-colored polymer baseboard",(.13,.16,.13)),
        "rail":mat_plain("Yellowed hospital corridor guardrail",(.27,.31,.25),.68),
        "iron":mat_plain("Scuffed oxidized aluminium and steel",(.23,.27,.25),.43,.53),
        "wheel":mat_plain("Medical trolley aged rubber wheels",(.085,.10,.09)),
        "door":mat_grime("Worn ward door cream-green paint",
            ((.16,.20,.15),(.38,.43,.31),(.46,.48,.34)),3.5,.68,.06),
        "glass":mat_plain("Dirty dark wired safety window",(.071,.115,.111),.27,.12),
        "mattress":mat_grime("Grey stained medical mattress",
            ((.30,.30,.25),(.61,.59,.48),(.72,.69,.58)),5.2,.94,.16),
        "blanket":mat_grime("Abandoned crumpled brown wool blanket",
            ((.17,.20,.17),(.31,.32,.26),(.38,.38,.30)),3.9,.97,.17),
        "leather":mat_plain("Cracked wheelchair upholstery",(.14,.16,.13),.86),
        "paper":mat_plain("Yellowed patient admission paper",(.65,.61,.44),.95),
        "board":mat_plain("Dusty nurse notice board",(.20,.25,.20)),
        "stencil":mat_plain("Faded black hospital stencil",(.075,.085,.07)),
        "dark_green":mat_plain("Oxidized green exit sign",(.08,.21,.13)),
        "white":mat_emission("Old phosphorescent white sign",(.62,.88,.64),.7),
        "diffuser":mat_emission("Old dirty fluorescent diffuser",(.73,.77,.61),2.1),
        "tube":mat_emission("Actual glowing ceiling tube",(.86,.90,.73),4.0)
    }
    tiled_floor(palette)
    ceiling_grid(palette)
    for ix in range(NX):
        for iy in range(NY):
            c=grid(ix,iy)
            east=((ix,iy),(ix+1,iy))
            north=((ix,iy),(ix,iy+1))
            wall_boundary("Y",c.x+CELL/2,c.y,
                          ix<NX-1 and edge(*east) in CONNECTED,palette)
            wall_boundary("X",c.y+CELL/2,c.x,
                          iy<NY-1 and edge(*north) in CONNECTED,palette)
            if ix==0:
                wall_boundary("Y",c.x-CELL/2,c.y,False,palette)
            if iy==0:
                wall_boundary("X",c.y-CELL/2,c.x,False,palette)
    route_cells=set(ROUTE)
    extras={(1,2),(3,3),(4,0),(1,0),(0,2)}
    lamps={}
    for ix in range(NX):
        for iy in range(NY):
            c=grid(ix,iy)
            active=(ix,iy) in route_cells or (ix,iy) in extras
            l=fluorescent(c.x,c.y,ix+NX*iy,palette,active)
            if l:
                lamps[(ix,iy)]=l
    # Physically actuated irregular flicker near the end of the exploration.
    flicker=lamps[(5,2)]
    nominal=flicker.data.energy
    points=[
        (1,nominal),
        (round(args.frames*.67),nominal),
        (round(args.frames*.71),nominal*.35),
        (round(args.frames*.714),0),
        (round(args.frames*.728),nominal),
        (round(args.frames*.86),nominal),
        (round(args.frames*.866),0),
        (round(args.frames*.89),nominal*.27),
        (args.frames,nominal*.36),
    ]
    for frame,value in points:
        flicker.data.energy=value
        flicker.data.keyframe_insert(data_path="energy",frame=frame)
    place_props(palette)
    animate_camera(args.frames,args.fps)
    s.frame_set(1)
    return s


def main():
    tail=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",default="output/backrooms")
    p.add_argument("--width",type=int,default=960)
    p.add_argument("--height",type=int,default=540)
    p.add_argument("--fps",type=int,default=18)
    p.add_argument("--frames",type=int,default=540)
    p.add_argument("--samples",type=int,default=7)
    p.add_argument("--render-still",action="store_true")
    p.add_argument("--still-frame",type=int,default=280)
    args=p.parse_args(tail)
    if min(args.width,args.height,args.fps,args.frames,args.samples)<1:
        p.error("All quality parameters must be positive")
    if args.frames!=args.fps*30:
        p.error("The continuous first-person shot MUST be exactly 30 seconds")
    out=os.path.abspath(args.output_dir)
    os.makedirs(out,exist_ok=True)
    frames=os.path.join(out,"frames")
    os.makedirs(frames,exist_ok=True)
    s=setup_scene(args)
    project=os.path.join(out,"backrooms_hospital_3d.blend")
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=project)
    print("ORIGINAL_BLENDER_3D_SCENE_SAVED",project,flush=True)
    print("PHYSICAL_SCENE_OBJECT_COUNT",len(bpy.data.objects),flush=True)
    print("CONTINUOUS_REAL_CAMERA",s.camera.name,flush=True)
    if args.render_still:
        frame=max(1,min(args.still_frame,args.frames))
        s.frame_set(frame)
        s.render.filepath=os.path.join(out,"preview.png")
        bpy.ops.render.render(write_still=True)
        print("ACTUAL_BLENDER_RENDERED_STILL",s.render.filepath,flush=True)
    else:
        s.render.filepath=os.path.join(frames,"frame_")
        bpy.ops.render.render(animation=True)
        print("ACTUAL_BLENDER_3D_ANIMATION_COMPLETE",args.frames,flush=True)


if __name__=="__main__":
    main()
