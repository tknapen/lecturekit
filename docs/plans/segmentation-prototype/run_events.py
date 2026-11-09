"""Event order on keyboard backward entry, and the cue state Reveal shows at slidechanged."""
import functools, os, sys, threading, time, json
from http.server import ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rangeserver import RangeHandler
from run_helpers import HELPERS
srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(RangeHandler, directory=str(HERE)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}/slides.html"
SPY = """window.__ev = []; window.addEventListener('load', () => { const r = () => {
  ['slidechanged','fragmentshown','fragmenthidden'].forEach(n => Reveal.on(n, e => {
    const s = Reveal.getCurrentSlide();
    __ev.push([n, Reveal.getIndices().h, s.querySelectorAll('.lk-cue.visible').length, s.querySelectorAll('.lk-cue.current-fragment').length]); })); };
  if (Reveal.isReady()) r(); else Reveal.on('ready', r); });"""
with sync_playwright() as p:
    br = p.chromium.launch(executable_path=os.environ.get("LK_CHROME"))
    ctx = br.new_context(viewport={"width": 1280, "height": 720}); ctx.add_init_script(HELPERS); ctx.add_init_script(SPY)
    page = ctx.new_page(); page.goto(BASE + "#/3")
    page.wait_for_function("() => window.Reveal && Reveal.isReady() && window.__lkClips"); time.sleep(0.5)
    page.evaluate("__ev.length = 0"); page.keyboard.press("ArrowLeft"); time.sleep(0.5)
    print("keyboard back-entry [event, h, visible cues, current cues]:", page.evaluate("__ev"))
    page.evaluate("Reveal.slide(1)"); time.sleep(0.3)
    page.evaluate("__ev.length = 0"); page.keyboard.press("ArrowRight"); time.sleep(0.3)
    print("keyboard forward entry:", page.evaluate("__ev"))
    page.evaluate("Reveal.slide(5)"); time.sleep(0.3)
    page.evaluate("__ev.length = 0"); page.evaluate("Reveal.setState({indexh: 2, indexv: 0, indexf: 0})"); time.sleep(0.3)
    print("setState from slide 5 to (2, f=0):", page.evaluate("__ev"), page.evaluate("__state('k30').phase"), page.evaluate("__state('k30').at"))
    br.close()
srv.shutdown()
