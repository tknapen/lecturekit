# The feature deck

A small complete lecturekit project that exercises every feature of the
dialect. It is the engine's test deck, the model for `lk new`, and the deck
the restyle episode runs on.

```bash
lk build .                       # _build/slides-live.html, _build/slides-study.pdf, timing.txt
lk build . --profile dark        # _build-dark/, from _brand-dark.yml
lk review shoot _build/slides-live.html --sheet
```

What to look at, slide by slide (numbers as the live deck's foot shows them):

| Slide | Shows |
| --- | --- |
| 2 What this deck is for | a `goals` slide on warm paper; a coloured span |
| 3 One source, two outputs | a `concept` eyebrow, `time=2`, a TikZ figure from `assets/figures/pipeline.tex` drawn at display size |
| 4 The budget is checked | columns, an inline ```` ```{.tikz} ```` block, the plan printed against `budget: 15` |
| 5 A clip, autoplaying | a `.movie` with `src=` in `.live-only`, a `.study-only` still for the PDF |
| 6 A clip through the seam | `clip="bar_bold"` resolved through `assets/clips/clips.json`: the video live, the still in the PDF |
| 7 A clip on a key press | `.fragment` > `.live-only` > `.movie`: the clip waits for the key, then plays from its start |
| 8 A sequence of clips | `.live-only` > `.r-stack` of two clips, the second in a `.fragment`: one step plays at a time |
| 9 A still from a checkpoint | `clip="bar-bold" still="midway"`: a checkpoint id from the entry's `checkpoints`; `-` and `_` name one clip |
| 10 Revealed step by step | `.incremental` bullets; a `.study-only` paragraph the PDF shows instead |
| 11 A quiz carries its answer | the answer as a `.fragment .live-only` and as a `.study-only` paragraph |
| 12 Citations and claims | citations set in italics and small, from `references.bib` |
| Study-only detail | a whole slide marked `.study-only` on its heading: absent from the live deck |
| 14 References | the bibliography |

The clip is a synthetic stand-in (a bar sweeping a disc) written by a script
in the repository's history; `bar_back.mp4` is the same clip reversed and
`bar_bold.midway.png` its frame at 0.75 s, both made with ffmpeg. A real
deck's clips come from `lk clips`. On the clip slides: a click or Space
pauses and resumes the clip on stage, R replays it. The
`_extensions` entry is a symlink to the engine's extension so that the deck
builds from this checkout; a project made with `lk new` holds a copy.

Content: CC BY 4.0, Tomas Knapen.
