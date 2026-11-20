# Складання ролика: кадри 3D → 1080p, кінографіка (сяйво, контраст, віньєтка, зерно), титри, звук.
# Працює на будь-якому стані рендеру: якщо кадру ще немає, бере найближчий готовий попередній (чернетка).
#   python assemble.py [вихідний файл]
import json, os, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.path.join(here, 'timeline.json'))); R = os.path.join(here, 'render'); fps = TL['fps']
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, 'anemia.mp4')
lines = []; missing = 0
for s in TL['shots']:
    last = None
    for f in range(s['frames']):
        p = os.path.join(R, s['shot'], f'{f:04d}.png')
        if os.path.exists(p): last = p
        else: missing += 1
        if last is None: sys.exit(f"немає першого кадру плану {s['shot']}")
        lines.append(f"file '{last}'\nduration {1 / fps:.6f}")
lst = os.path.join(R, 'frames.txt'); open(lst, 'w').write('\n'.join(lines) + '\n')
T = TL['total_frames'] / fps
fc = ("[0:v]fps=%d,scale=1920:1080:flags=lanczos,format=gbrp,split[a][b];"
      "[b]gblur=sigma=26,eq=brightness=-0.06:contrast=1.3[bl];[a][bl]blend=all_mode=screen:all_opacity=0.30,"
      "eq=contrast=1.14:saturation=1.06:gamma=0.94,vignette=PI/4.6,noise=alls=7:allf=t+u,format=yuv444p[g];"
      "[g][1:v]overlay=format=auto,fade=t=in:st=0:d=0.8,fade=t=out:st=%.3f:d=0.7,format=yuv420p[v];"
      "[2:a]loudnorm=I=-14:TP=-1.5:LRA=11[a2]") % (fps, T - 0.7)
cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-framerate', str(fps), '-i', os.path.join(R, 'overlay', '%04d.png'),
       '-i', os.path.join(R, 'mix.wav'), '-filter_complex', fc, '-map', '[v]', '-map', '[a2]', '-t', f'{T:.3f}',
       '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', out]
subprocess.check_call(cmd)
print('готово:', out, '| кадрів без власного рендеру:', missing, 'із', TL['total_frames'])
