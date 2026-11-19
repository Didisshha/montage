"""TikTok montage engine: renders a vertical video from SOURCE + a JSON edit plan.
usage: python3 render.py SOURCE OUT.mp4 PLAN.json SFX_DIR
See ../references/plan-format.md for the plan format."""
import subprocess, sys, math, os, wave, json
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SRC, OUT = sys.argv[1], sys.argv[2]
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts") + "/"
W, H, FPS = 1080, 1920, 30000 / 1001
CREAM, WHITE, LAV, PLUM, RED, GREEN = (0xF6, 0xDC, 0x93), (255, 255, 255), (0xA0, 0x8C, 0xFF), (0x1E, 0x12, 0x38), (0xFF, 0x5C, 0x7A), (0x7C, 0xF2, 0x9A)
PLAN = json.load(open(sys.argv[3], encoding="utf-8"))
SFXDIR = sys.argv[4]
CTA = [tuple(z) for z in PLAN.get("cta", [])]
ANCHOR = tuple(PLAN.get("anchor", [540, 690]))
SS = 2  # supersampling

UB = lambda s: ImageFont.truetype(FONTS + "Unbounded-Bold.ttf", s)
MR = lambda s: ImageFont.truetype(FONTS + "Manrope-Regular.ttf", s)


def in_cta(t):
    return any(a <= t < b for a, b in CTA)


# ---------------------------------------------------------------- drawing helpers
def shadowed(img, blur=10, alpha=0.7, off=(3, 5)):
    pad = blur * 3
    big = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    big.paste(img, (pad, pad), img)
    sh = Image.new("RGBA", big.size, (0, 0, 0, 0))
    sh.putalpha(big.split()[3].point(lambda v: int(v * alpha)))
    sh = sh.filter(ImageFilter.GaussianBlur(blur)).transform(big.size, Image.AFFINE, (1, 0, -off[0], 0, 1, -off[1]))
    return Image.alpha_composite(sh, big)


def text_img(lines, align="left"):
    """lines: [(text, font, color)] -> RGBA with shadow"""
    d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    boxes = [d0.textbbox((0, 0), t, font=f) for t, f, _ in lines]
    wmax = max(b[2] for b in boxes) + 8
    hs = [b[3] for b in boxes]
    img = Image.new("RGBA", (wmax, sum(hs) + 8 * len(lines)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img); y = 0
    for (t, f, c), b, h in zip(lines, boxes, hs):
        x = 0 if align == "left" else (wmax - b[2]) // 2
        d.text((x, y), t, font=f, fill=c + (255,)); y += h + 8
    return shadowed(img)


def card(draw_icon, caption, w=280, h=300, border=LAV):
    """Rounded plum card with an icon (drawn at SS scale) and caption."""
    big = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.rounded_rectangle((0, 0, w * SS - 1, h * SS - 1), 40 * SS, fill=PLUM + (230,), outline=border + (255,), width=4 * SS)
    icon_h = (h - 70) * SS if caption else h * SS
    draw_icon(d, big, (0, 0, w * SS, icon_h))
    if caption:
        f = MR(34 * SS)
        b = d.textbbox((0, 0), caption, font=f)
        d.text(((w * SS - b[2]) // 2, icon_h + 4 * SS), caption, font=f, fill=WHITE + (255,))
    return shadowed(big.resize((w, h), Image.LANCZOS), blur=14, alpha=0.55)


def star(cx, cy, r1, r2, n=5, rot=-90):
    pts = []
    for i in range(2 * n):
        r = r1 if i % 2 == 0 else r2
        a = math.radians(rot + i * 180 / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def C(box):
    x0, y0, x1, y1 = box
    return (x0 + x1) / 2, (y0 + y1) / 2, min(x1 - x0, y1 - y0)


# ---------------------------------------------------------------- icons (draw(d, img, box))
def ic_medal(label):
    def f(d, img, box):
        cx, cy, s = C(box); cy += s * 0.08; r = s * 0.27
        d.polygon([(cx - r * .9, cy - r * 2.1), (cx - r * .2, cy - r * 2.1), (cx + r * .25, cy - r * .5), (cx - r * .35, cy - r * .5)], fill=LAV)
        d.polygon([(cx + r * .9, cy - r * 2.1), (cx + r * .2, cy - r * 2.1), (cx - r * .25, cy - r * .5), (cx + r * .35, cy - r * .5)], fill=(0x7A, 0x66, 0xE0))
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=CREAM, outline=(0xC9, 0xA8, 0x55), width=int(s * .03))
        d.polygon(star(cx, cy, r * .62, r * .27), fill=PLUM)
        if label:
            fb = UB(int(s * .1)); b = d.textbbox((0, 0), label, font=fb)
            d.text((cx - b[2] / 2, cy + r * 1.08), label, font=fb, fill=CREAM)
    return f


def ic_target(d, img, box):
    cx, cy, s = C(box); cy += s * .03
    for k, col in enumerate([CREAM, PLUM, CREAM, LAV]):
        r = s * .36 * (1 - k * .24)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    w = int(s * .035)
    d.line((cx, cy, cx + s * .38, cy - s * .38), fill=WHITE, width=w)
    ex, ey = cx + s * .38, cy - s * .38
    d.polygon([(ex, ey), (ex + s * .1, ey - s * .02), (ex + s * .02, ey + s * .1)], fill=RED)
    d.polygon([(ex - s * .02, ey - s * .1), (ex + s * .02, ey - s * .02), (ex - s * .06, ey - s * .02)], fill=RED)


def ic_uni(d, img, box):
    cx, cy, s = C(box); top = cy - s * .33; base = cy + s * .3; hw = s * .38
    d.polygon([(cx, top), (cx - hw, top + s * .2), (cx + hw, top + s * .2)], fill=CREAM)
    d.rectangle((cx - hw, base - s * .06, cx + hw, base), fill=CREAM)
    d.rectangle((cx - hw * .9, top + s * .22, cx + hw * .9, top + s * .27), fill=CREAM)
    for i in range(4):
        x = cx - hw * .7 + i * hw * .466
        d.rectangle((x - s * .035, top + s * .3, x + s * .035, base - s * .08), fill=LAV)
    d.polygon(star(cx, top + s * .12, s * .045, s * .02), fill=PLUM)
    for sx, sy in [(-.43, -.33), (.42, -.22)]:
        d.polygon(star(cx + s * sx, cy + s * sy, s * .05, s * .015, 4), fill=WHITE)


def ic_medals_strike(p):
    def f(d, img, box):
        cx, cy, s = C(box)
        for i in range(3):
            x = cx + (i - 1) * s * .3; r = s * .12
            d.ellipse((x - r, cy - r, x + r, cy + r), fill=CREAM)
            d.polygon(star(x, cy, r * .6, r * .26), fill=PLUM)
        if p > 0:
            x0, x1 = cx - s * .45, cx - s * .45 + s * .9 * p
            d.line((x0, cy + s * .12, x1, cy + s * .12 - s * .24 * p), fill=RED, width=int(s * .05))
    return f


def ic_bigtext(txt, col=CREAM, size=.34):
    def f(d, img, box):
        cx, cy, s = C(box); fb = UB(int(s * size)); b = d.textbbox((0, 0), txt, font=fb)
        d.text((cx - b[2] / 2, cy - b[3] / 2), txt, font=fb, fill=col)
    return f


def ic_book_speed(ph):
    def f(d, img, box):
        cx, cy, s = C(box); cx += s * .08
        for i in range(4):  # speed lines
            y = cy - s * .2 + i * s * .13; x = cx - s * .45 - ((ph * 3 + i * .37) % 1) * s * .12
            d.line((x - s * .2, y, x, y), fill=LAV, width=int(s * .03))
        bw, bh = s * .26, s * .34
        d.polygon([(cx, cy - bh / 2 + s * .03), (cx - bw, cy - bh / 2), (cx - bw, cy + bh / 2), (cx, cy + bh / 2 + s * .03)], fill=CREAM)
        d.polygon([(cx, cy - bh / 2 + s * .03), (cx + bw, cy - bh / 2), (cx + bw, cy + bh / 2), (cx, cy + bh / 2 + s * .03)], fill=WHITE)
        for i in range(4):
            y = cy - bh / 2 + s * .08 + i * s * .065
            d.line((cx - bw * .8, y, cx - bw * .15, y + s * .01), fill=PLUM, width=int(s * .012))
            d.line((cx + bw * .15, y + s * .01, cx + bw * .8, y), fill=PLUM, width=int(s * .012))
    return f


def ic_books(k):
    cols = [CREAM, LAV, RED, WHITE, GREEN, CREAM]
    def f(d, img, box):
        cx, cy, s = C(box); y = cy + s * .38
        for i in range(k):
            bw = s * (.62 - (i % 3) * .06); bh = s * .1; dx = s * (.04 if i % 2 else -.04)
            d.rounded_rectangle((cx - bw / 2 + dx, y - bh, cx + bw / 2 + dx, y), int(s * .015), fill=cols[i], outline=PLUM, width=int(s * .01))
            d.line((cx - bw / 2 + dx + s * .05, y - bh / 2, cx - bw / 2 + dx + s * .15, y - bh / 2), fill=PLUM, width=int(s * .01))
            y -= bh
    return f


def ic_clock(ang):
    def f(d, img, box):
        cx, cy, s = C(box); r = s * .36
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=CREAM, outline=LAV, width=int(s * .04))
        for i in range(12):
            a = math.radians(i * 30); r0 = r * (.78 if i % 3 else .7)
            d.line((cx + r0 * math.cos(a), cy + r0 * math.sin(a), cx + r * .9 * math.cos(a), cy + r * .9 * math.sin(a)), fill=PLUM, width=int(s * .015))
        a = math.radians(ang - 90)
        d.line((cx, cy, cx + r * .75 * math.cos(a), cy + r * .75 * math.sin(a)), fill=RED, width=int(s * .03))
        a2 = math.radians(ang / 12 - 90)
        d.line((cx, cy, cx + r * .5 * math.cos(a2), cy + r * .5 * math.sin(a2)), fill=PLUM, width=int(s * .04))
        d.ellipse((cx - s * .03, cy - s * .03, cx + s * .03, cy + s * .03), fill=PLUM)
    return f


def ic_battery(level, charging):
    def f(d, img, box):
        cx, cy, s = C(box); bw, bh = s * .62, s * .34; x0, y0 = cx - bw / 2 - s * .03, cy - bh / 2
        d.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), int(s * .05), outline=WHITE, width=int(s * .035))
        d.rounded_rectangle((x0 + bw, cy - bh * .2, x0 + bw + s * .06, cy + bh * .2), int(s * .02), fill=WHITE)
        col = GREEN if level > .55 else CREAM if level > .25 else RED
        pad = s * .045
        if level > 0.02:
            d.rounded_rectangle((x0 + pad, y0 + pad, x0 + pad + (bw - 2 * pad) * level, y0 + bh - pad), int(s * .025), fill=col)
        if charging:
            d.polygon([(cx + s * .03, cy - bh * .45), (cx - s * .08, cy + s * .02), (cx, cy + s * .02), (cx - s * .04, cy + bh * .45), (cx + s * .09, cy - s * .03), (cx + s * .01, cy - s * .03)], fill=PLUM)
    return f


def ic_pause(d, img, box):
    cx, cy, s = C(box); r = s * .34
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=LAV)
    for dx in (-1, 1):
        d.rounded_rectangle((cx + dx * s * .09 - s * .05, cy - s * .15, cx + dx * s * .09 + s * .05, cy + s * .15), int(s * .02), fill=WHITE)


def ic_quote(p):
    def f(d, img, box):
        cx, cy, s = C(box); fb = UB(int(s * .42))
        d.text((cx - s * .44, cy - s * .32), "«", font=fb, fill=CREAM)
        d.text((cx + s * .1, cy - s * .32), "»", font=fb, fill=CREAM)
        n = int(p * 3.99)
        for i in range(n):
            r = s * .035; x = cx - s * .1 + i * s * .1
            d.ellipse((x - r, cy - r, x + r, cy + r), fill=WHITE)
    return f


def ic_buoy(ang):
    def f(d, img, box):
        cx, cy, s = C(box); r = s * .38; ri = r * .52
        for i in range(8):
            d.pieslice((cx - r, cy - r, cx + r, cy + r), ang + i * 45, ang + (i + 1) * 45, fill=RED if i % 2 == 0 else WHITE)
        d.ellipse((cx - ri, cy - ri, cx + ri, cy + ri), fill=PLUM)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=PLUM, width=int(s * .012))
    return f


def stamp_img(text, col, size=64, angle=-8):
    f = UB(size * SS)
    d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1))); b = d0.textbbox((0, 0), text, font=f)
    pad = 26 * SS
    img = Image.new("RGBA", (b[2] + 2 * pad, b[3] + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((4, 4, img.width - 5, img.height - 5), 22 * SS, fill=PLUM + (200,), outline=col + (255,), width=7 * SS)
    d.text((pad, pad - 4 * SS), text, font=f, fill=col + (255,))
    img = img.resize((img.width // SS, img.height // SS), Image.LANCZOS).rotate(angle, Image.BICUBIC, expand=True)
    return shadowed(img)


def sparkles_img(ph, seed):
    rr = np.random.default_rng(seed)
    w, h = 300, 340
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    for i in range(6):
        x, y = rr.uniform(.15, .85) * w * SS, rr.uniform(.12, .88) * h * SS
        k = max(0.0, math.sin(2 * math.pi * (ph * 1.6 + i / 6)))
        r = (14 + 30 * k) * SS * rr.uniform(.6, 1)
        d.polygon(star(x, y, r, r * .22, 4, rot=0), fill=(CREAM if i % 2 else WHITE) + (int(255 * (0.3 + .7 * k)),))
    return img.resize((w, h), Image.LANCZOS)


# ---------------------------------------------------------------- element model
class El:
    def __init__(self, t_in, t_out, cx, cy, make, anim="pop", dyn=False, bob=6.0, rot=0.0, d_in=0.28, cta_ok=False):
        self.t_in, self.t_out, self.cx, self.cy = t_in, t_out, cx, cy
        self.make, self.anim, self.dyn, self.bob, self.rot, self.d_in = make, anim, dyn, bob, rot, d_in
        self.cache = {}
        assert cta_ok or not any(a < t_out + 0.2 and t_in < b for a, b in CTA), f"overlay in CTA {t_in}"

    def img(self, tr):
        key = round(tr * 15) if self.dyn else 0
        if key not in self.cache:
            im = self.make(key / 15) if self.dyn else self.make
            arr = np.asarray(im).astype(np.float32) / 255.0
            self.cache[key] = arr
        return self.cache[key]


def ease_back(x):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_cubic(x):
    return 1 - (1 - x) ** 3


def place(frame_f, el, t):
    tail = 0.0 if el.anim == "subpop" else 0.2
    if t < el.t_in or t >= el.t_out + tail:
        return frame_f
    tr = t - el.t_in
    a_in = min(tr / el.d_in, 1.0); a_out = 0.0 if tail == 0 else max(0.0, (t - el.t_out) / 0.2)
    alpha = min(1.0, a_in * 2.5) * (1 - a_out)
    sc, rot, dx, dy = 1.0, el.rot, 0.0, 0.0
    if el.anim == "pop":
        sc = 0.4 + 0.6 * ease_back(a_in)
    elif el.anim == "stamp":
        sc = 2.2 - 1.2 * ease_cubic(a_in); alpha = min(1.0, a_in * 4) * (1 - a_out)
    elif el.anim == "slide_l":
        dx = -(1 - ease_cubic(a_in)) * 500
    elif el.anim == "slide_r":
        dx = (1 - ease_cubic(a_in)) * 500
    elif el.anim == "slide_u":
        dy = (1 - ease_cubic(a_in)) * 900
    elif el.anim == "subpop":
        sc = 0.85 + 0.15 * ease_back(a_in); alpha = min(1.0, a_in * 4) * (1 - a_out)
    sc *= 1 - 0.35 * a_out
    dy += math.sin(2 * math.pi * 0.7 * tr) * el.bob
    rot += math.sin(2 * math.pi * 0.45 * tr) * (1.5 if el.bob else 0)
    src = el.img(tr)
    h, w = src.shape[:2]
    R = cv2.getRotationMatrix2D((w / 2, h / 2), rot, sc)
    cxo, cyo = el.cx + dx, el.cy + dy
    half = int(math.hypot(w, h) * sc / 2) + 2
    x0, y0 = int(cxo - half), int(cyo - half)
    R[0, 2] += half - w / 2; R[1, 2] += half - h / 2
    warped = cv2.warpAffine(src, R, (2 * half, 2 * half), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + 2 * half, W), min(y0 + 2 * half, H)
    if xa >= xb or ya >= yb:
        return frame_f
    s = warped[ya - y0:yb - y0, xa - x0:xb - x0]
    al = s[..., 3:4] * alpha
    if frame_f is None:
        frame_f = place.base.astype(np.float32)
    roi = frame_f[ya:yb, xa:xb]
    frame_f[ya:yb, xa:xb] = roi * (1 - al) + s[..., 2::-1] * 255.0 * al
    return frame_f


# ---------------------------------------------------------------- extra icons
def ic_calendar(p):
    def f(d, img, box):
        cx, cy, s = C(box); w2, h2 = s * .36, s * .34
        d.rounded_rectangle((cx - w2, cy - h2, cx + w2, cy + h2), int(s * .05), fill=WHITE)
        d.rounded_rectangle((cx - w2, cy - h2, cx + w2, cy - h2 + s * .17), int(s * .05), fill=LAV)
        d.rectangle((cx - w2, cy - h2 + s * .1, cx + w2, cy - h2 + s * .17), fill=LAV)
        for dx in (-.18, .18):
            d.rounded_rectangle((cx + s * dx - s * .02, cy - h2 - s * .06, cx + s * dx + s * .02, cy - h2 + s * .05), int(s * .01), fill=PLUM)
        for r in range(3):
            for c in range(4):
                x = cx - w2 + s * .12 + c * s * .16; y = cy - h2 + s * .28 + r * s * .13
                d.ellipse((x - s * .025, y - s * .025, x + s * .025, y + s * .025), fill=PLUM)
        if p > 0:  # red circle drawn around a date
            x = cx - w2 + s * .12 + 2 * s * .16; y = cy - h2 + s * .28 + s * .13; r = s * .075
            d.arc((x - r, y - r, x + r, y + r), -90, -90 + 360 * min(p, 1), fill=RED, width=int(s * .025))
    return f


def ic_check(n, rows=3):
    def f(d, img, box):
        cx, cy, s = C(box)
        for i in range(rows):
            y = cy - s * .26 + i * s * .26; x0 = cx - s * .36
            d.rounded_rectangle((x0, y - s * .08, x0 + s * .16, y + s * .08), int(s * .03), outline=WHITE, width=int(s * .02))
            d.rounded_rectangle((x0 + s * .24, y - s * .025, cx + s * .38, y + s * .025), int(s * .02), fill=LAV if i >= n else CREAM)
            if i < n:
                d.line((x0 + s * .03, y, x0 + s * .07, y + s * .05, x0 + s * .15, y - s * .07), fill=GREEN, width=int(s * .035), joint="curve")
    return f


def ic_bigcheck(d, img, box):
    cx, cy, s = C(box); r = s * .36
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=GREEN)
    d.line((cx - s * .17, cy, cx - s * .04, cy + s * .14, cx + s * .2, cy - s * .14), fill=PLUM, width=int(s * .07), joint="curve")


def ic_magnifier(ph):
    def f(d, img, box):
        cx, cy, s = C(box); cx += math.sin(ph * 6) * s * .05; r = s * .2
        d.line((cx + r * .7, cy + r * .7, cx + s * .33, cy + s * .33), fill=CREAM, width=int(s * .07))
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(0x40, 0x30, 0x70), outline=WHITE, width=int(s * .045))
        d.arc((cx - r * .6, cy - r * .6, cx + r * .6, cy + r * .6), 200, 260, fill=WHITE, width=int(s * .02))
    return f


def ic_warning(d, img, box):
    cx, cy, s = C(box); r = s * .38
    d.polygon([(cx, cy - r), (cx - r * 1.1, cy + r * .75), (cx + r * 1.1, cy + r * .75)], fill=CREAM)
    d.rounded_rectangle((cx - s * .03, cy - r * .45, cx + s * .03, cy + r * .2), int(s * .02), fill=PLUM)
    d.ellipse((cx - s * .035, cy + r * .35, cx + s * .035, cy + r * .35 + s * .07), fill=PLUM)


# ---------------------------------------------------------------- plan -> elements
COLORS = {"cream": CREAM, "white": WHITE, "lav": LAV, "plum": PLUM, "red": RED, "green": GREEN}
LX, RX, IY = 205, 875, 560   # card centres left/right of the head (1080x1920 output)
HX, HY = 50, 840             # tip header top-left
ELS, SFX_EV = [], []
col = lambda c: COLORS[c] if isinstance(c, str) else tuple(c)


def icon(spec):
    """Returns (make, dynamic). make is an Image (static) or f(seconds_since_in)->Image."""
    k = spec["icon"]; cap = spec.get("caption", ""); bd = col(spec.get("border", "lav"))
    c = lambda drawer: card(drawer, cap, border=bd)
    static = {"uni": ic_uni, "target": ic_target, "pause": ic_pause, "warning": ic_warning, "bigcheck": ic_bigcheck}
    if k in static:
        return c(static[k]), False
    if k == "medal":
        return c(ic_medal(spec.get("label", ""))), False
    if k == "bigtext":
        return c(ic_bigtext(spec["text"], col(spec.get("color", "cream")), spec.get("size", .34))), False
    if k == "counter":    # counts 0 -> to, starting `start` s after appearing, over `dur` s
        to, st, du = spec.get("to", 100), spec.get("start", 0.6), spec.get("dur", 0.45)
        return (lambda p: c(ic_bigtext(str(int(to * min(max((p - st) / du, 0), 1))), CREAM if p < st + du else GREEN, .3))), True
    if k == "calendar":
        return (lambda p: c(ic_calendar(max(0, (p - 0.3) / 0.6)))), True
    if k == "checklist":  # rows tick one by one every `step` s
        rows, step = spec.get("rows", 3), spec.get("step", 0.25)
        return (lambda p: c(ic_check(min(rows, int(p / step) + 1), rows))), True
    if k == "magnifier":
        return (lambda p: c(ic_magnifier(p))), True
    if k == "book_speed":
        return (lambda p: c(ic_book_speed(p))), True
    if k == "books":      # a book drops on the stack at each offset in `drops` (seconds after appearing)
        drops = spec.get("drops", [0, .35, .8, 1.3, 1.6, 2.0])
        return (lambda p: c(ic_books(sum(1 for d in drops if p >= d)))), True
    if k == "clock":
        sp = spec.get("speed", 900)
        return (lambda p: c(ic_clock(p * sp))), True
    if k == "battery_drain":
        return (lambda p: c(ic_battery(max(0.04, 1 - p / spec.get("dur", 2.4)), False))), True
    if k == "battery_charge":
        return (lambda p: c(ic_battery(min(1, 0.1 + p / spec.get("dur", 1.1)), True))), True
    if k == "quote":
        return (lambda p: c(ic_quote((p * 2) % 1.0))), True
    if k == "lifebuoy":
        return (lambda p: c(ic_buoy(p * 220))), True
    if k == "medals_strike":
        at = spec.get("strike_at", 0.8)
        return (lambda p: c(ic_medals_strike(min(max((p - at) / 0.4, 0), 1)))), True
    raise ValueError(f"unknown icon {k}")


def add_sfx(t, name, gain):
    if name:
        SFX_EV.append((t, name, gain))


for h in PLAN.get("headers", []):
    num = text_img([(str(h["n"]), UB(190), LAV)])
    t0 = text_img([(h["l1"], UB(46), WHITE), (h["l2"], UB(46), CREAM)])
    pad = 14
    txt = Image.new("RGBA", (t0.width + 2 * pad - 40, t0.height + 2 * pad - 40), (0, 0, 0, 0))
    ImageDraw.Draw(txt).rounded_rectangle((0, 0, txt.width - 1, txt.height - 1), 26, fill=PLUM + (205,))
    txt.paste(t0, (pad - 30, pad - 30), t0)
    im = Image.new("RGBA", (num.width + txt.width, max(num.height, txt.height)), (0, 0, 0, 0))
    im.paste(num, (0, 0), num); im.paste(txt, (num.width - 30, (num.height - txt.height) // 2 + 10), txt)
    ELS.append(El(h["t"], h["out"], HX + im.width / 2, HY + im.height / 2, im, anim="slide_l", bob=0, d_in=0.3))
    add_sfx(max(h["t"] - 0.1, 0), h.get("sfx_in", "swoosh_fast"), -9)
    add_sfx(h["t"] + 0.02, h.get("sfx_hit", "zoom_impact"), -8)

for cd in PLAN.get("cards", []):
    make, dyn = icon(cd)
    x = {"L": LX, "R": RX}.get(cd.get("side", "R"), cd.get("x", RX))
    ELS.append(El(cd["t"], cd["out"], x, cd.get("y", IY), make, anim=cd.get("anim", "pop"), dyn=dyn))
    add_sfx(cd["t"], cd.get("sfx", "pop_light"), cd.get("gain", -8))

for st in PLAN.get("stamps", []):
    ELS.append(El(st["t"], st["out"], st.get("x", 540), st.get("y", 1060),
                  stamp_img(st["text"], col(st.get("color", "cream")), st.get("size", 72), st.get("angle", -8)),
                  anim="stamp", bob=0, d_in=0.16))
    add_sfx(st["t"] + 0.08, st.get("sfx", "pop_hard"), st.get("gain", -8))

for tx in PLAN.get("texts", []):
    lines = [(l[0], (UB if l[1] == "UB" else MR)(l[2]), col(l[3])) for l in tx["lines"]]
    ELS.append(El(tx["t"], tx["out"], tx.get("x", 540), tx.get("y", 1000), text_img(lines, tx.get("align", "center")),
                  anim=tx.get("anim", "pop"), bob=tx.get("bob", 3), d_in=tx.get("d_in", 0.18)))
    add_sfx(tx["t"], tx.get("sfx"), tx.get("gain", -9))

for sp in PLAN.get("sparkles", []):
    ELS.append(El(sp["t"], sp["out"], LX if sp.get("side", "L") == "L" else RX, sp.get("y", 520),
                  (lambda seed: (lambda p: sparkles_img(p, seed)))(len(ELS)), dyn=True, bob=0, anim="fade"))
    add_sfx(sp["t"], sp.get("sfx"), sp.get("gain", -10))

RB = lambda s: ImageFont.truetype(FONTS + "Rubik-SemiBold.ttf", s)

# --- brand plate (persistent semi-transparent "тгк: ..." near the top, below TikTok's UI band)
if PLAN.get("brand"):
    b = PLAN["brand"]; f = MR(b.get("size", 40))
    d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1))); bb = d0.textbbox((0, 0), b["text"], font=f)
    padx, pady = 30, 14
    im = Image.new("RGBA", (bb[2] + 2 * padx, bb[3] + 2 * pady), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width - 1, im.height - 1), im.height // 2, fill=PLUM + (150,))
    d.text((padx, pady - 2), b["text"], font=f, fill=(255, 255, 255, 235))
    a = b.get("alpha", 0.6); im.putalpha(im.split()[3].point(lambda v: int(v * a)))
    ELS.append(El(0, 1e9, 540, b.get("y", 250), im, anim="none", bob=0, d_in=0.001, cta_ok=True))


# --- word-by-word subtitles (Rubik SemiBold, white; highlighted words in cream)
def _clean(w):
    return w.strip(" «»\"“”.,!?:;…")


if PLAN.get("subtitles"):
    sb = PLAN["subtitles"]; words = sb["words"]; hl = {h.lower() for h in sb.get("highlight", [])}
    size, sy = sb.get("size", 66), sb.get("y", 1330)
    cache = {}
    for i, (ws, we, w) in enumerate(words):
        w = _clean(w)
        if not w:
            continue
        nxt = words[i + 1][0] if i + 1 < len(words) else we + 0.4
        end = min(nxt, we + sb.get("hold", 0.35))
        key = (w, w.lower() in hl)
        if key not in cache:
            cache[key] = text_img([(w, RB(size), CREAM if key[1] else WHITE)], align="center")
        x, y = 540, sy
        for z in sb.get("zones", []):  # [t0, t1, x, y]: move subtitles while e.g. a phone screen is shown
            if z[0] <= ws < z[1]:
                x, y = z[2], z[3]
        ELS.append(El(ws, end, x, y, cache[key], anim="subpop", bob=0, d_in=0.12, cta_ok=True))


# --- phone/screen inserts from screenshots: slide up, optional typing reveal, taps, scrolling
def _screen_maker(sp):
    w = sp.get("w", 470)
    src_im = Image.open(sp["img"]).convert("RGB")
    src_im = src_im.resize((w, int(src_im.height * w / src_im.width)), Image.LANCZOS)
    ih = src_im.height; h = min(sp.get("h", 840), ih)
    smooth = lambda q: q * q * (3 - 2 * q)

    def make(p):
        off = 0
        if sp.get("scroll") and ih > h:
            st, du = sp["scroll"]; off = int(smooth(min(max((p - st) / du, 0), 1)) * (ih - h))
        im = src_im.crop((0, off, w, off + h)).convert("RGBA"); d = ImageDraw.Draw(im)
        ty = sp.get("type")
        if ty:  # hide the not-yet-typed part of a text field
            fx0, fy0, fx1, fy1 = ty["box"]; x0, y0, x1, y1 = fx0 * w, fy0 * ih - off, fx1 * w, fy1 * ih - off
            r = min(max((p - ty.get("start", 0.2)) / ty.get("dur", 0.8), 0), 1); xr = x0 + r * (x1 - x0)
            bg = src_im.getpixel((min(int(x1) - 2, w - 1), int((fy0 + fy1) / 2 * ih)))
            if r < 1:
                d.rectangle((xr, y0, x1, y1), fill=bg + (255,))
            if r < 1 or int(p * 3) % 2 == 0:
                d.rectangle((xr + 2, y0 + (y1 - y0) * .2, xr + 5, y1 - (y1 - y0) * .2), fill=(255, 255, 255, 255))
        for dt, fx, fy in sp.get("taps", []):
            k = (p - dt) / 0.6
            if 0 <= k < 1:
                cx, cy = fx * w, fy * ih - off; rr = 18 + 50 * k
                d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=(255, 255, 255, int(255 * (1 - k))), width=6)
                d.ellipse((cx - 16, cy - 16, cx + 16, cy + 16), fill=(255, 255, 255, int(160 * (1 - k))))
        mask = Image.new("L", im.size, 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), 34, fill=255)
        im.putalpha(Image.fromarray(np.minimum(np.asarray(im.split()[3]), np.asarray(mask))))
        frame = Image.new("RGBA", (w + 12, h + 12), (0, 0, 0, 0))
        ImageDraw.Draw(frame).rounded_rectangle((0, 0, w + 11, h + 11), 40, fill=LAV + (255,))
        frame.paste(im, (6, 6), im)
        return shadowed(frame, blur=16, alpha=0.6)
    return make


for sp in PLAN.get("screens", []):
    ELS.append(El(sp["t"], sp["out"], sp.get("x", 300), sp.get("y", 1150), _screen_maker(sp), anim=sp.get("anim", "slide_u"),
                  dyn=True, bob=sp.get("bob", 0), d_in=sp.get("d_in", 0.35), cta_ok=True))
    add_sfx(sp["t"], sp.get("sfx", "whoosh"), sp.get("gain", -12))
    for dt, *_ in sp.get("taps", []):
        add_sfx(sp["t"] + dt, sp.get("tap_sfx", "pop_bubble"), sp.get("tap_gain", -12))
    if sp.get("type"):
        ty = sp["type"]; n = ty.get("ticks", 8)
        for i in range(n):
            add_sfx(sp["t"] + ty.get("start", 0.2) + i * ty.get("dur", 0.8) / n, "typing", -20)

for e in PLAN.get("sfx", []):
    add_sfx(e[0], e[1], e[2])

FRAMING = [tuple(f) for f in PLAN.get("framing", [])]
SHAKES = PLAN.get("shakes", [])
FLASHES = PLAN.get("flashes", [])
add_sfx_shake = PLAN.get("shake_sfx", "zoom_impact")
for t in SHAKES:
    if not any(abs(t - e[0]) < 0.15 for e in SFX_EV):
        add_sfx(t, add_sfx_shake, -11)
if PLAN.get("whoosh_on_punch", True):  # quiet sweep on punch-ins that have no other sound nearby
    for f in FRAMING:
        if f[4] and not in_cta(f[0]) and not any(abs(f[0] - e[0]) < 0.4 for e in SFX_EV):
            add_sfx(f[0], "sweep", -18)


# ---------------------------------------------------------------- framing (zoom/shake/flash)
def scale_at(t):
    if in_cta(t):
        return 1.0
    for f in FRAMING:
        t0, t1, s0, s1, punch = f[:5]
        if t0 <= t < t1:
            p = (t - t0) / (t1 - t0); s = s0 + (s1 - s0) * p
            if punch:
                k = ease_cubic(min((t - t0) / 0.16, 1.0)); s = 1 + (s - 1) * k
            return s
    return 1.0


def anchor_at(t):
    for f in FRAMING:
        if f[0] <= t < f[1] and len(f) > 5:
            return tuple(f[5])
    return ANCHOR


SHAKE_OFF = np.random.default_rng(3).uniform(-1, 1, (4000, 2))


def shake_at(t, n):
    for s in SHAKES:
        if s <= t < s + 0.35:
            return SHAKE_OFF[n] * (1 - (t - s) / 0.35) ** 2 * 22
    return (0.0, 0.0)


def flash_at(t):
    for f in FLASHES:
        if f - 0.03 <= t < f + 0.2:
            return 0.5 * (1 - max(0, t - f) / 0.2)
    return 0.0


probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,r_frame_rate:stream_side_data=rotation", "-of", "json", SRC],
                                  capture_output=True, check=True).stdout)["streams"][0]
SW, SH = probe["width"], probe["height"]
if abs(SW / SH - W / H) > 0.01:
    sys.exit(f"source must be 9:16 (got {SW}x{SH})")
num_, den_ = map(int, probe["r_frame_rate"].split("/")); FPS = num_ / den_


def transform(frame, t, n):
    s = scale_at(t); dx, dy = (0.0, 0.0) if in_cta(t) else shake_at(t, n)
    if dx or dy:
        s = max(s, 1.03)
    if abs(s - 1) < 1e-4 and not (dx or dy):
        return frame if SW == W else cv2.resize(frame, (W, H), interpolation=cv2.INTER_AREA)
    k = s * W / SW; ax, ay = anchor_at(t)
    M = np.array([[k, 0, ax * (1 - s) + dx], [0, k, ay * (1 - s) + dy]], np.float32)
    return cv2.warpAffine(frame, M, (W, H), flags=cv2.INTER_AREA if SW > W else cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REFLECT)


# ---------------------------------------------------------------- audio
def load_mp3(path):
    if not os.path.exists(path):
        path = path[:-4] + ".wav"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "48000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    return x / (np.max(np.abs(x)) + 1e-9)


def build_audio(path_out):
    tmp = path_out + ".voice.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", SRC, "-vn", "-af",
                    "highpass=f=80,afftdn=nf=-30:nr=8,acompressor=threshold=-18dB:ratio=2.5:attack=10:release=150,"
                    "loudnorm=I=-14.5:LRA=9:TP=-2", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", tmp], check=True)
    with wave.open(tmp) as wf:
        v = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32).reshape(-1, 2) / 32768
    lib, mix = {}, v.copy()
    for t, name, g in SFX_EV:
        assert PLAN.get("cta_sfx_ok") or not in_cta(t), f"sound effect inside CTA at {t}s"
        if name not in lib:
            lib[name] = load_mp3(os.path.join(SFXDIR, name + ".mp3"))
        g = g + PLAN.get("sfx_gain", 0) + PLAN.get("sfx_trim", {}).get(name, 0)
        x = lib[name] * (10 ** (g / 20)); st = int(max(t, 0) * 48000); en = min(st + len(x), len(mix))
        for a, b in CTA:  # never let an effect ring on into the CTA
            if st < int(a * 48000) < en:
                en = int(a * 48000)
        if en <= st:
            continue
        fade = np.ones(en - st, np.float32); fl = min(2400, len(fade)); fade[-fl:] = np.linspace(1, 0, fl)
        mix[st:en] += (x[:en - st] * fade)[:, None]
    with wave.open(path_out, "w") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(48000)
        wf.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
    os.remove(tmp)


AUD = OUT + ".mix.wav"
build_audio(AUD)

# ---------------------------------------------------------------- video
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                        "-r", probe["r_frame_rate"], "-i", "-", "-i", AUD, "-map", "0:v", "-map", "1:a",
                        "-af", "alimiter=limit=0.84:level=false", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", OUT],
                       stdin=subprocess.PIPE)
n, fs = 0, SW * SH * 3
while True:
    buf = dec.stdout.read(fs)
    if len(buf) < fs:
        break
    t = n / FPS
    fr = transform(np.frombuffer(buf, np.uint8).reshape(SH, SW, 3), t, n % 4000)
    place.base = fr
    ff = None
    for el in ELS:
        ff = place(ff, el, t)
    fl = flash_at(t)
    if fl > 0:
        ff = (fr.astype(np.float32) if ff is None else ff) * (1 - fl) + 255 * fl
    out = fr if ff is None else np.clip(ff, 0, 255).astype(np.uint8)
    enc.stdin.write(np.ascontiguousarray(out).tobytes())
    n += 1
enc.stdin.close(); enc.wait(); dec.wait(); os.remove(AUD)
print(f"done: {n} frames -> {OUT}")
