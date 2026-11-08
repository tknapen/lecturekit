"""A small forward model of a bar-sweep pRF run, in numpy, for the kickoff deck's one clip (and its static figure).

Lifted from the Coimbra workshop's lecture 1 (`make_assets.py`), where the clip was first rendered, so that the example
deck renders its clip without the rest of that lecture. The clip prefers the recorded run in assets/data/s01.json
(a prfmodel forward model, 75 s shown); these functions are the fallback and the radial warp of the visual field.
"""
import numpy as np


def warp_r(rho, R, g=3.0):
    """Design radius -> visual radius: a radial log warp, compressed near fixation (schematic)."""
    return R * (np.exp(g * rho / R) - 1) / (np.exp(g) - 1)


def hrf(t, peak=5.0, under=15.0, ratio=6.0):
    """A two-gamma haemodynamic response, peak normalised to one."""
    from math import gamma
    def g(t, a): return np.where(t > 0, t ** (a - 1) * np.exp(-t) / gamma(a), 0.0)
    h = g(t, peak + 1) - g(t, under + 1) / ratio
    return h / h.max()


def bar_drive(px=2.5, py=1.5, s=1.0, R=8.0, w=2.0, step=0.8, dirs=(0, 90), n=101, blank=0):
    """Overlap of a sweeping bar with a Gaussian pRF, one value per TR (1 s); `blank` empty TRs after each sweep."""
    ax = np.linspace(-R, R, n); X, Y = np.meshgrid(ax, ax)
    g = np.exp(-((X - px) ** 2 + (Y - py) ** 2) / (2 * s * s)); inside = X ** 2 + Y ** 2 <= R * R
    out = []
    for d in dirs:
        th = np.deg2rad(d); u = X * np.cos(th) + Y * np.sin(th)
        for c in np.arange(-R, R + 1e-9, step): out.append(float((g * ((np.abs(u - c) <= w / 2) & inside)).sum()))
        out += [0.0] * blank
    out = np.array(out); return out / out.max()


def bold(drive, dt=1.0):
    """The drive convolved with the HRF, peak normalised to one."""
    t = np.arange(0, 32, dt); y = np.convolve(drive, hrf(t))[:len(drive)]; return y / y.max()
