# Authoring a deck

One Markdown file becomes a Reveal.js live deck and a Beamer study PDF. The two Quarto formats, `lecturekit-revealjs` and `lecturekit-beamer`, come from the extension vendored in the project's `_extensions/lecturekit/`. This page is the reference for the dialect those formats read. Everything not described here is ordinary Quarto Markdown and behaves as Quarto documents it.

The geometry rules are in [LAYOUT.md](LAYOUT.md), the method in [WORKFLOW.md](WORKFLOW.md), the writing rules in [POLICY.md](POLICY.md), figures in [FIGURES.md](FIGURES.md), clips in [CLIPS.md](CLIPS.md), the theme in [THEMING.md](THEMING.md).

## The project

A deck is a Quarto project: `_quarto.yml`, `_brand.yml`, `slides.qmd`, `assets/`, `references.bib`, and the extension in `_extensions/lecturekit/`. `lk new <dir>` writes all of it, with the method's files beside it (`STORYBOARD.md`, `PLAN.md`, `FACTS.md`, `MANIFEST.md`, `README.md`, `AGENTS.md`, `make_assets.py`). The complete small project in `examples/features/` is the reference; its `slides.qmd` exercises every feature on this page.

```yaml
# _quarto.yml
project:
  type: default
  output-dir: _build
  render:
    - slides.qmd
  resources:
    - assets/**

format:
  lecturekit-revealjs:
    output-file: slides-live.html
  lecturekit-beamer:
    output-file: slides-study.pdf

brand: _brand.yml

budget: 15
eyebrow-preset: course
short-title: features
bibliography: references.bib
```

The resources rule. Clips, stills and data files are referenced from raw HTML that Quarto does not scan for dependencies. `resources: [assets/**]` makes Quarto copy `assets/` into the output directory. Without that line the live deck in `_build/` has no clips.

Deck-wide options (`budget`, `eyebrow-preset`, `short-title`, `bibliography`) may sit in `_quarto.yml`, as above, or in the document's front matter. The front matter wins.

## Front matter

```yaml
---
title: "Every feature on one deck"
subtitle: "The lecturekit dialect, slide by slide"
author: "Tomas Knapen"
institute: "Vrije Universiteit Amsterdam"
date: 2026-11-08
series: "lecturekit features"
---
```

| Key | Meaning |
| --- | --- |
| `title`, `subtitle`, `author`, `institute`, `date` | The title slide and the PDF's title frame. `author` and `institute` may be lists. |
| `series` | A small uppercase line above the title (the title eyebrow), for the course or workshop name. `eyebrow` in the front matter overrides it. |
| `short-title` | The deck's name in the live foot and the PDF footline. Defaults to `title`. |
| `budget` | Planned minutes for the whole deck, as decimal minutes or `m:ss`. The formats default to 45. |
| `eyebrow-preset` | The role vocabulary: `course` (default), `prf` or `none`. See the next section. |
| `bibliography` | A BibTeX file for `[@key]` citations. |
| `slide-level` | The heading level that makes a slide. The formats set 2; leave it. |
| `timing-file` | Where the timing report is written, relative to the source. Default `timing.txt`. |

## Slide headings: role and time

Every `##` heading starts a slide. Its attributes carry the teaching role and the planned minutes:

```markdown
## One source, two outputs {.concept time=2}

## The budget is checked {.caveat time=1:30}
```

The role becomes the eyebrow, the small uppercase label above the title, set in the role's colour in both outputs. The time is summed into the timing report. `time=` takes decimal minutes (`1.5`) or minutes and seconds (`1:30`). A heading without `time=` counts as zero and shows `-` in the report.

The `course` preset has five roles: `concept`, `caveat`, `example`, `anchor`, `question`, labelled Concept, Caveat, Example, Anchor, Question. The `prf` preset has four: `where`, `how`, `what`, `when`, labelled WHERE, HOW, WHAT, WHEN and drawn in the concept, example, anchor and question colours. A role from the other preset is still recognised and labelled with its own name. What the roles mean is in POLICY.md.

`#` headings are section dividers. They get no eyebrow and no time.

## Eyebrow override

`eyebrow=` replaces the label and keeps the role's colour:

```markdown
## Where we are {.anchor time=1 eyebrow="Recap"}
```

`eyebrow=` on a heading without a role gives a label in the muted colour.

## Speaker notes

Notes go in a `notes` Div at the end of the slide. They show in the live deck's speaker view (press S) and nowhere else; the study PDF drops them. The method asks for four lines, each optional:

```markdown
::: notes
Line: the one sentence this slide exists for.
Ask: the question to put to the room, if any.
Say: what to say that is not on the slide.
Status: draft, reviewed or final, and what is still open.
:::
```

## Fragments

A `.fragment` Div appears on a key press in the live deck. The study PDF shows every fragment at once, in place.

```markdown
::: {.fragment}
- First the question
:::
::: {.fragment}
- Then the data
:::
```

Write fragments as Divs. Pandoc's `. . .` pause becomes `\pause` in Beamer and splits the study page into overlays, which the method does not want. `lk review frags <deck.html>` lists the fragments per slide; `lk review shoot <deck.html> --fragments` writes one PNG per step.

## Live-only and study-only

Content for one output only is marked `.live-only` or `.study-only`. The filter removes the other output's content before Quarto splits the slides, so what remains is laid out as if the removed part had never been written.

On a Div, the Div goes:

```markdown
::: {.live-only}
Click the clip to pause, R to replay.
:::

::: {.study-only}
**Answer.** The live deck decides the pixel budget; the study PDF reflows what it drops.
:::
```

On a slide heading, the heading and its whole slide go, up to the next heading of the same or a higher level:

```markdown
## Study-only detail {.study-only .example time=0}

A derivation, a table, or a figure the live budget drops but the reader wants.
```

Give a study-only slide `time=0`. It is absent from the live deck's report, and `time=0` keeps the study report's total equal to it. The classes combine with `.fragment`: `::: {.fragment .live-only}` is a step that exists only live, the usual form for a quiz answer that the PDF carries in a `.study-only` block instead.

## Columns

Quarto's columns keep a figure beside its text:

```markdown
::: columns
::: {.column width="55%"}
- Every slide heading has `time=`
- The build prints the plan against the budget
:::
::: {.column width="45%"}
![](assets/figures/clock.tikz){height=3.6cm}
:::
:::
```

In the live deck the columns are a flex row with a 32 px gap. In the study PDF they are Beamer columns, which do not shrink: a text column beside a tall figure must end above the footline on its own. `lk review overflow <deck.log>` reports it when it does not.

## TikZ figures

A figure is TikZ, compiled once with the deck's fonts and colour tokens, cached, and placed in both outputs. Two forms:

````markdown
![](assets/figures/pipeline.tikz){height=4.2cm}

```{.tikz height=3.6cm label="clock"}
\begin{tikzpicture}
  \draw[nm/hairline] (0,0) circle (1.6cm);
  \node[nm/muted, below=1.75cm] at (0,0) {15 of 15 minutes};
\end{tikzpicture}
```
````

The file form points at a `.tikz` (or `.tikz.tex`) file holding a `tikzpicture`, usually written by the deck's `make_assets.py`. The block form holds the picture inline; `label=` names it in messages and in the alt text. `height=` is a maximum, in cm or px, and the figure is never scaled up: 1 cm is 80 px of the live frame. The study PDF places the figure with `\lkfigureh{height}{file}`, the live deck with an `<img>` at the figure's drawn size, capped at the same height. A figure that fails to compile becomes a labelled placeholder so that the deck still builds, and its log stays in `_lecturekit/tikz/`. The styles, the kit and the traps are in FIGURES.md.

## Movie blocks

A clip is a `.movie` Div. Its content, if any, is the caption.

```markdown
::: {.movie clip="bar_bold" still="assets/clips/bar_bold.png" aspect=1.78 height=4.4cm}
A bar sweeps the visual field; the BOLD response of one voxel follows.
:::
```

| Attribute | Meaning |
| --- | --- |
| `clip` | A name looked up in `assets/clips/clips.json` (written by `lk clips`), or a path to an `.mp4` or `.webm`. `src` is accepted as an alias. |
| `still` | The frame the study PDF prints and the live deck shows before playback. Default: the `still` of the clips.json entry, else a `.png` beside the video with the same name. |
| `aspect` | Width over height, used to reserve the clip's box before the video loads. Default: the clips.json `width` over `height`. |
| `height` | Maximum height, cm or px, 80 px per cm. The study PDF defaults to 4.2cm; the live deck caps only when a height is given. |

Live, the clip autoplays when its slide or fragment appears, a click pauses and resumes it, and R replays the clips on the current slide. Study, the still is placed with `\lkfigureh`. A clip that cannot be resolved becomes a placeholder reading `clip missing: <name>`. A clip that is a fragment goes in a `.fragment` wrapper inside `.live-only`, never as a class on the `.movie` Div itself; see CLIPS.md and LAYOUT.md.

## Citations

`[@Hedger2025]` cites an entry of the `bibliography` file. The citation style, `_extensions/lecturekit/lecturekit.csl`, is Chicago author-date with the author names in italics: `(Hedger et al. 2025)`, names in italic, in both outputs. The bibliography is printed where the `refs` Div stands, usually on a last slide:

```markdown
## References {time=0}

::: {#refs}
:::
```

Neither output breaks a long bibliography across pages. Keep the slide to the entries that fit, or make two References slides; `lk review overflow` reports the study side, `lk review measure` the live side.

## Coloured spans

`[text]{.concept}` colours a span in the role's colour. The five roles and the four marks (`.mark-input`, `.mark-state`, `.mark-update`, `.mark-context`) are available in the live deck. In the study PDF these spans print in the text colour in the present version; the macros `\lkconcept{...}`, `\lkcaveat{...}`, `\lkexample{...}`, `\lkanchor{...}` and `\lkquestion{...}` exist for raw LaTeX. Colour is a signal, not decoration: POLICY.md says what each colour means.

## Math

Inline `$...$` and display `$$...$$` work as in Quarto: MathJax in the live deck, `unicode-math` with the deck's math font in the study PDF (set `mathfont` under the Beamer format in `_quarto.yml`, see THEMING.md). Display math is set at the body size and takes about one and a half lines. One display equation per slide is the layout rule; LAYOUT.md has the numbers.

## The timing report and timing.txt

Each render prints the plan against the budget to the terminal and writes the same text to `timing.txt` beside the source:

```text
lecturekit timing (live): 7 slides,  10' planned, budget  15'
   1  concept     2'    2'  One source, two outputs
   2  caveat      1'30    3'30  The budget is checked
   3  example     2'    5'30  A clip, autoplaying
   4  anchor      1'30    7'  Fragments and live-only steps
   5  question    2'    9'  A quiz carries its answer
   6  concept     1'   10'  Citations and claims
   7  -           0'   10'  References
  under budget by   5'
```

The columns are the slide number, the role, the slide's time, the cumulative time and the title. The last line says on budget, over, or under; over is a warning, not an error. `lk build` prints the report; `timing.txt` holds the report of the format rendered last. The same cumulative times drive the pacing clock in the speaker view, which compares the elapsed time with the plan at the current slide, turns red when more than a minute behind, and resets on P.

## Profiles

A preset is a Quarto profile: `_quarto-dark.yml` beside `_quarto.yml` overrides the brand and the output directory.

```yaml
# _quarto-dark.yml
project:
  output-dir: _build-dark
brand: _brand-dark.yml
brand-mode: dark
```

`quarto render --profile dark`, or `lk build --profile dark`, renders both outputs in the dark preset into `_build-dark/`. THEMING.md describes what a preset may change.

## Where outputs go

`quarto render`, or `lk build`, writes into `_build/`:

| Path | What |
| --- | --- |
| `_build/slides-live.html` | the live deck |
| `_build/slides-study.pdf` | the study PDF |
| `_build/assets/` | the copy made by the resources rule |
| `_build/_lecturekit/tikz/` | the figures' SVG and PDF files, referenced by the outputs |
| `_build/slides_files/libs/` | Reveal.js and its plugins |
| `_build/pacing.js`, `_build/movie.js` | the live deck's scripts |

Beside the source the build leaves `_lecturekit/` (the tokens as `tokens.tex` and `tokens.css`, and the TikZ cache keyed by content hash), `timing.txt`, `slides.tex` (the Beamer source, kept by `keep-tex`) and copies of the two scripts. The Beamer log, which `lk review overflow` reads, survives only when the Beamer format is given `latex-clean: false`.

`lk build --to live` or `--to study` renders one output. With Quarto alone: `quarto render --to lecturekit-revealjs` or `--to lecturekit-beamer`.

## A complete example

A condensed version of `examples/features/slides.qmd`: a title, four slides and the references, 7 minutes of a 10 minute budget.

````markdown
---
title: "Every feature on one deck"
subtitle: "The lecturekit dialect, slide by slide"
author: "Tomas Knapen"
institute: "Vrije Universiteit Amsterdam"
date: 2026-11-08
series: "lecturekit features"
short-title: features
budget: 10
eyebrow-preset: course
bibliography: references.bib
---

## One source, two outputs {.concept time=2}

- Write one `slides.qmd`; render a live deck and a study PDF
- Headings carry a teaching role and the planned minutes

![](assets/figures/pipeline.tikz){height=4.2cm}

::: notes
Line: the method in one sentence.
Ask: who has kept two versions of the same lecture in sync by hand?
Say: the filter is the only thing that knows about two outputs.
Status: final.
:::

## A clip, autoplaying {.example time=2}

::: {.movie clip="bar_bold" height=4.4cm}
A bar sweeps the visual field; the BOLD response of one voxel follows.
:::

::: {.live-only}
Click the clip to pause, R to replay.
:::

## A quiz carries its answer {.question time=2}

Which of the two outputs decides the pixel budget of a slide?

::: {.fragment .live-only}
**The live deck.** 1280 by 720 pixels; the study PDF reflows what the live budget drops.
:::

::: {.study-only}
**Answer.** The live deck. 1280 by 720 pixels; the study PDF reflows what the live budget drops.
:::

## Citations and claims {.concept time=1}

- The model: population receptive fields [@Dumoulin2008]
- The result: joint visual and somatotopic tuning [@Hedger2025]
- Every number on a slide traces to `FACTS.md`

## Study-only detail {.study-only .example time=0}

This slide exists only in the study PDF: a derivation, a table, or a figure
that the live budget drops but the reader wants.

## References {time=0}

::: {#refs}
:::
````

Build it with `lk build` (or `quarto render`) in the project folder, open `_build/slides-live.html` and `_build/slides-study.pdf`, and read the timing report.
