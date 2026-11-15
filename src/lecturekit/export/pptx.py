"""`lk export pptx`: a built live deck as a PowerPoint file that keeps its look, its reveals, its clips and notes.

    lk export pptx                          # the project found from here: its built live deck, slides.pptx beside it
    lk export pptx examples/features --profile dark
    lk export pptx _build/slides-live.html --out talk.pptx --video click --slides 3,5-7

Every slide at every reveal step becomes one PowerPoint slide: a full-bleed screenshot of the step (1280 by 720 CSS
px at --scale, clips hidden) on a slide of the page colour, with the clips placed on top in their content
rectangles. An ordinary clip that comes on stage is a movie that starts by itself (--video auto), or when clicked
(--video click), with frame 0 as its poster; one already on stage is a still of its last frame. A clip in parts is
one movie per part, cut frame-exactly, ending on its hold. --video still places stills only. The notes of each step
go to the slide's notes; the screenshot carries the slide's text as alt text. It reads the built deck and never
builds; docs/EXPORT.md says what carries over and what to test in PowerPoint before the talk.
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import sys
import tempfile
from pathlib import Path

from .plan import SLIDE_EMU, VIDEO_MODES, Movie, Still, emu, plan_slide
from .timing import timing_xml

EXTRA = "pip install 'lecturekit[export]' && playwright install chromium"


def checks(video: str, movies: int, parts: int = 0) -> list[str]:
    """What to try in PowerPoint before the talk (docs/EXPORT.md), for this file; `parts` counts the movies that are
    parts of a clip in parts."""
    out = ["the file opens without a repair prompt"]
    if movies:
        out.append("each movie starts by itself when its slide appears; a click on it pauses it" if video == "auto"
                   else "each movie starts when it is clicked; a second click pauses it")
        out.append("a movie that ends stays on its last frame, not its poster")
    if parts:
        out.append("the parts of a clip in parts join without a jump from slide to slide")
    return out + ["the notes show in Presenter View"]


def _n(count: int, word: str) -> str:
    return f"{count} {word}{'s' * (count != 1)}"


def _need() -> None:
    """One line naming the extra when a package the export needs is missing."""
    for mod, name in (("pptx", "python-pptx"), ("playwright", "playwright"), ("PIL", "pillow")):
        try:
            __import__(mod)
        except ImportError:
            raise SystemExit(f"lk export pptx: {name} is not installed: {EXTRA}") from None


def live_deck(project: Path, profile: str | None) -> Path:
    """The live deck `lk build` writes for a project: `output-file` of the lecturekit-revealjs format in the
    output folder of the profile (build.output_dir)."""
    import yaml

    from ..build import output_dir
    name = "slides-live.html"
    try:
        config = yaml.safe_load((project / "_quarto.yml").read_text(encoding="utf-8")) or {}
        fmt = ((config.get("format") or {}).get("lecturekit-revealjs") or {})
        name = fmt.get("output-file") or name
    except (OSError, AttributeError):
        pass
    return output_dir(project, profile) / name


def profiles(project: Path) -> list[str]:
    """The quarto profiles of a project: the names of its `_quarto-<profile>.yml` files."""
    return sorted(f.name[len("_quarto-"):-len(".yml")] for f in project.glob("_quarto-*.yml"))


def _build_cmd(project: Path, profile: str | None) -> str:
    return f"lk build {project} --to live" + (f" --profile {profile}" if profile else "")


def _output_of(folder: Path) -> tuple[Path, str | None] | None:
    """The project and profile whose build goes to `folder`, if `folder` is a project's output folder."""
    from ..build import output_dir
    from ..project import find_project
    try:
        project = find_project(folder)
    except FileNotFoundError:
        return None
    for prof in [None, *profiles(project)]:
        if output_dir(project, prof).resolve() == folder.resolve():
            return project, prof
    return None


def resolve(target: str | None, profile: str | None) -> tuple[Path, str | None, Path | None]:
    """The deck to export, the `lk build` command that writes it (None when it is not known) and its project."""
    from ..project import find_project
    path = Path(target) if target else None
    if path is not None and (target.endswith(".html") or (path.is_dir() and not (path / "_quarto.yml").exists())):
        if profile:
            raise SystemExit("lk export pptx: --profile chooses a project's build; give the project folder, "
                             f"not {'a deck file' if target.endswith('.html') else 'its build folder'}")
        folder = path.parent if target.endswith(".html") else path
        found = _output_of(folder) if folder.is_dir() else None
        if found is None:
            if not target.endswith(".html"):
                raise SystemExit(f"lk export pptx: {path} is neither a project folder (no _quarto.yml) nor the "
                                 "build folder of one; give a project folder or a built slides-live.html")
            return path, None, None
        project, prof = found
        deck = path if target.endswith(".html") else live_deck(project, prof)
        return deck, _build_cmd(project, prof), project
    try:
        project = find_project(path)
    except FileNotFoundError as exc:
        raise SystemExit(f"lk export pptx: {exc}; give a project folder or a built slides-live.html") from None
    if profile and not (project / f"_quarto-{profile}.yml").exists():
        have = profiles(project)
        raise SystemExit(f"lk export pptx: no _quarto-{profile}.yml in {project}; "
                         + (f"profiles here: {', '.join(have)}" if have else "it has no profiles"))
    return live_deck(project, profile), _build_cmd(project, profile), project


def stale(project: Path, deck: Path) -> list[str]:
    """The sources of a project (its .qmd files and _quarto*.yml, outside the build folders) newer than the deck."""
    built = deck.stat().st_mtime
    out = []
    for f in sorted([*project.glob("*.qmd"), *project.glob("_quarto*.yml")]):
        if f.stat().st_mtime > built:
            out.append(f.name)
    return out


# ------------------------------------------------------------------------ the PowerPoint file
def _reset_properties(prs, title: str, slides: int, notes: int, thumb: Path | None) -> None:
    """python-pptx's template carries the metadata of its author's machine (a Mac app name, a 4:3 format, its
    author): the export writes its own."""
    from .. import __version__
    now = dt.datetime.now(dt.UTC).replace(microsecond=0, tzinfo=None)
    cp = prs.core_properties
    cp.title, cp.author, cp.last_modified_by = title[:255], "", f"lecturekit {__version__}"
    cp.subject = cp.keywords = cp.category = cp.comments = ""
    cp.created = cp.modified = now
    cp.revision = 1
    app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
           'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
           f'<TotalTime>0</TotalTime><Application>lecturekit {__version__}</Application>'
           f'<PresentationFormat>Widescreen</PresentationFormat><Slides>{slides}</Slides><Notes>{notes}</Notes>'
           '</Properties>').encode()
    for rid, rel in list(prs.part.rels.items()):        # the template's Mac printer settings
        if rel.reltype.endswith("/printerSettings"):
            prs.part.drop_rel(rid)
    for part in prs.part.package.iter_parts():
        name = str(part.partname)
        if name == "/docProps/app.xml":
            part._blob = app
        elif name == "/docProps/thumbnail.jpeg" and thumb is not None:
            from PIL import Image
            with Image.open(thumb) as im:
                im = im.convert("RGB")
                im.thumbnail((256, 256))
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=85)
            part._blob = buf.getvalue()


def _alt(shape, text: str, name: str | None = None) -> None:
    c = shape._element.xpath("./*[1]/p:cNvPr")[0]
    if text:
        c.set("descr", text)
    if name:
        c.set("name", name)


def _widescreen(prs) -> None:
    """python-pptx's template is a 4:3 slide (10 inches wide): label the slide size as PowerPoint does for 16:9 (no
    `type`), and widen the master and its layouts to the 13.333 inch slide, so that a slide added in PowerPoint or a
    footer switched on there sits where PowerPoint's own widescreen master puts it."""
    from pptx.oxml.ns import qn
    prs.part._element.find(qn("p:sldSz")).attrib.pop("type", None)
    k = SLIDE_EMU[0] / 9144000
    for el in [prs.slide_master._element, *(layout._element for layout in prs.slide_layouts)]:
        for tag in ("a:off", "a:chOff"):
            for node in el.iter(qn(tag)):
                node.set("x", str(round(int(node.get("x")) * k)))
        for tag in ("a:ext", "a:chExt"):
            for node in el.iter(qn(tag)):
                node.set("cx", str(round(int(node.get("cx")) * k)))


def _notes_page(prs) -> None:
    """The slide picture of the notes page at 16:9, where PowerPoint's own widescreen notes master has it."""
    from pptx.enum.shapes import PP_PLACEHOLDER
    for sh in prs.notes_master.placeholders:
        if sh.placeholder_format.type == PP_PLACEHOLDER.SLIDE_IMAGE:
            sh.left, sh.top, sh.width, sh.height = 685800, 1143000, 5486400, 3086100


def write(steps_by_slide, plans, media, out: Path, video: str) -> dict:
    """Write the PowerPoint file; returns the counts."""
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.oxml import parse_xml
    prs = Presentation()
    prs.slide_width, prs.slide_height = SLIDE_EMU
    _widescreen(prs)
    blank = prs.slide_layouts[6]
    W, H = SLIDE_EMU
    counts = {"slides": 0, "movies": 0, "parts": 0, "stills": 0, "notes": 0}
    frames = [s.frame for plan in plans for shapes in plan for s in shapes if isinstance(s, Still)]
    frames += [s.poster for plan in plans for shapes in plan for s in shapes if isinstance(s, Movie)]
    stills = media.stills(frames)
    for steps, plan in zip(steps_by_slide, plans):
        for st, shapes in zip(steps, plan):
            sl = prs.slides.add_slide(blank)
            fill = sl.background.fill
            fill.solid()
            fill.fore_color.rgb = RGBColor(*st.colour)
            pic = sl.shapes.add_picture(str(st.shot), 0, 0, W, H)
            _alt(pic, st.alt, f"Slide {st.number}" + (f", step {st.f + 2}" if st.f >= 0 else ""))
            movies = []
            for s in shapes:
                x, y, w, h = emu(s.rect)
                if isinstance(s, Still):
                    p = sl.shapes.add_picture(str(stills[s.frame]), x, y, w, h)
                    _alt(p, s.label)
                    counts["stills"] += 1
                else:
                    m = sl.shapes.add_movie(str(media.movie(s.media)), x, y, w, h,
                                            poster_frame_image=str(stills[s.poster]), mime_type="video/mp4")
                    _alt(m, s.label)
                    movies.append((m.shape_id, media.duration_ms(s.media)))
                    counts["movies"] += 1
                    counts["parts"] += not s.media.whole
            if movies:
                el = sl._element
                el._remove_timing()
                el._insert_timing(parse_xml(timing_xml(movies, autoplay=video == "auto")))
            if st.notes:
                sl.notes_slide.notes_text_frame.text = st.notes
                counts["notes"] += 1
            counts["slides"] += 1
    if counts["notes"]:
        _notes_page(prs)
    first = steps_by_slide[0][0] if steps_by_slide and steps_by_slide[0] else None
    _reset_properties(prs, first.title if first else "", counts["slides"], counts["notes"],
                      first.shot if first else None)
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))
    return counts


# ------------------------------------------------------------------------ the command
def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lk export pptx",
        description="A built live deck as a PowerPoint file: each slide at each reveal step a picture, the clips "
                    "movies on top, the notes in the notes. Reads the deck; never builds.")
    p.add_argument("target", nargs="?", metavar="DIR|DECK.html",
                   help="the project folder (default: the project found from here), one of its build folders, or a "
                        "built slides-live.html")
    p.add_argument("--profile", help="the build of this quarto profile, e.g. dark (with a project folder)")
    p.add_argument("--out", type=Path, help="the .pptx to write (default: slides.pptx beside the live deck)")
    p.add_argument("--scale", type=int, default=2, help="device pixels per CSS px of the pictures (2: 2560x1440)")
    p.add_argument("--video", choices=VIDEO_MODES, default="auto",
                   help="auto: movies start by themselves; click: on a click on them; still: no movies (auto)")
    p.add_argument("--slides", metavar="LIST", help="deck slides to export, 1-based as the foot shows them: 3,5-7")
    return p


def _describe(steps, plan) -> str:
    st = steps[0]
    n_clips = len({c.index for s in steps for c in s.clips})
    n_parts = len({p.name for s in steps for p in s.parts})
    movies = sum(isinstance(x, Movie) for shapes in plan for x in shapes)
    stills = sum(isinstance(x, Still) for shapes in plan for x in shapes)
    bits = [_n(len(steps), "step")]
    if n_clips:
        bits.append(_n(n_clips, "clip"))
    if n_parts:
        bits.append(_n(n_parts, "clip") + " in parts")
    if movies or stills:
        bits.append(f"{_n(movies, 'movie')}, {_n(stills, 'still')}")
    return f"  {st.number:>3}  {(st.title or '(untitled)')[:34]:<34}  {', '.join(bits)}"


def main(argv: list[str]) -> int:
    a = parser().parse_args(argv)
    _need()
    from ..clips import ClipError
    from .media import Media
    from .walk import WalkError, walk
    if a.scale < 1 or a.scale > 4:
        print("lk export pptx: --scale is 1 to 4", file=sys.stderr)
        return 2
    deck, build_cmd, project = resolve(a.target, a.profile)
    run = f"run `{build_cmd}`" if build_cmd else "run lk build --to live in the deck's project"
    if not deck.is_file():
        print(f"lk export pptx: no built live deck at {deck}; {run} first", file=sys.stderr)
        return 1
    out = a.out or deck.with_name("slides.pptx")
    if out.suffix.lower() != ".pptx":
        print(f"lk export pptx: --out {out} must end in .pptx", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="lk-export-") as tmp:
        tmp = Path(tmp)
        media = Media(tmp / "media")
        plans = []

        def planned(steps):
            for s in steps:
                for c in s.clips + s.parts:
                    if c.file is None:
                        raise ClipError(f"slide {s.number}: a clip without a source")
                    info = media.info(c.file)
                    c.size = info.display
                    if hasattr(c, "frames"):
                        c.frames = info.frames
            plan = plan_slide(steps, a.video)
            plans.append(plan)
            print(_describe(steps, plan), flush=True)

        print(f"lk export pptx: {deck}")
        newer = stale(project, deck) if project else []
        if newer:
            print(f"  note: {', '.join(newer)} {'is' if len(newer) == 1 else 'are'} newer than the built deck; "
                  f"{run} first if you changed {'it' if len(newer) == 1 else 'them'}")
        from playwright.sync_api import Error as BrowserError
        try:
            steps_by_slide, seen = walk(deck, tmp / "shots", scale=a.scale, slides=a.slides, on_slide=planned)
            counts = write(steps_by_slide, plans, media, out, a.video)
        except (WalkError, ClipError, ValueError) as exc:
            print(f"lk export pptx: {exc}", file=sys.stderr)
            return 1
        except BrowserError as exc:
            first = (str(exc).strip().splitlines() or ["Chromium failed"])[0]
            if "Executable doesn't exist" in str(exc):
                first = "Chromium for Playwright is missing: playwright install chromium"
            print(f"lk export pptx: {first}", file=sys.stderr)
            return 1
    for w in seen["warnings"]:
        print(f"  note: {w}")
    if seen["errors"]:
        print(f"lk export pptx: {_n(len(seen['errors']), 'page error')} while shooting (first: {seen['errors'][0]})",
              file=sys.stderr)
    size = out.stat().st_size / 1e6
    print(f"{_n(counts['slides'], 'PowerPoint slide')} from {_n(len(steps_by_slide), 'deck slide')}; "
          f"{_n(counts['movies'], 'movie')}, {_n(counts['stills'], 'still')}, {counts['notes']} with notes; "
          f"{size:.1f} MB: {out}")
    print("Check in PowerPoint before the talk (docs/EXPORT.md):")
    for c in checks(a.video, counts["movies"], counts["parts"]):
        print(f"  - {c}")
    return 0
