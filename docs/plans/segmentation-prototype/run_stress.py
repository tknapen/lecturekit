"""Random key mashing on the segmented slide, and a blocked play() (autoplay refused)."""
import functools, os, json, random, sys, threading, time
from http.server import ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rangeserver import RangeHandler  # noqa: E402
from run_helpers import HELPERS  # noqa: E402

srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(RangeHandler, directory=str(HERE)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}/slides.html"
F = [0, 90, 180, 270, 359]
out = []


def check(name, ok, detail):
    out.append({"check": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + " :: " + json.dumps(detail)[:500])


def settle(page, timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = page.evaluate("__state('k30')")
        h = page.evaluate("Reveal.getIndices().h")
        if h != 2 or s["phase"] in ("holding", "static"):
            time.sleep(0.2)
            return h, page.evaluate("__state('k30')"), page.evaluate("Reveal.getIndices().f")
        time.sleep(0.05)
    return page.evaluate("Reveal.getIndices().h"), page.evaluate("__state('k30')"), None


with sync_playwright() as p:
    br = p.chromium.launch(executable_path=os.environ.get("LK_CHROME"),
                           args=["--autoplay-policy=no-user-gesture-required"])
    ctx = br.new_context(viewport={"width": 1280, "height": 720})
    ctx.add_init_script(HELPERS)
    page = ctx.new_page()
    page.goto(BASE + "#/2")
    page.wait_for_function("() => window.Reveal && Reveal.isReady() && window.__lkClips")
    time.sleep(0.5)
    for seed in range(6):
        rnd = random.Random(seed)
        seq = []
        for _ in range(16):
            k = rnd.choice(["ArrowRight", "ArrowRight", "ArrowLeft", "Space"])
            seq.append(k); page.keyboard.press(k); time.sleep(rnd.uniform(0, 0.15))
        # come back to the clip slide if the sequence left it
        h = page.evaluate("Reveal.getIndices().h")
        if h != 2:
            page.evaluate("Reveal.slide(2, 0, %d)" % (2 if h > 2 else -1))
        h, s, f = settle(page)
        if s["phase"] == "paused":       # the sequence ended on Space mid-part: a legal state; resume it
            page.keyboard.press("Space"); h, s, f = settle(page)
        want_b = s["k"] + 1
        k_dom = page.evaluate("document.querySelectorAll('.lk-cue[data-lk-for=k30].visible').length")
        ok = h == 2 and s["k"] == k_dom and s["phase"] == "holding" and s["at"] == want_b and s["frame"] == F[want_b]
        check(f"mash seed {seed}: settles on the hold for Reveal's state, exact frame", ok,
              {"seq": "".join({"ArrowRight": ">", "ArrowLeft": "<", "Space": "_"}[x] for x in seq),
               "k_runtime": s["k"], "k_dom": k_dom, "at": s["at"], "frame": s["frame"], "phase": s["phase"]})
    viol = [v for v in page.evaluate("__mon.viol") if v[1] == "clip"]
    check("mashing: no segmented clip played hidden", not viol, viol[:4])

    # play() refused (autoplay policy): the runtime must not show a hold the room has not seen
    page.evaluate("Reveal.slide(1)"); time.sleep(0.3)
    page.evaluate("""(() => { window.__realPlay = HTMLMediaElement.prototype.play;
        HTMLMediaElement.prototype.play = function () { return Promise.reject(new DOMException('blocked', 'NotAllowedError')); }; })()""")
    page.keyboard.press("ArrowRight"); time.sleep(1.0)
    s = page.evaluate("__state('k30')")
    check("play() refused on entry: blocked, showing the start still of part 0, not a hold", s["phase"] == "blocked" and s["stills"] == [0],
          {"phase": s["phase"], "stills": s["stills"]})
    page.evaluate("(() => { HTMLMediaElement.prototype.play = window.__realPlay; })()")
    page.keyboard.press("Space")
    t0 = time.time()
    while time.time() - t0 < 6 and page.evaluate("__state('k30').phase") != "holding":
        time.sleep(0.05)
    s = page.evaluate("__state('k30')")
    check("after unblocking, Space plays part 0 and it holds on stop 1", s["phase"] == "holding" and s["frame"] == 90, {"phase": s["phase"], "frame": s["frame"]})
    br.close()
srv.shutdown()
(HERE / "results_stress.json").write_text(json.dumps(out, indent=1))
print("passed", sum(o["ok"] for o in out), "of", len(out))
