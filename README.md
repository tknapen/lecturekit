# lecturekit

One Markdown source per lecture becomes a Reveal.js deck for the room and a Beamer PDF for study, with figures drawn
from numbers (TikZ), clips rendered from code (Manim), a timing budget checked at every build, and a review loop of
screenshots and log checks that keeps both outputs inside their frames. Built for a university course and a pRF
workshop; this repository is the engine extracted from them, as a Quarto extension and a Python package, so that a
project (a course, a workshop) depends on it instead of carrying it.

```sh
uv pip install -e ".[dev]"          # in a clone; docs/INSTALL.md installs from GitHub without one
lk build examples/kickoff           # _build/slides-live.html, _build/slides-study.pdf, the plan against the budget
lk new my-lecture && cd my-lecture && lk build
```

The build prints the plan against the budget:

```text
  min     at  role         slide
    2      2  concept      Why we are here
    2      4  explanation  Credit where credit is due
    ...
slides 8  planned 15 min  untimed 1  budget 15 min  ok
```

## Layout

```text
_extensions/lecturekit/   the Quarto extension: formats lecturekit-revealjs and lecturekit-beamer; the dialect
                          filter, the TikZ filter, the brand tokens; the Beamer theme and the live stylesheet
                          and script; the bundled fonts. A project vendors a copy (Quarto's convention).
src/lecturekit/           the Python package and the lk command: new, build, clips, theme, review; the TikZ kit
                          (tikzkit) and the Manim kit (nmstyle, nmnet, nmpix, nmfield, nmprf); the scaffold
examples/kickoff/         the worked example: the Coimbra workshop's opening deck with its storyboard, plan,
                          figures from make_assets.py, one clip, FACTS.md and MANIFEST.md
examples/features/        every construct of the dialect on one small deck; the engine's test deck
docs/                     AUTHORING (the dialect), LAYOUT (what fits where, with the check for each rule),
                          WORKFLOW (the per-deck method), POLICY, THEMING, FIGURES, CLIPS, MANIM, INSTALL
tutorials/                one folder per episode of the video series: script, prompts, before and after
AGENTS.md                 standing rules for an assistant working here (and for us)
```

## The dialect in one slide

```markdown
## Why we are here {role=concept time=2}

:::: {.live-only}
::: {.movie src="assets/clips/bar-bold.mp4" label="A bar sweeps the visual field"}
:::
::::

::: {.study-only}
\nmfigureh{3.8cm}{assets/figures/bar-bold.tex}
:::

- A pRF: [a model of what a neural population responds to]{.blue} [@DumoulinWandell2008].

::: notes
Line: the method in eighteen seconds.  Ask: who has fitted a pRF before?  Say: ...  Status: final.
:::
```

A heading's `role=` is its teaching role (explanation, concept, caveat, example, goals, summary, question, and the
workshop's own) and becomes the eyebrow in both outputs; `time=` feeds the plan. `.live-only` and `.study-only`
select an output, on a Div or on a whole slide. A `.movie` is an autoplaying clip without browser controls live
(click or space pauses, R replays) and a still in the PDF. Figures are TikZ files beside the deck, placed with
`\nmfigureh{height}{file}`, compiled once for the browser and set inline on the page, never scaled up.

## A clip in parts

One clip can play in parts, each started by the presenter's key and held exactly on the frame where it ends:

```markdown
::: {.movie clip="criterion_roc" stops="neutral strict" start=key}
:::: {.stop ref="start"}
Ask: if the criterion moves right, which rate falls faster?
::::
:::
```

The producer marks where a clip may hold, and `lk clips` lists those stops in `clips.json` with a still of each
frame: `checkpoint()` in a kit scene, `stop: true` on a manim8 snapshot, `lk clips adopt clip.mp4 --stops 4.0 8.0`
for an MP4 made elsewhere. The slide chooses the stops. A key pressed while a part plays lets it play on to the
next stop; Left holds the previous one at once; coming back to the slide holds its last frame without playing. The
speaker notes of each hold put its "Ask:" first, the study PDF prints a strip of the holds, and `lk review frags`
walks the clip with real keys and checks every hold's frame (docs/CLIPS.md, docs/AUTHORING.md).

## One theme, one file

The look is defined once, in Quarto's `_brand.yml`. Every palette entry is a token: `nmConcept` in Beamer and TikZ,
`--nm-concept` in the live deck, `CONCEPT` in Python. The fonts (TeX Gyre Heros and Pagella; Roboto for the dark
preset) are bundled and loaded by file, so a build is the same on every machine. A restyle is a second brand file
and a profile:

```sh
lk build examples/kickoff --profile dark
lk review contrast examples/kickoff/_brand-dark.yml --mode dark
```

## The review loop

```sh
lk review shoot   _build/slides-live.html --sheet     # a PNG per slide, what crosses the foot, page errors
lk review measure _build/slides-live.html             # free pixels above the foot line, wrapping bullets
lk review frags   _build/slides-live.html             # fragment steps, clips shown and playing, holds of a clip in parts
lk review overflow .                                  # overfull frames of the study PDF, by title
lk review figs    .                                   # the deck's TikZ figures standalone, with their sizes
lk review contrast _brand.yml                         # WCAG AA on every surface
```

## Status

The engine builds both example decks in both formats and both presets, and a project scaffolded by `lk new` builds
from a fresh directory; the figures of the worked example regenerate byte for byte from `make_assets.py` on the
kit. manim8, the deeper animation layer, is an optional extra on Python 3.12 (`lecturekit[manim8]`, pinned to
manim8's commit `fa99e8f`, its release 0.1.0a0 with stops (ADR-045); docs/INSTALL.md): `lk new --manim8` makes a project's `clips/` a manim8 workspace, `lk theme --manim8`
bridges the brand into manim8 styles for both presets, and `lk clips` renders kit scenes and manim8 projects alike
into `assets/clips/clips.json`, the seam that `clip=` on a movie block reads (docs/CLIPS.md).

## Licences

Code under MIT (`LICENSE`); the examples' content under CC BY 4.0; bundled fonts and third-party components in
`NOTICE.md`.
