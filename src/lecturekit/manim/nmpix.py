"""Pixel grids for the course clips: an image or a filter as coloured squares, a window that slides over it, and the
convolution (cross-correlation, as in convolutional networks) computed in numpy.

Storyboard source: 3Blue1Brown's convolution video (github.com/3b1b/videos, _2022/convolutions/discrete.py,
ImageConvolution and the Sobel scenes), redrawn for Manim Community in the course style; no code is copied.

    img = PixelGrid(arr, size=0.32, cmap='grey')                 # values in [0, 1]
    k = PixelGrid(kernel, size=0.32, cmap='div', show_values=True) # signed values, blue positive, orange negative
    win = img.window(r, c, 3)                                    # a rectangle around rows r..r+2, columns c..c+2
"""
from .nmstyle import *

def _rgb_of(colour):
    h = ManimColor(colour).to_hex()
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)]) / 255.0


# the brand's tokens (nmstyle reads the deck's _brand.yml, the dark side under LECTUREKIT_MODE=dark)
_INK_RGB, _BLUE_RGB, _ORANGE_RGB, _SLIDE_RGB = _rgb_of(INK), _rgb_of(BLUE), _rgb_of(ORANGE), _rgb_of(SLIDE)


def _hex(rgb):
    rgb = np.clip(rgb, 0, 1); return '#%02x%02x%02x' % tuple(int(round(v * 255)) for v in rgb)


def colour_for(v, cmap='grey', vmin=0.0, vmax=1.0):
    """'grey': the slide colour (white on paper) at vmin, ink at vmax. 'div': orange for negative, the slide colour at
    zero, blue for positive (|v| / vmax)."""
    if cmap == 'grey':
        s = 0.0 if vmax == vmin else float(np.clip((v - vmin) / (vmax - vmin), 0, 1))
        return _hex((1 - s) * _SLIDE_RGB + s * _INK_RGB)
    m = max(abs(vmin), abs(vmax), 1e-9); s = float(np.clip(abs(v) / m, 0, 1))
    return _hex((1 - s) * _SLIDE_RGB + s * (_BLUE_RGB if v >= 0 else _ORANGE_RGB))


class PixelGrid(VGroup):
    def __init__(self, arr, size=0.3, cmap='grey', vmin=None, vmax=None, stroke=HAIR, stroke_width=0.8,
                 show_values=False, fmt='{:g}', value_size=16, center=ORIGIN):
        super().__init__()
        self.arr = np.asarray(arr, dtype=float); self.size = size; self.cmap = cmap
        self.vmin = float(self.arr.min()) if vmin is None else vmin; self.vmax = float(self.arr.max()) if vmax is None else vmax
        if cmap == 'div' and vmin is None and vmax is None: m = float(np.max(np.abs(self.arr))) or 1.0; self.vmin, self.vmax = -m, m
        h, w = self.arr.shape; self.cells = []
        for r in range(h):
            row = []
            for c in range(w):
                sq = Square(side_length=size, stroke_color=stroke, stroke_width=stroke_width,
                            fill_color=colour_for(self.arr[r, c], cmap, self.vmin, self.vmax), fill_opacity=1)
                sq.move_to(np.array([(c - (w - 1) / 2) * size, -(r - (h - 1) / 2) * size, 0])); row.append(sq); self.add(sq)
            self.cells.append(row)
        self.values = VGroup()
        if show_values:
            for r in range(h):
                for c in range(w):
                    v = self.arr[r, c]; s = abs(v - self.vmin) / max(self.vmax - self.vmin, 1e-9) if cmap == 'grey' else abs(v) / max(abs(self.vmax), 1e-9)
                    self.values.add(label(fmt.format(v), value_size, WHITE if s > 0.6 else INK).move_to(self.cells[r][c]))
            self.add(self.values)
        self.move_to(center)

    def cell(self, r, c):
        return self.cells[r][c]

    def window(self, r, c, k, colour=BLUE, width=5, kw=None):
        """A rectangle around k rows and kw (default k) columns starting at (r, c)."""
        kw = kw or k
        tl = self.cells[r][c].get_corner(UL); br = self.cells[r + k - 1][c + kw - 1].get_corner(DR)
        return Rectangle(width=br[0] - tl[0], height=tl[1] - br[1], stroke_color=colour, stroke_width=width).move_to((tl + br) / 2)

    def fill_anim(self, r, c, v):
        return self.cells[r][c].animate.set_fill(colour_for(v, self.cmap, self.vmin, self.vmax), opacity=1)

    def set_value(self, r, c, v):
        self.cells[r][c].set_fill(colour_for(v, self.cmap, self.vmin, self.vmax), opacity=1); return self

    def blank(self):
        for row in self.cells:
            for sq in row: sq.set_fill(SLIDE, opacity=1)
        return self


def conv2d(img, kernel, mode='valid'):
    """Cross-correlation of a 2-D image with a 2-D kernel (what convolutional networks call convolution)."""
    img = np.asarray(img, float); k = np.asarray(kernel, float); kh, kw = k.shape
    if mode == 'same': img = np.pad(img, ((kh // 2, kh - 1 - kh // 2), (kw // 2, kw - 1 - kw // 2)))
    H, W = img.shape[0] - kh + 1, img.shape[1] - kw + 1
    out = np.zeros((H, W))
    for r in range(H):
        for c in range(W): out[r, c] = np.sum(img[r:r + kh, c:c + kw] * k)
    return out


def maxpool(img, p=2):
    img = np.asarray(img, float); H, W = img.shape[0] // p, img.shape[1] // p
    return img[:H * p, :W * p].reshape(H, p, W, p).max(axis=(1, 3))
