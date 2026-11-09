# Welcome to the Popylar workshop (Thursday 5 November 2026, 09:00, 15 minutes)

The opening deck for the Coimbra workshop, built on the evening of 4 November 2026 in the dual format: `slides.qmd`
gives the Reveal.js deck for the room and a study PDF. Seven content slides plus title and references, timed at 15
minutes (`_build/timing.txt`). The source material is the Popylar full proposal (Open eScience Call 2024, submitted
30 May 2024), the prfmodel 0.2.0 documentation and repository, PyPI and the workshop site.

This deck is the engine's worked example: `STORYBOARD.md` is the brief it was built from, `PLAN.md` the slide list
with times, `FACTS.md` the checked claims, `MANIFEST.md` the images and their origins.

```sh
lk build .                       # both outputs into _build/, the plan against the budget
lk build . --profile dark        # the dark preset (_brand-dark.yml) into _build-dark/
lk review shoot _build/slides-live.html --sheet
lk review overflow .
lk clips . --only bar-bold       # re-render the clip on the Manim kit (pip install lecturekit[clips])
```

## Slides

| # | title | figure | what it carries |
|---|---|---|---|
| 1 | Why we are here | clip `bar-bold.mp4` (study: `bar-bold.tex`) | the method in one clip; the field's size (1000+ papers, 100+ labs, from the proposal) |
| 2 | Credit where credit is due | `lineage.tex` | mrVista, popeye, prfpy, braincoder feeding prfmodel; the wider family from the proposal's section 9 |
| 3 | What we proposed: an engine | `engine.tex` (staged after `engine-0.tex`) | the proposal's computational engine (its Figure 4), redrawn; the three design commitments |
| 4 | What we proposed: a community | `community.tex` | 29 letters, development committee, governance, benchmark data, tutorials, Brain Hacks, yearly workshop |
| 5 | Where we stand: prfmodel 0.2.0 | `shelf.tex` (staged after `shelf-0.tex`) | the models of the 0.2.0 API as cards; fitters, backends, tutorials, examples in the bullets |
| 6 | The person who built it | `timeline.tex` | Malte Lüken; milestones from the commit history; commit counts by author |
| 7 | Two days | `programme.tex` | the provisional schedule from the workshop site |

Figures: `python make_assets.py` (TikZ on `lecturekit.tikz`; the build runs it as the project's pre-render step).
Clip: `anim/clip_bar_bold.py`, the bar-and-BOLD scene on the Manim kit with its numpy model in `anim/bar_model.py`;
it reproduces the shipped `bar-bold.mp4` frame for frame and reads `assets/data/s01.json` (a prfmodel forward model)
when it exists.

## Items that were open before the talk

- Slide 4 notes: "the first workshop abroad" and the host to thank (Jorge Almeida's group signed a letter of
  support; the proposal planned the first workshop at the Spinoza Centre).
- Slide 6: the names beside Malte. José Angel Daza is confirmed from the commit authors; the other two eScience
  Center contributors are shown as "two colleagues" because their full names could not be verified from here.
- Slide 7 notes: which notebooks go in which practical slot is not on the schedule; the figure labels the slots
  only as Practical 1 to 4.

## Log

- 4 November 2026: built for the workshop with the course toolchain (Pandoc, Tectonic, the shared template);
  three review rounds (text overflow in the lineage, engine and community figures and the programme; the engine's
  parameter box and the timeline's name labels; wording on slides 2 to 6 and the staged builds on 3 and 5).
- 8 November 2026: moved into lecturekit as a Quarto project. The figures regenerate byte for byte from
  `make_assets.py` on the packaged kit; both outputs build from a fresh clone; the study PDF's title page no longer
  overfills. The clip's source now imports the kit through `anim/kit.py`.

Content: CC BY 4.0, Tomas Knapen.
