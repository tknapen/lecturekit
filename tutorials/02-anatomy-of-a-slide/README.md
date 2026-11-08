# Episode 2: Anatomy of a slide

Length: 8 minutes.

## Goal

Read the kickoff deck's source and see each element of the dialect land in both outputs: a heading with role and time, notes with Line / Ask / Say / Status, a staged figure in an r-stack, live-only and study-only content, a movie block, coloured spans, a citation.

## What the viewer sees

`examples/kickoff/slides.qmd` in an editor on one half; the live deck and the PDF on the other. Each element is pointed to in the source, then found in the outputs. Two edits, each followed by a rebuild: a slide's time changes and the report goes over budget; a `.study-only` paragraph is added and appears only in the PDF.

## Commands

```sh
cd examples/kickoff
$EDITOR slides.qmd
lk build .
```

## The walk through the source

Slide numbers as the foot shows them: the title slide is 1.

| Source | Live deck | Study PDF |
| --- | --- | --- |
| `shorttitle: "Coimbra · Welcome"`, `eyebrow: "Popylar pRF workshop · ..."`, `budget: 15` | the foot on every slide; the line above the title; the pacing clock's budget | the footline; the title page |
| `## Why we are here {role=concept time=2}` | eyebrow CORE CONCEPT in blue, its rule, the title in capitals; 2 minutes in the report | the same eyebrow and rule above the frame title |
| `::: notes` with Line / Say / Ask / Status | S shows them in the speaker view | absent |
| `:::: {.live-only}` around `::: {.movie src="assets/clips/bar-bold.mp4" label="..."}` | the clip plays; click, space, R | absent |
| `::: {.study-only}` around `\nmfigureh{3.8cm}{assets/figures/bar-bold.tex}` | absent | the static equivalent, drawn from the same forward model, 3.8 cm |
| `[a model of what a neural population responds to]{.blue}` | the phrase in the course blue | `\textcolor{nmInput}` |
| `[limited model coverage, fragmented development]{.red}` (slide 3) | the trap in caveat red | the same |
| `[@DumoulinWandell2008]`, with `citation-size: small` | the citation in italics, small | the same; the References frame at the end |
| the `.r-stack` of `engine-0.tex` and `engine.tex` on slide 4, the second in a `::: {.fragment}` | the pipeline's forward half, then the fitting loop on a key press | the complete figure, from the `.study-only` block |
| `## References {.references .allowframebreaks role=explanation}` | the list, scrolling within the slide | footnote-size entries, breaking across frames when needed |

## The two edits

1. Change `time=2` to `time=3` on Why we are here. `lk build .` prints `planned 16 min ... budget 15 min  OVER`; over budget is a warning, not an error.
2. Under the bullets of Credit where credit is due add `::: {.study-only}` with one sentence, `:::`. Rebuild. The PDF shows it; the live deck does not, and the live foot still says 9 slides.

## Artefacts

- `before/slides.qmd`: the example as shipped.
- `after/slides.qmd`: with the two edits.
- `after/timing.txt`: the report after edit 1.
- `after/slide-03-live.png` and `after/slide-03-study.png`: the slide after edit 2.

## Notes

Everything on this page is specified in `docs/AUTHORING.md`. The quiz pattern of `docs/POLICY.md` (the answer as a `.fragment .live-only` block live, as a `.study-only` block in the PDF) is on slide 7 of `examples/features/slides.qmd`, which exercises every construct one per slide and is the deck to read beside this one.
