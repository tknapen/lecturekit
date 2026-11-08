"""The TikZ kit: what every deck's make_assets.py imports.

Shared helpers for drawing figures from numbers (from lecture 5 of the course on; the Coimbra workshop decks and the
kickoff example use them): the TikZ colour names, a data-to-page Panel with axes, a column of notes that does not
overlap (stack), curves clipped to a range, boxes, contour lines, and a writer for assets/figures/*.tex.

    from lecturekit.tikz import *
    write = writer(HERE / 'assets' / 'figures')
    L = []; P = Panel(0.5, 0.5, 12, 4, (0, 60), (0, 1)); L.append(P.path(points, f'{BLUE},line width=1pt'))
    write('name', L)                       # assets/figures/name.tex, placed with \\nmfigureh{4cm}{assets/figures/name.tex}

Colours are TikZ colour names (nmInk, nmConcept, nmGauss, ...), never values: the theme owns them, through
_brand.yml, in both outputs. The slide surface is SLIDE (nmSlide), never 'white'; a fill that fades into the slide
is tint(col, pct), never col!pct, which TikZ mixes with white. hex(name) gives the value of a token for a script
that must write a raster image.
Figures are drawn at the size they should appear (12 to 13 cm wide for a full-width slide, about 4.2 cm high for two
bullets); \\nmfigureh never scales up.
"""

from __future__ import annotations

import json
import math
import re as _re
from pathlib import Path

import numpy as np

# ------------------------------------------------------------------------------------------------ colour names
INK, MUTED, HAIR, PAPER, SLIDE = 'nmInk', 'nmMuted', 'nmHairline', 'nmPaper', 'nmSlide'
BLUE, TEAL, ORANGE, PURPLE, CAVEAT = 'nmConcept', 'nmState', 'nmUpdate', 'nmContext', 'nmCaveat'
CONCEPT, EXAMPLE, ANCHOR, QUESTION, INPUT = 'nmConcept', 'nmExample', 'nmAnchor', 'nmQuestion', 'nmInput'
GAUSS, DOG, CSS, DN, FUTURE = 'nmGauss', 'nmDoG', 'nmCSS', 'nmDN', 'nmFuture'   # the four pRF models (workshop lecture 2; course lectures 7, 8)
STYLE = r'[x=1cm,y=1cm,every node/.style={font=\sffamily\footnotesize,text=nmInk,inner sep=1.5pt}]'
SMALL = r'font=\sffamily\scriptsize'; TINY = r'font=\sffamily\tiny'; HEAD = r'font=\sffamily\footnotesize\bfseries'

PX_PER_CM = 88.0        # the live deck's max-height for a figure of 1 cm (8.8 px per mm)
PT_PER_CM = 28.4528

#: heights that leave room for text beside or above the figure (docs/LAYOUT.md)
FIGURE_HEIGHTS = {'full': '5.6cm', 'one_bullet': '4.8cm', 'two_bullets': '4.2cm', 'column': '4.4cm'}


def tint(col: str, pct) -> str:
    """A tint of a token towards the slide surface: tint(BLUE, 6) is 'nmConcept!6!nmSlide'.

    TikZ's own `col!6` mixes with white, which is wrong on any surface that is not white; a fill or a stroke that
    should fade into the slide mixes with the slide's token, so a restyle carries it along."""
    return f'{col}!{pct}!{SLIDE}'


def color(name: str) -> str:
    """The TikZ colour name of a brand token: color('concept') == 'nmConcept'."""
    from .theme import camel
    return f'nm{camel(name)}'


def hex(name: str) -> str:  # noqa: A001
    """The value of a brand token ('#175B8E' for 'concept' in the paper preset), for scripts that write rasters."""
    from . import tokens as _t
    key = name
    if key.startswith('nm'):
        key = _re.sub(r'(?<!^)(?=[A-Z])', '-', key[2:]).lower()
    return _t.tokens().colors[key]


# ------------------------------------------------------------------------------------------------ panels
class Panel:
    """Maps data coordinates (u, v) to page coordinates inside a rectangle at (x0, y0) of size w by h."""
    def __init__(self, x0, y0, w, h, u, v):
        self.x0, self.y0, self.w, self.h = x0, y0, w, h; self.u = u; self.v = v
    def __call__(self, a, b):
        return (self.x0 + (a - self.u[0]) / (self.u[1] - self.u[0]) * self.w, self.y0 + (b - self.v[0]) / (self.v[1] - self.v[0]) * self.h)
    def pt(self, a, b): x, y = self(a, b); return f'({x:.3f},{y:.3f})'
    def path(self, pts, style, close=False):
        return f'\\draw[{style}] ' + ' -- '.join(self.pt(a, b) for a, b in pts) + (' -- cycle;' if close else ';')
    def fill(self, pts, style): return f'\\fill[{style}] ' + ' -- '.join(self.pt(a, b) for a, b in pts) + ' -- cycle;'
    def hline(self, b, style, u0=None, u1=None):
        return f'\\draw[{style}] {self.pt(self.u[0] if u0 is None else u0, b)} -- {self.pt(self.u[1] if u1 is None else u1, b)};'
    def vline(self, a, style, v0=None, v1=None):
        return f'\\draw[{style}] {self.pt(a, self.v[0] if v0 is None else v0)} -- {self.pt(a, self.v[1] if v1 is None else v1)};'
    def axes(self, u_ticks=(), v_ticks=(), u_label='', v_label='', v_axis_at=None, u_axis_at=None, tick_fmt='{:g}', v_label_offset=0.75, u_tick_labels=None, v_tick_labels=None):
        va = self.v[0] if u_axis_at is None else u_axis_at; ua = self.u[0] if v_axis_at is None else v_axis_at
        out = [f'\\draw[{MUTED},line width=0.5pt] {self.pt(self.u[0], va)} -- {self.pt(self.u[1], va)};',
               f'\\draw[{MUTED},line width=0.5pt] {self.pt(ua, self.v[0])} -- {self.pt(ua, self.v[1])};']
        for i, t in enumerate(u_ticks):
            lab = tick_fmt.format(t) if u_tick_labels is None else u_tick_labels[i]
            out.append(f'\\node[below,text={MUTED}] at {self.pt(t, va)} {{{lab}}};')
        for i, t in enumerate(v_ticks):
            lab = tick_fmt.format(t) if v_tick_labels is None else v_tick_labels[i]
            out.append(f'\\node[left,text={MUTED}] at {self.pt(ua, t)} {{{lab}}};')
        if u_label: out.append(f'\\node[below=11pt,text={MUTED}] at {self.pt((self.u[0] + self.u[1]) / 2, va)} {{{u_label}}};')
        if v_label:
            x, y = self(ua, (self.v[0] + self.v[1]) / 2)
            # the rotated axis title is set with anchor=south at a fixed distance left of the axis (a rotated node's
            # above= shift moves it along the page, over the tick labels)
            out.append(f'\\node[rotate=90,anchor=south,text={MUTED}] at ({x - v_label_offset:.3f},{y:.3f}) {{{v_label}}};')
        return out


def stack(L, x, y, items, width=4.4, gap=0.18, size=SMALL, line_h=0.34, char_w=0.155):
    """A column of notes under each other from the top-left corner (x, y): items are (text, colour); the height of each
    is estimated from its length, so nothing overlaps. Returns the y below the last item."""
    for text, col in items:
        plain = _re.sub(r'\\\\[a-zA-Z]+|[{}$^_]', '', text); n_lines = max(1, math.ceil(len(plain) * char_w / width))
        L.append(f'\\node[anchor=north west,text={col},{size},text width={width:.2f}cm] at ({x},{y}) {{{text}}};')
        y -= n_lines * line_h + gap
    return y


def clipped_path(P, xs, ys, style, lo, hi):
    """Draw a curve only where lo <= y <= hi, as separate segments."""
    out = []; seg = []
    for x, y in zip(xs, ys):
        if lo <= y <= hi: seg.append((x, y))
        elif len(seg) > 1: out.append(P.path(seg, style)); seg = []
        else: seg = []
    if len(seg) > 1: out.append(P.path(seg, style))
    return out


def writer(fig_dir, style=STYLE):
    """write(name, lines) for one deck: wraps the TikZ lines and saves assets/figures/<name>.tex."""
    fig_dir = Path(fig_dir); fig_dir.mkdir(parents=True, exist_ok=True)
    def write(name, lines):
        (fig_dir / f'{name}.tex').write_text('\\begin{tikzpicture}' + style + '\n' + '\n'.join(lines) + '\n\\end{tikzpicture}\n'); print('wrote', name)
    return write


def box(L, x, y, w, h, title, body, col, fill=None):
    L.append(f'\\draw[{col},line width=0.8pt{",fill=" + fill if fill else ""},rounded corners=3pt] ({x},{y}) rectangle ({x + w},{y + h});')
    L.append(f'\\node[anchor=north west,text={col},{HEAD}] at ({x + 0.12},{y + h - 0.08}) {{{title}}};')
    if body: L.append(f'\\node[anchor=north west,align=left,text={INK},{SMALL},text width={w - 0.3:.2f}cm] at ({x + 0.12},{y + h - 0.45}) {{{body}}};')


def contours(P, A, Bl, Z, levels, col=INK, lw=0.45):
    """Contour lines of Z (rows A, columns Bl) through matplotlib, drawn in a panel; shade lighter for higher levels."""
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    cs = plt.contour(A, Bl, np.asarray(Z).T, levels=levels); L = []
    for k, (lev, segs) in enumerate(zip(cs.levels, cs.allsegs)):
        shade = int(100 - 65 * k / max(len(cs.levels) - 1, 1))
        for seg in segs:
            if len(seg) > 2: L.append(P.path(seg[::2].tolist() + [seg[-1].tolist()], f'{tint(col, shade)},line width={lw}pt'))
    plt.close('all'); return L


# ------------------------------------------------------------------------------------------------ small helpers
def load_data(path):
    """A JSON summary written by a simulation (assets/data/*.json)."""
    return json.loads(Path(path).read_text(encoding='utf-8'))


def escape(text: str) -> str:
    """Escape the characters that break a TikZ label (% above all)."""
    return (text.replace('\\', '\\textbackslash{}').replace('%', '\\%').replace('&', '\\&')
            .replace('#', '\\#').replace('_', '\\_'))


def nohyphen(text: str) -> str:
    """A wrapped node (text width=) hyphenates unless the font is told not to; prefix the node text with this."""
    return r'\hyphenchar\font=-1 ' + text


def polyline(points, fmt='{:.3f}'):
    """(x,y) -- (x,y) -- ... for a \\draw of sampled data in page coordinates."""
    return ' -- '.join(f'({fmt.format(x)},{fmt.format(y)})' for x, y in points)


__all__ = ['INK', 'MUTED', 'HAIR', 'PAPER', 'SLIDE', 'BLUE', 'TEAL', 'ORANGE', 'PURPLE', 'CAVEAT', 'CONCEPT', 'EXAMPLE',
           'ANCHOR', 'QUESTION', 'INPUT', 'GAUSS', 'DOG', 'CSS', 'DN', 'FUTURE', 'STYLE', 'SMALL', 'TINY', 'HEAD',
           'PX_PER_CM', 'PT_PER_CM', 'FIGURE_HEIGHTS', 'tint', 'color', 'hex', 'Panel', 'stack', 'clipped_path', 'writer',
           'box', 'contours', 'load_data', 'escape', 'nohyphen', 'polyline', 'np', 'Path', 'math']
