"""The shared Manim kit (lecturekit.manim) for this deck's clips: `from kit import *` in every clip.

HERE is this anim/ folder, DATA the deck's assets/data/; the kit's modules come from the installed lecturekit,
so the deck carries no copy of the style.
"""
from pathlib import Path
from lecturekit.manim import *  # noqa: F401,F403

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / 'assets' / 'data'
