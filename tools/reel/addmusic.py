"""Synthesize a royalty-free bed and mux it onto reel.mp4 -> reel_music.mp4.

Why synthesized and not a track off the internet: Instagram mutes or blocks
copyrighted audio on anything that is not posted through its own music picker,
so a downloaded song would get the Reel silenced. A tone bed generated here is
original and safe, and it can be swapped for Instagram's in-app audio anytime.

The bed matches the video's arc — a steady pulse that carries the count-up,
a warm sustained pad under it, and fades at both ends so it never starts or
stops abruptly. Everything is low and wide on purpose; it sits under speech-free
motion graphics without fighting the on-screen numbers.
"""
from __future__ import annotations
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "out" / "reel.mp4"
DST = HERE / "out" / "reel_music.mp4"
DUR = 20

# ── the bed, as ffmpeg lavfi expressions ──────────────────────────────────
# Commas inside an expression are escaped (\,) for ffmpeg's own parser; passing
# the filtergraph as one argv element keeps the shell out of it entirely.
#
# kick  : a 55 Hz sine that decays every half second — a calm 120-bpm heartbeat
# pad   : a soft D-rooted chord (D3, A3, D4), the warm sustained layer
# sub   : a low drone an octave under the pad, for body on phone speakers
# hat   : filtered noise ticking on the off-beat, quiet, for a little motion
KICK = r"sin(2*PI*55*t)*exp(-11*mod(t\,0.5))*0.9"
PAD = r"(sin(2*PI*146.83*t)+sin(2*PI*220*t)+sin(2*PI*293.66*t)*0.7)*0.045"
SUB = r"sin(2*PI*73.42*t)*0.10"
HAT = r"(2*random(0)-1)*exp(-55*mod(t+0.25\,0.5))*0.06"

FILTER = (
    f"aevalsrc={KICK}:d={DUR}:s=44100[k];"
    f"aevalsrc={PAD}:d={DUR}:s=44100[p];"
    f"aevalsrc={SUB}:d={DUR}:s=44100[s];"
    f"aevalsrc={HAT}:d={DUR}:s=44100[h];"
    "[k][p][s][h]amix=inputs=4:normalize=0,"
    # a gentle swell into the 92% reveal (~6s), then settle
    "volume='0.75+0.2*sin(2*PI*0.5*t)*between(t\\,5\\,7)':eval=frame,"
    "highpass=f=28,lowpass=f=11000,"
    "afade=t=in:st=0:d=1.4,afade=t=out:st=17.6:d=2.4,"
    # a safety limiter so nothing clips if the layers line up
    "alimiter=limit=0.95[a]"
)


def main() -> int:
    if not SRC.exists():
        sys.exit("out/reel.mp4 is missing — run:  python build.py && node render.js")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(SRC),
        "-filter_complex", FILTER,
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(DST),
    ]
    print("synthesizing bed and muxing…")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-1500:])
        return r.returncode
    mb = DST.stat().st_size / 1048576
    print(f"\n{DST}  ({mb:.1f} MB)")
    print("Preview it before posting. For a Reel, Instagram's own in-app music")
    print("(trending audio) reaches further — this bed is the ready alternative.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
