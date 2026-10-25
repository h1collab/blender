#!/usr/bin/env python3
"""Create royalty-free procedural *audio* for the real-footage POV film.

No external music or copyrighted recordings. A restrained 48/96-Hz electrical
hum, room ventilation, footfalls, and occasional distant metallic noises.
"""
import argparse
import math
import os
import random
import struct
import wave


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="output/backrooms/ambience.wav")
    p.add_argument("--seconds",type=int,default=30)
    p.add_argument("--sample-rate",type=int,default=24000)
    a=p.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.output)),exist_ok=True)
    rng=random.Random(725)
    sr=a.sample_rate
    tau=math.tau
    low_noise=0.
    with wave.open(a.output,"wb") as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(sr)
        packet=bytearray()
        for n in range(sr*a.seconds):
            t=n/sr
            low_noise=.988*low_noise+.012*(rng.random()*2-1)
            electrical=(.018*math.sin(tau*49.5*t)
                      + .006*math.sin(tau*99*t)
                      + .003*math.sin(tau*410*t)*(.6+.4*math.sin(tau*.18*t)))
            air=.021*low_noise
            # Uneven walking cadence, deliberately quieter on carpet.
            gait=.77
            phase=(t-1.0)%gait
            gate=math.exp(-29*phase) if t>=1 else 0.
            step=(.026*math.sin(tau*76*t)+.016*(rng.random()*2-1))*gate
            # Brief distant metallic taps. Avoid an exaggerated jump-scare cue.
            clang=0.
            for when in (13.4,23.8,27.1):
                delta=t-when
                if 0<=delta<1.5:
                    clang+=.010*math.exp(-4.0*delta)*(
                        math.sin(tau*386*delta)+.40*math.sin(tau*612*delta))
            fade=min(1.,max(0.,t/.8),max(0.,(a.seconds-t)/.85))
            signal=max(-.88,min(.88, (electrical+air+step+clang)*fade))
            left=int(32767*signal)
            right=int(32767*max(-.88,min(.88,signal*.96 + .002*low_noise)))
            packet+=struct.pack("<hh",left,right)
            if len(packet)>32768:
                out.writeframesraw(packet)
                packet.clear()
        if packet:
            out.writeframesraw(packet)
    print("GENERATED_HOSPITAL_AMBIENCE",a.output,
          os.path.getsize(a.output),flush=True)


if __name__=="__main__":
    main()
