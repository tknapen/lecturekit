# Episode 5: A clip

Length: 7 minutes.

## Goal

The bar-and-BOLD scene on the Manim kit, rendered by `lk clips` and indexed in `clips.json`; the movie block in its two forms; click to pause, R to replay; the static equivalent in the PDF.

## What the viewer sees

`examples/kickoff/anim/clip_bar_bold.py`: one scene class on the kit, `from kit import *`, its docstring saying what the clip shows and in which stages, its colours tokens (`BLUE`, `INK`, `MUTED`, `PAPER`), its numbers from `assets/data/s01.json` through the same numpy forward model as the static figure (`anim/bar_model.py`). `lk clips` renders it (the waiting cut) at 1280 by 720 on white and writes `assets/clips/bar-bold.mp4`, the still `bar-bold.png` from the last frame, and the entry in `clips.json` with width, height, frame rate, duration, source, revision and producer. The movie block in `slides.qmd`; the build; the clip autoplays on its slide; a click pauses it, space resumes it, R replays it; the PDF page shows the TikZ figure drawn from the same run. Then the second form: the block rewritten as `clip="bar-bold"`, which needs no live-only wrapper and puts the still in the PDF.

## Commands

```sh
cat examples/kickoff/anim/clip_bar_bold.py
lk clips examples/kickoff --only bar-bold
cat examples/kickoff/assets/clips/clips.json
lk build examples/kickoff
open examples/kickoff/_build/slides-live.html
```

The block as shipped, with the figure as the study equivalent:

```markdown
:::: {.live-only}
::: {.movie src="assets/clips/bar-bold.mp4" label="A bar sweeps across the visual field in two directions; ..."}
:::
::::

::: {.study-only}
\nmfigureh{3.8cm}{assets/figures/bar-bold.tex}
:::
```

The block through the seam, once `clips.json` exists:

```markdown
::: {.movie clip="bar-bold" height=3.8cm}
A bar sweeps the visual field; the predicted BOLD response follows.
:::
```

## Points to make

- The deck names the clip; `clips.json` knows the files. Any renderer that writes the entry can feed the slide (`docs/CLIPS.md`); manim8 does, in episode 10. `--only bar-bold` and `--only bar_bold` name the same clip.
- The aspect comes from the entry's width and height, so the slide reserves the box before the video loads; `--crop` trims a clip to its content for a column, and the entry records the new shape.
- The still is the last frame, or the second the scene names with `still = <seconds>`; the kickoff keeps its TikZ figure as the study equivalent because a drawing of the whole run reads better on paper than one frame.
- Clips carry no titles and render on the slide colour; click or space pauses, R replays; a re-rendered clip needs a new file name before a browser shows it.
- The MP4, the PNG and `clips.json` stay committed, so that the deck can be read without rendering.

## Artefacts

- `before/anim/clip_bar_bold.py`: the scene.
- `after/assets/clips/clips.json`, `after/assets/clips/bar-bold.png`, and the MP4 if small.
- `after/slide-02-live.png` and `after/slide-02-study.png`, in both forms of the block.

## Notes

The kit is `lecturekit.manim` (`docs/MANIM.md`); the clip uses `nmstyle` and `nmprf` only, so the licence note for the 3Blue1Brown-derived modules in `docs/CLIPS.md` does not apply to it. Rendering needs `pip install lecturekit[clips]` (Manim Community 0.22 with Pillow below 11.3, and the Cairo and Pango headers, `docs/INSTALL.md`).
