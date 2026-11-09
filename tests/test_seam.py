"""The seam between a deck and its clip producers: `lk clips` against manim8's real render layout (a fake
`scianim` that writes it from a recorded manifest), clip names, the dark preset, the bridged styles, the
vendored extension and the scaffold. The quarto build at the end needs quarto; the rest needs ffmpeg for
the videos the fake writes, and `scianim_core` (manim8-core) for the style and proposal validation, each
skipped when absent.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from lecturekit import __version__, clips
from lecturekit.cli import main as lk
from lecturekit.project import extension_source, extension_version, vendor_extension

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "manim8"
FAKE = FIXTURES / "fake_scianim.py"
TEMPLATES = ROOT / "src" / "lecturekit" / "scaffold" / "templates"
KICKOFF = ROOT / "examples" / "kickoff"
FAKE_ENV = ("FAKE_SCIANIM_OLD", "FAKE_SCIANIM_FAIL", "FAKE_SCIANIM_SCHEMA", "FAKE_SCIANIM_PROPOSALS")
SLUG = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

needs_ffmpeg = pytest.mark.skipif(clips._ffmpeg() is None, reason="ffmpeg not installed")
needs_quarto = pytest.mark.skipif(shutil.which("quarto") is None, reason="quarto not installed")


# ---------------------------------------------------------------- fixtures
@pytest.fixture
def scianim(tmp_path, monkeypatch):
    """A fake `scianim` first on PATH, its calls logged."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    exe = bindir / "scianim"
    exe.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE}" "$@"\n')
    exe.chmod(0o755)
    log = tmp_path / "scianim.log"
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("FAKE_SCIANIM_LOG", str(log))
    for k in (*FAKE_ENV, "LECTUREKIT_MODE", "LECTUREKIT_BRAND"):
        monkeypatch.delenv(k, raising=False)
    clips._CAPS.clear()

    def calls(cmd: str | None = None) -> list[list[str]]:
        rows = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        return [r for r in rows if cmd is None or r[:1] == [cmd]]

    return SimpleNamespace(bin=bindir, exe=exe, log=log, calls=calls)


@pytest.fixture
def no_manim8(tmp_path, monkeypatch):
    """No `scianim` anywhere lecturekit looks: not on PATH, and not beside this Python, where a venv that has the
    manim8 extra keeps it."""
    empty = tmp_path / "nothing"
    empty.mkdir(exist_ok=True)
    monkeypatch.setenv("PATH", str(empty))
    monkeypatch.setattr(sys, "executable", str(empty / "python"))
    return empty


def make_deck(root: Path, projects=("divisive_normalization",), style=("tomas_scientific", "0.5.1"),
              storyboard: bool = True) -> Path:
    """A deck with the scaffold's presets and a manim8 workspace in clips/ with one family."""
    deck = root / "deck"
    deck.mkdir()
    (deck / "_quarto.yml").write_text("project:\n  type: default\n")
    for name in ("_brand.yml", "_brand-dark.yml", "_quarto-dark.yml"):
        shutil.copy(TEMPLATES / name, deck / name)
    fam = deck / "clips" / "families" / "neuro"
    fam.mkdir(parents=True)
    (deck / "clips" / "workspace.yaml").write_text('schema_version: "1.0"\nid: clips\n')
    (fam / "family.yaml").write_text(f'schema_version: "1.0"\nid: neuro\n# the default style of new projects\n'
                                     f'style:\n  name: {style[0]}\n  version: "{style[1]}"\n')
    for name in projects:
        add_project(deck, name, style, storyboard)
    return deck


def add_project(deck: Path, name: str, style=("tomas_scientific", "0.5.1"), storyboard: bool = True) -> Path:
    d = deck / "clips" / "families" / "neuro" / name
    d.mkdir()
    (d / "animation.yaml").write_text(
        f'schema_version: "1.0"\nid: {name}\noutput:\n  width_px: 1920\n  height_px: 1080\n  fps: 30\n'
        f'# chosen by the lecturer\nstyle:\n  name: {style[0]}\n  version: "{style[1]}"\n  overrides: {{}}\n')
    if storyboard:
        (d / "storyboard.yaml").write_text(f'schema_version: "1.0"\nproject_id: {name}\nscenes: []\n')
    return d


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jobs(project: Path) -> list[Path]:
    return sorted(p for p in (project / "renders").glob("*/job_*") if p.is_dir())


def no_nulls(obj) -> bool:
    if isinstance(obj, dict):
        return all(v is not None and no_nulls(v) for v in obj.values())
    if isinstance(obj, list):
        return all(v is not None and no_nulls(v) for v in obj)
    return True


# ---------------------------------------------------------------- versions
def test_versions_and_the_manim8_extra():
    meta = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert meta["version"] == __version__ == extension_version() == "0.3.0"
    extra = meta["optional-dependencies"]["manim8"]
    assert any(d.startswith("manim8 @ git+https://github.com/tknapen/manim8@v0.1.0a0") for d in extra)
    assert any("#subdirectory=packages/scianim_core" in d and d.startswith("manim8-core @") for d in extra)
    assert all("python_version >= '3.12'" in d for d in extra)


def test_docs_point_at_the_installed_version(monkeypatch, tmp_path, capsys):
    from lecturekit import cli
    monkeypatch.setattr(cli, "PACKAGE_DIR", tmp_path / "site" / "lecturekit")
    assert lk(["docs"]) == 0
    assert capsys.readouterr().out.strip() == f"https://github.com/tknapen/lecturekit/tree/v{__version__}/docs"


# ---------------------------------------------------------------- manim8 through lk clips
@needs_ffmpeg
def test_manim8_clip_is_the_full_movie_with_its_checkpoints(scianim, tmp_path):
    deck = make_deck(tmp_path)
    project = deck / "clips" / "families" / "neuro" / "divisive_normalization"
    index, failures = clips.run_clips(deck)
    assert failures == []
    # sync (no .venv yet) and codegen run before the render, which asks for the manifest on stdout
    order = [c[0] if c[0] != "family" else "sync" for c in scianim.calls() if c[:2] != ["render", "--help"]]
    assert order == ["sync", "codegen", "render"]
    render = scianim.calls("render")[-1]
    assert "--json" in render and render[render.index("--profile") + 1] == "final"
    rec = index["divisive_normalization"]
    (job,) = jobs(project)
    manifest = json.loads((job / "manifest.json").read_text())
    movie = job / f"{job.name}.mp4"
    copied = deck / rec["video"]
    assert rec["video"] == "assets/clips/divisive_normalization.mp4"
    assert sha(copied) == sha(movie) == manifest["result"]["videos"][0]["sha256"]       # the movie ...
    assert all(sha(copied) != sha(s) for s in (job / "sections").glob("*.mp4"))         # ... never a section
    assert max((job / "sections").glob("*.mp4"), key=lambda p: p.stat().st_mtime).stat().st_mtime \
        >= movie.stat().st_mtime                                                         # sections are newer
    assert (rec["width"], rec["height"], rec["fps"], rec["duration"]) == (320, 180, 30.0, 2.0)
    assert rec["producer"] == "manim8" and rec["revision"] == "working"
    assert rec["source"] == "clips/families/neuro/divisive_normalization"                # relative to the deck
    assert rec["job"]["id"] == job.name and rec["job"]["cache_key"].startswith("sha256:")
    assert rec["job"]["registry_version"] == "0.5.0"
    assert set(rec["checkpoints"]) == {"excitation_visible", "pool_introduced", "pool_raised", "rebalanced"}
    for sid, png in rec["checkpoints"].items():
        assert png == f"assets/clips/divisive_normalization.{sid}.png"
        assert sha(deck / png) == sha(job / f"{sid}.png")
    assert rec["still"] == rec["checkpoints"]["rebalanced"]                              # the latest checkpoint
    text = (deck / "assets" / "clips" / "clips.json").read_text()
    assert "null" not in text and no_nulls(json.loads(text))


@needs_ffmpeg
def test_a_second_render_is_a_cache_hit(scianim, tmp_path):
    deck = make_deck(tmp_path)
    project = deck / "clips" / "families" / "neuro" / "divisive_normalization"
    first, _ = clips.run_clips(deck)
    first = json.loads(json.dumps(first))
    second, failures = clips.run_clips(deck)
    assert failures == []
    assert len(jobs(project)) == 1                                       # nothing new was rendered
    assert second["divisive_normalization"] == first["divisive_normalization"]
    assert len(scianim.calls("render")) - 1 == 2                         # two renders (and one --help probe)
    assert len([c for c in scianim.calls("family")]) == 1               # the environment was built once


@needs_ffmpeg
def test_no_cache_renders_again(scianim, tmp_path):
    deck = make_deck(tmp_path)
    project = deck / "clips" / "families" / "neuro" / "divisive_normalization"
    first, _ = clips.run_clips(deck)
    first = json.loads(json.dumps(first))
    second, failures = clips.run_clips(deck, no_cache=True)
    assert failures == []
    assert "--no-cache" in scianim.calls("render")[-1]
    assert len(jobs(project)) == 2                                       # a second job, not the cached one
    assert second["divisive_normalization"]["job"]["id"] != first["divisive_normalization"]["job"]["id"]
    assert second["divisive_normalization"]["job"]["cache_key"] == first["divisive_normalization"]["job"]["cache_key"]


@needs_ffmpeg
def test_named_still_and_an_unknown_one(scianim, tmp_path):
    deck = make_deck(tmp_path)
    index, failures = clips.run_clips(deck, stills=["divisive-normalization=pool_raised"])
    assert failures == []
    assert index["divisive_normalization"]["still"] == "assets/clips/divisive_normalization.pool_raised.png"
    _, failures = clips.run_clips(deck, stills=["divisive_normalization=nowhere"])
    assert len(failures) == 1 and "no checkpoint 'nowhere'" in failures[0].reason
    assert "rebalanced" in failures[0].reason


@needs_ffmpeg
def test_revision_is_passed_and_codegen_skipped(scianim, tmp_path):
    deck = make_deck(tmp_path)
    (deck / "clips" / "families" / "neuro" / ".venv").mkdir()
    index, failures = clips.run_clips(deck, revisions=["rev_0002"])
    assert failures == []
    render = scianim.calls("render")[-1]
    assert render[render.index("--revision") + 1] == "rev_0002"
    assert scianim.calls("codegen") == [] and scianim.calls("family") == []
    assert index["divisive_normalization"]["revision"] == "rev_0002"


@needs_ffmpeg
def test_no_sync_reports_the_missing_environment(scianim, tmp_path):
    deck = make_deck(tmp_path)
    _, failures = clips.run_clips(deck, sync=False)
    assert len(failures) == 1 and "scianim family env sync" in failures[0].reason
    assert scianim.calls("render") == []


@needs_ffmpeg
def test_older_manim8_without_json_finds_the_job_by_cache_key(scianim, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_SCIANIM_OLD", "1")
    deck = make_deck(tmp_path)
    project = deck / "clips" / "families" / "neuro" / "divisive_normalization"
    (project.parent / ".venv").mkdir()
    # a decoy job, newer than anything the render writes, with another cache key and its own movie
    decoy = project / "renders" / "working" / "job_29991231T235959_ffffff"
    decoy.mkdir(parents=True)
    record = json.loads((FIXTURES / "manifest_render.json").read_text())
    record["job"]["cache_key"] = "sha256:" + "0" * 64
    (decoy / "manifest.json").write_text(json.dumps(record))
    (decoy / "job_29991231T235959_ffffff.mp4").write_bytes(b"decoy")
    future = 4_102_444_800                                                # 2100-01-01: newer than any render
    for f in decoy.iterdir():
        os.utime(f, (future, future))
    index, failures = clips.run_clips(deck)
    assert failures == []
    assert "--json" not in scianim.calls("render")[-1]
    (job,) = [j for j in jobs(project) if j != decoy]
    assert sha(deck / index["divisive_normalization"]["video"]) == sha(job / f"{job.name}.mp4")
    index, failures = clips.run_clips(deck)                               # a cache hit: the same job again
    assert failures == [] and index["divisive_normalization"]["job"]["id"] == job.name


@needs_ffmpeg
def test_an_unknown_manifest_schema_is_refused(scianim, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_SCIANIM_SCHEMA", "2.0")
    deck = make_deck(tmp_path)
    index, failures = clips.run_clips(deck)
    assert len(failures) == 1 and "schema_version '2.0'" in failures[0].reason
    assert "divisive_normalization" not in index


@needs_ffmpeg
def test_one_failing_clip_does_not_stop_the_run(scianim, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_SCIANIM_FAIL", "alpha")
    deck = make_deck(tmp_path, projects=("alpha", "beta"))
    (deck / "anim").mkdir()
    (deck / "anim" / "clip_broken.py").write_text(
        "from manim import *\n\n\nclass Broken(Scene):\n    def construct(self):\n        raise RuntimeError('boom')\n")
    index, failures = clips.run_clips(deck)
    by = {f.name: f for f in failures}
    assert set(by) == {"broken", "alpha"}
    assert by["broken"].producer == "kit" and by["alpha"].producer == "manim8"
    assert "kind the registry does not have" in by["alpha"].reason                      # manim8's own message
    assert "\n" not in by["alpha"].reason and "Traceback" not in by["broken"].reason
    saved = json.loads((deck / "assets" / "clips" / "clips.json").read_text())
    assert "beta" in saved and "alpha" not in saved                                      # the run went on
    capsys.readouterr()
    assert lk(["clips", str(deck)]) == 1
    err = capsys.readouterr().err
    assert "alpha (manim8):" in err and "broken (kit):" in err


def test_a_failure_reason_is_the_error_not_a_pointer_to_it():
    printed = ["  error   /x/storyboard.yaml: invalid storyboard specification:\n",
               "  - scenes.1.objects.0.kind: Input should be 'text_caption' or 'custom'\n",
               "  note    project uses style 'a' while family 'b' defaults to 'c'\n",
               "x: invalid (1 errors, 0 warnings)\n", "error: fix the errors above before generating code\n"]
    assert clips._reason(printed) == ("/x/storyboard.yaml: invalid storyboard specification: "
                                      "scenes.1.objects.0.kind: Input should be 'text_caption' or 'custom'")
    assert clips._reason(["first\n", "\x1b[31mthe last\x1b[0m\n", "\n"]) == "the last"


def test_missing_manim_names_the_clips_extra(monkeypatch, tmp_path):
    monkeypatch.setattr(clips, "_manim_exe", lambda: None)
    (tmp_path / "anim").mkdir()
    script = tmp_path / "anim" / "clip_x.py"
    script.write_text("class X(Scene):\n    pass\n")
    with pytest.raises(clips.ClipError, match=r"lecturekit\[clips\]"):
        clips.render_kit_scene(tmp_path, script, "X")


def test_missing_scianim_names_the_manim8_extra(no_manim8):
    with pytest.raises(clips.ClipError) as err:
        clips.scianim_exe()
    message = str(err.value)
    assert "lecturekit[manim8]" in message and "3.12" in message and "uv" in message


# ---------------------------------------------------------------- names
def test_names_are_one_under_dash_and_underscore():
    assert clips.norm_name("bar-bold") == clips.norm_name("bar_bold") == "bar_bold"
    assert clips.clip_name(KICKOFF / "anim" / "clip_bar_bold.py", "BarBold", KICKOFF) == "bar-bold"
    index = {"bar_bold": {"video": "assets/clips/bar_bold.mp4"}, "other": {"video": "o.mp4"}}
    clips.store(index, "bar-bold", clips.ClipRecord(video="assets/clips/bar-bold.mp4"))
    assert set(index) == {"bar-bold", "other"}


@needs_ffmpeg
def test_only_matches_either_spelling_and_reports_a_miss(scianim, tmp_path):
    deck = make_deck(tmp_path, projects=("divisive_normalization", "other_clip"))
    (deck / "anim").mkdir()
    shutil.copy(KICKOFF / "anim" / "clip_bar_bold.py", deck / "anim" / "clip_bar_bold.py")
    index, failures = clips.run_clips(deck, only=["divisive-normalization", "bar_bold", "bar"])
    assert "divisive_normalization" in index and "other_clip" not in index
    names = {f.name for f in failures}
    assert "bar" in names                                         # names no clip: an error, not silence
    assert "other_clip" not in names
    miss = [f for f in failures if f.name == "bar"][0]
    assert "bar-bold" in miss.reason
    # the kit clip was attempted under its hyphenated name (it fails here only if Manim cannot render it)
    assert "bar-bold" in index or "bar-bold" in names


def test_colliding_names_are_an_error(scianim, tmp_path):
    deck = make_deck(tmp_path, projects=("sweep",))
    (deck / "anim").mkdir()
    (deck / "anim" / "clip_sweep.py").write_text("class Sweep(Scene):\n    pass\n")
    index, failures = clips.run_clips(deck)
    assert len(failures) == 1 and "one clip name" in failures[0].reason
    assert "'sweep' (kit" in failures[0].reason and "'sweep' (manim8" in failures[0].reason
    assert scianim.calls("render") == [] and index == {}


# ---------------------------------------------------------------- presets
@needs_ffmpeg
def test_dark_mode_writes_its_own_folder_and_index(scianim, tmp_path):
    from lecturekit.theme import write_tokens
    deck = make_deck(tmp_path)
    write_tokens(deck, manim8_version="0.1.0")                    # paper and dark styles; paper selected
    light, failures = clips.run_clips(deck)
    assert failures == []
    render = scianim.calls("render")[-1]
    assert render[render.index("--style") + 1] == "lecturekit_paper@0.1.0"
    dark, failures = clips.run_clips(deck, mode="dark")
    assert failures == []
    render = scianim.calls("render")[-1]
    assert render[render.index("--style") + 1] == "lecturekit_dark@0.1.0"
    rec = dark["divisive_normalization"]
    assert rec["video"] == "assets/clips/dark/divisive_normalization.mp4"
    assert rec["still"].startswith("assets/clips/dark/divisive_normalization.")
    assert rec["job"]["style"] == "lecturekit_dark@0.1.0"
    assert (deck / rec["video"]).exists() and (deck / rec["still"]).exists()
    on_disk = json.loads((deck / "assets" / "clips" / "dark" / "clips.json").read_text())
    assert on_disk["divisive_normalization"]["video"] == rec["video"]
    paper = json.loads((deck / "assets" / "clips" / "clips.json").read_text())
    assert paper["divisive_normalization"]["video"] == "assets/clips/divisive_normalization.mp4"
    assert light["divisive_normalization"]["job"]["id"] != rec["job"]["id"]


FAKE_MANIM = """import json, os, subprocess, sys
from pathlib import Path
args = sys.argv[1:]
media, name = Path(args[args.index("--media_dir") + 1]), args[args.index("-o") + 1]
if not Path(args[-2]).is_file():                     # Manim reads the scene file from its working directory
    sys.exit(f"FileNotFoundError: {Path.cwd() / args[-2]} not found")
w, h = args[args.index("-r") + 1].split(",")
out = media / "videos" / "clip" / f"{h}p30" / f"{name}.mp4"
out.parent.mkdir(parents=True, exist_ok=True)
subprocess.run([os.environ["FFMPEG"], "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r=30:d=1",
                "-pix_fmt", "yuv420p", str(out)], check=True)
keys = ("LECTUREKIT_MODE", "LECTUREKIT_BRAND", "FONTCONFIG_FILE", "NM_CLIP_SIZE")
Path(os.environ["FAKE_MANIM_ENV"]).write_text(json.dumps({k: os.environ.get(k) for k in keys}))
"""


@needs_ffmpeg
def test_kit_clips_follow_the_preset(scianim, tmp_path, monkeypatch):
    deck = make_deck(tmp_path, projects=())
    (deck / "anim").mkdir()
    (deck / "anim" / "clip_bar_bold.py").write_text("class BarBold(Scene):\n    still = 0.5\n")
    fake = tmp_path / "manim"
    fake.write_text(f"#!/bin/sh\nexec \"{sys.executable}\" \"{tmp_path / 'fake_manim.py'}\" \"$@\"\n")
    fake.chmod(0o755)
    (tmp_path / "fake_manim.py").write_text(FAKE_MANIM)
    monkeypatch.setattr(clips, "_manim_exe", lambda: str(fake))
    monkeypatch.setenv("FFMPEG", clips._ffmpeg())
    monkeypatch.setenv("FAKE_MANIM_ENV", str(tmp_path / "env.json"))
    monkeypatch.delenv("FONTCONFIG_FILE", raising=False)
    index, failures = clips.run_clips(deck, mode="dark", size="640x360")
    assert failures == []
    env = json.loads((tmp_path / "env.json").read_text())
    assert env["LECTUREKIT_MODE"] == "dark" and env["NM_CLIP_SIZE"] == "640x360"
    assert Path(env["LECTUREKIT_BRAND"]).resolve() == (deck / "_brand-dark.yml").resolve()
    assert env["FONTCONFIG_FILE"].endswith("fonts.conf")
    rec = index["bar-bold"]
    assert rec["video"] == "assets/clips/dark/bar-bold.mp4" and rec["still"] == "assets/clips/dark/bar-bold.png"
    assert (rec["producer"], rec["width"], rec["height"], rec["fps"]) == ("kit", 640, 360, 30.0)
    assert rec["source"] == "anim/clip_bar_bold.py:BarBold" and no_nulls(rec)
    assert (deck / rec["video"]).exists() and (deck / rec["still"]).exists()
    assert not (deck / "assets" / "clips" / "clips.json").exists()           # the paper index is untouched


@needs_ffmpeg
def test_kit_clips_from_a_relative_deck_path(scianim, tmp_path, monkeypatch):
    deck = make_deck(tmp_path, projects=())
    (deck / "anim").mkdir()
    (deck / "anim" / "clip_bar_bold.py").write_text("class BarBold(Scene):\n    pass\n")
    fake = tmp_path / "manim"
    fake.write_text(f"#!/bin/sh\nexec \"{sys.executable}\" \"{tmp_path / 'fake_manim.py'}\" \"$@\"\n")
    fake.chmod(0o755)
    (tmp_path / "fake_manim.py").write_text(FAKE_MANIM)
    monkeypatch.setattr(clips, "_manim_exe", lambda: str(fake))
    monkeypatch.setenv("FFMPEG", clips._ffmpeg())
    monkeypatch.setenv("FAKE_MANIM_ENV", str(tmp_path / "env.json"))
    monkeypatch.chdir(tmp_path)                                        # `lk clips deck` from the parent folder
    index, failures = clips.run_clips(Path("deck"), only=["bar_bold"])
    assert failures == [], failures
    assert index["bar-bold"]["video"] == "assets/clips/bar-bold.mp4"
    assert (deck / "assets" / "clips" / "bar-bold.mp4").exists()
    assert not (deck / "anim" / "deck").exists()                       # nothing written under a doubled path


def test_dark_mode_needs_a_bridged_dark_style(scianim, tmp_path):
    deck = make_deck(tmp_path)
    _, failures = clips.run_clips(deck, mode="dark")
    assert len(failures) == 1 and "lk theme" in failures[0].reason


@needs_ffmpeg
def test_dark_mode_from_the_environment(scianim, tmp_path, monkeypatch):
    from lecturekit.theme import write_tokens
    deck = make_deck(tmp_path)
    write_tokens(deck, manim8_version="0.1.0")
    monkeypatch.setenv("LECTUREKIT_MODE", "dark")
    assert lk(["clips", str(deck)]) == 0
    assert (deck / "assets" / "clips" / "dark" / "clips.json").exists()


@needs_ffmpeg
def test_crop_applies_to_manim8_clips(scianim, tmp_path):
    deck = make_deck(tmp_path)
    index, failures = clips.run_clips(deck, crop=True)
    assert failures == []
    rec = index["divisive_normalization"]
    # the fake's checkpoints draw boxes from x=60..200, y=40..120 on white; margin 24, even sizes
    assert (rec["width"], rec["height"]) == (188, 128)
    assert clips.probe(deck / rec["video"])[:2] == (188, 128)
    from PIL import Image
    for png in rec["checkpoints"].values():
        assert Image.open(deck / png).size == (188, 128)


@needs_ffmpeg
def test_size_that_differs_from_the_project_output_warns(scianim, tmp_path, capsys):
    deck = make_deck(tmp_path)
    clips.run_clips(deck, size="1280x720")
    assert "applies to kit clips only" in capsys.readouterr().err


def test_fonts_reach_fontconfig(tmp_path, monkeypatch):
    monkeypatch.delenv("FONTCONFIG_FILE", raising=False)
    env = clips.tool_env(tmp_path)
    conf = Path(env["FONTCONFIG_FILE"])
    text = conf.read_text()
    fonts = clips.fonts_dir(tmp_path)
    assert f"<dir>{fonts}</dir>" in text and "<include" in text
    monkeypatch.setenv("FONTCONFIG_FILE", "/elsewhere/fonts.conf")
    assert clips.tool_env(tmp_path)["FONTCONFIG_FILE"] == "/elsewhere/fonts.conf"
    if shutil.which("fc-list"):
        files = subprocess.run(["fc-list", "--format", "%{file}\n"], capture_output=True, text=True,
                               env=dict(os.environ, FONTCONFIG_FILE=str(conf))).stdout
        assert str(fonts / "texgyreheros-regular.otf") in files


@needs_ffmpeg
def test_index_existing_writes_no_nulls(tmp_path):
    out = tmp_path / "assets" / "clips"
    out.mkdir(parents=True)
    subprocess.run([clips._ffmpeg(), "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=white:s=64x36:d=1",
                    "-pix_fmt", "yuv420p", str(out / "loose.mp4")], check=True)
    rec = clips.index_existing(tmp_path)["loose"]
    assert "still" not in rec and rec["producer"] == "external" and no_nulls(rec)


# ---------------------------------------------------------------- the bridged styles
def _project_with_presets(tmp_path: Path, brand_dir: Path = TEMPLATES) -> Path:
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "_quarto.yml").write_text("project:\n  type: default\n")
    for name in ("_brand.yml", "_brand-dark.yml", "_quarto-dark.yml"):
        if (brand_dir / name).exists():
            shutil.copy(brand_dir / name, proj / name)
    return proj


@pytest.mark.parametrize("brands", [TEMPLATES, KICKOFF], ids=["scaffold", "kickoff"])
def test_bridged_styles_are_valid_manim8_styles(tmp_path, brands):
    from lecturekit.theme import load_brand, write_tokens
    proj = _project_with_presets(tmp_path, brands)
    written = write_tokens(proj, manim8_version="0.1.0")
    paper = proj / "styles" / "lecturekit_paper" / "0.1.0" / "style.yaml"
    dark = proj / "styles" / "lecturekit_dark" / "0.1.0" / "style.yaml"
    assert paper in written and dark in written
    for sheet, brand, mode in ((paper, "_brand.yml", "light"), (dark, "_brand-dark.yml", "dark")):
        doc = yaml.safe_load(sheet.read_text())
        tokens = load_brand(proj / brand, mode=mode)
        assert SLUG.match(doc["name"]) and doc["version"] == "0.1.0"
        assert all(SLUG.match(k) for k in doc["palette"]), [k for k in doc["palette"] if not SLUG.match(k)]
        assert doc["palette"]["background"] == tokens.colors["slide"]
        assert doc["palette"]["neutral"] == tokens.colors["hairline"]             # a quiet surface, not text
        assert doc["palette"]["neutral"] != doc["palette"]["secondary_text"]
        for role in ("primary_signal", "emphasis", "warning", "comparison", "normalization_pool", "dog", "css"):
            assert f"{role}_soft" in doc["palette"]
        for role, face in doc["typography"].items():
            fallbacks = face["font_fallbacks"]
            assert len(fallbacks) == len(set(fallbacks)) and face["font_family"] not in fallbacks, role
        try:
            from scianim_core.style import StyleSheet
        except ImportError:
            continue
        StyleSheet.model_validate(doc)
    assert yaml.safe_load(dark.read_text())["palette"]["background"] == "#000000"


def test_styles_go_into_the_workspace_and_are_written_once(tmp_path, no_manim8):
    from lecturekit.theme import write_tokens                                   # no scianim: direct edits
    deck = make_deck(tmp_path)
    write_tokens(deck, manim8_version="0.1.0")
    assert (deck / "clips" / "styles" / "lecturekit_paper" / "0.1.0" / "style.yaml").exists()
    assert (deck / "clips" / "styles" / "lecturekit_dark" / "0.1.0" / "style.yaml").exists()
    assert not (deck / "styles").exists()
    anim = deck / "clips" / "families" / "neuro" / "divisive_normalization" / "animation.yaml"
    text = anim.read_text()
    assert "# chosen by the lecturer" in text                                   # the file is edited in place
    assert yaml.safe_load(text)["style"] == {"name": "lecturekit_paper", "version": "0.1.0", "overrides": {}}
    fam = yaml.safe_load((deck / "clips" / "families" / "neuro" / "family.yaml").read_text())
    assert fam["style"] == {"name": "lecturekit_paper", "version": "0.1.0"}
    write_tokens(deck, manim8_version="0.1.0")                                  # the same content: fine
    brand = deck / "_brand.yml"
    brand.write_text(brand.read_text().replace('slide: "#FFFFFF"', 'slide: "#FFFFF0"'))
    with pytest.raises(ValueError, match="new version"):
        write_tokens(deck, manim8_version="0.1.0")
    assert lk(["theme", str(deck), "--manim8", "0.1.0"]) == 1
    write_tokens(deck, manim8_version="0.2.0")
    from lecturekit.theme import bridged_style
    assert bridged_style(deck, "light") == "lecturekit_paper@0.2.0"


def test_style_is_selected_through_a_manim8_proposal(scianim, tmp_path, monkeypatch):
    from lecturekit.theme import write_tokens
    saved = tmp_path / "proposals"
    saved.mkdir()
    monkeypatch.setenv("FAKE_SCIANIM_PROPOSALS", str(saved))
    deck = make_deck(tmp_path)
    project = deck / "clips" / "families" / "neuro" / "divisive_normalization"
    write_tokens(deck, manim8_version="0.1.0")
    (call,) = scianim.calls("propose")
    assert call[:3] == ["propose", "apply", str(project)]
    assert yaml.safe_load((project / "animation.yaml").read_text())["style"]["name"] == "lecturekit_paper"
    (proposal,) = saved.glob("*.yaml")
    doc = yaml.safe_load(proposal.read_text())
    assert doc["kind"] == "revise_spec" and doc["targets"][0]["file"] == "animation.yaml"
    try:
        from scianim_core.proposals import Proposal
    except ImportError:
        return
    Proposal.model_validate(doc)
    write_tokens(deck, manim8_version="0.1.0")
    assert len(scianim.calls("propose")) == 1                                 # already selected: no new proposal


# ---------------------------------------------------------------- vendoring
def _shared(tmp_path: Path) -> tuple[Path, Path]:
    shared = tmp_path / "shared" / "_extensions"
    shutil.copytree(extension_source(), shared / "lecturekit")
    (shared / "lecturekit" / "MARKER").write_text("the shared copy")
    (shared / "other").mkdir()
    (shared / "other" / "_extension.yml").write_text("title: other\n")
    proj = tmp_path / "shared" / "proj"
    proj.mkdir()
    os.symlink("../_extensions", proj / "_extensions")
    return shared, proj


def test_vendor_replaces_a_dangling_extensions_link(tmp_path):
    proj = tmp_path / "copied-out"
    proj.mkdir()
    os.symlink("../_extensions", proj / "_extensions")                         # as `cp -r` out of the expo leaves it
    dest = vendor_extension(proj)
    assert not (proj / "_extensions").is_symlink() and (dest / "_extension.yml").exists()


def test_vendor_replaces_a_dangling_lecturekit_link(tmp_path):
    (tmp_path / "proj" / "_extensions").mkdir(parents=True)
    os.symlink("../../nowhere/lecturekit", tmp_path / "proj" / "_extensions" / "lecturekit")
    dest = vendor_extension(tmp_path / "proj")
    assert not dest.is_symlink() and (dest / "_extension.yml").exists()


def test_vendor_keeps_a_shared_copy_without_force(tmp_path):
    shared, proj = _shared(tmp_path)
    vendor_extension(proj)
    assert (proj / "_extensions").is_symlink() and (shared / "lecturekit" / "MARKER").exists()


def test_vendor_force_never_overwrites_a_shared_copy(tmp_path, capsys):
    shared, proj = _shared(tmp_path)
    dest = vendor_extension(proj, force=True)
    assert not (proj / "_extensions").is_symlink()
    assert (shared / "lecturekit" / "MARKER").read_text() == "the shared copy"   # untouched
    assert not (dest / "MARKER").exists() and (dest / "_extension.yml").exists()
    assert (proj / "_extensions" / "other" / "_extension.yml").exists()        # the other extensions came along
    assert "now a real directory" in capsys.readouterr().err


# ---------------------------------------------------------------- the scaffold
def test_new_with_a_budget(tmp_path):
    assert lk(["new", str(tmp_path / "p"), "--budget", "20", "--title", "Joint visual and auditory maps"]) == 0
    p = tmp_path / "p"
    assert re.search(r"^budget: 20$", (p / "slides.qmd").read_text(), re.M)
    plan = (p / "PLAN.md").read_text()
    assert "Total: 5 of 20 minutes." in plan and "'s budget" not in plan and "example.tex" in plan
    assert "example.tex" in (p / "MANIFEST.md").read_text() and "example.tikz" not in (p / "MANIFEST.md").read_text()
    assert "_quarto.yml" not in (p / "AGENTS.md").read_text().split("Budget:")[1].splitlines()[0]
    for f in p.rglob("*.md"):
        assert "{{" not in f.read_text(), f
    ignore = (p / ".gitignore").read_text().splitlines()
    for pattern in ("clips/**/renders/", "clips/**/.scianim/", "clips/**/.venv/", "anim/media/",
                    "slides.aux", "slides.nav", "slides.snm", "slides.toc"):
        assert pattern in ignore, pattern


def test_new_manim8_without_manim8_says_how_to_install(tmp_path, no_manim8, capsys):
    assert lk(["new", str(tmp_path / "p"), "--manim8"]) == 1
    assert "lecturekit[manim8]" in capsys.readouterr().err
    assert (tmp_path / "p" / "slides.qmd").exists() and not (tmp_path / "p" / "clips").exists()


def test_new_manim8_makes_a_workspace(scianim, tmp_path):
    p = tmp_path / "my-lecture"
    assert lk(["new", str(p), "--manim8"]) == 0
    assert (p / "clips" / "workspace.yaml").exists()
    assert (p / "clips" / "styles" / "lecturekit_paper" / "0.1.0" / "style.yaml").exists()
    assert (p / "clips" / "styles" / "lecturekit_dark" / "0.1.0" / "style.yaml").exists()
    fam = yaml.safe_load((p / "clips" / "families" / "my_lecture" / "family.yaml").read_text())
    assert fam["style"] == {"name": "lecturekit_paper", "version": "0.1.0"}
    spec = yaml.safe_load((p / "clips" / "families" / "my_lecture" / "first_clip" / "animation.yaml").read_text())
    assert (spec["output"]["width_px"], spec["output"]["height_px"], spec["output"]["fps"]) == (1280, 720, 30)
    assert spec["style"]["name"] == "lecturekit_paper" and str(spec["style"]["version"]) == "0.1.0"
    # a project without a storyboard yet is skipped by lk clips, not an error
    index, failures = clips.run_clips(p)
    assert failures == [] and index == {}


def test_new_manim8_on_an_existing_project_adds_only_the_workspace(scianim, tmp_path):
    p = tmp_path / "existing"
    assert lk(["new", str(p)]) == 0
    (p / "slides.qmd").write_text("the lecturer's own\n")
    (p / "STORYBOARD.md").unlink()
    assert lk(["new", str(p), "--manim8"]) == 0
    assert (p / "clips" / "workspace.yaml").exists()
    assert (p / "slides.qmd").read_text() == "the lecturer's own\n" and not (p / "STORYBOARD.md").exists()


@needs_quarto
def test_new_project_reports_its_budget(tmp_path):
    p = tmp_path / "trial"
    assert lk(["new", str(p), "--budget", "20"]) == 0
    r = subprocess.run([sys.executable, "-m", "lecturekit.cli", "build", str(p), "--to", "live"],
                       capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    assert "budget 20 min" in (p / "_build" / "timing.txt").read_text()
