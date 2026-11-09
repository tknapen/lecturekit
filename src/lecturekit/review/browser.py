"""A headless browser on a built live deck, shared by shoot, frags and measure.

The deck is served from a local HTTP server on loopback rather than opened from disk: fonts and clips do not load
reliably from file:// URLs. Transitions are switched off before anything is measured, so a screenshot taken right
after a slide change shows that slide alone. Slide numbers are 1-based, as the foot shows them (the title slide is 1).
"""

from __future__ import annotations

import contextlib
import functools
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FRAME = (1280, 720)


def _browsers_path() -> None:
    # a preinstalled Playwright browser set (e.g. /opt/pw-browsers) is honoured
    if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ and Path("/opt/pw-browsers").exists():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/pw-browsers"


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D401
        pass


@contextlib.contextmanager
def served(deck_html: Path):
    """Serve the deck's directory on loopback; yields the deck's URL."""
    deck_html = deck_html.resolve()
    if deck_html.suffix != ".html" and deck_html.is_dir():
        for cand in ("slides-live.html", "index.html"):
            if (deck_html / cand).exists():
                deck_html = deck_html / cand
                break
    handler = functools.partial(_Quiet, directory=str(deck_html.parent))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/{deck_html.name}"
    finally:
        server.shutdown()
        server.server_close()


@contextlib.contextmanager
def deck_page(deck_html: Path, scale: int = 1):
    """Open the deck and wait for Reveal; yields (page, errors), errors being a list that collects page errors and
    failed requests while the page is used."""
    _browsers_path()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("playwright is not installed: pip install lecturekit[review] && playwright install chromium") from exc
    errors: list[str] = []
    with served(deck_html) as url, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": FRAME[0], "height": FRAME[1]}, device_scale_factor=scale)
        page.on("pageerror", lambda e: errors.append(f"page error: {e}"))
        page.on("response", lambda r: errors.append(f"{r.status} {r.url}") if r.status >= 400 else None)
        page.goto(url)
        page.wait_for_function("() => window.Reveal && Reveal.isReady()")
        page.evaluate("() => { Reveal.configure({transition: 'none', backgroundTransition: 'none'}); return document.fonts.ready; }")
        page.wait_for_timeout(200)
        try:
            yield page, errors
        finally:
            browser.close()


def slide_count(page) -> int:
    return int(page.evaluate("() => Reveal.getTotalSlides()"))


def goto(page, number: int, fragment: int | None = None, settle: int = 250) -> None:
    """Show slide `number` (1-based) with all fragments shown, or up to fragment index `fragment` (-1: none)."""
    if fragment is None:
        page.evaluate("(i) => Reveal.slide(i, 0, 9999)", number - 1)
    else:
        page.evaluate("([i, f]) => Reveal.slide(i, 0, f)", [number - 1, fragment])
    page.wait_for_timeout(settle)


def next_fragment(page) -> bool:
    """Advance one fragment; False when the slide has no more."""
    has = page.evaluate("() => Reveal.availableFragments().next")
    if has:
        page.evaluate("() => Reveal.nextFragment()")
        page.wait_for_timeout(450)   # past the r-stack fade (250 ms), so a replaced step reads as hidden
    return bool(has)


def slide_info(page) -> dict:
    """Title, role, planned seconds and fragment count of the current slide."""
    return page.evaluate(
        """() => {
          const s = Reveal.getCurrentSlide();
          const h = s.querySelector(':scope > h1, :scope > h2, :scope > h3');
          return {
            title: h ? h.textContent.trim() : '',
            role: s.getAttribute('data-role'),
            timing: s.getAttribute('data-timing'),
            fragments: s.querySelectorAll('.fragment').length,
            isTitle: s.id === 'title-slide' || s.classList.contains('title-slide')
          };
        }"""
    )


def shown_js() -> str:
    """JS predicate: is an element shown (not in a hidden fragment or a replaced r-stack step)."""
    return """
      function shown(el) {
        for (var n = el; n && n.tagName !== 'SECTION'; n = n.parentElement) {
          var cs = getComputedStyle(n);
          if (cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) === 0) return false;
          if (n.classList && n.classList.contains('fragment') && !n.classList.contains('visible')) return false;
        }
        return true;
      }"""
