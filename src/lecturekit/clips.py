"""`lk clips`: render a deck's clips and write `assets/clips/clips.json`.

The seam between the deck and whatever made the clip. A deck's movie block names a clip:

    ::: {.movie clip="bar-bold" height=4cm}

and `assets/clips/clips.json` says what that name means (paths relative to the deck folder; a value that is
not known is left out, never written as null):

    {"bar-bold": {"video": "assets/clips/bar-bold.mp4", "still": "assets/clips/bar-bold.png",
                  "width": 1280, "height": 720, "fps": 30.0, "duration": 20.0,
                  "source": "anim/clip_bar_bold.py:BarBold", "revision": "<sha1 of the script>",
                  "producer": "kit"}}

Two producers fill it:

* kit scenes: `anim/clip_<name>.py`, one or more Manim `Scene` classes on the shared kit (`from kit import *`).
  Rendered with Manim at 1280 by 720 on the slide colour (`--size 1920x1080` or the environment variable
  NM_CLIP_SIZE for another size; the kit reads it), 30 fps, without a title. The video is copied to
  `assets/clips/<name>.mp4`; its last frame becomes the still `<name>.png` unless the scene class sets
  `still = <seconds>`.
* manim8 projects: `clips/families/<family>/.../<name>/`, rendered with `scianim render --profile final --json`.
  `lk clips` builds the family environment when it is missing (`scianim family env sync`) and generates the
  scene module of the working copy (`scianim codegen`) first. The manifest printed on stdout names the full
  movie (`result.videos[0]`), its size, frame rate and duration, the job and its cache key, the revision and
  every checkpoint PNG; all of them are copied into `assets/clips/`, and the still is the latest checkpoint
  unless `--still <clip>=<snapshot_id>` names another. The record adds `job` and `checkpoints`.

`--crop` trims the video and the stills of either producer to the content's bounding box against the slide
colour, and the record carries the resulting shape, which the deck uses as the clip's aspect. `--mode dark`
(or LECTUREKIT_MODE=dark) renders the dark preset into `assets/clips/dark/` with its own `clips.json`: kit
scenes read the dark brand, manim8 projects render under the brand's bridged dark style (`lk theme --manim8`).

Names: `-` and `_` are equivalent wherever a clip is looked up, so `--only bar_bold` and `--only bar-bold` name
the same clip; two clips whose names differ only in that way are an error.

A failing clip is reported with its producer and a one-line reason, the index is saved after every clip, and
the run goes on; `lk clips` exits non-zero at the end when a clip failed. A re-rendered clip that looks
unchanged on screen is a browser cache at work: browsers cache clips by file name.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from collections import deque
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


def union_box(boxes: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int] | None:
    """The box around several content boxes (x, y, w, h), even-sized."""
    if not boxes:
        return None
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[0] + b[2] for b in boxes)
    y1 = max(b[1] + b[3] for b in boxes)
    return x0, y0, (x1 - x0) // 2 * 2, (y1 - y0) // 2 * 2


def extract_frame(video: Path, at: float, out: Path) -> None:
    exe = _ffmpeg()
    if not exe:
        raise ClipError("ffmpeg not found (pip install imageio-ffmpeg, or install ffmpeg)")
    subprocess.run([exe, "-y", "-loglevel", "error", "-ss", f"{max(at, 0):.3f}", "-i", str(video),
                    "-frames:v", "1", str(out)], check=True)


def crop_video(src: Path, dst: Path, box: tuple[int, int, int, int]) -> None:
    exe = _ffmpeg()
    if not exe:
        raise ClipError("ffmpeg not found (pip install imageio-ffmpeg, or install ffmpeg)")
    x, y, w, h = box
    tmp = dst.with_name(f"_{dst.name}")
    subprocess.run([exe, "-y", "-loglevel", "error", "-i", str(src), "-vf", f"crop={w}:{h}:{x}:{y}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart",
                    "-an", str(tmp)], check=True)
    tmp.replace(dst)


def crop_image(src: Path, dst: Path, box: tuple[int, int, int, int]) -> None:
    from PIL import Image
    x, y, w, h = box
    with Image.open(src) as im:
        im.crop((x, y, x + w, y + h)).save(dst)


def file_hash(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()[:12]


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
                     background: str | None = None, mode: str | None = None, still: float | None = None,
                     out_dir: Path | None = None) -> ClipRecord:
    """Render one Manim scene on the kit, copy it into the preset's clips folder, write the still, return the
    record."""
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
    cmd = [exe, "--disable_caching", "--progress_bar", "none", "-r", f"{w0},{h0}",
           "--media_dir", str(media), "-o", name, str(Path(script).resolve()), scene]
    rc, _, reason = run_tool(cmd, cwd=anim, env=env)
    if rc:
        raise ClipError(f"manim exited {rc}: {reason}" if reason else f"manim exited {rc}")
    produced = sorted(media.rglob(f"{name}.mp4"), key=lambda p: p.stat().st_mtime)
    if not produced:
        raise ClipError(f"Manim produced no video for {scene}")
    raw = produced[-1]
    rel_dir = clips_dir(m)
    out = out_dir or (deck / rel_dir)
    out.mkdir(parents=True, exist_ok=True)
    info = probe_video(raw)
    duration = info["duration"]
    still_at = still if still is not None else _scene_attr(script, scene, "still")
    at = duration - 0.05 if still_at in (None, "last") else float(still_at)
    tmp_frame = out / f"_{name}_frame.png"
    extract_frame(raw, at, tmp_frame)
    video = out / f"{name}.mp4"
    still_png = out / f"{name}.png"
    w, h = info["width"], info["height"]
    box = content_box(tmp_frame, background or _slide_color(deck, m)) if crop else None
    if box:
        crop_video(raw, video, box)
        crop_image(tmp_frame, still_png, box)
        w, h = box[2], box[3]
    else:
        shutil.copy2(raw, video)
        shutil.copy2(tmp_frame, still_png)
    tmp_frame.unlink(missing_ok=True)
    return ClipRecord(video=(rel_dir / video.name).as_posix(), still=(rel_dir / still_png.name).as_posix(),
                      width=w, height=h, fps=info["fps"], duration=round(duration, 3),
                      source=f"{_rel(script, deck)}:{scene}", revision=file_hash(script), producer="kit")


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
    else:
        manifest = _manifest_by_prefix(clip_dir, printed)
    return manim8_record(deck, clip_dir, manifest, still=still, crop=crop, size=size, mode=m,
                         background=background, out_dir=out_dir)


def manim8_record(deck: Path, clip_dir: Path, manifest: dict, still: str | float | None = None, crop: bool = False,
                  size: str | None = None, mode: str | None = None, background: str | None = None,
                  out_dir: Path | None = None) -> ClipRecord:
    """Copy what a manim8 render manifest names into the preset's clips folder and return the record."""
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
    rel_dir = clips_dir(m)
    out = out_dir or (deck / rel_dir)
    out.mkdir(parents=True, exist_ok=True)
    checkpoints = []
    for c in result.get("checkpoints") or []:
        png = clip_dir / c.get("png", "")
        if not c.get("snapshot_id") or not png.is_file():
            print(f"lecturekit: clip {name}: checkpoint {c.get('snapshot_id')} has no PNG at {png}", file=sys.stderr)
            continue
        t = c.get("renderer_time_seconds", c.get("expected_time_seconds"))
        checkpoints.append((str(c["snapshot_id"]), png, float(t) if t is not None else -1.0))
    width, height = int(v0["width_px"]), int(v0["height_px"])
    if size and tuple(int(v) for v in size.lower().split("x")) != (width, height):
        fps = f" at {float(v0['fps']):g} fps" if v0.get("fps") is not None else ""
        print(f"lecturekit: warning: clip {name} is {width}x{height}{fps}, as its manim8 project's output says; "
              f"--size {size} applies to kit clips only (set output in animation.yaml)", file=sys.stderr)
    box = None
    if crop:
        bg = background or _slide_color(deck, m)
        frames = [p for _, p, _ in checkpoints]
        if not frames:
            frames = [out / f"_{name}_frame.png"]
            extract_frame(movie, max(float(v0.get("duration_seconds", 0)) - 0.05, 0), frames[0])
        box = union_box([b for b in (content_box(f, bg) for f in frames) if b])
        if frames and frames[0].name.startswith("_"):
            frames[0].unlink(missing_ok=True)
    video = out / f"{name}.mp4"
    if box:
        crop_video(movie, video, box)
        width, height = box[2], box[3]
    else:
        shutil.copy2(movie, video)
    copied: dict[str, str] = {}
    for sid, png, _ in checkpoints:
        dst = out / f"{name}.{sid}.png"
        if box:
            crop_image(png, dst, box)
        else:
            shutil.copy2(png, dst)
        copied[sid] = (rel_dir / dst.name).as_posix()
    stale = re.compile(rf"^{re.escape(name)}\.([a-z][a-z0-9_]*)\.png$")
    for old in out.glob(f"{name}.*.png"):
        hit = stale.match(old.name)
        if hit and hit.group(1) not in copied:
            old.unlink()
    still_path = _manim8_still(name, still, checkpoints, copied, movie, out, rel_dir, box, v0)
    resolved = job.get("resolved_style") or {}
    job_rec = {"id": job.get("job_id"), "cache_key": job.get("cache_key"),
               "registry_version": job.get("registry_version"),
               "style": f"{resolved['theme']}@{resolved['theme_version']}"
               if resolved.get("theme") and resolved.get("theme_version") else None}
    return ClipRecord(video=(rel_dir / video.name).as_posix(), still=still_path, width=width, height=height,
                      fps=float(v0["fps"]) if v0.get("fps") is not None else None,
                      duration=round(float(v0["duration_seconds"]), 3) if v0.get("duration_seconds") is not None
                      else None,
                      source=_rel(clip_dir, deck), revision=job.get("revision_id"), producer="manim8",
                      job={k: v for k, v in job_rec.items() if v is not None},
                      checkpoints=copied or None)


def _manim8_still(name, still, checkpoints, copied, movie, out, rel_dir, box, v0) -> str:
    """The still of a manim8 clip: the named checkpoint, a second of the movie, or the latest checkpoint."""
    seconds = None
    if still is not None:
        sid = str(still)
        if sid in copied:
            return copied[sid]
        try:
            seconds = float(still)
        except (TypeError, ValueError):
            raise ClipError(f"--still {name}={sid}: the job has no checkpoint {sid!r} "
                            f"(it has {', '.join(copied) or 'none'})") from None
    if seconds is None and checkpoints:
        latest = max(checkpoints, key=lambda c: c[2])
        return copied[latest[0]]
    at = seconds if seconds is not None else max(float(v0.get("duration_seconds", 0)) - 0.05, 0)
    png = out / f"{name}.png"
    frame = out / f"_{name}_frame.png"
    extract_frame(movie, at, frame)
    if box:
        crop_image(frame, png, box)
        frame.unlink(missing_ok=True)
    else:
        frame.replace(png)
    return (rel_dir / png.name).as_posix()


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
    """Record the clips already in the preset's clips folder (an .mp4 with or without a .png) without rendering
    anything."""
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
                still = still_for.get(key)
                if still is not None:
                    try:
                        still = float(still)
                    except ValueError:
                        raise ClipError(f"--still {clip.name}={still}: a kit clip's still is a second of the "
                                        "clip (or `still = <seconds>` on the scene class)") from None
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
        print(f"lecturekit: {clip.producer} clip {clip.name}: {rec.width}x{rec.height}, {rec.duration}s -> "
              f"{rec.video}", file=sys.stderr)
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
