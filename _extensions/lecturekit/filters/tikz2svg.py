#!/usr/bin/env python3
"""Convert a one-page figure PDF to SVG (text as paths) or PNG, sized for the live slide.

Used by filters/tikz.lua. The scale maps PDF points to browser pixels so that a
figure keeps the proportion it has on the study page: the Beamer page is
453.54 pt wide and the live slide 1280 px, so 2.822 px per pt. Tries PyMuPDF
first, then pdftocairo, then dvisvgm (both without the px sizing).

    tikz2svg.py input.pdf output.svg|output.png [--scale PX_PER_PT]
"""
import re
import shutil
import subprocess
import sys

SCALE = 1280 / 453.54


def with_pymupdf(src: str, dst: str, scale: float) -> bool:
    try:
        import pymupdf  # type: ignore
    except ImportError:
        try:
            import fitz as pymupdf  # type: ignore
        except ImportError:
            return False
    doc = pymupdf.open(src)
    page = doc[0]
    if dst.lower().endswith(".svg"):
        svg = page.get_svg_image(text_as_path=True)
        w_px, h_px = page.rect.width * scale, page.rect.height * scale
        # the root width and height in pixels; the viewBox keeps the drawing scalable
        svg = re.sub(r'<svg([^>]*?)\swidth="[^"]*"', r'<svg\1 width="%.2f"' % w_px, svg, count=1)
        svg = re.sub(r'<svg([^>]*?)\sheight="[^"]*"', r'<svg\1 height="%.2f"' % h_px, svg, count=1)
        with open(dst, "w", encoding="utf-8") as fh:
            fh.write(svg)
    else:
        # two device pixels per CSS pixel keeps a PNG crisp on high-density displays
        pix = page.get_pixmap(matrix=pymupdf.Matrix(scale * 2, scale * 2), alpha=True)
        pix.save(dst)
    print("%.0f %.0f" % (page.rect.width * scale, page.rect.height * scale))
    return True


def with_pdftocairo(src: str, dst: str) -> bool:
    if not shutil.which("pdftocairo"):
        return False
    flag = "-svg" if dst.lower().endswith(".svg") else "-png"
    r = subprocess.run(["pdftocairo", flag, "-f", "1", "-l", "1", src, dst], capture_output=True)
    return r.returncode == 0


def with_dvisvgm(src: str, dst: str) -> bool:
    if not shutil.which("dvisvgm") or not dst.lower().endswith(".svg"):
        return False
    r = subprocess.run(["dvisvgm", "--pdf", "--no-fonts", "-o", dst, src], capture_output=True)
    return r.returncode == 0


def main() -> int:
    args = sys.argv[1:]
    scale = SCALE
    if "--scale" in args:
        i = args.index("--scale")
        scale = float(args[i + 1])
        del args[i:i + 2]
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    src, dst = args
    try:
        if with_pymupdf(src, dst, scale):
            return 0
    except Exception as exc:  # noqa: BLE001
        print(f"tikz2svg: pymupdf failed: {exc}", file=sys.stderr)
    for fn in (with_pdftocairo, with_dvisvgm):
        try:
            if fn(src, dst):
                return 0
        except Exception as exc:  # noqa: BLE001
            print(f"tikz2svg: {fn.__name__} failed: {exc}", file=sys.stderr)
    print("tikz2svg: no converter available (install pymupdf, poppler or dvisvgm)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
