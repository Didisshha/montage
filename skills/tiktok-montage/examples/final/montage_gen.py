"""Shared plan builder for the two-speaker edits (1.mov, 2.mov).
Text on screen comes ONLY from proofread strings; timings come from Whisper via align_subs."""
import json, sys, numpy as np
sys.path.insert(0, "/home/user/montage/skills/tiktok-montage/scripts")
from plan_helpers import anchor_for, align_subs

DL = "/tmp/claude-0/-home-user-montage/7dd93770-ed8c-50cb-9cc1-068fa60600fd/scratchpad/dl/"
PANT, MAT = DL + "plus/", DL + "plus2/"
SOUNDS = ["correct", "buzzer", "ding", "achievement", "pop_light"]   # minimal: meaning only, no whooshes


def glue(subs):
    """Russian typesetting for one-word subtitles: short prepositions/conjunctions/pronouns stick to the next
    word ("в отражении", "её ценности"); a near-instant word that ends a phrase sticks to the previous one."""
    out = []
    i = 0
    while i < len(subs):
        s, e, w = subs[i]
        core = w.strip("«»,.?!:;…")
        short = e - s < 0.15
        if i + 1 < len(subs) and (len(core) <= 2 or short) and not w.endswith((".", ",", "?", "!", ":", "…")):
            s2, e2, w2 = subs[i + 1]
            subs[i + 1] = [s, e2, w + " " + w2]; i += 1; continue
        if out and e - s < 0.12 and w.endswith(("?", "!", ".")) and len(core) <= 3:
            ps, pe, pw = out[-1]; out[-1] = [ps, e, pw + " " + w]; i += 1; continue
        out.append([s, e, w]); i += 1
    return out


class Gen:
    def __init__(self, segs_json, words_json, faces_json, text, default_faces):
        self.segs = json.load(open(segs_json)); self.END = self.segs[-1][1]
        self.subs = glue(align_subs(text, words_json))
        self.track = {"L": [], "R": []}
        for t, fs in json.load(open(faces_json)):
            for f in fs:
                if f[4] >= 0.75 and f[1] < 1000:
                    self.track["L" if f[0] < 560 else "R"].append((t, f[0], f[1]))
        self.DEFAULT = default_faces
        self.cards, self.stamps, self.texts, self.screens, self.sparkles, self.headers = [], [], [], [], [], []
        self.extra_sfx, self.shakes, self.framing = [], [], []

    # ---- word lookup on the proofread text
    def wt(self, sub, after=0.0, end=False):
        n = lambda x: x.lower().replace("ё", "е").strip("«»,.?!:;")
        for s, e, w in self.subs:
            if s >= after - 1e-6 and n(sub) in n(w):
                return e if end else s
        raise KeyError(sub)

    def face(self, who, t0, t1):
        pts = [(x, y) for t, x, y in self.track[who] if t0 <= t <= t1]
        if not pts:
            pts = [(x, y) for t, x, y in self.track[who] if t0 - 3 <= t <= t1 + 3]
        return tuple(np.median(np.array(pts), 0)) if pts else self.DEFAULT[who]

    def speaker(self, a, b):
        tt = {"L": 0.0, "R": 0.0}
        for s in self.segs:
            tt[s[2]] += max(0.0, min(s[1], b) - max(s[0], a))
        return max(tt, key=tt.get)

    # ---- framing: change shot on jump cuts; two-shot / single alternate; screens = offset single
    def build_framing(self, screens_windows):
        bounds = sorted({0.0} | {round(s[1], 3) for s in self.segs})
        fl, fr = self.face("L", 0, 2), self.face("R", 0, 2)
        self.framing = [[0.0, 0.35, 1.5, 1.15, False, anchor_for(((fl[0] + fr[0]) / 2, (fl[1] + fr[1]) / 2), (540, 760), 1.32)]]
        k = [0]

        def normal(a, b):
            t = a
            while t < b - 0.05:
                nxt = next((x for x in bounds if t + 1.5 <= x <= b), b)
                if b - nxt < 1.0:
                    nxt = b
                who = self.speaker(t, nxt); l_, r_ = self.face("L", t, nxt), self.face("R", t, nxt)
                mid = ((l_[0] + r_[0]) / 2, (l_[1] + r_[1]) / 2); shot = k[0] % 4
                if shot in (0, 2):
                    s0, s1, p = (1.18, 1.24, False) if shot == 0 else (1.30, 1.32, True)
                    self.framing.append([round(t, 3), round(nxt, 3), s0, s1, p, anchor_for(mid, (540, 760), (s0 + s1) / 2)])
                else:
                    s0, s1 = (1.68, 1.70) if shot == 1 else (1.78, 1.80)
                    self.framing.append([round(t, 3), round(nxt, 3), s0, s1, True, anchor_for(self.face(who, t, nxt), (540, 700), (s0 + s1) / 2)])
                t = nxt; k[0] += 1

        cur = 0.35
        for a, b, who in screens_windows:
            normal(cur, a)
            out = (770, 640) if who == "R" else (320, 640)
            self.framing.append([round(a, 3), round(b, 3), 1.82, 1.86, True, anchor_for(self.face(who, a, b), out, 1.84)])
            cur = b
        normal(cur, self.END)
        self.framing[-1][1] = 99
        self.windows = screens_windows

    def shot_at(self, t):
        return next((f for f in self.framing if f[0] <= t < f[1]), self.framing[-1])

    # ---- elements
    def card(self, t, out, side, **kw):
        f = self.shot_at(t + 0.05)
        if f[1] - t < 0.8:
            t = f[1] + 0.02; f = self.shot_at(t + 0.05)
        out = min(out, f[1] - 0.2)
        if out - t < 0.6:
            print("  dropped card:", kw.get("text", kw.get("icon")), round(t, 2)); return
        two = (f[2] + f[3]) / 2 < 1.5
        x = {"L": 385, "R": 695}.get(side, 540) if two else {"L": 205, "R": 875}[side or "R"]
        self.cards.append(dict(t=round(t, 3), out=round(out, 3), x=x, y=490 if two else 560, sfx=None, **kw))

    def stamp(self, t, out, text, color="cream", size=64, sfx="pop_light", gain=-14, x=540, y=1180):
        self.stamps.append(dict(t=round(t, 3), out=round(out, 3), text=text, color=color, size=size, x=x, y=y, angle=0, sfx=sfx, gain=gain))

    def header(self, n, l1, l2, t, out):
        self.headers.append(dict(n=n, l1=l1, l2=l2, t=round(t, 3), out=round(out, 3), sfx_in=None, sfx_hit=None))

    def screen(self, t, out, img, x=290, y=1150, **kw):
        self.screens.append(dict(t=round(t, 3), out=round(out, 3), img=img, x=x, y=y, w=470, sfx=None, tap_sfx=None, **kw))

    def label(self, t, out, text, who="R", color="cream"):
        """small caption under the phone side opposite to the screen"""
        self.stamp(t, out, text, color=color, size=28, x=290 if who == "R" else 790, y=700, sfx=None)  # above the phone

    def write(self, path, flashes=(), hook_sfx=True):
        zones = [[a, b, 775 if w == "R" else 305, 1300, 54] for a, b, w in self.windows]
        plan = {
            "cta": [], "anchor": [540, 760], "header_pos": [40, 880],
            "brand": {"text": "тгк: пантеон литература", "y": 255, "size": 38, "alpha": 0.6},
            "subtitles": {"words": self.subs, "y": 1330, "size": 64, "zones": zones, "highlight": self.highlight},
            "texts": self.texts, "headers": self.headers, "cards": self.cards, "stamps": self.stamps,
            "sparkles": self.sparkles, "screens": self.screens,
            "sfx": self.extra_sfx, "sfx_allow": SOUNDS, "whoosh_on_punch": False, "shake_sfx": None,
            "sfx_trim": {"correct": -6, "ding": -4, "buzzer": -6, "achievement": -4},
            "framing": self.framing, "shakes": self.shakes, "flashes": list(flashes),
        }
        json.dump(plan, open(path, "w"), ensure_ascii=False, indent=1)
        print(f"plan: {len(self.framing)} shots, {len(self.cards)} cards, {len(self.stamps)} stamps, "
              f"{len(self.screens)} screens, {len(self.subs)} subtitle words, END {self.END:.2f}")
