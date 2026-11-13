"""`lk clips`: render a deck's clips and write `assets/clips/clips.json`.

The seam between the deck and whatever made the clip. A deck's movie block names a clip:

    ::: {.movie clip="bar-bold" height=4cm}

and `assets/clips/clips.json` says what that name means (paths relative to the deck folder; a value that is
not known is left out, never written as null). Every entry `lk clips` writes is `format: 2`: besides the video,
the still, the size and the source, it carries the facts a deck needs to hold the clip at a frame:

    {"bar-bold": {"format": 2, "video": "assets/clips/bar-bold.mp4", "still": "assets/clips/bar-bold.png",
                  "width": 1280, "height": 720, "fps": 30.0, "frames": 600, "duration": 20.0,
                  "sha256": "<of the video>", "poster": "assets/clips/bar-bold.f0000.png",
                  "stops": [{"id": "first_sweep", "frame": 204, "pts": 6.8, "label": "first sweep",
                             "still": "assets/clips/bar-bold.f0204.png", "rest_before": 9, "rest_after": 9,
                             "frozen": []}],
                  "end": {"frame": 599, "pts": 19.966667, "still": "assets/clips/bar-bold.f0599.png"},
                  "source": "anim/clip_bar_bold.py:BarBold", "revision": "<sha1 of the script>",
                  "producer": "kit"}}

`frames` is counted by decoding the delivered video; a stop's `frame` is authoritative and `pts` is that frame's
presentation time; every still is that exact frame (`select=eq(n,K)`), named by its number; `rest_before` and
`rest_after` count the frames of unchanged picture on either side, measured on the pixels. `stops` are
candidates: the deck chooses among them. Every delivered video is remuxed with its index first (`+faststart`)
by stream copy; a re-encode (`--crop`, `adopt --size`) forces a keyframe at every stop and checks that the frame
count did not change. An entry without `format` (written by an older lecturekit, or by hand) keeps its meaning.

Three producers fill it:

* kit scenes: `anim/clip_<name>.py`, one or more Manim `Scene` classes on the shared kit (`from kit import *`).
  Rendered with Manim at 1280 by 720 on the slide colour (`--size 1920x1080` or the environment variable
  NM_CLIP_SIZE for another size; the kit reads it), 30 fps, without a title, with `--save_sections`. The video is
  copied to `assets/clips/<name>.mp4`; its last frame becomes the still `<name>.png` unless the scene class sets
  `still = <seconds>` or `still = "<checkpoint id>"`. Each `checkpoint(self, id, label=None, rest=0.0)` in the
  scene opens a Manim section of type `lecturekit.checkpoint`; its frame is the sum of the frames of the sections
  before it, and the labels come back through the file NM_CHECKPOINTS_FILE names.
* manim8 projects: `clips/families/<family>/.../<name>/`, rendered with `scianim render --profile final --json`.
  `lk clips` builds the family environment when it is missing (`scianim family env sync`) and generates the
  scene module of the working copy (`scianim codegen`) first. The manifest printed on stdout names the full
  movie (`result.videos[0]`), its size, frame rate and duration, the job and its cache key, the revision and
  every checkpoint PNG; all of them are copied into `assets/clips/`, and the still is the latest checkpoint
  unless `--still <clip>=<snapshot_id>` names another. The record adds `job` and `checkpoints`. The stops are
  the manifest's `result.stops` (manim8's snapshots marked `stop: true`, ADR-045), cross-checked against the
  movie; a manifest without them gives no candidates. A clip renders at its project's `output`; `lk clips` warns
  when that is not the deck's size (`--size`, else 1280 by 720) or 30 fps. manim8's warnings are printed; a cache
  hit on a job that lost the deck's fonts (rendered outside `lk clips`, on a machine without them) is rendered
  once more with them.
* an MP4 made elsewhere: `lk clips adopt <mp4> --name NAME [--stops S1 S2 ...] [--labels L1 L2 ...]` copies it in
  and writes its entry; a stop is a second of the video (or `ID=SECONDS`), snapped to the nearest frame.

`--crop` trims the video and the stills of any producer to the content's bounding box against the slide
colour, and the record carries the resulting shape, which the deck uses as the clip's aspect. `--mode dark`
(or LECTUREKIT_MODE=dark) renders the dark preset into `assets/clips/dark/` with its own `clips.json`: kit
scenes read the dark brand, manim8 projects render under the brand's bridged dark style (`lk theme --manim8`).

Names: `-` and `_` are equivalent wherever a clip is looked up, so `--only bar_bold` and `--only bar-bold` name
the same clip; two clips whose names differ only in that way are an error. Stop ids are exact slugs.

A failing clip is reported with its producer and a one-line reason, the index is saved after every clip, and
the run goes on; a clip's files are made in a staging folder and moved in together, so a failure leaves
`assets/clips/` as the index describes it; `lk clips` exits non-zero at the end when a clip failed. The deck
versions a clip's URL by its `sha256`, so a browser never shows a cached older render.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from collections import deque
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

CLIPS_DIR = Path("assets/clips")
KIT_SIZE = "1280x720"
#: manifest schema versions this lecturekit reads; another one is refused rather than guessed at
MANIFEST_SCHEMAS = ("1.0",)
PRODUCERS = ("kit", "manim8", "external")

INSTALL_MANIM8 = ("manim8 is not installed: install lecturekit's manim8 extra on Python 3.12 or later, "
                  "pip install 'lecturekit[manim8]' (manim8 builds each family's render environment with uv, "
                  "which it finds on PATH or installs with itself); see docs/INSTALL.md")
INSTALL_MANIM = ("Manim is not installed: pip install 'lecturekit[clips]' (Manim Community 0.22, and the Cairo "
                 "and Pango headers on the machine); see docs/INSTALL.md")


class ClipError(RuntimeError):
    """A clip that could not be made, with a one-line reason."""


@dataclass
class ClipRecord:
    video: str
    still: str | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    duration: float | None = None
    source: str | None = None
    revision: str | None = None
    producer: str = "kit"
    job: dict[str, Any] | None = None
    checkpoints: dict[str, str] | None = None
    # format 2 (every entry lk clips writes): the facts a deck needs to hold the clip at a frame
    format: int | None = None
    frames: int | None = None
    sha256: str | None = None
    poster: str | None = None
    stops: list[dict[str, Any]] | None = None
    end: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """The index entry: every known value, the unknown ones left out (never null)."""
        return {k: v for k, v in asdict(self).items() if v is not None and v != {}}


@dataclass
class Failure:
    name: str
    producer: str
    reason: str


@dataclass
class Clip:
    """A clip `lk clips` can make: its name, producer and where it comes from."""
    name: str
    producer: str
    path: Path                      # the scene script, or the manim8 project directory
    scene: str | None = None        # the Scene class of a kit clip
    aliases: list[str] = field(default_factory=list)


# ------------------------------------------------------------------------ names
def norm_name(name: str) -> str:
    """The lookup form of a clip name: `-` and `_` are equivalent (`bar-bold` and `bar_bold` are one clip)."""
    return str(name).strip().replace("-", "_")


# ------------------------------------------------------------------------ tools
def _ffmpeg() -> str | None:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg  # type: ignore
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def probe_video(video: Path) -> dict[str, Any]:
    """Width, height, frame rate and duration of a video, through ffmpeg's banner output."""
    exe = _ffmpeg()
    if not exe:
        raise ClipError("ffmpeg not found (pip install imageio-ffmpeg, or install ffmpeg)")
    r = subprocess.run([exe, "-i", str(video)], capture_output=True, text=True)
    text = r.stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", text)
    duration = float(m.group(1)) * 3600 + float(m.group(2)) * 60 + float(m.group(3)) if m else 0.0
    m2 = re.search(r"Video:.*? (\d{2,5})x(\d{2,5})", text)
    if not m2:
        raise ClipError(f"could not read the dimensions of {video}")
    m3 = re.search(r"Video:.*?(\d+(?:\.\d+)?) fps", text)
    return {"width": int(m2.group(1)), "height": int(m2.group(2)), "duration": round(duration, 3),
            "fps": float(m3.group(1)) if m3 else None}


def probe(video: Path) -> tuple[int, int, float]:
    """Width, height and duration of a video."""
    p = probe_video(video)
    return p["width"], p["height"], p["duration"]


def content_box(image_path: Path, background: str, margin: int = 24) -> tuple[int, int, int, int] | None:
    """Bounding box of everything that is not the background colour, with a margin, at an even offset and even-sized.

    Even, because ffmpeg's crop of a 4:2:0 video moves an odd offset down to an even one, while a still is cut at the
    offset it is given: an odd box would leave the video and its stills a pixel apart."""
    from PIL import Image, ImageChops
    im = Image.open(image_path).convert("RGB")
    bg = Image.new("RGB", im.size, background)
    diff = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 12 else 0)
    box = diff.getbbox()
    if not box:
        return None
    x0, y0, x1, y1 = box
    x0, y0 = max(0, x0 - margin), max(0, y0 - margin)
    x0, y0 = x0 - x0 % 2, y0 - y0 % 2
    x1, y1 = min(im.width, x1 + margin), min(im.height, y1 + margin)
    w, h = (x1 - x0) // 2 * 2, (y1 - y0) // 2 * 2
    return x0, y0, w, h


def union_box(boxes: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int] | None:
    """The box around several content boxes (x, y, w, h), at an even offset and even-sized (see content_box)."""
    if not boxes:
        return None
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x0, y0 = x0 - x0 % 2, y0 - y0 % 2
    x1 = max(b[0] + b[2] for b in boxes)
    y1 = max(b[1] + b[3] for b in boxes)
    return x0, y0, (x1 - x0) // 2 * 2, (y1 - y0) // 2 * 2


def _need_ffmpeg() -> str:
    exe = _ffmpeg()
    if not exe:
        raise ClipError("ffmpeg not found (pip install imageio-ffmpeg, or install ffmpeg)")
    return exe


def _ffprobe() -> str | None:
    """ffprobe on PATH or beside ffmpeg; None when only an ffmpeg (imageio-ffmpeg's) is there."""
    exe = shutil.which("ffprobe")
    if exe:
        return exe
    ff = _ffmpeg()
    if ff:
        cand = Path(ff).with_name("ffprobe" + Path(ff).suffix)
        if cand.exists():
            return str(cand)
    return None


_PASSTHROUGH: dict[str, list[str]] = {}


def _passthrough(exe: str) -> list[str]:
    """The options that keep every decoded frame and add none: `-fps_mode passthrough` (ffmpeg 5.1 and later),
    else `-vsync passthrough`."""
    if exe not in _PASSTHROUGH:
        r = subprocess.run([exe, "-hide_banner", "-h", "long"], capture_output=True, text=True)
        _PASSTHROUGH[exe] = ["-fps_mode", "passthrough"] if "-fps_mode" in r.stdout + r.stderr else \
            ["-vsync", "passthrough"]
    return _PASSTHROUGH[exe]


def _ff(args: list[str], what: str, *, binary: bool = False) -> subprocess.CompletedProcess:
    """Run ffmpeg; a failure is a ClipError that says what was being done and ffmpeg's last line."""
    r = subprocess.run([_need_ffmpeg(), "-y", "-v", "error", *args], capture_output=True, text=not binary)
    if r.returncode:
        err = r.stderr.decode(errors="replace") if binary else r.stderr
        raise ClipError(f"ffmpeg could not {what}: {_last_line(err.splitlines()) or f'exited {r.returncode}'}")
    return r


def _fraction(value: Any) -> float | None:
    try:
        num, _, den = str(value).partition("/")
        f = float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        return None
    return f if f > 0 else None


@dataclass
class FrameTable:
    """What decoding a video says: its size, its frame rate, and every frame's presentation time and keyframe flag,
    in display order."""
    width: int
    height: int
    fps: float
    pts: list[float]
    keys: list[bool]
    codec: str | None = None

    @property
    def frames(self) -> int:
        return len(self.pts)

    def nearest(self, seconds: float) -> int:
        """The frame whose presentation time is nearest to `seconds` (the earlier one on a tie)."""
        import bisect
        i = bisect.bisect_left(self.pts, seconds)
        if i <= 0:
            return 0
        if i >= self.frames:
            return self.frames - 1
        return i - 1 if seconds - self.pts[i - 1] <= self.pts[i] - seconds else i


def frame_table(video: Path) -> FrameTable:
    """Decode a video's frames and list them: `ffprobe -count_frames` with every frame's `pts_time` and
    `key_frame`, or ffmpeg's `showinfo` filter where there is no ffprobe. The count is the decoded one, never the
    container's."""
    video = Path(video)
    probe = _ffprobe()
    if probe:
        r = subprocess.run([probe, "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                            "stream=codec_name,width,height,r_frame_rate,avg_frame_rate,nb_read_frames:"
                            "frame=pts_time,best_effort_timestamp_time,key_frame", "-of", "json", str(video)],
                           capture_output=True, text=True)
        if r.returncode:
            raise ClipError(f"ffprobe could not read {video.name}: {_last_line(r.stderr.splitlines())}")
        data = json.loads(r.stdout or "{}")
        streams = data.get("streams") or []
        if not streams:
            raise ClipError(f"{video.name} has no video stream")
        st = streams[0]
        pts: list[float] = []
        keys: list[bool] = []
        for f in data.get("frames") or []:
            t = f.get("pts_time")
            if t in (None, "N/A"):
                t = f.get("best_effort_timestamp_time")
            pts.append(float(t) if t not in (None, "N/A") else float("nan"))
            keys.append(str(f.get("key_frame")) == "1")
        counted = int(st.get("nb_read_frames") or len(pts))
        if counted != len(pts):
            raise ClipError(f"ffprobe counted {counted} frames in {video.name} but listed {len(pts)}")
        r_rate, avg = _fraction(st.get("r_frame_rate")), _fraction(st.get("avg_frame_rate"))
        width, height, codec = int(st.get("width") or 0), int(st.get("height") or 0), st.get("codec_name")
    else:
        exe = _need_ffmpeg()
        r = subprocess.run([exe, "-hide_banner", "-nostats", "-i", str(video), "-map", "0:v:0", "-vf", "showinfo",
                            *_passthrough(exe), "-f", "null", "-"], capture_output=True, text=True)
        if r.returncode:
            raise ClipError(f"ffmpeg could not read {video.name}: {_last_line(r.stderr.splitlines())}")
        pts, keys = [], []
        width = height = 0
        rate = re.search(r"config in time_base: (\d+/\d+), frame_rate: (\d+/\d+)", r.stderr)
        r_rate = avg = _fraction(rate.group(2)) if rate else None
        base = _fraction(rate.group(1)) if rate else None
        for m in re.finditer(r"n:\s*\d+ pts:\s*(-?\d+) pts_time:(\S+).*? s:(\d+)x(\d+).*? iskey:(\d)", r.stderr):
            # pts_time is printed to six significant digits; the pts in the time base is exact
            pts.append(int(m.group(1)) * base if base else float(m.group(2)))
            width, height = int(m.group(3)), int(m.group(4))
            keys.append(m.group(5) == "1")
        codec = None
    if not pts:
        raise ClipError(f"{video.name} has no frames")
    if r_rate and avg and abs(r_rate - avg) <= 0.001 * avg:
        fps = r_rate
    else:
        fps = avg or r_rate
    if not fps:
        raise ClipError(f"could not read the frame rate of {video.name}")
    for i, t in enumerate(pts):   # a frame without a timestamp sits on the frame grid after the one before it
        if math.isnan(t):
            pts[i] = (pts[i - 1] + 1 / fps) if i else 0.0
    return FrameTable(width=width, height=height, fps=round(fps, 6), pts=[round(t, 6) for t in pts], keys=keys,
                      codec=codec)


#: two pictures are one when no luma value differs by more than this (of 255) with the video scaled to
#: REST_WIDTH pixels wide; the rests before and after a stop are counted in such frames, each compared with the
#: stop's own frame, so a slow drift cannot add up. The bound is the coding noise of a still picture. Measured on
#: the manim8 clips of the feature deck and the expo (1280 by 720, Manim's H.264 at CRF 23, 9 November 2026):
#: across the 143 keyframes that sit in a still rest (every manim8 stop is one, coded afresh), frame k-1 and
#: frame k differ by 1 to 10 levels, and inside one group of pictures by up to 7; the busier the picture, the
#: larger (10 on a map of 1380 coloured marks). Where something starts to move on the keyframe, the difference
#: was 62 or more (a readout appearing: 81). At 16 an edge of contrast 200 would have to move by less than
#: 0.6 pixel at 1280 wide to pass as no change.
REST_TOLERANCE = 16
REST_WIDTH = 160


def luma_frames(video: Path, table: FrameTable) -> tuple[tuple[int, int], list[bytes]]:
    """Every frame of the video as grey bytes at REST_WIDTH pixels wide (area-averaged, which smooths the coding
    noise of a still picture), in display order."""
    w = REST_WIDTH
    h = max(2, round(w * table.height / max(table.width, 1) / 2) * 2)
    exe = _need_ffmpeg()
    r = _ff(["-i", str(video), "-map", "0:v:0", "-vf", f"scale={w}:{h}:flags=area,format=gray",
             *_passthrough(exe), "-f", "rawvideo", "-"], f"decode {Path(video).name}", binary=True)
    size = w * h
    data = r.stdout
    if len(data) % size:
        raise ClipError(f"decoding {Path(video).name} gave a partial frame")
    return (w, h), [data[i:i + size] for i in range(0, len(data), size)]


def same_picture(a: bytes, b: bytes, size: tuple[int, int]) -> bool:
    """Whether two grey frames show one picture: no pixel differs by more than REST_TOLERANCE."""
    if a == b:
        return True
    try:
        from PIL import Image, ImageChops
        diff = ImageChops.difference(Image.frombytes("L", size, a), Image.frombytes("L", size, b))
        return diff.getextrema()[1] <= REST_TOLERANCE
    except ImportError:
        return max(abs(x - y) for x, y in zip(a, b)) <= REST_TOLERANCE


def rests(lumas: list[bytes], size: tuple[int, int], k: int) -> tuple[int, int]:
    """Frames of unchanged picture before and after frame k: the frames next to it that show its picture."""
    before = 0
    while k - before - 1 >= 0 and same_picture(lumas[k - before - 1], lumas[k], size):
        before += 1
    after = 0
    while k + after + 1 < len(lumas) and same_picture(lumas[k + after + 1], lumas[k], size):
        after += 1
    return before, after


def extract_frames(video: Path, frames: list[int], outs: list[Path]) -> None:
    """Write frame `frames[i]` of the video (0-based, in display order) to `outs[i]` as a PNG: selected by its
    number (`select=eq(n,K)`), never by a time. One decoding pass for all of them."""
    if not frames:
        return
    order = sorted(set(frames))
    exe = _need_ffmpeg()
    tmp = Path(tempfile.mkdtemp(prefix="._frames.", dir=Path(outs[0]).parent))
    try:
        expr = "+".join(f"eq(n\\,{k})" for k in order)
        _ff(["-i", str(video), "-map", "0:v:0", "-vf", f"select={expr}", *_passthrough(exe),
             "-frames:v", str(len(order)), "-start_number", "0", str(tmp / "%06d.png")],
            f"extract frames {', '.join(map(str, order))} of {Path(video).name}")
        got = sorted(tmp.glob("*.png"))
        if len(got) != len(order):
            raise ClipError(f"{Path(video).name} has no frame {order[len(got)]} (it has fewer frames)")
        by_frame = dict(zip(order, got))
        for k, out in zip(frames, outs):
            shutil.copyfile(by_frame[k], out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def extract_frame(video: Path, at: float, out: Path) -> None:
    """The frame shown at `at` seconds, by its number (the frame whose presentation time is nearest)."""
    table = frame_table(video)
    extract_frames(video, [table.nearest(at)], [Path(out)])


def faststart(src: Path, dst: Path) -> None:
    """Copy a video with its index (moov) first, by stream copy: every frame and keyframe stays as it was, and a
    browser can seek before the whole file has arrived."""
    _ff(["-i", str(src), "-map", "0:v:0", "-map", "0:a?", "-c", "copy", "-movflags", "+faststart", str(dst)],
        f"remux {Path(src).name}")


def reencode(src: Path, dst: Path, filters: list[str], keyframes: list[int], expect: int) -> FrameTable:
    """Re-encode a video through `filters` (a crop, a scale) with a keyframe forced at frame 0 and at every frame in
    `keyframes`, every frame kept, the index first; then check that it still has `expect` frames."""
    exe = _need_ffmpeg()
    force = "expr:" + "+".join(f"eq(n,{k})" for k in sorted({0, *keyframes}))
    _ff(["-i", str(src), "-map", "0:v:0", "-vf", ",".join(filters), "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-crf", "18", "-force_key_frames", force, *_passthrough(exe), "-movflags", "+faststart", "-an", str(dst)],
        f"re-encode {Path(src).name}")
    table = frame_table(dst)
    if table.frames != expect:
        raise ClipError(f"re-encoding {Path(src).name} gave {table.frames} frames, not {expect}")
    return table


def crop_video(src: Path, dst: Path, box: tuple[int, int, int, int], keyframes: list[int] = (),
               expect: int | None = None) -> FrameTable:
    """Crop a video to `box` (x, y, w, h), forcing keyframes at `keyframes` and keeping the frame count."""
    x, y, w, h = box
    tmp = dst.with_name(f"_{dst.name}")
    if expect is None:
        expect = frame_table(src).frames
    table = reencode(src, tmp, [f"crop={w}:{h}:{x}:{y}"], list(keyframes), expect)
    tmp.replace(dst)
    return table


def crop_image(src: Path, dst: Path, box: tuple[int, int, int, int]) -> None:
    from PIL import Image
    x, y, w, h = box
    with Image.open(src) as im:
        im.crop((x, y, x + w, y + h)).save(dst)


def file_hash(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()[:12]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mean_difference(a: Path, b: Path) -> float | None:
    """The mean absolute difference of two pictures, 0 to 255, the second scaled to the first's size; None without
    Pillow."""
    try:
        from PIL import Image, ImageChops, ImageStat
    except ImportError:
        return None
    with Image.open(a) as ia, Image.open(b) as ib:
        x, y = ia.convert("RGB"), ib.convert("RGB")
        if y.size != x.size:
            y = y.resize(x.size)
        return sum(ImageStat.Stat(ImageChops.difference(x, y)).mean) / 3


# ------------------------------------------------------------------------- stops
#: the slug rule of manim8's ids, for stop ids; compared exactly
STOP_ID = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
#: words the deck's `stops=` and `.stop ref=` give a meaning of their own
RESERVED_STOP_IDS = ("start", "end", "all")
LABEL_MAX = 40
#: a deck refuses a stop with fewer frames of rest before it (the live deck pauses a frame or two early)
MIN_REST_FRAMES = 3
#: two stops closer than this are allowed, and warned about
MIN_STOP_GAP = 0.5
#: the kit's checkpoint() (lecturekit.manim.nmcheckpoint, which imports Manim through its package)
CHECKPOINT_SECTION = "lecturekit.checkpoint"
CHECKPOINTS_ENV = "NM_CHECKPOINTS_FILE"
#: the most a still may differ from the producer's own picture of that frame (mean, of 255)
STILL_MATCH = 1.0


@dataclass
class Candidate:
    """A frame where a deck may hold the clip, before it is measured."""
    id: str
    frame: int
    label: str | None = None
    notes: str | None = None
    frozen: list[str] = field(default_factory=list)
    declared_rest: int | None = None   # frames of rest before it that the producer says it made
    picture: Path | None = None        # the producer's own picture of the frame, to compare the still with


def _warn(name: str, message: str) -> None:
    print(f"lecturekit: clip {name}: {message}", file=sys.stderr)


def check_candidates(name: str, candidates: list[Candidate], table: FrameTable, warn: bool = True) -> list[Candidate]:
    """The candidates in time order, or a ClipError for one a deck could never hold: an id that is not a slug or
    is reserved, a label that is not 1 to 40 characters of one line, a frame outside the video, at its first or
    last frame, or one frame for two stops. Two stops closer than 0.5 s are a warning."""
    seen: set[str] = set()
    for c in candidates:
        if not STOP_ID.match(c.id) or c.id in RESERVED_STOP_IDS:
            raise ClipError(f"stop id {c.id!r} is not a slug ([a-z][a-z0-9_]*, at most 64 characters) other than "
                            f"{', '.join(RESERVED_STOP_IDS)}")
        if c.id in seen:
            raise ClipError(f"stop id {c.id!r} is used twice")
        seen.add(c.id)
        if c.label is not None and (not 1 <= len(c.label) <= LABEL_MAX or "\n" in c.label):
            raise ClipError(f"stop {c.id}: the label is plain text of 1 to {LABEL_MAX} characters, one line")
        if not 0 < c.frame < table.frames - 1:
            where = "the first frame" if c.frame == 0 else \
                "the last frame" if c.frame == table.frames - 1 else "outside the video"
            raise ClipError(f"stop {c.id} is at frame {c.frame}, {where} (the video has {table.frames} frames, "
                            "and a stop sits strictly between its first and its last)")
    ordered = sorted(candidates, key=lambda c: c.frame)
    for a, b in zip(ordered, ordered[1:]):
        if a.frame == b.frame:
            raise ClipError(f"stops {a.id} and {b.id} are both at frame {a.frame}")
        gap = table.pts[b.frame] - table.pts[a.frame]
        if gap < MIN_STOP_GAP and warn:
            _warn(name, f"stops {a.id} and {b.id} are {gap:.2f} s apart (a part shorter than {MIN_STOP_GAP:g} s "
                  "is hard to see)")
    return ordered


def format2(video: Path, name: str, rel_dir: Path, candidates: list[Candidate], stage: Path,
            still: tuple[str, int] | None = None, rests_from: tuple[Path, FrameTable] | None = None) -> dict[str, Any]:
    """The format 2 fields of a delivered video in `stage`: its frame count, frame rate and sha256, the poster
    (frame 0), each candidate stop with its still and its rests, and the end. The stills are written into `stage`
    as `<name>.fNNNN.png`, and `still` = (file name, frame) writes one more (the study still). The rests are
    measured on `rests_from`, the producer's video, when the delivered one is a re-encode of it: a keyframe forced
    at a stop is coded afresh and differs from the frames before it by a few levels that are not in the picture."""
    table = frame_table(video)
    cands = check_candidates(name, candidates, table)
    last = table.frames - 1
    source, source_table = rests_from or (video, table)
    if source_table.frames != table.frames:
        raise ClipError(f"{Path(video).name} has {table.frames} frames, {Path(source).name} {source_table.frames}")
    size, lumas = luma_frames(source, source_table) if cands else ((0, 0), [])
    if cands and len(lumas) != table.frames:
        raise ClipError(f"decoding {Path(source).name} gave {len(lumas)} frames, ffprobe {table.frames}")
    bounds = sorted({0, last, *(c.frame for c in cands)})
    file_of = {k: f"{name}.f{k:04d}.png" for k in bounds}
    frames, outs = [k for k in bounds], [stage / file_of[k] for k in bounds]
    if still:
        frames.append(still[1])
        outs.append(stage / still[0])
    extract_frames(video, frames, outs)
    rel = {k: (rel_dir / f).as_posix() for k, f in file_of.items()}
    stops = []
    for c in cands:
        before, after = rests(lumas, size, c.frame)
        if before < MIN_REST_FRAMES:
            _warn(name, f"stop {c.id} (frame {c.frame}) has {before} frame{'s' if before != 1 else ''} of unchanged "
                  f"picture before it; a deck refuses a stop with fewer than {MIN_REST_FRAMES}")
        elif c.declared_rest is not None and before < c.declared_rest:
            _warn(name, f"stop {c.id}: the producer made {c.declared_rest} frames of rest before it, the pixels "
                  f"show {before}")
        if not table.keys[c.frame]:
            _warn(name, f"stop {c.id} (frame {c.frame}) is not a keyframe: a hold there is exact, but seeking to it "
                  "takes longer")
        if c.picture is not None and c.picture.exists():
            d = mean_difference(stage / file_of[c.frame], c.picture)
            if d is not None and d > STILL_MATCH:
                raise ClipError(f"stop {c.id}: frame {c.frame} of the movie is not the producer's picture of it "
                                f"(mean difference {d:.2f}); the stop's frame and the movie disagree")
        stop = {"id": c.id, "frame": c.frame, "pts": table.pts[c.frame], "label": c.label or c.id.replace("_", " "),
                "notes": c.notes or None, "still": rel[c.frame], "rest_before": before, "rest_after": after,
                "frozen": list(c.frozen)}
        stops.append({k: v for k, v in stop.items() if v is not None})
    return {"format": 2, "fps": table.fps, "frames": table.frames, "sha256": sha256_of(video),
            "poster": rel[0], "stops": stops, "end": {"frame": last, "pts": table.pts[last], "still": rel[last]},
            "width": table.width, "height": table.height}


def _move_in(stage: Path, out: Path, name: str) -> set[str]:
    """Move a clip's staged files into its folder, then drop the frame stills (`<name>.fNNNN.png`) of an earlier
    render that this one did not make. Returns the names of the files moved in."""
    made = {p.name for p in stage.iterdir() if p.is_file()}
    for f in sorted(stage.iterdir()):
        if f.is_file():
            f.replace(out / f.name)
    still = re.compile(rf"^{re.escape(name)}\.f\d{{4,}}\.png$")
    for old in out.iterdir():
        if still.match(old.name) and old.name not in made:
            old.unlink()
    return made


def _rel(path: Path, base: Path) -> str:
    return Path(os.path.relpath(Path(path).resolve(), Path(base).resolve())).as_posix()


_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


def _last_line(lines: list[str] | deque) -> str:
    for line in reversed(list(lines)):
        s = _ANSI.sub("", line).strip()
        if s:
            return s
    return ""


def _reason(lines: list[str] | deque, limit: int = 300) -> str:
    """The one-line reason of a tool's failure: its last line, or, when that only points at the errors above
    it (manim8's "fix the errors above"), the first error with its first detail. When the last line only says
    that a command exited (manim8's "`uv lock` exited 1"), the hint or the tool's own error above it follows."""
    clean = [s for s in (_ANSI.sub("", line).strip() for line in lines) if s]
    if not clean:
        return ""
    reason = clean[-1]
    if "above" in reason:
        for i, line in enumerate(clean[:-1]):
            if re.match(r"error\b", line):
                reason = re.sub(r"^error[:\s]+", "", line)
                if i + 1 < len(clean) - 1 and clean[i + 1].startswith("- "):
                    reason += " " + clean[i + 1][2:]
                break
    elif re.search(r"\bexited -?\d+", reason):
        reason = re.sub(r"`/[^`\s]*/([^/`\s]+)", r"`\1", reason)   # "`/abs/venv/bin/uv lock`" -> "`uv lock`"
        detail = _detail(clean[:-1])
        if detail:
            reason = f"{reason}: {detail}"
    reason = reason.replace(f"{Path.cwd()}{os.sep}", "")
    return reason if len(reason) <= limit else reason[:limit - 3] + "..."


_BLOCK_START = re.compile(r"^(error|warning|note|hint|help)\b:?|^× |^Using ", re.IGNORECASE)


def _detail(lines: list[str]) -> str:
    """What explains a bare "exited N": the last `hint:` block, else the last error block of uv (`× ...` with
    its `╰─▶` lines), joined into one line."""
    def block(start: int) -> str:
        parts = [lines[start]]
        for line in lines[start + 1:]:
            if _BLOCK_START.match(line):
                break
            parts.append(line)
        return re.sub(r"\s+", " ", " ".join(parts).replace("╰─▶", "")).strip()

    for pattern in (r"^hint:\s*", r"^× "):
        starts = [i for i, line in enumerate(lines) if re.match(pattern, line)]
        if starts:
            return re.sub(pattern, "", block(starts[-1]))
    return ""


def run_tool(cmd: list[str], *, env: dict[str, str] | None = None, cwd: Path | None = None,
             capture: bool = False, quiet: bool = False) -> tuple[int, str, str]:
    """Run a tool with its human output on stderr. Returns the exit code, stdout when `capture` (else ''), and
    the one-line reason of a failure (`_reason`)."""
    if not quiet:
        print("lecturekit: " + " ".join(str(c) for c in cmd), file=sys.stderr)
    try:
        proc = subprocess.Popen([str(c) for c in cmd], cwd=cwd, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, errors="replace")
    except FileNotFoundError as exc:
        raise ClipError(f"{cmd[0]} not found") from exc
    tails: dict[str, deque] = {"out": deque(maxlen=40), "err": deque(maxlen=40)}
    out: list[str] = []

    def pump(stream, keep: list[str] | None, tail: deque) -> None:
        for line in stream:
            if keep is not None:
                keep.append(line)
                continue
            tail.append(line)
            if not quiet:
                sys.stderr.write(line)
                sys.stderr.flush()

    threads = [threading.Thread(target=pump, args=(proc.stderr, None, tails["err"]), daemon=True),
               threading.Thread(target=pump, args=(proc.stdout, out if capture else None, tails["out"]), daemon=True)]
    for th in threads:
        th.start()
    rc = proc.wait()
    for th in threads:
        th.join()
    # the two streams interleave unpredictably: read stdout as printed above stderr, whose last line is the verdict
    return rc, "".join(out), _reason([*tails["out"], *tails["err"]])


def tool_env(deck: Path) -> dict[str, str]:
    """The environment for Manim and scianim: the bundled fonts through fontconfig (unless FONTCONFIG_FILE is
    set) and a terminal width that keeps manim8's messages on one line."""
    env = dict(os.environ)
    env.setdefault("COLUMNS", str(max(shutil.get_terminal_size((200, 24)).columns, 200)))
    if "FONTCONFIG_FILE" not in env:
        try:
            env["FONTCONFIG_FILE"] = str(write_fonts_conf(deck))
        except OSError:
            pass
    return env


def fonts_dir(deck: Path) -> Path | None:
    """The fonts the extension bundles: the project's vendored `_extensions/lecturekit/fonts`, else the
    package's own."""
    here = Path(deck).resolve()
    for d in [here, *here.parents]:
        cand = d / "_extensions" / "lecturekit" / "fonts"
        if cand.is_dir():
            return cand.resolve()
        if (d / "_quarto.yml").exists():
            break
    try:
        from .theme import bundled_fonts_dir
        d = bundled_fonts_dir()
        return d if d.is_dir() else None
    except FileNotFoundError:
        return None


SYSTEM_FONTS_CONF = ("/etc/fonts/fonts.conf", "/opt/homebrew/etc/fonts/fonts.conf", "/usr/local/etc/fonts/fonts.conf")


def write_fonts_conf(deck: Path) -> Path:
    """`<deck>/_lecturekit/fonts.conf`: the system's fontconfig plus the bundled fonts, so that Pango in Manim
    and in manim8's worker finds TeX Gyre Heros, Pagella and Roboto by name on any machine."""
    candidates = [Path(os.environ["FONTCONFIG_PATH"]) / "fonts.conf"] if os.environ.get("FONTCONFIG_PATH") else []
    candidates += [Path(sys.prefix) / "etc" / "fonts" / "fonts.conf"] + [Path(p) for p in SYSTEM_FONTS_CONF]
    system = next((c for c in candidates if c.exists()), Path(SYSTEM_FONTS_CONF[0]))
    fonts = fonts_dir(deck)
    lines = ['<?xml version="1.0"?>', '<!DOCTYPE fontconfig SYSTEM "fonts.dtd">',
             "<!-- written by lk clips: the system configuration and lecturekit's bundled fonts -->", "<fontconfig>",
             f'  <include ignore_missing="yes">{_xml(str(system))}</include>']
    if fonts:
        lines.append(f"  <dir>{_xml(str(fonts))}</dir>")
    lines.append("</fontconfig>")
    out = Path(deck) / "_lecturekit" / "fonts.conf"
    out.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines) + "\n"
    if not out.exists() or out.read_text(encoding="utf-8") != text:
        out.write_text(text, encoding="utf-8")
    return out.resolve()


def _xml(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------------------- modes
def clip_mode(mode: str | None = None) -> str:
    """`light` (the paper preset) or `dark`, from the argument or LECTUREKIT_MODE."""
    m = (mode or os.environ.get("LECTUREKIT_MODE") or "light").strip().lower()
    if m in ("light", "paper"):
        return "light"
    if m == "dark":
        return "dark"
    raise ClipError(f"unknown mode {m!r}: light or dark")


def clips_dir(mode: str = "light") -> Path:
    """Where a preset's clips go, relative to the deck: `assets/clips/`, or `assets/clips/dark/`."""
    return CLIPS_DIR / "dark" if mode == "dark" else CLIPS_DIR


def _brand_for(deck: Path, mode: str = "light") -> Path:
    from .theme import brand_for_mode
    return brand_for_mode(deck, mode) or deck / "_brand.yml"


def _slide_color(deck: Path, mode: str | None = None) -> str:
    try:
        from .theme import load_brand
        m = clip_mode(mode)
        return load_brand(_brand_for(deck, m), mode=m).colors.get("slide", "#FFFFFF")
    except Exception:
        return "#FFFFFF"


# --------------------------------------------------------------------- kit scenes
def kit_scenes(deck: Path) -> list[tuple[Path, str]]:
    """(script, SceneClass) pairs under `anim/clip_*.py`."""
    out = []
    for script in sorted((deck / "anim").glob("clip_*.py")):
        text = script.read_text(encoding="utf-8")
        for m in re.finditer(r"^class\s+(\w+)\s*\(([^)]*Scene[^)]*)\)\s*:", text, re.M):
            out.append((script, m.group(1)))
    return out


def clip_name(script: Path, scene: str, deck: Path) -> str:
    """`clip_bar_bold.py` -> `bar-bold`; a second scene in the same script gets its class name appended."""
    stem = script.stem[len("clip_"):] if script.stem.startswith("clip_") else script.stem
    name = stem.replace("_", "-")
    if sum(1 for s, _ in kit_scenes(deck) if s == script) > 1:
        name = f"{name}-{scene.lower()}"
    return name


def _manim_exe() -> str | None:
    sibling = Path(sys.executable).with_name("manim")
    if sibling.exists():
        return str(sibling)
    return shutil.which("manim")


def render_kit_scene(deck: Path, script: Path, scene: str, size: str = KIT_SIZE, crop: bool = False,
                     background: str | None = None, mode: str | None = None, still: float | str | None = None,
                     out_dir: Path | None = None) -> ClipRecord:
    """Render one Manim scene on the kit with its sections, copy it into the preset's clips folder with its index
    first, write the stills, return the format 2 record: its stops are the scene's `checkpoint()` calls."""
    m = clip_mode(mode)
    exe = _manim_exe()
    if not exe:
        raise ClipError(INSTALL_MANIM)
    anim = (deck / "anim").resolve()   # Manim runs in anim/: its paths must not be relative to the caller's
    media = anim / "media"
    name = clip_name(script, scene, deck)
    w0, h0 = (int(v) for v in size.lower().split("x"))
    env = tool_env(deck)
    env["NM_CLIP_SIZE"] = f"{w0}x{h0}"
    env["LECTUREKIT_MODE"] = m
    env.setdefault("LECTUREKIT_BRAND", str(_brand_for(deck, m)))
    sidecar = media / "lecturekit" / f"{name}.checkpoints.jsonl"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.unlink(missing_ok=True)
    env[CHECKPOINTS_ENV] = str(sidecar)
    for old in media.rglob(f"sections/{name}.json") if media.is_dir() else []:
        old.unlink()                   # a sections index of an earlier render must not be read as this one's
    cmd = [exe, "--disable_caching", "--progress_bar", "none", "--save_sections", "-r", f"{w0},{h0}",
           "--media_dir", str(media), "-o", name, str(Path(script).resolve()), scene]
    rc, _, reason = run_tool(cmd, cwd=anim, env=env)
    if rc:
        raise ClipError(f"manim exited {rc}: {reason}" if reason else f"manim exited {rc}")
    produced = sorted(media.rglob(f"{name}.mp4"), key=lambda p: p.stat().st_mtime)
    produced = [p for p in produced if p.parent.name != "sections"]
    if not produced:
        raise ClipError(f"Manim produced no video for {scene}")
    raw = produced[-1]
    recorded = _read_checkpoints(sidecar)
    raw_table = frame_table(raw)
    candidates = kit_candidates(name, media, recorded, raw_table, raw)
    rel_dir = clips_dir(m)
    out = out_dir or (deck / rel_dir)
    out.mkdir(parents=True, exist_ok=True)
    info = probe_video(raw)
    still_at = still if still is not None else _scene_attr(script, scene, "still")
    still_frame = _kit_still_frame(name, still_at, candidates, raw_table)
    video = out / f"{name}.mp4"
    still_png = out / f"{name}.png"
    with _staging(out, name) as stage:   # the video and the stills move in together, or none does
        box = None
        if crop:
            box = _content_of(raw, sorted({0, raw_table.frames - 1, still_frame, *(c.frame for c in candidates)}),
                              background or _slide_color(deck, m), stage)
        if box:
            crop_video(raw, stage / video.name, box, [c.frame for c in candidates], raw_table.frames)
        else:
            faststart(raw, stage / video.name)
        fields = format2(stage / video.name, name, rel_dir, candidates, stage, still=(still_png.name, still_frame),
                         rests_from=(raw, raw_table) if box else None)
        w, h = fields.pop("width"), fields.pop("height")
        _move_in(stage, out, name)
    return ClipRecord(video=(rel_dir / video.name).as_posix(), still=(rel_dir / still_png.name).as_posix(),
                      width=w, height=h, duration=round(info["duration"], 3),
                      source=f"{_rel(script, deck)}:{scene}", revision=file_hash(script), producer="kit",
                      checkpoints={s["id"]: s["still"] for s in fields["stops"]} or None, **fields)


def _read_checkpoints(sidecar: Path) -> list[dict]:
    """What the scene's checkpoint() calls wrote: one JSON object per call (id, label, rest), in call order."""
    if not sidecar.exists():
        return []
    rows = []
    for line in sidecar.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def kit_candidates(name: str, media: Path, recorded: list[dict], table: FrameTable, raw: Path) -> list[Candidate]:
    """The stops of a kit clip: each section of type `lecturekit.checkpoint` in Manim's sections index starts at
    the sum of the frames of the sections before it. The sum of all sections must be the movie's decoded frame
    count, and each checkpoint section's first frame must be the movie's frame there."""
    found = sorted(media.rglob(f"sections/{name}.json"), key=lambda p: p.stat().st_mtime) if media.is_dir() else []
    if not found:
        if recorded:
            raise ClipError(f"the scene calls checkpoint() ({', '.join(r['id'] for r in recorded)}) but Manim wrote "
                            "no sections index (it needs --save_sections, which lk clips passes)")
        return []
    index_file = found[-1]
    sections = json.loads(index_file.read_text(encoding="utf-8"))
    labels = {r["id"]: r for r in recorded}
    frame = 0
    out: list[Candidate] = []
    firsts: list[tuple[Candidate, Path]] = []
    for sec in sections:
        nb = int(sec.get("nb_frames") or 0)
        video = index_file.parent / str(sec.get("video", ""))
        if nb <= 0 and video.is_file():
            nb = frame_table(video).frames
        if sec.get("type") == CHECKPOINT_SECTION:
            r = labels.get(sec.get("name"), {})
            rest = r.get("rest")
            c = Candidate(id=str(sec.get("name")), frame=frame, label=r.get("label"),
                          declared_rest=int(rest / 2 * table.fps + 1e-6) if rest else None)
            out.append(c)
            if video.is_file():
                firsts.append((c, video))
        frame += nb
    if frame != table.frames:
        raise ClipError(f"Manim's sections add up to {frame} frames, the movie has {table.frames}")
    missing = [r["id"] for r in recorded if r["id"] not in {c.id for c in out}]
    if missing:
        raise ClipError(f"checkpoint {missing[0]} has no frames after it: put an animation or a wait between it and "
                        "the next checkpoint, or the end of the scene")
    if out and out[0].frame == 0:
        raise ClipError(f"checkpoint {out[0].id} is at the first frame: a stop sits after something has been shown")
    _check_section_starts(raw, firsts)
    return out


def _check_section_starts(raw: Path, firsts: list[tuple[Candidate, Path]]) -> None:
    """Each checkpoint section's first frame, from its own file, against the movie's frame at the summed index."""
    if not firsts:
        return
    tmp = Path(tempfile.mkdtemp(prefix="._sections.", dir=raw.parent))
    try:
        movie = [tmp / f"m{c.frame}.png" for c, _ in firsts]
        extract_frames(raw, [c.frame for c, _ in firsts], movie)
        for (c, video), png in zip(firsts, movie):
            own = tmp / f"s{c.frame}.png"
            extract_frames(video, [0], [own])
            d = mean_difference(png, own)
            if d is not None and d > STILL_MATCH:
                raise ClipError(f"checkpoint {c.id}: frame {c.frame} of the movie is not the first frame of its "
                                f"section (mean difference {d:.2f})")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _kit_still_frame(name: str, still_at: Any, candidates: list[Candidate], table: FrameTable) -> int:
    """The study still of a kit clip: the last frame, a second of the clip, or a checkpoint's frame."""
    if still_at in (None, "last"):
        return table.frames - 1
    if isinstance(still_at, str):
        try:
            still_at = float(still_at)
        except ValueError:
            by_id = {c.id: c.frame for c in candidates}
            if still_at not in by_id:
                raise ClipError(f"still {still_at!r} is neither a second of the clip nor one of its checkpoints "
                                f"({', '.join(by_id) or 'it has none'})") from None
            return by_id[still_at]
    return table.nearest(float(still_at))


def _content_of(video: Path, frames: list[int], background: str, stage: Path) -> tuple[int, int, int, int] | None:
    """The box around the content of the given frames, against the slide colour."""
    pngs = [stage / f"_box{k}.png" for k in frames]
    extract_frames(video, frames, pngs)
    try:
        return union_box([b for b in (content_box(p, background) for p in pngs) if b])
    finally:
        for p in pngs:
            p.unlink(missing_ok=True)


def _scene_attr(script: Path, scene: str, attr: str):
    """A class attribute of the scene, read from the source without importing Manim."""
    text = script.read_text(encoding="utf-8")
    m = re.search(rf"^class\s+{scene}\b.*?(?=^class\s|\Z)", text, re.M | re.S)
    if not m:
        return None
    a = re.search(rf"^\s+{attr}\s*=\s*([^\n#]+)", m.group(0), re.M)
    if not a:
        return None
    try:
        return eval(a.group(1).strip(), {}, {})  # noqa: S307  (a literal on the scene class)
    except Exception:
        return a.group(1).strip().strip("'\"")


# ------------------------------------------------------------------- manim8 clips
def manim8_root(deck: Path) -> Path:
    """Where `clips/families/` is looked for: the deck, else the project root (nearest `_quarto.yml`)."""
    if (deck / "clips" / "families").is_dir():
        return deck
    try:
        from .project import find_project
        return find_project(deck)
    except FileNotFoundError:
        return deck


def manim8_projects(project_root: Path) -> list[Path]:
    """manim8 project directories (an `animation.yaml`) under `clips/families/`, groups included."""
    from .theme import _manim8_files
    fam = project_root / "clips" / "families"
    return [p.parent for p in _manim8_files(fam, "animation.yaml")] if fam.is_dir() else []


def family_of(clip_dir: Path) -> Path | None:
    """The family directory of a manim8 project: the nearest `family.yaml` above it."""
    for d in Path(clip_dir).resolve().parents:
        if (d / "family.yaml").exists():
            return d
        if (d / "workspace.yaml").exists() or (d / "_quarto.yml").exists():
            break
    return None


def scianim_exe(required: bool = True) -> str | None:
    """The `scianim` command: on PATH, else beside this Python."""
    exe = shutil.which("scianim")
    if not exe:
        sibling = Path(sys.executable).with_name("scianim")
        exe = str(sibling) if sibling.exists() else None
    if exe is None and required:
        raise ClipError(INSTALL_MANIM8 + ("" if sys.version_info >= (3, 12) else
                                          f"; this Python is {sys.version_info.major}.{sys.version_info.minor}"))
    return exe


_CAPS: dict[str, set[str]] = {}


def scianim_caps(exe: str, env: dict[str, str] | None = None) -> set[str]:
    """The options `scianim render` accepts (an older manim8 has no `--json` and no `--style`)."""
    if exe not in _CAPS:
        r = subprocess.run([exe, "render", "--help"], capture_output=True, text=True, env=env)
        text = _ANSI.sub("", r.stdout + r.stderr)
        _CAPS[exe] = {opt for opt in ("--json", "--style", "--revision", "--profile", "--no-cache") if opt in text}
    return _CAPS[exe]


def _manifest_by_prefix(clip_dir: Path, printed: str) -> dict:
    """The manifest of the job an older `scianim render` (without --json) just ran or found in its cache: the
    one whose `job.cache_key` starts with the 23 characters it printed. Never the newest file."""
    m = re.findall(r"(sha256:[0-9a-f]{16})", printed)
    if not m:
        raise ClipError("scianim render printed no cache key, and this manim8 has no --json")
    prefix = m[-1]
    found = []
    for path in sorted((clip_dir / "renders").rglob("manifest.json")) if (clip_dir / "renders").is_dir() else []:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        job = data.get("job") or {}
        if str(job.get("cache_key", "")).startswith(prefix) and job.get("operation", "render_video") == "render_video" \
                and (data.get("result") or {}).get("status") == "succeeded":
            found.append(data)
    if not found:
        raise ClipError(f"no succeeded render manifest with cache key {prefix}... under {clip_dir / 'renders'}")
    return sorted(found, key=lambda d: str(d.get("created_at", "")))[-1]


def render_manim8(deck: Path, clip_dir: Path, profile: str = "final", still: str | float | None = None,
                  revision: str | None = None, style: str | None = None, mode: str | None = None,
                  sync: bool = True, crop: bool = False, size: str | None = None, background: str | None = None,
                  out_dir: Path | None = None, no_cache: bool = False) -> ClipRecord:
    """Render a manim8 project and bring its full movie, its checkpoints and its still into the deck. With
    `no_cache`, manim8 renders the job even when its cache holds the result."""
    m = clip_mode(mode)
    exe = scianim_exe()
    env = tool_env(deck)
    family = family_of(clip_dir)
    if family is None:
        raise ClipError(f"{clip_dir} is not inside a manim8 family (no family.yaml above it)")
    if not (family / ".venv").exists():
        if not sync:
            raise ClipError(f"the family environment {family / '.venv'} is missing: run `scianim family env sync "
                            f"{family}` (lk clips does it unless --no-sync)")
        rc, _, reason = run_tool([exe, "family", "env", "sync", str(family)], env=env)
        if rc:
            raise ClipError(f"scianim family env sync failed: {reason}")
    if revision is None:
        rc, _, reason = run_tool([exe, "codegen", str(clip_dir)], env=env)
        if rc:
            raise ClipError(f"scianim codegen failed: {reason}")
    caps = scianim_caps(exe, env)
    cmd = [exe, "render", str(clip_dir), "--profile", profile]
    if revision:
        cmd += ["--revision", revision]
    if style:
        if "--style" in caps:
            cmd += ["--style", style]
        elif m == "dark":
            raise ClipError(f"this manim8 has no `render --style`, so it cannot render under {style}; upgrade manim8")
        else:
            print(f"lecturekit: this manim8 has no `render --style`; {clip_dir.name} renders in the style its "
                  "animation.yaml names", file=sys.stderr)
    if no_cache:
        if "--no-cache" not in caps:
            raise ClipError("this manim8 has no `render --no-cache`; upgrade manim8")
        cmd.append("--no-cache")
    as_json = "--json" in caps
    if as_json:
        cmd.append("--json")
    manifest, hit = _run_render(cmd, clip_dir, env, as_json)
    name = clip_dir.name
    misses = font_misses(manifest)
    if hit and misses and "--no-cache" in caps and "FONTCONFIG_FILE" not in os.environ \
            and not _recorded(deck, m, name, (manifest.get("job") or {}).get("job_id")):
        # a job rendered outside lk clips (a `scianim render` in the workspace, on a machine without the deck's
        # fonts) is in manim8's cache, whose key does not depend on the fonts: render it once more with them
        print(f"lecturekit: clip {name}: the cached job {(manifest.get('job') or {}).get('job_id')} was rendered "
              f"without the deck's fonts ({misses[0]}); rendering it again with them", file=sys.stderr)
        manifest, hit = _run_render([*cmd, "--no-cache"], clip_dir, env, as_json)
    for warning in (manifest.get("result") or {}).get("warnings") or []:
        print(f"lecturekit: clip {name}: manim8 warns: {warning}", file=sys.stderr)
    return manim8_record(deck, clip_dir, manifest, still=still, crop=crop, size=size, mode=m,
                         background=background, out_dir=out_dir)


def _run_render(cmd: list[str], clip_dir: Path, env: dict[str, str], as_json: bool) -> tuple[dict, bool]:
    """Run `scianim render` and return the manifest of the job it ran or found in its cache, and whether it was a
    cache hit."""
    rc, printed, reason = run_tool(cmd, env=env, capture=True)
    if not as_json and printed:
        sys.stderr.write(printed)
    if rc:
        raise ClipError(f"scianim render exited {rc}: {reason}" if reason else f"scianim render exited {rc}")
    if as_json:
        try:
            manifest = json.loads(printed)
        except ValueError as exc:
            raise ClipError("scianim render --json did not print one JSON manifest") from exc
        return manifest, bool(manifest.get("cache_hit"))
    return _manifest_by_prefix(clip_dir, printed), "cache hit" in printed


def font_misses(manifest: dict) -> list[str]:
    """The manifest's font warnings that say a face was replaced by one lecturekit does not bundle: a generic
    family or Pango's substitute (`font 'TeX Gyre Heros' is not installed; using the generic 'sans-serif'
    family`). A fallback to a bundled face (`using fallback 'TeX Gyre Pagella'`) is not a miss."""
    from .theme import BUNDLED_FONTS
    out = []
    for warning in (manifest.get("result") or {}).get("warnings") or []:
        text = str(warning)
        if not re.match(r"font '", text):
            continue
        used = re.search(r"using fallback '([^']+)'", text)
        if used and used.group(1) in BUNDLED_FONTS:
            continue
        out.append(text)
    return out


def _recorded(deck: Path, mode: str, name: str, job_id: str | None) -> bool:
    """Whether the preset's index already records this job for the clip (lk clips brought it in before)."""
    try:
        index = load_index(deck, mode)
    except (OSError, ValueError):
        return False
    return any(norm_name(k) == norm_name(name) and isinstance(v, dict) and (v.get("job") or {}).get("id") == job_id
               for k, v in index.items())


#: the frame rate of the kit's clips; a manim8 project's output is compared with it and with the kit's size
KIT_FPS = 30.0


def _check_output(name: str, width: int, height: int, fps: float | None, size: str | None) -> None:
    """Warn when a manim8 clip's size or frame rate is not the deck's: `--size` when given, else the kit's 1280
    by 720, and 30 fps. A manim8 clip renders at its project's output, which `--size` does not reach."""
    want = tuple(int(v) for v in (size or KIT_SIZE).lower().split("x"))
    if (width, height) == want and (fps is None or abs(float(fps) - KIT_FPS) < 0.01):
        return
    at = f" at {float(fps):g} fps" if fps is not None else ""
    where = (f"--size {size} applies to kit clips only" if size else
             f"the deck's clips are {KIT_SIZE} at {KIT_FPS:g} fps")
    print(f"lecturekit: warning: clip {name} is {width}x{height}{at}, as its manim8 project's output says; {where} "
          "(set output in animation.yaml)", file=sys.stderr)


def manim8_record(deck: Path, clip_dir: Path, manifest: dict, still: str | float | None = None, crop: bool = False,
                  size: str | None = None, mode: str | None = None, background: str | None = None,
                  out_dir: Path | None = None) -> ClipRecord:
    """Copy what a manim8 render manifest names into the preset's clips folder and return the record. Nothing in
    the folder changes unless every file of the clip was made: they are made in a staging folder beside it and
    moved in at the end, so a failure leaves the folder as the index describes it."""
    m = clip_mode(mode)
    name = clip_dir.name
    version = str(manifest.get("schema_version"))
    if version not in MANIFEST_SCHEMAS:
        raise ClipError(f"the manifest's schema_version {version!r} is not one this lecturekit reads "
                        f"({', '.join(MANIFEST_SCHEMAS)}); upgrade lecturekit")
    job = manifest.get("job") or {}
    result = manifest.get("result") or {}
    if result.get("status") != "succeeded":
        errors = result.get("errors") or []
        raise ClipError(f"render {job.get('job_id', '?')} {result.get('status', 'did not succeed')}"
                        + (f": {errors[0]}" if errors else ""))
    if job.get("operation", "render_video") != "render_video" or not result.get("videos"):
        raise ClipError(f"manifest of job {job.get('job_id', '?')} lists no video (a snapshot job)")
    v0 = result["videos"][0]
    movie = clip_dir / v0["path"]
    if not movie.exists():
        raise ClipError(f"the manifest's video {v0['path']} is not in {clip_dir}")
    checkpoints = []
    for c in result.get("checkpoints") or []:
        png = clip_dir / c.get("png", "")
        if not c.get("snapshot_id") or not png.is_file():
            print(f"lecturekit: clip {name}: checkpoint {c.get('snapshot_id')} has no PNG at {png}", file=sys.stderr)
            continue
        t = c.get("renderer_time_seconds", c.get("expected_time_seconds"))
        checkpoints.append((str(c["snapshot_id"]), png, float(t) if t is not None else -1.0))
    if still is not None and str(still) not in {sid for sid, _, _ in checkpoints}:
        try:
            float(still)
        except (TypeError, ValueError):
            raise ClipError(f"--still {name}={still}: the job has no checkpoint {str(still)!r} "
                            f"(it has {', '.join(sid for sid, _, _ in checkpoints) or 'none'})") from None
    width, height = int(v0["width_px"]), int(v0["height_px"])
    _check_output(name, width, height, v0.get("fps"), size)
    raw_table = frame_table(movie)
    candidates = manim8_candidates(name, manifest, raw_table)
    declared = v0.get("frame_count")
    if declared is not None and int(declared) != raw_table.frames:
        message = f"the manifest says the movie has {declared} frames; decoding it gives {raw_table.frames}"
        if candidates:
            raise ClipError(f"{message}, so its stops' frames cannot be trusted")
        _warn(name, message)
    rel_dir = clips_dir(m)
    out = out_dir or (deck / rel_dir)
    out.mkdir(parents=True, exist_ok=True)
    with _staging(out, name) as stage:
        box = None
        if crop:
            bg = background or _slide_color(deck, m)
            frames = [p for _, p, _ in checkpoints]
            box = union_box([b for b in (content_box(f, bg) for f in frames) if b]) if frames else \
                _content_of(movie, [raw_table.frames - 1], bg, stage)
        if box:
            crop_video(movie, stage / f"{name}.mp4", box, [c.frame for c in candidates], raw_table.frames)
        else:
            faststart(movie, stage / f"{name}.mp4")
        copied: dict[str, str] = {}
        for sid, png, _ in checkpoints:
            dst = stage / f"{name}.{sid}.png"
            if box:
                crop_image(png, dst, box)
            else:
                shutil.copy2(png, dst)
            copied[sid] = (rel_dir / dst.name).as_posix()
        for c in candidates:   # the still of each stop is compared with manim8's own picture of that frame
            if c.id in copied:
                c.picture = stage / f"{name}.{c.id}.png"
        still_path, extract = _manim8_still(name, still, checkpoints, copied, raw_table, rel_dir)
        fields = format2(stage / f"{name}.mp4", name, rel_dir, candidates, stage, still=extract,
                         rests_from=(movie, raw_table) if box else None)
        width, height = fields.pop("width"), fields.pop("height")
        # every file is made: move them in, then drop the checkpoints (and a still) of an earlier job
        made = _move_in(stage, out, name)
    stale = re.compile(rf"^{re.escape(name)}\.([a-z][a-z0-9_]*)\.png$")
    for old in out.glob(f"{name}.*.png"):
        hit = stale.match(old.name)
        if hit and old.name not in made:
            old.unlink()
    if f"{name}.png" not in made:
        (out / f"{name}.png").unlink(missing_ok=True)
    resolved = job.get("resolved_style") or {}
    job_rec = {"id": job.get("job_id"), "cache_key": job.get("cache_key"),
               "registry_version": job.get("registry_version"),
               "style": f"{resolved['theme']}@{resolved['theme_version']}"
               if resolved.get("theme") and resolved.get("theme_version") else None}
    return ClipRecord(video=(rel_dir / f"{name}.mp4").as_posix(), still=still_path, width=width, height=height,
                      duration=round(float(v0["duration_seconds"]), 3) if v0.get("duration_seconds") is not None
                      else None,
                      source=_rel(clip_dir, deck), revision=job.get("revision_id"), producer="manim8",
                      job={k: v for k, v in job_rec.items() if v is not None},
                      checkpoints=copied or None, **fields)


def manim8_candidates(name: str, manifest: dict, table: FrameTable) -> list[Candidate]:
    """The stops of a manim8 clip: `result.stops`, which manim8 derives from the snapshots marked `stop: true`
    (ADR-045). Each one's `frame_index` must be its time on the movie's frame grid (a disagreement stops the
    clip); a stop where no play starts, or whose rest is not static plays, is a warning (manim8 refuses both in a
    final render and only warns in a draft). A manifest without `result.stops` gives no candidates."""
    result = manifest.get("result") or {}
    snapshots = (manifest.get("job") or {}).get("snapshots") or {}
    fps = table.fps
    plays = []
    for p in result.get("plays") or []:
        try:
            first = round(float(p["start_seconds"]) * fps)
            plays.append((first, first + int(p.get("frames", 1)), bool(p.get("static"))))
        except (KeyError, TypeError, ValueError):
            continue
    out = []
    for s in result.get("stops") or []:
        sid, k = s.get("snapshot_id"), s.get("frame_index")
        if not sid or k is None:
            raise ClipError(f"a stop in the manifest has no snapshot_id or frame_index: {json.dumps(s)[:120]}")
        k = int(k)
        t = s.get("time_seconds")
        if t is not None and round(float(t) * fps) != k:
            raise ClipError(f"stop {sid}: frame_index {k} is not its time, {float(t):g} s at {fps:g} fps "
                            f"(frame {round(float(t) * fps)})")
        before = s.get("rest_before_frames")
        if plays:
            if not any(first == k for first, _, _ in plays):
                _warn(name, f"stop {sid}: no play of the movie starts at its frame {k}")
            if before:
                moving = [first for first, last, static in plays if first < k and last > k - int(before)
                          and not static]
                if moving:
                    _warn(name, f"stop {sid}: a play that moves (from frame {moving[0]}) runs in the "
                          f"{int(before)} frames of rest before it")
        notes = s.get("notes") or (snapshots.get(sid) or {}).get("description")
        out.append(Candidate(id=str(sid), frame=k, label=s.get("label"), notes=notes,
                             frozen=[str(f) for f in s.get("frozen") or []],
                             declared_rest=int(before) if before is not None else None))
    return out


@contextmanager
def _staging(out: Path, name: str):
    """A fresh folder beside `out` for one clip's files, removed afterwards whatever happened."""
    stage = Path(tempfile.mkdtemp(prefix=f".{name}.", dir=out))
    try:
        yield stage
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def _manim8_still(name, still, checkpoints, copied, table: FrameTable, rel_dir: Path):
    """The still of a manim8 clip: the named checkpoint, a frame of the movie at a second, or the latest
    checkpoint (the last frame when the job has none). Returns its path and, for a frame of the movie, the file
    name and frame number to extract."""
    seconds = None
    if still is not None:
        sid = str(still)
        if sid in copied:
            return copied[sid], None
        try:
            seconds = float(still)
        except (TypeError, ValueError):
            raise ClipError(f"--still {name}={sid}: the job has no checkpoint {sid!r} "
                            f"(it has {', '.join(copied) or 'none'})") from None
    if seconds is None and checkpoints:
        latest = max(checkpoints, key=lambda c: c[2])
        return copied[latest[0]], None
    frame = table.nearest(seconds) if seconds is not None else table.frames - 1
    return (rel_dir / f"{name}.png").as_posix(), (f"{name}.png", frame)


# ----------------------------------------------------------------------- the index
def index_path(deck: Path, mode: str = "light") -> Path:
    return deck / clips_dir(mode) / "clips.json"


def load_index(deck: Path, mode: str = "light") -> dict:
    p = index_path(deck, mode)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_index(deck: Path, index: dict, mode: str = "light") -> Path:
    """Write the index, sorted, with no null value anywhere."""
    p = index_path(deck, mode)
    p.parent.mkdir(parents=True, exist_ok=True)
    clean = {k: {f: v for f, v in rec.items() if v is not None} if isinstance(rec, dict) else rec
             for k, rec in index.items()}
    p.write_text(json.dumps(clean, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def store(index: dict, name: str, rec: ClipRecord | dict) -> None:
    """Put a record under its name, replacing an entry spelled with the other separator (`bar_bold` for
    `bar-bold`), since both name one clip."""
    for key in [k for k in index if k != name and norm_name(k) == norm_name(name)]:
        print(f"lecturekit: the index entry {key!r} is now {name!r}", file=sys.stderr)
        del index[key]
    index[name] = rec.to_dict() if isinstance(rec, ClipRecord) else rec


def index_existing(deck: Path, mode: str = "light") -> dict:
    """The index with an entry (without `format`) for each MP4 already in the preset's clips folder that it does
    not name, with or without a .png beside it; nothing is rendered, copied or saved. For older callers:
    `lk clips adopt` is the way to bring an MP4 in."""
    index = load_index(deck, mode)
    known = {norm_name(k) for k in index}
    rel_dir = clips_dir(mode)
    folder = deck / rel_dir
    for video in sorted(folder.glob("*.mp4")) if folder.exists() else []:
        name = video.stem
        if norm_name(name) in known:
            continue
        info = probe_video(video)
        still = video.with_suffix(".png")
        index[name] = ClipRecord(video=(rel_dir / video.name).as_posix(),
                                 still=(rel_dir / still.name).as_posix() if still.exists() else None,
                                 width=info["width"], height=info["height"], fps=info["fps"],
                                 duration=info["duration"], source=(rel_dir / video.name).as_posix(),
                                 revision=file_hash(video), producer="external").to_dict()
    return index


CLIP_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


def parse_stops(stops: list[str] | None, labels: list[str] | None) -> list[tuple[str, float, str | None]]:
    """`--stops 4.0 8.0` or `--stops lenient=4.0 strict=8.0`, with `--labels` in the same order: (id, seconds,
    label) triples. A bare second gets the id `stop_1`, `stop_2`, ... by its position."""
    stops, labels = list(stops or []), list(labels or [])
    if labels and len(labels) != len(stops):
        raise ClipError(f"{len(labels)} label{'s' if len(labels) != 1 else ''} for {len(stops)} "
                        f"stop{'s' if len(stops) != 1 else ''}: give one label per stop, in the same order")
    out = []
    for i, item in enumerate(stops):
        sid, sep, value = str(item).rpartition("=")
        sid = sid.strip() if sep else f"stop_{i + 1}"
        try:
            seconds = float(value)
        except ValueError:
            raise ClipError(f"--stops {item}: a stop is a second of the video, or ID=SECONDS") from None
        if seconds < 0:
            raise ClipError(f"--stops {item}: a negative second")
        out.append((sid, seconds, labels[i] if labels else None))
    return out


def adopt(deck: Path, src: Path, name: str, stops: list[str] | None = None, labels: list[str] | None = None,
          mode: str | None = None, crop: bool = False, size: str | None = None,
          background: str | None = None) -> ClipRecord:
    """Bring an MP4 made elsewhere into the deck: copy it to the preset's clips folder with its index first (by
    stream copy; `crop` or `size` re-encode it with a keyframe at every stop), write its stills and its format 2
    entry, and save the index. Each stop is a second of the video, snapped to the nearest frame."""
    deck, src = Path(deck), Path(src)
    m = clip_mode(mode)
    if not CLIP_NAME.match(name):
        raise ClipError(f"--name {name!r}: a clip name is lower case letters, digits, _ and -, starting with a letter")
    if not src.is_file():
        raise ClipError(f"{src} is not a file")
    for clip in find_clips(deck):
        if norm_name(clip.name) == norm_name(name):
            raise ClipError(f"{name!r} is the {clip.producer} clip {_rel(clip.path, deck)}, which lk clips renders; "
                            "adopt the file under another name")
    table = frame_table(src)
    if table.codec and table.codec != "h264" and not (crop or size):
        _warn(name, f"the video is {table.codec}, which not every browser plays; --size WxH re-encodes it as H.264")
    candidates = []
    for sid, seconds, label in parse_stops(stops, labels):
        if seconds > table.pts[-1] + 1 / table.fps:
            raise ClipError(f"stop {sid} at {seconds:g} s is after the end of the video ({table.pts[-1]:g} s)")
        candidates.append(Candidate(id=sid, frame=table.nearest(seconds), label=label))
    check_candidates(name, candidates, table, warn=False)   # refuse before anything is copied
    rel_dir = clips_dir(m)
    out = deck / rel_dir
    out.mkdir(parents=True, exist_ok=True)
    keys = [c.frame for c in candidates]
    with _staging(out, name) as stage:
        video = stage / f"{name}.mp4"
        filters = []
        if crop:
            box = _content_of(src, sorted({0, table.frames - 1, *keys}), background or _slide_color(deck, m), stage)
            if box:
                x, y, w, h = box
                filters.append(f"crop={w}:{h}:{x}:{y}")
        if size:
            try:
                w, h = (int(v) for v in size.lower().split("x"))
            except ValueError:
                raise ClipError(f"--size {size}: WxH, for example 1280x720") from None
            filters.append(f"scale={w}:{h}")
        if filters:
            reencode(src, video, filters, keys, table.frames)
        else:
            faststart(src, video)
        fields = format2(video, name, rel_dir, candidates, stage, still=(f"{name}.png", table.frames - 1),
                         rests_from=(src, table) if filters else None)
        width, height = fields.pop("width"), fields.pop("height")
        info = probe_video(video)
        _move_in(stage, out, name)
    inside = src.resolve().is_relative_to(deck.resolve())
    rec = ClipRecord(video=(rel_dir / f"{name}.mp4").as_posix(), still=(rel_dir / f"{name}.png").as_posix(),
                     width=width, height=height, duration=info["duration"],
                     source=_rel(src, deck) if inside else src.name, revision=file_hash(src), producer="external",
                     checkpoints={s["id"]: s["still"] for s in fields["stops"]} or None, **fields)
    index = load_index(deck, m)
    store(index, name, rec)
    save_index(deck, index, m)
    return rec


# ------------------------------------------------------------------------ the run
def find_clips(deck: Path) -> list[Clip]:
    """Every clip of the deck: its kit scenes and the manim8 projects of its workspace."""
    clips = []
    for script, scene in kit_scenes(deck):
        name = clip_name(script, scene, deck)
        stem = script.stem[len("clip_"):] if script.stem.startswith("clip_") else script.stem
        clips.append(Clip(name, "kit", script, scene, [name, stem, script.stem, scene]))
    for clip_dir in manim8_projects(manim8_root(deck)):
        clips.append(Clip(clip_dir.name, "manim8", clip_dir, None, [clip_dir.name]))
    return clips


def collisions(clips: list[Clip]) -> list[str]:
    """Clip names that are one name under `-`/`_` equivalence, as messages."""
    by: dict[str, list[Clip]] = {}
    for c in clips:
        by.setdefault(norm_name(c.name), []).append(c)
    return [" and ".join(f"{c.name!r} ({c.producer}, {c.path.name if c.producer == 'kit' else c.path})" for c in group)
            + " are one clip name; rename one" for group in by.values() if len(group) > 1]


def _per_clip(values: list[str] | None, what: str) -> tuple[dict[str, str], str | None]:
    """`CLIP=VALUE` items by normalized clip name, and a bare VALUE for every clip."""
    named: dict[str, str] = {}
    bare = None
    for item in values or []:
        if "=" in item:
            clip, _, value = item.partition("=")
            named[norm_name(clip)] = value.strip()
        else:
            bare = item.strip()
    return named, bare


def _style_for(root: Path, clip_dir: Path, mode: str, cache: dict) -> str | None:
    """The `--style` of a manim8 clip in a preset. Dark: the brand's newest bridged dark style, which every
    clip renders under. Paper: the newest bridged paper style, for a project that selects that style (in any
    version); a project that selects another style keeps it."""
    from .theme import _style_of, bridged_style
    if (root, mode) not in cache:
        cache[(root, mode)] = bridged_style(root, mode)
    style = cache[(root, mode)]
    if mode == "dark":
        if not style:
            raise ClipError("no bridged dark style in the workspace: run `lk theme <project> --manim8 VERSION` "
                            "first")
        return style
    if style and _style_of(clip_dir / "animation.yaml")[0] == style.split("@")[0]:
        return style
    return None


def run_clips(deck: Path, only: list[str] | None = None, size: str | None = None, crop: bool = False,
              mode: str | None = None, stills: list[str] | None = None, revisions: list[str] | None = None,
              profile: str = "final", sync: bool = True, no_cache: bool = False) -> tuple[dict, list[Failure]]:
    """Render the deck's clips into the preset's folder. Returns the index and the clips that failed.
    `no_cache` makes manim8 render its projects even when its cache holds them (kit scenes always render)."""
    deck = Path(deck)
    m = clip_mode(mode)
    index = load_index(deck, m)
    failures: list[Failure] = []
    clips = find_clips(deck)
    for message in collisions(clips):
        failures.append(Failure("-", "-", message))
    if failures:
        for f in failures:
            print(f"lecturekit: error: {f.reason}", file=sys.stderr)
        return index, failures
    wanted = {norm_name(o) for o in only or []}
    matched: set[str] = set()
    still_for, _ = _per_clip(stills, "still")
    rev_for, rev_all = _per_clip(revisions, "revision")
    styles: dict = {}
    for clip in clips:
        hits = {norm_name(a) for a in clip.aliases} & wanted
        if wanted and not hits:
            continue
        matched |= hits
        key = norm_name(clip.name)
        try:
            if clip.producer == "kit":
                still = still_for.get(key)   # a second of the clip, or one of its checkpoints
                rec = render_kit_scene(deck, clip.path, clip.scene or "", size=size or KIT_SIZE, crop=crop,
                                       mode=m, still=still)
            else:
                if not (clip.path / "storyboard.yaml").exists():
                    if wanted:
                        raise ClipError("the project has no storyboard.yaml yet")
                    print(f"lecturekit: manim8 project {clip.name} has no storyboard.yaml yet; skipped",
                          file=sys.stderr)
                    continue
                style = _style_for(manim8_root(deck), clip.path, m, styles)
                rec = render_manim8(deck, clip.path, profile=profile, still=still_for.get(key),
                                    revision=rev_for.get(key, rev_all), style=style, mode=m, sync=sync,
                                    crop=crop, size=size, no_cache=no_cache)
        except Exception as exc:  # one clip's failure is reported, and the run goes on
            reason = _last_line(str(exc).splitlines()) or exc.__class__.__name__
            failures.append(Failure(clip.name, clip.producer, reason))
            print(f"lecturekit: clip {clip.name} ({clip.producer}) failed: {reason}", file=sys.stderr)
            continue
        store(index, clip.name, rec)
        save_index(deck, index, m)
        n = len(rec.stops or [])
        print(f"lecturekit: {clip.producer} clip {clip.name}: {rec.width}x{rec.height}, {rec.duration}s, "
              f"{rec.frames} frames, {n} stop{'s' if n != 1 else ''} -> {rec.video}", file=sys.stderr)
    for o in only or []:
        if norm_name(o) not in matched:
            names = ", ".join(c.name for c in clips) or "none"
            failures.append(Failure(o, "-", f"--only {o} names no clip (the deck's clips: {names})"))
            print(f"lecturekit: --only {o} names no clip (the deck's clips: {names})", file=sys.stderr)
    save_index(deck, index, m)
    return index, failures


def render_all(deck: Path, only: list[str] | None = None, size: str | None = None, crop: bool = False,
               mode: str | None = None, **kw) -> dict:
    """Render the deck's clips and return the index (failures are reported on stderr; see `run_clips`)."""
    index, _ = run_clips(deck, only=only, size=size, crop=crop, mode=mode, **kw)
    return index
