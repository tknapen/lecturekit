"""The feature deck's kit clip, a clip in parts made with checkpoint(): a Gaussian on thin axes halves its width,
then moves right. The deck opens on frame 0 and plays a part per key (stops="narrowed", start=key).

1. Frame 0: the Gaussian at mean 0 and width 1 (peak 0.40); the first key starts part 1.
2. Part 1 (1.2 s): the width halves to 0.5, so the peak doubles to 0.80; the area stays one.
   checkpoint "narrowed" holds it, with 0.3 s still on each side.
3. Part 2 (1.2 s): the mean moves to 1.5; the shape is unchanged. The clip ends on it.

A toy curve, normal_pdf of the kit, not data; nothing in it needs a source. `lk clips examples/features --only
gauss-parts` renders it (and `--mode dark` the dark preset), with Manim from lecturekit's `clips` extra.
"""
from kit import *


class GaussParts(Scene):
    def construct(self):
        fr = Frame(-5.6, -2.6, 11.2, 5.4, (-4, 4), (0, 0.9))
        sd, mu = ValueTracker(1.0), ValueTracker(0.0)
        xs = np.linspace(-4, 4, 241)
        curve = always_redraw(lambda: fr.polyline(
            [(x, normal_pdf(x, mu.get_value(), sd.get_value())) for x in xs], GAUSS, 5))
        self.add(fr.axes(u_ticks=(-4, -2, 0, 2, 4), w_ticks=(0, 0.4, 0.8), u_label='x', w_label='density'), curve)
        self.wait(0.2)
        self.play(sd.animate.set_value(0.5), run_time=1.2)
        checkpoint(self, "narrowed", label="half the width", rest=0.6)
        self.play(mu.animate.set_value(1.5), run_time=1.2)
        self.wait(0.3)
