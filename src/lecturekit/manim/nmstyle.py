"""House style for Manim clips, read from `_brand.yml`.

Every colour is a token; a clip refers to `INK`, `CONCEPT`, `GAUSS` and never
to a hex value. `apply(scene)` sets the background and the default font.
"""

from __future__ import annotations

from .. import tokens as _T

_t = _T.tokens()

# surfaces and text
PAPER = _t.colors.get("paper", "#F3F2EE")
SLIDE = _t.colors.get("slide", "#FFFFFF")
INK = _t.colors.get("ink", "#202B33")
MUTED = _t.colors.get("muted", "#566573")
HAIRLINE = _t.colors.get("hairline", "#C8C3BA")
# roles
CONCEPT = _t.colors.get("concept", "#175B8E")
CAVEAT = _t.colors.get("caveat", "#A33A32")
EXAMPLE = _t.colors.get("example", "#956000")
ANCHOR = _t.colors.get("anchor", "#006C65")
QUESTION = _t.colors.get("question", "#70508C")
# marks
INPUT = _t.colors.get("input", "#0072B2")
STATE = _t.colors.get("state", "#007F73")
UPDATE = _t.colors.get("update", "#C45A00")
CONTEXT = _t.colors.get("context", "#7A5195")

COLORS = dict(_t.colors)

BODY_FONT = _t.base_font or "TeX Gyre Heros"
HEADING_FONT = _t.heading_font or BODY_FONT

#: the frame the kit renders at; `lk clips` crops to content afterwards
FRAME = (1920, 1080)
STROKE = 3.0
FONT_SIZE = 32


def token(name: str) -> str:
    """A project token by name (`token("gauss")`)."""
    return COLORS[name]


def apply(scene) -> None:
    """Background from the brand, body font as Manim's default."""
    scene.camera.background_color = SLIDE
    try:
        from manim import Text  # type: ignore
        Text.set_default(font=BODY_FONT, color=INK)
    except Exception:  # pragma: no cover
        pass


__all__ = ["PAPER", "SLIDE", "INK", "MUTED", "HAIRLINE", "CONCEPT", "CAVEAT", "EXAMPLE", "ANCHOR",
           "QUESTION", "INPUT", "STATE", "UPDATE", "CONTEXT", "COLORS", "BODY_FONT", "HEADING_FONT",
           "FRAME", "STROKE", "FONT_SIZE", "token", "apply"]
