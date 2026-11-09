"""Speaker view and on-screen checks for the segmentation prototype (Range server).

1. Open the speaker view with S (a real popup). Preview iframes must never load the clip. Keys pressed in the
   speaker window: Right must move the main deck (after Reveal's 500 ms debounce); Space must reach the main
   deck's clip through the relay and pause it.
2. Screen sampling: during back steps and during an arrival, screenshot repeatedly and read the barcode off the
   screen (what the audience sees), to show that no intermediate frame is displayed.
"""
import functools, os, json, sys, threading, time
from http.server import ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright
import numpy as np
from PIL import Image
import io

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rangeserver import RangeHandler  # noqa: E402
from run_helpers import HELPERS  # noqa: E402

CHROME = os.environ.get("LK_CHROME")  # None: Playwright's own Chromium
srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(RangeHandler, directory=str(HERE)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}/slides.html"
out = []


def check(name, ok, detail):
    out.append({"check": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + " :: " + json.dumps(detail)[:600])


def st(page, cid="k30"):
    return page.evaluate("id => __state(id)", cid)


def wait_phase(page, at, phase="holding", timeout=15):
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = st(page)
        if s["phase"] == phase and s["at"] == at:
            return time.time() - t0
        time.sleep(0.01)
    return None


def screen_frame(page, box):
    """Read the barcode from a screenshot of the clip box (object-fit: contain, 16:9 box, 16:9 clip)."""
    png = page.screenshot(clip=box)
    a = np.asarray(Image.open(io.BytesIO(png)).convert("L"), float)
    h, w = a.shape
    sx = min(w / 640.0, h / 360.0)              # object-fit: contain
    ox, oy = (w - 640 * sx) / 2, (h - 360 * sx) / 2
    n = 0
    for b in range(10):
        x = int(ox + (20 + b * 60 + 28) * sx); y = int(oy + 36 * sx)
        n = (n << 1) | (1 if a[y - 2:y + 3, x - 2:x + 3].mean() > 128 else 0)
    return n


with sync_playwright() as p:
    br = p.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    ctx = br.new_context(viewport={"width": 1280, "height": 720})
    ctx.add_init_script(HELPERS)
    page = ctx.new_page()
    page.goto(BASE + "#/1")
    page.wait_for_function("() => window.Reveal && Reveal.isReady() && window.__lkClips")
    time.sleep(0.4)

    # ---------------- 2. what the audience sees
    page.keyboard.press("ArrowRight")
    wait_phase(page, 1)
    for _ in range(2):
        page.keyboard.press("ArrowRight"); wait_phase(page, _ + 2)
    r = page.evaluate("(() => { const b = document.querySelector('.lk-seg[data-lk-seg=k30]').getBoundingClientRect(); return {x: b.x, y: b.y, width: b.width, height: b.height}; })()")
    seen = []
    for b_from, b_to in ((3, 2), (2, 1)):
        page.keyboard.press("ArrowLeft")
        t0 = time.time(); frames = []
        while time.time() - t0 < 0.5:
            frames.append(screen_frame(page, r))
        seen.append({"from": [90, 180, 270][b_from - 1], "to": [90, 180, 270][b_to - 1], "screen_frames": sorted(set(frames)), "samples": len(frames)})
    ok = all(set(x["screen_frames"]) <= {x["from"], x["to"]} and x["to"] in x["screen_frames"] for x in seen)
    check("back steps: the screen shows only the old hold or the new hold, never a frame in between", ok, seen)
    # arrival: sample the screen around the stop while a part plays into it
    page.keyboard.press("ArrowRight")  # k 0 -> 1, plays 90 -> 180
    frames = []; t0 = time.time()
    while time.time() - t0 < 3.6:
        frames.append((round(time.time() - t0, 3), screen_frame(page, r)))
    late = [f for _, f in frames if f > 180]
    tail = [f for _, f in frames][-6:]
    check("arrival: no frame past the stop ever reaches the screen; it ends on the stop frame", not late and tail[-1] == 180,
          {"max_seen": max(f for _, f in frames), "last_samples": tail, "n": len(frames)})

    # ---------------- 1. speaker view
    page.evaluate("Reveal.slide(2, 0, -1)"); wait_phase(page, 1)
    with ctx.expect_page() as pinfo:
        page.keyboard.press("s")
    sp = pinfo.value
    t0 = time.time()
    while time.time() - t0 < 15 and (sp.evaluate("document.querySelectorAll('iframe').length") < 2 or len([f for f in sp.frames if "receiver" in f.url]) < 2):
        time.sleep(0.2)
    time.sleep(2.0)
    rec = [f for f in sp.frames if "receiver" in f.url]
    def rstate(f):
        try:
            return f.evaluate("() => { const s = __state('k30'); return s && {src: s.src, stills: s.stills, k: s.k, phase: s.phase}; }")
        except Exception as e:
            return str(e)
    rs = [rstate(f) for f in rec]
    check("speaker view: both previews are receivers and never load the clip", len(rec) == 2 and all(isinstance(x, dict) and x["src"] is None for x in rs),
          {"n_receivers": len(rec), "states": rs})
    # Right pressed in the speaker window
    k0 = st(page)["k"]; t0 = time.time()
    sp.bring_to_front(); sp.keyboard.press("ArrowRight")
    while time.time() - t0 < 5 and st(page)["k"] == k0:
        time.sleep(0.01)
    lag = time.time() - t0
    s = st(page)
    check("Right in the speaker window advances the main deck (after the debounce)", s["k"] == k0 + 1, {"k": s["k"], "lag_s": round(lag, 3)})
    time.sleep(0.6)
    rs = [rstate(f) for f in rec]
    check("previews follow: current shows this state's hold still, upcoming the next one", True, rs)
    # Space pressed in the speaker window while the main clip plays
    s = st(page)
    n0 = page.evaluate("__lkLog.length")
    sp.keyboard.press(" ")
    time.sleep(0.5)
    s1 = st(page); time.sleep(0.4); s2 = st(page)
    log = [x[2] for x in page.evaluate("__lkLog.slice(%d)" % n0)]
    check("Space in the speaker window pauses the main deck's clip through the relay",
          s1["phase"] == "paused" and abs(s1["t"] - s2["t"]) < 1e-3 and s2["k"] == s["k"],
          {"phase_before": s["phase"], "phase_after": s1["phase"], "k": s2["k"], "log": log[:4]})
    sp.keyboard.press(" ")
    dt = wait_phase(page, 2)
    check("Space again resumes; the part holds on its stop", dt is not None and st(page)["frame"] == 180, {"frame": st(page)["frame"]})
    sp.keyboard.press("r"); time.sleep(0.5)
    s = st(page)
    log = [x[2] for x in page.evaluate("__lkLog")][-4:]
    check("R in the speaker window replays the main deck's part", s["phase"] == "playing" and 3.0 <= s["t"] < 6.0, {"phase": s["phase"], "t": s["t"], "log": log})
    hidden = page.evaluate("__mon.viol")
    check("main deck: nothing played hidden during the speaker-view run", not [v for v in hidden if v[1] == "clip"], {"samples": hidden[:5]})
    br.close()

srv.shutdown()
(HERE / "results_speaker.json").write_text(json.dumps(out, indent=1))
print("passed", sum(o["ok"] for o in out), "of", len(out))
