"""Which speaker notes does the speaker view show after a backward entry onto a segmented slide?"""
import functools, os, sys, threading, time
from http.server import ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rangeserver import RangeHandler
from run_helpers import HELPERS
fix = len(sys.argv) > 1 and sys.argv[1] == "fix"
FIX = """window.addEventListener('load', () => { const r = () => Reveal.on('slidechanged', () => {
  const s = Reveal.getCurrentSlide();
  if (s.querySelector('.lk-cue.visible')) setTimeout(() => Reveal.dispatchEvent({ type: 'resumed' }), 0); });
  if (Reveal.isReady()) r(); else Reveal.on('ready', r); });"""
srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(RangeHandler, directory=str(HERE)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}/slides.html"
with sync_playwright() as p:
    br = p.chromium.launch(executable_path=os.environ.get("LK_CHROME"))
    ctx = br.new_context(viewport={"width": 1280, "height": 720}); ctx.add_init_script(HELPERS)
    if fix: ctx.add_init_script(FIX)
    page = ctx.new_page(); page.goto(BASE + "#/3")
    page.wait_for_function("() => window.Reveal && Reveal.isReady() && window.__lkClips")
    with ctx.expect_page() as pinfo:
        page.keyboard.press("s")
    sp = pinfo.value; time.sleep(4)
    notes = lambda: sp.evaluate("(document.querySelector('.speaker-controls-notes .value') || {}).textContent || ''").strip()[:60]
    page.bring_to_front(); page.keyboard.press("ArrowLeft"); time.sleep(1.0)
    print("fix" if fix else "no fix", "| after backward entry (k=3, holding the end):", repr(notes()))
    page.keyboard.press("ArrowLeft"); time.sleep(0.6)
    print("   after one more Left (k=2):", repr(notes()))
    br.close()
srv.shutdown()
