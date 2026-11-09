"""`lk review measure`: the pixel budget of the slides.

    lk review measure _build/slides-live.html              # a table: bottom edge, free px above the foot, title lines
    lk review measure _build/slides-live.html --slide 3    # the boxes of one slide: title, figure (with its natural
                                                           # size), paragraphs, bullets, foot

In pixels of the 1280 by 720 slide (Reveal's scaling undone). The foot's top edge is the limit; a slide whose
visible content (text, figures, clips, tables) crosses it is overfull. A title of two lines costs about 55 px of
figure. Slide numbers are 1-based, as the foot shows them.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .browser import deck_page, goto, slide_count, slide_info

MAX_TITLE_CHARS = 30

BOXES_JS = """
  () => {
    const s = Reveal.getCurrentSlide();
    const k = Reveal.getScale(), o = s.getBoundingClientRect();
    const box = e => { if (!e) return null; const b = e.getBoundingClientRect(); return { left: Math.round((b.left - o.left) / k), top: Math.round((b.top - o.top) / k), width: Math.round(b.width / k), height: Math.round(b.height / k), bottom: Math.round((b.bottom - o.top) / k) }; };
    const fig = s.querySelector('img,video');
    return { title: (s.querySelector('h1,h2') || {}).textContent, section: box(s), heading: box(s.querySelector('h1,h2')),
             figure: box(fig), figure_natural: fig ? [fig.naturalWidth || fig.videoWidth, fig.naturalHeight || fig.videoHeight] : null,
             columns: box(s.querySelector('.columns')), first_paragraph: box(s.querySelector('p')),
             bullets: [...s.querySelectorAll('li')].map(box), foot: box(s.querySelector('.nm-foot')) };
  }"""

SUMMARY_JS = """
  () => {
    const s = Reveal.getCurrentSlide(), k = Reveal.getScale();
    const srect = s.getBoundingClientRect();
    const foot = s.querySelector('.nm-foot');
    const limit = foot ? Math.round((foot.getBoundingClientRect().top - srect.top) / k) : Math.round(srect.height / k);
    let bottom = 0;
    s.querySelectorAll('p,li,h1,h2,h3,video,img,table,blockquote,.lk-placeholder,math').forEach(el => {
      if (el.closest('.nm-foot, aside')) return;
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden') return;
      const r = el.getBoundingClientRect();
      if (r.height === 0) return;
      bottom = Math.max(bottom, (r.bottom - srect.top) / k);
    });
    const h = s.querySelector('h1,h2');
    const lh = h ? parseFloat(getComputedStyle(h).lineHeight) : 0;
    const titleLines = h ? Math.round(h.getBoundingClientRect().height / lh) : 0;
    let wraps = 0;
    s.querySelectorAll('li').forEach(li => { const l = parseFloat(getComputedStyle(li).lineHeight); if (li.getBoundingClientRect().height > l * 1.5) wraps++; });
    return { bottom: Math.round(bottom), limit, titleLines, wraps, titleChars: h ? h.textContent.trim().length : 0 };
  }"""


def measure(deck_html: Path, slide: int | None = None) -> int:
    overfull = 0
    with deck_page(deck_html) as (page, errors):
        n = slide_count(page)
        if slide:
            goto(page, slide)
            print(json.dumps(page.evaluate(BOXES_JS), indent=1))
            return 0
        print(" #   bottom  limit  free  title  wraps  slide")
        for i in range(1, n + 1):
            goto(page, i)
            info = slide_info(page)
            if info["isTitle"]:
                continue
            m = page.evaluate(SUMMARY_JS)
            free = m["limit"] - m["bottom"]
            flags = []
            if free < 0:
                flags.append("OVERFULL")
                overfull += 1
            if m["titleLines"] > 1:
                flags.append("two-line title")
            if m["titleChars"] > MAX_TITLE_CHARS:
                flags.append(f"title {m['titleChars']} chars")
            if m["wraps"]:
                flags.append(f"{m['wraps']} wrapping bullet(s)")
            print(f"{i:2d}  {m['bottom']:6d}  {m['limit']:5d}  {free:4d}  {m['titleLines']:5d}  {m['wraps']:5d}  "
                  f"{info['title'][:40]:40s} {' '.join(flags)}")
    if overfull:
        print(f"{overfull} overfull slide(s)")
    return 1 if overfull else 0


def main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="lk review measure", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck", type=Path)
    ap.add_argument("--slide", type=int, default=None, help="one slide's boxes (1-based)")
    a = ap.parse_args(argv)
    return measure(a.deck, a.slide)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
