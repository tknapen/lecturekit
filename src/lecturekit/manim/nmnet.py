"""Networks for the course clips: units as circles in layers, edges whose width and colour carry the weight, activity
as fill, a forward sweep in teal and a backward sweep in orange.

Storyboard source: the network drawings of 3Blue1Brown's neural-network series (github.com/3b1b/videos, _2017/nn,
NetworkMobject), redrawn here for Manim Community in the course style; no code is copied.

    net = Net([2, 2, 1], width=5, height=3, center=LEFT * 3)
    self.add(net); net.set_weights(Ws)              # Ws[l] has shape (n_{l+1}, n_l)
    self.play(*net.activations_anim(acts))          # acts[l] has shape (n_l,), values in [0, 1]
    self.play(net.forward(acts)); self.play(net.backward(deltas))
"""
from .nmstyle import *


def weight_colour(w):
    return BLUE if w >= 0 else ORANGE


class Net(VGroup):
    def __init__(self, sizes, width=6.0, height=4.0, radius=0.24, center=ORIGIN, edge_width=2.5, wmax=None,
                 unit_stroke=INK, fill=TEAL, spacing=None):
        super().__init__()
        self.sizes, self.radius, self.edge_width, self.wmax, self.fill_colour = list(sizes), radius, edge_width, wmax, fill
        nL = len(sizes); xs = np.linspace(-width / 2, width / 2, nL) if nL > 1 else [0.0]
        self.layers = VGroup()
        for l, n in enumerate(sizes):
            step = spacing if spacing else (min(height / max(n - 1, 1), 4 * radius) if n > 1 else 0)
            ys = (np.arange(n) - (n - 1) / 2) * step
            layer = VGroup(*[Circle(radius=radius, stroke_color=unit_stroke, stroke_width=2.2, fill_color=SLIDE, fill_opacity=1)
                             .move_to(np.array([xs[l], -y, 0]) + center) for y in ys])
            self.layers.add(layer)
        self.edges = VGroup()          # self.edges[l][j][i]: from unit i of layer l to unit j of layer l + 1
        for l in range(nL - 1):
            gap = VGroup()
            for j, b in enumerate(self.layers[l + 1]):
                gap.add(VGroup(*[Line(a.get_center(), b.get_center(), buff=radius, stroke_color=HAIR, stroke_width=edge_width)
                                 for a in self.layers[l]]))
            self.edges.add(gap)
        self.add(self.edges, self.layers)

    # --------------------------------------------------------------- weights
    def _style(self, w, wmax):
        s = min(abs(w) / wmax, 1.0) if wmax > 0 else 0.0
        return dict(color=weight_colour(w), width=self.edge_width * (0.3 + 1.9 * s), opacity=0.25 + 0.75 * s)

    def _wmax(self, Ws):
        return self.wmax or max(float(np.max(np.abs(W))) for W in Ws)

    def set_weights(self, Ws):
        m = self._wmax(Ws)
        for l, W in enumerate(Ws):
            for j in range(W.shape[0]):
                for i in range(W.shape[1]): self.edges[l][j][i].set_stroke(**self._style(W[j, i], m))
        return self

    def weights_anim(self, Ws):
        m = self._wmax(Ws); out = []
        for l, W in enumerate(Ws):
            for j in range(W.shape[0]):
                for i in range(W.shape[1]): out.append(self.edges[l][j][i].animate.set_stroke(**self._style(W[j, i], m)))
        return out

    # --------------------------------------------------------------- activity
    def set_activations(self, acts, colour=None):
        for l, a in enumerate(acts):
            for i, v in enumerate(np.ravel(a)): self.layers[l][i].set_fill(colour or self.fill_colour, opacity=float(np.clip(v, 0, 1)))
        return self

    def activations_anim(self, acts, colour=None):
        return [self.layers[l][i].animate.set_fill(colour or self.fill_colour, opacity=float(np.clip(v, 0, 1)))
                for l, a in enumerate(acts) for i, v in enumerate(np.ravel(a))]

    def forward(self, acts, colour=None, run_time=1.6):
        """Layer by layer: a flash runs along every edge, then the next layer's units fill."""
        colour = colour or self.fill_colour; steps = [AnimationGroup(*[self.layers[0][i].animate.set_fill(colour, opacity=float(np.clip(v, 0, 1)))
                                                                    for i, v in enumerate(np.ravel(acts[0]))])]
        for l in range(len(self.sizes) - 1):
            flashes = [ShowPassingFlash(Line(e.get_start(), e.get_end(), stroke_color=colour, stroke_width=5), time_width=0.5)
                       for gap in self.edges[l] for e in gap]
            fills = [self.layers[l + 1][i].animate.set_fill(colour, opacity=float(np.clip(v, 0, 1))) for i, v in enumerate(np.ravel(acts[l + 1]))]
            steps += [AnimationGroup(*flashes), AnimationGroup(*fills)]
        return Succession(*steps, run_time=run_time)

    def backward(self, deltas=None, colour=ORANGE, run_time=1.6):
        """Layer by layer from the output: a flash runs back along every edge; units with an error get an orange ring
        whose width follows |delta| (deltas[l] for layers 1..L, or None for rings of equal width)."""
        steps = []
        for l in range(len(self.sizes) - 1, 0, -1):
            d = np.ravel(deltas[l]) if deltas is not None else np.ones(self.sizes[l])
            m = max(float(np.max(np.abs(d))), 1e-9)
            rings = [self.layers[l][i].animate.set_stroke(colour, width=2.2 + 4 * abs(v) / m) for i, v in enumerate(d)]
            flashes = [ShowPassingFlash(Line(e.get_end(), e.get_start(), stroke_color=colour, stroke_width=5), time_width=0.5)
                       for gap in self.edges[l - 1] for e in gap]
            steps += [AnimationGroup(*rings), AnimationGroup(*flashes)]
        return Succession(*steps, run_time=run_time)

    def clear_rings(self):
        return [u.animate.set_stroke(INK, width=2.2) for layer in self.layers for u in layer]

    # --------------------------------------------------------------- labels
    def label_layer(self, l, text, size=22, colour=MUTED, buff=0.35):
        return label(text, size, colour).next_to(self.layers[l], DOWN, buff=buff)

    def label_units(self, l, texts, size=22, colour=INK, side=LEFT, buff=0.2):
        return VGroup(*[label(t, size, colour, serif=True).next_to(u, side, buff=buff) for t, u in zip(texts, self.layers[l])])


def unit_diagram(n_in=2, center=ORIGIN, scale=1.0, in_labels=None, w_labels=None, out_label='y'):
    """One unit drawn as inputs, weights, a summing node and a nonlinearity box: the model neuron of lecture 5."""
    g = VGroup(); c = np.array(center)
    ys = (np.arange(n_in) - (n_in - 1) / 2) * 1.3 * scale
    body = Circle(radius=0.55 * scale, stroke_color=INK, stroke_width=2.5, fill_color=SLIDE, fill_opacity=1).move_to(c)
    sig = label('Σ', int(40 * scale), INK).move_to(c)
    box = RoundedRectangle(width=1.1 * scale, height=0.9 * scale, corner_radius=0.08, stroke_color=INK, stroke_width=2.2).move_to(c + RIGHT * 1.7 * scale)
    curve = VMobject(stroke_color=INK, stroke_width=3)
    xs = np.linspace(-0.4, 0.4, 30) * scale
    curve.set_points_smoothly([box.get_center() + np.array([x, (1 / (1 + np.exp(-x * 14 / scale)) - 0.5) * 0.6 * scale, 0]) for x in xs])
    out = Arrow(box.get_right(), box.get_right() + RIGHT * 1.1 * scale, buff=0, stroke_color=INK, stroke_width=3, max_tip_length_to_length_ratio=0.25)
    g.inputs, g.lines = VGroup(), VGroup()
    for k, y in enumerate(ys):
        p = c + np.array([-3.0 * scale, -y, 0])
        dot = Circle(radius=0.3 * scale, stroke_color=INK, stroke_width=2.2, fill_color=SLIDE, fill_opacity=1).move_to(p)
        d = (c - p) / np.linalg.norm(c - p)
        ln = Line(p + d * 0.3 * scale, c - d * 0.55 * scale, stroke_color=INK, stroke_width=2.5)
        g.inputs.add(dot); g.lines.add(ln)
    g.body, g.sigma, g.box, g.curve, g.out = body, sig, box, curve, out
    g.add(g.lines, g.inputs, body, sig, Line(body.get_right(), box.get_left(), stroke_color=INK, stroke_width=2.5), box, curve, out)
    if in_labels:
        g.in_labels = VGroup(*[label(t, int(24 * scale), INK, serif=True).next_to(d, LEFT, buff=0.15) for t, d in zip(in_labels, g.inputs)]); g.add(g.in_labels)
    if w_labels:
        g.w_labels = VGroup(*[label(t, int(22 * scale), BLUE, serif=True).move_to(ln.point_from_proportion(0.45) + UP * 0.28 * scale) for t, ln in zip(w_labels, g.lines)]); g.add(g.w_labels)
    g.out_label = label(out_label, int(26 * scale), INK, serif=True).next_to(out, RIGHT, buff=0.12); g.add(g.out_label)
    return g
