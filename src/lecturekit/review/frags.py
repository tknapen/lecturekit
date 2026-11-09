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
* a clip that plays while it is hidden (in a hidden fragment, or in an r-stack step a later one covers).

It also notes an r-stack whose steps have different sizes. The study PDF is not affected by fragments: Beamer gets
no overlay from them, and `.live-only` content is not in it.
"""

from __future__ import annotations

import json
import sys
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
    const vids = [...s.querySelectorAll('video')].map(v => ({ shown: shown(v), paused: v.paused, src: (v.getAttribute('src') || '').split('/').pop() }));
    // a fragment whose clip has no .live-only box between the fragment and the video (at the fragment or inside it);
    // an r-stack step is stacked in the r-stack's box
    const misplaced = frags.filter(f => {
      if (f.parentElement && f.parentElement.classList.contains('r-stack')) return false;
      return [...f.querySelectorAll('video')].some(v => { const box = v.closest('.live-only'); return !box || !f.contains(box); });
    }).length;
    const hiddenPlaying = vids.filter(v => !v.shown && !v.paused).length;
    return { vis, imgs, vids, misplaced, hiddenPlaying, nfrag: frags.length };
  }"""


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
