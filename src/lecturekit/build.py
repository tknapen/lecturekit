"""`lk build`: render a project with Quarto and report the plan against the budget."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .project import extension_version, find_project, vendored_version

FORMATS = {"live": "lecturekit-revealjs", "study": "lecturekit-beamer"}


def quarto_exe() -> str:
    exe = shutil.which("quarto")
    if not exe:
        sys.exit("quarto not found on PATH; see docs/INSTALL.md")
    return exe


def check_versions(project: Path) -> None:
    """Refuse a project whose vendored extension has another major version than the engine.

    A project pins the extension it builds with by committing it; the Python
    package and the extension share a version. A major mismatch means the
    dialect or the macros may differ, and the deck would build subtly wrong.
    """
    v_project = vendored_version(project)
    v_engine = extension_version()
    if v_project is None:
        print(f"lecturekit: no vendored extension in {project}; run `lk new --vendor-only {project}`", file=sys.stderr)
        return
    if v_project.split(".")[0] != v_engine.split(".")[0]:
        sys.exit(f"lecturekit: project extension {v_project} and engine {v_engine} differ in major version; "
                 f"upgrade the project with `lk new --vendor-only --force {project}` or install the matching engine")
    if v_project != v_engine:
        print(f"lecturekit: project extension {v_project}, engine {v_engine} (compatible)", file=sys.stderr)


def build(project: Path | None = None, to: str | None = None, profile: str | None = None,
          targets: list[str] | None = None, quiet: bool = False, extra: list[str] | None = None) -> int:
    proj = find_project(project)
    check_versions(proj)
    cmd = [quarto_exe(), "render"]
    cmd += targets or []
    if to:
        cmd += ["--to", FORMATS.get(to, to)]
    if profile:
        cmd += ["--profile", profile]
    if quiet:
        cmd += ["--quiet"]
    cmd += extra or []
    env = dict(os.environ)
    print("lecturekit: " + " ".join(cmd), file=sys.stderr)
    proc = subprocess.run(cmd, cwd=proj, env=env, text=True, capture_output=True)
    # the timing report is on stderr between quarto's own output; show it last
    report = _extract_timing(proc.stderr)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(_strip_timing(proc.stderr))
    if report:
        print(report)
    timing = proj / "_build" / "timing.txt"
    if proc.returncode == 0 and timing.exists():
        print(f"(per slide in {timing})")
    return proc.returncode


_TIMING_RE = re.compile(r"(lecturekit timing \((?:live|study)\):\n(?:(?!lecturekit timing)[^\n]*\n)*?slides \d+[^\n]*\n?)")


def _extract_timing(stderr: str) -> str:
    return "\n".join(m.strip("\n") for m in _TIMING_RE.findall(stderr))


def _strip_timing(stderr: str) -> str:
    return _TIMING_RE.sub("", stderr)
