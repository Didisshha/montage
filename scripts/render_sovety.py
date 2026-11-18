"""Finish-edit for 'советы.mov': drawn icon cards, tip headers, punch-ins, shakes, flashes + synthesized SFX.
CTA zones are passed through untouched (no zoom, overlays or SFX).
usage: python3 render_sovety.py SRC OUT"""
import subprocess, sys, math, os, wave
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfx

SRC, OUT = sys.argv[1], sys.argv[2]
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts") + "/"
W, H, FPS = 1080, 1920, 30000 / 1001
CREAM, WHITE, LAV, PLUM, RED, GREEN = (0xF6, 0xDC, 0x93), (255, 255, 255), (0xA0, 0x8C, 0xFF), (0x1E, 0x12, 0x38), (0xFF, 0x5C, 0x7A), (0x7C, 0xF2, 0x9A)
CTA = [(33.90, 47.52), (78.58, 999)]
ANCHOR = (540, 560)
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
    def __init__(self, t_in, t_out, cx, cy, make, anim="pop", dyn=False, bob=6.0, rot=0.0, d_in=0.28):
        self.t_in, self.t_out, self.cx, self.cy = t_in, t_out, cx, cy
        self.make, self.anim, self.dyn, self.bob, self.rot, self.d_in = make, anim, dyn, bob, rot, d_in
        self.cache = {}
        assert not any(a < t_out + 0.2 and t_in < b for a, b in CTA), f"overlay in CTA {t_in}"

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
    if t < el.t_in or t >= el.t_out + 0.2:
        return frame_f
    tr = t - el.t_in
    a_in = min(tr / el.d_in, 1.0); a_out = max(0.0, (t - el.t_out) / 0.2)
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


# ---------------------------------------------------------------- layout
LX, RX, IY = 205, 875, 560          # card centers: left / right of the head
HX, HY = 50, 840                     # tip header top-left
ELS, SFX_EV = [], []


def header(n, l1, l2, t_in, t_out):
    num = text_img([(str(n), UB(190), LAV)])
    t0 = text_img([(l1, UB(46), WHITE), (l2, UB(46), CREAM)])
    pad = 14
    txt = Image.new("RGBA", (t0.width + 2 * pad - 40, t0.height + 2 * pad - 40), (0, 0, 0, 0))
    ImageDraw.Draw(txt).rounded_rectangle((0, 0, txt.width - 1, txt.height - 1), 26, fill=PLUM + (205,))
    txt.paste(t0, (pad - 30, pad - 30), t0)
    im = Image.new("RGBA", (num.width + txt.width, max(num.height, txt.height)), (0, 0, 0, 0))
    im.paste(num, (0, 0), num); im.paste(txt, (num.width - 30, (num.height - txt.height) // 2 + 10), txt)
    ELS.append(El(t_in, t_out, HX + im.width / 2, HY + im.height / 2, im, anim="slide_l", bob=0, d_in=0.3))
    SFX_EV.extend([(t_in - 0.12, "whoosh", -15), (t_in, "impact", -13), (t_in + 0.25, "pop", -18)])


def cardel(t_in, t_out, side, make, dyn=False, sfx_name="pop", gain=-16, cy=IY):
    ELS.append(El(t_in, t_out, LX if side == "L" else RX, cy, make, anim="pop", dyn=dyn))
    SFX_EV.append((t_in, sfx_name, gain))


# Hook 0..7.3
# source already shows "советы олимпиаднику" until ~2.3s -> hook enters after it
hook = text_img([("4 СОВЕТА", UB(124), CREAM)], align="center")
ELS.append(El(2.45, 7.15, 540, 1000, hook, anim="pop", bob=4, d_in=0.18))
SFX_EV += [(0.0, "impact", -13), (2.40, "whoosh", -17), (2.47, "pop", -14)]
ELS.append(El(3.32, 7.15, RX, IY, stamp_img("БВИ", CREAM, 72, -10), anim="stamp", bob=0, d_in=0.16))
SFX_EV.append((3.42, "thud", -10))
cardel(4.86, 7.15, "L", card(ic_medal(""), "призёр"), sfx_name="ding", gain=-18)

# Tip 1: 7.44..24.4
header(1, "фокус на", "2–3 олимпиадах", 7.44, 24.40)
cardel(8.56, 10.70, "R", card(ic_target, "фокус"))
cardel(11.86, 13.15, "L", card(ic_uni, "вуз мечты"))
ELS.append(El(13.52, 15.40, RX, IY, lambda p: card(ic_medals_strike(min(max((p - 0.8) / 0.4, 0), 1)), "во всех?"), dyn=True))
SFX_EV += [(13.52, "pop", -16), (14.32, "scratch", -14)]
cardel(16.40, 18.70, "L", card(ic_bigtext("2–3"), "олимпиады"))
ELS.append(El(19.96, 21.60, RX, IY, stamp_img("БВИ", CREAM, 64, 8), anim="stamp", bob=0, d_in=0.16))
SFX_EV.append((20.06, "thud", -11))
ELS.append(El(22.72, 24.40, LX, IY, lambda p: card(ic_bigtext(str(int(100 * min(max((p - 0.9) / 0.45, 0), 1))), CREAM if p < 1.35 else GREEN, .3), "баллов"), dyn=True))
SFX_EV.append((22.72, "pop", -16))
SFX_EV += [(23.62 + i * 0.05, "tick", -22) for i in range(9)] + [(24.08, "ding", -15)]

# Tip 2: 24.52..33.86
header(2, "освой", "скорочтение", 24.52, 33.62)
ELS.append(El(25.36, 27.30, RX, IY, lambda p: card(ic_book_speed(p), "скорочтение"), dyn=True))
SFX_EV += [(25.36, "pop", -16), (25.50, "whoosh_fast", -20)]
drops = [27.34, 27.70, 28.12, 28.62, 28.90, 29.30]
ELS.append(El(27.34, 30.40, LX, IY, lambda p: card(ic_books(sum(1 for d in drops if 27.34 + p >= d)), "весь объём"), dyn=True))
SFX_EV += [(d, "tick_low", -14) for d in drops]
ELS.append(El(31.04, 33.30, 540, 1095, stamp_img("НЕРЕАЛЬНО", RED, 70, -6), anim="stamp", bob=0, d_in=0.16))
SFX_EV.append((31.12, "thud", -9))

# Tip 3: 47.66..64.3
header(3, "закладывай", "перерывы", 47.70, 64.26)
cardel(49.60, 51.40, "R", card(ic_pause, "пауза"))
ELS.append(El(54.46, 57.40, LX, IY, lambda p: card(ic_clock(p * 900), "8 часов в день"), dyn=True))
SFX_EV += [(54.46, "pop", -16)] + [(54.6 + i * 0.25, "tick", -20) for i in range(11)]
ELS.append(El(59.20, 62.40, RX, IY, lambda p: card(ic_battery(max(0.04, 1 - p / 2.4), False), "усталость", border=RED), dyn=True))
SFX_EV += [(59.20, "pop", -16), (59.6, "drain", -19)]
ELS.append(El(62.72, 64.20, LX, IY, lambda p: card(ic_battery(min(1, 0.1 + p / 1.1), True), "отдых", border=GREEN), dyn=True))
SFX_EV += [(62.72, "charge", -18)]

# Tip 4: 64.36..78.5
header(4, "учи", "стихи", 64.40, 78.30)
ELS.append(El(66.74, 69.00, RX, IY, lambda p: card(ic_quote((p * 2) % 1.0), "2–3 цитаты"), dyn=True))
SFX_EV += [(66.74, "pop", -16)] + [(66.9 + i * 0.16, "tick", -21) for i in range(10)]
ELS.append(El(68.50, 70.90, LX, IY, lambda p: card(ic_buoy(p * 220), "спасательный круг", border=RED), dyn=True, rot=0))
SFX_EV += [(68.40, "whoosh", -17), (68.55, "pop", -15)]
cardel(72.60, 74.40, "R", card(ic_medal(""), "финал"), sfx_name="ding", gain=-18)
ELS.append(El(74.90, 77.40, LX, 520, lambda p: sparkles_img(p, 1), dyn=True, bob=0, anim="fade"))
ELS.append(El(75.00, 77.40, RX, 520, lambda p: sparkles_img(p, 2), dyn=True, bob=0, anim="fade"))
SFX_EV.append((75.05, "sparkle", -15))

# ---------------------------------------------------------------- framing (zoom/shake/flash)
FRAMING = [  # (t0, t1, s0, s1, punch)
    (0.00, 0.35, 1.18, 1.00, False), (0.35, 2.40, 1.00, 1.04, False), (2.40, 4.72, 1.20, 1.22, True), (4.72, 7.40, 1.08, 1.12, False),
    (7.40, 10.72, 1.00, 1.05, False), (10.72, 13.15, 1.18, 1.20, True), (13.15, 15.42, 1.00, 1.03, False),
    (15.42, 18.74, 1.15, 1.17, True), (18.74, 21.58, 1.00, 1.05, False), (21.58, 24.48, 1.20, 1.24, True),
    (24.48, 26.45, 1.00, 1.05, False), (26.45, 29.76, 1.14, 1.17, True), (29.76, 31.00, 1.00, 1.02, False),
    (31.00, 33.88, 1.28, 1.30, True),
    (47.62, 51.40, 1.00, 1.06, False), (51.40, 55.78, 1.18, 1.21, True), (55.78, 59.82, 1.00, 1.05, False),
    (59.82, 62.44, 1.22, 1.24, True), (62.44, 64.32, 1.08, 1.12, False),
    (64.32, 66.30, 1.00, 1.05, False), (66.30, 70.42, 1.16, 1.18, True), (70.42, 74.38, 1.00, 1.06, False),
    (74.38, 76.70, 1.24, 1.26, True), (76.70, 78.50, 1.05, 1.08, False),
]
SHAKES = [13.22, 31.04, 53.04]
FLASHES = [7.44, 24.52, 47.70, 64.40]
SFX_EV += [(t, "whoosh", -17) for t in SHAKES]


def scale_at(t):
    if in_cta(t):
        return 1.0
    for t0, t1, s0, s1, punch in FRAMING:
        if t0 <= t < t1:
            p = (t - t0) / (t1 - t0); s = s0 + (s1 - s0) * p
            if punch:
                k = ease_cubic(min((t - t0) / 0.16, 1.0)); s = 1 + (s - 1) * k
            return s
    return 1.0


rng = np.random.default_rng(3)
SHAKE_OFF = rng.uniform(-1, 1, (4000, 2))


def shake_at(t, n):
    for s in SHAKES:
        if s <= t < s + 0.35:
            k = (1 - (t - s) / 0.35) ** 2 * 22
            return SHAKE_OFF[n] * k
    return (0.0, 0.0)


def flash_at(t):
    for f in FLASHES:
        if f - 0.03 <= t < f + 0.22:
            return 0.65 * (1 - max(0, t - f) / 0.22)
    return 0.0


def transform(frame, t, n):
    if in_cta(t):
        return frame
    s = scale_at(t); dx, dy = shake_at(t, n)
    if abs(s - 1) < 1e-4 and dx == 0 and dy == 0:
        return frame
    s = max(s, 1.03) if (dx or dy) else s  # avoid showing edges while shaking
    ax, ay = ANCHOR
    M = np.array([[s, 0, ax * (1 - s) + dx], [0, s, ay * (1 - s) + dy]], np.float32)
    return cv2.warpAffine(frame, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


# ---------------------------------------------------------------- audio
def build_audio(path_out):
    tmp = path_out + ".voice.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", SRC, "-vn", "-af",
                    "highpass=f=80,afftdn=nf=-30:nr=8,acompressor=threshold=-18dB:ratio=2.5:attack=10:release=150,"
                    "loudnorm=I=-14.5:LRA=9:TP=-2", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", tmp], check=True)
    with wave.open(tmp) as wf:
        v = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32).reshape(-1, 2) / 32768
    lib = {"whoosh": sfx.whoosh(), "whoosh_fast": sfx.whoosh(0.25), "pop": sfx.pop(), "ding": sfx.ding(),
           "thud": sfx.thud(), "tick": sfx.tick(), "tick_low": sfx.tick(900, 0.06), "sparkle": sfx.sparkle(),
           "scratch": sfx.scratch(), "drain": sfx.glide(900, 160, 1.2), "charge": sfx.glide(260, 1300, 0.9),
           "impact": sfx.impact()}
    mix = v.copy()
    for t, name, g in SFX_EV:
        assert not in_cta(t), f"sfx in CTA at {t}"
        x = lib[name] * (10 ** (g / 20)); st = int(max(t, 0) * sfx.SR)
        en = min(st + len(x), len(mix)); mix[st:en] += x[:en - st, None]
    out = np.clip(mix, -1, 1)
    with wave.open(path_out, "w") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(48000)
        wf.writeframes((out * 32767).astype(np.int16).tobytes())
    os.remove(tmp)


AUD = OUT + ".mix.wav"
build_audio(AUD)

# ---------------------------------------------------------------- video
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                        "-r", "30000/1001", "-i", "-", "-i", AUD, "-map", "0:v", "-map", "1:a",
                        "-af", "alimiter=limit=0.84:level=false", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", OUT],
                       stdin=subprocess.PIPE)
n, fs = 0, W * H * 3
while True:
    buf = dec.stdout.read(fs)
    if len(buf) < fs:
        break
    t = n / FPS
    fr = transform(np.frombuffer(buf, np.uint8).reshape(H, W, 3), t, n % 4000)
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
print("frames", n)
