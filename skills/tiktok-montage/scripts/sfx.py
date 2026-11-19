"""Synthesized sound effects (no external samples). All return float32 mono @ 48 kHz, peak 1.0."""
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
rng = np.random.default_rng(7)


def _t(d):
    return np.arange(int(SR * d)) / SR


def _norm(x):
    return (x / (np.max(np.abs(x)) + 1e-9)).astype(np.float32)


def _bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x)


def _lp(x, f, order=2):
    return sosfilt(butter(order, f, "lowpass", fs=SR, output="sos"), x)


def whoosh(d=0.45, up=True):
    n = int(SR * d); noise = rng.standard_normal(n)
    out = np.zeros(n); hop = 512
    for i in range(0, n, hop):
        p = i / n
        fc = 400 + 3200 * (p if up else 1 - p)
        seg = noise[max(0, i - 2048):i + hop]
        out[i:i + hop] = _bp(seg, fc * 0.6, min(fc * 1.6, 20000))[-len(out[i:i + hop]):]
    env = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5
    return _norm(out * env)


def pop(f0=950, f1=280, d=0.09):
    t = _t(d); f = f1 + (f0 - f1) * np.exp(-t * 45)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return _norm(np.sin(ph) * np.exp(-t * 38))


def ding(f=1320, d=0.9):
    t = _t(d)
    x = sum(a * np.sin(2 * np.pi * f * k * t) * np.exp(-t * (4 + 3 * k)) for k, a in [(1, 1), (2.01, .45), (3.02, .2), (4.2, .1)])
    return _norm(x * (1 - np.exp(-t * 400)))


def thud(d=0.35):
    t = _t(d)
    body = np.sin(2 * np.pi * (55 + 60 * np.exp(-t * 25)) * t) * np.exp(-t * 11)
    click = _lp(rng.standard_normal(len(t)), 1800) * np.exp(-t * 90) * 0.6
    return _norm(body + click)


def tick(f=2600, d=0.03):
    t = _t(d)
    return _norm(_bp(rng.standard_normal(len(t)), f * 0.7, f * 1.4) * np.exp(-t * 220))


def sparkle(d=0.8, n=9):
    out = np.zeros(int(SR * d))
    for _ in range(n):
        st = int(rng.uniform(0, d - 0.25) * SR); f = rng.uniform(2400, 5200); t = _t(0.25)
        out[st:st + len(t)] += np.sin(2 * np.pi * f * t) * np.exp(-t * 22) * rng.uniform(.4, 1)
    return _norm(out)


def scratch(d=0.28):
    t = _t(d)
    x = _bp(rng.standard_normal(len(t)), 900, 4500) * np.sin(np.pi * np.linspace(0, 1, len(t)))
    return _norm(x * (0.6 + 0.4 * np.sin(2 * np.pi * 30 * t)))


def glide(f0, f1, d=0.6):
    t = _t(d); f = np.geomspace(f0, f1, len(t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.3 * np.sin(2 * ph)
    env = np.minimum(1, t * 40) * np.minimum(1, (d - t) * 12)
    return _norm(x * env)


def impact(d=0.6):
    t = _t(d)
    sub = np.sin(2 * np.pi * (45 + 80 * np.exp(-t * 18)) * t) * np.exp(-t * 6)
    nz = _lp(rng.standard_normal(len(t)), 3000) * np.exp(-t * 25) * 0.5
    return _norm(sub + nz)
