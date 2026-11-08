"""The shared Manim kit: every deck's clips import this package instead of carrying their own style.

A deck's `anim/kit.py` is two lines (`lk new` writes it):

    from lecturekit.manim import *
    HERE = Path(__file__).resolve().parent; DATA = HERE.parent / 'assets' / 'data'

and every clip starts with `from kit import *`, which gives it:

- `nmstyle`: the house style (the bundled TeX Gyre fonts, the colours of the deck's _brand.yml, `label()`, `Frame`
  with `inv()` and `scale`, `normal_pdf`);
- `nmnet`: `Net` (units in layers; weights, activations, forward and backward sweeps) and `unit_diagram`;
- `nmpix`: `PixelGrid`, `colour_for`, `conv2d`, `maxpool`;
- `nmfield`: `arrows` and `streams` for a 2-D flow in a `Frame`, `integrate`, `trajectory`, `fixed_point`;
- `nmprf`: population receptive field primitives (`VisualField`, `HeightSurface`, `FeatureStack`, `TracePanel`,
  `Dial`, `Bars`, `clip_size`, the numpy fields and colour ramps).

The designs of nmnet, nmpix and nmfield follow scenes from 3Blue1Brown's videos (github.com/3b1b/videos), used as
storyboards only; the code is written for Manim Community and each clip's docstring names the scene it follows.
Manim Community 0.22 with Pillow below 11.3 (`pip install lecturekit[clips]`).
"""
from pathlib import Path  # noqa: F401  (re-exported for kit.py shims)

from .nmstyle import *  # noqa: F401,F403
from .nmnet import *  # noqa: F401,F403
from .nmpix import *  # noqa: F401,F403
from .nmfield import *  # noqa: F401,F403
from .nmprf import *  # noqa: F401,F403
