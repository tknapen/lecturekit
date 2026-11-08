"""TikZ figures for the Coimbra workshop opening deck (5 November 2026).

Six wide schematics: the software family tree, the computational engine the proposal asked for, the community
around it, the model shelf of prfmodel 0.2.0, the build timeline, and the two-day programme.

    python3 make_assets.py            # all figures
    python3 make_assets.py shelf      # one
Sources: the Popylar full proposal (OEC 2024, 30 May 2024); the prfmodel documentation (0.2.0) and GitHub
repository; PyPI release dates; the workshop site's schedule (marked provisional there).
"""
import sys, math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
from lecturekit.tikz import *       # the TikZ kit: colour names, Panel, stack, box, writer
write = writer(HERE / 'assets' / 'figures')

W = 13.0            # figure width in cm; heights per figure
LAB = r'font=\sffamily\scriptsize'; NAME = r'font=\sffamily\small\bfseries'; TINYI = r'font=\sffamily\tiny\itshape'
HEADL = r'font=\sffamily\footnotesize\bfseries'; LABB = r'font=\sffamily\scriptsize\bfseries'


def rbox(L, x, y, w, h, col, fill=None, lw=0.8, dashed=False):
    L.append(f'\\draw[{col},line width={lw}pt{",fill=" + fill if fill else ""}{",dashed" if dashed else ""},rounded corners=3pt] ({x:.3f},{y:.3f}) rectangle ({x + w:.3f},{y + h:.3f});')


def text(L, x, y, s, col=INK, size=LAB, anchor='center', width=None, align='center'):
    tw = f',text width={width:.2f}cm,align={align}' if width else ''
    noh = r'\hyphenchar\font=-1 ' if width else ''
    L.append(f'\\node[anchor={anchor},text={col},{size}{tw}] at ({x:.3f},{y:.3f}) {{{noh}{s}}};')


def arrow(L, p, q, col=MUTED, lw=0.7, bend=None, dashed=False):
    b = f',bend {bend}' if bend else ''
    L.append(f'\\draw[-{{Latex[length=5pt]}},{col},line width={lw}pt{",dashed" if dashed else ""}] ({p[0]:.3f},{p[1]:.3f}) to[{b.lstrip(",")}] ({q[0]:.3f},{q[1]:.3f});' if bend else
             f'\\draw[-{{Latex[length=5pt]}},{col},line width={lw}pt{",dashed" if dashed else ""}] ({p[0]:.3f},{p[1]:.3f}) -- ({q[0]:.3f},{q[1]:.3f});')


# ------------------------------------------------------------------------------------------------ 1. lineage
def lineage():
    """Where prfmodel comes from: a Matlab lane above and a Python lane below; the three named ancestors feed
    prfmodel; the wider family sits faded in the Matlab lane."""
    L = []
    text(L, 0.3, 5.5, 'Matlab, C, C++', MUTED, TINYI, 'south west'); text(L, 0.3, 3.1, 'Python', MUTED, TINYI, 'south west')
    L.append(f'\\draw[{HAIR},dashed,line width=0.4pt] (0.3,3.05) -- ({W - 0.3:.3f},3.05);')

    def node(x, y, w, h, name, sub, col, fill=None, lw=0.8):
        rbox(L, x, y, w, h, col, fill, lw)
        if name: text(L, x + w / 2, y + h - 0.3, name, col, NAME)
        text(L, x + w / 2, y + 0.07, sub, MUTED, TINYI, 'south', w - 0.2)
        return x, y, w, h

    mv = node(0.3, 4.15, 2.5, 1.15, 'mrVista', 'Wandell and Dumoulin labs, 2008', BLUE, f'{BLUE}!6')
    fam = [('analyzePRF', 'Kay lab'), ('SamSrf', 'Schwarzkopf lab'), ('mrTools', 'Gardner lab'), ('VSNLabTools', 'Cornelissen lab'), ('AFNI', 'NIH'), ('BrainVoyager', 'Goebel')]
    x0 = 3.15; wf = 1.52
    for i, (n, g) in enumerate(fam):
        xi = x0 + i * (wf + 0.1); rbox(L, xi, 4.3, wf, 0.85, HAIR, 'white', 0.5)
        text(L, xi + wf / 2, 4.88, n, MUTED, r'font=\sffamily\tiny\bfseries'); text(L, xi + wf / 2, 4.55, g, MUTED, TINYI)
    text(L, x0 + 3 * (wf + 0.1) - 0.05, 5.3, 'the wider family: many packages, one model each, few shared tests', MUTED, TINYI, 'south')

    po = node(0.6, 1.75, 2.4, 1.15, 'popeye', 'DeSimone, Rokem, Schneider, 2016', PURPLE, f'{PURPLE}!6')
    pp = node(4.9, 1.75, 2.5, 1.15, 'prfpy', 'Dumoulin and Knapen labs, VU and NIN', TEAL, f'{TEAL}!6')
    bc = node(4.9, 0.2, 2.5, 1.15, 'braincoder', 'de Hollander; TensorFlow', ORANGE, f'{ORANGE}!6')
    pm = node(9.5, 0.85, 3.2, 1.6, '', 'Popylar, 2025 onward; Keras on JAX, PyTorch, TensorFlow', BLUE, f'{BLUE}!10', 1.3)
    text(L, pm[0] + pm[2] / 2, pm[1] + pm[3] - 0.38, 'prfmodel', BLUE, r'font=\sffamily\large\bfseries')

    arrow(L, (1.55, 4.15), (5.6, 2.9), BLUE, 0.8)
    text(L, 3.95, 3.72, 'the models, rewritten in Python', BLUE, TINYI, 'south west')
    arrow(L, (3.0, 2.25), (4.9, 2.25), PURPLE, 0.8)
    text(L, 3.95, 2.35, 'object-oriented pRF fitting', PURPLE, TINYI, 'south', 1.9)
    arrow(L, (7.4, 2.3), (9.5, 1.95), TEAL, 0.9)
    text(L, 8.45, 2.45, 'the model family, validated on 7T data', TEAL, TINYI, 'south', 2.3)
    arrow(L, (7.4, 0.78), (9.5, 1.3), ORANGE, 0.9)
    text(L, 7.6, 0.72, 'the fitting workflow: tensors, gradients, speed', ORANGE, TINYI, 'north west', 2.7)
    write('lineage', L)


# ------------------------------------------------------------------------------------------------ 2. engine
def engine():
    """The proposal's computational engine: stimulus and parameters into one model definition, predictions against
    data, a fitter closing the loop; three design commitments underneath."""
    L = []; WE = 14.2
    y = 2.85; h = 1.3
    boxes = [(1.8, 'stimulus $x$', 'bars, images, sounds', BLUE),
             (3.0, 'model $f(x, \\theta)$', 'pRF $\\circ$ impulse response $\\circ$ scaling: one graph', TEAL),
             (1.9, 'prediction', 'the model as a data generator', TEAL),
             (1.9, 'data', 'fMRI, ECoG, electrodes', INK),
             (1.8, 'fitter', 'grid, then gradients', ORANGE),
             (1.8, 'estimate $\\hat\\theta$', 'cross-validated fit', ORANGE)]
    x = 0.2; xs = []; L2 = []     # L2: the second stage (data, fitter, estimate, the update loop)
    for k, (w, title, sub, col) in enumerate(boxes):
        T = L if k < 3 else L2
        rbox(T, x, y, w, h, col, f'{col}!6' if col != INK else 'white', 0.9)
        text(T, x + w / 2, y + h - 0.1, title, col, LABB, 'north'); text(T, x + w / 2, y + 0.08, sub, MUTED, TINYI, 'south', w - 0.15)
        xs.append((x, w)); x += w + 0.32
    for i in range(5):
        x0, w0 = xs[i]; x1, _ = xs[i + 1]; T = L if i < 2 else L2
        if i == 2:
            T.append(f'\\draw[{INK},line width=0.7pt] ({x0 + w0:.3f},{y + h / 2:.3f}) -- ({x1:.3f},{y + h / 2:.3f});'); text(T, (x0 + w0 + x1) / 2, y + h / 2 + 0.05, 'vs', MUTED, TINYI, 'south')
        else: arrow(T, (x0 + w0, y + h / 2), (x1, y + h / 2), boxes[i + 1][3] if i != 3 else ORANGE)
    # parameters above the model, and the loop back from the fitter
    mx = xs[1][0] + xs[1][1] / 2; fx = xs[4][0] + xs[4][1] / 2
    rbox(L, mx - 1.05, 4.5, 2.1, 0.7, PURPLE, f'{PURPLE}!6'); text(L, mx, 4.85, 'parameters $\\theta$', PURPLE, LABB)
    arrow(L, (mx, 4.5), (mx, y + h), PURPLE)
    L2.append(f'\\draw[-{{Latex[length=5pt]}},{ORANGE},line width=0.8pt,dashed] ({fx:.3f},{y + h:.3f}) -- ({fx:.3f},4.85) -- ({mx + 1.05:.3f},4.85);')
    text(L2, (mx + 1.05 + fx) / 2, 4.9, 'update $\\theta$, predict again', ORANGE, TINYI, 'south')
    # three commitments
    cy, ch, gap = 0.2, 2.15, 0.3; cw = (WE - 0.4 - 2 * gap) / 3
    items = [('One definition, any backend', 'Written once in Keras; runs on JAX, PyTorch or TensorFlow, on a laptop CPU or a GPU. Gradients come with the backend.', BLUE),
             ('Simulation first', 'Every model generates data before it fits data. Parameter recovery is a first-class citizen.', TEAL),
             ('Built to be extended', 'Stimulus encoder, tuning, impulse response, scaling, regressors: a new model is a new part, the fitting and tests stay.', ORANGE)]
    for i, (t, bd, col) in enumerate(items):
        x = 0.2 + i * (cw + gap); rbox(L, x, cy, cw, ch, col, None, 0.8)
        text(L, x + 0.15, cy + ch - 0.1, t, col, LABB, 'north west')
        text(L, x + 0.15, cy + ch - 0.45, bd, INK, LAB, 'north west', cw - 0.3, 'left')
    write('engine', L + L2)
    write('engine-0', L + ['\\begin{scope}[opacity=0]'] + L2 + ['\\end{scope}'])   # same bounding box, second stage invisible


# ------------------------------------------------------------------------------------------------ 3. community
def community():
    """The community half of the proposal: prfmodel in the middle, six commitments around it."""
    L = []
    cx, cy = W / 2, 2.75
    L.append(f'\\draw[{BLUE},line width=1.2pt,fill={BLUE}!10] ({cx:.3f},{cy:.3f}) circle (1.25);')
    text(L, cx, cy + 0.22, 'prfmodel', BLUE, r'font=\sffamily\large\bfseries'); text(L, cx, cy - 0.25, 'community software', BLUE, TINYI, 'center', 2.2)
    sats = [(-4.7, 1.55, '29 letters of support', 'labs around the world pledged data, teaching, testing and architecture', PURPLE),
            (0.0, 2.1, 'A development committee', 'the authors of other pRF packages at the table from the design stage', TEAL),
            (4.7, 1.55, 'Governance', 'open licence (Apache 2.0), code of conduct, release schedule, contributor guide', INK),
            (-4.7, -1.55, 'Benchmark datasets', 'fMRI, ECoG, primate electrophysiology, mouse imaging; small, downloadable, documented', ORANGE),
            (0.0, -2.1, 'Tutorials per model', 'simulate first, then fit real data; runnable in the browser', BLUE),
            (4.7, -1.55, 'Hacks and workshops', 'coding sprints at the Spinoza Centre; a hands-on school each year: this is one', TEAL)]
    for dx, dy, t, b, col in sats:
        x, y = cx + dx, cy + dy; w, h = 3.6, 1.25
        rbox(L, x - w / 2, y - h / 2, w, h, col, 'white', 0.8)
        text(L, x, y + h / 2 - 0.1, t, col, LABB, 'north'); text(L, x, y + h / 2 - 0.42, b, INK, TINYI, 'north', w - 0.3)
        # connector from the circle edge to the box edge
        ang = math.atan2(dy, dx); sx, sy = cx + 1.25 * math.cos(ang), cy + 1.25 * math.sin(ang)
        ex = x - math.copysign(w / 2, dx) if abs(dx) > 1 else x; ey = y - math.copysign(h / 2, dy) if abs(dx) <= 1 else y
        L.append(f'\\draw[{col},line width=0.6pt] ({sx:.3f},{sy:.3f}) -- ({ex:.3f},{ey:.3f});')
    write('community', L)


# ------------------------------------------------------------------------------------------------ 4. shelf
def shelf():
    """The models in prfmodel 0.2.0 as a shelf of cards, each with a small drawing of what it computes."""
    L = []
    cw, ch, gap = 2.0, 2.6, 0.2
    cards = [('Gaussian 1D', 'numerosity, tonotopy', GAUSS, 'g1'), ('Gaussian 2D', 'the canonical pRF', GAUSS, 'g2'),
             ('CSS', 'compressive summation', CSS, 'css'), ('Difference of Gaussians', 'centre and surround', DOG, 'dog'),
             ('Divisive\\\\normalization', 'activation over suppression', DN, 'dn'), ('Centre,\\\\surround', 'two fields, two signs', DOG, 'cs'),
             ('Connective field', 'a pRF on the cortex', TEAL, 'cf'), ('Contrast sensitivity', 'frequency and contrast', PURPLE, 'csf'),
             ('Delayed\\\\normalization', 'response over time', DN, 'dnorm'), ('CST', 'sustained and transient', ORANGE, 'cst'),
             ('Impulse responses', 'HRFs; sustained, transient', INK, 'hrf'), ('Your model', 'compose it from the parts', MUTED, 'custom')]
    x_grid = np.linspace(-1, 1, 60)
    L1 = L; L2 = []
    for k, (name, sub, col, kind) in enumerate(cards):
        r, c = divmod(k, 6); x = 0.2 + c * (cw + gap); y = 0.2 + (1 - r) * (ch + gap)
        L = L2 if kind == 'custom' else L1
        rbox(L, x, y, cw, ch, col, 'white' if kind != 'custom' else None, 0.8, dashed=(kind == 'custom'))
        text(L, x + cw / 2, y + ch - 0.08, name, col, LABB, 'north', cw - 0.2); text(L, x + cw / 2, y + 0.06, sub, MUTED, TINYI, 'south', cw - 0.2)
        # drawing area
        ax0, ay0, aw, ah = x + 0.25, y + 0.55, cw - 0.5, 1.25
        P = Panel(ax0, ay0, aw, ah, (-1, 1), (0, 1))
        if kind == 'g1':
            L.append(P.path([(u, 0.9 * math.exp(-u * u / 0.12)) for u in x_grid], f'{col},line width=1pt'))
            for u in np.linspace(-0.9, 0.9, 7): L.append(f'\\draw[{HAIR},line width=0.4pt] {P.pt(u, 0)} -- {P.pt(u, 0.05)};')
        elif kind == 'g2':
            mx, my = P(0, 0.5)
            for rr, op in ((0.5, 15), (0.36, 30), (0.22, 55), (0.1, 90)): L.append(f'\\fill[{col},fill opacity={op / 100:.2f}] ({mx:.3f},{my:.3f}) circle ({rr:.3f});')
            L.append(f'\\draw[{HAIR},line width=0.5pt] ({mx:.3f},{my:.3f}) circle (0.55);')
        elif kind == 'css':
            L.append(P.path([(u, 0.05 + 0.9 * ((u + 1) / 2) ** 0.4) for u in x_grid], f'{col},line width=1pt'))
            L.append(P.path([(-1, 0.05), (1, 0.95)], f'{HAIR},line width=0.5pt,dashed'))
            text(L, P(0.55, 0.3)[0], P(0.55, 0.3)[1], '$n<1$', col, TINYI)
        elif kind == 'dog':
            L.append(P.path([(u, 0.35 + 0.6 * math.exp(-u * u / 0.06) - 0.3 * math.exp(-u * u / 0.5)) for u in x_grid], f'{col},line width=1pt'))
            L.append(P.hline(0.35, f'{HAIR},line width=0.4pt'))
        elif kind == 'dn':
            L.append(P.path([(u, 0.55 + 0.4 * math.exp(-u * u / 0.06)) for u in x_grid], f'{col},line width=1pt'))
            L.append(P.hline(0.5, f'{INK},line width=0.6pt', -0.8, 0.8))
            L.append(P.path([(u, 0.05 + 0.35 * math.exp(-u * u / 0.5)) for u in x_grid], f'{col}!60,line width=1pt'))
        elif kind == 'cs':
            mx, my = P(0, 0.5)
            L.append(f'\\fill[{col},fill opacity=0.18] ({mx:.3f},{my:.3f}) circle (0.52);'); L.append(f'\\fill[white] ({mx:.3f},{my:.3f}) circle (0.26);')
            L.append(f'\\fill[{col},fill opacity=0.8] ({mx:.3f},{my:.3f}) circle (0.26);'); text(L, mx + 0.62, my + 0.35, '$-$', col, LAB); text(L, mx, my, '$+$', 'white', LAB)
        elif kind == 'cf':
            # a folded cortex strip with a Gaussian on it
            pts = [(u, 0.3 + 0.12 * math.sin(3 * u)) for u in x_grid]
            L.append(P.path([(u, v + 0.35) for u, v in pts], f'{HAIR},line width=0.6pt')); L.append(P.path(pts, f'{HAIR},line width=0.6pt'))
            mx, my = P(0.15, 0.5)
            for rr, op in ((0.42, 15), (0.28, 35), (0.14, 70)): L.append(f'\\fill[{col},fill opacity={op / 100:.2f}] ({mx:.3f},{my:.3f}) circle ({rr:.3f});')
            text(L, P(-0.7, 0.9)[0], P(-0.7, 0.9)[1], 'V1', MUTED, TINYI)
        elif kind == 'csf':
            L.append(P.path([(u, 0.15 + 0.75 * math.exp(-(u + 0.2) ** 2 / 0.25) * (1 - 0.3 * (u + 1))) for u in x_grid], f'{col},line width=1pt'))
            L.extend(P.axes(u_label='', v_label=''))
        elif kind == 'dnorm':
            tt = np.linspace(0, 1, 80); resp = [0.1 + 0.85 * (1 - math.exp(-t * 18)) * (0.45 + 0.55 * math.exp(-t * 6)) if t < 0.65 else 0.1 + 0.85 * (0.45 + 0.55 * math.exp(-0.65 * 6)) * math.exp(-(t - 0.65) * 14) for t in tt]
            L.append(P.path(list(zip(2 * tt - 1, resp)), f'{col},line width=1pt')); L.append(P.fill([(-1, 0), (-1, 0.06), (0.3, 0.06), (0.3, 0)], f'{INK}'))
        elif kind == 'cst':
            tt = np.linspace(0, 1, 80)
            L.append(P.path(list(zip(2 * tt - 1, [0.1 + 0.6 * (1 - math.exp(-t * 12)) * (t < 0.65) + 0.6 * math.exp(-(t - 0.65) * 12) * (t >= 0.65) for t in tt])), f'{col},line width=1pt'))
            L.append(P.path(list(zip(2 * tt - 1, [0.1 + 0.8 * math.exp(-((t - 0.08) ** 2) / 0.003) + 0.8 * math.exp(-((t - 0.69) ** 2) / 0.003) for t in tt])), f'{col}!55,line width=1pt'))
            text(L, P(0.5, 0.75)[0], P(0.5, 0.75)[1], 'S', col, TINYI); text(L, P(-0.55, 0.9)[0], P(-0.55, 0.9)[1], 'T', f'{col}!70', TINYI)
        elif kind == 'hrf':
            from math import gamma
            tt = np.linspace(0, 25, 90)
            def g(t, a): return np.where(t > 0, t ** (a - 1) * np.exp(-t) / gamma(a), 0.0)
            h1 = g(tt, 6) - g(tt, 16) / 6; h1 = h1 / h1.max(); h2 = g(tt - 1.5, 7) - g(tt - 1.5, 17) / 6; h2 = h2 / max(h2.max(), 1e-9)
            L.append(P.path(list(zip(2 * tt / 25 - 1, 0.2 + 0.75 * h1)), f'{col},line width=1pt')); L.append(P.path(list(zip(2 * tt / 25 - 1, 0.2 + 0.75 * h2)), f'{MUTED},line width=0.8pt,dashed'))
            L.append(P.hline(0.2, f'{HAIR},line width=0.4pt'))
        elif kind == 'custom':
            for i, (lab, cc) in enumerate((('stimulus', BLUE), ('tuning', TEAL), ('impulse', INK), ('scaling', ORANGE))):
                yy = ay0 + ah - 0.12 - i * 0.28; rbox(L, ax0 + 0.15, yy - 0.22, aw - 0.3, 0.24, cc, f'{cc}!8', 0.5); text(L, ax0 + aw / 2, yy - 0.1, lab, cc, TINYI)
    write('shelf', L1 + L2)
    write('shelf-0', L1 + ['\\begin{scope}[opacity=0]'] + L2 + ['\\end{scope}'])


# ------------------------------------------------------------------------------------------------ 5. timeline
def timeline():
    """From the proposal to the release: a dated axis with the verified milestones, and the commit counts."""
    L = []
    P = Panel(0.5, 0.0, W - 1.0, 1.0, (2024.3, 2027.0), (0, 1))
    ya = 2.0
    L.append(f'\\draw[{HAIR},line width=0.8pt] {P.pt(2024.3, 0)} ++(0,{ya}) -- ++({W - 1.0:.3f},0);')
    for yr in (2025, 2026, 2027):
        x, _ = P(yr, 0); L.append(f'\\draw[{MUTED},line width=0.5pt] ({x:.3f},{ya - 0.08:.3f}) -- ({x:.3f},{ya + 0.08:.3f});')
        text(L, x + 0.05, ya + 0.1, str(yr), MUTED, TINYI, 'south west')
    # (year, date, what, colour, side, level, horizontal nudge of the label)
    events = [(2024 + 4.97 / 12, 'May 2024', 'the proposal: 29 letters of support', PURPLE, 'up', 1, 0),
              (2025.0, 'Jan 2025', 'project start: governance, then the design stage', PURPLE, 'down', 1, 0),
              (2025 + 11.1 / 12, 'Dec 2025', 'connective field stimulus and model', TEAL, 'up', 1, -0.9),
              (2026 + 1.5 / 12, 'Feb 2026', 'difference of Gaussians model; docs for every branch', TEAL, 'down', 1, 0),
              (2026 + 2.3 / 12, 'Mar 2026', 'DoG tutorial online; the API reference', TEAL, 'up', 2, 0.9),
              (2026 + 9.87 / 12, '27 Oct 2026', 'prfmodel 0.1.0 on PyPI', BLUE, 'down', 1, -0.4),
              (2026 + 10.1 / 12, '3 Nov 2026', '0.2.0: the workshop release', BLUE, 'up', 1, 0),
              (2026 + 10.15 / 12, '5 Nov 2026', 'Coimbra', ORANGE, 'down', 2, 0.9)]
    for yr, date, what, col, side, level, dx in events:
        x, _ = P(yr, 0)
        L.append(f'\\fill[{col}] ({x:.3f},{ya:.3f}) circle (0.09);')
        d = 0.5 + 0.75 * (level - 1)
        if side == 'up':
            L.append(f'\\draw[{col},line width=0.5pt] ({x:.3f},{ya + 0.09:.3f}) -- ({x:.3f},{ya + d:.3f}) -- ({x + dx:.3f},{ya + d:.3f});')
            text(L, x + dx, ya + d + 0.05, f'\\textbf{{{date}}}\\\\{what}', col, TINYI, 'south', 2.4)
        else:
            L.append(f'\\draw[{col},line width=0.5pt] ({x:.3f},{ya - 0.09:.3f}) -- ({x:.3f},{ya - d:.3f}) -- ({x + dx:.3f},{ya - d:.3f});')
            text(L, x + dx, ya - d - 0.05, f'\\textbf{{{date}}}\\\\{what}', col, TINYI, 'north', 2.4)
    # commit counts
    yb = 4.75; text(L, 0.5, yb + 0.5, 'commits to popylar-org/prfmodel, by author (GitHub, 4 November 2026)', MUTED, TINYI, 'west')
    counts = [('Malte Lüken', 389, BLUE), ('José Angel Daza', 79, TEAL), ('two colleagues', 23, MUTED)]
    scale = (W - 1.0 - 2.3) / (389 + 79 + 23); x = 0.5
    for name, n, col in counts:
        w = n * scale
        L.append(f'\\fill[{col}] ({x:.3f},{yb:.3f}) rectangle ({x + w:.3f},{yb + 0.4:.3f});')
        if n > 200: text(L, x + 0.1, yb + 0.2, f'{name}: {n}', 'white', LAB, 'west')
        elif n > 50: text(L, x + w / 2, yb - 0.05, f'{name}: {n}', col, TINYI, 'north')
        else: text(L, x + w + 0.1, yb + 0.2, f'{name}: {n}', col, TINYI, 'west')
        x += w + 0.05
    write('timeline', L)


# ------------------------------------------------------------------------------------------------ 6. programme
def programme():
    """The two days as two columns with a shared vertical time axis: lectures, prfmodel sessions, practicals, breaks."""
    L = []
    KIND = {'lec': (BLUE, f'{BLUE}!8'), 'pm': (TEAL, f'{TEAL}!10'), 'prac': (ORANGE, f'{ORANGE}!10'), 'brk': (HAIR, 'white'), 'misc': (MUTED, 'white')}
    thu = [(9.0, 9.25, 'Welcome', 'misc', 'Tomas Knapen'), (9.25, 9.75, 'Historic origins', 'lec', 'Serge Dumoulin'), (9.75, 10.25, 'Designing experiments', 'lec', 'Tomas Knapen'),
           (10.25, 10.5, '', 'brk'), (10.5, 11.0, 'Cognitive pRF models', 'lec', 'Ben Harvey'), (11.0, 11.5, 'Introduction to prfmodel', 'pm', 'Malte Lüken'),
           (11.5, 11.75, '', 'brk'), (11.75, 13.0, 'Practical 1', 'prac'), (13.0, 14.0, 'lunch', 'brk'), (14.0, 16.5, 'Practical 2', 'prac'), (16.5, 17.0, 'Recap and discussion', 'misc')]
    fri = [(9.0, 9.25, 'Recap', 'pm', 'Malte Lüken'), (9.25, 10.0, 'Advanced pRF models', 'lec', 'Tomas Knapen'), (10.0, 10.25, '', 'brk'),
           (10.25, 10.75, 'Electrophysiology', 'lec', 'Ilona Bloem'), (10.75, 11.25, 'Contrast sensitivity', 'lec', 'Marcus Daghlian'), (11.25, 11.5, '', 'brk'),
           (11.5, 12.0, 'Modelling choices', 'pm', 'Malte Lüken'), (12.0, 13.0, 'Practical 3', 'prac'), (13.0, 14.0, 'lunch', 'brk'), (14.0, 16.5, 'Practical 4', 'prac'), (16.5, 17.0, 'Recap and discussion', 'misc')]
    top, bottom = 7.0, 0.6; per_h = (top - bottom) / 8.0
    def Y(t): return top - (t - 9.0) * per_h
    cols = [('Thursday 5 November', 1.0, thu, 'drinks at 17:00'), ('Friday 6 November', 7.1, fri, 'social dinner at 19:30')]; cw = 5.75
    for t in range(9, 18):
        text(L, 0.9, Y(t), f'{t}:00', MUTED, TINYI, 'east'); L.append(f'\\draw[{HAIR},line width=0.3pt] (0.95,{Y(t):.3f}) -- ({W - 0.1:.3f},{Y(t):.3f});')
    for day, x0, blocks, after in cols:
        text(L, x0, top + 0.08, day, INK, HEADL, 'south west'); text(L, x0 + cw, top + 0.1, after, MUTED, TINYI, 'south east')
        for bk in blocks:
            t0, t1, title, kind = bk[:4]; who = bk[4] if len(bk) > 4 else ''
            y1, y0 = Y(t0), Y(t1); col, fill = KIND[kind]; ym = (y0 + y1) / 2
            L.append(f'\\draw[{col},line width=0.6pt,fill={fill},rounded corners=2pt] ({x0:.3f},{y0 + 0.02:.3f}) rectangle ({x0 + cw:.3f},{y1 - 0.02:.3f});')
            if not title: continue
            if kind == 'prac':
                text(L, x0 + cw / 2, ym, title, col, HEADL)
            elif kind == 'brk':
                text(L, x0 + cw / 2, ym, title, MUTED, LAB)
            else:
                size = LABB if t1 - t0 >= 0.5 else r'font=\sffamily\tiny\bfseries'; wsize = LAB if t1 - t0 >= 0.5 else TINYI
                text(L, x0 + 0.12, ym, title, col if kind != 'misc' else INK, size, 'west')
                if who: text(L, x0 + cw - 0.12, ym, who, MUTED, wsize, 'east')
    lx = 1.0
    for lab, kind in (('lectures', 'lec'), ('prfmodel sessions', 'pm'), ('hands-on practicals with prfmodel', 'prac')):
        col, fill = KIND[kind]; L.append(f'\\draw[{col},fill={fill},line width=0.5pt] ({lx:.3f},0.08) rectangle ({lx + 0.35:.3f},0.3);'); text(L, lx + 0.45, 0.19, lab, MUTED, LAB, 'west'); lx += 3.4
    write('programme', L)


ALL = {'lineage': lineage, 'engine': engine, 'community': community, 'shelf': shelf, 'timeline': timeline, 'programme': programme}
if __name__ == '__main__':
    names = sys.argv[1:] or list(ALL)
    for n in names: ALL[n]()
