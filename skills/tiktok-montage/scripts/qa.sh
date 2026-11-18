#!/usr/bin/env bash
# QA a render: a contact sheet at the given times (one per planned overlay is ideal) + loudness.
# usage: qa.sh OUT.mp4 OUTDIR t1 t2 t3 ...
set -euo pipefail
v=$1; out=$2; shift 2; mkdir -p "$out"; rm -f "$out"/qa_*.jpg; i=0
for t in "$@"; do i=$((i+1))
  ffmpeg -v error -y -ss $t -i "$v" -frames:v 1 -vf "scale=240:-1,drawtext=text='$t':x=6:y=6:fontsize=22:fontcolor=red" "$out/qa_$(printf %02d $i).jpg"
done
ffmpeg -v error -y -pattern_type glob -i "$out/qa_*.jpg" -vf tile=7x3 "$out/qa_sheet.jpg"
ffmpeg -hide_banner -i "$v" -vn -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):"
echo "open $out/qa_sheet.jpg: check faces are never covered, text is readable, nothing is in the CTA."
