"""A clip in parts: the filter's markup and checks, the runtime with real key presses, the study strip, the timing
line and `lk review frags`.

The oracle is a barcode clip: every frame carries its own index as ten black and white blocks, so the frame a
browser shows is read back from its pixels. The picture rests for 0.5 s on each side of the stops at 3, 6 and 9 s.
Three encodings: `k30` (30 fps, keyframes at the stops), `g30` (30 fps, GOP 250 and moov at the end) and `k60` (60
fps). The fixture deck's clips.json is a format 2 index written here by hand from ffprobe, as `lk clips` would write
it, so these tests do not depend on the producer side. The browser tests need quarto and Playwright's Chromium; the
study tests need xelatex and pymupdf. They are pinned to the Quarto this was checked with (1.11.9, reveal.js 5.1.0),
whose event order the runtime relies on.
"""

from __future__ import annotations

import contextlib
import functools
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "examples" / "features"
EXTENSION = ROOT / "_extensions"
QUARTO_PINNED = "1.11.9"


def _quarto_version() -> str | None:
    exe = shutil.which("quarto")
    if not exe:
        return None
    r = subprocess.run([exe, "--version"], capture_output=True, text=True)
    return r.stdout.strip() or None


def _chromium() -> bool:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return False
    return True


QUARTO = _quarto_version()
needs_quarto = pytest.mark.skipif(QUARTO is None, reason="quarto not installed")
pinned = pytest.mark.skipif(QUARTO != QUARTO_PINNED, reason=f"the runtime is checked against Quarto {QUARTO_PINNED}")
needs_browser = pytest.mark.skipif(not _chromium(), reason="playwright not installed")
needs_tex = pytest.mark.skipif(shutil.which("xelatex") is None, reason="xelatex not installed")
needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
                                  reason="ffmpeg not installed")


def run(cmd, cwd=None, env=None):
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)


def lk_build(project: Path, *args: str):
    return run([sys.executable, "-m", "lecturekit.cli", "build", str(project), *args])


# ---------------------------------------------------------------- the barcode clips
W, H, BITS, BLK = 640, 360, 10, 56
STOP_S = (3.0, 6.0, 9.0)
REST_S = 0.5
STOP_IDS = ("lenient", "neutral", "strict")
SECONDS = 12


def _frame(n: int, fps: int, total: int):
    from PIL import Image, ImageDraw
    t = n / fps
    img = Image.new("RGB", (W, H), (235, 238, 242))
    d = ImageDraw.Draw(img)
    for b in range(BITS):                                   # bit b of n, most significant first
        on = (n >> (BITS - 1 - b)) & 1
        x0 = 20 + b * (BLK + 4)
        d.rectangle([x0, 8, x0 + BLK, 8 + BLK], fill=(255, 255, 255) if on else (0, 0, 0))
    tt = t
    for s in STOP_S:                                        # the dot rests around each stop
        if abs(t - s) <= REST_S:
            tt = s
    x = 40 + (W - 80) * (tt / (total / fps))
    d.ellipse([x - 22, 200 - 22, x + 22, 200 + 22], fill=(78, 134, 198))
    return img


def _ffprobe_frames(path: Path) -> list[tuple[int, float]]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=key_frame,pts_time",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True).stdout.split()
    rows = []
    for r in out:
        k, t = r.split(",")[:2]
        rows.append((int(k), float(t)))
    return rows


def _still(video: Path, frame: int, out: Path) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-vf", f"select=eq(n\\,{frame})",
                    "-fps_mode", "passthrough", "-frames:v", "1", str(out)], check=True)


def make_clip(clips: Path, name: str, fps: int, gop: int | None = None, faststart: bool = True,
              ids=STOP_IDS) -> dict:
    """Encode a barcode clip into `clips` with its stills by frame number, and return its format 2 entry."""
    total = fps * SECONDS
    stops = [int(round(s * fps)) for s in STOP_S]
    path = clips / f"{name}.mp4"
    args = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps),
            "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18"]
    if gop:
        args += ["-g", str(gop), "-sc_threshold", "0"]
    else:
        args += ["-force_key_frames", "expr:" + "+".join(f"eq(n,{k})" for k in [0] + stops)]
    if faststart:
        args += ["-movflags", "+faststart"]
    p = subprocess.Popen(args + [str(path)], stdin=subprocess.PIPE)
    for n in range(total):
        p.stdin.write(_frame(n, fps, total).tobytes())
    p.stdin.close()
    assert p.wait() == 0
    rows = _ffprobe_frames(path)
    assert len(rows) == total
    rel = f"assets/clips/{name}"
    for k in [0] + stops + [total - 1]:
        _still(path, k, clips / f"{name}.f{k:04d}.png")
    rest = int(round(REST_S * fps))
    return {
        "format": 2, "producer": "external", "video": f"{rel}.mp4",
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "poster": f"{rel}.f0000.png", "still": f"{rel}.f{total - 1:04d}.png",
        "width": W, "height": H, "fps": fps, "frames": total, "duration": float(SECONDS),
        "source": "tests/test_segments.py (barcode)", "revision": "barcode",
        "stops": [{"id": i, "frame": f, "pts": rows[f][1], "label": i.replace("_", " "),
                   "notes": f"The dot rests at {s:g} s.", "still": f"{rel}.f{f:04d}.png",
                   "rest_before": rest, "rest_after": rest, "frozen": []}
                  for i, f, s in zip(ids, stops, STOP_S)],
        "end": {"frame": total - 1, "pts": rows[total - 1][1], "still": f"{rel}.f{total - 1:04d}.png"},
    }


@pytest.fixture(scope="session")
def barcode(tmp_path_factory):
    """The three barcode clips and their format 2 entries, made once per session."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not installed")
    pytest.importorskip("PIL")
    clips = tmp_path_factory.mktemp("barcode") / "assets" / "clips"
    clips.mkdir(parents=True)
    index = {"k30": make_clip(clips, "k30", 30), "g30": make_clip(clips, "g30", 30, gop=250, faststart=False),
             "k60": make_clip(clips, "k60", 60)}
    return clips, index


def make_deck(where: Path, slides: str, barcode, index: dict | None = None, header: str = "") -> Path:
    """A project beside the engine: the features deck's brands, the extension by symlink, the barcode clips and
    stills, a format 2 index (the barcode one unless given) and the given slides."""
    clips, entries = barcode
    where.mkdir(parents=True, exist_ok=True)
    os.symlink(EXTENSION, where / "_extensions")
    for name in ("_brand.yml", "_brand-dark.yml", "_quarto.yml", "_quarto-dark.yml"):
        shutil.copy2(FEATURES / name, where / name)
    dst = where / "assets" / "clips"
    dst.mkdir(parents=True)
    for f in clips.iterdir():
        shutil.copy2(f, dst / f.name)
    shutil.copy2(FEATURES / "assets" / "clips" / "bar_bold.mp4", dst / "bar_bold.mp4")
    shutil.copy2(FEATURES / "assets" / "clips" / "bar_bold.png", dst / "bar_bold.png")
    (dst / "clips.json").write_text(json.dumps(entries if index is None else index, indent=2))
    (where / "slides.qmd").write_text('---\ntitle: "Fixture"\nbudget: 10\n' + header + '---\n\n' + slides)
    return where


# ---------------------------------------------------------------- the runtime deck
RUNTIME_SLIDES = """## Before {role=example}

A slide before the clip.

## Clip in parts {role=example time=2}

::: {.movie clip="k30" stops="all" label="barcode"}
The dot moves, rests, moves.

:::: {.stop ref="lenient"}
Ask: where does the dot go next?
::::
:::: {.stop ref="neutral"}
Ask: and after that?
::::
:::: {.stop ref="end"}
Say: that is the whole sweep.
::::
:::

::: notes
Slide notes: the clip runs in four parts.
:::

## After {role=example}

:::: {.live-only}
::: {.movie src="assets/clips/bar_bold.mp4" label="ordinary clip"}
:::
::::

::: {.study-only}
![](assets/clips/bar_bold.png){height=30mm}
:::

## Mid-GOP clip {role=example}

::: {.movie clip="g30" stops="lenient neutral strict"}
:::

## Key start {role=example}

::: {.movie clip="k60" stops="all" start=key}
:::: {.stop ref="start"}
Ask: what will the dot do?
::::
:::

## End {role=example}

The end.
"""
# slide indices (0-based, Reveal's h): title 0, Before 1, Clip in parts 2, After 3, Mid-GOP 4, Key start 5, End 6
K30, G30, K60 = 2, 4, 5
F30 = [0, 90, 180, 270, 359]
F60 = [0, 180, 360, 540, 719]

# In the page: the frame index read off the video's barcode, the runtime's state with it, and a monitor that samples
# every 20 ms whether any video plays while it is not shown on the present slide.
HELPERS = r"""
window.__readFrame = function (v) {
  const c = document.createElement('canvas'); c.width = v.videoWidth; c.height = v.videoHeight;
  const g = c.getContext('2d'); g.drawImage(v, 0, 0); const sx = c.width / 640; let n = 0;
  for (let b = 0; b < 10; b++) {
    const x = Math.round((20 + b * 60 + 28) * sx), y = Math.round(36 * sx);
    const d = g.getImageData(x - 3, y - 3, 7, 7).data; let s = 0;
    for (let i = 0; i < d.length; i += 4) s += d[i] + d[i + 1] + d[i + 2];
    n = (n << 1) | (s / (d.length / 4) / 3 > 128 ? 1 : 0);
  }
  return n;
};
window.__seg = function (id) {
  const s = window.lecturekitSegments && lecturekitSegments.state(id); if (!s) return null;
  const st = lecturekitSegments.clips.find(c => c.id === id);
  s.barcode = (st.v.readyState >= 2 && s.driving) ? __readFrame(st.v) : null;
  s.hidden = document.querySelectorAll('.lk-seg video[src]').length;
  return s;
};
window.__viol = [];
function __shown(v) {
  if (!v.closest('section.present')) return false;
  for (let n = v; n && n.tagName !== 'SECTION'; n = n.parentElement) {
    if (n.classList && n.classList.contains('fragment') && !n.classList.contains('visible')) return false;
    const p = n.parentElement;
    if (p && p.classList && p.classList.contains('r-stack'))
      for (let s = n.nextElementSibling; s; s = s.nextElementSibling)
        if (s.classList.contains('fragment') && s.classList.contains('visible')) return false;
  }
  return true;
}
setInterval(() => {
  document.querySelectorAll('.reveal video').forEach(v => {
    if (!v.paused && (!__shown(v) || document.hidden || (window.Reveal && Reveal.isOverview && Reveal.isOverview())))
      window.__viol.push([Math.round(performance.now()), v.getAttribute('aria-label'), +v.currentTime.toFixed(3)]);
  });
}, 20);
"""


@pytest.fixture(scope="module")
def runtime_deck(tmp_path_factory, barcode):
    if QUARTO is None:
        pytest.skip("quarto not installed")
    deck = make_deck(tmp_path_factory.mktemp("runtime") / "deck", RUNTIME_SLIDES, barcode)
    r = lk_build(deck, "--to", "live")
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    return deck / "_build" / "slides-live.html"


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@contextlib.contextmanager
def served_without_ranges(html: Path):
    """A static server that ignores Range: a clip it serves cannot be sought, so the runtime fetches it into a Blob."""
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(html.parent)))
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}/{html.name}"
    finally:
        srv.shutdown()
        srv.server_close()


@contextlib.contextmanager
def browser_page(html: Path, ranges: bool = True, init: str = "", query: str = "", hash_: str = "#/1"):
    from lecturekit.review.browser import _browsers_path, served
    from playwright.sync_api import sync_playwright
    _browsers_path()
    server = served(html) if ranges else served_without_ranges(html)
    errors: list[str] = []
    with server as url, sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        context.add_init_script(HELPERS + init)
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url + query + hash_)
        page.wait_for_function("() => window.Reveal && Reveal.isReady() && window.lecturekitSegments")
        page.wait_for_timeout(400)
        try:
            yield page, context, url
        finally:
            browser.close()
    assert not errors, errors


def seg(page, cid="k30"):
    return page.evaluate("id => __seg(id)", cid)


def wait_hold(page, b, cid="k30", timeout=15.0):
    """Wait for the clip to hold boundary b; its state, with the barcode read 150 ms later (a late frame would show)."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        s = seg(page, cid)
        if s and s["phase"] == "holding" and s["at"] == b:
            page.wait_for_timeout(150)
            return seg(page, cid)
        page.wait_for_timeout(10)
    raise AssertionError(f"no hold on boundary {b}: {seg(page, cid)}")


def assert_hold(page, b, frames, cid="k30", plays=None):
    s = wait_hold(page, b, cid)
    assert s["barcode"] == frames[b] and s["frame"] == frames[b] and s["paused"], s
    if plays is not None:
        assert s["plays"] == plays, ("it played", s)
    return s


def no_hidden_playback(page):
    viol = page.evaluate("window.__viol")
    assert not viol, viol[:10]


def notes_text(html: str) -> list[str]:
    """The text of each speaker-notes aside in a piece of HTML, in order."""
    out = []
    for n in re.findall(r'<aside class="notes">(.*?)</aside>', html, re.S):
        out.append(" ".join(re.sub(r"<style.*?</style>|<[^>]+>", " ", n, flags=re.S).split()))
    return out


@needs_quarto
@pinned
def test_markup(runtime_deck):
    html = runtime_deck.read_text()
    sec = html[html.index('<section id="clip-in-parts"'):]
    sec = sec[:sec.index("</section>")]
    assert "data-autoplay" not in sec and "data-lk-autoplay" not in sec
    assert 'data-lk-src="assets/clips/k30.mp4"' in sec and ' src="assets' not in sec       # only the runtime sets src
    sha8 = json.loads((runtime_deck.parent.parent / "assets/clips/clips.json").read_text())["k30"]["sha256"][:8]
    assert f'data-lk-v="{sha8}"' in sec and f"k30.f0000.png?v={sha8}" in sec
    assert len(re.findall(r'<img class="lk-still"', sec)) == 5                              # one still per boundary
    assert len(re.findall(r'class="fragment lk-cue"', sec)) == 3                            # a key per stop (auto)
    key = html[html.index('<section id="key-start"'):]
    key = key[:key.index("</section>")]
    assert len(re.findall(r'class="fragment lk-cue"', key)) == 4                            # start=key adds one
    # notes: the Ask first, then the part, then what is on screen, then the slide's own notes; nowhere else
    text = notes_text(sec)
    assert len(text) == 4                                                                    # the slide's and three cues'
    assert text[0].startswith("Ask: where does the dot go next? Part 1 of 4, 3.0 seconds: holds on lenient.")
    assert text[0].endswith("On screen: The dot rests at 3 s. Slide notes: the clip runs in four parts.")
    assert text[1].startswith("Ask: and after that? Part 2 of 4")
    assert text[2].startswith("Part 3 of 4, 3.0 seconds: holds on strict.")
    assert text[3].startswith("Say: that is the whole sweep. Part 4 of 4, 3.0 seconds: holds on the last frame.")
    assert all(t.endswith("Slide notes: the clip runs in four parts.") for t in text)
    assert notes_text(key)[0] == "Ask: what will the dot do? Frame 0: part 1 of 4 (3.0 seconds) plays on the next key."


@needs_quarto
@needs_browser
@pinned
def test_forward_holds_exact_frames_and_back_never_plays(runtime_deck):
    with browser_page(runtime_deck) as (page, _, _):
        s = seg(page)
        assert s["src"] and s["paused"] and s["plays"] == 0                                  # the neighbour is loaded
        page.keyboard.press("ArrowRight")                                                    # enter: part 1 plays
        pauses = []
        for b in (1, 2, 3, 4):
            if b > 1:
                page.keyboard.press("ArrowRight")
            s = assert_hold(page, b, F30)
            pauses.append(s["lastPause"]["frame"])
        # the pause lands early, never late: at most the two-frame guard and a frame of latency before the stop
        assert all(F30[b] - 4 <= f <= F30[b] for b, f in zip((1, 2, 3, 4), pauses)), pauses
        plays = s["plays"]
        for b in (3, 2, 1):
            page.keyboard.press("ArrowLeft")
            assert_hold(page, b, F30, plays=plays)                                           # at once, no play
        page.keyboard.press("ArrowLeft")                                                     # leave backwards
        page.wait_for_timeout(300)
        s = seg(page)
        assert s["phase"] == "static" and s["paused"] and page.evaluate("Reveal.getIndices().h") == 1
        no_hidden_playback(page)


@needs_quarto
@needs_browser
@pinned
def test_without_frame_callbacks_the_timeupdate_path_holds_exactly(runtime_deck):
    """The fallback for a browser without requestVideoFrameCallback pauses up to 0.3 s early, then seeks."""
    with browser_page(runtime_deck, query="?lk-timeupdate", hash_="#/2") as (page, _, _):
        s = assert_hold(page, 1, F30)
        assert F30[1] - 12 <= s["lastPause"]["frame"] <= F30[1], s["lastPause"]               # early, never late
        page.keyboard.press("ArrowRight")
        s = assert_hold(page, 2, F30)
        assert F30[2] - 12 <= s["lastPause"]["frame"] <= F30[2], s["lastPause"]
        no_hidden_playback(page)


@needs_quarto
@needs_browser
@pinned
def test_a_key_during_a_part_plays_through(runtime_deck):
    with browser_page(runtime_deck, hash_="#/2") as (page, _, _):
        assert_hold(page, 1, F30)
        page.keyboard.press("ArrowRight")                                                    # part 2 plays
        page.wait_for_timeout(700)
        assert seg(page)["phase"] == "playing"
        page.keyboard.press("ArrowRight")                                                    # mid-part: on to the next stop
        s = assert_hold(page, 3, F30)
        log = [m for _, _, m in page.evaluate("lecturekitSegments.log")]
        assert "target -> 3" in log and not [m for m in log if m.startswith("reached 2")], log[-12:]
        assert s["lastPause"]["b"] == 3
        page.keyboard.press("ArrowRight")
        page.keyboard.press("ArrowLeft")                                                     # back during the last part
        s = assert_hold(page, 3, F30)
        no_hidden_playback(page)


@needs_quarto
@needs_browser
@pinned
def test_backward_entry_holds_the_last_frame_and_reposts_the_notes(runtime_deck):
    with browser_page(runtime_deck, hash_="#/3") as (page, context, _):
        page.wait_for_timeout(500)
        assert not page.evaluate("document.querySelector('#after video').paused")            # the ordinary clip plays
        with context.expect_page() as popup:
            page.keyboard.press("s")
        speaker = popup.value
        speaker.wait_for_load_state()
        speaker.wait_for_timeout(3000)
        notes = "() => (document.querySelector('.speaker-controls-notes .value') || {}).textContent || ''"
        plays = seg(page)["plays"]
        page.bring_to_front()
        page.keyboard.press("ArrowLeft")                                                     # back onto the clip
        assert_hold(page, 4, F30, plays=plays)
        assert page.evaluate("document.querySelector('#after video').paused")
        speaker.wait_for_timeout(800)
        assert "Say: that is the whole sweep." in speaker.evaluate(notes)                    # the last cue's notes
        page.keyboard.press("ArrowLeft")
        assert_hold(page, 3, F30, plays=plays)
        speaker.wait_for_timeout(800)
        assert "holds on strict" in speaker.evaluate(notes)
        # Space pressed in the speaker window: at a hold it is the next key, and a playing part pauses
        speaker.bring_to_front()
        speaker.keyboard.press(" ")
        t0 = time.monotonic()
        while seg(page)["phase"] != "playing" and time.monotonic() - t0 < 5:
            page.wait_for_timeout(20)
        page.wait_for_timeout(300)
        speaker.keyboard.press(" ")
        page.wait_for_timeout(500)
        s1 = seg(page)
        page.wait_for_timeout(400)
        s2 = seg(page)
        assert s1["phase"] == "paused" and s1["k"] == 3 and abs(s1["t"] - s2["t"]) < 1e-3, (s1, s2)
        previews = [f for f in speaker.frames[1:] if "receiver" in f.url]
        assert previews and all(f.evaluate("() => !document.querySelector('.lk-seg video[src]')") for f in previews)
        speaker.keyboard.press(" ")
        assert_hold(page, 4, F30)
        no_hidden_playback(page)


@needs_quarto
@needs_browser
@pinned
def test_jumps_hold_and_never_play(runtime_deck):
    with browser_page(runtime_deck, hash_="#/clip-in-parts/1") as (page, _, _):            # a hash with a fragment
        assert_hold(page, 3, F30, plays=0)
        page.evaluate("Reveal.slide(6)")
        page.wait_for_timeout(300)
        plays = seg(page)["plays"]
        page.evaluate("location.hash = '#/clip-in-parts/0'")                                 # a hash change
        assert_hold(page, 2, F30, plays=plays)
        page.evaluate("Reveal.slide(0)")
        page.wait_for_timeout(300)
        page.evaluate("Reveal.slide(2, 0, 2)")                                               # a jump with a fragment
        assert_hold(page, 4, F30, plays=plays)
        no_hidden_playback(page)


@needs_quarto
@needs_browser
@pinned
def test_start_key_and_the_mid_gop_clip(runtime_deck):
    with browser_page(runtime_deck, hash_="#/6") as (page, _, _):
        page.keyboard.press("ArrowLeft")                                                     # Key start, entered backwards
        assert_hold(page, 4, F60, "k60", plays=0)
        page.evaluate("Reveal.slide(4, 0, -1)")                                              # the mid-GOP clip
        for b in (1, 2):
            if b > 1:
                page.keyboard.press("ArrowRight")
            assert_hold(page, b, F30, "g30")
        plays = seg(page, "g30")["plays"]
        page.keyboard.press("ArrowLeft")
        assert_hold(page, 1, F30, "g30", plays=plays)
        page.evaluate("Reveal.slide(4, 0, 2)")
        page.keyboard.press("ArrowRight")                                                    # onto Key start, forwards
        s = assert_hold(page, 0, F60, "k60")
        assert s["plays"] == 0 and s["k"] == 0                                               # frame 0 waits for a key
        page.wait_for_timeout(500)
        assert seg(page, "k60")["phase"] == "holding" and seg(page, "k60")["plays"] == 0
        for b in (1, 2):
            page.keyboard.press("ArrowRight")
            assert_hold(page, b, F60, "k60")
        plays = seg(page, "k60")["plays"]
        for b in (1, 0):
            page.keyboard.press("ArrowLeft")
            assert_hold(page, b, F60, "k60", plays=plays)
        no_hidden_playback(page)


@needs_quarto
@needs_browser
@pinned
def test_space_and_r(runtime_deck):
    with browser_page(runtime_deck, hash_="#/2") as (page, _, _):
        assert_hold(page, 1, F30)
        page.keyboard.press("Space")                                                         # at a hold: the next key
        page.wait_for_timeout(500)
        s = seg(page)
        assert s["k"] == 1 and s["phase"] == "playing"
        page.keyboard.press("Space")                                                         # mid-part: pause
        page.wait_for_timeout(200)
        s1 = seg(page)
        page.wait_for_timeout(500)
        s2 = seg(page)
        assert s1["phase"] == "paused" and abs(s1["t"] - s2["t"]) < 1e-3, (s1, s2)
        page.keyboard.press("Space")                                                         # resume
        assert_hold(page, 2, F30)
        page.keyboard.press("r")                                                             # R: the part again
        page.wait_for_timeout(400)
        s = seg(page)
        assert s["phase"] == "playing" and 3.0 <= s["t"] < 6.0, s
        assert not page.evaluate("Reveal.isScrollView()")
        assert_hold(page, 2, F30)
        page.keyboard.press("Shift+Space")                                                   # back
        assert_hold(page, 1, F30)
        page.evaluate("Reveal.slide(2, 0, 2)")
        assert_hold(page, 4, F30)
        page.keyboard.press("Space")                                                         # the last hold: nothing
        page.wait_for_timeout(400)
        assert page.evaluate("Reveal.getIndices()")["h"] == 2 and seg(page)["phase"] == "holding"
        page.click(".present .lk-seg video")                                                 # a click is Space
        page.wait_for_timeout(300)
        assert page.evaluate("Reveal.getIndices()")["h"] == 2
        page.keyboard.press("Escape")                                                        # the overview pauses...
        page.wait_for_timeout(200)
        page.evaluate("Reveal.slide(2, 0, 0)")
        page.keyboard.press("Escape")
        assert_hold(page, 2, F30)
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(600)
        page.keyboard.press("Escape")                                                        # ...a playing part
        page.wait_for_timeout(400)
        assert page.evaluate("Reveal.isOverview()") and seg(page)["phase"] == "paused"
        page.keyboard.press("Escape")                                                        # and it resumes
        assert_hold(page, 3, F30)
        no_hidden_playback(page)


@needs_quarto
@needs_browser
@pinned
def test_a_foreign_play_is_paused_and_the_hold_sought_again(runtime_deck):
    with browser_page(runtime_deck, hash_="#/clip-in-parts/0") as (page, _, _):
        s = assert_hold(page, 2, F30, plays=0)
        page.evaluate("document.querySelector('.present .lk-seg video').play()")           # not the runtime's play
        page.wait_for_timeout(200)
        s = assert_hold(page, 2, F30)
        assert s["plays"] == 1
        assert "a play it did not start: paused" in [m for _, _, m in page.evaluate("lecturekitSegments.log")]
        no_hidden_playback(page)


@needs_quarto
@needs_browser
@pinned
def test_a_clip_that_fails_to_load_degrades_to_its_stills(runtime_deck):
    with browser_page(runtime_deck, hash_="#/1", init="") as (page, _, _):
        page.route("**/k30.mp4*", lambda route: route.abort())
        page.evaluate("document.querySelector('#clip-in-parts .lk-seg video').removeAttribute('src')")
        page.evaluate("(() => { const v = document.querySelector('#clip-in-parts .lk-seg video'); "
                      "v.setAttribute('src', v.getAttribute('data-lk-src') + '?broken'); v.load(); })()")
        page.wait_for_timeout(500)
        assert seg(page)["degraded"]
        page.keyboard.press("ArrowRight")                                                    # onto the clip: no play
        page.wait_for_timeout(400)
        s = seg(page)
        assert s["phase"] == "degraded" and s["stills"] == [1] and s["paused"], s           # the state's hold still
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(300)
        assert seg(page)["stills"] == [2]                                                    # the stills follow the cues
        page.keyboard.press("Space")                                                         # the keys move Reveal only
        page.wait_for_timeout(300)
        assert seg(page)["stills"] == [3] and page.evaluate("Reveal.getIndices()")["h"] == 2


REFUSE = """
(() => { const play = HTMLMediaElement.prototype.play; window.__refuse = true;
  HTMLMediaElement.prototype.play = function () {
    if (window.__refuse && this.closest('.lk-seg'))
      return Promise.reject(new DOMException('play() can only be initiated by a user gesture', 'NotAllowedError'));
    return play.call(this); }; })();
"""


@needs_quarto
@needs_browser
@pinned
def test_a_refused_play_shows_the_part_start(runtime_deck):
    with browser_page(runtime_deck, init=REFUSE, hash_="#/2") as (page, _, _):
        t0 = time.monotonic()
        while seg(page)["phase"] != "blocked" and time.monotonic() - t0 < 5:
            page.wait_for_timeout(20)
        s = seg(page)
        assert s["phase"] == "blocked" and s["stills"] == [0] and not s["driving"], s       # frame 0, not the hold
        page.evaluate("window.__refuse = false")
        page.keyboard.press("Space")                                                         # a gesture: play
        assert_hold(page, 1, F30)


@needs_quarto
@needs_browser
@pinned
def test_without_byte_ranges_the_clip_plays_from_a_blob(runtime_deck):
    with browser_page(runtime_deck, ranges=False, hash_="#/1") as (page, _, _):
        t0 = time.monotonic()
        while not seg(page)["blob"] and time.monotonic() - t0 < 10:
            page.wait_for_timeout(50)
        page.wait_for_timeout(500)
        assert seg(page)["src"].startswith("blob:")
        page.keyboard.press("ArrowRight")
        assert_hold(page, 1, F30)
        page.keyboard.press("ArrowRight")
        assert_hold(page, 2, F30)
        plays = seg(page)["plays"]
        page.keyboard.press("ArrowLeft")
        assert_hold(page, 1, F30, plays=plays)
        page.evaluate("Reveal.slide(4, 0, 0)")                                               # moov at the end, mid-GOP
        assert_hold(page, 2, F30, "g30", plays=0)
        assert seg(page, "g30")["src"].startswith("blob:")
        no_hidden_playback(page)


@needs_quarto
@needs_browser
@pinned
def test_previews_and_print_never_load_the_clip(runtime_deck):
    with browser_page(runtime_deck, query="?receiver", hash_="#/2") as (page, _, _):
        for f, still in ((-1, 1), (0, 2), (1, 3), (2, 4)):                                   # each state shows its hold
            page.evaluate(f"Reveal.setState({{indexh: 2, indexv: 0, indexf: {f}}})")
            page.wait_for_timeout(250)
            s = seg(page)
            assert s["src"] is None and s["stills"] == [still] and s["paused"], (f, s)
        page.evaluate("Reveal.setState({indexh: 5, indexv: 0, indexf: -1})")
        page.wait_for_timeout(250)
        assert seg(page, "k60")["stills"] == [0] and seg(page, "k60")["src"] is None
        assert page.evaluate("document.querySelectorAll('.lk-seg video[src]').length") == 0
    with browser_page(runtime_deck, query="?print-pdf", hash_="") as (page, _, _):
        page.wait_for_timeout(1000)
        for cid in ("k30", "g30", "k60"):
            s = seg(page, cid)
            assert s["src"] is None and s["stills"] == [4], (cid, s)                         # the last hold
        assert page.evaluate("document.querySelectorAll('.lk-seg video[src]').length") == 0


# ---------------------------------------------------------------- the filter's checks
def variants(barcode) -> dict:
    """The barcode index with entries that break one rule each: an old entry without format 2, a stop with too little
    rest before it, and six and five candidates (more than a clip may hold, and the most a strip prints)."""
    clips, index = barcode
    k30 = index["k30"]
    for f in (45, 135):
        if not (clips / f"k30.f{f:04d}.png").exists():
            _still(clips / "k30.mp4", f, clips / f"k30.f{f:04d}.png")
    old = {k: v for k, v in k30.items() if k not in ("format", "stops", "end")}
    tight = json.loads(json.dumps(k30))
    tight["stops"][1]["rest_before"] = 2

    def cands(frames):
        return [{"id": f"s{f}", "frame": f, "pts": f / 30, "label": f"at {f}", "still": f"assets/clips/k30.f{f:04d}.png",
                 "rest_before": 15, "rest_after": 15, "frozen": []} for f in frames]
    six = dict(k30, stops=cands([45, 90, 135, 180, 270, 300]))
    five = dict(k30, stops=cands([45, 90, 135, 180, 270]))
    if not (clips / "tiny.png").exists():                       # 64 by 36 pixels: 22.6 mm at 72 dpi
        from PIL import Image
        Image.new("RGB", (64, 36), (78, 134, 198)).save(clips / "tiny.png")
    tiny = dict(k30, poster="assets/clips/tiny.png", stops=[dict(c, still="assets/clips/tiny.png") for c in k30["stops"]],
                end=dict(k30["end"], still="assets/clips/tiny.png"))
    return dict(index, old=old, tight=tight, six=six, five=five, tiny=tiny)


FATAL = {
    "unknown": ('::: {.movie clip="k30" stops="lenient bogus"}\n:::\n',
                'stops= names "bogus", which is not a stop of clip "k30" (it has lenient, neutral, strict)'),
    "order": ('::: {.movie clip="k30" stops="neutral lenient"}\n:::\n', 'stops= names "lenient" out of order'),
    "src": (':::: {.live-only}\n::: {.movie src="assets/clips/k30.mp4" stops="lenient"}\n:::\n::::\n',
            "stops= needs the clip= form, not src="),
    "format": ('::: {.movie clip="old" stops="lenient"}\n:::\n', "stops= needs a clips.json entry of format 2"),
    "rest": ('::: {.movie clip="tight" stops="lenient neutral"}\n:::\n',
             'The stop "neutral" has 2 frame(s) of unchanged picture before it; a stop needs 3'),
    "many": ('::: {.movie clip="six" stops="all"}\n:::\n', "stops= names 6 stops; a clip holds at 5 at most"),
    "two": ('::: {.movie clip="k30" stops="lenient"}\n:::\n\n::: {.movie clip="k60" stops="lenient"}\n:::\n',
            'Two clips in parts on one slide ("The slide")'),
    "fragment": ('::: {.movie clip="k30" stops="lenient"}\n:::\n\n::: {.fragment}\nA line.\n:::\n',
                 "A clip in parts and another reveal on one slide"),
    "incremental": ('::: {.movie clip="k30" stops="lenient"}\n:::\n\n::: {.incremental}\n- a\n- b\n:::\n',
                    "A clip in parts and another reveal on one slide"),
    "in-fragment": ('::: {.fragment}\n:::: {.movie clip="k30" stops="lenient"}\n::::\n:::\n',
                    'A clip in parts inside a .fragment (movie "k30" on slide "The slide")'),
    "in-stack": (':::: {.live-only}\n::::: {.r-stack}\n::: {.movie clip="k30" stops="lenient"}\n:::\n:::::\n::::\n',
                 "A clip in parts inside an .r-stack"),
    "stop-ref": ('::: {.movie clip="k30" stops="lenient"}\n:::: {.stop ref="neutral"}\nAsk: x?\n::::\n:::\n',
                 '.stop ref="neutral" names no hold of this clip (its holds: lenient, end)'),
    "start-ref": ('::: {.movie clip="k30" stops="lenient"}\n:::: {.stop ref="start"}\nAsk: x?\n::::\n:::\n',
                  "with start=auto part 1 plays on entry, so frame 0 is not a hold"),
    "start": ('::: {.movie clip="k30" stops="lenient" start=later}\n:::\n', "start= is auto or key, not later"),
    "panels": ('::: {.movie clip="six" stops="s90" study="start s45 s90 s135 s180 s270 end"}\n:::\n',
               "study= prints 7 panels; a strip holds 6 at most: name fewer holds in study="),
    "study": ('::: {.movie clip="k30" stops="lenient" study="lenient later"}\n:::\n',
              'study= is strip, final or a list of holds (start, end, lenient, neutral, strict), and "later" is none of them'),
    "stop-unsegmented": ('::: {.movie clip="k30"}\n:::: {.stop ref="end"}\nAsk: x?\n::::\n:::\n',
                         "A .stop block needs stops= on its movie"),
}


@needs_quarto
@pytest.mark.parametrize("case", sorted(FATAL))
def test_the_build_fails(case, tmp_path, barcode):
    body, message = FATAL[case]
    deck = make_deck(tmp_path / "deck", "## The slide {role=example}\n\n" + body, barcode, variants(barcode))
    r = lk_build(deck, "--to", "live")
    out = r.stdout + r.stderr
    assert r.returncode != 0, out[-3000:]
    assert message in out and "the build failed" in out, out[-3000:]


@needs_quarto
def test_the_study_build_fails_too(tmp_path, barcode):
    body, message = FATAL["unknown"]
    deck = make_deck(tmp_path / "deck", "## The slide {role=example}\n\n" + body, barcode)
    r = lk_build(deck, "--to", "study")
    assert r.returncode != 0 and message in r.stdout + r.stderr


# ---------------------------------------------------------------- the study strip
STRIP_SLIDES = """## Two panels {role=example}

::: {.movie clip="k30" stops="neutral"}
The dot moves, then moves on.
:::

## Three panels {role=example}

::: {.movie clip="k30" stops="lenient strict" height=3cm}
:::

## Four panels {role=example}

::: {.movie clip="k30" stops="all"}
:::

## Six panels {role=example}

::: {.movie clip="five" stops="all"}
:::

## The end alone {role=example}

::: {.movie clip="k30" stops="all" study=final}
:::

## Named holds {role=example}

::: {.movie clip="k30" stops="all" study="end start strict"}
:::

## Held without parts {role=example}

::: {.movie clip="k60" study="lenient end"}
:::

## Never upscaled {role=example}

::: {.movie clip="tiny" stops="lenient"}
:::

## A still by its id {role=example}

::: {.movie clip="k60" still="neutral" height=3cm}
:::
"""
MM = 25.4 / 72


def page_layout(page) -> tuple[list, list]:
    """The images (x, y, w, h in mm) and the text blocks between the title and the foot (y0, x0, y1, text) of a PDF
    page, in reading order."""
    imgs = [tuple(round(v * MM, 1) for v in (b["bbox"][0], b["bbox"][1], b["bbox"][2] - b["bbox"][0],
                                              b["bbox"][3] - b["bbox"][1])) for b in page.get_image_info()]
    texts = []
    for b in page.get_text("dict")["blocks"]:
        if b["type"] == 0 and 21 < b["bbox"][1] * MM < 84:
            texts.append((round(b["bbox"][1] * MM, 1), round(b["bbox"][0] * MM, 1), round(b["bbox"][3] * MM, 1),
                          " ".join("".join(s["text"] for s in ln["spans"]) for ln in b["lines"])))
    return sorted(imgs, key=lambda i: (i[1], i[0])), sorted(texts)


@needs_quarto
@needs_tex
def test_the_study_strip(tmp_path, barcode):
    pymupdf = pytest.importorskip("pymupdf")
    deck = make_deck(tmp_path / "deck", STRIP_SLIDES, barcode, variants(barcode))
    r = lk_build(deck, "--to", "study", "--strict")
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    assert "Overfull" not in (deck / "slides.log").read_text()
    pdf = pymupdf.open(deck / "_build" / "slides-study.pdf")
    pages = {p.get_text().splitlines()[1]: page_layout(p) for p in pdf if p.number > 0}

    def strip(title, n, rows, height_mm, labels):
        imgs, texts = pages[title]
        assert len(imgs) == n, (title, imgs)
        assert len({y for _, y, _, _ in imgs}) == rows, (title, imgs)                     # rows
        assert all(h >= 18 or height_mm < 48 for *_, h in imgs), (title, imgs)            # at least 18 mm high
        assert all(abs(h - imgs[0][3]) < 0.2 for *_, h in imgs)                           # one size
        assert min(x for x, *_ in imgs) >= 8.9 and max(x + w for x, _, w, _ in imgs) <= 151.1   # within the text width
        got = [t for _, _, _, t in texts if re.match(r"^\d \S", t)]
        assert got == labels, (title, texts)
        bottom = max(y1 for _, _, y1, t in texts if t in labels)
        top = min(y for _, y, _, _ in imgs)
        assert bottom - top <= height_mm + 0.3, (title, top, bottom)                       # labels included
        return imgs

    imgs = strip("TWO PANELS", 2, 1, 48, ["1 neutral", "2 end"])
    assert imgs[0][3] > 30                                                                 # two panels are large
    imgs = strip("THREE PANELS", 3, 1, 30, ["1 lenient", "2 strict", "3 end"])
    imgs = strip("FOUR PANELS", 4, 2, 48, ["1 lenient", "2 neutral", "3 strict", "4 end"])
    assert all(h >= 18 for *_, h in imgs)
    imgs = strip("SIX PANELS", 6, 2, 48, ["1 at 45", "2 at 90", "3 at 135", "4 at 180", "5 at 270", "6 end"])
    assert all(h >= 18 for *_, h in imgs)
    imgs, texts = pages["THE END ALONE"]
    assert len(imgs) == 1 and abs(imgs[0][3] - 40) < 0.2                                  # today's still, 4 cm
    strip("NAMED HOLDS", 3, 1, 48, ["1 start", "2 strict", "3 end"])                             # in time order
    strip("HELD WITHOUT PARTS", 2, 1, 48, ["1 lenient", "2 end"])
    imgs, _ = pages["NEVER UPSCALED"]
    assert len(imgs) == 2 and all(abs(w - 22.6) < 0.3 for _, _, w, _ in imgs), imgs           # its own size
    imgs, _ = pages["A STILL BY ITS ID"]
    assert len(imgs) == 1 and abs(imgs[0][3] - 30) < 0.2
    tex = (deck / "slides.tex").read_text()
    assert "\\lkpanel{assets/clips/k30.f0180.png}{1}{neutral}" in tex and "k60.f0360.png" in tex


@needs_quarto
def test_a_dark_build_takes_the_dark_entry(tmp_path, barcode):
    clips, index = barcode
    dark = json.loads(json.dumps(index["k30"]).replace("assets/clips/", "assets/clips/dark/"))
    deck = make_deck(tmp_path / "deck", '## A slide {role=example}\n\n::: {.movie clip="k30" stops="lenient"}\n:::\n',
                     barcode)
    (deck / "assets/clips/dark").mkdir()
    for f in clips.glob("k30*"):
        shutil.copy2(f, deck / "assets/clips/dark" / f.name)
    r = lk_build(deck, "--to", "live", "--profile", "dark")
    out = r.stdout + r.stderr
    assert r.returncode == 0 and "drawn for the paper preset" in out, out[-3000:]           # paper index, dark deck
    (deck / "assets/clips/dark/clips.json").write_text(json.dumps({"k30": dark}))
    r = lk_build(deck, "--to", "live", "--profile", "dark", "--strict")
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    html = (deck / "_build-dark" / "slides-live.html").read_text()
    assert 'data-lk-src="assets/clips/dark/k30.mp4"' in html and "assets/clips/dark/k30.f0090.png" in html


# ---------------------------------------------------------------- timing
TIMING_SLIDE = """## Short on time {role=example time=0.5}

::: {.movie clip="k30" stops="all"}
:::: {.stop ref="lenient"}
Ask: where next?
::::
:::: {.stop ref="neutral"}
Ask: and then?
::::
:::: {.stop ref="strict"}
Ask: and last?
::::
:::

## Time enough {role=example time=4}

::: {.movie clip="k60" stops="lenient neutral"}
:::: {.stop ref="lenient"}
Ask: where next?
::::
:::
"""


@needs_quarto
def test_clip_over_time(tmp_path, barcode):
    deck = make_deck(tmp_path / "deck", TIMING_SLIDE, barcode)
    r = lk_build(deck, "--to", "live")
    out = r.stdout + r.stderr
    assert r.returncode == 0, out[-3000:]
    assert ('CLIP>TIME slide "Short on time": clip k30 runs 12.0 s and its 3 prompts take a minute each, 192.0 s in all, '
            'over time=0.5 (30.0 s)') in out
    assert "Time enough" not in "".join(ln for ln in out.splitlines() if "CLIP>TIME" in ln)
    timing = (deck / "_build" / "timing.txt").read_text()
    assert "clip k30: 12.0 s, 4 parts (3.0 3.0 3.0 3.0 s), 3 prompts  CLIP>TIME" in timing
    assert "clip k60: 12.0 s, 3 parts (3.0 3.0 6.0 s), 1 prompt\n" in timing
    r = lk_build(deck, "--to", "live", "--strict")
    assert r.returncode != 0 and "--strict treats warnings as errors" in r.stdout + r.stderr


# ---------------------------------------------------------------- lk review frags
@needs_quarto
@needs_browser
@pinned
def test_frags_walks_the_parts(runtime_deck, tmp_path, capsys):
    from lecturekit.review.frags import frags
    assert frags(runtime_deck, tmp_path / "frags", [3, 6]) == 0
    out = capsys.readouterr().out
    print(out)
    out, key = out.split(" 6  Key start")
    steps = re.findall(r"step (\d): hold (\d) of 4, frame (\d+) \(([\d.]+) s\), shown (\d+), paused at frame (\d+), "
                       r"key to hold ([\d.]+) s", out)
    k30 = [s for s in steps][:4]
    assert [(int(b), int(f), int(sh)) for _, b, f, _, sh, _, _ in k30] == [(1, 90, 90), (2, 180, 180), (3, 270, 270), (4, 359, 359)]
    assert all(int(f) - 4 <= int(p) <= int(f) for _, _, f, _, _, p, _ in k30)               # the pause lands early
    assert "backward entry: hold 4 of 4, frame 359 (11.967 s), shown 359" in out
    assert "jump to the first cue: hold 2 of 4, frame 180 (6.000 s), shown 180" in out
    assert "it played" not in out and "not the stop frame" not in out
    assert 'the hold 3 (strict) has no "Ask:" in its notes' in out
    assert 'the hold 1 (lenient)' not in out and 'the hold 2 (neutral)' not in out
    assert "a clip in parts: k60, 4 parts, start=key, 4 key(s)" in key
    assert "step 0: hold 0 of 4, frame 0 (0.000 s), shown 0" in key                       # start=key holds frame 0
    assert "step 4: hold 4 of 4, frame 719 (11.983 s), shown 719" in key
    assert "backward entry: hold 4 of 4, frame 719 (11.983 s), shown 719" in key
    assert "jump to the first cue: hold 1 of 4, frame 180 (3.000 s), shown 180" in key
    assert "it played" not in key and "not the stop frame" not in key and "no hold" not in key
    assert 'the hold 0 (start)' not in key and 'the hold 1 (lenient) has no "Ask:"' in key
    assert (tmp_path / "frags" / "s03-f3.png").exists()
