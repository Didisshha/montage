"""Rough-cut a raw source: keep chosen phrase ranges, strip micro-pauses inside them, speed up.
Picture and sound of every piece are cut TOGETHER (one ffmpeg call per piece, audio trimmed to the
exact frame count), so lip-sync cannot drift across joins.
usage: python3 cut.py SOURCE KEEP.json OUT.mp4 [speed=1.2]
  CUT_DRY=1  only print how many seconds each range keeps
  CUT_THR=x  voice threshold 0..1 (default 0.25; lower keeps quieter voices)
KEEP.json: [[start, end, "tag"], ...] in source seconds (tag = who speaks, e.g. "L"/"R").
  Add a 4th element "all" to keep a range whole (no pause stripping) - use it for short, quiet key replies.
Writes OUT.mp4 and OUT.segments.json: [[out_start, out_end, tag, src_start, src_end], ...] (output timeline)."""
import sys, json, subprocess, os, shutil, tempfile
import numpy as np

src, keep_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
speed = float(sys.argv[4]) if len(sys.argv) > 4 else 1.2
keep = json.load(open(keep_path, encoding="utf-8"))
SR = 48000
GAP, PAD_IN, PAD_OUT, FADE = 0.20, 0.05, 0.09, 0.006

probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=r_frame_rate", "-of", "json", src], capture_output=True, check=True).stdout)
num, den = map(int, probe["streams"][0]["r_frame_rate"].split("/")); FD = den / num

# --- voice activity (10 ms frames, adaptive threshold)
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                     capture_output=True, check=True).stdout
mono = np.frombuffer(raw, np.float32); hop = 160
rms = np.sqrt(np.add.reduceat(mono ** 2, np.arange(0, len(mono) - hop, hop)) / hop + 1e-12)
db = 20 * np.log10(rms)
floor = np.percentile(db, 10)
thr = floor + float(os.environ.get("CUT_THR", 0.25)) * (np.percentile(db, 95) - floor)
voiced = db > thr

segs = []  # (first_frame, n_frames, tag)
for entry in keep:
    s, e, tag = entry[:3]
    if len(entry) > 3 and entry[3] == "all":  # keep the whole range (short/quiet key replies)
        segs.append((int(round(s / FD)), int(round((e - s) / FD)), tag)); continue
    a, b = int(s * 100), int(e * 100); v = voiced[a:b]; runs = []; i = 0
    while i < len(v):
        if v[i]:
            j = i
            while j < len(v) and v[j]: j += 1
            runs.append([(a + i) / 100, (a + j) / 100]); i = j
        else:
            i += 1
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] < GAP:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    for r0, r1 in merged:
        if r1 - r0 < 0.08:
            continue
        f0 = int(round(max(s, r0 - PAD_IN) / FD)); f1 = int(round(min(e, r1 + PAD_OUT) / FD))
        if segs and segs[-1][2] == tag and f0 <= segs[-1][0] + segs[-1][1]:  # overlapping/adjacent: extend
            segs[-1] = (segs[-1][0], max(segs[-1][1], f1 - segs[-1][0]), tag)
        elif f1 > f0:
            segs.append((f0, f1 - f0, tag))

if os.environ.get("CUT_DRY"):
    tot = 0
    for s0, e0, tag, *_ in keep:
        k = sum(n * FD for f0, n, _ in segs if s0 - FD <= f0 * FD <= e0 + FD); tot += k
        print(f"{s0:7.2f}-{e0:7.2f} {tag} raw={e0 - s0:5.1f} kept={k:5.1f}")
    print(f"total kept {tot:.1f}s -> {tot / speed:.1f}s at {speed}x"); sys.exit()

# --- level matching: bring each piece's speech (90th percentile of 10 ms RMS) to the common level, so a
#     speaker far from the mic is not quieter than the one wearing it (CUT_LEVEL=0 disables)
def p90(f0, n):
    x = db[int(f0 * FD * 100):int((f0 + n) * FD * 100)]
    return float(np.percentile(x, 90)) if len(x) else -99.0
lev = [p90(f0, n) for f0, n, _ in segs]
target = float(np.median(lev))
gains = [min(10.0, max(-4.0, target - L)) if os.environ.get("CUT_LEVEL", "1") != "0" else 0.0 for L in lev]

# --- one clip per piece: same seek for picture and sound, audio forced to exactly n frames
tmp = tempfile.mkdtemp(prefix="cut_")
lst = open(os.path.join(tmp, "list.txt"), "w")
for i, (f0, n, _) in enumerate(segs):
    t0, dur = f0 * FD, n * FD
    clip = os.path.join(tmp, f"p{i:04d}.mov")
    ns = int(round(dur * SR))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.6f}", "-i", src, "-map", "0:v:0", "-map", "0:a:0",
                    "-frames:v", str(n), "-af",
                    f"aresample={SR},atrim=end_sample={ns},apad=whole_len={ns},volume={gains[i]:.1f}dB,"
                    f"afade=t=in:d={FADE},afade=t=out:st={max(dur - FADE, 0):.6f}:d={FADE}",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-pix_fmt", "yuv420p", "-r", f"{num}/{den}",
                    "-c:a", "pcm_s16le", "-ar", str(SR), clip], check=True)
    lst.write(f"file '{clip}'\n")
lst.close()
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "list.txt"),
                "-vf", f"setpts=PTS/{speed},fps={num}/{den}", "-af", f"atempo={speed}",
                "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "256k", out], check=True)
shutil.rmtree(tmp)

t = 0.0; segmap = []
for f0, n, tag in segs:
    d = n * FD / speed
    segmap.append([round(t, 3), round(t + d, 3), tag, round(f0 * FD, 3), round((f0 + n) * FD, 3)]); t += d
json.dump(segmap, open(out.rsplit(".", 1)[0] + ".segments.json", "w"), ensure_ascii=False)
print(f"{len(segs)} pieces -> output {t:.1f}s at {speed}x")
