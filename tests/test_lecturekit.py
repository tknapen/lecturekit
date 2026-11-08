"""End-to-end tests: the feature deck builds in both formats and the method's
checks run on it. They need quarto, xelatex, pymupdf and Playwright's chromium.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "examples" / "features"

needs_quarto = pytest.mark.skipif(shutil.which("quarto") is None, reason="quarto not installed")
needs_tex = pytest.mark.skipif(shutil.which("xelatex") is None, reason="xelatex not installed")


def run(cmd, cwd=None, **kw):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, **kw)


@pytest.fixture(scope="session")
def built_features():
    if not (FEATURES / "_extensions" / "lecturekit").exists():
        os.symlink("../../_extensions", FEATURES / "_extensions")
    r = run([sys.executable, "-m", "lecturekit.cli", "build", str(FEATURES)])
    assert r.returncode == 0, r.stderr[-3000:]
    return FEATURES


# ---------------------------------------------------------------- the theme
def test_tokens_from_brand():
    from lecturekit.theme import load_brand
    t = load_brand(FEATURES / "_brand.yml")
    assert t.colors["ink"] == "#202B33"
    assert t.colors["foreground"] == "#202B33"          # semantic alias resolved
    assert t.missing_engine_colors() == []
    assert "\\definecolor{nmConcept}{HTML}{175B8E}" in t.latex()
    assert "--nm-concept:#175B8E;" in t.css()
    assert "CONCEPT = '#175B8E'" in t.python()
    assert "\\setmainfont{TeX Gyre Heros}" in t.latex()
    assert "\\newfontfamily\\lkheadfont{TeX Gyre Pagella}" in t.latex()


def test_dark_brand_and_manim8_style():
    from lecturekit.theme import load_brand
    t = load_brand(FEATURES / "_brand-dark.yml", mode="dark")
    assert t.colors["slide"] == "#000000"
    style = t.manim8_style("0.1.0")
    assert "inherits: default@0.5.0" in style
    assert "background: '#000000'" in style


def test_tokens_module(monkeypatch):
    monkeypatch.setenv("LECTUREKIT_BRAND", str(FEATURES / "_brand.yml"))
    from lecturekit import tokens
    tokens.reload(str(FEATURES / "_brand.yml"))
    assert tokens.INK == "#202B33"
    assert tokens.GAUSS == "#175B8E"
    assert tokens.rgb("slide") == (1.0, 1.0, 1.0)


def test_contrast_tool_passes_on_presets():
    from lecturekit.review.contrast import check, ratio
    assert ratio("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert check(FEATURES / "_brand.yml") == []
    assert check(FEATURES / "_brand-dark.yml", mode="dark") == []


# ---------------------------------------------------------------- the build
@needs_quarto
@needs_tex
def test_both_outputs_exist(built_features):
    assert (built_features / "_build" / "slides-live.html").exists()
    assert (built_features / "_build" / "slides-study.pdf").exists()
    # clips and stills are copied beside the live deck
    assert (built_features / "_build" / "assets" / "clips" / "bar_bold.mp4").exists()


@needs_quarto
@needs_tex
def test_timing_report(built_features):
    text = (built_features / "timing.txt").read_text()
    assert "budget  15'" in text
    assert re.search(r"^\s+1\s+concept\s+2'", text, re.M)
    assert "under budget" in text


@needs_quarto
@needs_tex
def test_live_deck_content(built_features):
    html = (built_features / "_build" / "slides-live.html").read_text()
    assert "--nm-ink:#202B33" in html                       # brand tokens inline
    assert 'class="lk-eyebrow lk-role-concept"' in html     # eyebrows
    assert 'data-planned="2.00"' in html                    # pacing data
    assert "<video class=\"lk-clip\"" in html               # movie block
    assert "Study-only detail" not in html                  # study-only slide dropped
    assert "Click the clip to pause" in html                # live-only kept
    assert "lk-tikz" in html and ".svg" in html             # TikZ as SVG
    assert "<em>Hedger et al.</em>" in html                 # italic citation names


@needs_quarto
@needs_tex
def test_study_pdf_content(built_features):
    import pymupdf
    doc = pymupdf.open(built_features / "_build" / "slides-study.pdf")
    text = "\n".join(page.get_text() for page in doc)
    assert len(doc) == 9                                     # title + 7 slides + study-only + refs... see deck
    assert "Study-only detail" in text
    assert "Click the clip to pause" not in text             # live-only dropped
    assert "CONCEPT" in text and "CAVEAT" in text            # eyebrows
    tokens_tex = (built_features / "_lecturekit" / "tokens.tex").read_text()
    assert "\\definecolor{nmConcept}{HTML}{175B8E}" in tokens_tex


@needs_quarto
@needs_tex
def test_review_tools(built_features):
    from lecturekit.review.measure import measure
    from lecturekit.review.frags import frags
    deck = built_features / "_build" / "slides-live.html"
    assert measure(deck) == 0
    assert frags(deck) == 0
    from lecturekit.review.shoot import shoot
    out = built_features / "review" / "shots-test"
    files = shoot(deck, out)
    assert len(files) == 8


@needs_quarto
@needs_tex
def test_new_project_builds(tmp_path):
    from lecturekit.scaffold import create_project
    proj = create_project(tmp_path / "trial", title="A trial lecture")
    assert (proj / "_extensions" / "lecturekit" / "_extension.yml").exists()
    assert (proj / "slides.qmd").exists()
    r = run([sys.executable, "-m", "lecturekit.cli", "build", str(proj)])
    assert r.returncode == 0, r.stderr[-3000:]
    assert (proj / "_build" / "slides-live.html").exists()
    assert (proj / "_build" / "slides-study.pdf").exists()
    assert (proj / "assets" / "figures" / "example.tikz").exists()   # make_assets ran


def test_clips_index_schema():
    index = json.loads((FEATURES / "assets" / "clips" / "clips.json").read_text())
    rec = index["bar_bold"]
    for key in ("video", "still", "width", "height", "duration"):
        assert key in rec
