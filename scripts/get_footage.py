#!/usr/bin/env python3
"""Download licensed, REAL beach footage and normalize it for Blender VSE.

The input videos were filmed by their named creators on Pexels. No AI-generated
or procedurally modelled images are used in the resulting video.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys


def run(argv):
    print("+", " ".join(map(str, argv)), flush=True)
    subprocess.run(argv, check=True)


def is_video(path):
    if not os.path.isfile(path) or os.path.getsize(path) < 200_000:
        return False
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name,width,height",
         "-of", "json", path],
        capture_output=True, text=True)
    if p.returncode:
        return False
    try:
        v = json.loads(p.stdout)["streams"][0]
        return v["width"] >= 720 and v["height"] >= 400
    except (ValueError, IndexError, KeyError):
        return False


def obtain_clip(meta, root):
    ident, fps = str(meta["id"]), meta["fps"]
    base = "https://videos.pexels.com/video-files/{0}/{0}-".format(ident)
    candidates = [
        base + "hd_1920_1080_{}fps.mp4".format(fps),
        base + "hd_1280_720_{}fps.mp4".format(fps),
        base + "uhd_3840_2160_{}fps.mp4".format(fps),
        "https://www.pexels.com/video/{}/download/".format(ident),
    ]
    dst = os.path.join(root, "source_{}.mp4".format(ident))
    if is_video(dst):
        return dst
    for url in candidates:
        if os.path.exists(dst):
            os.remove(dst)
        print("DOWNLOAD", ident, url, flush=True)
        cmd = ["curl", "--fail", "--location", "--retry", "2",
               "--connect-timeout", "15", "--max-time", "180",
               "--user-agent", "Mozilla/5.0 (compatible; SummerBlenderWorkflow/1.0)",
               "--output", dst, url]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL)
        if result.returncode == 0 and is_video(dst):
            print("DOWNLOADED", dst, os.path.getsize(dst), flush=True)
            return dst
        print("UNAVAILABLE", url, flush=True)
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source-list", default="sources.json")
    p.add_argument("--output-dir", default="output/source")
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--seconds", type=float, default=4.0)
    p.add_argument("--fps", type=int, default=25)
    p.add_argument("--max-clips", type=int, default=3)
    a = p.parse_args()
    if a.width < 640 or a.height < 360 or a.seconds < 2 or a.fps < 1:
        p.error("Invalid video dimensions, duration, or frame rate")

    root = os.path.abspath(a.output_dir)
    os.makedirs(root, exist_ok=True)
    config = json.loads(pathlib.Path(a.source_list).read_text(encoding="utf-8"))
    used = []
    frames = int(round(a.seconds * a.fps))

    for meta in config["clips"]:
        if len(used) >= a.max_clips:
            break
        raw = obtain_clip(meta, root)
        if not raw:
            print("WARNING: Cannot fetch clip ID {}".format(meta["id"]), flush=True)
            continue
        output = os.path.join(root, "clip_{:02d}.mp4".format(len(used)+1))
        vf = ("fps={},scale={}:{}:force_original_aspect_ratio=increase,"
              "crop={}:{},setsar=1,format=yuv420p").format(
                 a.fps, a.width, a.height, a.width, a.height)
        try:
            run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                 "-ss", "0.5", "-i", raw,
                 "-an", "-vf", vf, "-frames:v", str(frames),
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                 "-pix_fmt", "yuv420p", "-movflags", "+faststart", output])
            if not is_video(output):
                raise RuntimeError("Invalid processed shot")
        except (subprocess.CalledProcessError, RuntimeError) as exc:
            print("WARNING: normalization failed", exc, flush=True)
            if os.path.exists(output):
                os.remove(output)
            continue
        used.append({"id":meta["id"], "artist":meta["artist"],
                     "page":meta["page"], "shot":output})
        print("READY", output, flush=True)

    if len(used) < 2:
        raise RuntimeError("Need 2 usable real-footage clips; source downloads failed.")
    pathlib.Path(root, "used_sources.json").write_text(
        json.dumps(used, ensure_ascii=False, indent=2), encoding="utf-8")
    print("READY_REAL_LIVE_ACTION_SHOTS", len(used), flush=True)


if __name__ == "__main__":
    main()
