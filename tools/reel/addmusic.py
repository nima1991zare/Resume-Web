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

# ── the bed — an energetic, modern house/EDM bed at 128 BPM ───────────────
# Commas inside an expression are escaped (\,) for ffmpeg's own parser; the
# whole graph is passed as one argv element so the shell never touches it.
#
#   B    = one beat at 128 BPM = 0.46875s
# kick   : punchy four-on-the-floor — a low sine plus a click transient
# clap   : noise burst on the back-beat (2 and 4), the thing that drives it
# bass   : an off-beat saw-ish bass, house-style, between the kicks
# pad    : a D-major chord SIDECHAINED to the kick — it ducks on every beat and
#          swells back, which is the pump that reads as "modern/energetic"
# hats   : bright eighth-note ticks for lift
B = 0.46875
KICK = r"(sin(2*PI*52*t)*exp(-8*mod(t\,0.46875))+(2*random(0)-1)*exp(-150*mod(t\,0.46875))*0.4)*0.95"
CLAP = r"(2*random(0)-1)*exp(-23*mod(t+0.46875\,0.9375))*0.38"
BASS = r"(sin(2*PI*73.42*t)+0.5*sin(2*PI*146.84*t))*exp(-9*mod(t+0.234375\,0.46875))*0.17"
PAD = r"(sin(2*PI*146.83*t)+sin(2*PI*220*t)+sin(2*PI*293.66*t)+sin(2*PI*369.99*t))*0.026*(0.22+0.78*(1-exp(-9*mod(t\,0.46875))))"
HAT = r"(2*random(0)-1)*exp(-70*mod(t\,0.234375))*0.05"

FILTER = (
    f"aevalsrc={KICK}:d={DUR}:s=44100[k];"
    f"aevalsrc={CLAP}:d={DUR}:s=44100[c];"
    f"aevalsrc={BASS}:d={DUR}:s=44100[b];"
    f"aevalsrc={PAD}:d={DUR}:s=44100[p];"
    f"aevalsrc={HAT}:d={DUR}:s=44100[h];"
    "[k][c][b][p][h]amix=inputs=5:normalize=0,"
    "highpass=f=26,"
    # glue the hits together and give the kick punch
    "acompressor=threshold=-18dB:ratio=3:attack=5:release=120,"
    # a little air so it reads bright/current, not muddy
    "treble=g=3:f=4500,"
    "volume=1.15,"
    # quick in for energy, clean out; limiter so nothing clips
    "afade=t=in:st=0:d=0.3,afade=t=out:st=18.4:d=1.6,"
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
