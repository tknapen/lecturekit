"""Colour tokens of the nearest `_brand.yml`, as module attributes.

    from lecturekit.tokens import INK, CONCEPT, GAUSS, rgb

reads `_brand.yml` from the current directory upwards (or the file named by
`LECTUREKIT_BRAND`; `LECTUREKIT_MODE=dark` selects the dark side of a unified
brand file) when the first attribute is asked for. Figure and clip scripts
therefore follow a restyle without being edited.
"""

from __future__ import annotations

import os
from typing import Any

from .theme import Tokens, constant, load_brand

_tokens: Tokens | None = None


def tokens() -> Tokens:
    global _tokens
    if _tokens is None:
        _tokens = load_brand(mode=os.environ.get("LECTUREKIT_MODE", "light"))
    return _tokens


def reload(path: str | None = None, mode: str | None = None) -> Tokens:
    global _tokens
    _tokens = load_brand(path, mode=mode or os.environ.get("LECTUREKIT_MODE", "light"))
    return _tokens


def rgb(name: str) -> tuple[float, float, float]:
    """0 to 1 RGB triple of a token, for matplotlib and Manim."""
    h = tokens().colors[name].lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def __getattr__(item: str) -> Any:
    if item.startswith("_"):
        raise AttributeError(item)
    t = tokens()
    for name, value in t.colors.items():
        if constant(name) == item:
            return value
    if item == "COLORS":
        return dict(t.colors)
    if item in ("BASE_FONT", "HEADING_FONT", "MONO_FONT"):
        return {"BASE_FONT": t.base_font, "HEADING_FONT": t.heading_font, "MONO_FONT": t.mono_font}[item]
    raise AttributeError(f"no token {item!r} in {t.path}")
