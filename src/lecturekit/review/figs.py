"""`lk review figs`: a deck's TikZ figures before they enter a slide.

    lk review figs .                         # every assets/figures/*.tex of the deck
    lk review figs . lineage shelf           # some, by name
    lk review figs . --brand _brand-dark.yml --mode dark

Each figure is compiled standalone with the brand's colours and fonts, as the build does, and written as a PNG to
`review/figs/` at the size the live deck shows (88 px per cm); its natural size in cm is printed, which is what
`\\nmfigureh` compares its cap with. A figure wider than the slide (14 cm) or taller than its slot is scaled down on
the page; one that is smaller stays small. Failures print the first error of the log.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from ..project import extension_source
from ..theme import find_brand, load_brand

PX_PER_CM = 88.0


def standalone_source(tikz: Path, brand: Path | None, mode: str) -> str:
    ext = extension_source()
    preamble = (ext / "beamer" / "figure-preamble.tex").read_text(encoding="utf-8")
    styles = (ext / "beamer" / "tikz-styles.tex").read_text(encoding="utf-8")
    brand_path = brand or find_brand(tikz.parent)
    tokens = load_brand(brand_path, mode=mode) if brand_path else None
    colors = "\n".join(l for l in tokens.latex().splitlines() if l.startswith("\\definecolor")) if tokens else ""
    fonts = "\n".join(tokens.fontspec_lines()) if tokens else ""
    return "\n".join([
        "\\documentclass[12pt,tikz,border=1pt]{standalone}",
        "\\usepackage{amsmath}",
        "\\usepackage{fontspec}",
        "\\usepackage{unicode-math}",
        fonts,
        colors,
        "\\usepackage{tikz}",
        styles,
        preamble,
        "\\begin{document}",
        tikz.read_text(encoding="utf-8"),
        "\\end{document}",
    ])


def compile_figure(tikz: Path, out_png: Path, brand: Path | None, mode: str) -> tuple[str | None, tuple[float, float] | None]:
    """Returns (error, (width_cm, height_cm))."""
    src = standalone_source(tikz, brand, mode)
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        (tdp / "fig.tex").write_text(src, encoding="utf-8")
        r = subprocess.run(["xelatex", "-interaction=batchmode", "-halt-on-error", "fig.tex"], cwd=td, capture_output=True, text=True)
        pdf = tdp / "fig.pdf"
        if r.returncode != 0 or not pdf.exists():
            log = (tdp / "fig.log").read_text(encoding="utf-8", errors="replace") if (tdp / "fig.log").exists() else ""
            err = next((l for l in log.splitlines() if l.startswith("!")), "compilation failed")
            return err, None
        import pymupdf
        page = pymupdf.open(pdf)[0]
        zoom = PX_PER_CM / (72 / 2.54)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False).save(out_png)
        return None, (page.rect.width / 72 * 2.54, page.rect.height / 72 * 2.54)


def preview(deck: Path, names: list[str] | None = None, brand: Path | None = None, mode: str = "light", out: Path | None = None) -> int:
    fig_dir = deck / "assets" / "figures"
    if names:
        figs = [fig_dir / (n if n.endswith((".tex", ".tikz")) else f"{n}.tex") for n in names]
    else:
        figs = sorted(list(fig_dir.glob("*.tex")) + list(fig_dir.glob("*.tikz")))
    out_dir = out or deck / "review" / "figs"
    if not figs:
        print(f"no figure files in {fig_dir}")
        return 0
    failures = 0
    for f in figs:
        err, size = compile_figure(f, out_dir / (f.stem + ".png"), brand, mode)
        if err:
            failures += 1
            print(f"  FAIL {f.name}: {err}")
        else:
            w, h = size
            note = "  (wider than the 14 cm slide: scaled down on the page)" if w > 14.0 else ""
            print(f"  ok   {f.name}: {w:.1f} x {h:.1f} cm  ->  {out_dir / (f.stem + '.png')}{note}")
    print(f"{len(figs) - failures} of {len(figs)} figures in {out_dir}")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="lk review figs", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck", type=Path, nargs="?", default=Path("."))
    ap.add_argument("names", nargs="*", help="figure names (default: all)")
    ap.add_argument("--brand", type=Path, default=None)
    ap.add_argument("--mode", default="light", choices=["light", "dark"])
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    return preview(a.deck, a.names or None, a.brand, a.mode, a.out)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
