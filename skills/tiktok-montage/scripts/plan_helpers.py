"""Small helpers for writing plans in Python (then json.dump the dict)."""


def anchor_for(face, out, s):
    """Zoom centre that puts source point `face` at output point `out` at scale `s` (1080x1920 coords)."""
    return [round((o - s * f) / (1 - s), 1) for f, o in zip(face, out)]


def words_from(transcript_json):
    import json
    d = json.load(open(transcript_json, encoding="utf-8"))
    return [[w["s"], w["e"], w["w"]] for seg in d for w in seg["words"]]


def align_subs(text, transcript_json):
    """Subtitles from a PROOFREAD text: every word of `text` gets its time from the nearest matching
    Whisper word (difflib alignment). Words Whisper misheard keep the correct spelling; words it missed
    get interpolated times. Dashes are dropped (one word per screen)."""
    import json, difflib, re
    ws = [w for seg in json.load(open(transcript_json, encoding="utf-8")) for w in seg["words"]]
    norm = lambda w: re.sub(r"[«»\"“”.,!?:;…()—–-]", "", w.lower().replace("ё", "е"))
    canon = [t for t in text.split() if t not in ("—", "–", "-")]
    A, B = [norm(t) for t in canon], [norm(w["w"]) for w in ws]
    times = [None] * len(canon)
    for op, a1, a2, b1, b2 in difflib.SequenceMatcher(None, A, B, autojunk=False).get_opcodes():
        if op == "equal":
            for i in range(a2 - a1):
                times[a1 + i] = (ws[b1 + i]["s"], ws[b1 + i]["e"])
        elif op == "replace":
            s0, s1 = ws[b1]["s"], ws[b2 - 1]["e"]; n = a2 - a1
            for i in range(n):
                times[a1 + i] = (s0 + (s1 - s0) * i / n, s0 + (s1 - s0) * (i + 1) / n)
    for i in range(len(times)):  # words Whisper did not hear at all: squeeze between neighbours
        if times[i] is None:
            prev = next((times[j][1] for j in range(i - 1, -1, -1) if times[j]), 0.0)
            nxt = next((times[j][0] for j in range(i + 1, len(times)) if times[j]), prev + 0.3)
            times[i] = (prev, max(prev + 0.12, min(nxt, prev + 0.35)))
    return [[round(a, 2), round(b, 2), w] for (a, b), w in zip(times, canon)]
