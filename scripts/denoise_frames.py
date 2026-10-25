#!/usr/bin/env python3
"""Edge-aware cleanup of Cycles CPU frames with OpenCV.

All input pixels were physically rendered by Blender; this filters only
Monte-Carlo render noise. It never adds or edits scene geometry or source shots.
"""
import argparse
import glob
import os
import pathlib

import cv2


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="output/backrooms/frames")
    p.add_argument("--output",default="output/backrooms/clean")
    p.add_argument("--strength",type=int,default=14)
    a=p.parse_args()
    src=sorted(glob.glob(os.path.join(a.input,"frame_*.png")))
    if not src:
        raise RuntimeError("No Blender Cycles rendered frames to denoise")
    os.makedirs(a.output,exist_ok=True)
    for i,path in enumerate(src):
        frame=cv2.imread(path,cv2.IMREAD_COLOR)
        if frame is None:
            raise RuntimeError("Cannot open Blender rendering: "+path)
        cleaned=cv2.fastNlMeansDenoisingColored(
            frame,None,a.strength,a.strength,7,21)
        dest=os.path.join(a.output,os.path.basename(path))
        if not cv2.imwrite(dest,cleaned):
            raise RuntimeError("Unable to save denoised frame: "+dest)
        if i%30==0:
            print("DENOISED_BLENDER_FRAMES",i+1,"/",len(src),flush=True)
    if len(list(pathlib.Path(a.output).glob("frame_*.png")))!=len(src):
        raise RuntimeError("Denoiser did not produce all Blender frames")
    print("DENOISED_ALL_ORIGINAL_BLENDER_FRAMES",len(src),flush=True)


if __name__=="__main__":
    main()
