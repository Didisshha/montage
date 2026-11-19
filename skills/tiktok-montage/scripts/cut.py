"""Rough-cut a raw source: keep chosen phrase ranges, strip micro-pauses inside them, speed up.
usage: python3 cut.py SOURCE KEEP.json OUT.mp4 [speed=1.2]
KEEP.json: [[start, end, "tag"], ...] in source seconds (tag = who speaks, e.g. "L"/"R"; free text).
Writes OUT.mp4 and OUT.segments.json: [[out_start, out_end, tag, src_start, src_end], ...] on the
OUTPUT timeline (after speed-up), so framing can follow the speaker."""
import sys, json, subprocess, numpy as np, wave, os

src, keep_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
speed = float(sys.argv[4]) if len(sys.argv) > 4 else 1.2
keep = json.load(open(keep_path, encoding="utf-8"))
SR = 48000
GAP, PAD_IN, PAD_OUT, XF = 0.20, 0.05, 0.09, 0.008  # merge gaps < GAP; pads; 8 ms crossfades

probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=r_frame_rate", "-of", "json", src], capture_output=True, check=True).stdout)
num, den = map(int, probe["streams"][0]["r_frame_rate"].split("/")); FD = den / num  # frame duration

raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                     capture_output=True, check=True).stdout
audio = np.frombuffer(raw, np.float32).reshape(-1, 2)
mono = audio.mean(1)
hop = SR // 100  # 10 ms
rms = np.sqrt(np.convolve(mono ** 2, np.ones(hop) / hop, "same")[::hop] + 1e-12)
db = 20 * np.log10(rms)
floor = np.percentile(db, 10)
THR = float(os.environ.get("CUT_THR", 0.25))  # 0..1 between noise floor and loud speech; lower keeps quieter voices
thr = floor + THR * (np.percentile(db, 95) - floor)
voiced = db > thr

segs = []
for s, e, tag in keep:
    a, b = int(s * 100), int(e * 100)
    v = voiced[a:b]; runs = []; i = 0
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
            continue  # clicks / breaths
        r0 = max(s, r0 - PAD_IN); r1 = min(e, r1 + PAD_OUT)
        r0 = round(r0 / FD) * FD; r1 = round(r1 / FD) * FD  # snap to frames so audio and video stay in sync
        if r1 > r0:
            segs.append((r0, r1, tag))

if os.environ.get("CUT_DRY"):
    tot = 0
    for s0, e0, tag in keep:
        k = sum(r1 - r0 for r0, r1, _ in segs if r0 >= s0 - FD and r1 <= e0 + FD); tot += k
        print(f"{s0:7.2f}-{e0:7.2f} {tag} raw={e0 - s0:5.1f} kept={k:5.1f}")
    print(f"total kept {tot:.1f}s -> {tot / speed:.1f}s at {speed}x"); sys.exit()

# audio: concatenate with short crossfade-free fades (avoid clicks)
pieces = []
for r0, r1, _ in segs:
    x = audio[int(r0 * SR):int(r1 * SR)].copy(); n = int(XF * SR)
    if len(x) > 2 * n:
        x[:n] *= np.linspace(0, 1, n)[:, None]; x[-n:] *= np.linspace(1, 0, n)[:, None]
    pieces.append(x)
cat = np.concatenate(pieces)
tmpa = out + ".cut.wav"
with wave.open(tmpa, "w") as wf:
    wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
    wf.writeframes((np.clip(cat, -1, 1) * 32767).astype(np.int16).tobytes())

expr = "+".join(f"between(t,{r0:.4f},{r1 - FD / 2:.4f})" for r0, r1, _ in segs)
fexpr = out + ".select.txt"
open(fexpr, "w").write(f"[0:v:0]select='{expr}',setpts=N/FRAME_RATE/TB,setpts=PTS/{speed},fps={num}/{den}[v]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-i", tmpa, "-filter_complex_script", fexpr,
                "-map", "[v]", "-map", "1:a", "-af", f"atempo={speed}", "-c:v", "libx264", "-preset", "fast",
                "-crf", "14", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest", out], check=True)
os.remove(tmpa); os.remove(fexpr)

t = 0.0; segmap = []
for r0, r1, tag in segs:
    d = (r1 - r0) / speed
    segmap.append([round(t, 3), round(t + d, 3), tag, round(r0, 3), round(r1, 3)]); t += d
json.dump(segmap, open(out.rsplit(".", 1)[0] + ".segments.json", "w"), ensure_ascii=False)
print(f"{len(segs)} pieces, source kept {sum(r1 - r0 for r0, r1, _ in segs):.1f}s -> output {t:.1f}s at {speed}x")
