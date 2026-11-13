"""End-to-end tests: the two example decks build in both formats through the extension, the dialect has its
effects in each output, and the method's checks run on the results. They need quarto, xelatex, pymupdf and
Playwright's chromium (PLAYWRIGHT_BROWSERS_PATH is honoured).
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
KICKOFF = ROOT / "examples" / "kickoff"

needs_quarto = pytest.mark.skipif(shutil.which("quarto") is None, reason="quarto not installed")
needs_tex = pytest.mark.skipif(shutil.which("xelatex") is None, reason="xelatex not installed")


def run(cmd, cwd=None, **kw):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, **kw)


def link_extension(project: Path) -> None:
    link = project / "_extensions"
    if not link.exists() and not link.is_symlink():
        os.symlink("../../_extensions", link)


@pytest.fixture(scope="session")
def built_features():
    link_extension(FEATURES)
    r = run([sys.executable, "-m", "lecturekit.cli", "build", str(FEATURES)])
    assert r.returncode == 0, (r.stdout + r.stderr)[-4000:]
    return FEATURES


@pytest.fixture(scope="session")
def built_kickoff():
    link_extension(KICKOFF)
    r = run([sys.executable, "-m", "lecturekit.cli", "build", str(KICKOFF)])
    assert r.returncode == 0, (r.stdout + r.stderr)[-4000:]
    return KICKOFF


def pdf_text(path: Path) -> str:
    import pymupdf
    return "\n".join(page.get_text() for page in pymupdf.open(path))


def pdf_pages(path: Path) -> int:
    import pymupdf
    return len(pymupdf.open(path))


# ---------------------------------------------------------------- the theme
def test_tokens_from_brand():
    from lecturekit.theme import load_brand
    t = load_brand(KICKOFF / "_brand.yml")
    assert t.colors["ink"] == "#202B33"
    assert t.colors["foreground"] == "#202B33"          # semantic alias resolved
    assert t.missing_engine_colors() == []
    latex = t.latex()
    assert "\\definecolor{nmConcept}{HTML}{175B8E}" in latex
    assert "\\definecolor{nmDoG}{HTML}{B87400}" in latex   # palette keys keep the LaTeX spelling
    assert "\\setmainfont{texgyrepagella-regular.otf}[Path=" in latex
    assert "\\newfontfamily\\nmSansCaps{texgyreheros-regular.otf}" in latex
    assert "--nm-concept:#175B8E;" in t.css()
    assert "CONCEPT = '#175B8E'" in t.python()


def test_dark_brand_and_manim8_style():
    from lecturekit.theme import load_brand
    t = load_brand(KICKOFF / "_brand-dark.yml", mode="dark")
    assert t.colors["slide"] == "#000000"
    assert t.colors["heading"] == "#C9B6F2"
    assert "\\setmainfont{Roboto-Regular.ttf}[Path=" in t.latex()
    style = t.manim8_style("0.1.0")
    assert "inherits: default@0.5.0" in style
    assert "background: '#000000'" in style


def test_tokens_module(monkeypatch):
    from lecturekit import tokens
    tokens.reload(str(KICKOFF / "_brand.yml"))
    assert tokens.INK == "#202B33"
    assert tokens.GAUSS == "#175B8E"
    assert tokens.rgb("slide") == (1.0, 1.0, 1.0)


def test_tikz_kit_names():
    from lecturekit import tikz
    assert (tikz.INK, tikz.BLUE, tikz.DOG, tikz.CSS, tikz.DN) == ("nmInk", "nmConcept", "nmDoG", "nmCSS", "nmDN")
    P = tikz.Panel(0, 0, 10, 5, (0, 100), (0, 1))
    assert P.pt(50, 0.5) == "(5.000,2.500)"
    assert tikz.escape("50% of _x_") == "50\\% of \\_x\\_"


def test_contrast_tool_passes_on_presets():
    from lecturekit.review.contrast import check, ratio
    assert ratio("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert check(KICKOFF / "_brand.yml") == []
    assert check(KICKOFF / "_brand-dark.yml", mode="dark") == []


# ---------------------------------------------------------------- the feature deck
@needs_quarto
@needs_tex
def test_features_outputs(built_features):
    build = built_features / "_build"
    assert (build / "slides-live.html").exists()
    assert (build / "slides-study.pdf").exists()
    assert (build / "assets" / "clips" / "bar_bold.mp4").exists()      # the resources rule
    assert not (build / "_build").exists()                             # the glob is anchored
    timing = (build / "timing.txt").read_text()
    assert re.search(r"^\s+2\s+3\s+concept\s+One source, two outputs$", timing, re.M)
    assert "budget 15 min  ok" in timing


@needs_quarto
@needs_tex
def test_features_live_deck(built_features):
    html = (built_features / "_build" / "slides-live.html").read_text()
    assert "--nm-ink:#202B33" in html                                   # brand tokens inline
    assert 'data-role-label="CORE CONCEPT"' in html                     # the eyebrow label
    assert 'data-timing="120"' in html                                  # pacing data in seconds
    assert 'data-background-color="#F3F2EE"' in html                    # paper roles
    assert '<div class="nm-foot"' in html                                # the per-slide foot
    assert "<video" in html and "data-lk-autoplay" in html               # movie blocks, played by the runtime
    assert 'poster="assets/clips/bar_bold.png"' in html                 # the seam supplies the still
    # the manim8 clip, through the same seam, its latest checkpoint as the poster, both versioned by its sha256
    sha8 = json.loads((built_features / "assets/clips/clips.json").read_text())["tuning_sweep"]["sha256"][:8]
    assert f'src="assets/clips/tuning_sweep.mp4?v={sha8}"' in html
    assert f'poster="assets/clips/tuning_sweep.widened.png?v={sha8}"' in html
    assert 'src="assets/clips/bar_bold.mp4"' in html                    # an entry without a sha256: no version
    # the compiled theme finds the brand's font files (Quarto writes their project paths, which the CSS cannot reach)
    theme = next((built_features / "_build").glob("slides_files/libs/revealjs/dist/theme/*.css")).read_text()
    assert 'url("_extensions/' not in theme and 'url("../../../../../_extensions/lecturekit/fonts/' in theme
    assert 'class="tikz"' in html and "_lecturekit/tikz/" in html        # TikZ as SVG
    # three clips in parts: one cue per key, the video loaded by the runtime only, versioned by its sha256
    cues = re.findall(r'<div class="fragment lk-cue"[^>]*data-lk-for="([^"]+)"', html)
    assert cues == ["bar_steps"] * 3 + ["tuning_sweep"] * 2 + ["gauss-parts"] * 2, cues   # start=key adds one
    assert 'data-lk-src="assets/clips/bar_steps.mp4"' in html and ' src="assets/clips/bar_steps.mp4' not in html
    assert 'data-lk-start="key"' in html and "Ask: the bar rests left of centre." in html
    assert "Study-only detail" not in html                              # study-only slide dropped
    assert "The clip's last frame" not in html                          # study-only block dropped
    assert 'class="citation"' in html                                    # citations (italic by CSS)
    assert 'class="blue"' in html                                        # coloured spans
    assert "@font-face" in html and "texgyrepagella-regular.otf" in html  # bundled fonts


@needs_quarto
@needs_tex
def test_features_study_pdf(built_features):
    pdf = built_features / "_build" / "slides-study.pdf"
    assert pdf_pages(pdf) == 19
    text = pdf_text(pdf)
    assert "STUDY-ONLY DETAIL" in text                                   # study-only slide kept, title in capitals
    assert "CORE CONCEPT" in text and "TAKEAWAYS" in text                # eyebrows
    assert "FEATURES" in text                                            # the foot's short title
    assert "Named in assets/clips/clips.json" in text                    # the seam's still carries its caption
    assert "the PDF shows its last checkpoint" in text                   # the manim8 clip's still and caption
    tex = (built_features / "slides.tex").read_text()
    assert re.search(r"\\textcolor\{nmInput\}\{a live deck\s+and a study PDF\}", tex)   # coloured spans (Pandoc wraps lines)
    assert "{\\footnotesize\\itshape " in tex                           # citations italic and small
    assert "\\begin{frame}[fragile,nmrole=concept]" in tex              # roles as frame options, fragile allowed
    assert "\\nmfigureh{4.2cm}{assets/figures/pipeline.tex}" in tex     # the raw figure form stays
    assert "assets/clips/tuning_sweep.widened.png" in tex                # the manim8 checkpoint as the still
    # the clips in parts print a strip of their holds: four panels for bar_steps (three stops and the end), three
    # for tuning_sweep, two for gauss-parts (start=key: the strip shows the hold after each part)
    strips = re.findall(r"^\\lkstrip\{([^}]*)\}\{(\d)\}\{(\d)\}", tex, re.M)
    assert strips == [("4.8cm", "2", "2"), ("4.8cm", "3", "1"), ("4.8cm", "2", "1")], strips
    assert "\\lkpanel{assets/clips/bar_steps.f0042.png}{1}{left of centre}" in tex
    assert "\\lkpanel{assets/clips/tuning_sweep.f0069.png}{2}{gain 2}" in tex
    assert "1 left of centre" in text and "2 gain 2" in text and "1 half the width" in text
    tokens_tex = (built_features / "_lecturekit" / "tokens.tex").read_text()
    assert "\\definecolor{nmConcept}{HTML}{175B8E}" in tokens_tex


@needs_quarto
@needs_tex
def test_filter_and_python_tokens_agree(built_features):
    from lecturekit.theme import load_brand
    filter_lines = {l for l in (built_features / "_lecturekit" / "tokens.tex").read_text().splitlines() if l.startswith("\\definecolor")}
    python_lines = {l for l in load_brand(built_features / "_brand.yml").latex().splitlines() if l.startswith("\\definecolor")}
    assert filter_lines == python_lines


# ---------------------------------------------------------------- the worked example
@needs_quarto
@needs_tex
def test_kickoff_builds(built_kickoff):
    build = built_kickoff / "_build"
    assert pdf_pages(build / "slides-study.pdf") == 9
    text = pdf_text(build / "slides-study.pdf")
    assert "COIMBRA · WELCOME" in text                                   # shorttitle in the foot
    assert "POPYLAR PRF WORKSHOP" in text                                # eyebrow on the title page
    timing = (build / "timing.txt").read_text()
    assert "slides 8  planned 15 min  untimed 1  budget 15 min  ok" in timing
    html = (build / "slides-live.html").read_text()
    assert html.count("<section") >= 9
    assert 'data-eyebrow="Popylar pRF workshop' in html
    # the figures regenerate identically from make_assets.py (pre-render) and the kit
    assert (built_kickoff / "assets" / "figures" / "shelf.tex").exists()


@needs_quarto
@needs_tex
def test_review_tools(built_features, tmp_path):
    from lecturekit.review.frags import frags
    from lecturekit.review.measure import measure
    from lecturekit.review.overflow import report
    from lecturekit.review.shoot import shoot
    deck = built_features / "_build" / "slides-live.html"
    result = shoot(deck, tmp_path / "shots", sheet=True)
    assert result["slides"] == 18
    assert (tmp_path / "shots" / "slide-14.png").exists()
    assert (tmp_path / "shots" / "report.json").exists()
    assert not [r for r in result["report"] if r["over"]], result["report"]
    assert not result["errors"], result["errors"]
    # every ordinary clip is shot paused on its last frame; a clip in parts is left to its runtime
    from lecturekit.review.browser import deck_page, goto, slide_count
    from lecturekit.review.shoot import settle_clips
    settled = 0
    with deck_page(deck) as (page, errors):
        for i in range(1, slide_count(page) + 1):
            goto(page, i)
            n = settle_clips(page, errors)
            state = page.evaluate("""() => [...Reveal.getCurrentSlide().querySelectorAll('video')]
              .filter(v => !v.closest('.lk-seg')).map(v => [v.paused, v.currentTime, v.duration])""")
            assert len(state) == n
            assert all(p and t == d for p, t, d in state), (i, state)
            settled += n
        assert not errors, errors
    assert settled >= 3
    assert measure(deck) == 0
    assert frags(deck, tmp_path / "frags") == 0
    assert report(built_features / "slides.log") in (0, 1)


@needs_quarto
@needs_tex
def test_figs_preview(tmp_path):
    from lecturekit.review.figs import preview
    link_extension(KICKOFF)
    assert preview(KICKOFF, ["timeline"], out=tmp_path) == 0
    assert (tmp_path / "timeline.png").exists()


@needs_quarto
@needs_tex
def test_new_project_builds(tmp_path):
    """A scaffolded project builds, and its first build leaves a committed scaffold clean: what the build writes
    is ignored (Quarto's own .gitignore lines included) or is the scaffold's own figure, regenerated unchanged."""
    from lecturekit.scaffold import create_project
    proj = create_project(tmp_path / "trial", title="A trial lecture")
    assert (proj / "_extensions" / "lecturekit" / "_extension.yml").exists()
    assert (proj / "anim" / "kit.py").exists()
    git = ["git", "-C", str(proj), "-c", "user.name=t", "-c", "user.email=t@example.org", "-c", "commit.gpgsign=false"]
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "scaffold"]):
        assert run([*git, *args]).returncode == 0
    r = run([sys.executable, "-m", "lecturekit.cli", "build", str(proj)])
    assert r.returncode == 0, (r.stdout + r.stderr)[-4000:]
    assert (proj / "_build" / "slides-live.html").exists()
    assert (proj / "_build" / "slides-study.pdf").exists()
    assert (proj / "assets" / "figures" / "example.tex").exists()     # make_assets ran as pre-render
    status = run([*git, "status", "--porcelain", "--untracked-files=all"])
    assert status.stdout == "", status.stdout


def test_scaffold_figure_is_what_make_assets_writes(tmp_path):
    """The scaffold ships assets/figures/example.tex so that a new project's first build changes no file; it must be
    exactly what the scaffold's make_assets.py writes."""
    pytest.importorskip("numpy")
    from lecturekit.scaffold import TEMPLATE_DIR, create_project
    proj = create_project(tmp_path / "p")
    (proj / "assets" / "figures" / "example.tex").unlink()
    r = run([sys.executable, str(proj / "make_assets.py")])
    assert r.returncode == 0, r.stderr
    assert (proj / "assets" / "figures" / "example.tex").read_bytes() == \
        (TEMPLATE_DIR / "assets" / "figures" / "example.tex").read_bytes()


def test_docs_ship_in_the_wheel():
    """`lk docs` lists the docs where the package is installed: every docs/*.md is force-included in the wheel."""
    import tomllib
    include = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["hatch"]["build"]["targets"]["wheel"][
        "force-include"]
    docs = {f"docs/{p.name}": f"lecturekit/docs/{p.name}" for p in (ROOT / "docs").glob("*.md")}
    assert docs and all(include.get(k) == v for k, v in docs.items())


def test_clips_index_schema():
    index = json.loads((FEATURES / "assets" / "clips" / "clips.json").read_text())
    rec = index["bar_bold"]
    for key in ("video", "still", "width", "height", "duration"):
        assert key in rec


def test_clips_index_existing():
    from lecturekit.clips import index_existing
    index = index_existing(KICKOFF)
    assert index["bar-bold"]["width"] == 1280 and index["bar-bold"]["height"] == 720
