# Installation

A build needs Quarto, a TeX distribution with XeLaTeX, Python 3.11 or later with the `lecturekit` package, and, for the review tools, Playwright's Chromium. macOS and Linux are supported. This page records what worked.

## Quarto

Quarto 1.11 or later, from quarto.org. The extension declares `quarto-required: ">=1.6.0"`, but the formats are developed against 1.11 and that is what to install. Verify the installation:

```sh
quarto check
```

## TeX

The study PDF and every TikZ figure compile with `xelatex` and `fontspec`. Two ways to get them.

TinyTeX, on macOS or Linux:

```sh
quarto install tinytex
```

TinyTeX's installer fetches from api.github.com; on a machine without that access, use the system packages below. The formats set `latex-auto-install: false`, so a missing package is reported during a build, not fetched; with TinyTeX, install what the formats use once: `tlmgr install beamer pgf adjustbox collectbox standalone etoolbox ragged2e ms fontspec unicode-math xcolor microtype upquote lmodern tex-gyre tex-gyre-math roboto`. Some of these are already in TinyTeX; `tlmgr` skips them.

Debian or Ubuntu, with the distribution's packages:

```sh
sudo apt-get install texlive-xetex texlive-latex-extra texlive-fonts-recommended \
  fonts-texgyre fonts-texgyre-math fonts-roboto lmodern
```

This is the combination that built the example on the machine this repository was made on.

Fonts. The paper preset names TeX Gyre Heros and TeX Gyre Pagella with `source: system`, so they must be visible to fontconfig (`fc-list | grep "TeX Gyre"`); `fonts-texgyre` provides them on Debian and Ubuntu, and TinyTeX's `tex-gyre` package on macOS once fontconfig sees TeX's font directory. The dark preset names Roboto (`fonts-roboto`, or Google Fonts on macOS). When the font files ship with the extension (`_extensions/lecturekit/fonts/`, see its README) and `_brand.yml` uses `source: file`, this dependency goes away.

## Python

Python 3.11 or later and `uv` (astral.sh/uv). From a clone of this repository:

```sh
uv venv
source .venv/bin/activate
uv pip install -e ".[review,clips]"
playwright install chromium
```

`pip install lecturekit` installs a release instead. The command is `lk`, with `lecturekit` as an alias. The `review` extra brings Playwright and the image tools for `lk review`; `clips` brings Manim for `lk clips`. `playwright install chromium` fetches the browser that `lk review shoot`, `frags` and `measure` drive.

The TikZ filter converts each compiled figure to SVG for the live deck with PyMuPDF, falling back to poppler's `pdftocairo`, then `dvisvgm`. One of them must be present: `uv pip install pymupdf`, or `apt-get install poppler-utils`, or `brew install poppler`.

## Verify

```sh
lk build examples/features
```

The build prints the timing report and writes `examples/features/_build/slides-live.html` and `slides-study.pdf`. Open both. Then:

```sh
lk review shoot examples/features/_build/slides-live.html --out examples/features/review
```

writes one PNG per slide. Without the Python package, `cd examples/features && quarto render` builds the same outputs; the report prints, the review tools do not run.

## Not in this repository yet

The TikZ kit (`lecturekit.tikz`), the Manim kit (`lecturekit.manim`) and the kickoff example deck are being extracted from the course project. The features example builds without them.
