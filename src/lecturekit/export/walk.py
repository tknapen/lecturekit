"""The walk through a built live deck: every horizontal slide at every reveal step, shot with its clips hidden.

The page is review/browser.py's (1280 by 720 CSS px, served with byte ranges, slide transitions off). On top of
it: CSS transitions and animations off (a fragment fades in over 0.2 s), every video and every still of a clip in
parts hidden by `visibility`, which keeps their boxes where they are (the exporter places the clips itself), and a
flash slide's image kept visible without its fixation cross. After each `Reveal.slide(h, 0, f)` the walk waits for
the fonts, the slide's images and two painted frames, then reads the step and takes the screenshot; boxes are read
on the page that takes it, at its device scale (layout snaps to device pixels).

The steps of a slide are f = -1 and each distinct `data-fragment-index` (Reveal writes and renumbers them at
initialisation, so they exist before a slide is shown). The notes of a step follow Reveal's notes plugin: the
notes of the current fragments, else the slide's `data-notes`, else every `aside.notes` of the slide outside a
fragment. Where two fragments share an index, the notes of both are taken (the speaker view shows the first only).

A clip the page blends by multiplication (`mix-blend-mode: multiply`, which theme.scss gives a video of class
`paper`) is recorded with the colour it is blended with: the nearest background colour from its parent upwards.
The search ends where the blend's backdrop ends: at the first ancestor that is a group of its own to the browser (a
stacking context), and at the slide's section at the latest (Reveal's own background layer lies outside it). A
clip with no colour within that group shows unblended in the live deck and gets no tint here. A shown `.fragment`
is such a group (Reveal leaves `will-change: opacity` on it), so a clip that comes with a reveal step, or as a
later step of an `.r-stack`, is not blended by the live deck, and not here.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from ..review.browser import deck_page
from .plan import Clip, Parts, Step, notes_text, parse_slides

CSS = """
.reveal *, .reveal *::before, .reveal *::after,
.reveal-viewport, .reveal-viewport::before, .reveal-viewport::after {
  transition: none !important; transition-duration: 0s !important; transition-delay: 0s !important;
  animation: none !important; animation-duration: 0s !important; animation-delay: 0s !important;
}
.reveal .slides video,
.reveal .slides .lk-seg > img.lk-still { visibility: hidden !important; }
.reveal .slides section[data-flash] img { visibility: visible !important; }
.reveal .slides section[data-flash] .nm-fix { visibility: hidden !important; }
"""

SETUP_JS = """(css) => {
  const s = document.createElement('style'); s.id = 'lk-export'; s.textContent = css; document.head.appendChild(s);
  return Reveal.getHorizontalSlides().map(sl => ({
    title: (sl.querySelector(':scope > h1, :scope > h2, :scope > h3, h1.title') || {textContent: ''}).textContent.trim(),
    vertical: sl.querySelectorAll(':scope > section').length,
    steps: [...new Set([...sl.querySelectorAll('.fragment')].map(f => f.getAttribute('data-fragment-index'))
      .filter(a => a !== null).map(Number))].sort((a, b) => a - b)
  }));
}"""

SETTLE_JS = """async () => {
  await document.fonts.ready;
  const s = Reveal.getCurrentSlide();
  await Promise.all([...s.querySelectorAll('img')].filter(im => !im.closest('.lk-seg'))
    .map(im => (im.complete && im.naturalWidth) ? null : (im.decode ? im.decode().catch(() => null) : null)));
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
}"""

RECORD_JS = """() => {
  const slide = Reveal.getCurrentSlide();
  const rect = el => { const r = el.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; };
  function inHiddenFragment(el) {
    for (let n = el; n && n.tagName !== 'SECTION'; n = n.parentElement)
      if (n.classList.contains('fragment') && !n.classList.contains('visible')) return true;
    return false;
  }
  function covered(el) {
    for (let n = el; n && n.tagName !== 'SECTION'; n = n.parentElement) {
      const stack = n.parentElement;
      if (!stack || !stack.classList.contains('r-stack')) continue;
      for (let s = n.nextElementSibling; s; s = s.nextElementSibling)
        if (s.classList.contains('fragment') && s.classList.contains('visible')) return true;
    }
    return false;
  }
  const opaque = c => c && c !== 'transparent' && !/rgba\\(.*,\\s*0\\)$/.test(c);
  const blended = el => !!el && getComputedStyle(el).mixBlendMode === 'multiply';
  // whether the browser paints an element as a group of its own (a stacking context): a blend inside it sees
  // nothing painted outside it
  function isolates(n) {
    const s = getComputedStyle(n), none = v => !v || v === 'none';
    const lifted = s.zIndex !== 'auto' && (s.position !== 'static'
      || /flex|grid/.test(n.parentElement ? getComputedStyle(n.parentElement).display : ''));
    return s.isolation === 'isolate' || parseFloat(s.opacity) < 1 || s.mixBlendMode !== 'normal'
      || !none(s.transform) || !none(s.filter) || !none(s.backdropFilter) || !none(s.perspective)
      || !none(s.clipPath) || !none(s.maskImage) || s.position === 'fixed' || s.position === 'sticky' || lifted
      || /opacity|transform|filter|perspective|clip-path|mask|isolation|mix-blend-mode/.test(s.willChange || '')
      || /layout|paint|strict|content/.test(s.contain || '');
  }
  function backdrop(el) {
    for (let n = el.parentElement; n; n = n.parentElement) {
      const c = getComputedStyle(n).backgroundColor;
      if (opaque(c)) return c;
      if (n === slide || isolates(n)) break;
    }
    return null;
  }
  const srcOf = v => v.getAttribute('src') || (v.querySelector('source') || {getAttribute: () => null}).getAttribute('src');
  const videos = [...slide.querySelectorAll('video')].filter(v => !v.closest('.lk-seg')).map((v, i) => ({
    index: i, src: srcOf(v), box: rect(v), onStage: !inHiddenFragment(v) && !covered(v),
    label: v.getAttribute('aria-label') || '', paper: blended(v), under: blended(v) ? backdrop(v) : null }));
  const parts = [...slide.querySelectorAll('.lk-seg')].map(b => {
    const name = b.getAttribute('data-lk-seg'), v = b.querySelector('video');
    const paper = blended(v) || [...b.querySelectorAll('img.lk-still')].some(blended);
    const cues = [...slide.querySelectorAll('.lk-cue')].filter(c => c.getAttribute('data-lk-for') === name);
    return { name, start: b.getAttribute('data-lk-start') === 'key' ? 'key' : 'auto',
      bounds: JSON.parse(b.getAttribute('data-lk-bounds') || '[]').map(x => x.f),
      src: v.getAttribute('data-lk-src') || srcOf(v), k: cues.filter(c => c.classList.contains('visible')).length,
      box: rect(v), label: v.getAttribute('aria-label') || '', paper, under: paper ? backdrop(v) : null };
  });
  // notes: Reveal's notes plugin, with every current fragment's notes where fragments share an index
  let notes = [];
  const cur = [...slide.querySelectorAll('.current-fragment')];
  for (const c of cur) {
    const a = c.querySelector('aside.notes');
    if (a) notes.push(a.outerHTML); else if (c.hasAttribute('data-notes')) notes.push(c.getAttribute('data-notes'));
  }
  if (!notes.length) {
    if (slide.hasAttribute('data-notes')) notes = [slide.getAttribute('data-notes')];
    else notes = [...slide.querySelectorAll('aside.notes')].filter(a => !a.closest('.fragment')).map(a => a.outerHTML);
  }
  // alt text: the role label or eyebrow (CSS ::before text), the title, the visible text without the foot
  const title = (slide.querySelector(':scope > h1, :scope > h2, :scope > h3, h1.title') || {textContent: ''}).textContent.trim();
  const text = [];
  for (const c of slide.children) {
    if (c.matches('aside, .nm-foot, h1, h2, h3, style, script, .lk-cue')) continue;
    if (getComputedStyle(c).display === 'none') continue;
    const t = (c.innerText || '').split('\\n').map(l => l.trim()).filter(Boolean).join('\\n');
    if (t) text.push(t);
  }
  const head = slide.getAttribute('data-role-label') || slide.getAttribute('data-eyebrow') || '';
  const bgEl = slide.slideBackgroundElement;
  const colours = [bgEl ? getComputedStyle(bgEl).backgroundColor : null, getComputedStyle(slide).backgroundColor,
    getComputedStyle(document.querySelector('.reveal-viewport') || document.body).backgroundColor];
  const refs = slide.querySelector('#refs');
  return { title, alt: [head, title, ...text].filter(Boolean).join('\\n'), notes, videos, parts,
    colour: colours.find(opaque) || 'rgb(255, 255, 255)',
    links: slide.querySelectorAll('a[href]').length,
    refsCut: !!refs && refs.scrollHeight > refs.clientHeight + 1 };
}"""


def _rgb(css: str) -> tuple[int, int, int]:
    m = re.match(r"rgba?\(\s*([\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)", css or "")
    return tuple(round(float(v)) for v in m.groups()) if m else (255, 255, 255)


def _tint(css: str | None) -> tuple[int, int, int] | None:
    """The colour a blended clip is multiplied by; None where there is none or it is white (which changes nothing)."""
    if not css:
        return None
    rgb = _rgb(css)
    return None if rgb == (255, 255, 255) else rgb


def media_file(deck: Path, src: str | None) -> Path | None:
    """The file a clip's `src` names, relative to the deck (the `?v=` query dropped)."""
    if not src:
        return None
    return (deck.parent / unquote(urlparse(src).path)).resolve()


class WalkError(Exception):
    pass


def walk(deck: Path, shots: Path, scale: int = 2, slides: str | None = None,
         on_slide=None) -> tuple[list[list[Step]], dict]:
    """Every step of the chosen slides (`3,5-7`, 1-based as the foot shows them; all when None), each with its
    screenshot in `shots`; `on_slide(steps)` is called after each slide. Returns the steps by slide and what else
    the walk saw: the slide count, warnings, page errors."""
    deck = Path(deck).resolve()
    shots.mkdir(parents=True, exist_ok=True)
    out: list[list[Step]] = []
    seen: dict = {"warnings": []}
    with deck_page(deck, scale=scale) as (page, errors):
        meta = page.evaluate(SETUP_JS, CSS)
        seen["count"] = len(meta)
        try:
            chosen = parse_slides(slides, len(meta))
        except ValueError as exc:
            raise WalkError(str(exc)) from None
        for number in chosen:
            m = meta[number - 1]
            if m["vertical"]:
                raise WalkError(f"slide {number} ({m['title'] or 'untitled'}) holds vertical slides; "
                                f"lk export pptx exports horizontal slides only")
            steps = []
            for f in [-1, *m["steps"]]:
                page.evaluate("([h, f]) => Reveal.slide(h, 0, f)", [number - 1, f])
                page.evaluate(SETTLE_JS)
                r = page.evaluate(RECORD_JS)
                shot = shots / f"s{number:03d}-f{f + 1:02d}.png"
                page.screenshot(path=str(shot))
                clips = [Clip(index=v["index"], file=media_file(deck, v["src"]), box=tuple(v["box"]),
                              on_stage=v["onStage"], label=v["label"], paper=v["paper"], tint=_tint(v["under"]))
                         for v in r["videos"]]
                parts = [Parts(name=p["name"], file=media_file(deck, p["src"]), start=p["start"], bounds=p["bounds"],
                               k=p["k"], box=tuple(p["box"]), label=p["label"], paper=p["paper"],
                               tint=_tint(p["under"])) for p in r["parts"]]
                steps.append(Step(number=number, f=f, title=r["title"], shot=shot, colour=_rgb(r["colour"]),
                                  alt=r["alt"], notes=notes_text(r["notes"]), clips=clips, parts=parts))
                if f == -1:
                    if r["links"]:
                        seen["warnings"].append(f"slide {number}: {r['links']} link(s) become part of the picture")
                    if r["refsCut"]:
                        seen["warnings"].append(f"slide {number}: the references scroll; the picture shows the top")
            out.append(steps)
            if on_slide:
                on_slide(steps)
        seen["errors"] = list(errors)
    return out, seen
