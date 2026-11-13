"""Проєкції опорних точок серця в кадр: python3 hproj.py <geo> <proj.json>"""
import json
import sys

import hscene

S = hscene.HeartScene(sys.argv[1])
S.sc.render.resolution_x, S.sc.render.resolution_y = 1920, 1080
S.set_camera(hscene.CAM)
json.dump({k: S.project(v) for k, v in S.lm.items()}, open(sys.argv[2], "w"), indent=1)
