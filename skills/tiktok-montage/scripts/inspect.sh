#!/usr/bin/env bash
# Look at a source video before planning: format, loudness, existing cuts, a contact sheet,
# and full frames from the first seconds (to see burned-in titles/subtitles/watermark).
# usage: inspect.sh VIDEO OUTDIR
set -euo pipefail
src=$1; out=$2; mkdir -p "$out"
ffprobe -v error -show_entries format=duration:stream=codec_type,codec_name,width,height,r_frame_rate -of compact "$src"
echo "--- loudness"; ffmpeg -hide_banner -i "$src" -vn -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" || true
echo "--- existing cuts (s)"; ffmpeg -i "$src" -vf "select='gt(scene,0.08)',showinfo" -an -f null - 2>&1 | grep -o "pts_time:[0-9.]*" | cut -d: -f2 | tr '\n' ' '; echo
d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$src")
ffmpeg -v error -y -i "$src" -vf "fps=18/$d,scale=200:-1,tile=9x2" -frames:v 1 "$out/sheet.jpg"
for t in 0.3 1.5 3 6 12; do
  ffmpeg -v error -y -ss $t -i "$src" -frames:v 1 -vf "scale=360:-1,drawtext=text='$t':x=6:y=6:fontsize=24:fontcolor=red" "$out/f_$t.jpg"
done
ffmpeg -v error -y -i "$out/f_0.3.jpg" -i "$out/f_1.5.jpg" -i "$out/f_3.jpg" -i "$out/f_6.jpg" -i "$out/f_12.jpg" -filter_complex hstack=5 "$out/opening.jpg"
echo "wrote $out/sheet.jpg and $out/opening.jpg — open them and look."
