# Style guide

## Look
| Item | Value |
|---|---|
| Output | 1080×1920, H.264 CRF 17, AAC 192k, source frame rate |
| Accent / highlight | cream `#F6DC93` (`"cream"`) |
| Numbers, card borders | lavender `#A08CFF` (`"lav"`) |
| Plates / cards | plum `#1E1238`, ~80–90 % opaque, rounded corners |
| Positive / negative | green `#7CF29A` / red-pink `#FF5C7A` |
| Main text | white |
| Headline font | Unbounded Bold (`assets/fonts`) |
| Secondary font | Manrope Regular (card captions) |
| Text shadow | black at 70 % opacity, soft blur, small offset |

The source videos already contain burned-in word-by-word subtitles (white, centre, about y = 1260–1410), an opening title in cream "script" style (left-centre, first 2–3 s) and a small watermark near the top ("тгк: Пантеон литература"). Leave all three as they are.

## Layout (1080×1920 output coordinates)
```
 y   0 ┌───────────────────────────┐  TikTok UI band: keep empty
     ~ │   watermark (source) ~350 │
 400 │ [card L]   FACE   [card R] │  cards: centre (205,560) / (875,560), 280×300
 760 │            ~x 400–700     │
 840 │ 1 header     (torso)      │  header: top-left (50,840), big number + plate
1060 │      STAMP / hook text    │  stamps and hook text centred around y 1000–1120
1260 │   subtitles (source)      │  keep clear
1650 │                      [UI] │  bottom and right-bottom: TikTok UI, keep empty
1920 └───────────────────────────┘
```

## Pacing ("динамика на максимум")
- **Something new every 1.5–3 s** outside the CTA: a card, a stamp, a header, a punch-in or a shake. No static stretch longer than about 3 s.
- **Framing alternates** wide (1.00→1.05 slow push) and close (1.15–1.35 punch-in, eased in over 0.16 s). Cut on word boundaries (gaps between words). With a 4K source punch-ins up to about 1.4 stay sharp; with 1080p keep them at 1.30 or less.
- **Hook (first 2–7 s):** a zoom-out reveal at 0 s (1.25→1.0 in 0.3 s) with a deep impact sound. After the source title disappears, add big hook text built from the opening question (for example "КОЛЛЕДЖ → ВУЗ?", "4 СОВЕТА").
- **Each tip/factor:** a white flash, a header sliding in from the left (whoosh and impact), then 2–4 cards on its key words.
- **Emphasis words** get a stamp ("ДА!", "НЕРЕАЛЬНО", "НИКТО НЕ СКАЖЕТ", "ВУАЛЯ") and often a shake.
- **Finale:** sparkles, a summary checklist, a medal or "вуз мечты" card, and an "achievement" sound on the last words.
- Cards live 1–2.5 s. Headers live for the whole tip. Overlays exit 0.2 s after `out`.

## Sound (Mixkit, real recordings — sounds like normal TikTok edits)
- Every visual event has a sound: header = `swoosh_fast` + `zoom_impact`, card = `pop_light`, stamp = `pop_hard`/`zoom_impact`, positive = `correct`, negative = `buzzer`, magic = `sparkle`, finale = `achievement`.
- Sound effects sit 8–18 dB under the voice (gain −8 … −18). Never put a sound effect in the CTA.
- Earlier experiment: synthesised effects sounded "AI-made", and the user preferred real samples.

## Reference analysis (what the approved videos do)
- r3 «ЕГЭ — лотерея» (the main reference): framing changes every 2–4 s; big lavender numbers with white text for list items; rounded-corner photo and screenshot cards; one keyword-per-word subtitle.
- r6 «Найди своих» and r4 «1/3 · 2/3 · 3/3»: numbered progress headers; cream accent.
- Approved results: `examples/college_plan.json` («Колледж»). «Советы» (88 s, two CTA zones, 4 tips) used the same density: about 25 overlays and 22 framing segments.
