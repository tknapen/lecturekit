"""`lk review shoot`: every slide of a live deck as a PNG, with its fragments shown, and a report of what crosses
the foot or the right edge.

    lk review shoot _build/slides-live.html                 # review/shots/slide-NN.png and report.json
    lk review shoot _build/slides-live.html --sheet         # plus a contact sheet
    lk review shoot _build/slides-live.html --fragments     # one PNG per fragment step as well
    lk review shoot _build/slides-live.html --against review/shots-round3

The frame is 1280 by 720 at device scale 1 (`--scale 2` for a sheet a person will read closely). The report lists,
per slide, the elements whose box crosses the foot line or the right edge, and any page error or failed load.
`--against` compares with an earlier run and lists the slides whose pixels changed beyond anti-aliasing. Slide
numbers are 1-based, as the foot shows them.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .browser import deck_page, goto, slide_count, slide_info

OVER_JS = """
  () => {
    const s = Reveal.getCurrentSlide(), r = s.getBoundingClientRect(), k = Reveal.getScale();
    const foot = s.querySelector('.nm-foot');
    const limit = foot ? foot.getBoundingClientRect().top - 1 : r.bottom + 1;
    const over = [...s.querySelectorAll('p,li,h1,h2,h3,video,img,table,blockquote,.lk-placeholder')]
      .filter(e => !e.closest('.nm-foot, aside'))
      .filter(e => { const cs = getComputedStyle(e); return cs.display !== 'none' && cs.visibility !== 'hidden'; })
      .filter(e => { const b = e.getBoundingClientRect(); return b.height > 0 && (Math.round(b.bottom) > Math.round(limit) || Math.round(b.right) > Math.round(r.right) + 1); })
      .map(e => (e.tagName + ' ' + (e.textContent || e.getAttribute('src') || '').trim()).slice(0, 70));
    const h = s.querySelector('h1,h2');
    const lh = h ? parseFloat(getComputedStyle(h).lineHeight) : 0;
    return { over, titleLines: h ? Math.round(h.getBoundingClientRect().height / lh) : 0 };
  }"""


def shoot(deck_html: Path, out: Path, fragments: bool = False, scale: int = 1, sheet: bool = False) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    report = []
    with deck_page(deck_html, scale=scale) as (page, errors):
        n = slide_count(page)
        for i in range(1, n + 1):
            goto(page, i)
            info = slide_info(page)
            if fragments and info["fragments"]:
                for f in range(-1, info["fragments"]):
                    goto(page, i, f)
                    p = out / f"slide-{i:02d}-f{f + 1}.png"
                    page.screenshot(path=str(p))
                    written.append(p)
                goto(page, i)
            p = out / f"slide-{i:02d}.png"
            page.screenshot(path=str(p))
            written.append(p)
            m = page.evaluate(OVER_JS)
            entry = {"slide": i, "title": info["title"], "over": m["over"], "titleLines": m["titleLines"]}
            report.append(entry)
            flags = []
            if m["over"]:
                flags.append(f"crosses foot or edge: {'; '.join(m['over'])}")
            if m["titleLines"] > 1:
                flags.append("title on two lines")
            print(f"  {i:2d}  {info['title'][:44]:44s}  {p.name}  {' | '.join(flags)}")
        result = {"slides": n, "report": report, "errors": errors}
    (out / "report.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    if sheet:
        contact_sheet(written, out / "sheet.png")
    if errors:
        print("page errors and failed loads:")
        for e in errors:
            print(f"  {e}")
    return result


def contact_sheet(files: list[Path], out: Path, cols: int = 3, width: int = 480) -> Path:
    from PIL import Image
    ims = [Image.open(f) for f in files if f.suffix == ".png" and f.name != out.name and "-f" not in f.stem]
    if not ims:
        return out
    w, h = ims[0].size
    tw, th = width, int(h * width / w)
    rows = (len(ims) + cols - 1) // cols
    gap = 8
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * gap, rows * th + (rows + 1) * gap), "#777777")
    for i, im in enumerate(ims):
        sheet.paste(im.resize((tw, th)), (gap + (i % cols) * (tw + gap), gap + (i // cols) * (th + gap)))
    sheet.save(out)
    print(f"contact sheet: {out}")
    return out


def compare(a_dir: Path, b_dir: Path, tolerance: float = 0.002) -> list[tuple[str, float]]:
    """Fraction of differing pixels per matching file name; returns those above tolerance."""
    from PIL import Image, ImageChops
    out = []
    for a in sorted(a_dir.glob("slide-??.png")):
        b = b_dir / a.name
        if not b.exists():
            out.append((a.name, 1.0))
            continue
        ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
        if ia.size != ib.size:
            out.append((a.name, 1.0))
            continue
        diff = ImageChops.difference(ia, ib).convert("L").point(lambda v: 255 if v > 24 else 0)
        frac = sum(1 for v in diff.getdata() if v) / (ia.width * ia.height)
        if frac > tolerance:
            out.append((a.name, frac))
    return out


def main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="lk review shoot", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck", type=Path, help="the built live deck (_build/slides-live.html)")
    ap.add_argument("--out", type=Path, default=None, help="output directory (default: review/shots beside _build)")
    ap.add_argument("--fragments", action="store_true", help="one PNG per fragment step as well")
    ap.add_argument("--scale", type=int, default=1, help="device scale factor (2 for a sheet people will read)")
    ap.add_argument("--sheet", action="store_true", help="also write a contact sheet")
    ap.add_argument("--against", type=Path, default=None, help="compare with an earlier shots directory")
    a = ap.parse_args(argv)
    out = a.out or a.deck.resolve().parent.parent / "review" / "shots"
    result = shoot(a.deck, out, fragments=a.fragments, scale=a.scale, sheet=a.sheet)
    over = [r for r in result["report"] if r["over"]]
    print(f"{result['slides']} slides in {out}; {len(over)} cross the foot or the edge; {len(result['errors'])} page errors")
    status = 1 if (over or result["errors"]) else 0
    if a.against:
        diffs = compare(out, a.against)
        if diffs:
            print("slides that differ:")
            for name, frac in diffs:
                print(f"  {name}: {frac * 100:.2f}% of pixels")
            status = 1
        else:
            print("no slide differs beyond anti-aliasing")
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
