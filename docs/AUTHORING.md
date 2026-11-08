# Authoring a deck

One source, two teaching outputs. Approved 13 October 2026: the browser presentation supports live teaching; the PDF is the authoritative student study version. This page is the reference for the dialect that lecturekit's two Quarto formats, `lecturekit-revealjs` (the live deck) and `lecturekit-beamer` (the study PDF), read from a deck's `slides.qmd`. Everything not described here is ordinary Quarto Markdown and behaves as Quarto documents it.

The geometry of a slide and the command that checks each rule are in [LAYOUT.md](LAYOUT.md), the per-deck method in [WORKFLOW.md](WORKFLOW.md), what goes on a slide in [POLICY.md](POLICY.md), figures in [FIGURES.md](FIGURES.md), clips in [CLIPS.md](CLIPS.md), the theme in [THEMING.md](THEMING.md). The worked example is `examples/kickoff`; `examples/features/slides.qmd` exercises every construct on this page, one per slide.

## Editorial contract

- Every required learning outcome, definition, interpretation, caveat and self-check answer must be understandable from the PDF alone.
- Shared explanations live once in the source. Speaker notes contain delivery cues and optional elaboration.
- Motion has a static equivalent: a labelled figure, an annotated sequence, or a complete explanation.
- Study output has no hidden answers, progressive reveals or embedded video.
- Both outputs share the bibliography, the TeX Gyre Heros and Pagella typography (since 26 October 2026), all-cap headings, role labels and colours. Layout and slide counts may differ.
- Build the PDF through Beamer, not by printing the browser deck. Edit `slides.qmd`, never the generated HTML, LaTeX or PDF.

## The project

A deck is a Quarto project. `lk new <dir>` writes one: `_quarto.yml`, `_brand.yml` (the look, see THEMING.md), `_brand-dark.yml` and `_quarto-dark.yml` (the dark preset), `slides.qmd`, `make_assets.py`, `anim/kit.py`, `references.bib`, the method's files (`STORYBOARD.md`, `PLAN.md`, `FACTS.md`, `MANIFEST.md`, `README.md`, `AGENTS.md`), the `assets/` folders, and a copy of the engine's extension in `_extensions/lecturekit/`. Quarto's convention is that a project vendors the extension it builds with; `lk new --vendor-only <dir>` adds the extension to an existing project, `quarto add tknapen/lecturekit` does the same without the Python package, and `lk build` refuses to build when the vendored extension and the installed engine differ in major version.

The kickoff example's `_quarto.yml`:

```yaml
project:
  type: default
  output-dir: _build
  render:
    - slides.qmd
  pre-render:
    - make_assets.py            # the TikZ figures from assets/data, on lecturekit.tikz
  resources:
    - assets/**                 # the clip and the data, referenced from raw HTML

format:
  lecturekit-revealjs:
    output-file: slides-live.html
  lecturekit-beamer:
    output-file: slides-study.pdf

brand: _brand.yml
```

The resources rule: clips, stills and data files are referenced from raw HTML that Quarto does not scan for dependencies, so `resources: [assets/**]` tells Quarto to copy `assets/` into the output directory. Without it the live deck in `_build/` has no clips. `lk new` writes the anchored form `/assets/**`, which Quarto reads relative to the project rather than to the output directory.

What the two formats set: the live deck is 1280 by 720 with a 3 percent margin, fade transitions, linear navigation, mathematics as MathML, and no controls, progress bar or slide number, because the foot shows the position. The study PDF is Beamer at 16:9, 12 pt, top-aligned frames, compiled with XeLaTeX; the Beamer source `slides.tex` and its log `slides.log` are kept beside `slides.qmd` for the overflow check. Both formats make a slide of every level-two heading and run the bibliography through citeproc.

## Front matter

The kickoff deck's header:

```yaml
---
title: "Welcome to the Popylar workshop"
subtitle: "Population receptive field modelling with prfmodel: where it came from, what we meant to build, and where we stand"
shorttitle: "Coimbra · Welcome"
eyebrow: "Popylar pRF workshop · Coimbra · Thursday 5 November 2026, 09:00"
author: "Tomas Knapen"
date: ""
budget: 15
bibliography: references.bib
citation-size: small
---
```

| Key | Meaning |
| --- | --- |
| `title`, `subtitle`, `author`, `institute`, `date` | The title slide and the PDF's title page: eyebrow, the title in capitals, a short rule, the subtitle in muted serif, author and date in sans. |
| `shorttitle` (alias `short-title`) | The running foot on every content slide, in muted small capitals beside "n / total". Without it the foot uses the full title. |
| `eyebrow` (alias `series`) | The small letterspaced line above the main title, for the course or workshop name and the date. |
| `budget` | The planned minutes of the whole deck. The timing report compares the plan with it; the pacing clock shows it. |
| `citation-size: small` | Sets every in-text citation smaller in both outputs, so that the claim carries the line. |
| `bibliography` | The BibTeX file for `[@key]` citations. |

The filter writes `shorttitle`, `eyebrow` and the citation size for Beamer into `_lecturekit/<deck>-deck.tex` (`\nmShortTitle{}`, `\nmEyebrow{}`, `\lkCitationSmalltrue`), which the theme inputs; in the browser they become `data-eyebrow` and `data-budget` on the title slide and the per-slide foot.

## Slides, roles and times

Use level-two headings for slides and a role attribute:

```markdown
## A first crossing gives the decision {role=concept time=2}

**Decision time** is the time to reach either bound.
```

The role becomes the eyebrow, the small letterspaced label above the title, with its rule and colour, in both outputs: a CSS class and data attributes in the browser, the `nmrole` frame option in Beamer. A role name as a class is accepted too (`{.concept}`). A heading without a role is an explanation. An unknown role stops the build. The roles and their labels:

| Role | Eyebrow | Colour and surface |
| --- | --- | --- |
| `explanation` (default) | EXPLANATION | heading colour on white |
| `concept` | CORE CONCEPT | concept blue |
| `caveat` | CAVEAT / INTERPRET WITH CARE | caveat red |
| `example` | WORKED EXAMPLE (the study PDF adds FOLLOW THE STEPS) | example amber |
| `goals` | LEARNING GOALS | anchor teal on warm paper |
| `summary` | TAKEAWAYS | anchor teal on warm paper |
| `question` | CHECK YOUR UNDERSTANDING | question purple |
| `section` | NEXT PART | anchor teal on warm paper; a divider for a recording cut into parts |
| `pause` | PAUSE THE RECORDING | question purple on warm paper; a recorded lecture's prompt to stop and think |
| `detection`, `estimation`, `discrimination` | MAPS, ESTIMATION, DISCRIMINATION | the three objectives of the pRF workshop decks (2 November 2026): concept, state and context colours, each with its icon before the label |
| `where`, `how`, `what`, `when` | WHERE, HOW, WHAT, WHEN | the four dimensions of the advanced-models lecture: heading colour, an icon each |

`label="..."` replaces the eyebrow text and keeps the role's colour (`eyebrow="..."` is accepted as an alias); in Beamer it becomes `\slidecue{...}`. What the roles mean and how many of each a lecture takes is in POLICY.md.

`time=` is the slide's planned minutes, decimal where needed (`time=1.5`). A heading without `time=` is listed as untimed in the report. The live deck carries the plan as `data-timing` seconds for the pacing clock (see Pacing below).

`flash=500` on a heading makes a brief-exposure slide in the browser: after a short fixation cross the slide's image is shown for that many milliseconds, then blanked; the title stays, and R shows it again.

A title longer than 30 characters wraps in the serif capitals. The build warns on the terminal ("Title may wrap") when a title exceeds 32 characters; `lk review measure` flags every title over 30 characters and every title set on two lines.

## Live-only and study-only

Content for one output only is marked `.live-only` or `.study-only`. The filter removes the other output's content before Quarto splits the slides, so what remains is laid out as if the removed part had never been written.

On a fenced Div, the Div goes:

```markdown
::: {.study-only}
**Answer.** The live deck decides the pixel budget; the study PDF reflows what it drops.
:::
```

On a slide heading, the heading and its whole slide go, up to the next level-two heading:

```markdown
## Study-only detail {.study-only role=example time=0}
```

A study-only slide is not counted in the live foot's total and its minutes appear in the study report only. The classes combine with `.fragment`: `::: {.fragment .live-only}` is a step that exists only live, the usual form for a quiz answer that the PDF carries in a `.study-only` block instead.

### Paired visuals

The pattern for a clip with its static equivalent:

```markdown
## Why we are here {role=concept time=2}

:::: {.live-only}
::: {.movie src="assets/clips/bar-bold.mp4" label="A bar sweeps across the visual field; the predicted BOLD response follows"}
:::
::::

::: {.study-only}
\nmfigureh{3.8cm}{assets/figures/bar-bold.tex}
:::
```

Use local paths without spaces for movies. Put assets beside the source; the resources rule copies them into the live output. Check scale visually; a height that suits one figure is not universal.

### Live widgets

A raw HTML block inside a `.live-only` Div reaches the browser deck unchanged and is dropped from the PDF, so a slide can carry a small interactive piece with a script from the deck's `assets/`. Give the slide a `.study-only` alternative (a figure of a sample run) so that the PDF carries the same content, keep keyboard shortcuts away from Reveal's (digits are free; letters such as b, f, s and o are not), and test it in the browser check (`lk review shoot` reports page errors).

## Speaker notes

Speaker cues belong in a `notes` Div at the end of the slide. They show in the speaker view of the live deck (S) and nowhere else; the study PDF drops them (raw `\note{}` too). The method asks for four lines:

```markdown
::: notes
Line: the one sentence the slide exists for.
Ask: the question to the room, and its answer.
Say: what to say beyond the slide.
Status: where the numbers come from ([SIM], [DRAWN], [LIT]); draft, reviewed or final.
:::
```

Essential answers must also appear in shared or study-only text.

## Reveals

The default is a complete slide (POLICY.md). Where the order is the explanation:

- `::: incremental` around a list reveals it item by item in the browser; the PDF displays the complete list. A nested list reveals with its parent, which is how two or three lines that belong together appear together.
- `::: {.fragment}` around a block is one step. Write fragments as Divs; Pandoc's `. . .` pause splits the study page into overlays, which the method does not want.
- A staged figure is an `.r-stack` of the stages inside `.live-only`, each later stage in a `.fragment`, with the final stage in a `.study-only` block for the page:

```markdown
:::::: {.live-only}
::::: {.r-stack}
\nmfigureh{3.9cm}{assets/figures/engine-0.tex}

:::: {.fragment}
\nmfigureh{3.9cm}{assets/figures/engine.tex}
::::
:::::
::::::

::: {.study-only}
\nmfigureh{3.5cm}{assets/figures/engine.tex}
:::
```

Once a later step of a stack is visible, every earlier step fades out, so figures of different extent never show through one another; the stages should still share a bounding box (FIGURES.md). `lk review frags <live.html>` shows what each step contains; `lk review shoot --fragments` writes a PNG per step.

## Figures

A figure is a TikZ picture, compiled once with the deck's fonts and colour tokens and placed in both outputs. Four ways to put one on a slide:

````markdown
\nmfigureh{4.2cm}{assets/figures/name.tex}        a figure file beside the deck, height-capped (bare, or in a {=latex} block)
\nmfigure{assets/figures/name.tex}                 the same, width-capped only
\input{assets/figures/name.tex}                    the same, no cap
![](assets/figures/name.tex){height=4.2cm}         the same file as an image link (.tex or .tikz)

```{.tikz height=3.6cm label="clock"}
\begin{tikzpicture}
  \draw[nm/hairline] (0,0) circle (1.6cm);
  \node[nm/muted, below=1.75cm] at (0,0) {15 of 15 minutes};
\end{tikzpicture}
```
````

In the study PDF `\nmfigureh` inputs the file in the frame, scaled down to the text width and the given height when it is larger, never up; `\nmfigure` caps the width only. In the live deck each picture becomes a standalone XeLaTeX document with the brand's fonts, colours and named styles, converted to an SVG with text as paths, so the browser needs no fonts. The SVG arrives at the figure's proportion on the study page (1280 px for the 453.54 pt frame) and the height cap carries over as a `max-height` at 8.8 px per mm; a figure is never upscaled beyond its natural size, so figures are drawn at display size (FIGURES.md). Figures are cached in `_lecturekit/tikz/` under a hash of their full source and rebuilt only when that changes. A figure that fails to compile becomes a labelled placeholder so that the deck still builds; its log stays in `_lecturekit/tikz/`.

## Images

A print height on an image, `{height=42mm}` or `{height=4cm}`, sizes the study page; the filter turns it into a `max-height` for the browser at 8.8 px per mm (a 720 px slide for a 90 mm frame, plus a tenth for the smaller body type). Without a height, the theme caps images at 420 px (raster) and 400 px (TikZ). Width percentages apply to both outputs.

On goals, summary, section and pause slides (warm paper) every image is composited with the multiply blend mode in both outputs, so a figure's white background becomes the slide background without editing the file. `{.keepwhite}` opts an image out (white markers on a coloured field), `{.paper}` applies the treatment on a white slide, where it changes nothing visible. The same applies to a `.movie`.

A row of images, `::: {.row live-height=205px}` around one paragraph of images with `{height=20mm}`, lays them out side by side in the browser at the given height and leaves the page at the print height.

`::: {.small}` sets its contents (a wide table, say) in `\small` on the page and at 25 px in the browser.

## Movies

A clip is a `.movie` Div. Three forms:

```markdown
::: {.movie src="assets/clips/bar-bold.mp4" label="what the clip shows"}
:::
```

inside a `.live-only` block with a `.study-only` alternative, as in Paired visuals above; `label` is the accessible name. `aspect="4:3"` or `aspect="1:1"` keeps a clip's own shape, for a clip in a column; any other `aspect="W:H"` in whole numbers (a clip cropped to its content) is set on the wrapper as an aspect ratio.

```markdown
::: {.movie clip="bar-bold" height=4cm}
A one-line caption, set small and muted under the clip; on the page it follows the still.
:::
```

names a clip in `assets/clips/clips.json`, which `lk clips` writes (CLIPS.md). The entry supplies the video, the still, and the width and height that become the aspect, so this form needs no `.live-only` wrapper: the live deck gets a boxed video with the still as poster, the study PDF gets the still at `height=` (default 4 cm) through `\lkimageh`, which never upscales. A `clip=` name that is not in the index and has no `src=` stops the build.

```markdown
::: {.movie src="assets/clips/name.mp4" still="assets/clips/name.png"}
:::
```

names the still explicitly; a `.png` of the same name beside the video is picked up without `still=`. A `.movie` without a still and outside `.live-only` is an error: "Wrap a movie in .live-only and supply a study alternative". Every clip has a static equivalent in the study PDF, as the policy requires.

In the browser a clip starts when its slide appears and pauses when the slide is left; it is muted and has no browser controls. A click or the space bar pauses and resumes it (space does not advance the slide while a clip is shown), R replays it from the start. A clip slide, one `.movie` in `.live-only`, gives the clip everything below the title at 16:9; a clip among other content is 440 px tall. A clip on a key press puts the fragment outside the live-only block, never inside it: `::: {.fragment}` around `:::: {.live-only}` around the `.movie`; `lk review frags` flags the reverse. A sequence of clips is an `.r-stack` inside `.live-only`, each later clip in a `.fragment`; the step's clip starts when its fragment appears and the earlier one stops.

## Colour emphasis and coloured spans

Each slide colours the words that carry it (rule of 27 October 2026, POLICY.md): `[words]{.blue}` for the term or claim to keep, `[words]{.red}` for the trap, the contrast, what is not the case or what still has to be shown. One to three coloured phrases per slide. The browser gets the class, the page `\textcolor`. The spans and their tokens:

| Span | Token | Use |
| --- | --- | --- |
| `.blue` | `nmInput` | the term or claim to keep |
| `.red` | `nmCaveat` | the trap, the contrast |
| `.teal`, `.purple`, `.orange` | `nmState`, `nmContext`, `nmUpdate` | a word that names an element drawn in a mark colour |
| `.gauss` | `nmGauss` | a project token (the Gaussian model's blue of the workshop figures) |
| `.grey`, `.muted` | `nmMuted` | a reference curve, a secondary remark |
| `.concept`, `.caveat`, `.example`, `.anchor`, `.question` | the role colours | a word in a role's colour |
| `.mark-input`, `.mark-state`, `.mark-update`, `.mark-context` | the mark colours | the same as the colour names above, by meaning |

## Citations and references

`[@Key]` cites an entry of the bibliography; a narrative citation (`@Key`) is shorter than a parenthetical one when the sentence is about the paper. Every in-text citation, parenthetical or author-in-text, is set in italics in both outputs (rule of 27 October 2026); `citation-size: small` in the header sets them in `\footnotesize` on the page and at 0.68 em in the browser. Nothing to do in the source.

The bibliography appends to the last slide unless the deck ends with a references heading:

```markdown
## References {.references .allowframebreaks role=explanation}
```

Since 19 October 2026 the references are set in footnote size with half a line between entries, so a page holds four to six entries instead of two or three, and the frame breaks when they are more; the browser scrolls a long list within the slide.

## Mathematics

Use ordinary dollar-delimited mathematics, `$...$` inline and `$$...$$` display; both render in both outputs. Beamer uses TeX Gyre Pagella Math, bundled with the extension. The browser uses native MathML (`html-math-method: mathml`) and the math font it has (TeX Gyre Pagella Math where installed, else STIX Two Math or Cambria Math); exact browser math-font matching is not implemented, and no remote math renderer is needed. A line of inline equation pieces centred like a display equation is `::: {.eqline}` (MathML has no colour command, so a coloured term is a coloured span around an inline piece).

## Pacing and the timing report

Put the planned minutes on each slide heading and a `budget:` in the header. After each render the filter prints the plan against the budget and, for the live render, writes it to `timing.txt` in the output directory (`_build/timing.txt`); `lk build` prints the report last and names the file. The kickoff deck's report:

```text
  min     at  role         slide
    2      2  concept      Why we are here
    2      4  explanation  Credit where credit is due
    2      6  concept      What we proposed: an engine
    2      8  concept      What we proposed: a community
    3     11  explanation  Where we stand: prfmodel 0.2.0
    2     13  concept      The person who built it
    2     15  summary      Two days
    -     15  explanation  References
slides 8  planned 15 min  untimed 1  budget 15 min  ok
```

The columns are the slide's minutes, the cumulative minutes, the role and the title; the last line sums the plan and says `ok` or `OVER` against the budget. Over is a warning, not an error. The study render prints its own report (study-only slides included) and writes no file.

In the browser the same numbers drive the pacing clock in the speaker view (S): elapsed time against the plan up to the current slide, the difference, and the budget from the title slide. It turns red when more than a minute behind and teal when more than a minute ahead; P resets it. Planning first and timing a rehearsal against the plan is how topics fit.

## Profiles

A preset is a second brand file and a Quarto profile that selects it:

```yaml
# _quarto-dark.yml
project:
  output-dir: _build-dark
brand: _brand-dark.yml
brand-mode: dark
```

`lk build --profile dark` (or `quarto render --profile dark`) builds both outputs in the preset into `_build-dark/`; the default build is untouched. THEMING.md says what a preset may change and what a restyle regenerates.

## Where outputs go

| Path | What |
| --- | --- |
| `_build/slides-live.html` | the live deck, with `_build/slides_files/` (Reveal.js and its plugins) and `_build/_lecturekit/tikz/` (the figures' SVGs) |
| `_build/slides-study.pdf` | the study PDF |
| `_build/assets/` | the copy made by the resources rule: clips, stills, data |
| `_build/timing.txt` | the timing report of the live render |
| `_lecturekit/` beside the source | the cache and the tokens: `tokens.tex` and `tokens.css` from the brand, `<deck>-deck.tex` from the front matter, `tikz/` with each figure's standalone `.tex`, `.pdf`, `.svg` and `.log` under its hash |
| `slides.tex`, `slides.log` beside the source | the Beamer source and log, kept for `lk review overflow` |

`lk build --to live` or `--to study` renders one output. The build directories, the cache and the kept LaTeX files are ignored by git; the sources and `assets/` are what a project commits.

## A complete short example

A condensed `examples/features/slides.qmd`: a goals slide on paper, a figure, columns with an inline picture, a clip through the seam, a reveal, a quiz with its answer, citations, a study-only page, takeaways and the references.

````markdown
---
title: "Every feature on one deck"
subtitle: "The lecturekit dialect, slide by slide"
shorttitle: "Features"
eyebrow: "lecturekit · the feature deck"
author: "Tomas Knapen"
date: ""
budget: 15
bibliography: references.bib
citation-size: small
---

## What this deck is for {role=goals time=1}

- Every construct of the dialect, one per slide, so that a change to the engine is seen in both outputs.
- A paper slide: [learning goals and takeaways]{.blue} sit on warm paper, with a teal label.

## One source, two outputs {role=concept time=2}

\nmfigureh{4.2cm}{assets/figures/pipeline.tex}

- Write one `slides.qmd`; render [a live deck and a study PDF]{.blue}.
- A heading carries a [role]{.blue} and the planned minutes; the figure is TikZ, drawn at display size.

::: notes
Line: the method in one sentence.
Ask: who has kept two versions of the same lecture in sync by hand?
Say: the filter is the only thing that knows about two outputs.
:::

## The budget is checked {role=caveat time=1.5}

:::: columns
::: {.column width="55%"}
- Every slide heading has `time=`.
- Over budget is [a warning, not an error]{.red}.
:::
::: {.column width="45%"}
```{.tikz height=3.6cm label="clock"}
\begin{tikzpicture}
  \draw[nm/hairline] (0,0) circle (1.6cm);
  \draw[nmCaveat, line width=1.6pt] (0,0) -- (60:1.1cm);
  \node[nm/muted, below=1.75cm] at (0,0) {15 of 15 minutes};
\end{tikzpicture}
```
:::
::::

## A clip through the seam {role=example time=1}

::: {.movie clip="bar_bold" height=4cm}
Named in `assets/clips/clips.json`: the live deck gets the video, the study PDF the still, and both the shape.
:::

## Revealed step by step {role=explanation time=1.5}

::: incremental
- First the question
- Then the data
- Then the model, and where it fails
:::

## A quiz carries its answer {role=question time=2}

Which of the two outputs decides the pixel budget of a slide?

::: {.fragment .live-only}
**The live deck.** 1280 by 720 pixels; the study PDF reflows what the live budget drops.
:::

::: {.study-only}
**Answer.** The live deck. 1280 by 720 pixels; the study PDF reflows what the live budget drops.
:::

## Citations and claims {role=concept time=1}

- The model: population receptive fields [@Dumoulin2008].
- Every number on a slide traces to `FACTS.md`; citations are set in italics and, here, small.

## Study-only detail {.study-only role=example time=0}

This slide exists only in the study PDF: a derivation, a table, or a figure
that the live budget drops but the reader wants.

## Takeaways {role=summary time=1}

- One source, [two outputs]{.blue}, one theme file.
- The study PDF is the whole argument; the live deck is its spine.

## References {.references .allowframebreaks role=explanation}
````

Build it with `lk build` in the project folder, open `_build/slides-live.html` and `_build/slides-study.pdf`, and read the timing report.

## Verification before a lecture

1. Build both outputs from the same source (`lk build`); inspect the PDF for complete explanations and answers.
2. Render and review every PDF page; resolve overflow (`lk review overflow <deck>`), missing glyphs and malformed mathematics.
3. Check the browser deck's fonts, equations, clips, reveals and slide boundaries (`lk review shoot <live.html> --sheet`, `lk review frags`, `lk review measure`).
4. Rehearse on the actual lecture machine, with the speaker view and its pacing clock; classroom equipment and presenter view need their own rehearsal.
5. Distribute the PDF as the study reference.
