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


def compatible(v_project: str, v_engine: str) -> bool:
    """Whether a project's extension builds with this engine: the same major version, and while the major is 0 the
    same minor too (a 0.x release may change the dialect, the filters or the clip index)."""
    p, e = v_project.split("."), v_engine.split(".")
    if p[0] != e[0]:
        return False
    if p[0] == "0" and p[1:2] != e[1:2]:
        return False
    return True


def check_versions(project: Path) -> None:
    """Refuse a project whose vendored extension is not compatible with the engine.

    A project pins the extension it builds with by committing it; the Python package and the extension share a
    version. A mismatch in the major version (in the minor too while the major is 0) means the dialect or the
    macros may differ, and the deck would build subtly wrong.
    """
    v_project = vendored_version(project)
    v_engine = extension_version()
    if v_project is None:
        print(f"lecturekit: no vendored extension in {project}; run `lk new --vendor-only {project}`", file=sys.stderr)
        return
    if not compatible(v_project, v_engine):
        which = "major" if v_project.split(".")[0] != v_engine.split(".")[0] else "minor"
        sys.exit(f"lecturekit: project extension {v_project} and engine {v_engine} differ in {which} version; "
                 f"upgrade the project with `lk new --vendor-only --force {project}` or install the matching engine")
    if v_project != v_engine:
        print(f"lecturekit: project extension {v_project}, engine {v_engine} (compatible)", file=sys.stderr)


def build_env() -> dict[str, str]:
    """The render's environment: QUARTO_PYTHON is this interpreter unless set, so the pre-render (make_assets.py)
    and the figure conversion import lecturekit and pymupdf without an activated venv."""
    env = dict(os.environ)
    env.setdefault("QUARTO_PYTHON", sys.executable)
    return env


def build(project: Path | None = None, to: str | None = None, profile: str | None = None,
          targets: list[str] | None = None, quiet: bool = False, extra: list[str] | None = None,
          strict: bool = False) -> int:
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
    print("lecturekit: " + " ".join(cmd), file=sys.stderr)
    proc = subprocess.run(cmd, cwd=proj, env=build_env(), text=True, capture_output=True)
    # the timing report is on stderr between quarto's own output; show it last
    report = _extract_timing(proc.stderr)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(_strip_timing(proc.stderr))
    errors = filter_errors(proc.stdout + "\n" + proc.stderr)
    if errors:
        print(f"lecturekit: the build failed: the lecturekit filters reported {len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return proc.returncode or 1
    warnings = filter_warnings(proc.stdout + "\n" + proc.stderr)
    if warnings:
        print(f"lecturekit: {len(warnings)} warning(s) from the lecturekit filters:", file=sys.stderr)
        for w in warnings:
            print(f"  {w}", file=sys.stderr)
        if strict:
            print("lecturekit: the build failed: --strict treats warnings as errors", file=sys.stderr)
            return proc.returncode or 1
    if proc.returncode == 0:
        theme_font_urls(output_dir(proj, profile))
    if report:
        print(report)
    timing = output_dir(proj, profile) / "timing.txt"
    if proc.returncode == 0 and timing.exists():
        print(f"(per slide in {timing})")
    return proc.returncode


def output_dir(proj: Path, profile: str | None = None) -> Path:
    """The folder a render writes to: `project: output-dir:` of the profile's `_quarto-<profile>.yml`, else of
    `_quarto.yml`, else `_build`."""
    import yaml
    for name in ([f"_quarto-{profile}.yml"] if profile else []) + ["_quarto.yml"]:
        try:
            config = yaml.safe_load((proj / name).read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        out = (config.get("project") or {}).get("output-dir") if isinstance(config, dict) else None
        if out:
            return proj / out
    return proj / "_build"


_CSS_URL_RE = re.compile(r'url\("([^":)]+)"\)')


def theme_font_urls(out: Path) -> int:
    """Point the compiled Reveal theme's font URLs at the fonts. Quarto writes the brand's `source: file` fonts into
    the theme CSS with their paths from the project (`_extensions/lecturekit/fonts/...`), which a browser resolves
    from the CSS, four folders below the deck: the live view never asks for them (the deck's own rules come later),
    but the print view does, and logs a 404 for each. A path that is missing beside the CSS and present in the output
    is rewritten relative to the CSS. Returns the number of URLs rewritten."""
    n = 0
    for css in out.glob("**/libs/revealjs/dist/theme/*.css"):
        text = css.read_text(encoding="utf-8")

        def fix(m: re.Match) -> str:
            nonlocal n
            rel = m.group(1)
            if rel.startswith(("/", "../", "data")) or (css.parent / rel).exists():
                return m.group(0)
            for base in (css.parent, *css.parent.parents):
                if (base / rel).exists() and base.is_relative_to(out):
                    n += 1
                    return f'url("{os.path.relpath(base / rel, css.parent).replace(os.sep, "/")}")'
            return m.group(0)

        new = _CSS_URL_RE.sub(fix, text)
        if new != text:
            css.write_text(new, encoding="utf-8")
    return n


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
# An ERROR line from a lecturekit filter: the filters' own `ERROR (lecturekit) ...`, or Quarto's logger
# `ERROR (<path>/lecturekit/filters/<file>.lua:<line>) ...`, which a filter that calls error() produces and which
# does not stop the render by itself.
_FILTER_ERROR_RE = re.compile(r"ERROR \(([^)\n]*lecturekit[^)\n]*)\) ?(.*)")


_FILTER_WARNING_RE = re.compile(r"WARNING \(lecturekit\) ?(.*)")


def filter_warnings(output: str) -> list[str]:
    """The distinct warnings the lecturekit filters wrote during a render, in order."""
    seen: list[str] = []
    for line in _ANSI_RE.sub("", output).splitlines():
        m = _FILTER_WARNING_RE.search(line)
        if m and m.group(1).strip() not in seen:
            seen.append(m.group(1).strip())
    return seen


def filter_errors(output: str) -> list[str]:
    """The distinct error messages the lecturekit filters wrote during a render, in order."""
    seen: list[str] = []
    for line in _ANSI_RE.sub("", output).splitlines():
        m = _FILTER_ERROR_RE.search(line)
        if m:
            source = m.group(1)
            where = "" if source == "lecturekit" else f" ({Path(source.rsplit(':', 1)[0]).name})"
            msg = m.group(2).strip() + where
            if msg not in seen:
                seen.append(msg)
    return seen


_TIMING_RE = re.compile(r"(lecturekit timing \((?:live|study)\):\n(?:(?!lecturekit timing)[^\n]*\n)*?slides \d+[^\n]*\n?)")


def _extract_timing(stderr: str) -> str:
    return "\n".join(m.strip("\n") for m in _TIMING_RE.findall(stderr))


def _strip_timing(stderr: str) -> str:
    return _TIMING_RE.sub("", stderr)
