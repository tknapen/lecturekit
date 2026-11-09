"""`lk new`: a project from the templates in this directory.

A project is content plus the code that simulates what it shows; the engine
is vendored (the Quarto extension, by Quarto's convention) and installed (the
Python package), never copied in. The scaffold writes the files the method
prescribes so that the first review round starts from the right shape.
"""

from __future__ import annotations

import datetime as _dt
import shutil
from pathlib import Path

from ..project import extension_version, vendor_extension

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def create_project(dest: Path, title: str = "Untitled lecture", force: bool = False, budget: int = 45) -> Path:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    if int(budget) <= 0:
        raise ValueError(f"a budget is a positive number of minutes, not {budget}")
    subs = {
        "TITLE": title,
        "SHORT": _short(title),
        "DATE": _dt.date.today().isoformat(),
        "VERSION": extension_version(),
        "BUDGET": str(int(budget)),
    }
    for src in sorted(TEMPLATE_DIR.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(TEMPLATE_DIR)
        name = rel.with_suffix("") if rel.suffix == ".tmpl" else rel
        out = dest / name
        if out.exists() and not force:
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        if rel.suffix == ".tmpl":
            text = src.read_text(encoding="utf-8")
            for k, v in subs.items():
                text = text.replace("{{" + k + "}}", v)
            out.write_text(text, encoding="utf-8")
        else:
            shutil.copy2(src, out)
    for d in ("assets/figures", "assets/clips", "assets/data", "anim", "references", "sims"):
        (dest / d).mkdir(parents=True, exist_ok=True)
        keep = dest / d / ".gitkeep"
        if not any((dest / d).iterdir()):
            keep.touch()
    vendor_extension(dest, force=force)
    return dest


def _short(title: str) -> str:
    words = [w for w in title.split() if w.isalnum()]
    return " ".join(words[:3]).lower() or "deck"


STARTER = "first_clip"
STARTER_OUTPUT = {"width_px": 1280, "height_px": 720, "fps": 30}


def create_manim8_workspace(dest: Path, family: str | None = None, version: str = "0.1.0") -> list[str]:
    """Make the project's `clips/` a manim8 workspace: `scianim workspace init clips`, the bridged styles of the
    project's presets (`lk theme --manim8`), a family that defaults to the paper style, and a starter project at
    1280 by 720 and 30 fps in that style, waiting for its storyboard. Returns what was done, as lines to print.
    Raises RuntimeError when manim8 is not installed or a step fails."""
    from ..clips import ClipError, run_tool, scianim_exe, tool_env
    from ..theme import load_brand, manim8_presets, select_manim8_style, slug, style_name, write_manim8_styles
    dest = Path(dest)
    try:
        exe = scianim_exe()
    except ClipError as exc:
        raise RuntimeError(f"{exc}. The project is made without clips/; run `lk new --manim8 {dest}` again once "
                           "manim8 is installed") from None
    ws = dest / "clips"
    lines: list[str] = []

    env = tool_env(dest)

    def step(cmd: list[str], what: str) -> None:
        rc, _, reason = run_tool([exe, *cmd], env=env)
        if rc:
            raise RuntimeError(f"`scianim {' '.join(cmd[:2])}` failed: {reason}")
        lines.append(what)

    if not (ws / "workspace.yaml").exists():
        step(["workspace", "init", str(ws)], f"manim8 workspace in {ws}")
    for path in write_manim8_styles(dest, version, select=False):
        lines.append(f"bridged style {path.relative_to(dest)}")
    light, mode = manim8_presets(dest)[0]
    paper = style_name(load_brand(light, mode=mode), mode)
    fam = family or slug(dest.resolve().name, prefix="f") or "lecture"
    fam_dir = ws / "families" / fam
    if not (fam_dir / "family.yaml").exists():
        step(["family", "init", fam, "--workspace", str(ws), "--style", f"{paper}@{version}"],
             f"family {fam} in {fam_dir.relative_to(dest)}")
    starter = fam_dir / STARTER
    if not (starter / "animation.yaml").exists():
        step(["project", "init", STARTER, "--family", fam, "--workspace", str(ws), "--title", "First clip"],
             f"starter project {starter.relative_to(dest)} at 1280x720, 30 fps, in {paper}@{version}")
        _set_output(starter / "animation.yaml", STARTER_OUTPUT)
    select_manim8_style(dest, paper, version)
    lines += [
        f"next: scianim family env sync {fam_dir.relative_to(dest)}   (Manim and the bridge, once, with uv)",
        "      scianim skill install   (the manim8 skill, for the agent that turns a brief into the storyboard)",
        f"      the brief fills {starter.relative_to(dest)}; then lk clips and a ::: {{.movie clip=\"{STARTER}\"}}",
    ]
    return lines


def _set_output(path: Path, values: dict[str, int]) -> None:
    """Set keys of the `output:` block of a fresh animation.yaml, keeping the rest of the file as written."""
    import re
    text = path.read_text(encoding="utf-8")
    m = re.search(r"(?m)^output:[ \t]*\n((?:[ \t]+.*(?:\n|$))*)", text)
    if not m:
        raise RuntimeError(f"{path} has no output block")
    block = m.group(1)
    for key, value in values.items():
        block, n = re.subn(rf"(?m)^([ \t]+{key}:)[ \t]*.*$", lambda g: f"{g.group(1)} {value}", block, count=1)
        if not n:
            block += f"  {key}: {value}\n"
    path.write_text(text[:m.start(1)] + block + text[m.end(1):], encoding="utf-8")
