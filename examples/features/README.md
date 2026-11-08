# The feature deck

A small complete lecturekit project that exercises every feature of the
dialect. It is the engine's test deck, the model for `lk new`, and the deck
the restyle episode runs on.

```bash
lk build .                       # _build/slides-live.html, _build/slides-study.pdf, timing.txt
lk build . --profile dark        # _build-dark/, from _brand-dark.yml
lk review shoot _build/slides-live.html --sheet
```

What to look at, slide by slide:

| Slide | Shows |
| --- | --- |
| 1 One source, two outputs | a `concept` eyebrow, `time=2`, a TikZ figure from `assets/figures/pipeline.tikz` drawn at display size |
| 2 The budget is checked | columns, an inline ```` ```{.tikz} ```` block, the plan printed against `budget: 15` |
| 3 A clip, autoplaying | a `.movie` block resolved through `assets/clips/clips.json`; the still in the PDF; a `.live-only` hint |
| 4 Fragments and live-only steps | three fragments; a `.study-only` paragraph the PDF shows instead |
| 5 A quiz carries its answer | the answer as a `.fragment .live-only` and as a `.study-only` paragraph |
| 6 Citations and claims | citations with italic names (`lecturekit.csl`), from `references.bib` |
| Study-only detail | a whole slide marked `.study-only` on its heading: absent from the live deck |
| References | `::: {#refs}` |

The clip is a synthetic stand-in (a bar sweeping a disc) written by a script
in the repository's history; a real deck's clips come from `lk clips`. The
`_extensions` entry is a symlink to the engine's extension so that the deck
builds from this checkout; a project made with `lk new` holds a copy.

Content: CC BY 4.0, Tomas Knapen.
