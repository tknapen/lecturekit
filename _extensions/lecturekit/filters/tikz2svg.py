#!/usr/bin/env python3
"""Convert the first page of a PDF to SVG.

Used by filters/tikz.lua. Tries PyMuPDF first (text as paths, so the SVG
needs no fonts), then pdftocairo, then dvisvgm. Exits non-zero if none work.
"""
import shutil
import subprocess
import sys


def with_pymupdf(src: str, dst: str) -> bool:
    try:
        import pymupdf  # type: ignore
    except ImportError:
        try:
            import fitz as pymupdf  # type: ignore
        except ImportError:
            return False
    doc = pymupdf.open(src)
    page = doc[0]
    svg = page.get_svg_image(text_as_path=True)
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(svg)
    return True


def with_pdftocairo(src: str, dst: str) -> bool:
    if not shutil.which("pdftocairo"):
        return False
    r = subprocess.run(["pdftocairo", "-svg", "-f", "1", "-l", "1", src, dst], capture_output=True)
    return r.returncode == 0


def with_dvisvgm(src: str, dst: str) -> bool:
    if not shutil.which("dvisvgm"):
        return False
    r = subprocess.run(["dvisvgm", "--pdf", "--no-fonts", "-o", dst, src], capture_output=True)
    return r.returncode == 0


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: tikz2svg.py in.pdf out.svg", file=sys.stderr)
        return 2
    src, dst = sys.argv[1], sys.argv[2]
    for fn in (with_pymupdf, with_pdftocairo, with_dvisvgm):
        try:
            if fn(src, dst):
                return 0
        except Exception as exc:  # noqa: BLE001
            print(f"tikz2svg: {fn.__name__} failed: {exc}", file=sys.stderr)
    print("tikz2svg: no converter available (install pymupdf, poppler or dvisvgm)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
