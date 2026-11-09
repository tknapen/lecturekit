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
    index, failures = clips.run_clips(deck)
    assert failures == []
    future = 4_102_444_800                                                # 2100-01-01
    os.utime(decoy / "manifest.json", (future, future))
    assert "--json" not in scianim.calls("render")[-1]
    (job,) = [j for j in jobs(project) if j != decoy]
    assert sha(deck / index["divisive_normalization"]["video"]) == sha(job / f"{job.name}.mp4")
    index, failures = clips.run_clips(deck)                               # a cache hit, after the decoy got newer
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


def test_missing_manim_names_the_clips_extra(monkeypatch, tmp_path):
    monkeypatch.setattr(clips, "_manim_exe", lambda: None)
    (tmp_path / "anim").mkdir()
    script = tmp_path / "anim" / "clip_x.py"
    script.write_text("class X(Scene):\n    pass\n")
    with pytest.raises(clips.ClipError, match=r"lecturekit\[clips\]"):
        clips.render_kit_scene(tmp_path, script, "X")


def test_missing_scianim_names_the_manim8_extra(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))
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


def test_styles_go_into_the_workspace_and_are_written_once(tmp_path, monkeypatch):
    from lecturekit.theme import write_tokens
    monkeypatch.setenv("PATH", str(tmp_path / "nothing"))                       # no scianim: direct edits
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


