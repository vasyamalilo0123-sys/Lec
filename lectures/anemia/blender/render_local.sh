#!/bin/bash
# Рендер на власному комп'ютері через встановлений Blender (4.4+), одразу в повній якості. Відновлюваний.
#   ./blender/render_local.sh            — 1920×1080, 32 семпли
#   WIDTH=1280 SAMPLES=24 ./blender/render_local.sh
cd "$(dirname "$0")/.."
BLENDER=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}
command -v "$BLENDER" >/dev/null || BLENDER=blender
for shot in sizes third flow outro; do
  "$BLENDER" -b --python-exit-code 1 -P blender/render.py -- shot $shot ${WIDTH:-1920} ${SAMPLES:-32} 1 2>&1 | grep -E "^SHOT|^Cycles:|Traceback|Error"
done
