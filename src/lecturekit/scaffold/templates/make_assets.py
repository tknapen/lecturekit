#!/usr/bin/env python3
"""TikZ figures for this deck, from the numbers in assets/data, on the lecturekit TikZ kit.

Run by the build (pre-render in _quarto.yml) and by hand: `python make_assets.py [name ...]`.
Every figure names colours (nmConcept) and never a value a simulation did not write. Draw at the size the figure
should appear: 12 to 13 cm wide for a full-width slide, about 4.2 cm high above two bullets.
"""
import sys
from pathlib import Path

from lecturekit.tikz import *       # colour names, Panel, stack, box, writer

HERE = Path(__file__).resolve().parent
write = writer(HERE / 'assets' / 'figures')
DATA = HERE / 'assets' / 'data'


def example():
    """A data-to-page panel with axes and one curve: replace it with the deck's first figure."""
    L = []
    P = Panel(0.9, 0.6, 11.5, 3.2, (0, 60), (0, 1))
    L.extend(P.axes(u_ticks=(0, 30, 60), v_ticks=(0, 1), u_label='time (s)', v_label='response'))
    t = np.linspace(0, 60, 121)
    y = np.exp(-((t - 20) / 6) ** 2) + 0.8 * np.exp(-((t - 45) / 6) ** 2)
    L.append(P.path(list(zip(t, y)), f'{BLUE},line width=1pt'))
    L.append(f'\\node[anchor=south west,text={MUTED},{SMALL}] at {P.pt(1, 0.88)} {{drawn at display size: 12 by 4 cm}};')
    write('example', L)


ALL = {'example': example}
if __name__ == '__main__':
    names = sys.argv[1:] or list(ALL)
    for n in names: ALL[n]()
