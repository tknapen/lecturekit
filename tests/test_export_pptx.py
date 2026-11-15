"""`lk export pptx`: a built live deck as a PowerPoint file.

The pure parts first, without a browser: the timing XML against what PowerPoint itself wrote (two files PowerPoint
saved, from LibreOffice's test data: a movie set to start automatically in PowerPoint 2007, a movie played when
clicked on in PowerPoint 2013), the content rectangle, the plan of movies and stills from synthetic steps, the notes
text, the parts cut frame-exactly from a barcode clip (each frame carries its own index, so a frame is read back as
the frame it is). Then two decks end to end: the clip-in-parts runtime deck of test_segments.py, and the feature
deck. The XSD check runs when LK_PML_XSD names pml.xsd of the ISO/IEC 29500-4 schemas (the transitional schemas
from the standard's part 4, published by ISO and Ecma as ECMA-376 part 4); the id and spid checks run everywhere,
since the schema does not enforce either.
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from collections import Counter
from pathlib import Path

import pytest
from test_segments import barcode  # noqa: F401  (the barcode clips of test_segments.py, a fixture)

from lecturekit import clips
from lecturekit.cli import main as lk
from lecturekit.export.media import Media
from lecturekit.export.plan import (
    SLIDE_EMU,
    Clip,
    Cut,
    Frame,
    Movie,
    Parts,
    Step,
    contain,
    emu,
    notes_text,
    parse_slides,
    plan_slide,
)
from lecturekit.export.timing import timing_xml

etree = pytest.importorskip("lxml.etree")

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "examples" / "features"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS = {"p": P}
XSD = Path(os.environ["LK_PML_XSD"]) if os.environ.get("LK_PML_XSD") else None
needs_ffmpeg = pytest.mark.skipif(clips._ffmpeg() is None, reason="ffmpeg not installed")


def _have(mod: str) -> bool:
    try:
        __import__(mod)
    except ImportError:
        return False
    return True


needs_pptx = pytest.mark.skipif(not _have("pptx"), reason="python-pptx not installed")
needs_browser = pytest.mark.skipif(not _have("playwright"), reason="playwright not installed")
needs_quarto = pytest.mark.skipif(shutil.which("quarto") is None, reason="quarto not installed")


# ---------------------------------------------------------------- the timing XML
# PowerPoint 2007 (bnc591147.pptx, slide 1): the main sequence of a movie set to start automatically, spid 4, 30093 ms
PP2007_MAINSEQ = (
    '<p:seq xmlns:p="%s" concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
    '<p:par><p:cTn id="3" fill="hold"><p:stCondLst><p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0">'
    '<p:tn val="2"/></p:cond></p:stCondLst><p:childTnLst><p:par><p:cTn id="4" fill="hold"><p:stCondLst>'
    '<p:cond delay="0"/></p:stCondLst><p:childTnLst><p:par><p:cTn id="5" presetID="1" presetClass="mediacall" '
    'presetSubtype="0" fill="hold" nodeType="afterEffect"><p:stCondLst><p:cond delay="0"/></p:stCondLst>'
    '<p:childTnLst><p:cmd type="call" cmd="playFrom(0.0)"><p:cBhvr><p:cTn id="6" dur="30093" fill="hold"/>'
    '<p:tgtEl><p:spTgt spid="4"/></p:tgtEl></p:cBhvr></p:cmd></p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn>'
    '</p:par></p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0">'
    '<p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl>'
    '<p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq>' % P)
# PowerPoint 2013 (tdf106867.pptx, slide 1): the whole timing of a movie played when clicked on, spid 4
PP2013_CLICK = (
    '<p:timing xmlns:p="%s"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">'
    '<p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" restart="whenNotActive" fill="hold" '
    'evtFilter="cancelBubble" nodeType="interactiveSeq"><p:stCondLst><p:cond evt="onClick" delay="0"><p:tgtEl>'
    '<p:spTgt spid="4"/></p:tgtEl></p:cond></p:stCondLst><p:endSync evt="end" delay="0"><p:rtn val="all"/>'
    '</p:endSync><p:childTnLst><p:par><p:cTn id="3" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst>'
    '<p:childTnLst><p:par><p:cTn id="4" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
    '<p:par><p:cTn id="5" presetID="2" presetClass="mediacall" presetSubtype="0" fill="hold" nodeType="clickEffect">'
    '<p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst><p:cmd type="call" cmd="togglePause"><p:cBhvr>'
    '<p:cTn id="6" dur="1" fill="hold"/><p:tgtEl><p:spTgt spid="4"/></p:tgtEl></p:cBhvr></p:cmd></p:childTnLst>'
    '</p:cTn></p:par></p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn>'
    '<p:nextCondLst><p:cond evt="onClick" delay="0"><p:tgtEl><p:spTgt spid="4"/></p:tgtEl></p:cond></p:nextCondLst>'
    '</p:seq><p:video><p:cMediaNode vol="80000"><p:cTn id="7" fill="hold" display="0"><p:stCondLst>'
    '<p:cond delay="indefinite"/></p:stCondLst></p:cTn><p:tgtEl><p:spTgt spid="4"/></p:tgtEl></p:cMediaNode>'
    '</p:video></p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>' % P)

# the child order of every element the timing uses (ISO/IEC 29500-1, pml.xsd)
ORDER = {
    "cTn": ["stCondLst", "endCondLst", "endSync", "iterate", "childTnLst", "subTnLst"],
    "seq": ["cTn", "prevCondLst", "nextCondLst"],
    "par": ["cTn"],
    "cmd": ["cBhvr"],
    "cBhvr": ["cTn", "tgtEl", "attrNameLst"],
    "video": ["cMediaNode"],
    "cMediaNode": ["cTn", "tgtEl"],
    "timing": ["tnLst", "bldLst", "extLst"],
}


def canon(el) -> bytes:
    return etree.tostring(el, method="c14n")


def check_timing(xml: str, movies: list[tuple[int, int]]) -> etree._Element:
    """Well formed; ids 1..n in document order; every spid one of the movies and every movie targeted by its play
    (with autoplay), its pause toggle and its media node; children in schema order."""
    t = etree.fromstring(xml)
    ids = [int(x) for x in t.xpath("//p:cTn/@id", namespaces=NS)]
    assert ids == list(range(1, len(ids) + 1))
    spids = Counter(int(x) for x in t.xpath("//p:spTgt/@spid", namespaces=NS))
    assert set(spids) == {s for s, _ in movies}
    for el in t.iter():
        name = etree.QName(el).localname
        if name in ORDER:
            kids = [etree.QName(k).localname for k in el]
            assert all(k in ORDER[name] for k in kids), (name, kids)
            assert kids == sorted(kids, key=ORDER[name].index), (name, kids)
    for spid, _ in movies:
        assert len(t.xpath(f"//p:video/p:cMediaNode[p:tgtEl/p:spTgt/@spid='{spid}']", namespaces=NS)) == 1
        assert len(t.xpath(f"//p:cmd[@cmd='togglePause'][p:cBhvr/p:tgtEl/p:spTgt/@spid='{spid}']", namespaces=NS)) == 1
    return t


def strip_ids(el):
    el = etree.fromstring(canon(el))
    for c in el.iter(f"{{{P}}}cTn"):
        c.attrib.pop("id", None)
    return canon(el)


def test_one_autoplay_movie_is_what_powerpoint_writes():
    t = check_timing(timing_xml([(4, 30093)]), [(4, 30093)])
    main = t.xpath("//p:seq[p:cTn/@nodeType='mainSeq']", namespaces=NS)[0]
    assert canon(main) == canon(etree.fromstring(PP2007_MAINSEQ))                  # the same ids, 2 to 6
    ref = etree.fromstring(PP2013_CLICK)
    for path in ("//p:seq[p:cTn/@nodeType='interactiveSeq']", "//p:video"):
        assert strip_ids(t.xpath(path, namespaces=NS)[0]) == strip_ids(ref.xpath(path, namespaces=NS)[0])
    assert t.xpath("//p:cMediaNode/p:cTn/@id", namespaces=NS) == ["12"]


def test_click_is_powerpoint_2013s_timing():
    assert canon(etree.fromstring(timing_xml([(4, 2000)], autoplay=False))) == canon(etree.fromstring(PP2013_CLICK))


def test_two_movies_start_together():
    movies = [(3, 1500), (4, 6467)]
    t = check_timing(timing_xml(movies), movies)
    effects = t.xpath("//p:par/p:cTn[@presetClass='mediacall'][@presetID='1']", namespaces=NS)
    assert [e.get("nodeType") for e in effects] == ["afterEffect", "withEffect"]
    assert len({e.getparent().getparent().getparent().get("id") for e in effects}) == 1     # one group par
    assert [int(x) for x in t.xpath("//p:cmd[@cmd='playFrom(0.0)']/p:cBhvr/p:cTn/@dur", namespaces=NS)] == [1500, 6467]
    check_timing(timing_xml(movies, autoplay=False), movies)


def test_a_timing_needs_a_movie_with_a_length():
    with pytest.raises(ValueError):
        timing_xml([])
    with pytest.raises(ValueError):
        timing_xml([(3, 0)])


# ---------------------------------------------------------------- rectangles and the plan
def test_contain_fits_the_files_own_aspect():
    assert contain((100, 100, 400, 300), 1280, 720) == pytest.approx((100, 137.5, 400, 225))      # 16:9 in 4:3
    assert contain((0, 0, 640, 360), 640, 480) == pytest.approx((80, 0, 480, 360))                 # 4:3 in 16:9
    assert contain((10, 20, 300, 100), 500, 500) == pytest.approx((110, 20, 100, 100))             # 1:1
    assert emu((0, 0, 1280, 720)) == (0, 0, *SLIDE_EMU)
    assert emu((-10, 700, 100, 100)) == (0, 700 * 9525, 90 * 9525, 20 * 9525)                      # cut to the slide


F = Path("bar.mp4")
G = Path("back.mp4")


def step(f, clips=(), parts=()):
    return Step(number=1, f=f, title="t", shot=Path("s.png"), clips=list(clips), parts=list(parts))


def clip(index, on, file=F, frames=45):
    return Clip(index=index, file=file, box=(0, 0, 640, 360), on_stage=on, size=(640, 360), frames=frames)


def part(k, start="auto", bounds=(0, 42, 96, 150, 194)):
    return Parts(name="p", file=F, start=start, bounds=list(bounds), k=k, box=(0, 0, 640, 360), size=(640, 360))


def kinds(plan):
    out = []
    for shapes in plan:
        row = []
        for s in shapes:
            if isinstance(s, Movie):
                row.append(("movie", s.media.file.name, s.media.a, s.media.b, s.poster.n))
            else:
                row.append(("still", s.frame.file.name, s.frame.n))
        out.append(row)
    return out


def test_plan_start_auto_plays_a_part_at_every_step():
    plan = plan_slide([step(-1, parts=[part(0)]), step(0, parts=[part(1)]), step(1, parts=[part(2)]),
                       step(2, parts=[part(3)])])
    assert kinds(plan) == [[("movie", "bar.mp4", 0, 42, 0)], [("movie", "bar.mp4", 42, 96, 42)],
                           [("movie", "bar.mp4", 96, 150, 96)], [("movie", "bar.mp4", 150, 194, 150)]]
    assert plan[1][0].media.frames == 55
    still = plan_slide([step(-1, parts=[part(0)]), step(0, parts=[part(1)])], video="still")
    assert kinds(still) == [[("still", "bar.mp4", 42)], [("still", "bar.mp4", 96)]]


def test_plan_start_key_opens_on_frame_zero():
    b = (0, 51, 104)
    plan = plan_slide([step(-1, parts=[part(0, "key", b)]), step(0, parts=[part(1, "key", b)]),
                       step(1, parts=[part(2, "key", b)])])
    assert kinds(plan) == [[("still", "bar.mp4", 0)], [("movie", "bar.mp4", 0, 51, 0)],
                           [("movie", "bar.mp4", 51, 104, 51)]]


def test_plan_ordinary_clip_in_a_fragment_comes_on_with_its_step():
    plan = plan_slide([step(-1, [clip(0, False)]), step(0, [clip(0, True)])])
    assert kinds(plan) == [[], [("movie", "bar.mp4", 0, 44, 0)]]
    assert plan[1][0].media.whole


def test_plan_sequence_in_an_r_stack_plays_each_step():
    plan = plan_slide([step(-1, [clip(0, True), clip(1, False, G, 30)]),
                       step(0, [clip(0, False), clip(1, True, G, 30)])])
    assert kinds(plan) == [[("movie", "bar.mp4", 0, 44, 0)], [("movie", "back.mp4", 0, 29, 0)]]


def test_plan_clip_on_stage_while_a_fragment_appears_is_its_last_frame():
    plan = plan_slide([step(-1, [clip(0, True)]), step(0, [clip(0, True)]), step(1, [clip(0, True)])])
    assert kinds(plan) == [[("movie", "bar.mp4", 0, 44, 0)], [("still", "bar.mp4", 44)], [("still", "bar.mp4", 44)]]
    assert kinds(plan_slide([step(-1, [clip(0, True)])], video="click")) == kinds(plan[:1])
    assert kinds(plan_slide([step(-1, [clip(0, True)])], video="still")) == [[("still", "bar.mp4", 44)]]
    with pytest.raises(ValueError):
        plan_slide([], video="loop")


def test_plan_places_clips_in_their_content_rectangle():
    square = (0, 0, 400, 400)
    c = Clip(index=0, file=F, box=square, on_stage=True, size=(640, 360), frames=45)
    p = Parts(name="p", file=F, start="auto", bounds=[0, 42], k=0, box=square, size=(640, 360))
    for video in ("auto", "still"):
        shapes = plan_slide([step(-1, [c], [p])], video=video)[0]
        assert [s.rect for s in shapes] == [pytest.approx((0, 87.5, 400, 225))] * 2


def test_plan_carries_the_colour_a_clip_is_blended_with():
    paper = (243, 242, 238)
    c = Clip(index=0, file=F, box=(0, 0, 640, 360), on_stage=True, paper=True, tint=paper, size=(640, 360), frames=45)
    p = Parts(name="p", file=F, start="auto", bounds=[0, 42, 96], k=0, box=(0, 0, 640, 360), paper=True, tint=paper,
              size=(640, 360))
    movie, part = plan_slide([step(-1, [c], [p])])[0]
    assert movie.media == Cut(F, 0, 44, whole=True, tint=paper) and movie.poster == Frame(F, 0, paper)
    assert part.media == Cut(F, 0, 42, tint=paper) and part.poster == Frame(F, 0, paper)
    still, hold = plan_slide([step(-1, [c], [p])], video="still")[0]
    assert still.frame == Frame(F, 44, paper) and hold.frame == Frame(F, 42, paper)
    assert Cut(F, 0, 42, tint=paper) != Cut(F, 0, 42)                           # made and stored apart


def test_slides_option():
    assert parse_slides("3,5-7", 10) == [3, 5, 6, 7]
    assert parse_slides(None, 3) == [1, 2, 3]
    assert parse_slides("7,2,2", 10) == [2, 7]
    for bad in ("0", "4-2", "11", "a", "3,,4"):
        with pytest.raises(ValueError):
            parse_slides(bad, 10)


def test_notes_text_drops_style_and_keeps_blocks():
    aside = ('<aside class="notes"><p>Line: the deck is the engine’s test.\n  Status: release.</p>'
             '<style type="text/css">span.MJX_Assistive_MathML { position:absolute!important; }</style>'
             '<ul><li>one</li><li>two<br>three</li></ul><script>var x = 1;</script>'
             '<p>Width <math><mi>σ</mi><annotation encoding="application/x-tex">\\sigma</annotation></math>.</p></aside>')
    assert notes_text([aside, "Plain notes from data-notes."]) == (
        "Line: the deck is the engine’s test. Status: release.\none\ntwo\nthree\nWidth $\\sigma$.\n"
        "Plain notes from data-notes.")
    assert notes_text([]) == ""


# ---------------------------------------------------------------- media, frame-exact
def barcode_clip(path: Path, frames: int = 120, fps: int = 30, *args: str) -> Path:
    from test_stops_index import barcode_frame, write_video
    return write_video(path, (barcode_frame(n, n / frames) for n in range(frames)), fps, *args)


def read_frames(video: Path, ns: list[int], work: Path) -> list[int]:
    from test_stops_index import read_barcode
    outs = [work / f"read{n}.png" for n in ns]
    clips.extract_frames(video, ns, outs)
    return [read_barcode(p) for p in outs]


@needs_ffmpeg
def test_parts_are_cut_frame_exactly(tmp_path):
    pytest.importorskip("PIL")
    src = barcode_clip(tmp_path / "src" / "code.mp4", 120, 30, "-g", "250")       # one keyframe: cuts mid-GOP
    media = Media(tmp_path / "work")
    for a, b in ((0, 37), (37, 81), (81, 119)):
        out = media.movie(Cut(src, a, b))
        table = clips.frame_table(out)
        assert table.frames == b - a + 1
        assert read_frames(out, [0, table.frames - 1], tmp_path) == [a, b]
        assert media.movie(Cut(src, a, b)) == out                                  # cut once
        assert media.duration_ms(Cut(src, a, b)) == round((b - a + 1) / 30 * 1000)
    stills = media.stills([Frame(src, 0), Frame(src, 81), Frame(src, 119)])
    from test_stops_index import read_barcode
    assert [read_barcode(p) for p in stills.values()] == [0, 81, 119]
    with pytest.raises(clips.ClipError):
        media.movie(Cut(src, 100, 130))


@needs_ffmpeg
def test_a_whole_clip_is_embedded_as_it_is_or_moved_to_index_first(tmp_path):
    from test_stops_index import atoms
    pytest.importorskip("PIL")
    fast = barcode_clip(tmp_path / "fast.mp4", 30, 30, "-movflags", "+faststart")
    slow = barcode_clip(tmp_path / "slow.mp4", 30, 30)
    media = Media(tmp_path / "work")
    assert media.info(fast).index_first and media.info(fast).embeddable
    assert media.movie(Cut(fast, 0, 29, whole=True)) == fast
    assert not media.info(slow).index_first
    out = media.movie(Cut(slow, 0, 29, whole=True))
    assert out != slow and atoms(out).index("moov") < atoms(out).index("mdat")
    assert clips.frame_table(out).frames == 30


@needs_ffmpeg
def test_without_ffprobe_a_whole_clip_is_still_embedded_as_it_is(tmp_path, monkeypatch):
    pytest.importorskip("PIL")
    fast = barcode_clip(tmp_path / "fast.mp4", 30, 30, "-movflags", "+faststart")
    monkeypatch.setattr(clips, "_ffprobe", lambda: None)
    media = Media(tmp_path / "work")
    info = media.info(fast)
    assert (info.codec, info.pix_fmt, info.mp4, info.frames) == ("h264", "yuv420p", True, 30)
    assert media.movie(Cut(fast, 0, 29, whole=True)) == fast


@needs_ffmpeg
def test_a_tinted_clip_is_multiplied_by_the_page_colour(tmp_path):
    """The frames of a clip the page blends by multiplication: each colour times the page colour over 255, in the
    stills exactly, in the movies within the rounding of the H.264 coding."""
    pytest.importorskip("PIL")
    from PIL import Image
    src = barcode_clip(tmp_path / "src" / "code.mp4", 60, 30, "-movflags", "+faststart")
    paper = (243, 242, 238)
    ground = (235, 238, 242)                                                     # the barcode frames' background
    want = tuple(round(a * b / 255) for a, b in zip(ground, paper))

    def at(png: Path) -> tuple:
        with Image.open(png) as im:
            return im.convert("RGB").getpixel((im.width // 2, im.height - 20))

    def near(a, b, by):
        return all(abs(x - y) <= by for x, y in zip(a, b))

    media = Media(tmp_path / "work")
    stills = media.stills([Frame(src, 7), Frame(src, 7, paper), Frame(src, 30, paper)])
    plain, tinted = stills[Frame(src, 7)], stills[Frame(src, 7, paper)]
    assert plain != tinted and near(at(plain), ground, 3) and near(at(tinted), want, 3)
    assert not near(at(tinted), at(plain), 3)
    whole = media.movie(Cut(src, 0, 59, whole=True, tint=paper))
    assert whole != src and media.movie(Cut(src, 0, 59, whole=True)) == src     # the plain clip stays as it is
    part = media.movie(Cut(src, 7, 30, tint=paper))
    assert part != media.movie(Cut(src, 7, 30))
    for movie, frames in ((whole, [0, 59]), (part, [7, 30])):
        table = clips.frame_table(movie)
        assert table.frames == frames[1] - frames[0] + 1
        assert read_frames(movie, [0, table.frames - 1], tmp_path) == frames     # the same frames, still readable
        clips.extract_frames(movie, [0], [tmp_path / "first.png"])
        assert near(at(tmp_path / "first.png"), at(tinted), 2)                   # the movie as its poster


def test_the_checklist_names_parts_only_when_there_are_some():
    from lecturekit.export.pptx import checks
    assert not [c for c in checks("auto", 1) if "parts" in c]
    assert [c for c in checks("auto", 3, 2) if "parts" in c]
    assert len(checks("still", 0)) == 2


def project(tmp: Path) -> Path:
    """A project with a dark profile and a paper deck built in _build."""
    (tmp / "_quarto.yml").write_text("project:\n  output-dir: _build\n")
    (tmp / "_quarto-dark.yml").write_text("project:\n  output-dir: _build-dark\n")
    (tmp / "slides.qmd").write_text("# t\n")
    (tmp / "_build").mkdir()
    (tmp / "_build" / "slides-live.html").write_text("<html></html>")
    return tmp


def test_a_build_folder_exports_its_own_deck(tmp_path):
    from lecturekit.export.pptx import resolve
    proj = project(tmp_path)
    (proj / "_build-dark").mkdir()
    deck, cmd, found = resolve(str(proj / "_build-dark"), None)
    assert deck == proj / "_build-dark" / "slides-live.html" and found == proj.resolve()
    assert cmd == f"lk build {proj.resolve()} --to live --profile dark"
    assert resolve(str(proj / "_build"), None)[:2] == (proj / "_build" / "slides-live.html",
                                                       f"lk build {proj.resolve()} --to live")
    (proj / "figures").mkdir()
    with pytest.raises(SystemExit, match="neither a project folder"):
        resolve(str(proj / "figures"), None)
    with pytest.raises(SystemExit, match="--profile"):
        resolve(str(proj / "_build-dark"), "dark")


def test_an_unknown_profile_is_refused(tmp_path):
    from lecturekit.export.pptx import resolve
    proj = project(tmp_path)
    with pytest.raises(SystemExit, match="no _quarto-drak.yml .*profiles here: dark"):
        resolve(str(proj), "drak")
    assert resolve(str(proj), "dark")[0] == proj.resolve() / "_build-dark" / "slides-live.html"


def test_a_missing_deck_file_names_the_build_command(tmp_path, capsys):
    pytest.importorskip("pptx")
    pytest.importorskip("playwright")
    proj = project(tmp_path)
    (proj / "_build-dark").mkdir()
    assert lk(["export", "pptx", str(proj / "_build-dark" / "slides-live.html")]) == 1
    assert f"run `lk build {proj.resolve()} --to live --profile dark` first" in capsys.readouterr().err
    assert lk(["export", "pptx", str(tmp_path / "elsewhere.html")]) == 1
    assert "run lk build --to live in the deck's project first" in capsys.readouterr().err


def test_a_stale_deck_and_a_missing_chromium_say_so_in_one_line(tmp_path, capsys, monkeypatch):
    pytest.importorskip("pptx")
    playwright = pytest.importorskip("playwright.sync_api")
    proj = project(tmp_path)
    os.utime(proj / "_build" / "slides-live.html", (1, 1))
    import lecturekit.export.walk as walk

    def no_browser(*a, **k):
        raise playwright.Error("BrowserType.launch: Executable doesn't exist at /x/chrome\n" + "box\n" * 20)
    monkeypatch.setattr(walk, "walk", no_browser)
    assert lk(["export", "pptx", str(proj), "--out", str(tmp_path / "x.pptx")]) == 1
    out = capsys.readouterr()
    note = [line for line in out.out.splitlines() if "newer than the built deck" in line]
    assert len(note) == 1 and "slides.qmd" in note[0] and "--to live` first" in note[0]
    assert out.err.strip().splitlines() == ["lk export pptx: Chromium for Playwright is missing: "
                                            "playwright install chromium"]


def test_a_missing_deck_names_the_build_command(tmp_path, capsys):
    (tmp_path / "_quarto.yml").write_text("project:\n  output-dir: _build\n")
    (tmp_path / "_quarto-dark.yml").write_text("project:\n  output-dir: _build-dark\n")
    pytest.importorskip("pptx")
    pytest.importorskip("playwright")
    assert lk(["export", "pptx", str(tmp_path), "--profile", "dark"]) == 1
    err = capsys.readouterr().err
    assert "no built live deck" in err and f"lk build {tmp_path.resolve()} --to live --profile dark" in err
    assert lk(["export", "docx"]) == 2


# ---------------------------------------------------------------- end to end
def run_export(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "lecturekit.cli", "export", "pptx", *args],
                          capture_output=True, text=True)


def check_package(path: Path) -> list:
    """Reopen with python-pptx; per slide: one timing at most, unique shape ids, time node ids 1..n, every spid a
    shape on the slide, the picture's alt text; XSD where the schemas are installed. Returns the slides."""
    from pptx import Presentation
    prs = Presentation(str(path))
    assert (prs.slide_width, prs.slide_height) == SLIDE_EMU
    schema = etree.XMLSchema(etree.parse(str(XSD))) if XSD and XSD.exists() else None
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        size = etree.fromstring(z.read("ppt/presentation.xml")).find("p:sldSz", NS)
        assert size.get("type") is None                                      # 16:9 is not "screen4x3"
        A = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
        master = etree.fromstring(z.read("ppt/slideMasters/slideMaster1.xml"))
        title = master.xpath("//p:sp[.//p:ph[@type='title']]//a:xfrm", namespaces={**NS, **A})[0]
        assert (int(title.find("a:off", A).get("x")), int(title.find("a:ext", A).get("cx"))) == (609600, 10972800)
        if "ppt/notesMasters/notesMaster1.xml" in z.namelist():
            notes = etree.fromstring(z.read("ppt/notesMasters/notesMaster1.xml"))
            img = notes.xpath("//p:sp[.//p:ph[@type='sldImg']]//a:ext", namespaces={**NS, **A})[0]
            assert int(img.get("cx")) * 9 == int(img.get("cy")) * 16
        assert not [n for n in z.namelist() if "printerSettings" in n]
        for s in prs.slides:
            doc = etree.fromstring(z.read(s.part.partname.lstrip("/")))
            if schema is not None:
                assert schema.validate(doc), [e.message for e in schema.error_log][:3]
            shapes = [int(x) for x in doc.xpath("//p:cSld//p:cNvPr/@id", namespaces=NS)]
            ids = [int(x) for x in doc.xpath("//p:timing//p:cTn/@id", namespaces=NS)]
            spids = {int(x) for x in doc.xpath("//p:timing//p:spTgt/@spid", namespaces=NS)}
            assert len(doc.xpath("//p:timing", namespaces=NS)) <= 1
            assert len(shapes) == len(set(shapes)) and ids == list(range(1, len(ids) + 1)) and spids <= set(shapes)
            assert s.shapes[0]._element.xpath("./*[1]/p:cNvPr/@descr")
    return list(prs.slides)


def by_number(slides) -> dict[int, list]:
    """The PowerPoint slides of each deck slide, by the deck slide's number (the picture is named after it)."""
    out: dict[int, list] = {}
    for s in slides:
        n = int(re.match(r"Slide (\d+)", s.shapes[0].name).group(1))
        out.setdefault(n, []).append(s)
    return out


def movies_of(slide) -> list[tuple[bytes, bytes, int]]:
    """Each movie of a slide: its media bytes, its poster bytes, its play length in the timing (0 without)."""
    out = []
    for sh in slide.shapes:
        if type(sh).__name__ != "Movie":
            continue
        el = sh._element
        rid = etree.XPath(".//p14:media/@r:embed", namespaces={
            "p14": "http://schemas.microsoft.com/office/powerpoint/2010/main",
            "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"})(el)[0]
        blip = el.xpath("./p:blipFill/a:blip/@r:embed")[0]
        dur = slide._element.xpath(f".//p:cmd[@cmd='playFrom(0.0)'][p:cBhvr/p:tgtEl/p:spTgt/@spid='{sh.shape_id}']"
                                   f"/p:cBhvr/p:cTn/@dur")
        out.append((slide.part.related_part(rid).blob, slide.part.related_part(blip).blob, int(dur[0]) if dur else 0))
    return out


def read_640(png: bytes) -> int:
    """The barcode of test_segments.py's 640 by 360 clips."""
    from PIL import Image
    with Image.open(io.BytesIO(png)) as im:
        g = im.convert("L")
        s = g.width / 640
        n = 0
        for b in range(10):
            n = n * 2 + (1 if g.getpixel((int((20 + b * 60 + 28) * s), int(36 * s))) > 128 else 0)
        return n


@pytest.fixture(scope="module")
def runtime_export(tmp_path_factory, barcode):  # noqa: F811
    """The runtime deck of test_segments.py (a clip in parts with notes at its stops, an ordinary clip, a mid-GOP clip
    in parts, one with start=key), built live and exported in the three video modes."""
    if shutil.which("quarto") is None or not _have("playwright") or not _have("pptx"):
        pytest.skip("quarto, playwright and python-pptx are needed")
    from test_segments import RUNTIME_SLIDES, lk_build, make_deck
    deck = make_deck(tmp_path_factory.mktemp("export") / "deck", RUNTIME_SLIDES, barcode)
    r = lk_build(deck, "--to", "live")
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    out = {}
    for mode in ("auto", "click", "still"):
        path = deck / f"{mode}.pptx"
        r = run_export(str(deck), "--out", str(path), "--video", mode)
        assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
        out[mode] = (path, r.stdout)
    return deck, out



def test_runtime_deck_steps_parts_and_notes(runtime_export, tmp_path):
    deck, out = runtime_export
    path, stdout = out["auto"]
    slides = check_package(path)
    # title 1, Before 1, Clip in parts 4 (k30: 3 cues), After 1, Mid-GOP 4, Key start 5 (k60, key: 4 cues), End 1
    assert len(slides) == 17
    assert "17 PowerPoint slides from 7 deck slides" in stdout
    by = by_number(slides)
    k30 = by[3]
    f30 = [0, 90, 180, 270, 359]
    for i, s in enumerate(k30):
        (blob, poster, dur), = movies_of(s)
        mp4 = tmp_path / f"k30-{i}.mp4"
        mp4.write_bytes(blob)
        table = clips.frame_table(mp4)
        a, b = f30[i], f30[i + 1]
        assert table.frames == b - a + 1 and dur == round((b - a + 1) / 30 * 1000)
        clips.extract_frames(mp4, [0, table.frames - 1], [tmp_path / "a.png", tmp_path / "b.png"])
        assert [read_640((tmp_path / n).read_bytes()) for n in ("a.png", "b.png")] == [a, b]
        assert read_640(poster) == a
    notes = [s.notes_slide.notes_text_frame.text for s in k30]
    # each step holds on a stop and shows its notes (the filter puts the first hold's before the slide's own)
    assert notes[0].startswith("Ask: where does the dot go next?") and "Slide notes: the clip runs" in notes[0]
    assert notes[1].startswith("Ask: and after that?")
    assert "holds on strict" in notes[2]
    assert notes[3].startswith("Say: that is the whole sweep.")
    assert len(set(notes)) == 4
    key = by[6]
    assert len(key) == 5 and movies_of(key[0]) == [] and len(movies_of(key[1])) == 1
    assert key[0].notes_slide.notes_text_frame.text.startswith("Ask: what will the dot do?")
    still = [sh for sh in key[0].shapes if type(sh).__name__ == "Picture"][1]
    assert read_640(still.image.blob) == 0
    assert len(by[5]) == 4 and all(len(movies_of(s)) == 1 for s in by[5])
    (whole, _, dur), = movies_of(by[4][0])
    assert whole == (deck / "assets" / "clips" / "bar_bold.mp4").read_bytes()          # embedded as it is
    assert "Fixture" in slides[0].shapes[0]._element.xpath("./*[1]/p:cNvPr/@descr")[0].split("\n")
    assert "A slide before the clip." in by[2][0].shapes[0]._element.xpath("./*[1]/p:cNvPr/@descr")[0]


BLEND_SLIDES = """## On paper {role=summary}

:::: {.live-only}
::: {.movie src="assets/clips/bar_bold.mp4" label="on paper"}
:::
::::

## Forced on white {role=example}

:::: {.live-only}
::: {.movie src="assets/clips/bar_bold.mp4" label="forced" .paper}
:::
::::

## Kept white {role=summary}

:::: {.live-only}
::: {.movie src="assets/clips/bar_bold.mp4" label="kept white" .keepwhite}
:::
::::
"""


def test_a_clip_on_a_paper_slide_takes_the_page_colour(tmp_path, barcode):  # noqa: F811
    """theme.scss blends a clip of a goals, summary, section or pause slide with the page by multiplication: the
    clip's white becomes the page colour. The export multiplies the frames by the colour under the clip. A clip
    forced to `.paper` on a white slide and one kept white stay as they are."""
    if shutil.which("quarto") is None or not _have("playwright") or not _have("pptx"):
        pytest.skip("quarto, playwright and python-pptx are needed")
    from PIL import Image
    from test_segments import lk_build, make_deck
    deck = make_deck(tmp_path / "deck", BLEND_SLIDES, barcode)
    r = lk_build(deck, "--to", "live")
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    out = tmp_path / "blend.pptx"
    r = run_export(str(deck), "--out", str(out))
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    by = by_number(check_package(out))
    source = (deck / "assets" / "clips" / "bar_bold.mp4").read_bytes()

    def corner(png: bytes) -> tuple:
        with Image.open(io.BytesIO(png)) as im:
            return im.convert("RGB").getpixel((6, 6))

    def page(slide) -> tuple:
        return tuple(slide.background.fill.fore_color.rgb)

    (movie, poster, _), = movies_of(by[2][0])
    paper = page(by[2][0])
    assert paper != (255, 255, 255) and corner(poster) == paper                 # white times the page colour
    assert movie != source                                                      # re-encoded, multiplied
    (tmp_path / "m.mp4").write_bytes(movie)
    clips.extract_frames(tmp_path / "m.mp4", [0], [tmp_path / "m0.png"])
    assert all(abs(a - b) <= 4 for a, b in zip(corner((tmp_path / "m0.png").read_bytes()), paper))
    (movie, poster, _), = movies_of(by[3][0])                                   # no colour under it: unblended
    assert page(by[3][0]) == (255, 255, 255) and corner(poster) == (255, 255, 255) and movie == source
    (movie, poster, _), = movies_of(by[4][0])                                   # kept white on the paper page
    assert page(by[4][0]) == paper and corner(poster) == (255, 255, 255) and movie == source


def test_runtime_deck_click_and_still(runtime_export):
    _, out = runtime_export
    click = check_package(out["click"][0])
    assert len(click) == 17
    assert not any(s._element.xpath(".//p:cTn[@nodeType='mainSeq']") for s in click)
    assert sum(len(movies_of(s)) for s in click) == 13                        # parts 4 + 4 + 4, the ordinary clip 1
    assert all(d == 0 for s in click for _, _, d in movies_of(s))
    still, stdout = out["still"]
    assert len(check_package(still)) == 17
    with zipfile.ZipFile(still) as z:
        assert not [n for n in z.namelist() if n.endswith(".mp4")]
        assert "video" not in z.read("[Content_Types].xml").decode()
    assert "0 movies" in stdout


@pytest.fixture(scope="module")
def features_export(tmp_path_factory):
    if shutil.which("quarto") is None or not _have("playwright") or not _have("pptx"):
        pytest.skip("quarto, playwright and python-pptx are needed")
    link = FEATURES / "_extensions"
    if not link.exists() and not link.is_symlink():
        link.symlink_to("../../_extensions")
    r = subprocess.run([sys.executable, "-m", "lecturekit.cli", "build", str(FEATURES), "--to", "live"],
                       capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    path = tmp_path_factory.mktemp("features") / "features.pptx"
    r = run_export(str(FEATURES), "--out", str(path))
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    return path, r.stdout


def test_features_deck(features_export, tmp_path):
    path, _ = features_export
    slides = check_package(path)
    html = (FEATURES / "_build" / "slides-live.html").read_text(encoding="utf-8")
    # the steps counted in the page by stepping (Reveal's own fragment navigation), not by indices
    from lecturekit.review.browser import deck_page
    with deck_page(FEATURES / "_build" / "slides-live.html") as (page, _):
        total = page.evaluate("""() => { let n = 0; const hs = Reveal.getHorizontalSlides();
          for (let h = 0; h < hs.length; h++) { Reveal.slide(h, 0, -1); n++; while (Reveal.nextFragment()) n++; }
          return n; }""")
    assert len(slides) == total
    # every part of every clip in parts is a movie of its frames, once
    want = Counter()
    for bounds in re.findall(r'data-lk-bounds="([^"]+)"', html):
        b = [x["f"] for x in json.loads(bounds.replace("&quot;", '"'))]
        want.update(b[i + 1] - b[i] + 1 for i in range(len(b) - 1))
    got = Counter()
    for i, s in enumerate(slides):
        for j, (blob, _, dur) in enumerate(movies_of(s)):
            mp4 = tmp_path / f"m{i}-{j}.mp4"
            mp4.write_bytes(blob)
            table = clips.frame_table(mp4)
            got[table.frames] += 1
            assert dur == round(table.frames / table.fps * 1000)
    assert not want - got
    # a hold's notes: every step of a clip in parts has its own, without the style element the build puts in them
    sections = re.split(r"<section\b", html)[1:]
    seg = [n for n, chunk in enumerate(sections, 1) if 'class="live-only lk-seg"' in chunk]
    assert len(seg) == 3
    by = by_number(slides)
    for n in seg:
        notes = [s.notes_slide.notes_text_frame.text for s in by[n]]
        assert len(notes) >= 3 and all(notes) and len(set(notes)) == len(notes), (n, notes)
        assert not any("MJX" in t or "{" in t for t in notes)
