"""Writes the soft synthesized sound set (the one used for «Советы») as WAV files under the
same names the engine uses, so a plan can switch libraries by pointing SFX_DIR here.
usage: python3 make_synth_sfx.py OUT_DIR"""
import os, sys, wave, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfx

out = sys.argv[1]; os.makedirs(out, exist_ok=True)
lib = {
    "whoosh": sfx.whoosh(), "swoosh_fast": sfx.whoosh(0.25), "swoosh_quick": sfx.whoosh(0.35),
    "sweep": sfx.whoosh(0.3), "fly_swoosh": sfx.whoosh(0.6),
    "pop_light": sfx.pop(), "pop_msg": sfx.pop(1100, 400, 0.08), "pop_bubble": sfx.pop(1300, 600, 0.06),
    "pop_hard": sfx.thud(), "zoom_impact": sfx.impact(), "deep_impact": sfx.impact(0.9),
    "ding": sfx.ding(), "correct": sfx.ding(1568, 0.8), "achievement": sfx.ding(1320, 1.2),
    "bonus": sfx.ding(1760, 0.6), "level_done": sfx.ding(1175, 1.2),
    "buzzer": sfx.glide(420, 160, 0.5), "boing": sfx.glide(300, 900, 0.3),
    "sparkle": sfx.sparkle(), "typing": sfx.tick(), "tick_fast": sfx.tick(), "shutter": sfx.tick(1800, 0.05),
    "scratch": sfx.scratch(), "drain": sfx.glide(900, 160, 1.2), "charge": sfx.glide(260, 1300, 0.9),
}
for name, x in lib.items():
    with wave.open(os.path.join(out, name + ".wav"), "w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sfx.SR)
        wf.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
print(f"{len(lib)} sounds -> {out}")
