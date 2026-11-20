import sys, json, subprocess, numpy as np
src, segj = sys.argv[1], sys.argv[2]
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
a = np.frombuffer(raw, np.float32)
lvl = lambda t0, t1: 20 * np.log10(np.sqrt((a[int(t0 * 16000):int(t1 * 16000)] ** 2).mean()) + 1e-9)
for o0, o1, tag, r0, r1 in json.load(open(segj)):
    s_in, s_out = lvl(r0, r0 + 0.04), lvl(r1 - 0.04, r1)
    after = lvl(r1, r1 + 0.08)
    flag = []
    if s_in > -32: flag.append(f"starts loud {s_in:.0f}dB")
    if s_out > -32 and after > -32: flag.append(f"ends mid-sound {s_out:.0f}/{after:.0f}dB")
    if flag: print(f"src {r0:7.2f}-{r1:7.2f} out {o0:6.2f}  " + "; ".join(flag))
