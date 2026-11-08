"""Where things are: the engine's extension, a project, its decks."""

from __future__ import annotations

import shutil
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
    """Copy the extension into `project/_extensions/lecturekit` (Quarto's convention)."""
    dest = project / "_extensions" / "lecturekit"
    if dest.exists() or dest.is_symlink():
        if not force:
            return dest
        if dest.is_symlink():
            dest.unlink()
        else:
            shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(extension_source(), dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return dest


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
