# lecturekit

One Markdown source, two outputs: a Reveal.js deck for the room and a Beamer PDF
for study, with figures and animations computed from numbers rather than drawn
by hand. lecturekit is a Quarto extension, a Python package and a method, for
lecturers and workshop teachers who write their own material, with or without
an LLM assistant.

```bash
pip install lecturekit            # or: uv pip install -e .   (see docs/INSTALL.md)
lk new my-lecture && cd my-lecture
lk build                          # _build/slides-live.html and _build/slides-study.pdf
```

The build prints the plan against the budget:

```text
lecturekit timing (live): 7 slides,  10' planned, budget  15'
   1  concept     2'    2'  One source, two outputs
   2  caveat      1'30  3'30  The budget is checked
   ...
  under budget by   5'
```

## What is in the repository

| Path | What it is |
| --- | --- |
| `_extensions/lecturekit/` | The Quarto extension: formats `lecturekit-revealjs` and `lecturekit-beamer`, the dialect filter, the TikZ filter, the theme for both outputs, the citation style. A project vendors a copy, by Quarto's convention. |
| `src/lecturekit/` | The Python package and the `lk` command: `new`, `build`, `clips`, `theme`, `review`. The TikZ and Manim kits and the review tools live here. |
| `examples/features/` | A small complete project that exercises every feature of the dialect: roles and times, study-only and live-only content, a TikZ figure, a clip, fragments, a quiz with its answer, citations, a dark preset. It is the test deck and the scaffold's model. |
| `docs/` | The dialect (`AUTHORING.md`), the pixel budget (`LAYOUT.md`), the per-deck method (`WORKFLOW.md`), the theme (`THEMING.md`), figures (`FIGURES.md`), clips and their seam (`CLIPS.md`), what goes on a slide (`POLICY.md`), installation (`INSTALL.md`). |
| `tutorials/` | One folder per episode of the video series: script, prompts, before and after. |
| `AGENTS.md` | What an assistant reads first: commands, rules, what is never delegated. |

## The dialect in one slide

```markdown
## The budget is checked {.caveat time=1.5}

- Every slide heading has `time=`
- The build prints the plan against the deck's budget

![](assets/figures/clock.tikz){height=4.2cm}

::: {.movie clip="bar_bold" height=4.4cm}
A bar sweeps the visual field; the BOLD response of one voxel follows.
:::

::: {.study-only}
A derivation the live budget drops, printed for the reader.
:::

::: notes
Line: the one sentence the slide exists for.  Ask: ...  Say: ...  Status: final.
:::
```

A heading's class is its teaching role (`concept`, `caveat`, `example`,
`anchor`, `question`; or `where`, `how`, `what`, `when` with the `prf`
preset) and becomes the eyebrow in both outputs; `time=` feeds the plan.
`.study-only` and `.live-only` select an output, on a Div or on a whole slide.
A `.movie` block is a `<video>` live and the clip's still in the PDF. TikZ
figures are compiled once with the deck's colours and fonts and placed at the
size they were drawn, never upscaled.

## One theme, one file

The look is defined once, in Quarto's `_brand.yml`. Every palette entry becomes
a token: `nmConcept` in Beamer and TikZ, `--nm-concept` in the live deck,
`CONCEPT` in Python. A restyle is a second brand file and a profile:

```bash
lk build --profile dark      # _brand-dark.yml, black surfaces, Roboto, lifted role tints
lk review contrast _brand-dark.yml --mode dark
```

Figures regenerate because they name colours; clips re-render with `lk clips`;
the PDF follows. What does not carry over by construction is judged by eye and
checked by the contrast tool.

## The review loop

```bash
lk review shoot   _build/slides-live.html --sheet   # a PNG per slide, a contact sheet
lk review measure _build/slides-live.html           # free pixels above the foot line, wrapping bullets
lk review frags   _build/slides-live.html           # fragments per slide, misplaced clip fragments
lk review overflow slides.log                       # Beamer's overfull boxes
lk review figs    .                                 # the deck's TikZ figures as PNG, at live size
lk review contrast _brand.yml                       # WCAG AA on every surface
```

## Status

The engine builds the feature deck in both formats and in both presets, and
a project scaffolded by `lk new` builds from a fresh directory. The TikZ and
Manim kits (`tikzkit`, `nmstyle`, `nmnet`, `nmpix`, `nmfield`, `nmprf`) and
the worked example (the Coimbra kickoff deck) are being extracted from the
course project that this repository generalises; what is here under
`lecturekit.tikz` and `lecturekit.manim` is the token layer they will sit on.
manim8, the deeper animation layer, is planned as an optional extra for the
second release; its seam (`.movie` fields and `clips.json`) is defined now.

## Licence

MIT for the engine (see `LICENSE`); the example deck's content is CC BY 4.0.
Bundled fonts and third-party notices are listed in `NOTICE.md`.
