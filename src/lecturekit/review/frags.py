"""`lk review frags`: slides through their fragments, step by step.

    lk review frags _build/slides-live.html                  # every slide that has fragments
    lk review frags _build/slides-live.html --slides 4 6     # these slides (1-based, as the foot shows them)

Per step: a PNG (`review/frags/s04-f1.png`), which fragments are visible, where the images sit, and whether a clip
is shown and playing. Flags a clip's `.fragment` that is not inside `.live-only` (the study PDF would then carry a
fragment step that does not exist on paper) and an r-stack whose steps have different sizes.
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
    const misplaced = frags.filter(f => f.querySelector('video') && !f.closest('.live-only')).length;
    return { vis, imgs, vids, misplaced, nfrag: frags.length };
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
            while True:
                step = page.evaluate(STEP_JS)
                page.screenshot(path=str(out / f"s{i:02d}-f{k}.png"))
                clips = ", ".join(f"{v['src']}: {'shown' if v['shown'] else 'hidden'}{', paused' if v['paused'] else ', playing'}" for v in step["vids"])
                imgs = "; ".join(f"{s} at {x},{y} {w}x{h}" for s, x, y, w, h in step["imgs"])
                print(f"      step {k}: fragments {step['vis'] or '-'}  images [{imgs}]  clips [{clips}]")
                if not next_fragment(page):
                    break
                k += 1
            if step["misplaced"]:
                problems += 1
                print("      <- a clip's .fragment outside .live-only")
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
