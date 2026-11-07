"""Synthesize a royalty-free track (beat bed + melody) and mux it onto a reel.

    python addmusic.py            # out/reel.mp4  -> out/reel_music.mp4
    python addmusic.py show       # out/show.mp4  -> out/show_music.mp4

Instagram mutes copyrighted audio on anything not added through its own music
picker, so a downloaded song would silence the Reel. Everything here is
original: a 128-bpm house bed (punchy kick, back-beat clap, off-beat bass, a
chord pad sidechained to the kick so it pumps) and, on top, a plucked lead
MELODY sequenced note by note in C-major pentatonic — pentatonic because every
note in it sits consonant against the others, which keeps it safe even though
nobody here can hear the result before it ships.
"""
from __future__ import annotations
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
BASE = (sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "reel")
SRC = HERE / "out" / f"{BASE}.mp4"
DST = HERE / "out" / f"{BASE}_music.mp4"
DUR = 15 if BASE == "show" else 20

# ── the beat bed (128 BPM) ────────────────────────────────────────────────
KICK = r"(sin(2*PI*52*t)*exp(-8*mod(t\,0.46875))+(2*random(0)-1)*exp(-150*mod(t\,0.46875))*0.4)*0.9"
CLAP = r"(2*random(0)-1)*exp(-23*mod(t+0.46875\,0.9375))*0.34"
BASS = r"(sin(2*PI*73.42*t)+0.5*sin(2*PI*146.84*t))*exp(-9*mod(t+0.234375\,0.46875))*0.16"
PAD = r"(sin(2*PI*146.83*t)+sin(2*PI*220*t)+sin(2*PI*293.66*t)+sin(2*PI*369.99*t))*0.024*(0.22+0.78*(1-exp(-9*mod(t\,0.46875))))"
HAT = r"(2*random(0)-1)*exp(-70*mod(t\,0.234375))*0.045"

# ── the melody — a plucked lead, C-major pentatonic, on eighth notes ───────
# A rising-then-falling motif that loops; the ear reads a tune, and pentatonic
# means no note can clash with the pad underneath.
MOTIF = [659.25, 783.99, 880.0, 1046.5, 880.0, 783.99, 659.25, 587.33,
         523.25, 659.25, 783.99, 880.0, 783.99, 659.25, 587.33, 523.25]
STEP = 0.234375          # eighth note at 128 bpm


def melody_expr() -> str:
    terms = []
    n = int(DUR / STEP) + 1
    for i in range(n):
        s = i * STEP
        if s >= DUR:
            break
        f = MOTIF[i % len(MOTIF)]
        e = s + 0.2
        # a plucked note: a sine that starts at s and decays; windowed to its slot
        terms.append(
            f"sin(2*PI*{f:.2f}*(t-{s:.4f}))*between(t\\,{s:.4f}\\,{e:.4f})*exp(-10*(t-{s:.4f}))")
    return "(" + "+".join(terms) + ")*0.085"


FILTER = (
    f"aevalsrc={KICK}:d={DUR}:s=44100[k];"
    f"aevalsrc={CLAP}:d={DUR}:s=44100[c];"
    f"aevalsrc={BASS}:d={DUR}:s=44100[b];"
    f"aevalsrc={PAD}:d={DUR}:s=44100[p];"
    f"aevalsrc={HAT}:d={DUR}:s=44100[h];"
    f"aevalsrc={melody_expr()}:d={DUR}:s=44100[m];"
    "[k][c][b][p][h][m]amix=inputs=6:normalize=0,"
    "highpass=f=26,"
    "acompressor=threshold=-18dB:ratio=3:attack=5:release=120,"
    "treble=g=3:f=4500,"
    "volume=1.1,"
    f"afade=t=in:st=0:d=0.3,afade=t=out:st={DUR - 1.6}:d=1.6,"
    "alimiter=limit=0.95[a]"
)


def main() -> int:
    if not SRC.exists():
        sys.exit(f"out/{BASE}.mp4 is missing — render it first.")
    cmd = [
        "ffmpeg", "-y", "-i", str(SRC),
        "-filter_complex", FILTER,
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(DST),
    ]
    print(f"synthesizing bed + melody and muxing onto {BASE}.mp4…")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-1500:])
        return r.returncode
    mb = DST.stat().st_size / 1048576
    print(f"\n{DST}  ({mb:.1f} MB)")
    print("Preview the sound before posting. In-app trending audio reaches")
    print("further on Reels — this track is the ready alternative.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
