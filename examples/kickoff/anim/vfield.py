"""Visual-field drawing for the lecture's clips, in step with make_assets.py (the static TikZ figures of the PDF).

A VField maps degrees of visual angle to scene units: a circular 16-degree field (radius 8 degrees) centred on
fixation. Its shapes are those of make_assets.py: wedge, ring, straight bar (a strip clipped to the field), the
radially log-warped bar (warped_bar through warp_r, with a warp strength for morphing), square patches and half discs.
Colours follow the figures: an aperture is the course blue at 45 per cent on white (an opaque tint, as TikZ's
nmConcept!45), the illustrative population a teal disc with fill opacity 0.22 at x 2.5, y 1.5 degrees, sigma 1, the
field a hairline circle on white with a fixation cross. hrf, bar_drive, bold and warp_r are imported from make_assets.py
itself (as MA), so the clips and the figures share one implementation of the forward model and the warp.

Frame size: the kit fixes 1280 x 720 (16 x 9 scene units) when it is imported; render_clips.py sets NM_CLIP_SIZE (for
example 960x720) for a clip with another size, and this module applies it, keeping 80 pixels per unit and a frame 9
units high. FW and FH are the frame's width and height in scene units, for the clips' layouts.
"""
import os, sys
from kit import *
from manim.mobject.geometry.boolean_ops import Intersection

_saved = list(sys.path), sys.dont_write_bytecode
sys.path.insert(0, str(HERE.parent)); sys.dont_write_bytecode = True    # no __pycache__ beside make_assets.py
import bar_model as MA        # the numpy model of the bar run (from lecture 1 of the Coimbra workshop)
sys.path[:], sys.dont_write_bytecode = _saved

if os.environ.get('NM_CLIP_SIZE'):
    _w, _h = (int(v) for v in os.environ['NM_CLIP_SIZE'].lower().split('x'))
    config.pixel_width, config.pixel_height = _w, _h
    config.frame_height = 9.0; config.frame_width = 9.0 * _w / _h
FW, FH = config.frame_width, config.frame_height

PRF = dict(px=2.5, py=1.5, s=1.0)     # the illustrative population of every figure (degrees)


def tint(colour, pct):
    """TikZ's colour!pct as the deck's figures draw it: the colour mixed with the slide colour (white on paper), as an
    opaque hex colour; the dark preset tints towards its dark slide."""
    c = np.array([int(colour[i:i + 2], 16) for i in (1, 3, 5)]) / 255.0
    bg = np.array([int(SLIDE[i:i + 2], 16) for i in (1, 3, 5)]) / 255.0
    m = pct / 100 * c + (1 - pct / 100) * bg
    return '#' + ''.join(f'{int(round(v * 255)):02X}' for v in m)


APER = tint(BLUE, 45)


def on_baseline(t, x, y):
    """Centre a label on x with its baseline at y, so that a row of labels lines up whatever their descenders (the
    first glyph must have none)."""
    t.move_to([x, y, 0]); return t.shift(UP * (y - t[0].get_bottom()[1]))


class VField:
    """A circular visual field: centre and radius in scene units, positions in degrees (radius deg)."""
    def __init__(self, center, radius, deg=8.0):
        self.c = np.array([center[0], center[1], 0.0]); self.r = radius; self.R = deg; self.k = radius / deg

    def pt(self, x, y):
        return self.c + np.array([x * self.k, y * self.k, 0.0])

    def pts(self, xy):
        xy = np.asarray(xy, dtype=float)
        return self.c + np.column_stack([xy[:, 0] * self.k, xy[:, 1] * self.k, np.zeros(len(xy))])

    def disc(self, width=2.4):
        return Circle(radius=self.r, stroke_color=HAIR, stroke_width=width, fill_color=SLIDE, fill_opacity=1).move_to(self.c)

    def cross(self, size=0.11, width=2.0):
        return VGroup(Line(self.c + LEFT * size, self.c + RIGHT * size), Line(self.c + DOWN * size, self.c + UP * size)).set_stroke(MUTED, width)

    def prf(self, px=2.5, py=1.5, s=1.0, opacity=0.22, width=2.6):
        return Circle(radius=s * self.k, stroke_color=TEAL, stroke_width=width, fill_color=TEAL, fill_opacity=opacity).move_to(self.pt(px, py))

    def poly(self, xy, colour=APER, opacity=1.0):
        m = VMobject(fill_color=colour, fill_opacity=opacity, stroke_width=0)
        p = self.pts(xy); m.set_points_as_corners(np.vstack([p, p[:1]]))
        return m

    def empty(self):
        """An invisible stand-in for an aperture that is outside the field."""
        m = VMobject(fill_opacity=0, stroke_width=0); m.set_points_as_corners([self.c, self.c + RIGHT * 1e-3, self.c]); return m

    def wedge(self, a0, a1, colour=APER, opacity=1.0):
        """A wedge from polar angle a0 to a1 (degrees, counter-clockwise from the right horizontal meridian)."""
        t = np.radians(np.linspace(a0, a1, max(4, int(abs(a1 - a0)) + 1)))
        return self.poly(np.vstack([[0, 0], np.column_stack([self.R * np.cos(t), self.R * np.sin(t)])]), colour, opacity)

    def ring(self, r0, r1, colour=APER, opacity=1.0):
        """A ring between radii r0 and r1 (degrees), clipped to the field."""
        r1 = min(r1, self.R)
        if r1 <= max(r0, 0) + 1e-3: return self.empty()
        if r0 <= 1e-3: return Circle(radius=r1 * self.k, stroke_width=0, fill_color=colour, fill_opacity=opacity).move_to(self.c)
        return Annulus(inner_radius=r0 * self.k, outer_radius=r1 * self.k, color=colour, fill_opacity=opacity, stroke_width=0).move_to(self.c)

    def bar(self, pos, w, theta=0.0, colour=APER, opacity=1.0):
        """make_assets.bar: the strip |u - pos| <= w/2, u along the direction theta (degrees), clipped to the field.
        theta 0 is a vertical bar at x = pos; theta 90 a horizontal bar at y = pos."""
        R = self.R; a, b = max(pos - w / 2, -R), min(pos + w / 2, R)
        if b - a <= 1e-4: return self.empty()
        ha, hb = np.sqrt(max(R * R - a * a, 0)), np.sqrt(max(R * R - b * b, 0))
        ta, tb = np.arctan2(ha, a), np.arctan2(hb, b)
        top = np.column_stack([R * np.cos(np.linspace(ta, tb, 48)), R * np.sin(np.linspace(ta, tb, 48))])
        bot = np.column_stack([R * np.cos(np.linspace(tb, ta, 48)), -R * np.sin(np.linspace(tb, ta, 48))])
        uv = np.vstack([[[a, -ha]], top, bot])
        th = np.radians(theta); x = uv[:, 0] * np.cos(th) - uv[:, 1] * np.sin(th); y = uv[:, 0] * np.sin(th) + uv[:, 1] * np.cos(th)
        return self.poly(np.column_stack([x, y]), colour, opacity)

    def warp(self, rho, lam=1.0, g=3.0):
        """Design radius to visual radius: (1 - lam) rho + lam warp_r(rho); lam 1 is make_assets.warp_r itself."""
        return (1 - lam) * rho + lam * MA.warp_r(rho, self.R, g)

    def warped_bar(self, pos, w, lam=1.0, g=3.0, colour=APER, opacity=1.0):
        """make_assets.warped_bar in degrees: a straight bar in design space (centre pos, width w) mapped through the
        radial warp of strength lam (0 leaves it straight), then clipped to the field."""
        R = self.R
        if abs(pos) - w / 2 >= R: return self.empty()
        ys = np.linspace(-1.6 * R, 1.6 * R, 241)
        def edge(c):
            rho = np.hypot(c, ys); phi = np.arctan2(ys, c); rv = self.warp(np.minimum(rho, 1.6 * R), lam, g)
            return np.column_stack([rv * np.cos(phi), rv * np.sin(phi)])
        shape = self.poly(np.vstack([edge(pos - w / 2), edge(pos + w / 2)[::-1]]), colour, opacity)
        out = Intersection(shape, Circle(radius=self.r).move_to(self.c), fill_color=colour, fill_opacity=opacity, stroke_width=0)
        return out if len(out.points) else self.empty()

    def square(self, x, y, size, colour=APER, opacity=1.0):
        """A square patch centred at (x, y) with side size (degrees)."""
        return Square(side_length=size * self.k, stroke_width=0, fill_color=colour, fill_opacity=opacity).move_to(self.pt(x, y))

    def half(self, ax, ay, ar, side, colour=APER, opacity=1.0):
        """make_assets.half: half of a disc aperture (centre ax, ay, radius ar, degrees); side 'L', 'R', 'lower', 'upper'
        or 'both'."""
        if side == 'both': return Circle(radius=ar * self.k, stroke_width=0, fill_color=colour, fill_opacity=opacity).move_to(self.pt(ax, ay))
        a0, a1 = {'L': (90, 270), 'R': (-90, 90), 'lower': (180, 360), 'upper': (0, 180)}[side]
        t = np.radians(np.linspace(a0, a1, 91))
        return self.poly(np.vstack([[ax, ay], np.column_stack([ax + ar * np.cos(t), ay + ar * np.sin(t)])]), colour, opacity)
