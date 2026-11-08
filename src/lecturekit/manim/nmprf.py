"""Population receptive field primitives for the course's Manim clips (shared kit; written for the Coimbra pRF workshop's
lecture 2, reused by the course's lectures 7 and 8).

    clip_size((1920, 1080))           # render size; NM_CLIP_SIZE (e.g. '1440x1080') overrides; frame 9 units high
    F = VisualField((x, y), radius)   # a window in degrees: F.pt(deg) -> scene, F.outline(), F.fixation()
    F.image(arr, GAUSS)               # a numpy map (rows = y from low to high) as an image in the window
    F.bar(pos, w, theta), F.disc(x, y, r), F.ring(x, y, r0, r1), F.half(x, y, r, side)   # light-grey apertures
    F.prf(x0, y0, s)                  # a pRF outline (ink), one sigma
    gauss2d, dog2d, gabor2d, grid     # numpy fields; colour_ramp(arr, colour) -> RGBA image
    prf_surface(f, ...)               # a 3-D surface over a square window, coloured by value (ThreeDScene)
    FeatureStack(maps)                # feature maps as an oblique stack of image planes (2-D scene)
    TracePanel(frame) .series(y, colour, t) .cursor(t, ys)   # traces that draw up to a time, with a cursor
    Dial(tracker, lo, hi, name)       # an arc gauge with a needle and a numeric readout
    Bars(frame) .bar(j, v0, v1) .outline(j, v0, v1)          # bar charts whose bars can be stacked

Conventions (lecture 2's palette): GAUSS, DOG, CSS, DN and FUTURE are the model colours in nmstyle; stimulus apertures
are light grey (APERTURE, ink at 20 per cent) and never blue, because blue is the Gaussian; pRF outlines are ink.
Positions are in degrees of visual angle; maps are numpy arrays with row 0 at the lowest y (plot with origin 'lower').
Everything is drawn fresh for Manim Community 0.22 (cairo renderer).
"""
import os
from .nmstyle import *


# ------------------------------------------------------------------ frame size
def clip_size(default=(1920, 1080)):
    """Set the render size: NM_CLIP_SIZE ('WxH', set by a deck's render_clips.py) or the default. The frame stays 9
    scene units high, so 16 x 9 at 16:9 and 12 x 9 at 4:3; returns (width, height) in scene units."""
    w, h = default
    if os.environ.get('NM_CLIP_SIZE'): w, h = (int(v) for v in os.environ['NM_CLIP_SIZE'].lower().split('x'))
    config.pixel_width, config.pixel_height = w, h
    config.frame_height = 9.0; config.frame_width = 9.0 * w / h
    return config.frame_width, config.frame_height


# ------------------------------------------------------------------ colours
def _rgb(colour):
    c = ManimColor(colour).to_hex()
    return np.array([int(c[i:i + 2], 16) for i in (1, 3, 5)]) / 255.0


def tint(colour, pct):
    """colour!pct as in TikZ: the colour mixed with white, opaque."""
    m = pct / 100 * _rgb(colour) + (1 - pct / 100)
    return '#' + ''.join(f'{int(round(v * 255)):02X}' for v in m)


APERTURE = tint(INK, 20)        # stimulus apertures: light grey, never blue


def baseline(lbl):
    """The baseline (y) of a Text label: the median bottom of its glyphs that have no descender. Text objects of different
    words have different boxes ('odd' is taller than 'even', 'grating' reaches lower), so align words by this."""
    chars = [c for c in lbl.text if not c.isspace()]
    bots = [g.get_bottom()[1] for c, g in zip(chars, lbl.submobjects) if c not in 'gjpqyQ,;()[]{}|/_°']
    return float(np.median(bots)) if bots else float(lbl.get_bottom()[1])


def on_baseline(lbl, y):
    """Shift a Text label so that its baseline sits at y."""
    return lbl.shift(UP * (y - baseline(lbl)))


def colour_ramp(arr, colour, vmax=None, neg=None, gamma=1.0, alpha=None, base=(1.0, 1.0, 1.0)):
    """RGBA image (uint8) of a map: white at 0, `colour` at +vmax; negative values towards `neg` (if given; otherwise
    clipped at white). `alpha` (array in [0, 1], same shape) makes pixels transparent, e.g. outside a circular field."""
    a = np.asarray(arr, float)
    vmax = float(np.max(np.abs(a))) if vmax is None else float(vmax)
    s = np.clip(a / (vmax or 1.0), -1, 1); base = np.asarray(base, float)
    pos = np.clip(s, 0, 1) ** gamma; out = base[None, None, :] * (1 - pos[..., None]) + _rgb(colour)[None, None, :] * pos[..., None]
    if neg is not None:
        ng = np.clip(-s, 0, 1) ** gamma; out = out * (1 - ng[..., None]) + _rgb(neg)[None, None, :] * ng[..., None]
    rgba = np.concatenate([out, np.ones(a.shape)[..., None] if alpha is None else np.asarray(alpha, float)[..., None]], axis=-1)
    return (np.clip(rgba, 0, 1) * 255).round().astype(np.uint8)


# ------------------------------------------------------------------ numpy fields (degrees)
def grid(extent=8.0, n=301, centre=(0.0, 0.0)):
    """X, Y over a square of half-width `extent` around `centre`; row 0 is the lowest y."""
    ax = np.linspace(-extent, extent, n)
    X, Y = np.meshgrid(ax + centre[0], ax + centre[1])
    return X, Y


def gauss2d(X, Y, x0, y0, s):
    """A Gaussian with peak 1."""
    return np.exp(-((X - x0) ** 2 + (Y - y0) ** 2) / (2 * s * s))


def gauss2d_density(X, Y, x0, y0, s):
    """A normalised Gaussian density (integrates to 1 over the plane)."""
    return gauss2d(X, Y, x0, y0, s) / (2 * np.pi * s * s)


def dog2d(X, Y, x0, y0, sc, ss, g):
    """Centre minus surround, each with peak 1: G(sc) - g G(ss)."""
    return gauss2d(X, Y, x0, y0, sc) - g * gauss2d(X, Y, x0, y0, ss)


def gabor2d(X, Y, x0, y0, s, theta_deg=0.0, freq=1.0, phase_deg=0.0, gamma=1.0, carrier=1.0):
    """A Gabor with peak 1: Gaussian envelope (sigma s, aspect gamma) times cos(2 pi f x' + phase), x' along the
    orientation theta (degrees, the direction across the stripes). carrier 0 gives the bare envelope, 1 the Gabor;
    values between blend the two (for a morph)."""
    th = np.radians(theta_deg); xr = (X - x0) * np.cos(th) + (Y - y0) * np.sin(th); yr = -(X - x0) * np.sin(th) + (Y - y0) * np.cos(th)
    env = np.exp(-(xr ** 2 + (gamma * yr) ** 2) / (2 * s * s))
    return env * ((1 - carrier) + carrier * np.cos(2 * np.pi * freq * xr + np.radians(phase_deg)))


# ------------------------------------------------------------------ the visual field
class VisualField:
    """A window onto the visual field: centre (scene units), radius (scene units) showing `deg` degrees from the
    centre `look` (degrees). Circular by default; square=True for a square window."""
    def __init__(self, center, radius, deg=8.0, look=(0.0, 0.0), square=False):
        self.c = np.array([center[0], center[1], 0.0]); self.r = radius; self.R = deg; self.k = radius / deg
        self.look = np.array(look, float); self.square = square

    def pt(self, x, y):
        return self.c + np.array([(x - self.look[0]) * self.k, (y - self.look[1]) * self.k, 0.0])

    def pts(self, xy):
        xy = np.asarray(xy, float)
        return self.c + np.column_stack([(xy[:, 0] - self.look[0]) * self.k, (xy[:, 1] - self.look[1]) * self.k, np.zeros(len(xy))])

    def outline(self, colour=HAIR, width=3.0, fill=WHITE, fill_opacity=1.0):
        m = Square(2 * self.r) if self.square else Circle(radius=self.r)
        return m.set_stroke(colour, width).set_fill(fill, fill_opacity).move_to(self.c)

    def fixation(self, size=0.13, colour=MUTED, width=2.6):
        f = self.pt(0, 0)
        return VGroup(Line(f + LEFT * size, f + RIGHT * size), Line(f + DOWN * size, f + UP * size)).set_stroke(colour, width)

    def clip_shape(self):
        return (Square(2 * self.r) if self.square else Circle(radius=self.r)).move_to(self.c)

    # maps
    def coords(self, n=301):
        """X, Y (degrees) for an image of this window, n x n, row 0 the lowest y."""
        return grid(self.R, n, tuple(self.look))

    def mask(self, X, Y, soft=0.0):
        if self.square: return np.ones_like(X)
        d = np.hypot(X - self.look[0], Y - self.look[1])
        return np.clip((self.R - d) / soft, 0, 1) if soft else (d <= self.R).astype(float)

    def image(self, arr, colour, vmax=None, neg=None, gamma=1.0, opacity=1.0, X=None, Y=None):
        """An n x n map (row 0 the lowest y, covering this window) as an image, white to `colour`; outside a circular
        window it is transparent."""
        n = np.asarray(arr).shape[0]
        if X is None: X, Y = self.coords(n)
        alpha = self.mask(X, Y, soft=self.R / n) * opacity
        im = ImageMobject(np.flipud(colour_ramp(arr, colour, vmax=vmax, neg=neg, gamma=gamma, alpha=alpha)))
        im.set_resampling_algorithm(RESAMPLING_ALGORITHMS['bilinear'])
        return im.stretch_to_fit_width(2 * self.r).stretch_to_fit_height(2 * self.r).move_to(self.c)

    # outlines and apertures (degrees)
    def prf(self, x0, y0, s, colour=INK, width=3.0, dash=False, n_sigma=1.0):
        m = Circle(radius=n_sigma * s * self.k).set_stroke(colour, width).move_to(self.pt(x0, y0))
        return DashedVMobject(m, num_dashes=40) if dash else m

    def poly(self, xy, colour=APERTURE, opacity=1.0):
        m = VMobject(fill_color=colour, fill_opacity=opacity, stroke_width=0)
        p = self.pts(xy); m.set_points_as_corners(np.vstack([p, p[:1]]))
        return m

    def empty(self):
        m = VMobject(fill_opacity=0, stroke_width=0); m.set_points_as_corners([self.c, self.c + RIGHT * 1e-3, self.c]); return m

    def bar(self, pos, w, theta=0.0, colour=APERTURE, opacity=1.0):
        """The strip |u - pos| <= w/2, u along the motion direction theta (degrees, counter-clockwise from rightward),
        clipped to the window (circle of radius R around `look`, or the square)."""
        R = self.R; th = np.radians(theta)
        if self.square:
            sq = Square(2 * self.r).move_to(self.c)
            strip = self.poly([(self.look[0] + (pos - w / 2) * np.cos(th) - 2 * R * np.sin(th), self.look[1] + (pos - w / 2) * np.sin(th) + 2 * R * np.cos(th)),
                               (self.look[0] + (pos + w / 2) * np.cos(th) - 2 * R * np.sin(th), self.look[1] + (pos + w / 2) * np.sin(th) + 2 * R * np.cos(th)),
                               (self.look[0] + (pos + w / 2) * np.cos(th) + 2 * R * np.sin(th), self.look[1] + (pos + w / 2) * np.sin(th) - 2 * R * np.cos(th)),
                               (self.look[0] + (pos - w / 2) * np.cos(th) + 2 * R * np.sin(th), self.look[1] + (pos - w / 2) * np.sin(th) - 2 * R * np.cos(th))], colour, opacity)
            out = Intersection(strip, sq, fill_color=colour, fill_opacity=opacity, stroke_width=0)
            return out if len(out.points) else self.empty()
        a, b = max(pos - w / 2, -R), min(pos + w / 2, R)
        if b - a <= 1e-4: return self.empty()
        ha, hb = np.sqrt(max(R * R - a * a, 0)), np.sqrt(max(R * R - b * b, 0))
        ta, tb = np.arctan2(ha, a), np.arctan2(hb, b)
        top = np.column_stack([R * np.cos(np.linspace(ta, tb, 48)), R * np.sin(np.linspace(ta, tb, 48))])
        bot = np.column_stack([R * np.cos(np.linspace(tb, ta, 48)), -R * np.sin(np.linspace(tb, ta, 48))])
        uv = np.vstack([[[a, -ha]], top, bot])
        x = uv[:, 0] * np.cos(th) - uv[:, 1] * np.sin(th) + self.look[0]; y = uv[:, 0] * np.sin(th) + uv[:, 1] * np.cos(th) + self.look[1]
        return self.poly(np.column_stack([x, y]), colour, opacity)

    def disc(self, x, y, r, colour=APERTURE, opacity=1.0):
        return Circle(radius=max(r, 1e-3) * self.k, stroke_width=0, fill_color=colour, fill_opacity=opacity).move_to(self.pt(x, y))

    def clipped(self, m):
        """A filled shape (disc, ring, patch) cut to the window, with the shape's fill; empty if nothing is left."""
        out = Intersection(m, self.clip_shape(), fill_color=m.get_fill_color(), fill_opacity=m.get_fill_opacity(), stroke_width=0)
        return out if len(out.points) else self.empty()

    def ring(self, x, y, r0, r1, colour=APERTURE, opacity=1.0):
        if r1 <= r0 + 1e-3: return self.empty()
        if r0 <= 1e-3: return self.disc(x, y, r1, colour, opacity)
        return Annulus(inner_radius=r0 * self.k, outer_radius=r1 * self.k, color=colour, fill_opacity=opacity, stroke_width=0).move_to(self.pt(x, y))

    def half(self, x, y, r, side, colour=APERTURE, opacity=1.0):
        """Half of a disc: side 'L', 'R', 'lower', 'upper' or 'both'."""
        if side == 'both': return self.disc(x, y, r, colour, opacity)
        a0, a1 = {'L': (90, 270), 'R': (-90, 90), 'lower': (180, 360), 'upper': (0, 180)}[side]
        t = np.radians(np.linspace(a0, a1, 91))
        return self.poly(np.vstack([[x, y], np.column_stack([x + r * np.cos(t), y + r * np.sin(t)])]), colour, opacity)

    def square_patch(self, x, y, size, colour=APERTURE, opacity=1.0):
        return Square(side_length=size * self.k, stroke_width=0, fill_color=colour, fill_opacity=opacity).move_to(self.pt(x, y))

    def scale_bar(self, deg=2.0, colour=MUTED, size=26, where=DOWN):
        """A short scale bar of `deg` degrees with its label, under (or beside) the window."""
        p = self.c + where * (self.r + 0.35)
        line = Line(p + LEFT * deg * self.k / 2, p + RIGHT * deg * self.k / 2).set_stroke(colour, 3)
        return VGroup(line, label(f'{deg:g}°', size, colour).next_to(line, DOWN, buff=0.1))


# ------------------------------------------------------------------ 3-D surfaces (ThreeDScene)
class HeightSurface(VGroup):
    """A surface z = height * Z over a square grid (half_width degrees, `scale` units per degree), for a ThreeDScene,
    made of quads that are reshaped and recoloured in place: set_heights(Z) is cheap enough to animate a parameter
    frame by frame (an always_redraw Surface is rebuilt and recoloured per frame and is about ten times slower).
    colorscale: [(colour, z), ...] in data units, interpolated per face on the face's mean height."""
    def __init__(self, Z, half_width=4.0, scale=1.0, height=1.0, center=ORIGIN, colorscale=((WHITE, 0.0), (INK, 1.0)),
                 opacity=1.0, stroke_colour=WHITE, stroke_width=0.35, stroke_opacity=0.5, shade=True):
        super().__init__()
        Z = np.asarray(Z, float); n = Z.shape[0]
        ax = np.linspace(-half_width, half_width, n) * scale
        self.XY = np.stack(np.meshgrid(ax, ax), axis=-1)                     # [row = y, col = x, (x, y)]
        self._zh, self._c, self._op = height, np.array(center, float), opacity    # (not .height/.center: Mobject's own)
        cs = sorted(colorscale, key=lambda c: c[1]); self.cz = np.array([c[1] for c in cs]); self.crgb = np.array([_rgb(c[0]) for c in cs])
        for i in range(n - 2, -1, -1):                                      # back rows (high y) first
            for j in range(n - 1):
                f = Polygon(*[ORIGIN, RIGHT, UP, LEFT]).set_stroke(stroke_colour, stroke_width, opacity=stroke_opacity)
                if shade: f.set_shade_in_3d(True)
                f.ij = (i, j); self.add(f)
        self.set_heights(Z)

    def set_heights(self, Z):
        Z = np.asarray(Z, float)
        P = np.concatenate([self.XY, (self._zh * Z)[..., None]], axis=-1) + self._c
        zf = (Z[:-1, :-1] + Z[1:, :-1] + Z[:-1, 1:] + Z[1:, 1:]) / 4
        rgb = np.stack([np.interp(zf, self.cz, self.crgb[:, k]) for k in range(3)], axis=-1)
        for f in self.submobjects:
            i, j = f.ij
            f.set_points_as_corners([P[i, j], P[i, j + 1], P[i + 1, j + 1], P[i + 1, j], P[i, j]])
            f.set_fill(rgb_to_color(rgb[i, j]), self._op)
        return self


def prf_surface(f, half_width=4.0, scale=1.0, height=1.0, resolution=36, colorscale=None, opacity=1.0, center=ORIGIN,
                stroke=0.0):
    """A surface z = height * f(x, y) over [-half_width, half_width]^2 (degrees, drawn `scale` units per degree),
    coloured by z with `colorscale`, a list of (colour, z) pairs (for example [(DOG, -0.3), (WHITE, 0), (GAUSS, 1)])."""
    s = Surface(lambda u, v: np.array([u * scale, v * scale, height * f(u, v)]) + center,
                u_range=[-half_width, half_width], v_range=[-half_width, half_width], resolution=(resolution, resolution),
                fill_opacity=opacity, stroke_width=stroke, checkerboard_colors=False, should_make_jagged=False)
    if colorscale:
        ax = ThreeDAxes(x_range=[-1, 1], y_range=[-1, 1], z_range=[-1, 1], x_length=2, y_length=2, z_length=2).move_to(ORIGIN)
        s.set_fill_by_value(axes=ax, colorscale=[(c, (z * height + center[2]) / 1.0) for c, z in colorscale], axis=2)
    return s


# ------------------------------------------------------------------ a stack of feature maps
class FeatureStack(Group):
    """Feature maps as image planes in an oblique view: each map is drawn as a parallelogram (sheared and flattened
    square), the planes offset along the stack's depth. maps: list of RGBA arrays (row 0 at the top) or (array, colour)
    pairs for colour_ramp. Use plane_point(i, u, v) for a point on plane i (u, v in [-1, 1])."""
    def __init__(self, maps, size=2.6, step=(0.42, 0.30), shear=0.55, squash=0.55, center=ORIGIN, frame_colour=HAIR):
        super().__init__()
        self.size, self.step, self.shear, self.squash = size, np.array([step[0], step[1], 0.0]), shear, squash
        self.M = np.array([[1.0, shear], [0.0, squash]])
        c = np.zeros(3); c[:len(center)] = center                          # (x, y) or (x, y, z)
        self.origin = c - self.step * (len(maps) - 1) / 2
        self.planes = Group(); self.frames = VGroup()
        for i, m in enumerate(maps):
            rgba = colour_ramp(*m) if isinstance(m, tuple) else m
            im = ImageMobject(rgba).set_resampling_algorithm(RESAMPLING_ALGORITHMS['bilinear'])
            im.stretch_to_fit_width(size).stretch_to_fit_height(size).move_to(ORIGIN).apply_matrix(self.M).shift(self.centre(i))
            self.planes.add(im)
            self.frames.add(Polygon(*[self.plane_point(i, u, v) for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1))]).set_stroke(frame_colour, 2.0).set_fill(opacity=0))
        # back planes first, so that the front plane is drawn last
        for i in reversed(range(len(maps))): self.add(self.planes[i], self.frames[i])

    def centre(self, i):
        return self.origin + self.step * i

    def plane_point(self, i, u, v):
        """Point on plane i at (u, v) in [-1, 1]^2 (u right, v up, in the map's own coordinates)."""
        x, y = u * self.size / 2, v * self.size / 2
        return self.centre(i) + np.array([x + self.shear * y, self.squash * y, 0.0])

    def plane_outline(self, i, colour=INK, width=2.5):
        return Polygon(*[self.plane_point(i, u, v) for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1))]).set_stroke(colour, width).set_fill(opacity=0)

    def ellipse_on(self, i, u0, v0, r, colour=GAUSS, width=3.0, fill_opacity=0.0, n=64):
        """A circle of radius r (in map units, map half-width 1) drawn onto plane i: an ellipse in the oblique view."""
        t = np.linspace(0, 2 * np.pi, n, endpoint=False)
        m = Polygon(*[self.plane_point(i, u0 + r * np.cos(a), v0 + r * np.sin(a)) for a in t])
        return m.set_stroke(colour, width).set_fill(colour, fill_opacity)

    def map_on(self, i, rgba):
        """An image drawn onto plane i (same shear), e.g. a translucent pooling field."""
        im = ImageMobject(rgba).set_resampling_algorithm(RESAMPLING_ALGORITHMS['bilinear'])
        return im.stretch_to_fit_width(self.size).stretch_to_fit_height(self.size).move_to(ORIGIN).apply_matrix(self.M).shift(self.centre(i))


# ------------------------------------------------------------------ traces with a cursor
class TracePanel:
    """Time courses in a Frame that draw up to the time held by a ValueTracker, with a cursor.

        P = TracePanel(Frame(...), t)               # t: ValueTracker of the time (data units of the u axis)
        P.series(ts, ys, colour)                    # an always_redraw polyline up to t
        P.cursor([(ts, ys, colour), ...])           # a vertical line at t with a dot on each series
    """
    def __init__(self, frame, t):
        self.F, self.t = frame, t

    @staticmethod
    def upto(ts, ys, t):
        ts = np.asarray(ts, float); ys = np.asarray(ys, float)
        k = int(np.searchsorted(ts, t, side='right'))
        pts = list(zip(ts[:k], ys[:k]))
        if 0 < k < len(ts) and t > ts[k - 1]: pts.append((t, float(np.interp(t, ts, ys))))
        if not pts: pts = [(ts[0], ys[0])]
        return pts if len(pts) > 1 else pts + pts

    def series(self, ts, ys, colour=INK, width=4.0, opacity=1.0):
        return always_redraw(lambda: self.F.polyline(self.upto(ts, ys, self.t.get_value()), colour, width, opacity))

    def cursor(self, series=(), colour=MUTED, width=2.0, dot=0.075, w_range=None):
        lo, hi = w_range or (self.F.w0, self.F.w1)
        def make():
            t = self.t.get_value()
            g = VGroup(Line(self.F(t, lo), self.F(t, hi), stroke_color=colour, stroke_width=width, stroke_opacity=0.5))
            for ts, ys, c in series: g.add(Dot(self.F(t, float(np.interp(t, ts, ys))), radius=dot, color=c))
            return g
        return always_redraw(make)


# ------------------------------------------------------------------ a dial
class Dial(VGroup):
    """An arc gauge from lo to hi with a needle and a readout 'name = value', following a ValueTracker.

        n = ValueTracker(1.0); d = Dial(n, 0.0, 1.0, 'n', colour=CSS).move_to(...)
        self.play(n.animate.set_value(0.25))
    readout_at: the readout's centre relative to the hub (default inside the arc, radius * 0.45 below the hub; for a small
    dial with a long readout pass e.g. DOWN * (radius * 0.4 + 0.3) to set it below the arc).
    """
    def __init__(self, tracker, lo, hi, name, colour=INK, radius=1.0, fmt='{:.2f}', ticks=None, size=34, serif_name=True,
                 arc=(200, -20), width=6, readout_at=None):
        super().__init__()
        self.tracker, self.lo, self.hi, self.a0, self.a1, self.radius = tracker, lo, hi, np.radians(arc[0]), np.radians(arc[1]), radius
        self.hub = Dot(ORIGIN, radius=0.07, color=INK); self._centre = self.hub          # before the always_redraw parts
        self.add(Arc(radius=radius, start_angle=self.a0, angle=self.a1 - self.a0).set_stroke(HAIR, width))
        for v in (ticks if ticks is not None else (lo, hi)):
            a = self.angle(v); p = np.array([np.cos(a), np.sin(a), 0])
            self.add(Line(p * radius * 0.86, p * radius * 1.0).set_stroke(MUTED, 3))
            self.add(label(f'{v:g}', 22, MUTED).move_to(p * radius * 1.24))
        self.fill_arc = always_redraw(lambda: Arc(radius=radius, start_angle=self.a0, angle=min(self.angle(self.tracker.get_value()) - self.a0, -1e-3), arc_center=self.get_center_point()).set_stroke(colour, width))
        self.needle = always_redraw(lambda: Line(self.get_center_point(), self.get_center_point() + radius * 0.82 * np.array([np.cos(self.angle(self.tracker.get_value())), np.sin(self.angle(self.tracker.get_value())), 0])).set_stroke(INK, 4))
        prefix = f'{name} = ' if name else ''
        off = DOWN * radius * 0.45 if readout_at is None else np.asarray(readout_at, float)   # readout centre from the hub
        self.readout = always_redraw(lambda: label(prefix + fmt.format(self.tracker.get_value()), size, colour, serif=serif_name and bool(name)).move_to(self.get_center_point() + off))
        self.add(self.hub)

    def get_center_point(self):
        return self._centre.get_center()

    def angle(self, v):
        s = (np.clip(v, min(self.lo, self.hi), max(self.lo, self.hi)) - self.lo) / (self.hi - self.lo)
        return self.a0 + s * (self.a1 - self.a0)

    def live(self):
        """The moving parts, to be added to the scene with the dial: Group(fill arc, needle, readout). They are brought
        to the dial's current place here, so that a dial moved after it was made shows right in the first frame."""
        g = VGroup(self.fill_arc, self.needle, self.readout); g.update()
        return g


# ------------------------------------------------------------------ bar charts that stack
class Bars:
    """Bars in a Frame (u: slot index, w: value). Slot j spans u in [j + gap/2, j + 1 - gap/2].

        B = Bars(Frame(...), gap=0.4)
        B.bar(j, v0, v1, colour)                    # a filled bar from v0 to v1 (stack by passing v0 = the top below)
        B.outline(j, v0, v1, colour, dashed=True)   # an outline, for a prediction
        B.under(j, 'text', ...)                     # a label under slot j
    """
    def __init__(self, frame, gap=0.4):
        self.F, self.gap = frame, gap

    def rect(self, j, v0, v1):
        a, b = self.F(j + self.gap / 2, v0), self.F(j + 1 - self.gap / 2, v1)
        return Rectangle(width=abs(b[0] - a[0]), height=max(abs(b[1] - a[1]), 1e-4)).move_to((a + b) / 2)

    def bar(self, j, v0, v1, colour, opacity=1.0, edge=WHITE, edge_width=2.0):
        return self.rect(j, v0, v1).set_fill(colour, opacity).set_stroke(edge, edge_width)

    def outline(self, j, v0, v1, colour=INK, width=4.0, dashed=True):
        r = self.rect(j, v0, v1).set_fill(opacity=0).set_stroke(colour, width)
        return DashedVMobject(r, num_dashes=36, dashed_ratio=0.55) if dashed else r

    def under(self, j, *lines, size=26, colour=INK):
        return VGroup(*[label(s, size, colour) for s in lines]).arrange(DOWN, buff=0.06).next_to(self.F(j + 0.5, self.F.w0), DOWN, buff=0.16)
