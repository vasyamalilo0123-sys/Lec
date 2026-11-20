# Звукова доріжка: голос + синтезоване оточення (серцебиття, гул кровотоку, перехідні «подихи» на склейках).
# Серце прискорюється, коли в кадрі настає анемія (компенсаторна тахікардія). Жодних готових записів — лише numpy.
import json, os, subprocess, wave
import numpy as np
here = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.path.join(here, 'timeline.json')))
SR = 44100
T = TL['total_frames'] / TL['fps']
n = int(T * SR); t = np.arange(n) / SR
rng = np.random.default_rng(3)
cuts = [s['start'] / TL['fps'] for s in TL['shots'][1:]]

def lowpass(x, fc, order=2):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / (1 + (f / fc) ** (2 * order)), len(x))

def bandpass(x, f0, f1):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X * (1 / (1 + (f / f1) ** 6)) * (1 - 1 / (1 + (f / f0) ** 6)), len(x))

# серцебиття: 62 уд/хв → 94 після настання анемії
bpm = np.interp(t, [0, TL['voice']['n2'] - 1, TL['voice']['n2'] + 5, T], [62, 62, 94, 94])
phase = np.cumsum(bpm / 60) / SR
beats = [np.searchsorted(phase, k) / SR for k in range(1, int(phase[-1]) + 1)]
heart = np.zeros(n)
def thump(at, f0, f1, dec, amp):
    i = int(at * SR); m = int(0.5 * SR)
    if i + m >= n: return
    tt = np.arange(m) / SR
    fr = f1 + (f0 - f1) * np.exp(-tt / 0.03)
    heart[i:i + m] += amp * np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-tt / dec) * np.minimum(1, tt / 0.004)
for b in beats:
    per = 60 / np.interp(b, t[::SR], bpm[::SR])
    thump(b, 82, 44, 0.085, 1.0); thump(b + 0.30 * per, 96, 54, 0.06, 0.62)
heart = lowpass(heart, 160)

# гул кровотоку: низький «коричневий» шум із повільним диханням + тихий тон
def brown(seed):
    x = np.cumsum(np.random.default_rng(seed).standard_normal(n)); x -= np.linspace(x[0], x[-1], n)
    return bandpass(x / np.max(np.abs(x)), 30, 260)
flowL, flowR = brown(1), brown(2)
breath = 0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * t)
pad = (0.5 * np.sin(2 * np.pi * 55 * t) + 0.3 * np.sin(2 * np.pi * 82.41 * t + 1) + 0.16 * np.sin(2 * np.pi * 110.3 * t)) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.07 * t))

# «подих» на склейках
whoosh = np.zeros(n)
for c in cuts:
    env = np.exp(-((t - c) / 0.28) ** 2)
    whoosh += bandpass(rng.standard_normal(n), 300, 2400) * env
whoosh /= max(1e-9, np.max(np.abs(whoosh)))

# голос
voice = np.zeros(n)
for vid, start in TL['voice'].items():
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', os.path.join(here, 'audio', vid + '.mp3'), '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'])
    x = np.frombuffer(raw, np.float32); i = int(start * SR); voice[i:i + len(x)] += x[:n - i]
venv = lowpass(np.abs(voice), 4); venv /= max(1e-9, venv.max())
duck = 1 - 0.5 * np.clip(venv * 4, 0, 1)

fade = np.clip(t / 1.2, 0, 1) * np.clip((T - t) / 1.6, 0, 1)
amb_c = 0.50 * heart + 0.10 * pad
L = (amb_c + 0.55 * flowL * breath + 0.10 * whoosh) * duck * fade * 0.42 + voice * 0.95
R = (amb_c + 0.55 * flowR * breath + 0.10 * np.roll(whoosh, 400)) * duck * fade * 0.42 + voice * 0.95
st = np.stack([L, R], 1); st = st / max(1.0, np.max(np.abs(st)) / 0.97)
out = os.path.join(here, 'render', 'mix.wav'); os.makedirs(os.path.dirname(out), exist_ok=True)
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes())
print('mix', round(T, 2), 's, beats', len(beats))
