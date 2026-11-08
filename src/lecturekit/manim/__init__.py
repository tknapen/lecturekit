"""The Manim kit (stand-in).

The course project's kit (`nmstyle`, `nmnet`, `nmpix`, `nmfield`, `nmprf`) is
being extracted into this package. Until it lands, :mod:`lecturekit.manim.nmstyle`
provides the part every clip needs: the brand's colours and fonts as Manim
constants, so that a clip rendered after a restyle follows the new palette.

A clip is a Manim scene in a deck's `anim/clip_<name>.py`:

    from lecturekit.manim import *

    class BarBold(Scene):
        still = "last"            # which frame becomes the study PDF's still
        def construct(self):
            ...

`lk clips` renders every such scene, crops the video to its content, writes
the still, and records the result in `assets/clips/clips.json`.
"""

from .nmstyle import *  # noqa: F401,F403
from .nmstyle import __all__ as _style_all

try:  # Manim is an optional dependency (`pip install lecturekit[clips]`)
    from manim import *  # type: ignore # noqa: F401,F403
    HAS_MANIM = True
except ImportError:  # pragma: no cover
    HAS_MANIM = False

__all__ = list(_style_all) + ["HAS_MANIM"]
