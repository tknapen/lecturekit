"""`lk clips`: render a deck's clips and write `assets/clips/clips.json`.

The seam between the deck and whatever made the clip. A deck's movie block names a clip:

    ::: {.movie clip="bar-bold" height=4cm}

and `assets/clips/clips.json` says what that name means:

    {"bar-bold": {"video": "assets/clips/bar-bold.mp4", "still": "assets/clips/bar-bold.png",
                  "width": 1280, "height": 720, "duration": 20.0,
                  "source": "anim/clip_bar_bold.py:BarBold", "revision": "<sha1 of the script>"}}

Two producers fill it:

* kit scenes: `anim/clip_<name>.py`, one or more Manim `Scene` classes on the shared kit (`from kit import *`).
  Rendered with Manim at 1280 by 720 on white, as the presentation policy asks (`--size 1920x1080` or the
  environment variable NM_CLIP_SIZE for another size; the kit reads it), 30 fps, without a title. The video is
  copied to `assets/clips/<name>.mp4`; its last frame becomes the still `<name>.png` unless the scene class sets
  `still = <seconds>`; `--crop` trims the video and the still to the content's bounding box (for a clip in a
  column), and clips.json records the resulting shape, which the deck uses as the clip's aspect.
* manim8 projects: `clips/families/<family>/<name>/` rendered with `scianim render --profile final` (the second
  release); the final video and the named checkpoint PNG are copied in and the render manifest supplies the
  dimensions, duration and revision.

A re-rendered clip that looks unchanged on screen is a browser cache at work: browsers cache clips by file name.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

CLIPS_DIR = Path("assets/clips")


@dataclass
class ClipRecord:
    video: str
    still: str | None
    width: int
    height: int
    duration: float
    source: str
    revision: str


def _ffmpeg() -> str | None:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg  # type: ignore
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def probe(video: Path) -> tuple[int, int, float]:
    """Width, height and duration of a video, through ffmpeg's banner output."""
    exe = _ffmpeg()
    if not exe:
        raise RuntimeError("ffmpeg not found (pip install imageio-ffmpeg, or install ffmpeg)")
    r = subprocess.run([exe, "-i", str(video)], capture_output=True, text=True)
    text = r.stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", text)
    duration = float(m.group(1)) * 3600 + float(m.group(2)) * 60 + float(m.group(3)) if m else 0.0
    m2 = re.search(r"Video:.*? (\d{2,5})x(\d{2,5})", text)
    if not m2:
        raise RuntimeError(f"could not read dimensions of {video}")
    return int(m2.group(1)), int(m2.group(2)), duration


def content_box(image_path: Path, background: str, margin: int = 24) -> tuple[int, int, int, int] | None:
    """Bounding box of everything that is not the background colour, with a margin, even-sized."""
    from PIL import Image, ImageChops
    im = Image.open(image_path).convert("RGB")
    bg = Image.new("RGB", im.size, background)
    diff = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 12 else 0)
    box = diff.getbbox()
    if not box:
        return None
    x0, y0, x1, y1 = box
    x0, y0 = max(0, x0 - margin), max(0, y0 - margin)
    x1, y1 = min(im.width, x1 + margin), min(im.height, y1 + margin)
    w, h = (x1 - x0) // 2 * 2, (y1 - y0) // 2 * 2
    return x0, y0, w, h


def extract_frame(video: Path, at: float, out: Path) -> None:
    exe = _ffmpeg()
    subprocess.run([exe, "-y", "-loglevel", "error", "-ss", f"{max(at, 0):.3f}", "-i", str(video),
                    "-frames:v", "1", str(out)], check=True)


def crop_video(src: Path, dst: Path, box: tuple[int, int, int, int]) -> None:
    exe = _ffmpeg()
    x, y, w, h = box
    subprocess.run([exe, "-y", "-loglevel", "error", "-i", str(src), "-vf", f"crop={w}:{h}:{x}:{y}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart",
                    "-an", str(dst)], check=True)


def file_hash(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()[:12]


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


def render_kit_scene(deck: Path, script: Path, scene: str, size: str = "1280x720", crop: bool = False,
                     background: str | None = None) -> ClipRecord:
    """Render one Manim scene on the kit, copy it into assets/clips, write the still, return the record."""
    media = deck / "anim" / "media"
    name = clip_name(script, scene, deck)
    w0, h0 = (int(v) for v in size.lower().split("x"))
    env = dict(os.environ, NM_CLIP_SIZE=f"{w0}x{h0}")
    env.setdefault("LECTUREKIT_BRAND", str(_brand_for(deck)))
    manim = Path(sys.executable).with_name("manim")
    cmd = [str(manim) if manim.exists() else "manim", "--disable_caching", "--progress_bar", "none", "-r", f"{w0},{h0}",
           "--media_dir", str(media), "-o", name, str(script), scene]
    print("lecturekit: " + " ".join(cmd), file=sys.stderr)
    subprocess.run(cmd, cwd=deck / "anim", env=env, check=True)
    produced = sorted(media.rglob(f"{name}.mp4"), key=lambda p: p.stat().st_mtime)
    if not produced:
        raise RuntimeError(f"Manim produced no video for {scene}")
    raw = produced[-1]
    out_dir = deck / CLIPS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    w, h, duration = probe(raw)
    still_at = _scene_attr(script, scene, "still")
    at = duration - 0.05 if still_at in (None, "last") else float(still_at)
    tmp_frame = out_dir / f"_{name}_frame.png"
    extract_frame(raw, at, tmp_frame)
    video = out_dir / f"{name}.mp4"
    still = out_dir / f"{name}.png"
    box = content_box(tmp_frame, background or _slide_color(deck)) if crop else None
    if box:
        crop_video(raw, video, box)
        from PIL import Image
        x, y, bw, bh = box
        Image.open(tmp_frame).crop((x, y, x + bw, y + bh)).save(still)
        w, h = bw, bh
    else:
        shutil.copy2(raw, video)
        shutil.copy2(tmp_frame, still)
    tmp_frame.unlink(missing_ok=True)
    return ClipRecord(video=str(CLIPS_DIR / video.name), still=str(CLIPS_DIR / still.name), width=w, height=h,
                      duration=round(duration, 3), source=f"{script.relative_to(deck)}:{scene}",
                      revision=file_hash(script))


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


def _brand_for(deck: Path) -> Path:
    from .theme import find_brand
    return find_brand(deck) or deck / "_brand.yml"


def _slide_color(deck: Path) -> str:
    try:
        from .theme import load_brand
        return load_brand(_brand_for(deck), mode=os.environ.get("LECTUREKIT_MODE", "light")).colors.get("slide", "#FFFFFF")
    except Exception:
        return "#FFFFFF"


# ------------------------------------------------------------------- manim8 clips
def manim8_projects(project_root: Path) -> list[Path]:
    """`clips/families/<family>/<clip>/` directories holding a storyboard.yaml."""
    fam = project_root / "clips" / "families"
    return sorted(p.parent for p in fam.glob("*/*/storyboard.yaml")) if fam.exists() else []


def render_manim8(deck: Path, clip_dir: Path, profile: str = "final", still_checkpoint: str | None = None) -> ClipRecord:
    """Render a manim8 project and bring its final video and still into the deck."""
    exe = shutil.which("scianim") or shutil.which("manim8")
    if not exe:
        raise RuntimeError("manim8 not installed (pip install lecturekit[manim8])")
    subprocess.run([exe, "render", str(clip_dir), "--profile", profile], check=True)
    renders = clip_dir / "renders"
    manifests = sorted(renders.rglob("manifest.json"), key=lambda p: p.stat().st_mtime) if renders.exists() else []
    manifest = json.loads(manifests[-1].read_text(encoding="utf-8")) if manifests else {}
    videos = sorted(renders.rglob("*.mp4"), key=lambda p: p.stat().st_mtime)
    if not videos:
        raise RuntimeError(f"manim8 produced no video in {clip_dir}")
    raw = videos[-1]
    out_dir = deck / CLIPS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    name = clip_dir.name
    video = out_dir / f"{name}.mp4"
    shutil.copy2(raw, video)
    still = None
    stills = sorted((clip_dir / "checkpoints").rglob("*.png")) if (clip_dir / "checkpoints").exists() else []
    if still_checkpoint:
        stills = [s for s in stills if still_checkpoint in s.stem] or stills
    if stills:
        still = out_dir / f"{name}.png"
        shutil.copy2(stills[-1], still)
    w, h, duration = probe(video)
    return ClipRecord(video=str(CLIPS_DIR / video.name), still=str(CLIPS_DIR / still.name) if still else None,
                      width=manifest.get("width", w), height=manifest.get("height", h),
                      duration=manifest.get("duration", round(duration, 3)),
                      source=str(clip_dir), revision=str(manifest.get("revision", manifest.get("hash", "unknown"))))


# ----------------------------------------------------------------------- the index
def load_index(deck: Path) -> dict:
    p = deck / CLIPS_DIR / "clips.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_index(deck: Path, index: dict) -> Path:
    p = deck / CLIPS_DIR / "clips.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def index_existing(deck: Path) -> dict:
    """Record the clips already in assets/clips (an .mp4 with or without a .png) without rendering anything."""
    index = load_index(deck)
    for video in sorted((deck / CLIPS_DIR).glob("*.mp4")) if (deck / CLIPS_DIR).exists() else []:
        name = video.stem
        if name in index:
            continue
        w, h, duration = probe(video)
        still = video.with_suffix(".png")
        index[name] = asdict(ClipRecord(video=str(CLIPS_DIR / video.name), still=str(CLIPS_DIR / still.name) if still.exists() else None,
                                        width=w, height=h, duration=round(duration, 3), source="assets/clips (pre-existing)",
                                        revision=file_hash(video)))
    return index


def render_all(deck: Path, only: list[str] | None = None, size: str = "1280x720", crop: bool = False) -> dict:
    index = load_index(deck)
    for script, scene in kit_scenes(deck):
        name = clip_name(script, scene, deck)
        short = script.stem[len("clip_"):]
        if only and not ({name, short, short.replace("_", "-"), scene} & set(only)):
            continue
        rec = render_kit_scene(deck, script, scene, size=size, crop=crop)
        index[Path(rec.video).stem] = asdict(rec)
        print(f"lecturekit: clip {Path(rec.video).stem}: {rec.width}x{rec.height}, {rec.duration}s -> {rec.video}", file=sys.stderr)
    try:
        from .project import find_project
        root = find_project(deck)
    except FileNotFoundError:
        root = deck
    for clip_dir in manim8_projects(root):
        if only and clip_dir.name not in only:
            continue
        rec = render_manim8(deck, clip_dir)
        index[clip_dir.name] = asdict(rec)
        print(f"lecturekit: manim8 clip {clip_dir.name}: {rec.width}x{rec.height}, {rec.duration}s", file=sys.stderr)
    save_index(deck, index)
    return index
