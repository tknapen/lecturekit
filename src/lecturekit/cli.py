"""`lk`: the lecturekit command.

    lk new <dir>            scaffold a project (vendors the Quarto extension)
    lk build [dir]          render live deck and study PDF, print the timing plan
    lk clips [dir]          render clips into assets/clips and write clips.json
    lk theme [dir]          write tokens.tex, tokens.css, tokens.py (and a manim8 style)
    lk review <tool> ...    shoot | frags | measure | contrast | overflow | figs
    lk docs                 where the documentation is
    lk version
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import __version__
from .project import PACKAGE_DIR, extension_version, find_project, vendor_extension


def cmd_new(a: argparse.Namespace) -> int:
    from .scaffold import create_project
    dest = Path(a.dir)
    if a.vendor_only:
        vendor_extension(dest, force=a.force)
        print(f"extension {extension_version()} vendored into {dest / '_extensions' / 'lecturekit'}")
        return 0
    create_project(dest, title=a.title, force=a.force)
    print(f"project created in {dest}\n  next: cd {dest} && lk build")
    return 0


def cmd_build(a: argparse.Namespace) -> int:
    from .build import build
    return build(Path(a.dir) if a.dir else None, to=a.to, profile=a.profile, targets=a.targets or None,
                 quiet=a.quiet)


def cmd_clips(a: argparse.Namespace) -> int:
    from .clips import render_all
    deck = Path(a.dir) if a.dir else Path.cwd()
    index = render_all(deck, only=a.only or None, quality=a.quality)
    print(f"{len(index)} clip(s) in {deck / 'assets' / 'clips' / 'clips.json'}")
    return 0


def cmd_theme(a: argparse.Namespace) -> int:
    from .theme import write_tokens
    project = Path(a.dir) if a.dir else find_project()
    written = write_tokens(project, brand=Path(a.brand) if a.brand else None, mode=a.mode,
                           manim8_version=a.manim8)
    for p in written:
        print(f"  {p}")
    return 0


def cmd_review(a: argparse.Namespace) -> int:
    tool = a.tool
    rest = a.rest
    if tool == "shoot":
        from .review.shoot import main
    elif tool == "frags":
        from .review.frags import main
    elif tool == "measure":
        from .review.measure import main
    elif tool == "contrast":
        from .review.contrast import main
    elif tool == "overflow":
        from .review.overflow import main
    elif tool == "figs":
        from .review.figs import main
    else:
        print(f"unknown review tool {tool!r}; one of shoot, frags, measure, contrast, overflow, figs", file=sys.stderr)
        return 2
    return main(rest)


def cmd_docs(a: argparse.Namespace) -> int:
    candidates = [PACKAGE_DIR / "docs", PACKAGE_DIR.parents[1] / "docs"]
    for c in candidates:
        if c.exists():
            print(c)
            for p in sorted(c.glob("*.md")):
                print(f"  {p.name}")
            return 0
    print("https://github.com/tknapen/lecturekit/tree/main/docs")
    return 0


def cmd_version(a: argparse.Namespace) -> int:
    print(f"lecturekit {__version__}, extension {extension_version()}, quarto {shutil.which('quarto') or 'not found'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="lk", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new", help="scaffold a project")
    p.add_argument("dir")
    p.add_argument("--title", default="Untitled lecture")
    p.add_argument("--vendor-only", action="store_true", help="only copy the extension into an existing project")
    p.add_argument("--force", action="store_true", help="overwrite an existing vendored extension")
    p.set_defaults(fn=cmd_new)

    p = sub.add_parser("build", help="render with quarto")
    p.add_argument("dir", nargs="?")
    p.add_argument("--to", choices=["live", "study"], help="one output only")
    p.add_argument("--profile", help="a quarto profile, e.g. dark")
    p.add_argument("--quiet", action="store_true")
    p.add_argument("targets", nargs="*", help="specific .qmd files")
    p.set_defaults(fn=cmd_build)

    p = sub.add_parser("clips", help="render clips and write clips.json")
    p.add_argument("dir", nargs="?")
    p.add_argument("--only", nargs="*", help="clip names")
    p.add_argument("--quality", default="h", choices=["l", "m", "h", "p", "k"], help="manim quality flag")
    p.set_defaults(fn=cmd_clips)

    p = sub.add_parser("theme", help="write token files from _brand.yml")
    p.add_argument("dir", nargs="?")
    p.add_argument("--brand", help="brand file (default _brand.yml in the project)")
    p.add_argument("--mode", default="light", choices=["light", "dark"])
    p.add_argument("--manim8", metavar="VERSION", help="also write a manim8 style version, e.g. 0.1.0")
    p.set_defaults(fn=cmd_theme)

    p = sub.add_parser("review", help="review tools")
    p.add_argument("tool")
    p.add_argument("rest", nargs=argparse.REMAINDER)
    p.set_defaults(fn=cmd_review)

    p = sub.add_parser("docs", help="where the documentation is")
    p.set_defaults(fn=cmd_docs)

    p = sub.add_parser("version")
    p.set_defaults(fn=cmd_version)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
