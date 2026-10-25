#!/usr/bin/env python3
"""Blender CLI VSE edit of real-life summer footage.

This is footage editing and video rendering, NOT a cartoon/CGI animation.
Example:
  blender -b --factory-startup --python scripts/real_summer.py -- \
    --shots-dir output/source --output output/summer_real.mp4
"""
import argparse
import glob
import os
import shutil
import sys

import bpy


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--shots-dir", default="output/source")
    p.add_argument("--output", default="output/summer_real.mp4")
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--fps", type=int, default=25)
    p.add_argument("--shot-seconds", type=float, default=4.0)
    p.add_argument("--fade-frames", type=int, default=10)
    a = p.parse_args(args)

    shots = sorted(glob.glob(os.path.join(a.shots_dir, "clip_*.mp4")))
    if len(shots) < 2:
        raise RuntimeError("Expected at least two normalized real-footage shots.")
    if a.fade_frames < 0:
        raise ValueError("--fade-frames cannot be negative")
    shot_frames = int(a.shot_seconds * a.fps)
    if shot_frames < a.fade_frames + 10:
        raise ValueError("Crossfade is too long for the clip duration")

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.resolution_x = a.width
    scene.render.resolution_y = a.height
    scene.render.resolution_percentage = 100
    scene.render.fps = a.fps
    scene.frame_start = 1
    scene.render.use_sequencer = True
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1

    edit = scene.sequence_editor_create()
    seqs = getattr(edit, "strips", None)
    if seqs is None:
        seqs = edit.sequences
    start = 1

    for idx, path in enumerate(shots):
        strip = seqs.new_movie("REAL FILMED COAST SHOT {}".format(idx+1),
                               os.path.abspath(path), idx+1, start)
        strip.color_saturation = 1.01
        strip.color_multiply = 1.005
        # The upper strip fades in over the previous filmed shot.
        if idx:
            strip.blend_type = "ALPHA_OVER"
            strip.blend_alpha = 0.0
            strip.keyframe_insert(data_path="blend_alpha", frame=start)
            strip.blend_alpha = 1.0
            strip.keyframe_insert(
                data_path="blend_alpha", frame=start + a.fade_frames)
        else:
            strip.blend_type = "REPLACE"
        start += shot_frames - a.fade_frames if idx < len(shots)-1 else shot_frames

    total_frames = len(shots) * shot_frames - (len(shots)-1) * a.fade_frames
    scene.frame_end = total_frames
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    scene.render.ffmpeg.audio_codec = "NONE"

    target = os.path.abspath(a.output)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    render_prefix = os.path.join(os.path.dirname(target), "blender_vse_render_")
    scene.render.filepath = render_prefix
    scene.render.use_file_extension = True

    project = os.path.join(os.path.dirname(target), "summer_real_edit.blend")
    bpy.ops.wm.save_as_mainfile(filepath=project)
    print("BLENDER_VSE_PROJECT", project, flush=True)
    print("START_REAL_FOOTAGE_RENDER", total_frames, a.width, a.height, flush=True)
    bpy.ops.render.render(animation=True)

    result_candidates = sorted(
        glob.glob(render_prefix + "*.mp4"), key=os.path.getmtime, reverse=True)
    if not result_candidates:
        raise RuntimeError("Blender VSE did not produce a video")
    shutil.move(result_candidates[0], target)
    if os.path.getsize(target) < 100_000:
        raise RuntimeError("Rendered MP4 is suspiciously small")
    print("BLENDER_REAL_SUMMER_VIDEO_COMPLETE", target, os.path.getsize(target),
          flush=True)


if __name__ == "__main__":
    main()
