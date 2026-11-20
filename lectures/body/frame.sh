#!/bin/bash
# Кадр під ключ: ./frame.sh <сцена> [ширина=1920] [семпли=64]. Чернетка: ./frame.sh <сцена> 960 16
cd "$(dirname "$0")"
PY=${PY:-python3}
$PY still.py "$1" ${2:-1920} ${3:-64} 2>&1 | grep -E "^STILL|Traceback|Error|error|line " ; node compose.js "$1"
