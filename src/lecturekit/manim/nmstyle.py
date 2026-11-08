"""House style for the Manim clips: fonts, colours, and a data-to-scene frame helper (shared kit, from lecture 5 on).

The clips carry no titles (presentation policy); the slide supplies the claim. 1280 x 720, white background.
Colours come from the deck's _brand.yml when one is found above the working directory (or LECTUREKIT_BRAND), so a
clip re-rendered after a restyle follows the new palette; the values below are the paper preset's, as fall-back.
The fonts are the bundled TeX Gyre faces of the lecturekit extension, registered with Pango.
"""
import json, glob, os  # noqa: F401  (json and glob reach the clips through the kit's star import)
from pathlib import Path
from manim import *

HERE = Path(__file__).resolve().parent

# ------------------------------------------------------------------------------------------------ colours
_DEFAULT = {'ink': '#202B33', 'muted': '#566573', 'hairline': '#C8C3BA', 'paper': '#F3F2EE', 'slide': '#FFFFFF',
            'concept': '#175B8E', 'state': '#007F73', 'update': '#C45A00', 'context': '#7A5195', 'caveat': '#A33A32',
            'input': '#0072B2', 'example': '#956000', 'anchor': '#006C65', 'question': '#70508C',
            'gauss': '#175B8E', 'dog': '#B87400', 'css': '#B63564', 'dn': '#009999', 'future': '#7A5195'}


def _brand_colors():
    try:
        from ..theme import find_brand, load_brand
        p = find_brand()
        if p is None: return {}
        return dict(load_brand(p, mode=os.environ.get('LECTUREKIT_MODE', 'light')).colors)
    except Exception:
        return {}


COLORS = dict(_DEFAULT); COLORS.update(_brand_colors())
INK, MUTED, HAIR, PAPER = COLORS['ink'], COLORS['muted'], COLORS['hairline'], COLORS['paper']
SLIDE = COLORS['slide']
BLUE, TEAL, ORANGE, PURPLE, RED = COLORS['concept'], COLORS['state'], COLORS['update'], COLORS['context'], COLORS['caveat']
CAVEAT = RED   # the figures' name for the caveat red
INPUT, EXAMPLE, ANCHOR, QUESTION = COLORS['input'], COLORS['example'], COLORS['anchor'], COLORS['question']
# pRF model colours (Coimbra lecture 2 and the course's model lectures): every pair, the ink included, stays
# distinguishable under simulated deutan, protan and tritan vision. FUTURE (hypotheses, future work) is drawn dotted.
GAUSS, DOG, CSS, DN, FUTURE = COLORS['gauss'], COLORS['dog'], COLORS['css'], COLORS['dn'], COLORS['future']


def token(name):
    """A project token by name (token('gauss')), when a clip needs a colour that has no constant here."""
    return COLORS[name]


config.background_color = SLIDE
config.pixel_width, config.pixel_height, config.frame_rate = 1280, 720, 30
config.frame_width, config.frame_height = 16, 9


# ------------------------------------------------------------------------------------------------ fonts
def _fonts_dir():
    try:
        from ..project import extension_source
        return extension_source() / 'fonts'
    except Exception:
        return None


def register_fonts():
    """The deck fonts, TeX Gyre Pagella (Palatino) and Heros (Helvetica), from the extension's fonts/ directory."""
    import manimpango
    folder = _fonts_dir()
    if folder is None or not folder.is_dir():
        return 'TeX Gyre Pagella', 'TeX Gyre Heros'   # installed fonts, if the machine has them
    for path in sorted(folder.glob('texgyre*.otf')): manimpango.register_font(str(path))
    for path in sorted((folder / 'roboto').glob('*.ttf')): manimpango.register_font(str(path))
    return 'TeX Gyre Pagella', 'TeX Gyre Heros'


SERIF, SANS = register_fonts()
try:  # a brand that names other families (the dark preset's Roboto) wins
    from ..theme import find_brand, load_brand
    _p = find_brand()
    if _p is not None:
        _t = load_brand(_p, mode=os.environ.get('LECTUREKIT_MODE', 'light'))
        SERIF, SANS = _t.heading_font or SERIF, _t.base_font or SANS
except Exception:
    pass


def label(s, size=22, color=INK, serif=False, **kw):
    return Text(s, font=SERIF if serif else SANS, font_size=size, color=color, **kw)


class Frame:
    """Maps data coordinates (u, w) to scene coordinates inside a rectangle."""
    def __init__(self, left, bottom, width, height, u_range, w_range):
        self.left, self.bottom, self.width, self.height = left, bottom, width, height
        self.u0, self.u1 = u_range; self.w0, self.w1 = w_range

    def __call__(self, u, w):
        return np.array([self.left + (u - self.u0) / (self.u1 - self.u0) * self.width,
                         self.bottom + (w - self.w0) / (self.w1 - self.w0) * self.height, 0.0])

    def inv(self, p):
        """Scene point to data coordinates."""
        return (self.u0 + (p[0] - self.left) / self.width * (self.u1 - self.u0),
                self.w0 + (p[1] - self.bottom) / self.height * (self.w1 - self.w0))

    @property
    def scale(self):
        """Scene units per data unit, along u and w."""
        return self.width / (self.u1 - self.u0), self.height / (self.w1 - self.w0)

    @property
    def right(self): return self.left + self.width
    @property
    def top(self): return self.bottom + self.height

    def axes(self, u_ticks=(), w_ticks=(), u_label='', w_label='', tick_size=20, color=MUTED, w_axis_at=None, label_size=22):
        """Thin L-shaped axes with tick labels, in the muted colour."""
        g = VGroup()
        u_axis_w = self.w0 if w_axis_at is None else w_axis_at
        g.add(Line(self(self.u0, u_axis_w), self(self.u1, u_axis_w), stroke_width=1.6, color=color))
        g.add(Line(self(self.u0, self.w0), self(self.u0, self.w1), stroke_width=1.6, color=color))
        for u in u_ticks:
            g.add(label(f'{u:g}', tick_size, color).next_to(self(u, u_axis_w), DOWN, buff=0.12))
        for w in w_ticks:
            g.add(label(f'{w:g}', tick_size, color).next_to(self(self.u0, w), LEFT, buff=0.12))
        if u_label: g.add(label(u_label, label_size, color).move_to([self.left + self.width / 2, self.bottom - 0.68, 0]))
        if w_label: g.add(label(w_label, label_size, color).rotate(PI / 2).move_to([self.left - 0.8, self.bottom + self.height / 2, 0]))
        return g

    def polyline(self, points, color=TEAL, width=3, opacity=1.0):
        m = VMobject(stroke_color=color, stroke_width=width, stroke_opacity=opacity)
        m.set_points_as_corners([self(u, w) for u, w in points])
        return m


def normal_pdf(x, mu, sd=1.0):
    return np.exp(-0.5 * ((x - mu) / sd) ** 2) / (sd * np.sqrt(2 * np.pi))
