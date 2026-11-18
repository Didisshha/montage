#!/usr/bin/env bash
# Downloads the Mixkit sound effects used by render_college.py into $1 (default: sfxlib/).
# Mixkit Free License: free to use in videos; do not redistribute the raw files (so they are not committed).
set -euo pipefail
dir=${1:-sfxlib}; mkdir -p "$dir"
for p in whoosh:1490 sweep:166 swoosh_quick:1464 swoosh_fast:3115 pop_light:3005 pop_hard:2364 pop_msg:2354 \
         pop_bubble:2357 zoom_impact:772 deep_impact:1143 correct:2870 achievement:600 ding:586 shutter:1133 \
         buzzer:950 typing:1125 tick_fast:1063 sparkle:3062 bonus:2060 level_done:2059 boing:2894 fly_swoosh:1469; do
  n=${p%%:*}; i=${p##*:}
  curl -sSfL -o "$dir/$n.mp3" "https://assets.mixkit.co/active_storage/sfx/$i/$i-preview.mp3"
done
