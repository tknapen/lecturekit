# Working in this repository

lecturekit is the engine behind a lecturer's decks: one Markdown source per deck becomes a Reveal.js live deck and
a Beamer study PDF; figures are TikZ drawn from numbers; clips are Manim on a shared kit; a review loop of
screenshots and log checks keeps both outputs within their frames. The engine is a Quarto extension (two formats)
plus a Python package (`lk`). `docs/WORKFLOW.md` says how a deck is made and who decides what; `docs/LAYOUT.md`
says what fits where and how to check it; `docs/AUTHORING.md` is the dialect; `docs/POLICY.md` the rules of the
slides. Read them before building or changing a slide.

## Commands

```sh
lk new <dir>                                   # a project: _quarto.yml, _brand.yml, slides.qmd, the method's files, the vendored extension
lk build [dir] [--to live|study] [--profile dark] [--strict]   # quarto render; the plan against the budget; --strict fails on warnings
python <deck>/make_assets.py [figure ...]      # regenerate TikZ figures from assets/data (also the project's pre-render step)
lk clips <deck> [--only name] [--crop] [--mode dark]   # kit scenes (anim/clip_*.py) and manim8 projects (clips/) into assets/clips, write clips.json
lk review shoot <deck>/_build/slides-live.html [--sheet] [--fragments] [--against DIR]   # PNG per slide, report.json
lk review measure <deck>/_build/slides-live.html [--slide N]   # free pixels above the foot; one slide's boxes
lk review frags <deck>/_build/slides-live.html [--slides N ...] # fragment steps, clips shown and playing
lk review overflow <deck>                      # overfull frames of the study PDF, by title (slides.log, slides.tex)
lk review figs <deck> [name ...]               # figures standalone, with their natural size in cm
lk review contrast <_brand.yml> [--mode dark]  # WCAG AA of the brand's colours on its surfaces
pytest -q                                      # the engine's tests: both example decks, the tools, a scaffolded project
```

Check a layout change with `shoot` and the PDF with `overflow` before reporting it done. Look at the PNGs. A change
to the extension is not done until both example decks (`examples/kickoff`, `examples/features`) have been built and
looked at in both outputs, in the paper preset and in the dark one.

## Rules

- Titles under 30 characters, one claim each, sentence case in the source (the theme sets caps).
- A visual on every slide, as large as the slide allows; two one-line bullets leave 4.1 to 4.4 cm of figure.
- Bullets are one line at the live font (about 70 characters); longer text goes to the notes or a study-only block.
- Reveal only where the order is the explanation; the study PDF always shows everything, answers included.
- Quiz and pause slides carry their answers.
- Numbers come from scripts in `assets/data`; a figure whose data are missing is a labelled placeholder, never an
  invented curve. Every claim on a slide is in `FACTS.md` with its source and the date it was checked.
- Published figures are redrawn from digitised values or replaced by our own simulation; never reproduce them, and
  record the source and method in `MANIFEST.md`.
- Colours are named tokens (`nmInk`, `nmConcept`, the model colours), never literal values in a figure or clip; the
  values live in `_brand.yml` alone.
- Edit `slides.qmd`, `make_assets.py` and the clip sources; never the generated HTML, LaTeX or PDF.
- Every revision round ends with an entry in the deck's `README.md`: what changed, why, what remains unverified.
- Write prose the lecturer would sign: direct, precise, no filler, sentence-case headings, no em dashes.

## What the lecturer decides

The claims, the titles, the storyboard, what a lecture is for, and every review round. When a change would alter
what a slide claims, propose it and wait; when a number cannot be sourced, say so rather than supply one.

## Engine conventions

- The Quarto extension (`_extensions/lecturekit`) and the Python package share one version; a project pins the
  extension by vendoring it; `lk build` refuses a major-version mismatch, and a minor-version one while the major is 0.
- Filters: `dual-output.lua` (the dialect, pre-quarto), `tikz.lua` (figures, pre-quarto), `tokens.lua` (the brand
  into each output, post-quarto); `lkbrand.lua` reads the brand. Quarto 1.11 rewrites `header-includes` set by
  filters and drops `include_text` for Reveal, so tokens go in as a body `<style>` block and `_lecturekit/*.tex`
  files; its SCSS analyser wants one rule per line and no selector starting with `#`.
- Beamer: a frame option handler must not call `\setbeamercolor` (keyval is not re-entrant; frames marked
  `fragile` then fail), so roles set the named colours `nmRoleColor` and `nmRoleBg` that the templates read.
- The fonts are bundled in the extension and loaded by file; nothing in the engine depends on an installed font, a
  machine path or a tool outside Quarto, TeX, Python and Chromium.
- Helpers migrate upward: a helper lives in a project's `lib/` until a second project wants it, then moves into the
  engine with a release.
