#!/usr/bin/env bash
# Process a raw app-walkthrough recording (from the PoT app directory) into
# LinkedIn-ready crops. Recipes validated 2026-05-22 (ffmpeg 8.1.1).
#
# Usage:
#   scripts/process_recording.sh <input.(webm|mp4)> [out_basename]
#
# Produces in matchmaker_content/assets/:
#   <base>.mp4       normalized h264 (audio stripped — Playwright video is silent)
#   <base>_4x5.mp4   1080x1350  (LinkedIn portrait — primary)
#   <base>_1x1.mp4   1080x1080  (LinkedIn square)
#
# Smart crop: if the source is already portrait/4:5, it scales without losing
# content; if landscape, it center-crops. Keep the key UI centred when recording.
#
# PII blur is NOT automated here — see the template at the bottom. Prefer recording
# against demo/seeded data so no blur is needed at all.
set -euo pipefail

IN="${1:?usage: process_recording.sh <input.(webm|mp4)> [out_basename]}"
BASE="${2:-$(basename "${IN%.*}")}"
OUTDIR="matchmaker_content/assets"
mkdir -p "$OUTDIR"

IFS=, read -r W H < <(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$IN")
echo "source: ${W}x${H}"

MP4="$OUTDIR/${BASE}.mp4"
ffmpeg -y -v error -i "$IN" -c:v libx264 -pix_fmt yuv420p -crf 18 -preset slow -an "$MP4"
echo "normalized -> $MP4"

# crop_to <ratio_w> <ratio_h> <out_w> <out_h> <suffix>
crop_to() {
  local rw=$1 rh=$2 ow=$3 oh=$4 suf=$5
  # target aspect = rw/rh. Compare to source W/H via cross-multiplication (integer-safe).
  local cw ch cx cy
  if (( W * rh >= H * rw )); then          # source wider than target -> crop width
    cw=$(( H * rw / rh )); ch=$H; cx=$(( (W - cw) / 2 )); cy=0
  else                                      # source taller -> crop height
    cw=$W; ch=$(( W * rh / rw )); cx=0; cy=$(( (H - ch) / 2 ))
  fi
  # ensure even dims for h264
  cw=$(( cw - cw % 2 )); ch=$(( ch - ch % 2 ))
  ffmpeg -y -v error -i "$MP4" -vf "crop=${cw}:${ch}:${cx}:${cy},scale=${ow}:${oh}" \
    -c:v libx264 -pix_fmt yuv420p -an "$OUTDIR/${BASE}_${suf}.mp4"
  echo "cropped -> $OUTDIR/${BASE}_${suf}.mp4 (${ow}x${oh})"
}

crop_to 4 5 1080 1350 4x5
crop_to 1 1 1080 1080 1x1

echo "done."

# --- PII blur template (fill coords + timestamps from the actual footage) -------
# Find the on-screen box (x,y,w,h) of the name to hide and the seconds it's visible,
# then run (repeat the crop/overlay pair per region):
#
#   ffmpeg -i "$MP4" -filter_complex \
#     "[0:v]crop=W:H:X:Y,boxblur=15[b];[0:v][b]overlay=X:Y:enable='between(t,T1,T2)'" \
#     -c:v libx264 -pix_fmt yuv420p -an "$OUTDIR/${BASE}_blurred.mp4"
#
# Then re-run this script on *_blurred.mp4 to produce the crops.
