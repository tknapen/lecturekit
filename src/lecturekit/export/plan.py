"""What each PowerPoint slide of an export holds, decided from the records of a walk through the live deck.

Pure: no browser, no ffmpeg, no python-pptx. The walk (walk.py) records one `Step` per slide and reveal step; the
media (media.py) are read before planning, so that a clip's size and frame count are known here; the writer (pptx.py)
places what `plan_slide` returns. Rectangles are in the CSS px of the 1280 by 720 frame the walk shoots, which is
the frame of the PowerPoint slide (9525 EMU per CSS px).

The rules follow the runtime (reveal/live-head.html, reveal/segments.html):

* An ordinary clip (a video outside a clip in parts) is on stage at a step when it is not inside a `.fragment` that
  is not `.visible` and not covered in an `.r-stack` by a later visible step. When it comes on stage (at the slide's
  first step, or at a step where it was not on stage before) it is a movie that starts by itself, frame 0 its
  poster; when it was on stage already it is a still of its last frame, where the live clip has (usually) ended.
* A clip in parts holds on boundary T(k) with k cues visible: T = k + 1 with start=auto, T = k with start=key. At a
  step where k changed, and at the first step with start=auto, it is a movie of the part from boundary T - 1 to T
  (both frames included), the still of boundary T - 1 its poster, so the movie ends on the hold and the next
  slide's poster is that hold. Otherwise it is a still of boundary T.
* `still` mode: never a movie; each clip is a still of the frame it would end on.
* A clip the page blends by multiplication (class `paper`: every clip of a goals, summary, section or pause slide)
  carries the colour of the page under it as its `tint`; its frames are multiplied by that colour, which is what the
  blend shows on a page of one colour. White changes nothing and is no tint.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

FRAME_W, FRAME_H = 1280, 720            # CSS px: the frame of review/browser.py and of the PowerPoint slide
EMU_PER_PX = 9525                       # 12192000 / 1280: PowerPoint's 16:9 slide is 13.333 in wide
SLIDE_EMU = (FRAME_W * EMU_PER_PX, FRAME_H * EMU_PER_PX)
VIDEO_MODES = ("auto", "click", "still")

Rect = tuple[float, float, float, float]          # x, y, width, height in CSS px
Colour = tuple[int, int, int]


# ------------------------------------------------------------------------ what the walk records
@dataclass
class Clip:
    """An ordinary clip on a slide at one step."""
    index: int                          # its place among the slide's ordinary clips, the same at every step
    file: Path
    box: Rect                           # the video element's box
    on_stage: bool
    label: str = ""
    paper: bool = False                 # blended with the page by multiplication
    tint: Colour | None = None          # then: the colour of the page under it, unless that is white
    size: tuple[float, float] = (0, 0)  # the file's display size (width times the sample aspect ratio, height)
    frames: int = 0


@dataclass
class Parts:
    """A clip in parts on a slide at one step."""
    name: str
    file: Path
    start: str                          # auto | key
    bounds: list[int]                   # the boundary frames: 0, each stop, the last frame
    k: int                              # cues visible
    box: Rect
    label: str = ""
    paper: bool = False
    tint: Colour | None = None
    size: tuple[float, float] = (0, 0)

    @property
    def hold(self) -> int:
        """T(k): the boundary the clip holds on, kept inside the boundaries."""
        t = self.k if self.start == "key" else self.k + 1
        return max(0, min(t, len(self.bounds) - 1))


@dataclass
class Step:
    """One reveal step of one slide, as the walk saw it."""
    number: int                         # the deck slide, 1-based as the foot shows it
    f: int                              # Reveal's fragment index, -1 before the first
    title: str
    shot: Path                          # the screenshot, clips hidden
    colour: tuple[int, int, int] = (255, 255, 255)
    alt: str = ""
    notes: str = ""
    clips: list[Clip] = field(default_factory=list)
    parts: list[Parts] = field(default_factory=list)


# ------------------------------------------------------------------------ what a PowerPoint slide holds
@dataclass(frozen=True)
class Frame:
    """Frame `n` (0-based, display order) of a video, as a still; multiplied by `tint` when it has one."""
    file: Path
    n: int
    tint: Colour | None = None


@dataclass(frozen=True)
class Cut:
    """Frames `a` to `b` of a video, both included; the whole clip when `whole`; multiplied by `tint` when it has
    one."""
    file: Path
    a: int
    b: int
    whole: bool = False
    tint: Colour | None = None

    @property
    def frames(self) -> int:
        return self.b - self.a + 1


@dataclass(frozen=True)
class Movie:
    media: Cut
    poster: Frame
    rect: Rect
    label: str = ""


@dataclass(frozen=True)
class Still:
    frame: Frame
    rect: Rect
    label: str = ""


Shape = Movie | Still


def contain(box: Rect, w: float, h: float) -> Rect:
    """The content rectangle of a w by h picture in `box` under `object-fit: contain` (centred, as theme.scss and
    segments.html leave `object-position`)."""
    x, y, bw, bh = box
    if bw <= 0 or bh <= 0 or w <= 0 or h <= 0:
        return (x, y, max(bw, 0.0), max(bh, 0.0))
    s = min(bw / w, bh / h)
    cw, ch = w * s, h * s
    return (x + (bw - cw) / 2, y + (bh - ch) / 2, cw, ch)


def emu(rect: Rect) -> tuple[int, int, int, int]:
    """A CSS px rectangle in EMU, cut to the slide."""
    x, y, w, h = rect
    x0, y0 = max(0.0, x), max(0.0, y)
    x1, y1 = min(float(FRAME_W), x + w), min(float(FRAME_H), y + h)
    return (round(x0 * EMU_PER_PX), round(y0 * EMU_PER_PX), round(max(0.0, x1 - x0) * EMU_PER_PX),
            round(max(0.0, y1 - y0) * EMU_PER_PX))


def plan_slide(steps: list[Step], video: str = "auto") -> list[list[Shape]]:
    """The clips placed on each PowerPoint slide of one deck slide (one list per step, in step order)."""
    if video not in VIDEO_MODES:
        raise ValueError(f"video mode {video!r}: one of {', '.join(VIDEO_MODES)}")
    out: list[list[Shape]] = []
    for i, st in enumerate(steps):
        prev = steps[i - 1] if i else None
        shapes: list[Shape] = []
        for c in st.clips:
            if not c.on_stage:
                continue
            rect = contain(c.box, *c.size)
            last = Frame(c.file, max(c.frames - 1, 0), c.tint)
            was = prev is not None and any(p.index == c.index and p.on_stage for p in prev.clips)
            if video == "still" or was:
                shapes.append(Still(last, rect, c.label))
            else:
                shapes.append(Movie(Cut(c.file, 0, max(c.frames - 1, 0), whole=True, tint=c.tint),
                                    Frame(c.file, 0, c.tint), rect, c.label))
        for p in st.parts:
            rect = contain(p.box, *p.size)
            t = p.hold
            before = next((q for q in prev.parts if q.name == p.name), None) if prev else None
            plays = (before is None and p.start == "auto") or (before is not None and before.k != p.k)
            if video != "still" and plays and t > 0:
                a, b = p.bounds[t - 1], p.bounds[t]
                shapes.append(Movie(Cut(p.file, a, b, tint=p.tint), Frame(p.file, a, p.tint), rect, p.label))
            else:
                shapes.append(Still(Frame(p.file, p.bounds[t], p.tint), rect, p.label))
        out.append(shapes)
    return out


# ------------------------------------------------------------------------ notes
_BLOCKS = {"address", "article", "aside", "blockquote", "dd", "details", "div", "dl", "dt", "figcaption", "figure",
           "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "ol", "p", "pre",
           "section", "summary", "table", "tr", "ul"}
_SKIP = {"style", "script", "template"}


class _Text(HTMLParser):
    """Text of an HTML fragment, one line per block element and per `<br>`; style and script left out; a MathML
    formula as its TeX annotation when it has one."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []
        self.cur: list[str] = []
        self.skip = 0
        self.math: list[dict] = []

    def _break(self) -> None:
        line = re.sub(r"\s+", " ", "".join(self.cur)).strip()
        if line:
            self.lines.append(line)
        self.cur = []

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP:
            self.skip += 1
        elif tag == "math":
            self.math.append({"text": [], "tex": None, "in_tex": False})
        elif tag == "annotation" and self.math:
            if (dict(attrs).get("encoding") or "").lower() in ("application/x-tex", "tex"):
                self.math[-1]["in_tex"] = True
                self.math[-1]["tex"] = []
        elif tag == "br" or tag in _BLOCKS:
            self._break()

    def handle_startendtag(self, tag, attrs):
        if tag == "br" or tag in _BLOCKS:
            self._break()

    def handle_endtag(self, tag):
        if tag in _SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag == "annotation" and self.math:
            self.math[-1]["in_tex"] = False
        elif tag == "math" and self.math:
            m = self.math.pop()
            text = "".join(m["tex"]).strip() if m["tex"] else "".join(m["text"]).strip()
            self._emit(f"${text}$" if m["tex"] else text)
        elif tag in _BLOCKS:
            self._break()

    def _emit(self, data: str) -> None:
        if self.math:
            m = self.math[-1]
            (m["tex"] if m["in_tex"] else m["text"]).append(data)
        else:
            self.cur.append(data)

    def handle_data(self, data):
        if not self.skip:
            self._emit(data)

    def close(self):
        super().close()
        self._break()


def notes_text(fragments: list[str]) -> str:
    """The text of the notes chosen for a step (each an `aside.notes` element's HTML, or plain text from a
    `data-notes` attribute): one line per block, in order."""
    lines: list[str] = []
    for frag in fragments:
        p = _Text()
        p.feed(frag)
        p.close()
        lines += p.lines
    return "\n".join(lines)


# ------------------------------------------------------------------------ the --slides option
def parse_slides(spec: str | None, count: int) -> list[int]:
    """`3,5-7` as the 1-based slide numbers 3, 5, 6, 7 (in deck order, each once); all slides when empty."""
    if not spec:
        return list(range(1, count + 1))
    want: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", part)
        if not m:
            raise ValueError(f"--slides {spec!r}: write slide numbers and ranges, as in 3,5-7")
        a, b = int(m.group(1)), int(m.group(2) or m.group(1))
        if a < 1 or b < a or b > count:
            raise ValueError(f"--slides {spec!r}: the deck has slides 1 to {count}")
        want.update(range(a, b + 1))
    return sorted(want)
