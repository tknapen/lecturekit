# Episode 9: A talk from a paper

Length: 12 to 15 minutes, or two parts. Recorded as one real session, with the waiting cut. The episode closest to how a researcher would use the workflow.

## Goal

A 20-slide talk for 20 to 25 minutes, built in dialogue from a paper, with the author correcting the assistant's reading on camera; figures redrawn and recomputed; `FACTS.md` built from the paper.

## The material

Hedger, Naselaris, Kay and Knapen, Joint visual and somatotopic tuning in the dorsolateral visual cortex, Nature 650, 173 to 181 (2025), doi 10.1038/s41586-025-09796-0; its supplementary information; the data and code where public. PubMed's record gives the copyright as the authors' (2025, The Author(s)). The reuse terms are read on the publisher's page before any published figure is reproduced; the method prefers figures redrawn from the paper's values or recomputed from its data, and the episode reproduces none.

## What the viewer sees

`lk new hedger-2025-talk`; the PDF goes into `references/`. The assistant reads it and proposes a storyboard (the question; the joint somatotopic and visual tuning model; the maps found at rest and during video watching; the alignment of body position with visual field and category; what it means) and a plan of about twenty slides with times against a budget of 22 minutes. The author corrects what the assistant misread, which the author can do better than anyone. `FACTS.md` is built from the paper's own numbers with page references. The figures: a schematic of the model drawn with `lecturekit.tikz`; the body maps along the dorsolateral visual system on an inflated hemisphere, from the surface renderer of the workshop's lecture 2 (a project helper, which moves into the kit when a second project wants it); alignment plots recomputed where the data allow. Two review rounds with `lk review shoot --against`. The PDF and the live deck exported.

## Prompts

```text
Read references/hedger-2025.pdf and its supplement. Propose STORYBOARD.md
for a 20 to 25 minute talk to a neuroscience audience, then PLAN.md with
about twenty slides following docs/WORKFLOW.md. Stop after the plan; I will
correct your reading before anything is drawn.
```

```text
Build FACTS.md from the paper: every number and claim the plan uses, with
the page, figure or table it comes from. Mark anything you inferred rather
than read as "to confirm".
```

```text
Write slides.qmd from the plan. Draw the model schematic with lecturekit.tikz
from the equations in the methods; redraw the alignment figures from
digitised values and say so on the slide and in MANIFEST.md; recompute them
from the public data where it exists. Build, then run lk review shoot and
lk review measure and show me.
```

```sh
lk build .
lk review shoot _build/slides-live.html --out review/round-1 --sheet
lk review measure _build/slides-live.html
lk review overflow .
```

## Artefacts

- `before/references/`: the paper and its supplement (not committed; their location noted).
- `after/STORYBOARD.md`, `after/PLAN.md`, `after/FACTS.md`, `after/MANIFEST.md`, `after/slides.qmd`, `after/timing.txt`.
- `after/review/round-1/` and `after/review/round-2/`: the PNGs of each round.

## Notes

The author's corrections on camera are the point of the episode: the claims and the titles are never delegated (`docs/WORKFLOW.md`). Published figures are redrawn from digitised values and cited, never reproduced (`docs/FIGURES.md`, `docs/POLICY.md`).
