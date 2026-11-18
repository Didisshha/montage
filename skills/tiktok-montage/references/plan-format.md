# Edit plan format (`plan.json`)

All times are in seconds on the **source** timeline (use the `word@time` list). Coordinates are in the 1080×1920 output. Every key is optional except `cta` (use `[]` when the video has no CTA).

```jsonc
{
  "cta": [[16.38, 24.70]],      // untouched zones: no zoom/overlay/sfx. Several allowed.
  "anchor": [540, 690],         // zoom centre ≈ the speaker's face centre
  "texts":   [ ... ],           // free text blocks (the hook)
  "headers": [ ... ],           // numbered tip/factor headers
  "cards":   [ ... ],           // icon cards beside the head
  "stamps":  [ ... ],           // rotated outlined words that slam in
  "sparkles":[ ... ],           // twinkling stars beside the head
  "sfx":     [[t, "name", gainDb], ...],   // extra sounds
  "framing": [[t0, t1, scaleStart, scaleEnd, punch], ...],
  "shakes":  [t, ...],          // 0.35 s camera shake (+ zoom_impact unless a sound is already there)
  "flashes": [t, ...],          // 0.2 s white flash
  "whoosh_on_punch": true       // quiet "sweep" on punch-ins that have no other sound nearby
}
```

## texts
`{"t":3.0,"out":7.3,"x":540,"y":1010,"lines":[["КОЛЛЕДЖ","UB",96,"white"]],"anim":"pop","align":"center","sfx":"pop_hard","gain":-9}`
Each line is `[text, "UB"|"MR", size, color]`. `anim`: `pop`, `slide_l`, `slide_r`, `stamp` or `fade`.

## headers
`{"n":1,"l1":"фактор","l2":"даты","t":10.6,"out":16.15}`. This draws a big lavender number with a plum plate holding two lines (white l1, cream l2), sliding in from the left at (50, 840). Default sounds: `swoosh_fast` and `zoom_impact`. Override them with `sfx_in` / `sfx_hit`.

## cards
`{"t":11.78,"out":13.95,"side":"R","icon":"calendar","caption":"даты олимпиад","sfx":"pop_light","gain":-8}`
`side`: `L` (centre x 205) or `R` (x 875). `y` defaults to 560. `border`: a colour name (`red` for negative, `green` for positive). Defaults are `sfx` = `pop_light` and `gain` = −8.

| icon | what it shows | extra keys |
|---|---|---|
| `uni` | university building | |
| `target` | target with arrow (focus) | |
| `pause` | pause button (rest/breaks) | |
| `warning` | warning triangle | |
| `bigcheck` | big green tick | |
| `medal` | medal with star | `label` |
| `bigtext` | any short text, e.g. "2–3", "?", "8 ч" | `text`, `color`, `size` (0.3–0.5) |
| `counter` | number counting up, then turning green | `to`, `start`, `dur` |
| `calendar` | calendar with a date being circled | |
| `checklist` | rows ticked one by one | `rows`, `step` |
| `magnifier` | wobbling magnifier (find out) | |
| `book_speed` | open book with speed lines (speed-reading) | |
| `books` | stack growing (reading volume) | `drops` (offsets in s) |
| `clock` | clock with spinning hand | `speed` (deg/s) |
| `battery_drain` | battery emptying to red (tiredness) | `dur` |
| `battery_charge` | battery charging (rest) | `dur` |
| `quote` | « » with typing dots (quotes/poems) | |
| `lifebuoy` | rotating lifebuoy | |
| `medals_strike` | three medals crossed out | `strike_at` |

## stamps
`{"t":8.08,"out":9.4,"text":"ДА!","color":"green","x":540,"y":1060,"size":110,"angle":-6,"sfx":"correct","gain":-9}`

## sparkles
`{"t":41.9,"out":43.3,"side":"L","y":520,"sfx":"sparkle","gain":-10}`

## framing
`[t0, t1, s0, s1, punch]`. The scale moves linearly from s0 to s1. `punch: true` eases in from 1.0 over 0.16 s, so it reads as a hard punch-in. Segments should tile the timeline outside the CTA. Inside the CTA the renderer forces 1.0 anyway. Use `99` as the last t1.

## Sound names (`sfxlib/<name>.mp3`, from `scripts/fetch_sfx.sh`)
| name | use |
|---|---|
| `whoosh`, `swoosh_fast`, `swoosh_quick`, `sweep`, `fly_swoosh` | transitions, slides, punch-ins |
| `pop_light`, `pop_hard`, `pop_msg`, `pop_bubble` | cards, stamps, checklist ticks |
| `zoom_impact`, `deep_impact` | headers, shakes, video start |
| `correct`, `achievement`, `bonus`, `level_done`, `ding` | positive moments, finale |
| `buzzer` | "no" / wrong |
| `sparkle` | magic / "вуаля" / "блеснуть" |
| `typing`, `tick_fast`, `shutter`, `boing` | keyboard, clock, photo, comic "?" |

Gains: cards about −8, stamps −8 … −10, background details −12 … −18.
