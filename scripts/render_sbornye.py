"""Finish-edit for 'сборные.mov': punch-in framing + word-synced callouts + audio cleanup.
CTA zone (CTA_START..CTA_END) is passed through untouched (scale 1.0, no overlays)."""
import subprocess, sys, math
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC, OUT = sys.argv[1], sys.argv[2]
FONTS = "/home/user/montage/fonts/"
W, H, FPS = 1080, 1920, 30000 / 1001
WHITE, ACCENT = (255, 255, 255), (0xF6, 0xDC, 0x93)
CTA_START, CTA_END = 27.22, 48.84
ANCHOR = (540, 250)  # zoom keeps this point fixed (speaker's face area)

# (t0, t1, scale_start, scale_end, punch) -- punch = quick eased zoom-in at segment start
FRAMING = [
    (0.00, 3.15, 1.00, 1.06, False),
    (3.15, 3.90, 1.30, 1.30, True),
    (3.90, 9.60, 1.00, 1.04, False),
    (9.60, 16.25, 1.24, 1.27, False),
    (16.25, 19.75, 1.00, 1.03, False),
    (19.75, 24.15, 1.28, 1.28, True),
    (24.15, CTA_START, 1.10, 1.14, False),
    (CTA_START, CTA_END, 1.00, 1.00, False),   # CTA: untouched
    (CTA_END, 52.30, 1.00, 1.05, False),
    (52.30, 57.35, 1.25, 1.28, False),
    (57.35, 58.70, 1.00, 1.00, False),
    (58.70, 99.0, 1.36, 1.40, True),
]


def font(name, size):
    return ImageFont.truetype(FONTS + name, size)


def text_layer(lines, x, y):
    """lines: list of (text, font, color, extra_gap). Returns RGBA full-frame layer + bbox."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cy = y
    for txt, f, col, gap in lines:
        d.text((x, cy), txt, font=f, fill=col + (255,))
        bb = d.textbbox((x, cy), txt, font=f)
        cy = bb[3] + gap
    # soft shadow: black, 70% opacity
    a = img.split()[3]
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh.putalpha(a.point(lambda v: int(v * 0.7)))
    sh = sh.filter(ImageFilter.GaussianBlur(10))
    sh = sh.transform(sh.size, Image.AFFINE, (1, 0, -3, 0, 1, -5))
    out = Image.alpha_composite(sh, img)
    return out, out.getbbox()


UB = lambda s: font("Unbounded-Bold.ttf", s)
MR = lambda s: font("Manrope-Regular.ttf", s)

# Callouts: list of elements; each element = (appear_t, layer)
# group = (elements, t_out)
X0 = 64
CALLOUTS = []


def plate_layer(box, radius=30, alpha=0.55):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle(box, radius, fill=(20, 12, 40, int(255 * alpha)))
    return img, img.getbbox()


def group(t_out, *elems):
    out = []
    for e in elems:
        if e[1] == "PLATE":
            out.append((e[0], *plate_layer(e[2])))
        else:
            t, lines, x, y = e
            out.append((t, *text_layer(lines, x, y)))
    CALLOUTS.append((out, t_out))


group(9.55,
      (5.70, [("ЗАКРЫТОЕ", UB(78), ACCENT, 6)], X0, 880),
      (6.20, [("КОМЬЮНИТИ", UB(78), WHITE, 0)], X0, 975))
group(16.20,
      (12.40, "PLATE", (X0 - 26, 836, 700, 1182)),
      (12.50, [("→", UB(52), ACCENT, 0)], X0, 860), (12.50, [("поддержка", MR(56), WHITE, 0)], X0 + 64, 852),
      (13.20, [("→", UB(52), ACCENT, 0)], X0, 950), (13.20, [("обмен опытом", MR(56), WHITE, 0)], X0 + 64, 942),
      (14.30, [("→", UB(52), ACCENT, 0)], X0, 1040), (14.30, [("ответы на сложные", MR(56), WHITE, 0)], X0 + 64, 1032),
      (14.30, [("вопросы", MR(56), WHITE, 0)], X0 + 64, 1100))
group(23.30,
      (20.55, [("НОВИЧКОВ", UB(80), ACCENT, 6)], X0, 880),
      (20.85, [("НЕ ПУСКАЮТ", UB(80), WHITE, 0)], X0, 978))
group(52.25,
      (50.05, [("ОТКРЫТО", UB(80), WHITE, 6)], X0, 880),
      (51.25, [("КАЖДОМУ", UB(80), ACCENT, 0)], X0, 978))
group(99.0,
      (58.70, [("ГЛАВНОЕ —", UB(64), WHITE, 0)], X0, 900),
      (59.55, [("ПЕРВЫЙ ШАГ", UB(84), ACCENT, 0)], X0, 985))

for elems, t_out in CALLOUTS:
    for t, *_ in elems:
        assert not (CTA_START <= t < CTA_END) and not (CTA_START < t_out <= CTA_END), "overlay in CTA"
# precompute premultiplied numpy versions (cropped to bbox)
PRE = []
for elems, t_out in CALLOUTS:
    pe = []
    for t, layer, bb in elems:
        crop = np.asarray(layer.crop(bb)).astype(np.float32) / 255.0
        pe.append((t, crop, bb))
    PRE.append((pe, t_out))


def ease_out_back(x):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def scale_at(t):
    for t0, t1, s0, s1, punch in FRAMING:
        if t0 <= t < t1:
            p = (t - t0) / max(t1 - t0, 1e-6)
            s = s0 + (s1 - s0) * p
            if punch:  # ease in from 1.0 over 0.18s
                k = min((t - t0) / 0.18, 1.0)
                k = 1 - (1 - k) ** 3
                s = 1.0 + (s - 1.0) * k
            return s
    return 1.0


def zoom(frame, s):
    if abs(s - 1.0) < 1e-4:
        return frame
    ax, ay = ANCHOR
    M = np.array([[s, 0, ax * (1 - s)], [0, s, ay * (1 - s)]], dtype=np.float32)
    return cv2.warpAffine(frame, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def composite(frame, t):
    f = None
    for pe, t_out in PRE:
        for t_in, crop, (x0, y0, x1, y1) in pe:
            if t < t_in or t >= t_out + 0.2:
                continue
            a_in = min((t - t_in) / 0.22, 1.0)
            a_out = 1.0 - max(0.0, (t - t_out) / 0.2)
            alpha = max(0.0, min(a_in * 3, 1.0) * a_out)
            sc = 0.6 + 0.4 * ease_out_back(a_in) if a_in < 1 else 1.0
            img = crop
            if abs(sc - 1) > 1e-3:
                h, w = crop.shape[:2]
                nw, nh = max(1, int(w * sc)), max(1, int(h * sc))
                img = cv2.resize(crop, (nw, nh), interpolation=cv2.INTER_LINEAR)
                cx, cy = x0, (y0 + y1) / 2  # grow from left edge, vertical center
                x0_, y0_ = int(cx), int(cy - nh / 2)
            else:
                x0_, y0_ = x0, y0
            h, w = img.shape[:2]
            xa, ya, xb, yb = max(x0_, 0), max(y0_, 0), min(x0_ + w, W), min(y0_ + h, H)
            if xa >= xb or ya >= yb:
                continue
            if f is None:
                f = frame.astype(np.float32)
            src = img[ya - y0_:yb - y0_, xa - x0_:xb - x0_]
            rgb = src[..., 2::-1] * 255.0  # RGBA->BGR
            al = src[..., 3:4] * alpha
            roi = f[ya:yb, xa:xb]
            f[ya:yb, xa:xb] = roi * (1 - al) + rgb * al
    return frame if f is None else np.clip(f, 0, 255).astype(np.uint8)


AF = ("highpass=f=80,afftdn=nf=-30:nr=8,"
      "acompressor=threshold=-18dB:ratio=2.5:attack=10:release=150,"
      "loudnorm=I=-14:LRA=9:TP=-1.5")
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                       stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                        "-s", f"{W}x{H}", "-r", "30000/1001", "-i", "-", "-i", SRC,
                        "-map", "0:v", "-map", "1:a", "-af", AF, "-ar", "48000",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", OUT],
                       stdin=subprocess.PIPE)
n, fs = 0, W * H * 3
while True:
    buf = dec.stdout.read(fs)
    if len(buf) < fs:
        break
    t = n / FPS
    fr = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    fr = zoom(fr, scale_at(t))
    fr = composite(fr, t)
    enc.stdin.write(np.ascontiguousarray(fr).tobytes())
    n += 1
enc.stdin.close(); enc.wait(); dec.wait()
print("frames", n)
