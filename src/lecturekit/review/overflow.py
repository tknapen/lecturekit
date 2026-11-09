"""`lk review overflow`: the frames of the study PDF whose content runs past the page.

    lk review overflow slides.log          # the Beamer log beside the source (the format keeps it)
    lk review overflow .                   # a deck directory: finds slides.log and slides.tex

Reads Beamer's overfull-vbox warnings and maps each to its frame title through the kept LaTeX source (slides.tex
beside the log), largest first. Missing characters (a font without the glyph) and undefined colours (a token
missing from _brand.yml) are listed too.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def frames_of(tex: Path) -> list[tuple[int, int, str]]:
    frames = []
    title, start = None, None
    for i, line in enumerate(tex.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        m = re.match(r"\\begin\{frame\}(?:\[[^\]]*\])?\{(.*)", line)
        if m:
            title, start = m.group(1).rstrip("}"), i
        if line.startswith("\\end{frame}") and start:
            frames.append((start, i, title or "(untitled)"))
            start = None
    return frames


def report(target: Path, min_pt: float = 1.0) -> int:
    if target.is_dir():
        logs = sorted(target.glob("*.log"))
        log = next((l for l in logs if l.stem == "slides"), logs[0] if logs else None)
        if log is None:
            print(f"no .log in {target} (the Beamer format keeps it beside the source)")
            return 2
    else:
        log = target
    tex = log.with_suffix(".tex")
    frames = frames_of(tex) if tex.exists() else []
    text = log.read_text(encoding="utf-8", errors="replace")
    hits: dict[str, float] = {}
    for m in re.finditer(r"Overfull \\vbox \(([\d.]+)pt too high\) (?:has occurred while \\output is active|detected at line (\d+))", text):
        pts = float(m.group(1))
        if pts < min_pt:
            continue
        ln = int(m.group(2)) if m.group(2) else None
        name = f"(line {ln})" if ln else "(output routine)"
        if ln:
            for s, e, t in frames:
                if s <= ln <= e + 1:
                    name = t
                    break
        hits[name] = max(hits.get(name, 0), pts)
    for t, p in sorted(hits.items(), key=lambda kv: -kv[1]):
        print(f"{p:7.1f} pt  {t}")
    other = 0
    for line in text.splitlines():
        if "Missing character" in line or "Undefined color" in line:
            other += 1
            print(f"  {line.strip()}")
    print(f"{len(hits)} frame(s) overflow" if hits else "no overfull frames", f"; {other} other warning(s)" if other else "")
    return 1 if (hits or other) else 0


def main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="lk review overflow", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", type=Path, nargs="?", default=Path("."), help="a .log file or a deck directory")
    ap.add_argument("--min", type=float, default=1.0, help="ignore overfull boxes below this many pt")
    a = ap.parse_args(argv)
    return report(a.target, a.min)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
