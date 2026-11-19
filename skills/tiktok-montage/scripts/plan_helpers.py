"""Small helpers for writing plans in Python (then json.dump the dict)."""


def anchor_for(face, out, s):
    """Zoom centre that puts source point `face` at output point `out` at scale `s` (1080x1920 coords)."""
    return [round((o - s * f) / (1 - s), 1) for f, o in zip(face, out)]


def words_from(transcript_json):
    import json
    d = json.load(open(transcript_json, encoding="utf-8"))
    return [[w["s"], w["e"], w["w"]] for seg in d for w in seg["words"]]
