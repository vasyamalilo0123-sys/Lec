#!/bin/bash
# Увесь рендер, відновлюваний. Спершу кожен другий кадр (швидка чернетка всього ролика), потім решта.
# PY — python із встановленим модулем bpy (pip install bpy).
cd "$(dirname "$0")/.."
PY=${PY:-python3}
for step in 2 1; do
  for shot in sizes third flow outro; do
    $PY blender/render.py shot $shot 960 12 $step 2>&1 | grep -E "^SHOT|Traceback|Error" 
  done
done
