#!/usr/bin/env python3
"""Procedural summer-island loop for Blender CLI (Cycles CPU; no external assets)."""
import argparse
import math
import os
import random
import sys

import bpy
from mathutils import Vector

RNG = random.Random(24)
TAU = math.tau


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(description="Create and render Summer Paradise")
    p.add_argument("--output-dir", default="output/frames")
    p.add_argument("--width", type=int, default=854)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--frames", type=int, default=96)
    p.add_argument("--samples", type=int, default=12)
    return p.parse_args(argv)


def material(name, rgb, rough=0.7, metallic=0.0, emission=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1.0)
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (*rgb, 1.0)
    bs.inputs["Roughness"].default_value = rough
    bs.inputs["Metallic"].default_value = metallic
    if emission > 0:
        if "Emission Color" in bs.inputs:
            bs.inputs["Emission Color"].default_value = (*rgb, 1.0)
            bs.inputs["Emission Strength"].default_value = emission
        elif "Emission" in bs.inputs:
            bs.inputs["Emission"].default_value = (*rgb, 1.0)
    return m


def object_mesh(name, verts, faces, mat, mat_indexes=None):
    mesh = bpy.data.meshes.new(name + " geometry")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for m in (mat if isinstance(mat, (list, tuple)) else [mat]):
        obj.data.materials.append(m)
    if mat_indexes is not None:
        for polygon, index in zip(mesh.polygons, mat_indexes):
            polygon.material_index = index
    return obj


def uv_sphere(name, location, radius, mat, scale=(1, 1, 1), segments=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=12,
                                        radius=radius, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def cube(name, loc, scale, mat, bevel=0.06):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel > 0:
        mod = obj.modifiers.new("Soft rounded edges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        obj.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
    return obj


def rod(name, start, end, radius, mat, vertices=12):
    p1, p2 = Vector(start), Vector(end)
    d = p2 - p1
    mid = (p1 + p2) / 2
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius,
                                        depth=d.length, location=mid)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def stroke(name, points, radius, mat, closed=False):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = 2
    cu.bevel_depth = radius
    cu.bevel_resolution = 2
    s = cu.splines.new("POLY")
    s.points.add(len(points) - 1)
    for p, xyz in zip(s.points, points):
        p.co = (*xyz, 1.0)
    s.use_cyclic_u = closed
    o = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(mat)
    return o


def island(sand, wet, rim):
    N = 64
    verts = [(0.0, 0.0, 0.37)]
    rings = [(1.45, 0.37), (3.25, 0.34), (3.85, 0.23),
             (4.15, -0.035), (4.26, -0.17)]
    for radius, z in rings:
        for i in range(N):
            a = TAU * i / N
            wobble = 1 + 0.025 * math.sin(5*a) + 0.018 * math.sin(9*a + 1.3)
            x = radius * math.cos(a) * wobble
            y = radius * math.sin(a) * 0.80 * wobble
            verts.append((x, y, z + 0.017 * math.sin(4*a)))
    faces, inds = [], []
    for i in range(N):
        faces.append((0, 1+i, 1+(i+1) % N))
        inds.append(0)
    for j in range(len(rings)-1):
        for i in range(N):
            a = 1 + j*N + i
            b = 1 + j*N + (i+1) % N
            c = 1 + (j+1)*N + (i+1) % N
            d = 1 + (j+1)*N + i
            faces.append((a, d, c, b))
            inds.append(0 if j < 2 else 1 if j == 2 else 2)
    beach = object_mesh("Sculpted golden-sand island", verts, faces,
                        [sand, wet, rim], inds)
    bevel = beach.modifiers.new("Gently soften sandy shore", "BEVEL")
    bevel.width = 0.07
    bevel.segments = 2
    beach.modifiers.new("Beach weighted normals", "WEIGHTED_NORMAL")


def palm(name, x, y, h, lean_x, lean_y, bark, band, leaves, coconut, fcount):
    base = Vector((x, y, 0.35))
    coords = []
    for i in range(10):
        t = i/9
        coords.append(base + Vector((lean_x*t*t, lean_y*t*t, h*t)))
    for i in range(len(coords)-1):
        rod(name + " trunk %02d" % i, coords[i], coords[i+1],
            0.215 - 0.095*(i/9), bark, 12)
    for i in (2, 4, 6, 8):
        p, q = coords[i], coords[i+1]
        v = (q-p).normalized()
        rod(name + " bark ring %d" % i, p-v*0.025, p+v*0.025,
            0.225 - 0.09*(i/9), band, 12)
    top = coords[-1]
    uv_sphere(name + " palm crown", top, 0.25, bark)
    for i in range(3):
        a = TAU*i/3
        uv_sphere(name + " coconut", top + Vector((0.19*math.cos(a), 0.19*math.sin(a), -0.22)),
                  0.17, coconut, segments=16)
    for i in range(9):
        theta = TAU*i/9
        length = (2.1 + 0.32*math.sin(i*2.1)) * (0.82 if h < 3.2 else 1)
        verts, faces = [], []
        for k in range(13):
            t = k/12
            dist = length*t
            z = 0.12 + 0.34*math.sin(math.pi*t) - 0.91*t*t
            center = Vector((math.cos(theta)*dist, math.sin(theta)*dist, z))
            width = 0.40 * (max(0.0, math.sin(math.pi*t))**0.75)
            across = Vector((-math.sin(theta), math.cos(theta), 0))
            verts.extend((center + across*width, center - across*width))
        for k in range(12):
            faces.append((2*k, 2*k+1, 2*k+3, 2*k+2))
        leaf = object_mesh(name + " frond %d" % i, verts, faces,
                           leaves[i % len(leaves)])
        # Each frond has its pivot at the crown for a looping ocean-breeze sway.
        pivot = bpy.data.objects.new(name + " animated frond pivot %d" % i, None)
        bpy.context.collection.objects.link(pivot)
        pivot.location = top
        leaf.parent = pivot
        for frame, t in ((1, 0), (1+fcount//4, .25),
                         (1+fcount//2, .5), (1+3*fcount//4, .75),
                         (1+fcount, 1)):
            pivot.rotation_euler = (
                0.05*math.sin(TAU*t + i*.4),
                0.06*math.cos(TAU*t + i*.5),
                0.025*math.sin(TAU*t + i*.2),
            )
            pivot.keyframe_insert(data_path="rotation_euler", frame=frame)


def parasol(name, x, y, pole, fabrics):
    z0, radius, n = 0.37, 1.12, 12
    rod(name + " wooden pole", (x,y,z0), (x,y,2.77), 0.055, pole)
    verts = [(x,y,2.78)]
    for i in range(n):
        a = TAU*i/n
        verts.append((x+radius*math.cos(a), y+radius*math.sin(a),
                      2.12 + 0.035*math.cos(6*a)))
    faces = [(0, 1+i, 1+(i+1)%n) for i in range(n)]
    canopy = object_mesh(name + " coral-and-cream fabric", verts, faces, fabrics,
                         [i % len(fabrics) for i in range(n)])
    solid = canopy.modifiers.new("Subtle fabric thickness", "SOLIDIFY")
    solid.thickness = 0.025
    uv_sphere(name + " top finial", (x,y,2.83), 0.095, pole, segments=16)


def deck_chair(x, y, wood, canvas):
    # An airy lounger next to the umbrella.
    for side in (-0.43, 0.43):
        rod("Lounger long side", (x+side,y-0.72,0.65),
            (x+side,y+0.45,0.65), 0.058, wood)
        rod("Lounger back", (x+side,y+0.30,0.65),
            (x+side,y+0.99,1.38), 0.058, wood)
        for yy in (-0.5, 0.30):
            rod("Lounger leg", (x+side,y+yy,0.36),
                (x+side,y+yy,0.65), 0.047, wood)
    seat = cube("Turquoise lounger seat", (x,y-0.15,0.655),
                (0.79,1.10,0.055), canvas, 0.05)
    back = cube("Turquoise lounger back", (x,y+0.66,1.02),
                (0.79,1.00,0.055), canvas, 0.045)
    back.rotation_euler.x = math.radians(43)


def beach_ball(location, colors, fcount):
    ball = uv_sphere("Rolling pastel striped beach ball", location, 0.48,
                     colors[0], segments=48)
    for m in colors[1:]:
        ball.data.materials.append(m)
    for poly in ball.data.polygons:
        c = poly.center
        angle = (math.atan2(c.y, c.x) + TAU) % TAU
        poly.material_index = int(angle / TAU * 8) % len(colors)
        if abs(c.z) > 0.45:
            poly.material_index = 1
    for frame, t in ((1,0), (1+fcount/4,.25), (1+fcount/2,.5),
                     (1+3*fcount/4,.75), (1+fcount,1)):
        ball.rotation_euler = (TAU*t, 0, 0)
        ball.keyframe_insert(data_path="rotation_euler", frame=int(frame))


def starfish(name, x, y, orange):
    verts_top = []
    for k in range(10):
        a = TAU*k/10 + math.pi/2
        r = 0.39 if k%2==0 else 0.155
        verts_top.append((x+r*math.cos(a), y+r*math.sin(a), 0.405))
    verts = verts_top + [(x,y,0.48)] + [
        (vx,vy,0.35) for vx,vy,_ in verts_top
    ]
    faces = []
    for i in range(10):
        faces.append((10, i, (i+1)%10))
        faces.append((i, 11+i, 11+(i+1)%10, (i+1)%10))
    object_mesh(name, verts, faces, orange)


def environment(mats):
    ocean = cube("Endless warm turquoise ocean", (0,0,-0.39),
                 (200,200,0.36), mats["sea"], 0)
    # Soft, broken white foam follows the island edge.
    for shift, phase, thickness in ((4.28,0.1,0.034), (4.47,0.55,0.019)):
        for part in range(7):
            points = []
            start = part*TAU/7 + phase
            for j in range(15):
                a = start + (j/14)*TAU/7*.68
                rr = shift + .055*math.sin(11*a)
                points.append((rr*math.cos(a),
                               rr*0.80*math.sin(a), -0.19))
            stroke("Curved sea-foam whitecap", points, thickness, mats["foam"])
    for k in range(26):
        x = RNG.uniform(-8.5, 8.5)
        y = RNG.uniform(-7.0, 6.0)
        if abs(x) < 5 and abs(y) < 4.1:
            continue
        t = RNG.uniform(0.25, .8)
        pts = [(x+t*(j/10-0.5), y+0.09*math.sin(j/10*math.pi),
                -0.204) for j in range(11)]
        stroke("Distant sparkling water ripples", pts, 0.012, mats["foam"])
    island(mats["sand"], mats["wet_sand"], mats["shore"])
    for i in range(22):
        a = RNG.uniform(0, TAU)
        r = RNG.uniform(1.8, 3.25)
        x,y = r*math.cos(a),r*.80*math.sin(a)
        # Little green beach-grass tufts.
        for dx in (-0.075, 0, 0.075):
            rod("Dune grass", (x+dx,y,0.36), (x+dx*.7,y+.03,0.54+RNG.random()*.13),
                0.015, mats["grass"], 6)


def set_camera_and_titles(mats, fcount):
    bpy.ops.object.camera_add(location=(8.6,-12.0,8.4))
    camera = bpy.context.object
    camera.name = "Slow orbit hero camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 14.6
    bpy.context.scene.camera = camera
    for frame, offset in ((1,0), (1+fcount//4,1), (1+fcount//2,0),
                          (1+3*fcount//4,-1), (1+fcount,0)):
        camera.location = (8.6+0.62*offset, -12.0+0.30*offset, 8.4+0.14*offset)
        target = Vector((0,0,1.20))
        direction = target - camera.location
        camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        camera.keyframe_insert(data_path="location", frame=frame)
        camera.keyframe_insert(data_path="rotation_euler", frame=frame)
    # A lightweight camera-space title, always legible during the camera orbit.
    def text_overlay(label, size, y, material):
        cu = bpy.data.curves.new(label, "FONT")
        cu.body = label
        cu.align_x = "CENTER"
        cu.align_y = "CENTER"
        cu.size = size
        cu.extrude = 0.0
        ob = bpy.data.objects.new(label + " title overlay", cu)
        bpy.context.collection.objects.link(ob)
        ob.parent = camera
        ob.location = (0, y, -8)
        cu.materials.append(material)
        return ob
    text_overlay("S U M M E R", 0.74, 2.75, mats["title"])
    text_overlay("I S L A N D   D R E A M S", 0.20, 2.19, mats["title"])


def make_cloud(name, x, y, z, white, fcount):
    parent = bpy.data.objects.new(name + " floating pivot", None)
    bpy.context.collection.objects.link(parent)
    parent.location = (x,y,z)
    puffs = [(-.7,0,.02,.52), (-.28,0,.17,.72), (.3,0,.03,.64),
             (.72,0,-.08,.43), (0,-.23,-.16,.48)]
    for px,py,pz,r in puffs:
        ob = uv_sphere(name + " fluffy puff",
                       (x+px,y+py,z+pz),r,white,
                       scale=(1,1,.65), segments=20)
        ob.parent = parent
        # Preserve position after parenting with an explicit local transform.
        ob.location = (px,py,pz)
    for frame,t in ((1,0),(1+fcount//4,.25),(1+fcount//2,.5),
                    (1+3*fcount//4,.75),(1+fcount,1)):
        parent.location.x = x+0.18*math.sin(TAU*t)
        parent.location.z = z+0.09*math.sin(TAU*t)
        parent.keyframe_insert(data_path="location", frame=frame)


def main():
    a = parse_args()
    if min(a.width, a.height, a.fps, a.frames, a.samples) <= 0:
        raise ValueError("All render parameters must be positive")
    output = os.path.abspath(a.output_dir)
    os.makedirs(output, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = a.samples
    scene.cycles.use_adaptive_sampling = True
    if hasattr(scene.cycles, "use_denoising"):
        scene.cycles.use_denoising = True
    if hasattr(bpy.context.view_layer, "cycles"):
        bpy.context.view_layer.cycles.use_denoising = True
    scene.render.resolution_x = a.width
    scene.render.resolution_y = a.height
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.fps = a.fps
    scene.frame_start = 1
    scene.frame_end = a.frames
    scene.render.filepath = os.path.join(output, "frame_")
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    mats = {
        "sand": material("Vanilla gold warm sand", (0.91,0.69,0.37)),
        "wet_sand": material("Saturated honey shoreline", (0.88,0.58,0.29)),
        "shore": material("Darker sand island edge", (0.66,0.40,0.20)),
        "sea": material("Shimmering Caribbean aqua", (0.05,0.67,0.78), .31),
        "foam": material("Ivory ocean whitecap", (0.84,0.99,0.98),.3,emission=.12),
        "palm_bark": material("Cocoa palm wood", (0.40,0.23,0.12)),
        "palm_band": material("Palm bark golden bands", (0.62,0.38,0.17)),
        "coconut": material("Dark coconut", (0.30,0.17,0.10)),
        "palm_bright": material("Lime green frond", (0.25,0.68,0.25)),
        "palm_deep": material("Deep green frond", (0.07,0.48,0.28)),
        "palm_light": material("Sunlit teal leaf", (0.33,0.78,0.39)),
        "grass": material("Dune grass", (0.24,0.59,0.27)),
        "parasol_red": material("Vintage coral beach umbrella", (0.95,0.34,0.25)),
        "parasol_cream": material("Vanilla striped canopy", (1.0,0.90,0.67)),
        "parasol_yellow": material("Mango yellow canopy", (1.0,0.69,0.18)),
        "wood": material("Honey wooden furnishings", (0.56,0.30,0.17)),
        "canvas": material("Mint lounge fabric", (0.17,0.71,0.65)),
        "ball_blue": material("Ball mint stripe", (0.15,0.69,0.79)),
        "ball_white": material("Ball cream stripe", (0.98,0.92,0.76)),
        "ball_red": material("Ball coral stripe", (1.0,0.39,0.28)),
        "ball_yellow": material("Ball sunny yellow stripe", (1.0,0.75,0.21)),
        "star": material("Coral orange starfish", (1.0,0.47,0.30)),
        "shell": material("Soft peach shells", (0.98,0.78,0.64)),
        "cloud": material("Warm ivory summer clouds", (0.98,0.97,0.88)),
        "title": material("White cinematic titles", (0.99,0.99,0.89),.5,emission=.6),
    }

    environment(mats)
    palm("Tall left palm", -2.5, 1.10, 3.7, .70, -.2,
         mats["palm_bark"], mats["palm_band"],
         [mats["palm_bright"],mats["palm_deep"],mats["palm_light"]],
         mats["coconut"],a.frames)
    palm("Small right palm", 2.7, 1.35, 2.85, -.45, -.15,
         mats["palm_bark"], mats["palm_band"],
         [mats["palm_light"],mats["palm_bright"],mats["palm_deep"]],
         mats["coconut"],a.frames)
    parasol("Seaside striped umbrella", 1.15, -0.55, mats["wood"],
            [mats["parasol_red"],mats["parasol_cream"],
             mats["parasol_yellow"],mats["parasol_cream"]])
    deck_chair(-0.15, -0.15, mats["wood"], mats["canvas"])
    beach_ball((-1.65,-1.50,0.81),
               [mats["ball_blue"],mats["ball_white"],
                mats["ball_red"],mats["ball_yellow"]], a.frames)
    starfish("Five-point coral starfish", 2.05, -2.05, mats["star"])
    for i in range(9):
        x = RNG.uniform(-2.8,2.7)
        y = RNG.uniform(-2.25,1.4)
        if (x+1.65)**2+(y+1.50)**2 < 0.6:
            continue
        uv_sphere("Tiny peach seashell", (x,y,.39),
                  RNG.uniform(.055,.12),mats["shell"],
                  scale=(1.4,.75,.45),segments=12)
    make_cloud("Sky cloud left", -4.3, 2.9, 5.0, mats["cloud"],a.frames)
    make_cloud("Sky cloud right", 4.15, 3.6, 4.85, mats["cloud"],a.frames)

    # Large soft key and fill lights keep the miniature readable on CPU.
    def area_light(name, loc, energy, color, size):
        bpy.ops.object.light_add(type="AREA", location=loc)
        lamp = bpy.context.object
        lamp.name = name
        lamp.data.energy = energy
        lamp.data.color = color
        lamp.data.shape = "DISK"
        lamp.data.size = size
        direction = Vector((0,0,0.6)) - lamp.location
        lamp.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    area_light("Warm summer afternoon sunlight", (-4,-5,9), 1800, (1.0,.83,.65), 7.0)
    area_light("Soft ocean-blue bounce fill", (5,3,6), 950, (.65,.87,1.0), 8.0)
    scene.world.color = (.5,.7,.9)
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (.52,.77,.90,1)
    background.inputs["Strength"].default_value = 0.70

    set_camera_and_titles(mats,a.frames)
    scene.frame_set(1)
    scene.render.image_settings.color_depth = "8"
    project_file = os.path.join(os.path.dirname(output), "summer_paradise.blend")
    bpy.ops.wm.save_as_mainfile(filepath=project_file)
    print("SUMMER_PROJECT", project_file, flush=True)
    print("SUMMER_FRAME_DIR", output, flush=True)
    bpy.ops.render.render(animation=True)
    print("SUMMER_RENDER_COMPLETE",flush=True)


if __name__ == "__main__":
    main()
