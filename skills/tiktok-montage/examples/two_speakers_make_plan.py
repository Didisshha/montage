import json, sys
sys.path.insert(0, "/home/user/montage/skills/tiktok-montage/scripts")
from plan_helpers import anchor_for, words_from

W4 = "/tmp/claude-0/-home-user-montage/7dd93770-ed8c-50cb-9cc1-068fa60600fd/scratchpad/work4/"
PLUS = "/tmp/claude-0/-home-user-montage/7dd93770-ed8c-50cb-9cc1-068fa60600fd/scratchpad/dl/plus/"
PLUS2 = PLUS.replace("plus/", "plus2/")
segs = json.load(open(W4 + "cut2.segments.json"))
END = 88.39
FACE = {"L": (300, 750), "R": (790, 740)}
MID = (545, 745)
CTA_A, CTA_B = 72.90, 80.22   # Фариша's channel mention, then Pantheon (screens)


def two(s0, s1, punch=False):
    return [s0, s1, punch, anchor_for(MID, (540, 720), (s0 + s1) / 2)]


def single(who, s0, s1, punch=True, out=(540, 700)):
    return [s0, s1, punch, anchor_for(FACE[who], out, (s0 + s1) / 2)]


# --- framing: change shot on jump cuts (hides them), min ~1.6 s per shot, alternate two-shot / single
bounds = [0.0] + [round(s[1], 3) for s in segs]
spk = lambda t: next((s[2] for s in segs if s[0] <= t < s[1]), "R")
framing, t, k = [], 0.0, 0
framing.append([0.0, 0.35, 1.6, 1.22, False, anchor_for(MID, (540, 720), 1.4)])  # zoom-out reveal
t = 0.35
cands = [b for b in bounds if b > t + 1.6]
while t < CTA_A - 0.1:
    nxt = next((b for b in bounds if b >= t + 1.6 and b <= CTA_A), CTA_A)
    if CTA_A - nxt < 1.2:
        nxt = CTA_A
    tot = {"L": 0.0, "R": 0.0}
    for s_ in segs:
        tot[s_[2]] += max(0.0, min(s_[1], nxt) - max(s_[0], t))
    who = max(tot, key=tot.get)  # whoever talks most in this shot
    shot = k % 4
    if shot == 0:
        s0, s1, p, a = two(1.22, 1.28)
    elif shot == 1:
        s0, s1, p, a = single(who, 1.70, 1.74)
    elif shot == 2:
        s0, s1, p, a = two(1.34, 1.36, True)
    else:
        s0, s1, p, a = single(who, 1.78, 1.80)
    framing.append([round(t, 3), round(nxt, 3), s0, s1, p, a]); t = nxt; k += 1
framing.append([CTA_A, CTA_B, 1.80, 1.84, True, anchor_for(FACE["R"], (770, 640), 1.82)])
framing.append([CTA_B, 99, 1.88, 1.92, True, anchor_for(FACE["R"], (770, 640), 1.90)])

# --- words for subtitles (from the cut's own transcript)
words = words_from(W4 + "cut2_words.json")
fix = {"фанвизина": "Фонвизина", "фанвизину": "Фонвизина", "бугакова": "Булгакова", "недоросли": "«Недоросль»",
       "недросы": "«Недоросль»", "метрофанушку": "Митрофанушку", "метрофан": "Митрофан", "стародума": "Стародума",
       "отписала": "расписала", "обавление": "добавление", "eg": "ЕГЭ", "pantheon": "Пантеон", "literatura": "литература",
       "ура": "которое", "-е": "", "которым": "о котором", "собачье": "«Собачье", "сердце": "сердце»", "ревизор": "«Ревизор»"}
clean = []
for s, e, w in words:
    key = w.lower().strip(".,?!«»")
    if key == "как?" or (w == "Как?" and 37.9 < s < 38.3):
        continue  # stray word picked up in a pause
    if key in fix:
        w = fix[key]
        if not w:
            continue
    clean.append([s, e, w])

plan = {
    "cta": [],
    "anchor": [540, 720],
    "header_pos": [40, 905],
    "brand": {"text": "тгк: пантеон литература", "y": 255, "size": 38, "alpha": 0.6},
    "subtitles": {"words": clean, "y": 1330, "size": 64,
                  "highlight": ["ЕГЭ", "олимпиаде", "олимпиада", "Олимпиаде", "Олимпиада", "оригинальность",
                                "невежества", "прогресса", "прогресс", "невежество", "смелости", "клише", "Пантеон"],
                  "zones": [[CTA_A, 99, 770, 1250]]},
    "texts": [
        {"t": 0.05, "out": 3.55, "x": 540, "y": 1060, "lines": [["ЕГЭ", "UB", 120, "white"], ["vs ОЛИМПИАДА", "UB", 76, "cream"]],
         "anim": "pop", "d_in": 0.14, "sfx": None},
    ],
    "headers": [
        {"n": 1, "l1": "как в", "l2": "ЕГЭ", "t": 11.55, "out": 19.40},
        {"n": 2, "l1": "как на", "l2": "олимпиаде", "t": 19.55, "out": 29.55},
        {"n": 3, "l1": "первая фраза:", "l2": "ЕГЭ", "t": 35.90, "out": 42.95},
        {"n": 3, "l1": "первая фраза:", "l2": "олимпиада", "t": 43.10, "out": 61.55},
        {"n": 4, "l1": "база", "l2": "одна", "t": 65.40, "out": 72.70},
    ],
    "cards": [
        {"t": 7.00, "out": 8.30, "x": 540, "y": 470, "icon": "bigtext", "text": "Недоросль", "size": 0.15, "caption": "Фонвизин"},
        {"t": 8.40, "out": 10.10, "x": 540, "y": 470, "icon": "bigtext", "text": "Собачье сердце", "size": 0.105, "caption": "Булгаков"},
        {"t": 15.40, "out": 19.30, "side": "R", "icon": "checklist", "rows": 3, "step": 1.0, "caption": "3 героя",
         "sfx": "pop_bubble", "gain": -14},
        {"t": 20.20, "out": 21.90, "side": "L", "icon": "bigtext", "text": "200", "caption": "слов в ЕГЭ"},
        {"t": 22.70, "out": 24.30, "side": "R", "icon": "bigtext", "text": "300–400", "size": 0.2, "caption": "на олимпиаде",
         "sfx": "ding", "gain": -16},
        {"t": 27.10, "out": 28.45, "side": "L", "icon": "calendar", "caption": "история"},
        {"t": 28.50, "out": 29.55, "side": "R", "icon": "book_speed", "caption": "биография"},
        {"t": 30.60, "out": 32.30, "x": 540, "y": 470, "icon": "quote", "caption": "первая фраза"},
        {"t": 33.45, "out": 35.80, "side": "L", "icon": "bigtext", "text": "ЕГЭ", "size": 0.3, "caption": "чётко"},
        {"t": 34.48, "out": 35.80, "side": "R", "icon": "bigtext", "text": "ОЛИМП", "size": 0.2, "caption": "смело",
         "border": "cream"},
        {"t": 38.76, "out": 40.20, "side": "R", "icon": "calendar", "caption": "эпоха Просвещения"},
        {"t": 40.25, "out": 42.90, "side": "R", "icon": "bigtext", "text": "2 мира", "size": 0.18, "caption": "прогресс/невежество"},
        {"t": 54.60, "out": 56.40, "side": "L", "icon": "magnifier", "caption": "отражение"},
        {"t": 57.45, "out": 59.40, "side": "L", "icon": "bigtext", "text": "Ревизор", "size": 0.17, "caption": "Гоголь"},
        {"t": 59.70, "out": 61.55, "side": "R", "icon": "bigtext", "text": "Собачье сердце", "size": 0.105, "caption": "Булгаков"},
        {"t": 63.55, "out": 65.25, "side": "R", "icon": "book_speed", "caption": "эрудиция"},
        {"t": 67.25, "out": 70.60, "side": "R", "icon": "checklist", "rows": 3, "step": 0.95, "caption": "текст·логика·факты",
         "sfx": "pop_bubble", "gain": -14},
    ],
    "stamps": [
        {"t": 3.92, "out": 6.40, "text": "ПРОГРЕСС vs НЕВЕЖЕСТВО", "color": "cream", "y": 1110, "size": 46, "angle": -4},
        {"t": 14.14, "out": 15.30, "text": "100%", "color": "green", "x": 540, "y": 1150, "size": 90, "angle": -7, "sfx": "correct"},
        {"t": 25.20, "out": 26.70, "text": "ОРИГИНАЛЬНОСТЬ", "color": "cream", "y": 1150, "size": 58, "angle": -5},
        {"t": 49.16, "out": 51.30, "text": "ЛИЦО НЕВЕЖЕСТВА", "color": "red", "y": 1150, "size": 58, "angle": -5},
        {"t": 62.14, "out": 63.50, "text": "ВЫПЕНДРИВАЙСЯ", "color": "cream", "y": 1150, "size": 60, "angle": -6},
        {"t": 76.40, "out": 80.00, "text": "БАЗА КЛИШЕ ДЛЯ ЕГЭ", "color": "cream", "x": 790, "y": 1470, "size": 30, "angle": -4},
        {"t": 80.40, "out": 83.00, "text": "тгк: пантеон литература", "color": "cream", "x": 790, "y": 1470, "size": 28, "angle": -4,
         "sfx": "pop_light"},
        {"t": 74.00, "out": 76.30, "text": "тгк: Мать стобалльников", "color": "lav", "x": 790, "y": 1470, "size": 28, "angle": -4,
         "sfx": "pop_light"},
        {"t": 71.48, "out": 72.70, "text": "+ СМЕЛОСТЬ", "color": "green", "y": 1150, "size": 70, "angle": -6, "sfx": "correct"},
    ],
    "sparkles": [{"t": 57.45, "out": 61.50, "side": "R", "y": 470, "sfx": "sparkle", "gain": -16}],
    "screens": [
        {"t": 73.90, "out": 75.55, "img": PLUS2 + "IMG_3195.png", "x": 290, "y": 1080, "w": 470,
         "type": {"box": [0.115, 0.13, 0.50, 0.33], "start": 0.2, "dur": 0.85, "ticks": 8}, "taps": [[1.2, 0.5, 0.77]]},
        {"t": 75.55, "out": 76.70, "img": PLUS2 + "IMG_3199.png", "x": 290, "y": 1150, "w": 470, "anim": "pop", "sfx": "swoosh_fast"},
        {"t": 76.70, "out": 78.10, "img": PLUS2 + "IMG_3196.png", "x": 290, "y": 1190, "w": 470, "anim": "pop",
         "taps": [[0.4, 0.42, 0.115]], "sfx": "swoosh_fast"},
        {"t": 78.10, "out": 80.05, "img": PLUS2 + "IMG_3197.png", "x": 290, "y": 1190, "w": 470, "anim": "pop",
         "taps": [[0.7, 0.40, 0.42]], "sfx": "swoosh_fast"},
        {"t": 80.22, "out": 81.95, "img": PLUS + "IMG_3190.png", "x": 290, "y": 1080, "w": 470,
         "type": {"box": [0.115, 0.15, 0.48, 0.31], "start": 0.25, "dur": 0.85, "ticks": 7}, "taps": [[1.3, 0.45, 0.79]]},
        {"t": 81.95, "out": 83.00, "img": PLUS + "IMG_3191.png", "x": 290, "y": 1190, "w": 470, "anim": "pop",
         "taps": [[0.45, 0.45, 0.125]], "sfx": "swoosh_fast"},
        {"t": 83.00, "out": 86.25, "img": PLUS + "IMG_3193.png", "x": 290, "y": 1190, "w": 470, "anim": "pop",
         "taps": [[0.30, 0.40, 0.31]], "sfx": "swoosh_fast"},
        {"t": 86.25, "out": 88.60, "img": PLUS + "IMG_3194.png", "x": 290, "y": 1150, "w": 470, "anim": "pop", "sfx": "swoosh_fast"},
    ],
    "sfx": [[0.0, "deep_impact", -12], [0.05, "whoosh", -16], [3.95, "whoosh", -17], [7.0, "pop_light", -16],
            [87.30, "achievement", -18]],
    "sfx_trim": {"pop_light": -8, "pop_hard": -2, "swoosh_fast": -6, "zoom_impact": -5, "whoosh": -3, "sweep": -2,
                 "correct": -6, "ding": -2, "pop_bubble": -2},
    "framing": framing,
    "shakes": [14.14, 49.16, 62.14],
    "flashes": [11.55, 19.55, 29.66, 65.40, 80.22],
}


def shot_at(t):
    for f in framing:
        if f[0] <= t < f[1]:
            return "two" if (f[2] + f[3]) / 2 < 1.6 or f[0] >= CTA_B else "single"
    return "two"


def shot_span(t):
    for f in framing:
        if f[0] <= t < f[1]:
            return f[0], f[1]
    return t, 99


for c in plan["cards"]:
    side = c.pop("side", None); c.pop("x", None); c.pop("y", None)
    a, b = shot_span(c["t"] + 0.05)
    if b - c["t"] < 0.8:            # too little of this shot left: start in the next shot instead
        c["t"] = b + 0.02; a, b = shot_span(c["t"] + 0.05)
    c["out"] = min(c["out"], b - 0.2)  # leave before the framing changes (0.2 s exit)
    sh = shot_at(c["t"] + 0.1)
    if sh == "two":
        c["x"] = {"L": 385, "R": 695}.get(side, 540); c["y"] = 470
    else:
        c["x"] = {"L": 205, "R": 875}.get(side, 875); c["y"] = 560
    c["shot"] = sh
json.dump(plan, open(W4 + "plan.json", "w"), ensure_ascii=False, indent=1)
print(len(framing), "framing segments;", len(clean), "subtitle words")
for f in framing:
    print(f[:5])
