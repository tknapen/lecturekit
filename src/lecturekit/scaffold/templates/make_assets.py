#!/usr/bin/env python3
"""Figures for this deck, from the numbers in assets/data, on lecturekit.tikz.

Run by the build (pre-render) and by hand: `python make_assets.py`.
Every figure names colours (nmConcept) and styles (nm/box); none holds a value
that a simulation did not write. Draw at display size: 1 cm here is 80 px live.
"""
from pathlib import Path

from lecturekit.tikz import write_tikz

FIG = Path("assets/figures")
DATA = Path("assets/data")


def example():
    body = r"""
  \node[nm/box] (a) {question};
  \node[nm/box, nm/concept, right=1.2cm of a] (b) {model};
  \node[nm/box, nm/anchor, right=1.2cm of b] (c) {prediction};
  \draw[nm/arrow] (a) -- (b);
  \draw[nm/arrow] (b) -- (c);
  \node[nm/muted, below=0.3cm of b] {drawn at display size: 1 cm here is 80 px in the live deck};
"""
    write_tikz(FIG / "example.tikz", body, options="node distance=0.6cm",
               comment="example figure written by make_assets.py; replace it")


if __name__ == "__main__":
    example()
