"""`lk review contrast`: WCAG contrast of a brand's colours on its surfaces.

    lk review contrast _brand.yml
    lk review contrast _brand-dark.yml --mode dark --aa-large

Every text colour (ink, muted, body, heading) and every role and mark colour
is checked against every surface (slide, paper). Text needs 4.5:1 (AA), the
eyebrow and large titles 3:1 (AA large). Failures are printed with the
nearest tint or shade of the same hue that passes, so that the restyle
episode can take the suggestion or argue with it.
"""

from __future__ import annotations

import colorsys
import sys
from pathlib import Path

from ..theme import load_brand

TEXT_NAMES = ("ink", "body", "muted", "heading", "foreground")
ROLE_NAMES = ("concept", "caveat", "example", "anchor", "question")
MARK_NAMES = ("input", "state", "update", "context")
SURFACES = ("slide", "paper", "background")

AA_TEXT = 4.5
AA_LARGE = 3.0


def _lin(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_: str) -> float:
    h = hex_.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def ratio(fg: str, bg: str) -> float:
    l1, l2 = luminance(fg), luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def _to_hex(r: float, g: float, b: float) -> str:
    return "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))


def suggest(fg: str, bg: str, target: float) -> str | None:
    """The same hue and saturation, lightness moved away from the surface until it passes."""
    h = fg.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    direction = 1 if luminance(bg) < 0.5 else -1
    for step in range(1, 101):
        l2 = min(1.0, max(0.0, ll + direction * step / 100))
        cand = _to_hex(*colorsys.hls_to_rgb(hh, l2, ss))
        if ratio(cand, bg) >= target:
            return cand
    return None


def check(brand_path: Path, mode: str = "light", large_ok_for_roles: bool = True) -> list[tuple[str, str, float, float, str | None]]:
    t = load_brand(brand_path, mode=mode)
    c = t.colors
    surfaces = [(s, c[s]) for s in SURFACES if s in c]
    seen = set()
    failures = []
    rows = []
    for name in list(TEXT_NAMES) + list(ROLE_NAMES) + list(MARK_NAMES):
        if name not in c or name in seen:
            continue
        seen.add(name)
        target = AA_TEXT if name in TEXT_NAMES else (AA_LARGE if large_ok_for_roles else AA_TEXT)
        for sname, shex in surfaces:
            if shex == c[name]:
                continue
            r = ratio(c[name], shex)
            ok = r >= target
            rows.append((name, sname, r, target, ok))
            if not ok:
                failures.append((name, sname, r, target, suggest(c[name], shex, target)))
    print(f"brand {t.name} ({mode}); AA text {AA_TEXT}:1, roles and marks {AA_LARGE if large_ok_for_roles else AA_TEXT}:1")
    for name, sname, r, target, ok in rows:
        mark = "ok  " if ok else "FAIL"
        print(f"  {mark} {name:9s} on {sname:10s} {r:5.2f}:1  (needs {target})")
    if failures:
        print("suggestions:")
        for name, sname, r, target, s in failures:
            print(f"  {name} on {sname}: {c[name]} -> {s or 'no tint of this hue passes'}")
    return failures


def main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="lk review contrast", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brand", type=Path, nargs="?", default=Path("_brand.yml"))
    ap.add_argument("--mode", default="light", choices=["light", "dark"])
    ap.add_argument("--strict", action="store_true", help="require 4.5:1 for roles and marks too")
    a = ap.parse_args(argv)
    failures = check(a.brand, a.mode, large_ok_for_roles=not a.strict)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
