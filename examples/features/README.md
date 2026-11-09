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
| 10 A clip from manim8 | `clip="tuning_sweep"`: a manim8 project in `clips/`, rendered by `lk clips`; the PDF prints its latest checkpoint |
| 11 A clip in parts | `stops="all"` on an MP4 adopted with `lk clips adopt`: three keys, four parts, each held on its stop's frame; `.stop` notes per hold; the PDF prints a strip of four holds in two rows |
| 12 A manim8 clip in parts | `stops="gain_low gain_high"`: stops marked in the storyboard (`stop: true`), rendered by `lk clips`; a strip of three holds |
| 13 A kit clip in parts | `start=key`: a kit scene's `checkpoint()`; the slide opens on frame 0 and the first key plays part 1; a strip of two holds |
| 14 Revealed step by step | `.incremental` bullets; a `.study-only` paragraph the PDF shows instead |
| 15 A quiz carries its answer | the answer as a `.fragment .live-only` and as a `.study-only` paragraph |
| 16 Citations and claims | citations set in italics and small, from `references.bib` |
| Study-only detail | a whole slide marked `.study-only` on its heading: absent from the live deck |
| 17 Takeaways | a `summary` slide |
| 18 References | the bibliography |

The clip is a synthetic stand-in (a bar sweeping a disc) that `make_clips.py`
draws from each preset's brand: `assets/clips/` from `_brand.yml` and
`assets/clips/dark/` from `_brand-dark.yml`, so the dark build plays a dark
clip; `bar_back.mp4` is the same clip reversed and `bar_bold.midway.png` its
frame at 0.75 s. A real
deck's clips come from `lk clips`. On the clip slides: a click or Space
pauses and resumes the clip on stage, R replays it.

`make_clips.py` also draws `bar_steps`, the stand-in for a clip in parts: the bar crosses the disc in four moves
and rests at three positions, 0.6 s still before and after each. It is written to a temporary file and adopted
through `lk clips adopt` (the same function), with its stops `left`, `centre` and `right` at 1.4, 3.2 and 5.0 s:
the entry is format 2, with a still of frame 0, of each stop and of the end, and rests measured on the pixels. Its
`source` is the temporary file's name, `bar_steps.mp4`, as for any MP4 made outside the deck.

Slide 13's clip is a kit scene, `anim/clip_gauss_parts.py`: a Gaussian halves its width, then moves, with one
`checkpoint()` between the two. `lk clips . --only gauss-parts` renders it with Manim (lecturekit's `clips`
extra), and `--mode dark` the dark preset; the MP4s, stills and entries are committed.

On a clip in parts, Right (or Space at a hold) plays the next part and holds on its last frame; a key pressed while
a part plays lets it play on to the next stop; Left holds the previous stop at once; R replays the part that ends
at the hold. `lk review frags _build/slides-live.html --slides 11 12 13` walks the three with real keys.

Slide 10's clip is real: `clips/` is a manim8 workspace (`lk new --manim8 .`) with one family, `features`, and
one project, `tuning_sweep`: two scenes, 6 s at 1280 by 720 and 30 fps, in the bridged style that `lk theme .
--manim8 0.1.0` wrote from this deck's brands. Its content is a toy analytic curve, labelled so in the clip and in
the project's README. To render it again, with manim8 installed (lecturekit's `manim8` extra on Python 3.12, docs/INSTALL.md):

```bash
lk clips . --only tuning_sweep               # assets/clips/tuning_sweep.mp4, its checkpoints, clips.json
lk clips . --only tuning_sweep --mode dark   # the same under lecturekit_dark, into assets/clips/dark/
```

`gain_low` and `gain_high` are stops (`stop: true` in `storyboard.yaml`), which slide 12 holds at. manim8 wants
0.3 s with nothing moving before a stop, and the gain scene's closing fade starts at 2.35 s, so the gain's sweep
was moved and shortened (from 0.9 s for 1.3 s to 1.3 s for 0.7 s) and `gain_low` moved from 0.88 s to 1.2 s; the
project's README gives the arithmetic. Stops need manim8 at the commit that lecturekit's `manim8` extra names
(`fa99e8f`), and so does the family's `uv.lock`.

The first run builds the family's render environment with uv (Manim and manim8's bridge, at the commit that
`clips/families/features/uv.lock` records). The MP4s, the checkpoint PNGs and both `clips.json` files are
committed, so the deck builds without manim8; the projects' `renders/` and `.scianim/` and the family's `.venv/`
are not (`clips/.gitignore`).

The `_extensions` entry is a symlink to the engine's extension so that the deck
builds from this checkout; a project made with `lk new` holds a copy.

## Revisions

**9 November 2026, lecturekit 0.4.0: clips in parts.** Three slides, 11 to 13, one per producer of a clip in
parts: an adopted MP4 (`bar_steps`, new in `make_clips.py`), the manim8 clip with two stops, and a kit scene with a
checkpoint (`anim/`, new). The plan stays at the 15-minute budget: the three slides take 1.5 minutes each, and seven
slides gave up time (the budget, the autoplaying clip, the seam, the incremental list, the quiz, the citations and
the takeaways). Each clip in parts carries one "Ask:", at its first hold, since a prompt costs a minute; the other
holds before the last carry "Say:" notes, and `lk review frags` reports them (four holds), as it should. Checked:
both presets build with `--strict`; `lk review frags` and a separate walk with real keys held every stop on its
frame forwards, backwards, on a backward entry and on a jump, in both presets; the study strips measured on the PDF.
Not checked: Firefox, WebKit, `file://` and the lecture laptop; the CI seam job, until manim8's commit `fa99e8f`
is on GitHub.

Content: CC BY 4.0, Tomas Knapen.
