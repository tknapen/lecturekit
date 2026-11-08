# Working with lecturekit

Read this first in every session. It is short because it points to the
documents that hold the rules: `docs/AUTHORING.md` (the dialect),
`docs/LAYOUT.md` (the pixel budget, each rule with the command that checks
it), `docs/WORKFLOW.md` (the per-deck method), `docs/POLICY.md` (what goes
on a slide), `docs/THEMING.md`, `docs/FIGURES.md`, `docs/CLIPS.md`.

## Commands

```bash
lk build [dir] [--to live|study] [--profile dark]   # render, print the plan against the budget
lk review shoot <live.html> --sheet                 # every slide as PNG; compare rounds with --against
lk review measure <live.html>                       # bottom edge per slide, free px above the foot (677)
lk review frags <live.html>                         # fragments; a clip's .fragment outside .live-only is flagged
lk review overflow <slides.log>                     # Beamer overfull boxes, missing glyphs, undefined colours
lk review figs <deck>                               # TikZ figures as PNG at live size, before placing them
lk review contrast <_brand.yml> [--mode dark]       # WCAG AA for text and roles on every surface
lk clips [deck]                                     # render clips, write assets/clips/clips.json
lk theme [dir] [--manim8 0.1.0]                     # tokens.tex / .css / .py (and a manim8 style) from _brand.yml
lk new <dir>                                        # a project with the files the method prescribes
pytest -q                                           # the engine's own tests (feature deck, scaffold, tools)
```

In this repository the feature deck is `examples/features`; build it with
`lk build examples/features` and look at `review/shots/sheet.png` after
`lk review shoot`. A change to the extension is not done until both outputs
of the feature deck have been looked at, in the paper and the dark preset.

## Writing rules

- Titles under 30 characters; one line per bullet at the live font; a visual on every slide, as large as the slide allows.
- Every slide heading carries a role and `time=`; the plan must fit the budget in `_quarto.yml`.
- Quiz and pause slides carry their answers (live: a `.fragment .live-only`; study: a `.study-only` answer).
- Verified claims only, with the source in `FACTS.md`. Published figures are redrawn from digitised values and cited, never reproduced.
- Colours are tokens from `_brand.yml`: `nmConcept`, `--nm-concept`, `CONCEPT`. Never a hex value in a figure, a clip or a slide.
- A figure whose data are missing becomes a labelled placeholder (`\lkplaceholder`, or the filter's own when compilation fails) so that the deck always builds.
- TikZ is drawn at display size: 1 cm of the Beamer frame is 80 px of the live deck; `\lkfigureh` caps the height and never upscales.
- A clip's `.fragment` goes inside `.live-only`. Anything the live budget drops goes to a study-only slide, not into a smaller font.
- `%` and hyphenation break TikZ labels; use `lecturekit.tikz.escape`.

## Colour meanings

Roles: concept (blue), caveat (red), example (amber), anchor (teal), question (purple).
Marks in figures and clips: input, state, update, context. Project tokens (model colours and the like) are the project's own and travel under the same mechanism.

## What is never delegated

The claims, the titles, and what the lecture is for belong to the lecturer. An assistant proposes storyboards, plans, figures and fixes, and runs the review tools; it does not change a claim, a number or a title silently, and it records every number's source in `FACTS.md` and every image's origin in `MANIFEST.md`.

## Engine conventions

- The Quarto extension in `_extensions/lecturekit/` and the Python package share one version; a project pins the extension by vendoring it, and `lk build` refuses a major-version mismatch.
- Filters: `dual-output.lua` (the dialect, pre-quarto), `tikz.lua` (figures, pre-quarto), `tokens.lua` (brand into each output, post-quarto). The brand is read in `lkbrand.lua`. Quarto 1.11 rewrites `header-includes` set by filters and drops `include_text` for Reveal, so tokens go in as a body `<style>` block and a `_lecturekit/tokens.tex` file; do not move them back.
- Helpers migrate upward: a helper lives in a project's `lib/` until a second project wants it, then moves into the engine with a release.
- No machine-specific paths, fonts or tools in the engine. Fonts ship in the extension or come from the system through fontspec.
