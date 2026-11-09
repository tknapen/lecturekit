# Installation

A build needs Quarto, a TeX distribution with XeLaTeX, and Python 3.11 or later with the `lecturekit` package; the review tools need Playwright's Chromium; the clips need Manim, and manim8 clips need Python 3.12 or later. macOS and Linux are supported. `tools/install.sh` does the Linux and macOS steps below in one go and ends by building both example decks; this page says what it does and what to do by hand.

## Quarto

Quarto 1.11 or later, from quarto.org (the installer fetches 1.11.9 when `quarto` is not on the path). Verify it:

```sh
quarto check
```

## TeX

The study PDF and every TikZ figure compile with XeLaTeX and fontspec. The fonts are bundled with the extension and loaded by file, so no font package is needed. Two ways to get TeX.

TinyTeX, on macOS or Linux, then the packages the formats use:

```sh
quarto install tinytex
tlmgr install beamer adjustbox etoolbox ragged2e pgf xcolor standalone fontspec unicode-math textcase lm
```

The TinyTeX installer fetches from api.github.com; where that is blocked, use the distribution's packages instead. On Debian or Ubuntu:

```sh
sudo apt-get install texlive-xetex texlive-latex-extra texlive-fonts-recommended lmodern fonts-lmodern
```

The formats set `latex-auto-install: false`, so a missing package is reported during a build rather than fetched.

## Python

Python 3.11 or later. From a clone of this repository, with `uv` (astral.sh/uv):

```sh
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

or from PyPI:

```sh
pip install "lecturekit[review,figures]"
```

The command is `lk`, with `lecturekit` as an alias; `lk version` prints the package and extension versions and where Quarto was found. The `review` extra brings Playwright and the image tools for `lk review`; `figures` brings numpy, matplotlib, Pillow and PyMuPDF for `make_assets.py` and the figure conversion; `dev` brings both and pytest.

The review tools drive a headless Chromium:

```sh
playwright install chromium
```

A preinstalled browser set is honoured through `PLAYWRIGHT_BROWSERS_PATH` (a set in `/opt/pw-browsers` is picked up without it).

SVG conversion. The TikZ filter turns each compiled figure into an SVG for the live deck with PyMuPDF (AGPL, used at build time only; nothing of it is distributed), falling back to poppler's `pdftocairo`. One of them must be present: `pip install pymupdf`, or `apt-get install poppler-utils`, or `brew install poppler`.

Clips. `lk clips` renders Manim scenes on the kit:

```sh
pip install "lecturekit[clips]"
```

brings Manim Community 0.22 with Pillow below 11.3 and `imageio-ffmpeg`. Manim needs the Cairo and Pango development headers on the machine (`libcairo2-dev libpango1.0-dev pkg-config` on Debian and Ubuntu, `cairo pango pkg-config` through Homebrew).

## manim8

manim8 is the second clip producer (CLIPS.md). It needs Python 3.12 or later; the extra installs nothing on an older Python. With pip:

```sh
pip install "lecturekit[manim8]"
```

or with uv, in a project's environment:

```sh
uv pip install "lecturekit[manim8]"
```

The extra installs manim8 and its contracts package, `manim8-core`, from manim8's `v0.1.0a0` tag on GitHub (pip needs both named, since it does not read uv's workspace sources; the extra names both). manim8 depends on the `uv` package, so a pip install brings the uv that manim8 uses to build each family's render environment; a uv already on the path is used as well. The render environment holds Manim and manim8's bridge, at the same commit as the control plane, and is built once per family, on the first `lk clips` that needs it (or by `scianim family env sync clips/families/<family>`); Manim's Cairo and Pango headers are needed for it as above. Then:

```sh
lk new my-lecture --manim8        # clips/ as a manim8 workspace, the bridged styles, a starter project
scianim skill install             # the manim8 skill for the agent that turns a brief into a storyboard
```

`scianim doctor` checks the control plane, and `scianim doctor --family clips/families/<family>` a family's render environment.

## An existing Quarto project

```sh
quarto add tknapen/lecturekit
```

vendors the extension alone into the project's `_extensions/lecturekit/`, which is enough for `quarto render` with the two formats; `pip install lecturekit` adds `lk`, the kits and the review tools. `lk new --vendor-only <dir>` does the same from the installed package.

## Verify

```sh
lk build examples/kickoff
```

prints the timing report (15 of 15 minutes) and writes `examples/kickoff/_build/slides-live.html` and `slides-study.pdf`. Open both. Then:

```sh
lk review shoot examples/kickoff/_build/slides-live.html --sheet
lk review overflow examples/kickoff
```

write one PNG per slide and a contact sheet to `examples/kickoff/review/shots/` and read the Beamer log. Without the Python package, `cd examples/kickoff && quarto render` builds the same outputs; the timing report prints, the review tools do not run. The engine's own tests are `pytest -q` from the repository root; they need the whole toolchain.
