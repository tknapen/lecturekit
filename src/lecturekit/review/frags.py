"""`lk review frags`: slides through their fragments, step by step.

    lk review frags _build/slides-live.html                  # every slide that has fragments
    lk review frags _build/slides-live.html --slides 4 6     # these slides (1-based, as the foot shows them)

Per step: a PNG (`review/frags/s04-f1.png`), which fragments are visible, where the images sit, and whether a clip
is shown and playing. Flags, and exits 1 on:

* a clip's `.fragment` inside the clip's `.live-only` box rather than around it (`.live-only > .fragment > .movie`):
  the box keeps its place below the title while the clip is hidden, so the hidden clip covers the slide. The
  prescribed form is `.fragment > .live-only > .movie`; a `clip=` movie, which the filter boxes itself, may sit in a
  `.fragment` directly; a step of an `.r-stack` sequence (`.live-only > .r-stack > .fragment > .movie`) is stacked in
  the r-stack's box and passes;
* a clip that plays while it is hidden (in a hidden fragment, or in an r-stack step a later one covers);
* a clip in parts (stops=) that does not hold exactly on the frame its state expects, whose pause lands after the
  stop, or that plays when the slide is entered backwards or by a jump.

A clip in parts is walked with real key presses: per step, the hold expected (frame and presentation time), the
frame on screen, the last frame shown before the pause and the time from the key to the hold; then a backward entry
from the next slide, which must hold the last frame without playing, and a jump onto the first cue, which must hold
without playing. A hold whose notes have no "Ask:" is reported (POLICY.md: the prompt is the first line of the notes).

It also notes an r-stack whose steps have different sizes. The study PDF is not affected by fragments: Beamer gets
no overlay from them, and `.live-only` content is not in it.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from .browser import deck_page, goto, next_fragment, shown_js, slide_count, slide_info

STEP_JS = """
  () => {
    """ + shown_js() + """
    const s = Reveal.getCurrentSlide();
    const frags = [...s.querySelectorAll('.fragment')];
    const vis = frags.map(f => f.classList.contains('visible') ? 1 : 0).join('');
    const imgs = [...s.querySelectorAll('img')].filter(shown)
      .map(e => { const r = e.getBoundingClientRect(); return [(e.getAttribute('src') || '').split('/').pop().slice(0, 18), Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; });
    const vids = [...s.querySelectorAll('video')].map(v => ({ shown: shown(v), paused: v.paused, src: (v.getAttribute('src') || '').split('/').pop().split('?')[0] }));
    // a fragment whose clip has no .live-only box between the fragment and the video (at the fragment or inside it);
    // an r-stack step is stacked in the r-stack's box
    const misplaced = frags.filter(f => {
      if (f.parentElement && f.parentElement.classList.contains('r-stack')) return false;
      return [...f.querySelectorAll('video')].some(v => { const box = v.closest('.live-only'); return !box || !f.contains(box); });
    }).length;
    const hiddenPlaying = vids.filter(v => !v.shown && !v.paused).length;
    return { vis, imgs, vids, misplaced, hiddenPlaying, nfrag: frags.length };
  }"""


SEG_JS = "(id) => window.lecturekitSegments ? window.lecturekitSegments.state(id || undefined) : null"
ASK_JS = """() => {
  const s = Reveal.getCurrentSlide();
  return [...s.querySelectorAll('.lk-stop-notes')].map(d => [d.getAttribute('data-lk-ref'), d.textContent.includes('Ask:')]);
}"""


def _wait_hold(page, b: int, timeout: float, sid: str | None = None) -> tuple[float | None, dict]:
    """Wait until the clip in parts `sid` (default: the current slide's) holds on boundary b; (seconds waited or
    None, its state)."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        st = page.evaluate(SEG_JS, sid)
        if st and st["phase"] == "holding" and st["at"] == b:
            page.wait_for_timeout(120)              # a late frame, if any, before reading
            return time.monotonic() - t0, page.evaluate(SEG_JS, sid)
        page.wait_for_timeout(10)
    return None, page.evaluate(SEG_JS, sid)


def _hold_line(label: str, st: dict, b: int, dt: float | None) -> tuple[str, bool]:
    """One reported step of a clip in parts, and whether it is a problem."""
    want = st["bounds"][b]
    nb = len(st["bounds"]) - 1
    head = f"      {label}: hold {b} of {nb}, frame {want['f']} ({want['t']:.3f} s)"
    if dt is None:
        return head + f"  <- no hold within the time (phase {st['phase']}, at {st['at']}, frame {st['frame']})", True
    bad = st["frame"] != want["f"]
    pause = st.get("lastPause") or {}
    paused = ""
    if pause.get("b") == b and pause.get("frame") is not None:
        paused = f", paused at frame {pause['frame']}"
        bad = bad or pause["frame"] > want["f"]
    line = f"{head}, shown {st['frame']}{paused}, key to hold {dt:.2f} s"
    if st["frame"] != want["f"]:
        line += "  <- not the stop frame"
    elif pause.get("b") == b and pause.get("frame", 0) > want["f"]:
        line += "  <- the pause landed after the stop"
    return line, bad


def walk_parts(page, i: int, out: Path) -> int:
    """Walk the clip in parts on slide i (1-based): its holds forward, a backward entry and a jump. Returns the
    number of problems."""
    problems = 0
    goto(page, i, -1, settle=50)
    st = page.evaluate(SEG_JS)
    sid, nb, key = st["id"], len(st["bounds"]) - 1, st["key"]
    ncues = nb if key else nb - 1
    limit = max(d["t"] for d in st["bounds"]) + 5.0
    print(f"      a clip in parts: {st['id']}, {nb} parts, start={'key' if key else 'auto'}, {ncues} key(s)")
    for k in range(ncues + 1):
        if k:
            page.keyboard.press("ArrowRight")
        b = k if key else k + 1
        dt, st = _wait_hold(page, b, limit, sid)
        line, bad = _hold_line(f"step {k}", st, b, dt)
        print(line)
        problems += bad
        page.screenshot(path=str(out / f"s{i:02d}-f{k}.png"))
    total = page.evaluate("() => Reveal.getTotalSlides()")
    if i < total:
        goto(page, i + 1, -1, settle=300)           # no fragment shown, so that Left leaves the next slide
        plays = st["plays"]
        page.keyboard.press("ArrowLeft")
        dt, st = _wait_hold(page, nb, 5.0, sid)
        line, bad = _hold_line("backward entry", st, nb, dt)
        if st["plays"] != plays:
            line, bad = line + f"  <- it played ({st['plays'] - plays} play(s))", True
        if page.evaluate("() => Reveal.getState().indexh") != i - 1:
            line, bad = line + "  <- Left did not come back to this slide", True
        print(line)
        problems += bad
    goto(page, 1 if i > 1 else total, settle=300)
    plays = page.evaluate("(h) => { const c = window.lecturekitSegments.clips.find(s => s.h === h); return c ? c.plays : 0; }", i - 1)
    page.evaluate("([h]) => Reveal.slide(h, 0, 0)", [i - 1])
    b = 1 if key else 2
    dt, st = _wait_hold(page, b, 5.0, sid)
    line, bad = _hold_line("jump to the first cue", st, b, dt)
    if st["plays"] != plays:
        line, bad = line + f"  <- it played ({st['plays'] - plays} play(s))", True
    print(line)
    problems += bad
    # the holds before the last are where the room predicts: their notes start with "Ask:"
    asks = dict(page.evaluate(ASK_JS))
    for b in range(0 if key else 1, nb):
        ref = st["bounds"][b].get("r", str(b))
        if not asks.get(ref):
            print(f'      <- the hold {b} ({ref}) has no "Ask:" in its notes')
    return problems


def frags(deck_html: Path, out: Path, slides: list[int] | None = None) -> int:
    out.mkdir(parents=True, exist_ok=True)
    problems = 0
    with deck_page(deck_html) as (page, errors):
        n = slide_count(page)
        wanted = slides or list(range(1, n + 1))
        for i in wanted:
            goto(page, i, -1)
            info = slide_info(page)
            if not slides and not info["fragments"]:
                continue
            print(f"{i:2d}  {info['title'][:60]}  ({info['fragments']} fragments)")
            if page.evaluate("() => !!Reveal.getCurrentSlide().querySelector('.lk-seg')"):
                problems += walk_parts(page, i, out)
                continue
            k = 0
            hidden_playing = False
            while True:
                step = page.evaluate(STEP_JS)
                page.screenshot(path=str(out / f"s{i:02d}-f{k}.png"))
                clips = ", ".join(f"{v['src']}: {'shown' if v['shown'] else 'hidden'}{', paused' if v['paused'] else ', playing'}" for v in step["vids"])
                imgs = "; ".join(f"{s} at {x},{y} {w}x{h}" for s, x, y, w, h in step["imgs"])
                print(f"      step {k}: fragments {step['vis'] or '-'}  images [{imgs}]  clips [{clips}]")
                if step["hiddenPlaying"]:
                    hidden_playing = True
                    print("      <- a hidden clip is playing")
                if not next_fragment(page):
                    break
                k += 1
            if step["misplaced"]:
                problems += 1
                print("      <- a clip's .fragment inside its .live-only box: put the .fragment around the .live-only block")
            if hidden_playing:
                problems += 1
            sizes = {(w, h) for _, _, _, w, h in step["imgs"]}
            if page.evaluate("() => !!Reveal.getCurrentSlide().querySelector('.r-stack')") and len(sizes) > 1:
                print(f"      <- r-stack steps differ in size: {sorted(sizes)}")
        if errors:
            print("page errors and failed loads:")
            for e in errors:
                print(f"  {e}")
    return 1 if problems else 0


def main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="lk review frags", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck", type=Path)
    ap.add_argument("--slides", type=int, nargs="*", default=None, help="slide numbers (1-based)")
    ap.add_argument("--out", type=Path, default=None, help="output directory (default: review/frags beside _build)")
    a = ap.parse_args(argv)
    out = a.out or a.deck.resolve().parent.parent / "review" / "frags"
    return frags(a.deck, out, a.slides or None)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
