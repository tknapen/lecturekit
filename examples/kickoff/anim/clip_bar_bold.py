"""Clip A04 (slide 4): a clean response. A bar sweeps across the field, rightward and then back; on the right, the overlap
of the bar with the illustrative population (blue) and the predicted BOLD response (charcoal) draw in step with it, the
BOLD response several seconds behind. No captions or notes on screen (the speaker gives them); the drawing fills the
frame, with its tick labels, the legend words and the hemodynamic-delay marker.

Stages (with assets/data/s01.json, the first 75 s of the run, as the static figure):
  1. The bar, 2 degrees wide, sweeps rightward (direction 0 degrees, 0 to 30 s); the overlap rises and falls as it
     crosses the population (x 2.5, y 1.5 degrees, sigma 1).
  2. The predicted BOLD response follows; a marker spans the hemodynamic delay between the first overlap peak (19 s)
     and the first BOLD peak (24 s).
  3. The bar sweeps back (direction 180 degrees, 30 to 60 s; the arrow turns), and a second response follows.
  4. A blank (60 to 75 s, a grey band): the response returns to baseline, through an undershoot.
  5. Hold on the complete traces.
Simulated time runs at 5 s per second of clip. Numbers: assets/data/s01.json (prfmodel forward model): t_s 0 to 74,
bar_centre_deg and bar_direction_deg per second for the bar (null is a blank; the centre is measured along the motion
direction), drive and bold each divided by its maximum over those 75 s, as make_assets.py bar_bold() does. The bar
moves smoothly between the per-second positions. The trace panel spans -0.25 to 1.1 as in the figure, except that its
lower bound drops to -0.35 when the BOLD undershoot goes below -0.25 (s01: -0.29), so the trace clears the time axis.
Without s01.json the clip falls back, as the static figure does, to make_assets.py bar_drive(dirs=(0, 90), blank=12)
and bold() in numpy (imported, not copied). Storyboard: STORYBOARD.md section 4, A04.
"""
from vfield import *

RATE = 5.0                   # simulated seconds per second of clip
WIDTH = 2.0                  # bar width (degrees)
NS01 = 75                    # make_assets.py bar_bold(): the first 75 s of s01


def series():
    """Per second: overlap, BOLD, bar centre and direction (None in a blank), with the figure's ticks and legend."""
    f = DATA / 's01.json'
    if f.exists():
        S = json.loads(f.read_text())
        d = np.array(S['drive'][:NS01], float); b = np.array(S['bold'][:NS01], float)
        return dict(drive=d / d.max(), bold=b / np.abs(b).max(), centre=S['bar_centre_deg'][:NS01], dirn=S['bar_direction_deg'][:NS01],
                    ticks=(0, 30, 60), legend=('overlap', 'BOLD', 0.8))
    d = MA.bar_drive(dirs=(0, 90), blank=12); centre, dirn = [], []
    for a in (0, 90):
        pos = [float(c) for c in np.arange(-8, 8 + 1e-9, 0.8)]
        centre += pos + [None] * 12; dirn += [float(a)] * len(pos) + [None] * 12
    return dict(drive=d, bold=MA.bold(d), centre=centre, dirn=dirn, ticks=(0, len(d) // 2, len(d)), legend=('input overlap', 'predicted BOLD', 0.36))


D = series(); DRIVE, BOLD, CENTRE, DIRN = D['drive'], D['bold'], D['centre'], D['dirn']; N = len(DRIVE)
W0 = min(-0.25, np.floor((BOLD.min() - 0.03) * 20) / 20)    # the figure's -0.25, lowered when the undershoot goes below it


def segments():
    """The schedule as sweeps [start, end, direction] and blanks [start, end], in seconds."""
    kind = [None if c is None else d for c, d in zip(CENTRE, DIRN)]
    sweeps, blanks = [], []
    for j, k in enumerate(kind):
        if j and k == kind[j - 1]: (blanks if k is None else sweeps)[-1][1] = j + 1
        elif k is None: blanks.append([j, j + 1])
        else: sweeps.append([j, j + 1, k])
    return sweeps, blanks


SWEEPS, BLANKS = segments()


def bar_at(t):
    """Bar centre (along its direction) and direction at time t, or None in a blank: per-second positions, moving
    smoothly between them and on at the same step past the last one of a sweep."""
    j = int(np.floor(t))
    if j >= N or CENTRE[j] is None: return None
    c, a = CENTRE[j], DIRN[j]
    if j + 1 < N and CENTRE[j + 1] is not None and DIRN[j + 1] == a: c1 = CENTRE[j + 1]
    elif j > 0 and CENTRE[j - 1] is not None and DIRN[j - 1] == a: c1 = 2 * c - CENTRE[j - 1]
    else: c1 = c
    return c + (c1 - c) * (t - j), a


def at(y, t):
    """y (one sample per second) at time t, linearly interpolated."""
    return float(np.interp(t, np.arange(len(y)), y))


def upto(y, t):
    """The samples of y up to time t, ending on the interpolated value at t."""
    j = int(np.floor(t)); pts = [(i, y[i]) for i in range(min(j, len(y) - 1) + 1)]
    if t > j and j + 1 < len(y): pts.append((t, at(y, t)))
    return pts if len(pts) > 1 else pts + pts


class BarBold(Scene):
    def construct(self):
        F = VField((-4.35, 0.45), 3.35)
        P = Frame(-0.15, -3.15, 7.85, 6.85, (0, N), (W0, 1.1))
        t = ValueTracker(0.0)

        def bar_now():
            s = bar_at(t.get_value())
            return F.empty() if s is None else F.bar(s[0], WIDTH, s[1], colour=tint(BLUE, 70))
        bar = always_redraw(bar_now).set_z_index(1)

        def arrow_for(a):
            """The sweep direction: a horizontal arrow under the field, a vertical one at its right."""
            s, e = ((F.c + [-1.6, -F.r - 0.38, 0], F.c + [1.6, -F.r - 0.38, 0]) if a % 180 == 0 else (F.c + [F.r + 0.38, -1.6, 0], F.c + [F.r + 0.38, 1.6, 0]))
            if a in (180, 270): s, e = e, s
            return Arrow(s, e, buff=0, color=BLUE, stroke_width=4, tip_length=0.22)
        arrow = arrow_for(SWEEPS[0][2])

        axes = P.axes(u_ticks=D['ticks'], u_label='time (s)', tick_size=24, label_size=26)
        drive = always_redraw(lambda: P.polyline(upto(DRIVE, t.get_value()), BLUE, 4.0)).set_z_index(2)
        bold = always_redraw(lambda: P.polyline(upto(BOLD, t.get_value()), INK, 5.0)).set_z_index(3)
        cursor = always_redraw(lambda: VGroup(
            Line(P(t.get_value(), W0), P(t.get_value(), 1.1), stroke_color=MUTED, stroke_width=2.0, stroke_opacity=0.45),
            Dot(P(t.get_value(), at(DRIVE, t.get_value())), radius=0.075, color=BLUE),
            Dot(P(t.get_value(), at(BOLD, t.get_value())), radius=0.085, color=INK))).set_z_index(4)
        name_d, name_b, ul = D['legend']
        legend = VGroup(label(name_d, 26, BLUE).move_to(P(N * ul, 0.92), aligned_edge=LEFT), label(name_b, 26, INK).move_to(P(N * ul, 0.74), aligned_edge=LEFT))
        j0, j1 = int(np.argmax(DRIVE[: N // 2])), int(np.argmax(BOLD[: N // 2]))         # as bar_bold(): 19 and 24 s with s01
        delay = DoubleArrow(P(j0, 1.05), P(j1, 1.05), buff=0, color=MUTED, stroke_width=3, tip_length=0.15, max_tip_length_to_length_ratio=0.3)
        delay = VGroup(delay, label('hemodynamic delay', 22, MUTED).next_to(delay, UP, buff=0.1))

        def blank(u0, u1):
            a, b = P(u0, W0), P(u1, 1.1)
            return Rectangle(width=b[0] - a[0], height=b[1] - a[1], stroke_width=0, fill_color=PAPER, fill_opacity=1).move_to((a + b) / 2).set_z_index(-1)

        self.add(F.disc(width=3.0), bar, F.cross(size=0.14, width=2.4).set_z_index(2), F.prf(**PRF, width=3.0).set_z_index(3), arrow, axes, legend, drive, bold, cursor)

        def run(t1, *anims):
            """Advance simulated time to t1 at RATE, with other animations alongside (time already past: nothing)."""
            t1 = max(t1, t.get_value())
            if t1 - t.get_value() < 1e-6 and not anims: return
            self.play(t.animate.set_value(t1), *anims, run_time=max((t1 - t.get_value()) / RATE, 1 / 15), rate_func=linear)

        half = 0.5 * RATE                                                  # half a second of clip, in simulated time
        current = {'arrow': arrow}

        def swap(d):
            """At the start of a later sweep, the arrow turns to its direction."""
            new = arrow_for(d); old = current['arrow']; current['arrow'] = new
            return [FadeOut(old), FadeIn(new)]

        events = [(j1 + 1.5, lambda: [FadeIn(delay)])]
        events += [(a - half / 2, lambda d=d: swap(d)) for a, b, d in SWEEPS[1:]]
        events += [(a, lambda a=a, b=b: [FadeIn(blank(a, b))]) for a, b in BLANKS]
        self.wait(0.8)
        for when, make in sorted(events, key=lambda e: e[0]):
            run(when); run(t.get_value() + half, *make())
        run(N - 1)
        cursor.clear_updaters()
        self.play(FadeOut(cursor), run_time=0.6)
        self.wait(2.6)
