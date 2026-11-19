"""Lip-sync check for a cut made by cut.py: for every 7th piece, find which source frame the cut shows and
compare it with where that moment's audio comes from. 0..1 frame = in sync.
usage: python3 vcheck.py SOURCE CUT.mp4 CUT.segments.json SPEED"""
import sys, json, subprocess, numpy as np
src, cut, segj, speed = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
FD = 1001 / 30000
def frame(path, t):
    b = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", path, "-map", "0:v:0", "-frames:v", "1", "-vf", "scale=135:240", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
    return np.frombuffer(b, np.uint8).astype(np.float32)
segs = json.load(open(segj))
for o0, o1, tag, r0, r1 in segs[::7]:
    to = o0 + 0.4                      # a moment inside the piece (output time)
    ts = r0 + (to - o0) * speed        # where audio for that moment comes from in the source
    c = frame(cut, to)
    errs = [(np.abs(frame(src, ts + k * FD) - c).mean(), k) for k in range(-6, 7)]
    best = min(errs)[1]
    print(f"out {o0:6.2f}s  video is {best:+d} frames vs audio (+ = picture shows later source moment)")
