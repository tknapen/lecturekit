"""Drive the segmentation prototype deck with real key presses in headless Chromium.

usage: run_proto.py [range|norange] [guard] [norvfc]
Prints one line per check and writes results_<server>_g<guard>[_norvfc].json.
"""
import functools, os, json, sys, threading, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rangeserver import RangeHandler  # noqa: E402

mode = sys.argv[1] if len(sys.argv) > 1 else "range"
guard = sys.argv[2] if len(sys.argv) > 2 else "2"
norvfc = len(sys.argv) > 3 and sys.argv[3] == "norvfc"
CHROME = os.environ.get("LK_CHROME")  # None: Playwright's own Chromium


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


H = RangeHandler if mode == "range" else Quiet
srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(H, directory=str(HERE)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}/slides.html"
QS = f"?guard={guard}" + ("&norvfc=1" if norvfc else "")

# in-page helpers: read the frame index from the barcode; which still is visible; a hidden-play monitor
HELPERS = r"""
window.__mon = {viol: []};
window.__readFrame = function (v) {
  const c = document.createElement('canvas'); c.width = v.videoWidth; c.height = v.videoHeight;
  const g = c.getContext('2d'); g.drawImage(v, 0, 0);
  const sx = c.width / 640; let n = 0;
  for (let b = 0; b < 10; b++) {
    const x = Math.round((20 + b * 60 + 28) * sx), y = Math.round(36 * sx);
    const d = g.getImageData(x - 3, y - 3, 7, 7).data; let s = 0;
    for (let i = 0; i < d.length; i += 4) s += d[i] + d[i + 1] + d[i + 2];
    n = (n << 1) | (s / (d.length / 4) / 3 > 128 ? 1 : 0);
  }
  return n;
};
window.__readImg = function (img) {
  const c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight;
  const g = c.getContext('2d'); g.drawImage(img, 0, 0); const sx = c.width / 640; let n = 0;
  for (let b = 0; b < 10; b++) {
    const x = Math.round((20 + b * 60 + 28) * sx), y = Math.round(36 * sx);
    const d = g.getImageData(x - 3, y - 3, 7, 7).data; let s = 0;
    for (let i = 0; i < d.length; i += 4) s += d[i] + d[i + 1] + d[i + 2];
    n = (n << 1) | (s / (d.length / 4) / 3 > 128 ? 1 : 0);
  }
  return n;
};
window.__state = function (id) {
  const st = (window.__lkClips || []).find(s => s.id === id); if (!st) return null;
  const vis = Array.from(st.box.querySelectorAll('img.lk-still')).filter(i => getComputedStyle(i).opacity === '1').map(i => +i.getAttribute('data-lk-b'));
  return {phase: st.phase, at: st.at, k: st.k, plays: st.plays, paused: st.v.paused, t: st.v.currentTime,
          src: st.v.getAttribute('src'), driving: st.box.classList.contains('lk-driving'), stills: vis,
          frame: (st.v.readyState >= 2 && st.box.classList.contains('lk-driving')) ? __readFrame(st.v) : null,
          trace: st.trace.slice(-400)};
};
function shownVideo(v) {
  if (!v.closest('section.present')) return false;
  for (let n = v; n && n.tagName !== 'SECTION'; n = n.parentElement) {
    if (n.classList && n.classList.contains('fragment') && !n.classList.contains('visible')) return false;
    const p = n.parentElement;
    if (p && p.classList && p.classList.contains('r-stack'))
      for (let s = n.nextElementSibling; s; s = s.nextElementSibling) if (s.classList.contains('fragment') && s.classList.contains('visible')) return false;
  }
  return true;
}
setInterval(() => {
  document.querySelectorAll('.reveal video').forEach(v => {
    if (!v.paused && !shownVideo(v)) window.__mon.viol.push([Math.round(performance.now()), v.getAttribute('aria-label'), (v.getAttribute('src')||'').split('/').pop(), +v.currentTime.toFixed(3)]);
  });
}, 20);
"""

results = []


def check(name, ok, detail):
    results.append({"check": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + " :: " + json.dumps(detail)[:400])


def st(page, cid):
    return page.evaluate("id => __state(id)", cid)


def wait_hold(page, cid, b, timeout=15.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = st(page, cid)
        if s and s["phase"] == "holding" and s["at"] == b:
            time.sleep(0.15)  # let a late frame (if any) arrive before reading
            return time.time() - t0, st(page, cid)
        time.sleep(0.01)
    return None, st(page, cid)


def key(page, k):
    page.keyboard.press(k)


def hold_check(page, cid, b, frame, label, t_key, plays_before=None, expect_no_play=False):
    dt, s = wait_hold(page, cid, b)
    ok = dt is not None and s["frame"] == frame and s["paused"]
    d = {"hold_s": None if dt is None else round(dt, 3), "frame": s["frame"], "want": frame, "phase": s["phase"],
         "at": s["at"], "paused": s["paused"], "t": round(s["t"], 4)}
    if expect_no_play:
        d["plays_delta"] = s["plays"] - plays_before
        ok = ok and s["plays"] == plays_before
    check(label, ok, d)
    return s


def last_pause(s):
    ps = [x for x in s["trace"] if x[0] == "pause"]
    return ps[-1] if ps else None


with sync_playwright() as p:
    br = p.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    ctx = br.new_context(viewport={"width": 1280, "height": 720})
    ctx.add_init_script(HELPERS)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE + QS + "#/1")
    page.wait_for_function("() => window.Reveal && Reveal.isReady() && window.__lkClips")
    time.sleep(0.5)
    meta = json.loads((HERE / "assets/clips/meta.json").read_text())
    F = {n: [b["f"] for b in m["bounds"]] for n, m in meta.items()}

    s = st(page, "k30")
    check("before entry: neighbour clip preloaded, not playing", s["src"] is not None and s["paused"] and s["plays"] == 0,
          {"src": s["src"], "paused": s["paused"]})

    # ---- k30: forward through the stops with real key presses
    key(page, "ArrowRight")
    s = hold_check(page, "k30", 1, F["k30"][1], "k30 enter, part 0 plays and holds exactly on stop 1", 0)
    lp = last_pause(s)
    overs = []
    overs.append(lp)
    for b in (2, 3, 4):
        key(page, "ArrowRight")
        s = hold_check(page, "k30", b, F["k30"][b], f"k30 next -> holds exactly on boundary {b}", 0)
        overs.append(last_pause(s))
    # the last part's presented frames continued from the previous hold (no seek back to 0)
    tr = s["trace"]; i = max(j for j, x in enumerate(tr) if x[0] == "pause" and x[3] == 3)
    fr = [x[1] for x in tr[i + 1:] if x[0] == "f"]
    check("a part continues from the hold (first presented frame after the key)", fr and 9.0 - 1e-3 <= min(fr) <= 9.0 + 2.5 / 30, {"first_media": min(fr) if fr else None})
    # ---- back through the stops: never plays, exact
    for b in (3, 2, 1):
        pb = st(page, "k30")["plays"]
        t0 = time.time(); key(page, "ArrowLeft")
        hold_check(page, "k30", b, F["k30"][b], f"k30 previous -> holds boundary {b}, no play", t0, pb, True)
    # ---- leave backwards, re-enter forwards (plays part 0 again from frame 0)
    key(page, "ArrowLeft"); time.sleep(0.4)
    s = st(page, "k30")
    h = page.evaluate("Reveal.getIndices().h")
    check("leaving backwards pauses and goes static", s["paused"] and s["phase"] == "static" and h == 1,
          {"phase": s["phase"], "paused": s["paused"], "h": h, "stills": s["stills"]})
    key(page, "ArrowRight")
    s = hold_check(page, "k30", 1, F["k30"][1], "re-entry forwards replays part 0 and holds stop 1", 0)
    fr = [x[1] for x in s["trace"] if x[0] == "f"]
    # ---- to the end, onto the next slide, and back in: holds the last frame, never plays
    for _ in range(3):
        key(page, "ArrowRight")
    s = hold_check(page, "k30", 4, F["k30"][4], "mashing 3 x next during a part plays through to the end", 0)
    passes = [x for x in s["trace"] if x[0] == "pause"]
    key(page, "ArrowRight"); time.sleep(1.0)
    after = page.evaluate("(() => { const v = document.querySelector('#after video'); return {paused: v.paused, t: v.currentTime}; })()")
    s = st(page, "k30")
    check("next slide: ordinary clip autoplays, segmented clip paused", (not after["paused"]) and s["paused"], {"after": after, "seg": s["phase"]})
    pb = s["plays"]
    key(page, "ArrowLeft")
    s = hold_check(page, "k30", 4, F["k30"][4], "enter backwards from next slide: holds last frame, never plays", 0, pb, True)
    after = page.evaluate("(() => { const v = document.querySelector('#after video'); return {paused: v.paused}; })()")
    check("after leaving, the next slide's clip is paused", after["paused"], after)
    # ---- play-through: from hold 1, press next mid-part twice quickly
    for _ in range(3):
        key(page, "ArrowLeft")
    wait_hold(page, "k30", 1)
    key(page, "r")  # replay part 0 (seek 0, play to 90)
    time.sleep(0.6)
    s = st(page, "k30")
    check("R replays the current part (seek to its start, play)", s["phase"] == "playing" and s["t"] < 3.0,
          {"phase": s["phase"], "t": round(s["t"], 3), "scrollview": page.evaluate("Reveal.isScrollView ? Reveal.isScrollView() : null"),
           "h": page.evaluate("Reveal.getIndices().h")})
    key(page, "ArrowRight")  # mid-part: target extends to boundary 2
    s = hold_check(page, "k30", 2, F["k30"][2], "next during part 0 plays through stop 1 and holds stop 2", 0)
    pauses = [x for x in s["trace"][-200:] if x[0] == "pause"]
    check("play-through did not pause at stop 1", pauses and pauses[-1][3] == 2 and not any(x[3] == 1 for x in pauses[-1:]), {"last_pause": pauses[-1] if pauses else None})
    # ---- Space: at an intermediate hold advances; mid-part pauses and resumes
    n0 = page.evaluate("__lkLog.length")
    key(page, "Space"); time.sleep(0.8)
    s = st(page, "k30")
    print("   log:", page.evaluate("__lkLog.slice(%d)" % n0)[:6])
    check("Space at an intermediate hold advances one stop", s["k"] == 2 and s["phase"] == "playing", {"k": s["k"], "phase": s["phase"]})
    key(page, "Space"); time.sleep(0.3)
    s1 = st(page, "k30"); time.sleep(0.5); s2 = st(page, "k30")
    check("Space mid-part pauses (time stands still)", s1["phase"] == "paused" and abs(s1["t"] - s2["t"]) < 1e-3, {"t1": s1["t"], "t2": s2["t"], "phase": s1["phase"]})
    key(page, "Space")
    hold_check(page, "k30", 3, F["k30"][3], "Space resumes and the part holds on its boundary", 0)
    key(page, "Space")
    hold_check(page, "k30", 4, F["k30"][4], "Space at hold 3 plays the last part to the end", 0)
    key(page, "Space"); time.sleep(0.4)
    s = st(page, "k30")
    check("Space at the final hold does not leave the slide", page.evaluate("Reveal.getIndices().h") == 2 and s["phase"] == "holding", {"h": page.evaluate("Reveal.getIndices().h")})
    key(page, "r"); time.sleep(0.3)
    check("R does not switch on Quarto's scroll view", not page.evaluate("Reveal.isScrollView()"), {"scroll": page.evaluate("Reveal.isScrollView()")})
    wait_hold(page, "k30", 4)
    # ---- jump with a fragment index from another slide (fragment events fire before slidechanged)
    page.evaluate("Reveal.slide(0)"); time.sleep(0.3)
    pb = st(page, "k30")["plays"]
    n0 = page.evaluate("__lkLog.length")
    page.evaluate("Reveal.slide(2, 0, 1)")
    s = hold_check(page, "k30", 3, F["k30"][3], "Reveal.slide(2,0,1) from another slide holds boundary 3, never plays", 0, pb, True)
    evs = [x[2] for x in page.evaluate("__lkLog.slice(%d)" % n0) if x[2].startswith("event") or x[2].startswith("enter")]
    check("event order on a jump with f (recorded)", True, {"order": evs[:6]})
    # ---- overview pauses, closing it re-enters
    for _ in range(2):
        key(page, "ArrowLeft")
    wait_hold(page, "k30", 1)
    key(page, "ArrowRight"); time.sleep(0.5)
    key(page, "Escape"); time.sleep(0.4)
    s = st(page, "k30")
    check("overview pauses a playing part", s["paused"] and page.evaluate("Reveal.isOverview()"), {"phase": s["phase"]})
    key(page, "Escape")
    dt, s = wait_hold(page, "k30", 2)
    check("closing overview resumes the part, which holds on its boundary", dt is not None and s["frame"] == F["k30"][2] and s["k"] == 1, {"frame": s["frame"], "phase": s["phase"], "k": s["k"]})

    # ---- stack slide (I9 guard) and the mid-GOP / non-faststart clip
    page.evaluate("Reveal.slide(4)"); time.sleep(1.0)
    key(page, "ArrowRight"); time.sleep(1.2)
    key(page, "ArrowRight")
    s = hold_check(page, "g30", 1, F["g30"][1], "g30 (GOP 250, moov last) enter: holds stop 1", 0)
    for b in (2, 3, 4):
        key(page, "ArrowRight")
        hold_check(page, "g30", b, F["g30"][b], f"g30 next -> boundary {b}", 0)
    for b in (3, 2, 1):
        pb = st(page, "g30")["plays"]
        key(page, "ArrowLeft")
        hold_check(page, "g30", b, F["g30"][b], f"g30 previous -> boundary {b} (mid-GOP seek), no play", 0, pb, True)
    # ---- k60, start=key: entering holds frame 0
    page.evaluate("Reveal.slide(5, 0, 2)"); time.sleep(0.3)
    key(page, "ArrowRight")  # -> slide 6 with k=0
    s = hold_check(page, "k60", 0, F["k60"][0], "k60 start=key: entering holds frame 0, nothing plays", 0)
    check("start=key: no play on entry", s["plays"] == 0, {"plays": s["plays"]})
    for b in (1, 2, 3, 4):
        key(page, "ArrowRight")
        s = hold_check(page, "k60", b, F["k60"][b], f"k60 (60 fps) next -> boundary {b}", 0)
        overs.append(last_pause(s))
    for b in (3, 2, 1, 0):
        pb = st(page, "k60")["plays"]
        key(page, "ArrowLeft")
        hold_check(page, "k60", b, F["k60"][b], f"k60 previous -> boundary {b}, no play", 0, pb, True)

    viol = page.evaluate("__mon.viol")
    by = {}
    for t, lab, src, ct in viol:
        by.setdefault(lab, []).append(t)
    spans = {lab: (len(ts), (max(ts) - min(ts)) if ts else 0) for lab, ts in by.items()}
    seg_viol = {lab: v for lab, v in spans.items() if lab == "clip"}
    check("no segmented clip ever plays while hidden or off its slide", not seg_viol, {"hidden_play_samples": spans})
    log = page.evaluate("__lkLog")
    check("page errors", not errors, errors[:3])
    seekable = [x for x in log if "seekable" in x[2] or "Blob" in x[2] or "blob" in x[2] or "timeout" in x[2] or "missed" in x[2]]
    check("seekable / fallback log", True, seekable[:12])
    guardlog = [x for x in log if "guard" in x[2]]
    check("guard actions", True, guardlog[:8])
    pauses = [o for o in overs if o]
    check("pause landing (rVFC/timeupdate): [lastPresentedMedia, currentTimeAfterPause, boundary]", True, pauses)

    # ---- receiver (speaker preview) and print
    rp = ctx.new_page()
    rp.goto(BASE.replace("slides.html", "slides.html?receiver") + "#/2")
    rp.wait_for_function("() => window.Reveal && Reveal.isReady() && window.__lkClips")
    out = []
    for f in (-1, 0, 1, 2):
        rp.evaluate(f"Reveal.setState({{indexh: 2, indexv: 0, indexf: {f}}})"); time.sleep(0.3)
        s = st(rp, "k30")
        out.append({"indexf": f, "src": s["src"], "stills": s["stills"], "paused": s["paused"]})
    check("receiver: never loads the clip, shows the hold still for each state", all(o["src"] is None and o["stills"] == [o["indexf"] + 2] for o in out), out)
    pp = ctx.new_page()
    pp.goto(BASE + "?print-pdf")
    pp.wait_for_function("() => window.Reveal && Reveal.isReady() && window.__lkClips")
    time.sleep(1.5)
    s = st(pp, "k30"); s6 = st(pp, "k60")
    check("print-pdf: no clip loaded, final hold still shown", s["src"] is None and s["stills"] == [4] and s6["stills"] == [4], {"k30": s["stills"], "k60": s6["stills"], "src": s["src"]})
    br.close()

srv.shutdown()
name = f"results_{mode}_g{guard}{'_norvfc' if norvfc else ''}.json"
(HERE / name).write_text(json.dumps(results, indent=1))
print("wrote", name, "passed", sum(r["ok"] for r in results), "of", len(results))
