#!/usr/bin/env bash
# lecturekit installer for macOS and Linux: Quarto, TeX, the Python package,
# Playwright's Chromium for the review tools, then a build of the feature deck.
# Nothing is added to your shell; the virtual environment lives in .venv.
set -euo pipefail

QUARTO_VERSION="${QUARTO_VERSION:-1.11.9}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

say() { printf '\n== %s\n' "$*"; }

say "Quarto"
if ! command -v quarto >/dev/null 2>&1; then
  OS="$(uname -s)"; ARCH="$(uname -m)"
  case "$OS-$ARCH" in
    Linux-x86_64)  PKG="quarto-${QUARTO_VERSION}-linux-amd64.tar.gz" ;;
    Linux-aarch64) PKG="quarto-${QUARTO_VERSION}-linux-arm64.tar.gz" ;;
    Darwin-*)      PKG="quarto-${QUARTO_VERSION}-macos.tar.gz" ;;
    *) echo "install Quarto ${QUARTO_VERSION} from https://quarto.org/docs/download/ and rerun"; exit 1 ;;
  esac
  URL="https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VERSION}/${PKG}"
  mkdir -p "$HOME/.local/opt/quarto" "$HOME/.local/bin"
  curl -fsSL "$URL" | tar xz -C "$HOME/.local/opt/quarto" --strip-components=1
  ln -sf "$HOME/.local/opt/quarto/bin/quarto" "$HOME/.local/bin/quarto"
  export PATH="$HOME/.local/bin:$PATH"
  echo "quarto installed in $HOME/.local/opt/quarto (add $HOME/.local/bin to PATH)"
fi
quarto --version

say "TeX"
if ! command -v xelatex >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    echo "Debian/Ubuntu: installing TeX Live packages with apt (needs sudo)"
    sudo apt-get install -y --no-install-recommends texlive-xetex texlive-latex-extra texlive-fonts-recommended \
      fonts-texgyre fonts-texgyre-math fonts-roboto lmodern fonts-lmodern
  else
    quarto install tinytex --no-prompt
    tlmgr install beamer adjustbox collectbox etoolbox ragged2e pgf xcolor standalone fontspec unicode-math tex-gyre tex-gyre-math varwidth || true
  fi
fi

say "Python environment"
if command -v uv >/dev/null 2>&1; then
  uv venv .venv
  uv pip install -p .venv/bin/python -e ".[dev]"
else
  python3 -m venv .venv
  .venv/bin/pip install -e ".[dev]"
fi

say "Chromium for the review tools"
if [ -d /opt/pw-browsers ]; then
  echo "using the Playwright browsers in /opt/pw-browsers (set PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers)"
else
  .venv/bin/playwright install chromium
fi

say "Building the feature deck"
ln -sfn ../../_extensions examples/features/_extensions
.venv/bin/lk build examples/features

say "Done"
echo "activate with: source .venv/bin/activate"
echo "then: lk review shoot examples/features/_build/slides-live.html --sheet"
