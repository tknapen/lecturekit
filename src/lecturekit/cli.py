"""`lk`: the lecturekit command.

    lk new <dir>            scaffold a project (vendors the Quarto extension; --manim8 adds a clips workspace)
    lk build [dir]          render live deck and study PDF, print the timing plan
    lk clips [deck]         render kit scenes and manim8 projects into assets/clips and write clips.json
    lk clips adopt <mp4>    copy an MP4 made elsewhere into assets/clips and write its entry (--name, --stops)
    lk theme [dir]          write tokens.tex, tokens.css, tokens.py (and the bridged manim8 styles)
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
    from .scaffold import create_manim8_workspace, create_project
    dest = Path(a.dir)
    if a.vendor_only:
        vendor_extension(dest, force=a.force)
        print(f"extension {extension_version()} vendored into {dest / '_extensions' / 'lecturekit'}")
        return 0
    if a.manim8 and (dest / "_quarto.yml").exists() and not a.force:
        print(f"adding a manim8 workspace to the project in {dest}")
    else:
        create_project(dest, title=a.title, force=a.force, budget=a.budget)
        print(f"project created in {dest}")
    if a.manim8:
        try:
            for line in create_manim8_workspace(dest):
                print(f"  {line}")
        except (RuntimeError, ValueError) as exc:
            print(f"lk new --manim8: {exc}", file=sys.stderr)
            return 1
    print(f"  next: cd {dest} && lk build")
    return 0


def cmd_build(a: argparse.Namespace) -> int:
    from .build import build
    return build(Path(a.dir) if a.dir else None, to=a.to, profile=a.profile, targets=a.targets or None,
                 quiet=a.quiet, strict=a.strict)


def cmd_clips(a: argparse.Namespace) -> int:
    from .clips import ClipError, clip_mode, index_path, run_clips
    deck = Path(a.dir) if a.dir else Path.cwd()
    try:
        mode = clip_mode(a.mode)
    except ClipError as exc:
        print(f"lk clips: {exc}", file=sys.stderr)
        return 2
    index, failures = run_clips(deck, only=a.only or None, size=a.size, crop=a.crop, mode=mode,
                                stills=a.still, revisions=a.revision, profile=a.profile, sync=not a.no_sync,
                                no_cache=a.no_cache)
    print(f"{len(index)} clip(s) in {index_path(deck, mode)}")
    if failures:
        print(f"{len(failures)} failed:", file=sys.stderr)
        for f in failures:
            print(f"  {f.name} ({f.producer}): {f.reason}", file=sys.stderr)
        return 1
    return 0


def clips_adopt_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lk clips adopt",
        description="Copy an MP4 made elsewhere into the deck's clips folder (with its index first, by stream copy) "
                    "and write its clips.json entry: the frame count, the frame rate, a still of frame 0, of each "
                    "stop and of the last frame, and the rest around each stop, measured on the pixels.")
    p.add_argument("mp4", help="the video to adopt")
    p.add_argument("--name", required=True, help="the clip's name in clips.json (what clip= names)")
    p.add_argument("--deck", default=None, help="the deck folder (default: the current folder)")
    p.add_argument("--stops", nargs="+", default=[], metavar="S",
                   help="candidate stops, each a second of the video or ID=SECONDS, snapped to the nearest frame "
                        "(a bare second gets the id stop_1, stop_2, ...)")
    p.add_argument("--labels", nargs="+", default=[], metavar="L",
                   help="one label per stop, in the same order (plain text, 1 to 40 characters; default the id)")
    p.add_argument("--mode", choices=["light", "dark"],
                   help="the preset (default LECTUREKIT_MODE, else light); dark writes assets/clips/dark/")
    p.add_argument("--crop", action="store_true",
                   help="crop to the content's bounding box against the slide colour (re-encodes)")
    p.add_argument("--size", metavar="WxH", help="scale to this size (re-encodes as H.264)")
    return p


def cmd_clips_adopt(argv: list[str]) -> int:
    from .clips import ClipError, adopt, clip_mode, index_path
    a = clips_adopt_parser().parse_args(argv)
    deck = Path(a.deck) if a.deck else Path.cwd()
    try:
        mode = clip_mode(a.mode)
        rec = adopt(deck, Path(a.mp4), a.name, stops=a.stops, labels=a.labels, mode=mode, crop=a.crop, size=a.size)
    except ClipError as exc:
        print(f"lk clips adopt: {exc}", file=sys.stderr)
        return 1
    stops = ", ".join(f"{s['id']} at frame {s['frame']} ({s['pts']:g} s, rest {s['rest_before']}+{s['rest_after']})"
                      for s in rec.stops or []) or "no stops"
    print(f"{a.name}: {rec.width}x{rec.height}, {rec.frames} frames at {rec.fps:g} fps; {stops}")
    print(f"  {rec.video} in {index_path(deck, mode)}")
    return 0


def cmd_theme(a: argparse.Namespace) -> int:
    from .theme import write_tokens
    project = Path(a.dir) if a.dir else find_project()
    try:
        written = write_tokens(project, brand=Path(a.brand) if a.brand else None, mode=a.mode,
                               manim8_version=a.manim8)
    except ValueError as exc:
        print(f"lk theme: {exc}", file=sys.stderr)
        return 1
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
    # a wheel carries no docs: point at the ones of this version's tag
    print(f"https://github.com/tknapen/lecturekit/tree/v{__version__}/docs")
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
    p.add_argument("--budget", type=int, default=45, metavar="MIN", help="the deck's budget in minutes (45)")
    p.add_argument("--manim8", action="store_true",
                   help="also make clips/ a manim8 workspace: a family, the bridged styles and a starter project")
    p.set_defaults(fn=cmd_new)

    p = sub.add_parser("build", help="render with quarto")
    p.add_argument("dir", nargs="?")
    p.add_argument("--to", choices=["live", "study"], help="one output only")
    p.add_argument("--profile", help="a quarto profile, e.g. dark")
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--strict", action="store_true",
                   help="fail on the filters' warnings too (a dark build that plays a paper clip, for one)")
    p.add_argument("targets", nargs="*", help="specific .qmd files")
    p.set_defaults(fn=cmd_build)

    p = sub.add_parser("clips", help="render clips and write clips.json (lk clips adopt <mp4>: bring one in)",
                       epilog="lk clips adopt <mp4> --name NAME [--stops S ...] [--labels L ...] [--mode dark] "
                              "copies an MP4 made elsewhere in; lk clips adopt --help says more")
    p.add_argument("dir", nargs="?", help="the deck folder (default: the current folder)")
    p.add_argument("--only", nargs="+", action="extend", metavar="NAME",
                   help="clip names (- and _ are the same); repeatable, and one --only takes several")
    p.add_argument("--size", default=None, help="kit render size, WxH (1280x720; the kit reads NM_CLIP_SIZE); "
                   "a manim8 clip renders at its project's output, and lk clips warns when that differs")
    p.add_argument("--crop", action="store_true", help="crop videos and stills to the content's bounding box")
    p.add_argument("--mode", choices=["light", "dark"], help="the preset (default LECTUREKIT_MODE, else light); "
                   "dark writes assets/clips/dark/")
    p.add_argument("--still", action="append", metavar="CLIP=ID",
                   help="the still of a clip: a manim8 checkpoint id, or a second of the clip (repeatable)")
    p.add_argument("--revision", action="append", metavar="[CLIP=]REV",
                   help="render a manim8 revision (rev_0002) instead of the working copy (repeatable)")
    p.add_argument("--profile", default="final", help="manim8 quality profile (final)")
    p.add_argument("--no-sync", action="store_true",
                   help="do not build a missing manim8 family environment (scianim family env sync)")
    p.add_argument("--no-cache", action="store_true",
                   help="render manim8 projects even when manim8's cache holds the job (kit scenes always render)")
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

    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:2] == ["clips", "adopt"]:   # `lk clips [deck]` takes a folder; `lk clips adopt` is its own command
        return cmd_clips_adopt(argv[2:])
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
