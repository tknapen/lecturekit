"""Flows for the course clips: a two-dimensional dynamical system drawn as stream lines or arrows inside a Frame, with
trajectories integrated from chosen starts and fixed points marked (filled when stable, open when not).

Storyboard source: 3Blue1Brown's differential-equations series (github.com/3b1b/videos, _2019/diffyq/part1,
phase_space.py: IntroduceVectorField, TakeManyTinySteps), redrawn for Manim Community in the course style.

    fr = Frame(-6, -3, 8, 6, (-2, 2), (-2, 2))
    f = lambda u, w: (w, -u - 0.3 * w)                        # du/dt, dw/dt in data units
    self.add(arrows(fr, f)); path = trajectory(fr, f, (1.5, 0), T=20)
"""
from .nmstyle import *


def _scene_func(fr, f, gain=1.0):
    sx, sy = fr.scale
    def func(p):
        u, w = fr.inv(p); du, dw = f(u, w)
        return np.array([du * sx * gain, dw * sy * gain, 0.0])
    return func


def arrows(fr, f, n=(17, 13), colour=HAIR, length=0.32, width=2.0):
    """A grid of short arrows of equal length showing the direction of flow; opacity follows the speed."""
    g = VGroup(); sx, sy = fr.scale
    us = np.linspace(fr.u0, fr.u1, n[0] + 2)[1:-1]; ws = np.linspace(fr.w0, fr.w1, n[1] + 2)[1:-1]
    speeds = np.array([[np.hypot(*f(u, w)) for u in us] for w in ws]); smax = max(float(speeds.max()), 1e-9)
    for iw, w in enumerate(ws):
        for iu, u in enumerate(us):
            du, dw = f(u, w); v = np.array([du * sx, dw * sy, 0.0]); nv = np.linalg.norm(v)
            if nv < 1e-9: continue
            p = fr(u, w); d = v / nv * length
            g.add(Arrow(p - d / 2, p + d / 2, buff=0, stroke_color=colour, stroke_width=width, stroke_opacity=0.35 + 0.65 * speeds[iw, iu] / smax,
                        max_tip_length_to_length_ratio=0.35, max_stroke_width_to_length_ratio=10))
    return g


def streams(fr, f, colour=HAIR, dt=0.05, virtual_time=3, stroke_width=1.6, delta=0.5):
    """Manim's StreamLines over the frame (call .start_animation(warm_up=False) for moving flow)."""
    return StreamLines(_scene_func(fr, f), x_range=[fr.left, fr.right, delta], y_range=[fr.bottom, fr.top, delta],
                       stroke_width=stroke_width, colors=[colour], dt=dt, virtual_time=virtual_time, padding=0)


def integrate(f, start, T, dt=0.01):
    """Fourth-order Runge-Kutta in data coordinates; returns an (n, 2) array."""
    x = np.array(start, float); out = [x.copy()]
    F = lambda z: np.array(f(z[0], z[1]), float)
    for _ in range(int(T / dt)):
        k1 = F(x); k2 = F(x + dt / 2 * k1); k3 = F(x + dt / 2 * k2); k4 = F(x + dt * k3)
        x = x + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4); out.append(x.copy())
    return np.array(out)


def trajectory(fr, f, start, T, dt=0.01, colour=BLUE, width=3.5, clip=True):
    pts = integrate(f, start, T, dt)
    if clip:
        keep = (pts[:, 0] >= fr.u0) & (pts[:, 0] <= fr.u1) & (pts[:, 1] >= fr.w0) & (pts[:, 1] <= fr.w1)
        if not keep.all(): pts = pts[:np.argmin(keep)] if not keep[0] else pts[:int(np.argmax(~keep))]
    return fr.polyline([tuple(p) for p in pts], colour, width)


def fixed_point(fr, u, w, stable=True, colour=INK, radius=0.11):
    p = fr(u, w)
    return Dot(p, radius=radius, color=colour) if stable else Circle(radius=radius, stroke_color=colour, stroke_width=3, fill_color=SLIDE, fill_opacity=1).move_to(p)
