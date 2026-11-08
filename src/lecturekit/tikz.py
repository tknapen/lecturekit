"""The TikZ kit (stand-in).

The course project's `tikzkit.py`, the figure library behind `make_assets.py`,
is being extracted into this module. Until it lands, this file provides the
pieces a `make_assets.py` needs to produce figures that the build accepts:

* the colour tokens of the active brand, by name (`T.INK`, `T.CONCEPT`,
  `rgb("gauss")`), so that a restyle regenerates the figures;
* :func:`write_tikz`, which writes a `.tikz` file that the deck includes with
  `![](assets/figures/name.tikz){height=4.2cm}`;
* :func:`load_data`, which reads the JSON summaries a simulation wrote to
  `assets/data/`, so that every number in a figure traces to a script;
* a few helpers for sizes, so that figures are drawn at display size
  (1 cm of the Beamer frame is 80 px of the live deck).

Figures name colours (`nmConcept`) and styles (`nm/box`); they never contain
hex values. The styles live in the extension's `beamer/figure-preamble.tex`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from . import tokens as T
from .tokens import rgb  # noqa: F401  (re-exported for make_assets.py)

PX_PER_CM = 80.0
PT_PER_CM = 28.4528

#: heights that leave room for text beside or above the figure (see docs/LAYOUT.md)
FIGURE_HEIGHTS = {
    "full": "5.6cm",        # a figure alone under the title
    "one_bullet": "4.9cm",  # one single-line bullet above
    "two_bullets": "4.2cm", # two single-line bullets above
    "column": "4.4cm",      # beside a column of text
}


def color(name: str) -> str:
    """The LaTeX colour name of a token: `color("concept") == "nmConcept"`."""
    from .theme import camel
    return f"nm{camel(name)}"


def load_data(path: str | Path) -> Any:
    """A JSON summary written by a simulation (`assets/data/*.json`)."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_tikz(path: str | Path, body: str, options: str = "", comment: str | None = None) -> Path:
    """Write a `.tikz` file holding one tikzpicture.

    `body` is the picture's content; `options` go into `\\begin{tikzpicture}[...]`.
    The file is included by the deck and compiled by the extension's TikZ
    filter with the brand's colours and fonts.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if comment:
        lines.append("% " + comment.replace("\n", "\n% "))
    lines.append(f"\\begin{{tikzpicture}}[{options}]")
    lines.append(body.rstrip("\n"))
    lines.append("\\end{tikzpicture}")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def escape(text: str) -> str:
    """Escape the characters that break a TikZ label (`%` above all)."""
    return (text.replace("\\", "\\textbackslash{}").replace("%", "\\%").replace("&", "\\&")
            .replace("#", "\\#").replace("_", "\\_"))


def polyline(points: Iterable[tuple[float, float]], fmt: str = "{:.3f}") -> str:
    """`(x,y) -- (x,y) -- ...` for a `\\draw` of sampled data."""
    return " -- ".join(f"({fmt.format(x)},{fmt.format(y)})" for x, y in points)


def scale_to(values: Iterable[float], lo: float, hi: float, out_lo: float, out_hi: float) -> list[float]:
    """Map data values from [lo, hi] to figure coordinates [out_lo, out_hi]."""
    span = (hi - lo) or 1.0
    return [out_lo + (v - lo) / span * (out_hi - out_lo) for v in values]


__all__ = ["T", "rgb", "color", "load_data", "write_tikz", "escape", "polyline", "scale_to",
           "FIGURE_HEIGHTS", "PX_PER_CM", "PT_PER_CM"]
