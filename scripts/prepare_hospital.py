#!/usr/bin/env python3
"""Prepare real filmed material for a 30-second abandoned-hospital POV edit.

No AI images, CGI corridors, or invented 'actual hospital' footage. The story is
a fictional hospital exploration assembled from correctly credited real footage.
"""
import argparse
import json
import math
import os
import pathlib
import subprocess


def command(args):
    print("+", " ".join(map(str, args)), flush=True)
    subprocess.run(args, check=True)


def probe(path):
    if not os.path.isfile(path) or os.path.getsize(path) < 200_000:
        return None
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name,width,height,nb_frames",
         "-show_entries", "format=duration", "-of", "json", path],
        capture_output=True, text=True)
    try:
        data = json.loads(p.stdout)
        v = data["streams"][0]
        duration = float(data["format"]["duration"])
        if p.returncode or v["width"] < 720 or v["height"] < 400 or duration < 1:
            return None
        return {"duration":duration,"width":v["width"],"height":v["height"]}
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def fetch_video(meta, cache):
    ident = str(meta["id"])
    dst = os.path.join(cache,"pexels_{}.mp4".format(ident))
    if probe(dst):
        return dst
    fps = [meta["source_fps"], 30, 24, 25, 60]
    fps = list(dict.fromkeys(fps))
    urls = []
    for size in ("hd_1920_1080", "hd_1280_720"):
        for speed in fps:
            urls.append("https://videos.pexels.com/video-files/{0}/{0}-{1}_{2}fps.mp4".format(
                ident,size,speed))
    for url in urls:
        if os.path.exists(dst):
            os.remove(dst)
        print("TRY_SOURCE",ident,url,flush=True)
        r = subprocess.run(
            ["curl","-fLSs","--retry","2","--retry-delay","1",
             "--connect-timeout","12","--max-time","90",
             "-A","Mozilla/5.0 (compatible; BlenderHospitalPOV/1.0)",
             "-o",dst,url])
        if r.returncode == 0 and probe(dst):
            print("SOURCE_OK",ident,os.path.getsize(dst),flush=True)
            return dst
    print("WARNING: unavailable footage", ident, flush=True)
    return None


def normalize(raw, dst, width, height, fps, frames, offset, grade):
    larger_w = math.ceil((width*1.040)/2)*2
    larger_h = math.ceil((height*1.040)/2)*2
    profiles = {
        "ruins":(-0.028,1.11,0.70,0.96),
        "hallway":(-0.065,1.16,0.73,0.94),
        "ward":(-0.100,1.15,0.61,0.92),
        "night":(-0.014,1.08,0.76,0.98),
    }
    brightness,contrast,sat,gamma = profiles[grade]
    # Subtle head-camera movement. Retains the texture of real filmed spaces.
    vf = (
      "fps={fps},scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,"
      "crop={ow}:{oh}:x='(iw-ow)/2+5*sin(n/15)+2*sin(n/31)':"
      "y='(ih-oh)/2+3*sin(n/19)',"
      "eq=brightness={bright}:contrast={contrast}:saturation={sat}:gamma={gamma},"
      "colorbalance=rs=-0.009:gs=0.009:bs=0.020:"
      "rm=-0.015:gm=0.007:bm=0.023,"
      "vignette=PI/5,format=yuv420p"
    ).format(fps=fps,w=larger_w,h=larger_h,ow=width,oh=height,
             bright=brightness,contrast=contrast,sat=sat,gamma=gamma)
    command([
      "ffmpeg","-hide_banner","-loglevel","error","-y",
      "-ss","{:.3f}".format(offset),"-i",raw,"-an","-vf",vf,
      "-frames:v",str(frames),"-c:v","libx264","-preset","veryfast",
      "-crf","19","-pix_fmt","yuv420p","-movflags","+faststart",dst
    ])
    meta = probe(dst)
    if not meta:
        raise RuntimeError("Normalized clip missing or corrupt: "+dst)
    actual_frames = round(meta["duration"]*fps)
    if actual_frames != frames:
        raise RuntimeError("Expected {} frames, found {} in {}".format(
            frames,actual_frames,dst))


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--spec",default="hospital_sources.json")
    p.add_argument("--output-dir",default="output/backrooms")
    p.add_argument("--width",type=int,default=1920)
    p.add_argument("--height",type=int,default=1080)
    a=p.parse_args()
    if a.width<640 or a.height<360 or a.width%2 or a.height%2:
        p.error("Output must have positive even width and height")
    spec=json.loads(pathlib.Path(a.spec).read_text(encoding="utf-8"))
    frames=sum(s["frames"] for s in spec["shots"])
    frames -= spec["crossfade_frames"]*(len(spec["shots"])-1)
    if frames!=spec["total_frames"] or frames!=spec["fps"]*30:
        raise RuntimeError("Shot timings must add up to exactly 30 seconds")
    root=os.path.abspath(a.output_dir)
    cache=os.path.join(root,"raw")
    shotdir=os.path.join(root,"input")
    os.makedirs(cache,exist_ok=True)
    os.makedirs(shotdir,exist_ok=True)
    used=[]
    for i,shot in enumerate(spec["shots"]):
        print("SECTION",i+1,shot["section"],flush=True)
        frames=shot["frames"]
        duration=frames/spec["fps"]
        result=None
        for candidate in shot["candidates"]:
            raw=fetch_video(candidate,cache)
            if not raw:
                continue
            info=probe(raw)
            if info["duration"] < duration + .12:
                print("SOURCE_TOO_SHORT",candidate["id"],info["duration"],flush=True)
                continue
            offset=min(float(shot["start_at"]),max(0,info["duration"]-duration-.12))
            target=os.path.join(shotdir,"shot_{:02d}.mp4".format(i+1))
            try:
                normalize(raw,target,a.width,a.height,spec["fps"],
                          frames,offset,shot["grade"])
            except (subprocess.CalledProcessError,RuntimeError) as e:
                print("SOURCE_NORMALIZATION_FAILED",candidate["id"],str(e),flush=True)
                if os.path.exists(target):
                    os.remove(target)
                continue
            result={"segment":shot["section"],"id":candidate["id"],
                    "artist":candidate["artist"],"source_title":candidate["title"],
                    "source_page":candidate["page"],"source_start_seconds":round(offset,2),
                    "frames":frames,"file":target}
            print("SHOT_READY",i+1,candidate["id"],flush=True)
            break
        if not result:
            raise RuntimeError("Cannot obtain real footage for section: "+shot["section"])
        used.append(result)
    manifest={
        "title":spec["title"],"license":spec["source_license"],"fps":spec["fps"],
        "width":a.width,"height":a.height,"total_frames":spec["total_frames"],
        "crossfade_frames":spec["crossfade_frames"],
        "note":"Fictional abandoned hospital edit using genuine footage; not all clips were shot at the same physical hospital.",
        "shots":used
    }
    outfile=os.path.join(root,"sources_used.json")
    pathlib.Path(outfile).write_text(json.dumps(manifest,indent=2,ensure_ascii=False),
                                     encoding="utf-8")
    print("ALL_POV_FOOTAGE_READY", len(used), outfile, flush=True)


if __name__=="__main__":
    main()
