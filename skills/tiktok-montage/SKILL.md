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

## Raw sources (long, uncut, no subtitles)
If the source is raw footage ("лютый исходник"):
1. Transcribe the source and choose the story. Keep only what carries the point; drop side remarks, repeats, "понимаешь", rhetorical detours. Aim for a target length; at 1.2× the kept source must be ≤ target × 1.2.
2. Write `keep.json` with phrase ranges `[start, end, "speaker"]`. Run `CUT_DRY=1 python3 scripts/cut.py SRC keep.json cut.mp4 1.2` to see the kept seconds, iterate, then run it without `CUT_DRY`. The script strips pauses over 0.2 s inside each range, crossfades the joins and speeds up. `CUT_THR` (default 0.25) is the voice threshold; raise it for a noisy room, lower it if a quiet speaker gets cut.
3. Re-transcribe `cut.mp4` and plan everything on that timeline. Add `subtitles` and a title `text`, because raw sources have none.
   - **Lip-sync is sacred.** `cut.py` cuts every piece's picture and sound in one call and pads or trims the audio to the exact frame count. Never cut the picture with `select` and the sound separately: that drifted by up to 6 frames, and the user heard it as "sound separate from the picture". Check with `python3 scripts/vcheck.py SOURCE cut.mp4 cut.segments.json 1.2`: every piece should be within 0–1 frame.
   - **Level matching** is on by default: each piece's speech is brought to a common level (max +10 dB). This matters when only one person wears the mic.
   - Whisper's word times are unreliable around pauses and quiet speakers. For short key replies ("Пушкин.", "Да.") find the word on the volume profile and add `"all"` as the 4th element of the keep range. Then confirm the word made it into the cut by re-transcribing it.
4. Two speakers in a wide shot: find who talks when (from content; mouth motion is noisy). Track faces with `scripts/faces.py` (MediaPipe BlazeFace on tiles; `pip install mediapipe`, `apt-get install libegl1 libgles2`, model URL in the script header) and take each shot's zoom anchor from the median face position in that shot. Then alternate a two-shot (about 1.45×) with singles (1.7–1.8×, face centred) on the active speaker. In two-shots, put cards between the heads, not beside them.

## Workflow
1. **Setup** (once per machine):
   `pip install faster-whisper opencv-python-headless pillow numpy scipy` and have `ffmpeg` installed.
   Sounds: the user prefers the **soft synthesized set**. Run `python3 scripts/make_synth_sfx.py sfxsynth` and use `sfxsynth` as SFX_DIR. The Mixkit set (`bash scripts/fetch_sfx.sh sfxlib`) was judged "too harsh"; use it only if asked.
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
