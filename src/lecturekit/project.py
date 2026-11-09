"""Where things are: the engine's extension, a project, its decks."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import yaml

PACKAGE_DIR = Path(__file__).resolve().parent


def extension_source() -> Path:
    """The Quarto extension shipped with this install.

    In a wheel it sits inside the package (`lecturekit/_extension`); in an
    editable install it is the repository's `_extensions/lecturekit`.
    """
    bundled = PACKAGE_DIR / "_extension"
    if (bundled / "_extension.yml").exists():
        return bundled
    repo = PACKAGE_DIR.parents[1] / "_extensions" / "lecturekit"
    if (repo / "_extension.yml").exists():
        return repo
    raise FileNotFoundError("lecturekit's Quarto extension was not found next to the package")


def extension_version() -> str:
    data = yaml.safe_load((extension_source() / "_extension.yml").read_text(encoding="utf-8")) or {}
    return str(data.get("version", "0"))


def find_project(start: Path | None = None) -> Path:
    """The nearest directory with a `_quarto.yml`, from `start` upwards."""
    here = (start or Path.cwd()).resolve()
    for d in [here, *here.parents]:
        if (d / "_quarto.yml").exists():
            return d
    raise FileNotFoundError(f"no _quarto.yml found above {here}")


def vendor_extension(project: Path, force: bool = False) -> Path:
    """Copy the extension into `project/_extensions/lecturekit` (Quarto's convention).

    An existing copy is kept unless `force`. Symlinks are handled so that a shared copy is never overwritten:
    a dangling `_extensions` (or `_extensions/lecturekit`) link, as a project copied out of the expo has, is
    removed and replaced by a real directory; an `_extensions` that links to a directory other projects share
    becomes a real directory of this project before anything is written into it (the other extensions it held
    are copied along), and the shared copy is left as it was.
    """
    project = Path(project)
    parent = project / "_extensions"
    dest = parent / "lecturekit"
    source = extension_source()
    if parent.is_symlink() and not parent.exists():
        target = os.readlink(parent)
        parent.unlink()
        _note(f"{parent} was a dangling link (to {target}); replaced by a real directory")
    if dest.is_symlink() and not dest.exists():
        if not parent.is_symlink():
            target = os.readlink(dest)
            dest.unlink()
            _note(f"{dest} was a dangling link (to {target}); replaced by a copy")
    if dest.exists() and not force:
        return dest
    if parent.is_symlink():
        shared = parent.resolve()
        parent.unlink()
        parent.mkdir()
        for entry in sorted(shared.iterdir()):
            if entry.name == "lecturekit":
                continue
            if entry.is_dir():
                shutil.copytree(entry, parent / entry.name, symlinks=True)
            else:
                shutil.copy2(entry, parent / entry.name)
        _note(f"{parent} linked to {shared}, which other projects may share; it is now a real directory of "
              f"this project with its own copy of the extension, and {shared} is unchanged")
    if dest.is_symlink():
        target = os.readlink(dest)
        dest.unlink()
        _note(f"{dest} linked to {target}; replaced by a copy (the link target is unchanged)")
    elif dest.exists():
        shutil.rmtree(dest)
    parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return dest


def _note(message: str) -> None:
    print(f"lecturekit: {message}", file=sys.stderr)


def vendored_version(project: Path) -> str | None:
    p = project / "_extensions" / "lecturekit" / "_extension.yml"
    if not p.exists():
        return None
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return str(data.get("version", "0"))


def project_config(project: Path) -> dict:
    p = project / "_quarto.yml"
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {} if p.exists() else {}


def deck_dirs(project: Path) -> list[Path]:
    """Directories that hold a `slides.qmd` under the project (the project itself included)."""
    out = []
    for p in sorted(project.rglob("slides.qmd")):
        if any(part.startswith(("_", ".")) for part in p.relative_to(project).parts):
            continue
        out.append(p.parent)
    return out
