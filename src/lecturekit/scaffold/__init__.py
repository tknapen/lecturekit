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


def create_project(dest: Path, title: str = "Untitled lecture", force: bool = False) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    subs = {
        "TITLE": title,
        "SHORT": _short(title),
        "DATE": _dt.date.today().isoformat(),
        "VERSION": extension_version(),
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
