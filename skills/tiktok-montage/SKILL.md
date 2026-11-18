---
name: tiktok-montage
description: Finish-edit a vertical (9:16) talking-head video into a high-energy TikTok/Reels cut in the "Пантеон литература" style — word-synced drawn icon cards, numbered tip headers, stamps, punch-in zooms, shakes, flashes and TikTok-style sound effects — while leaving the call-to-action (CTA) zone untouched. Use when the user asks to "домонтировать", add visuals/animation/dynamics/sound effects to a vertical video, or make a video "like the previous ones".
---

# TikTok montage (Пантеон литература style)

You turn an already-cut talking-head video (speech, subtitles and titles are usually burned in) into a maximally dynamic TikTok edit. You do **not** write drawing code: you write a JSON **edit plan** and render it with `scripts/render.py`. Everything is timed to the speaker's words.

Read these before planning (they are short):
- `references/style-guide.md` — palette, fonts, layout zones, pacing rules, what the references look like.
- `references/plan-format.md` — every plan field, every icon, every sound name.
- `examples/college_plan.json` — a complete, approved plan for a 47 s video. Copy its rhythm.

## Hard rules (never break)
1. **CTA zone is sacred.** The part where the speaker advertises the Telegram channel / pinned message / guide ("в моём телеграм-канале", "кликай на закреплённое", "забирай гайд") gets **no zoom, no overlays, no sound effects, no cuts, no speed change**. Put its `[start, end]` in `"cta"`; the renderer refuses overlays/SFX inside it. A video can have several CTA zones.
2. **Never cover the face** with anything. Cards go left/right of the head; headers and stamps go on the torso.
3. **Never cover burned-in text**: the opening title (usually first ~2–3 s), the subtitles, the watermark. Start your own hook after the source title disappears.
4. Do not remove or re-add the watermark. Do not cut speech unless asked.
5. Audio: voice ends at about −14 LUFS with peaks at or below −1.5 dBTP. The renderer does this; you only verify it.

## Workflow
1. **Setup** (once per machine):
   `pip install faster-whisper opencv-python-headless pillow numpy scipy` and have `ffmpeg` installed.
   `bash scripts/fetch_sfx.sh sfxlib` downloads the sound library (Mixkit, free licence, do not commit the files).
2. **Inspect** the source: `bash scripts/inspect.sh SOURCE work/` then open `work/sheet.jpg` and `work/opening.jpg`.
   Note: resolution must be 9:16; when the source title disappears; the subtitle line's y position; where the face is (x/y range in 1080×1920 coordinates); any existing phone/screen inserts (they mark the CTA).
3. **Transcribe**: `python3 scripts/transcribe.py SOURCE work/words.json` → segments + `word@time` list.
4. **Find the structure** in the transcript: hook question, "короткий ответ", numbered tips/factors (headers 1…N), CTA zone(s), finale ("вуаля", "главное…").
5. **Write the plan** `work/plan.json` (see the pacing rules in style-guide.md):
   - one **header** per tip/factor, from the word that starts it to just before the next one or the CTA;
   - a **card** or **stamp** on almost every concrete noun or verb: one every 1.5–3 s outside the CTA, alternating sides L/R;
   - **framing**: a new segment every 2–3 s, alternating ~1.0 (slow push) and 1.15–1.35 punch-ins (`true`) on emphasis words; cover the whole timeline except the CTA;
   - **shakes** on 2–4 strongest words ("нет!", "нереально", "никто"), **flashes** at every header start;
   - sound on every visual event (the defaults cover headers/cards/stamps; add extra `sfx` for typing, ticks, finale).
6. **Render**: `python3 scripts/render.py SOURCE work/out.mp4 work/plan.json sfxlib` (about 2× realtime on 4 CPU cores).
7. **QA**: `bash scripts/qa.sh work/out.mp4 work/qa <one time inside each overlay…>`, open `work/qa/qa_sheet.jpg`. Check that nothing covers the face or subtitles, all text is readable, the CTA is clean and loudness is about −14 LUFS. Fix the plan and re-render. Expect 1–2 iterations.
8. Deliver the mp4 and summarise for the user in Russian: what was added, the CTA times you left untouched, and open questions.

## When something does not fit
- The source is not 9:16 → ask the user; do not crop people out.
- The face sits much higher or lower than in the examples → change `"anchor"` (zoom centre ≈ face centre) and the card `y`.
- An idea needs a new icon → reuse `bigtext` (any short text or emoji-free symbol), or a `stamp`, before writing new drawing code. New icons go in `render.py` next to `ic_*` and get a branch in `icon()`.
