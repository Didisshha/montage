import json, sys, numpy as np
sys.path.insert(0, "/home/user/montage/skills/tiktok-montage/scripts")
from plan_helpers import anchor_for, words_from

W5 = "/tmp/claude-0/-home-user-montage/7dd93770-ed8c-50cb-9cc1-068fa60600fd/scratchpad/work5/"
DL = "/tmp/claude-0/-home-user-montage/7dd93770-ed8c-50cb-9cc1-068fa60600fd/scratchpad/dl/"
PANT, MAT = DL + "plus/", DL + "plus2/"
segs = json.load(open(W5 + "cut.segments.json"))
END = segs[-1][1]
words = words_from(W5 + "cut_words.json")


def wt(sub, after=0.0, end=False):
    """start (or end) time of the first word containing `sub` after `after`"""
    for s, e, w in words:
        if s >= after and sub.lower().replace("ё", "е") in w.lower().replace("ё", "е"):
            return e if end else s
    raise KeyError(sub)


# ---------------- faces: average L / R positions per time window (from faces.py)
fd = json.load(open(W5 + "faces.json"))
track = {"L": [], "R": []}
for t, fs in fd:
    for f in fs:
        if f[4] >= 0.75 and f[1] < 1000:
            track["L" if f[0] < 560 else "R"].append((t, f[0], f[1]))
DEFAULT = {"L": (300, 790), "R": (825, 710)}


def face(who, t0, t1):
    pts = [(x, y) for t, x, y in track[who] if t0 <= t <= t1]
    if not pts:
        pts = [(x, y) for t, x, y in track[who] if t0 - 3 <= t <= t1 + 3]
    return tuple(np.median(np.array(pts), 0)) if pts else DEFAULT[who]


# ---------------- key moments
T = {}
T["q1"] = wt("Какой"); T["gugl"] = wt("гуглить"); T["otvet1"] = wt("Корневильские")
T["cta1"] = wt("статью", T["otvet1"]); T["q2"] = wt("Горькому") - 0.6; T["stan"] = wt("Станислав")
T["net"] = wt("Нет", T["stan"]); T["andr"] = wt("Андреев"); T["druzh"] = wt("дружок")
T["q3"] = wt("Ещё"); T["bel"] = wt("Белинский"); T["epig"] = wt("графе", T["bel"]); T["cta2"] = wt("Фариши")
T["galka"] = wt("галочку"); T["q4"] = wt("последний"); T["plen"] = wt("пленник")
T["push"] = wt("Пушкин") if any("пушкин" in w.lower() for _, _, w in words) else T["plen"] + 1.2
T["umn"] = wt("умница"); T["outro"] = wt("говоря", T["umn"]) - 0.6; T["zakrep1"] = wt("закреп", T["outro"])
T["olymp"] = wt("готовитесь"); T["zakrep2"] = wt("закреп", T["olymp"])
print({k: round(v, 2) for k, v in T.items()})

# CTA windows (phone screens) and who talks there
SCR = [(T["cta1"], T["q2"] - 0.05, "R"), (T["cta2"] - 0.3, T["galka"] - 0.1, "R"),
       (T["zakrep1"] - 1.4, T["olymp"] - 0.15, "L"), (T["zakrep2"] - 1.0, END, "R")]

# ---------------- framing: shot changes on jump cuts, min 1.5 s; screens get offset singles
bounds = sorted({0.0} | {round(s[1], 3) for s in segs})
framing, t, k = [], 0.0, 0
framing.append([0.0, 0.35, 1.55, 1.15, False, anchor_for(((face("L", 0, 2)[0] + face("R", 0, 2)[0]) / 2, 750), (540, 760), 1.35)])
t = 0.35


def tot_speaker(a, b):
    tt = {"L": 0.0, "R": 0.0}
    for s_ in segs:
        tt[s_[2]] += max(0.0, min(s_[1], b) - max(s_[0], a))
    return max(tt, key=tt.get)


def add_normal(a, b):
    global k
    t_ = a
    while t_ < b - 0.05:
        nxt = next((x for x in bounds if x >= t_ + 1.5 and x <= b), b)
        if b - nxt < 1.0:
            nxt = b
        who = tot_speaker(t_, nxt); fl, fr = face("L", t_, nxt), face("R", t_, nxt)
        mid = ((fl[0] + fr[0]) / 2, (fl[1] + fr[1]) / 2)
        shot = k % 4
        if shot in (0, 2):
            s0, s1, p = (1.18, 1.24, False) if shot == 0 else (1.32, 1.34, True)
            fr_ = [round(t_, 3), round(nxt, 3), s0, s1, p, anchor_for(mid, (540, 760), (s0 + s1) / 2)]
        else:
            s0, s1 = (1.70, 1.73) if shot == 1 else (1.80, 1.82)
            fr_ = [round(t_, 3), round(nxt, 3), s0, s1, True, anchor_for(face(who, t_, nxt), (540, 700), (s0 + s1) / 2)]
        framing.append(fr_); t_ = nxt; k += 1


cur = 0.35
for a, b, who in SCR:
    add_normal(cur, a)
    out = (770, 640) if who == "R" else (320, 640)
    framing.append([round(a, 3), round(b, 3), 1.82, 1.86, True, anchor_for(face(who, a, b), out, 1.84)])
    cur = b
add_normal(cur, END)
framing[-1][1] = 99


def shot_at(t):
    for f in framing:
        if f[0] <= t < f[1]:
            return f
    return framing[-1]


# ---------------- subtitles
fix = {"егешника": "ЕГЭшника", "неегешным": "не-ЕГЭшным", "пантон": "Пантеон", "кэйзи": "Это же", "васильон": "Виссарион",
       "брижалова": "Бризжалова", "станислав": "Станиславский", "закрепке": "закрепе", "стабальников": "стобалльников",
       "егешных": "ЕГЭшных", "еге": "ЕГЭ", "литература": "литература"}
subs = []
for s, e, w in words:
    key = w.lower().strip(".,?!«»")
    if key in fix:
        w = w.lower().replace(key, fix[key]) if key != w.lower() else fix[key]
    subs.append([s, e, w])
zones = [[a, b, 770 if who == "R" else 310, 1250] for a, b, who in SCR]

# ---------------- elements
cards, stamps, texts, screens, sparkles, extra = [], [], [], [], [], []


def card(t, out, side, **kw):
    f = shot_at(t + 0.05)
    if f[1] - t < 0.8:                 # shot ends almost at once: start the card in the next shot
        t = f[1] + 0.02; f = shot_at(t + 0.05)
    out = min(out, f[1] - 0.2)
    if out - t < 0.6:
        print("dropped card", kw.get("text", kw.get("icon")), round(t, 2)); return
    two = (f[2] + f[3]) / 2 < 1.5
    x = {"L": 385, "R": 695}.get(side, 540) if two else {"L": 205, "R": 875}[side or "R"]
    cards.append(dict(t=t, out=out, x=x, y=520 if two else 560, **kw))


texts.append({"t": 0.05, "out": wt("МГУ") - 0.05, "x": 540, "y": 1080, "lines": [["ТЕСТ", "UB", 120, "white"], ["для ЕГЭшника", "UB", 66, "cream"]],
              "anim": "pop", "d_in": 0.14})
stamps.append({"t": wt("МГУ"), "out": wt("собрала") - 0.1, "text": "ОТБОР МГУ", "color": "lav", "x": 540, "y": 1080, "size": 72, "angle": -6})
card(wt("четыре"), wt("задача"), None, icon="bigtext", text="4", size=0.4, caption="вопроса")
card(wt("одного", 9) if any("одного" in w for _, _, w in words) else wt("один", 9), T["q1"] - 0.1, None, icon="bigtext", text="1/4", size=0.3, caption="хотя бы")

HEAD = [(1, "вопрос", "Чехов", T["q1"], T["cta1"] - 0.1), (2, "вопрос", "Горький", T["q2"], T["q3"] - 0.1),
        (3, "вопрос", "Тургенев", T["q3"], T["cta2"] - 0.4), (4, "вопрос", "Толстой", T["q4"], T["umn"] + 0.6)]
headers = [{"n": n, "l1": a, "l2": b, "t": t0, "out": t1} for n, a, b, t0, t1 in HEAD]

card(wt("смерти", T["q1"]), wt("чихнул") + 0.8, "R", icon="bigtext", text="Смерть\nчиновника", size=0.14, caption="Чехов")
card(wt("Жестко") if any("жестко" in w.lower() for _, _, w in words) else T["gugl"] - 1.5, T["gugl"] - 0.2, "L", icon="warning", caption="жёстко")
card(T["gugl"] - 0.4, T["otvet1"] - 0.1, "R", icon="magnifier", caption="гуглим")
stamps.append({"t": T["otvet1"], "out": T["cta1"] - 0.1, "text": "КОРНЕВИЛЬСКИЕ КОЛОКОЛА", "color": "cream", "y": 1180, "size": 42, "angle": -4, "sfx": "ding"})
card(T["q2"] + 0.5, T["stan"] - 0.1, "R", icon="bigtext", text="На дне", size=0.2, caption="Горький")
stamps.append({"t": T["stan"] + 0.4, "out": T["net"] + 0.7, "text": "МИМО", "color": "red", "y": 1180, "size": 80, "angle": -7, "sfx": "buzzer"})
stamps.append({"t": T["andr"] - 0.3, "out": T["druzh"] + 0.9, "text": "ЛЕОНИД АНДРЕЕВ", "color": "cream", "y": 1180, "size": 54, "angle": -5, "sfx": "ding"})
card(wt("Тургенев"), T["bel"] - 0.15, "R", icon="bigtext", text="Отцы\nи дети", size=0.17, caption="Тургенев")
stamps.append({"t": T["bel"], "out": T["epig"] - 0.1, "text": "ВЕРНО!", "color": "green", "y": 1180, "size": 84, "angle": -6, "sfx": "correct"})
card(T["epig"], T["cta2"] - 0.45, "R", icon="quote", caption="эпиграф")
stamps.append({"t": T["galka"] - 0.4, "out": T["q4"] - 0.1, "text": "+1 ГАЛОЧКА", "color": "green", "y": 1180, "size": 64, "angle": -6})
card(wt("Толстого"), T["push"] - 0.1, "R", icon="bigtext", text="Кавказский\nпленник", size=0.13, caption="Толстой")
stamps.append({"t": T["push"], "out": T["umn"] - 0.6, "text": "ПУШКИН — ВЕРНО!", "color": "green", "y": 1180, "size": 56, "angle": -6, "sfx": "correct"})
stamps.append({"t": T["umn"] - 0.5, "out": T["outro"] - 0.05, "text": "СЧЁТ 2/4", "color": "cream", "y": 1180, "size": 80, "angle": -6, "sfx": "achievement", "gain": -12})
sparkles += [{"t": T["push"], "out": T["outro"] - 0.1, "side": "L", "y": 470}, {"t": T["push"] + 0.1, "out": T["outro"] - 0.1, "side": "R", "y": 470, "sfx": "sparkle", "gain": -16}]
shakes = [T["stan"] + 0.4, T["bel"], T["push"]]


def scr(t, out, img, y=1150, **kw):
    screens.append(dict(t=t, out=out, img=img, x=kw.pop("x", 290), y=y, w=470, **kw))


# CTA 1: Pantheon (Маша) - статья
a, b, _ = SCR[0]; m = a + (b - a) * 0.5
scr(a, m, PANT + "IMG_3190.png", y=1080, type={"box": [0.115, 0.15, 0.48, 0.31], "start": 0.15, "dur": 0.7, "ticks": 6}, taps=[[m - a - 0.35, 0.45, 0.79]])
scr(m, b + 0.05, PANT + "IMG_3191.png", y=1190, anim="pop", sfx="swoosh_fast", taps=[[0.35, 0.45, 0.125]])
stamps.append({"t": a + 0.3, "out": b - 0.1, "text": "тгк: пантеон литература", "color": "cream", "x": 790, "y": 1470, "size": 28, "angle": -4, "sfx": "pop_light"})
# CTA 2: Мать стобалльников (Маша про Фаришу) - эпиграфы
a, b, _ = SCR[1]; d = (b - a) / 4
scr(a, a + d, MAT + "IMG_3195.png", y=1080, type={"box": [0.115, 0.13, 0.50, 0.33], "start": 0.15, "dur": 0.7, "ticks": 6}, taps=[[d - 0.3, 0.5, 0.77]])
scr(a + d, a + 2 * d, MAT + "IMG_3199.png", y=1150, anim="pop", sfx="swoosh_fast")
scr(a + 2 * d, a + 3 * d, MAT + "IMG_3196.png", y=1190, anim="pop", sfx="swoosh_fast", taps=[[0.35, 0.42, 0.115]])
scr(a + 3 * d, b + 0.05, MAT + "IMG_3197.png", y=1190, anim="pop", sfx="swoosh_fast", taps=[[0.5, 0.40, 0.42]])
stamps.append({"t": a + 0.3, "out": a + 2 * d, "text": "тгк: Мать стобалльников", "color": "lav", "x": 790, "y": 1470, "size": 28, "angle": -4, "sfx": "pop_light"})
stamps.append({"t": a + 2 * d + 0.1, "out": b - 0.1, "text": "АНАЛИЗ ВСЕХ ЭПИГРАФОВ", "color": "cream", "x": 790, "y": 1470, "size": 28, "angle": -4})
# CTA 3: Фариша - закреп «Мать стобалльников» (phone on the RIGHT, she is on the left)
a, b, _ = SCR[2]; m = a + (b - a) * 0.45
scr(a, m, MAT + "IMG_3199.png", x=790, y=1150)
scr(m, b + 0.05, MAT + "IMG_3196.png", x=790, y=1190, anim="pop", sfx="swoosh_fast", taps=[[0.4, 0.42, 0.115]])
stamps.append({"t": a + 0.3, "out": b - 0.1, "text": "закреп: Мать стобалльников", "color": "lav", "x": 300, "y": 1470, "size": 26, "angle": -4, "sfx": "pop_light"})
# CTA 4: Маша - у меня в закрепе (Pantheon)
a, b, _ = SCR[3]; m = a + (b - a) * 0.4
scr(a, m, PANT + "IMG_3191.png", y=1190, taps=[[0.4, 0.45, 0.125]])
scr(m, b + 0.3, PANT + "IMG_3193.png", y=1190, anim="pop", sfx="swoosh_fast", taps=[[0.6, 0.40, 0.31]])
stamps.append({"t": a + 0.3, "out": b, "text": "закреп: пантеон литература", "color": "cream", "x": 790, "y": 1470, "size": 26, "angle": -4, "sfx": "pop_light"})

plan = {
    "cta": [], "anchor": [540, 760], "header_pos": [40, 880],
    "brand": {"text": "тгк: пантеон литература", "y": 255, "size": 38, "alpha": 0.6},
    "subtitles": {"words": subs, "y": 1330, "size": 64, "zones": zones,
                  "highlight": ["ЕГЭшника", "МГУшной", "Олимпиады", "олимпиаде", "Корневильские", "колокола", "Андреев", "Леонид",
                                "Белинский", "Пушкин", "эпиграфов", "Пантеон", "стобалльников", "Чехова", "Горькому", "Тургенев", "Толстого"]},
    "texts": texts, "headers": headers, "cards": cards, "stamps": stamps, "sparkles": sparkles, "screens": screens,
    "sfx": [[0.0, "deep_impact", -12], [0.05, "whoosh", -16]],
    "sfx_trim": {"pop_light": -8, "pop_hard": -2, "swoosh_fast": -6, "zoom_impact": -5, "whoosh": -3, "sweep": -2,
                 "correct": -6, "ding": -2, "pop_bubble": -2, "buzzer": -4},
    "framing": framing, "shakes": shakes, "flashes": [h["t"] for h in headers],
}
json.dump(plan, open(W5 + "plan.json", "w"), ensure_ascii=False, indent=1)
print(len(framing), "framing,", len(cards), "cards,", len(stamps), "stamps,", len(screens), "screens; END", END)
