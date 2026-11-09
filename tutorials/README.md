# Tutorials

Ten short episodes, each one repository action shown end to end with the prompt visible and the result on screen. Each has a folder here with its script (the README), the exact prompts and commands, and the before and after artefacts, so that a viewer can replay the episode without the video. The worked example throughout is the kickoff deck, `examples/kickoff`: the opening talk of the Coimbra pRF workshop, 15 minutes, seven slides, eight TikZ figures, one clip, a storyboard, a plan, checked facts and a manifest.

| # | Episode | What the viewer sees | Length |
| --- | --- | --- | --- |
| 1 | [One source, two outputs](01-one-source-two-outputs/README.md) | Clone, install, build the kickoff deck; the live deck and the PDF side by side; the timing report | 6 min |
| 2 | [Anatomy of a slide](02-anatomy-of-a-slide/README.md) | A heading with role and time; notes with Line / Ask / Say; a staged figure; live-only and study-only; a movie block; a citation | 8 min |
| 3 | [From storyboard to plan](03-from-storyboard-to-plan/README.md) | The kickoff's `STORYBOARD.md`, the assistant turning it into `PLAN.md` with times against the budget; what the lecturer changes by hand | 8 min |
| 4 | [Figures from numbers](04-figures-from-numbers/README.md) | A `make_assets.py` function on the TikZ kit; a two-stage figure; `lk review figs`; why the figure is drawn at display size | 8 min |
| 5 | [A clip](05-a-clip/README.md) | The bar-and-BOLD scene on the Manim kit; `lk clips`, `clips.json`, the `clip=` form; click to pause, R to replay | 7 min |
| 6 | [The review loop](06-the-review-loop/README.md) | A deliberately overfull slide; `lk review overflow`, `shoot`, `measure`; the assistant's fix; `FACTS.md` catching a wrong date | 8 min |
| 7 | [Restyle in one instruction](07-restyle-in-one-instruction/README.md) | The dark preset from one instruction, including the palette judgement in its second half | 10 min |
| 8 | [Publish and share](08-publish-and-share/README.md) | The continuous build, GitHub Pages, exporting the PDF, how a colleague forks a project | 5 min |
| 9 | [A talk from a paper](09-a-talk-from-a-paper/README.md) | Hedger et al. (2025) dropped into a new project; a 20-slide talk built in dialogue, the author correcting the assistant's reading on camera; figures redrawn and recomputed; `FACTS.md` from the paper | 12 to 15 min, or two parts |
| 10 | [A clip from a brief](10-a-clip-from-a-brief/README.md) | A manim8 clip from a one-paragraph brief, through checkpoints and review, into a slide through the seam, in both presets | 8 min |

## What can be replayed today

Episodes 1, 2, 4, 5, 6 and 7 run on `examples/kickoff`, which builds in both formats and both presets from a fresh clone; episode 2 can also be followed on `examples/features`, the small deck that exercises every construct. Episode 3 runs on a fresh `lk new` project, with the kickoff's own `STORYBOARD.md` and `PLAN.md` as the model of what comes out. Episode 8 shows the continuous build in `.github/workflows/build.yml`, which builds both example decks and publishes them to Pages; the fork half needs a project repository on the released engine, which is still to come. Episode 9 is a new project from a paper. Episode 10 is a new project made with `lk new --manim8`; it needs manim8 0.1.0a0, which lecturekit's `manim8` extra installs on Python 3.12 or later.

## Folder layout

```text
tutorials/NN-slug/
├── README.md     the script: goal, what the viewer sees, prompts and commands, artefacts, length
├── before/       the files as they are when the episode starts
└── after/        the files, reports and PNGs the episode produces
```

The README lists what belongs in `before/` and `after/`. Reports (`timing.txt`, the output of the review commands) are kept as text; slides as PNGs from `lk review shoot`; clips as the PNG still and, when small, the MP4.

## Recording

Screen capture at 1920 by 1080 with the browser deck on one half and the terminal or chat on the other. A voice track recorded separately and cut to the screen; no face camera. Each prompt is typed on screen rather than pasted, slowly enough to read. Episodes 3, 6, 7 and 9 are recorded in one real session each, with the waiting cut, so that the viewer sees what the assistant did and where the lecturer intervened. Whether each episode's chat transcript is published beside the video is an open decision; it would make the series reproducible without the video.

## The documents the episodes point at

[AUTHORING](../docs/AUTHORING.md) for the dialect, [LAYOUT](../docs/LAYOUT.md) for the geometry and its checks, [WORKFLOW](../docs/WORKFLOW.md) for the method, [POLICY](../docs/POLICY.md) for what goes on a slide, [FIGURES](../docs/FIGURES.md), [CLIPS](../docs/CLIPS.md), [MANIM](../docs/MANIM.md), [THEMING](../docs/THEMING.md) and [INSTALL](../docs/INSTALL.md).
