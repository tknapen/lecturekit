"""The clip runtime and the seam's failure paths: what the live deck does with real key presses (Playwright's
Chromium), what the filter does with an index entry that has null or missing fields, a dark index, a checkpoint
still, and what `lk build` makes of a filter error. The deck tests need quarto and Playwright's chromium
(PLAYWRIGHT_BROWSERS_PATH is honoured); the study builds need xelatex.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "examples" / "features"
EXTENSION = ROOT / "_extensions"

needs_quarto = pytest.mark.skipif(shutil.which("quarto") is None, reason="quarto not installed")
needs_tex = pytest.mark.skipif(shutil.which("xelatex") is None, reason="xelatex not installed")


def run(cmd, cwd=None, env=None):
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)


def lk_build(project: Path, *args: str, env=None):
    return run([sys.executable, "-m", "lecturekit.cli", "build", str(project), *args], env=env)


def _chromium():
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return False
    return True


needs_browser = pytest.mark.skipif(not _chromium(), reason="playwright not installed")


# ---------------------------------------------------------------- fixture decks
def make_deck(where: Path, slides: str, index: dict | None = None, dark_index: dict | None = None,
              files: tuple[str, ...] = ()) -> Path:
    """A minimal project beside the engine: the features deck's brands, the extension by symlink, the given slides,
    clips index (paper and dark) and placeholder clip files."""
    where.mkdir(parents=True, exist_ok=True)
    os.symlink(EXTENSION, where / "_extensions")
    for name in ("_brand.yml", "_brand-dark.yml", "_quarto.yml", "_quarto-dark.yml"):
        shutil.copy2(FEATURES / name, where / name)
    clips = where / "assets" / "clips"
    clips.mkdir(parents=True)
    if index is not None:
        (clips / "clips.json").write_text(json.dumps(index, indent=2))
    if dark_index is not None:
        (clips / "dark").mkdir()
        (clips / "dark" / "clips.json").write_text(json.dumps(dark_index, indent=2))
    for rel in files:
        src = FEATURES / "assets" / "clips" / Path(rel).name
        dst = where / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src if src.exists() else FEATURES / "assets" / "clips" / "bar_bold.png", dst)
    (where / "slides.qmd").write_text('---\ntitle: "Fixture"\nbudget: 5\n---\n\n' + slides)
    return where


CLIP_SLIDE = """## A clip slide {role=example time=1}

::: {.movie clip="sweep"}
:::
"""


@pytest.fixture(scope="module")
def null_still_deck(tmp_path_factory):
    """An index entry as a buggy writer leaves it: still, fps and checkpoints null; looked up as `sweep`."""
    entry = {"video": "assets/clips/bar_bold.mp4", "still": None, "width": 960, "height": 540, "fps": None,
             "duration": 1.5, "checkpoints": None, "producer": "kit"}
    return make_deck(tmp_path_factory.mktemp("nullstill"), CLIP_SLIDE, {"sweep": entry},
                     files=("assets/clips/bar_bold.mp4",))


@needs_quarto
def test_null_still_builds_live(null_still_deck):
    r = lk_build(null_still_deck, "--to", "live")
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    html = (null_still_deck / "_build" / "slides-live.html").read_text()
    assert '<video data-lk-autoplay' in html and 'src="assets/clips/bar_bold.mp4"' in html
    assert "poster=" not in html                                      # null is absent, not a value


@needs_quarto
@needs_tex
def test_missing_still_fails_study_build(null_still_deck):
    r = lk_build(null_still_deck, "--to", "study")
    out = r.stdout + r.stderr
    assert r.returncode != 0, out[-3000:]
    assert "No still for the study PDF" in out
    assert 'movie "sweep" on slide "A clip slide"' in out             # names the movie and its slide
    assert "the build failed" in out                                  # lk build's own summary


@needs_quarto
def test_filter_error_stops_quarto_itself(null_still_deck):
    """The filter's own failure stops `quarto render` (not only lk build): Quarto's error() is a logger."""
    deck = null_still_deck
    (deck / "slides.qmd").write_text('---\ntitle: "Fixture"\n---\n\n## A slide {role=nonsense}\n\nText.\n')
    try:
        r = run(["quarto", "render", "--to", "lecturekit-revealjs"], cwd=deck)
        assert r.returncode != 0
        assert "ERROR (lecturekit) Unknown slide role: nonsense" in r.stdout + r.stderr
    finally:
        (deck / "slides.qmd").write_text('---\ntitle: "Fixture"\nbudget: 5\n---\n\n' + CLIP_SLIDE)


@needs_quarto
def test_unknown_checkpoint_fails(tmp_path):
    entry = {"video": "assets/clips/sweep.mp4", "still": "assets/clips/sweep.png", "width": 960, "height": 540,
             "checkpoints": {"start": "assets/clips/sweep.start.png", "end": "assets/clips/sweep.end.png"}}
    deck = make_deck(tmp_path / "deck", '## A clip slide {role=example}\n\n::: {.movie clip="sweep" still="middle"}\n:::\n',
                     {"sweep": entry}, files=("assets/clips/sweep.mp4", "assets/clips/sweep.png"))
    r = lk_build(deck, "--to", "live")
    out = r.stdout + r.stderr
    assert r.returncode != 0
    assert 'still="middle" names no checkpoint of clip "sweep"' in out and "(it has end, start)" in out


@needs_quarto
def test_dark_build_prefers_the_dark_index(tmp_path):
    paper = {
        "sweep": {"video": "assets/clips/sweep.mp4", "still": "assets/clips/sweep.png", "width": 960, "height": 540},
        "only_paper": {"video": "assets/clips/only_paper.mp4", "still": "assets/clips/only_paper.png",
                       "width": 960, "height": 540},
    }
    dark = {"sweep": {"video": "assets/clips/dark/sweep.mp4", "still": "assets/clips/dark/sweep.png",
                      "width": 960, "height": 540}}
    slides = ('## Both presets {role=example}\n\n::: {.movie clip="sweep"}\n:::\n\n'
              '## Paper only {role=example}\n\n::: {.movie clip="only-paper"}\n:::\n')
    deck = make_deck(tmp_path / "deck", slides, paper, dark,
                     files=("assets/clips/sweep.mp4", "assets/clips/sweep.png", "assets/clips/only_paper.mp4",
                            "assets/clips/only_paper.png", "assets/clips/dark/sweep.mp4",
                            "assets/clips/dark/sweep.png"))
    r = lk_build(deck, "--to", "live", "--profile", "dark")
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    html = (deck / "_build-dark" / "slides-live.html").read_text()
    assert 'src="assets/clips/dark/sweep.mp4"' in html and 'poster="assets/clips/dark/sweep.png"' in html
    assert 'src="assets/clips/only_paper.mp4"' in html                 # falls back to the paper index
    r = lk_build(deck, "--to", "live")
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    html = (deck / "_build" / "slides-live.html").read_text()
    assert 'src="assets/clips/sweep.mp4"' in html and "clips/dark/" not in html


# ---------------------------------------------------------------- lk build
def test_version_compatibility():
    from lecturekit.build import compatible
    assert compatible("0.3.0", "0.3.2")
    assert not compatible("0.2.0", "0.3.0")                            # minor counts while the major is 0
    assert compatible("1.2.0", "1.4.1")
    assert not compatible("1.0.0", "2.0.0")


def test_output_dir_follows_the_profile(tmp_path):
    from lecturekit.build import output_dir
    (tmp_path / "_quarto.yml").write_text("project:\n  output-dir: _build\n")
    (tmp_path / "_quarto-dark.yml").write_text("project:\n  output-dir: _build-dark\nbrand: _brand-dark.yml\n")
    (tmp_path / "_quarto-print.yml").write_text("brand: _brand.yml\n")
    assert output_dir(tmp_path) == tmp_path / "_build"
    assert output_dir(tmp_path, "dark") == tmp_path / "_build-dark"
    assert output_dir(tmp_path, "print") == tmp_path / "_build"                 # the profile keeps the base's
    assert output_dir(tmp_path / "nowhere") == tmp_path / "nowhere" / "_build"


def test_filter_errors_are_found():
    from lecturekit.build import filter_errors
    out = ("\x1b[91mERROR (/p/_extensions/lecturekit/filters/dual-output.lua:217) Wrap a movie in .live-only\x1b[39m\n"
           "ERROR (lecturekit) No still for the study PDF (movie \"a\" on slide \"B\")\n"
           "\x1b[91mERROR: ERROR (lecturekit) No still for the study PDF (movie \"a\" on slide \"B\")\n"
           "ERROR (/opt/quarto/share/filters/main.lua:10) not ours\n")
    assert filter_errors(out) == ["Wrap a movie in .live-only (dual-output.lua)",
                                  'No still for the study PDF (movie "a" on slide "B")']


def test_build_fails_on_a_logged_filter_error(tmp_path, monkeypatch):
    """Quarto exits 0 after a filter's error() (a logger); lk build does not."""
    from lecturekit import build as b
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "_quarto.yml").write_text("project:\n  type: default\n")
    os.symlink(EXTENSION, proj / "_extensions")
    seen = {}

    def fake_run(cmd, cwd=None, env=None, **kw):
        seen["env"] = env
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr=(
            "ERROR (/x/_extensions/lecturekit/filters/dual-output.lua:217) Wrap a movie in .live-only\nOutput created\n"))
    monkeypatch.setattr(b.subprocess, "run", fake_run)
    monkeypatch.setattr(b, "quarto_exe", lambda: "quarto")
    monkeypatch.delenv("QUARTO_PYTHON", raising=False)
    assert b.build(proj) == 1
    assert seen["env"]["QUARTO_PYTHON"] == sys.executable
    monkeypatch.setenv("QUARTO_PYTHON", "/some/python")
    b.build(proj)
    assert seen["env"]["QUARTO_PYTHON"] == "/some/python"              # an explicit choice stands


@needs_quarto
def test_prerender_uses_lk_build_python(tmp_path):
    """make_assets.py runs on the Python lk build runs on, even when python3 on PATH is another one."""
    here = os.path.dirname(sys.executable)
    path = os.pathsep.join(p for p in os.environ.get("PATH", "").split(os.pathsep) if p and Path(p) != Path(here))
    other = shutil.which("python3", path=path)
    # a venv's python links to the base interpreter's binary, so compare the paths as given, not resolved
    if other and os.path.abspath(other) == os.path.abspath(sys.executable):
        pytest.skip("python3 on PATH is this interpreter")
    proj = tmp_path / "p"
    proj.mkdir()
    os.symlink(EXTENSION, proj / "_extensions")
    (proj / "_quarto.yml").write_text("project:\n  type: default\n  pre-render: which_python.py\n  render:\n    - doc.qmd\n")
    (proj / "which_python.py").write_text("import sys, pathlib\npathlib.Path('python.txt').write_text(sys.executable)\n")
    (proj / "doc.qmd").write_text("---\ntitle: x\n---\n\nText.\n")
    env = {k: v for k, v in os.environ.items() if k != "QUARTO_PYTHON"}
    env["PATH"] = path + os.pathsep + os.path.dirname(shutil.which("quarto"))
    r = run([sys.executable, "-m", "lecturekit.cli", "build", str(proj)], env=env)
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    assert os.path.abspath((proj / "python.txt").read_text()) == os.path.abspath(sys.executable)


# ---------------------------------------------------------------- the review server
def test_range_server(tmp_path):
    from lecturekit.review.browser import served
    data = bytes(range(256)) * 40
    (tmp_path / "clip.mp4").write_bytes(data)

    def get(url, rng=None):
        req = urllib.request.Request(url, headers={"Range": rng} if rng else {})
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), b""

    with served(tmp_path) as url:
        status, headers, body = get(url + "clip.mp4", "bytes=100-199")
        assert status == 206 and body == data[100:200]
        assert headers["Content-Range"] == f"bytes 100-199/{len(data)}"
        status, headers, body = get(url + "clip.mp4", "bytes=-10")
        assert status == 206 and body == data[-10:]
        status, headers, body = get(url + "clip.mp4", "bytes=10000-")
        assert status == 206 and body == data[10000:]
        status, headers, body = get(url + "clip.mp4")
        assert status == 200 and body == data and headers["Accept-Ranges"] == "bytes"
        status, headers, _ = get(url + "clip.mp4", f"bytes={len(data)}-")
        assert status == 416 and headers["Content-Range"] == f"bytes */{len(data)}"


# ---------------------------------------------------------------- the frags check
@needs_quarto
@needs_browser
def test_frags_flags_the_reverse_form_only(tmp_path):
    from lecturekit.review.frags import frags
    entry = {"video": "assets/clips/bar_bold.mp4", "still": "assets/clips/bar_bold.png", "width": 960, "height": 540}
    slides = """## Prescribed {role=example}

::: {.fragment}
:::: {.live-only}
::: {.movie src="assets/clips/bar_bold.mp4"}
:::
::::
:::

## Reverse {role=example}

:::: {.live-only}
::: {.fragment}
::: {.movie src="assets/clips/bar_bold.mp4"}
:::
:::
::::

## Clip in a fragment {role=example}

::: {.fragment}
::: {.movie clip="bar_bold"}
:::
:::

## Sequence {role=example}

:::: {.live-only}
::::: {.r-stack}
::: {.movie src="assets/clips/bar_bold.mp4"}
:::
:::: {.fragment}
::: {.movie src="assets/clips/bar_bold.mp4"}
:::
::::
:::::
::::
"""
    deck = make_deck(tmp_path / "deck", slides, {"bar_bold": entry},
                     files=("assets/clips/bar_bold.mp4", "assets/clips/bar_bold.png"))
    r = lk_build(deck, "--to", "live")
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    html = deck / "_build" / "slides-live.html"
    assert frags(html, tmp_path / "f", [2]) == 0                      # .fragment > .live-only > .movie
    assert frags(html, tmp_path / "f", [3]) == 1                      # .live-only > .fragment > .movie
    assert frags(html, tmp_path / "f", [4]) == 0                      # a clip= movie boxes itself
    assert frags(html, tmp_path / "f", [5]) == 0                      # an r-stack step


# ---------------------------------------------------------------- the live runtime, real keys
@pytest.fixture(scope="module")
def features_live():
    link = FEATURES / "_extensions"
    if not link.exists() and not link.is_symlink():
        os.symlink("../../_extensions", link)
    r = lk_build(FEATURES, "--to", "live")
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    return FEATURES / "_build" / "slides-live.html"


@pytest.fixture()
def deck(features_live):
    from lecturekit.review.browser import _browsers_path, served
    from playwright.sync_api import sync_playwright
    _browsers_path()
    errors: list[str] = []
    with served(features_live) as url, sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url)
        page.wait_for_function("() => window.Reveal && Reveal.isReady()")
        # the stand-in clip is 1.5 s: looping keeps a clip that should play playing while the test looks
        page.evaluate("() => document.querySelectorAll('video').forEach(v => { v.loop = true; })")
        try:
            yield page, context, errors
        finally:
            browser.close()
    assert not errors, errors


STATE_JS = """() => {
  const slides = [...document.querySelectorAll('.reveal .slides > section')];
  const cur = Reveal.getCurrentSlide();
  const shown = v => { for (let n = v; n && n.tagName !== 'SECTION'; n = n.parentElement) {
      const cs = getComputedStyle(n);
      if (cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) === 0) return false; }
    return true; };
  const vids = [...document.querySelectorAll('.reveal .slides video')].map(v => ({
    slide: slides.indexOf(v.closest('.reveal .slides > section')), src: v.getAttribute('src').split('/').pop(),
    playing: !v.paused, t: v.currentTime, present: cur.contains(v), shown: cur.contains(v) && shown(v) }));
  return { h: Reveal.getState().indexh, f: Reveal.getState().indexf, scroll: Reveal.isScrollView(), vids };
}"""


def state(page, settle=450):
    page.wait_for_timeout(settle)          # past the r-stack fade (250 ms), so a covered step reads as hidden
    return page.evaluate(STATE_JS)


def playing(st):
    return [(v["src"], v["slide"]) for v in st["vids"] if v["playing"]]


def no_hidden_playback(st):
    bad = [v for v in st["vids"] if v["playing"] and not v["shown"]]
    assert not bad, bad


def index_of(page, title: str) -> int:
    return page.evaluate("""(t) => [...document.querySelectorAll('.reveal .slides > section')]
      .findIndex(s => { const h = s.querySelector(':scope > h2'); return h && h.textContent.trim() === t; })""", title)


@needs_quarto
@needs_browser
def test_sequence_forward_plays_one_step(deck):
    page, _, _ = deck
    keypress, seq = index_of(page, "A clip on a key press"), index_of(page, "A sequence of clips")
    page.evaluate("(h) => Reveal.slide(h, 0, -1)", keypress)
    st = state(page)
    no_hidden_playback(st)
    assert playing(st) == []                                           # the clip waits for its fragment
    page.keyboard.press("ArrowRight")
    st = state(page)
    assert playing(st) == [("bar_bold.mp4", keypress)]
    page.keyboard.press("ArrowRight")                                  # onto the sequence: step 0 only
    st = state(page)
    assert st["h"] == seq
    no_hidden_playback(st)
    assert playing(st) == [("bar_bold.mp4", seq)]
    page.keyboard.press("ArrowRight")                                  # step 1 covers step 0, which stops
    st = state(page, settle=300)
    no_hidden_playback(st)
    assert playing(st) == [("bar_back.mp4", seq)]
    step1 = next(v for v in st["vids"] if v["src"] == "bar_back.mp4")
    assert step1["t"] < 0.9                                            # from its first frame
    page.keyboard.press("ArrowLeft")                                   # back to step 0: it starts again
    st = state(page, settle=300)
    no_hidden_playback(st)
    assert playing(st) == [("bar_bold.mp4", seq)]
    assert next(v for v in st["vids"] if v["slide"] == seq and v["src"] == "bar_bold.mp4")["t"] < 0.9


@needs_quarto
@needs_browser
def test_sequence_entered_backwards_plays_the_top_step(deck):
    page, _, _ = deck
    seq = index_of(page, "A sequence of clips")
    page.evaluate("(h) => Reveal.slide(h, 0)", seq + 1)
    state(page)
    page.keyboard.press("ArrowLeft")                                   # back onto the sequence, all steps shown
    st = state(page)
    assert (st["h"], st["f"]) == (seq, 0)
    no_hidden_playback(st)
    assert playing(st) == [("bar_back.mp4", seq)]
    page.keyboard.press("ArrowLeft")
    st = state(page, settle=300)
    no_hidden_playback(st)
    assert playing(st) == [("bar_bold.mp4", seq)]


@needs_quarto
@needs_browser
def test_jumps_play_nothing_hidden(deck):
    page, _, _ = deck
    seq, keypress = index_of(page, "A sequence of clips"), index_of(page, "A clip on a key press")
    for h, f, expect in [(seq, 0, [("bar_back.mp4", seq)]), (keypress, -1, []), (seq, -1, [("bar_bold.mp4", seq)]),
                         (keypress, 0, [("bar_bold.mp4", keypress)]), (1, None, [])]:
        if f is None:
            page.evaluate("(h) => Reveal.slide(h)", h)
        else:
            page.evaluate("([h, f]) => Reveal.slide(h, 0, f)", [h, f])
        st = state(page)
        no_hidden_playback(st)
        assert playing(st) == expect, (h, f, st)


@needs_quarto
@needs_browser
def test_space_toggles_the_clip_and_otherwise_advances(deck):
    page, _, _ = deck
    clip = index_of(page, "A clip, autoplaying")
    page.evaluate("(h) => Reveal.slide(h)", clip)
    assert playing(state(page)) == [("bar_bold.mp4", clip)]
    page.keyboard.press("Space")
    st = state(page, settle=200)
    assert st["h"] == clip and playing(st) == []                       # paused, the slide stays
    page.keyboard.press("Space")
    st = state(page, settle=200)
    assert st["h"] == clip and playing(st) == [("bar_bold.mp4", clip)]
    page.evaluate("(h) => Reveal.slide(h)", clip - 1)                  # a slide without a clip
    page.keyboard.press("Space")
    assert state(page, settle=200)["h"] == clip


@needs_quarto
@needs_browser
def test_r_replays_without_scroll_view(deck):
    page, _, _ = deck
    clip = index_of(page, "A clip, autoplaying")
    page.evaluate("(h) => Reveal.slide(h)", clip)
    state(page, settle=900)
    page.keyboard.press("Space")                                       # pause it mid-way
    paused_at = next(v for v in state(page, settle=150)["vids"] if v["slide"] == clip)["t"]
    page.keyboard.press("r")
    st = state(page, settle=150)
    assert st["scroll"] is False and st["h"] == clip
    v = next(v for v in st["vids"] if v["slide"] == clip)
    assert v["playing"] and v["t"] < 0.6, (paused_at, v)
    page.keyboard.press("R")
    st = state(page, settle=150)
    assert st["scroll"] is False and st["h"] == clip


@needs_quarto
@needs_browser
def test_p_resets_the_clock_and_stays(deck):
    page, _, _ = deck
    seq = index_of(page, "A sequence of clips")
    page.evaluate("(h) => Reveal.slide(h, 0, 0)", seq)
    state(page)
    before = time.time() * 1000
    page.keyboard.press("p")
    st = state(page, settle=200)
    assert (st["h"], st["f"]) == (seq, 0)                              # no previous slide, no previous fragment
    reset = float(page.evaluate("() => document.documentElement.getAttribute('data-lk-clock-reset')"))
    assert reset >= before - 1000


@needs_quarto
@needs_browser
def test_speaker_window(deck):
    """Keys in the speaker window reach the bindings through triggerKey: Space pauses the main window's clip, P
    resets the pacing clock; the previews never play a clip."""
    page, context, _ = deck
    clip = index_of(page, "A clip, autoplaying")
    page.evaluate("(h) => Reveal.slide(h)", clip)
    state(page)
    with context.expect_page() as popup:
        page.keyboard.press("s")
    speaker = popup.value
    speaker.wait_for_load_state()
    previews = []
    for _ in range(40):
        previews = [f for f in speaker.frames[1:] if f.evaluate("() => !!(window.Reveal && Reveal.isReady && Reveal.isReady())")]
        if len(previews) == 2:
            break
        speaker.wait_for_timeout(250)
    assert len(previews) == 2
    speaker.wait_for_timeout(2600)
    clock = "() => document.querySelector('.lk-pacing').textContent"
    clocks = [f.evaluate(clock) for f in previews]
    assert all(c.startswith("elapsed 0:0") and not c.startswith(("elapsed 0:00", "elapsed 0:01")) for c in clocks), clocks
    playing_in_previews = "() => [...document.querySelectorAll('video')].filter(v => !v.paused).length"
    assert [f.evaluate(playing_in_previews) for f in previews] == [0, 0]
    assert playing(state(page, settle=0)) == [("bar_bold.mp4", clip)]
    speaker.keyboard.press("Space")
    speaker.wait_for_timeout(400)
    st = state(page, settle=0)
    assert st["h"] == clip and playing(st) == []                       # the main window's clip paused
    speaker.keyboard.press("Space")
    speaker.wait_for_timeout(400)
    assert playing(state(page, settle=0)) == [("bar_bold.mp4", clip)]
    assert [f.evaluate(playing_in_previews) for f in previews] == [0, 0]
    speaker.keyboard.press("p")
    speaker.wait_for_timeout(1300)
    clocks = [f.evaluate(clock) for f in previews]
    assert all(c.startswith(("elapsed 0:00", "elapsed 0:01")) for c in clocks), clocks          # both previews reset
    assert state(page, settle=0)["h"] == clip
