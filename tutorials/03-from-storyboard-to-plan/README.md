# Episode 3: From storyboard to plan

Length: 8 minutes. Recorded as one real session, with the waiting cut.

## Goal

The lecturer's `STORYBOARD.md` becomes `PLAN.md` with times against the budget. The viewer sees what the assistant proposes and what the lecturer changes by hand.

## What the viewer sees

`lk new` scaffolds a project. The lecturer fills `STORYBOARD.md` on camera for the kickoff deck, in the shape the kickoff's own storyboard has: the brief quoted, the audience, the one thing to take away, the argument in order, the moments that need a visual, the tone. One prompt to the assistant. `PLAN.md` appears with a slide table whose times sum to 15. The lecturer edits two titles and moves a minute from one slide to another. A second prompt writes `slides.qmd` from the plan with placeholder figures; `lk build` confirms the sum.

## Commands and prompts

```sh
lk new kickoff-redo --title "Welcome to the Popylar workshop"
cd kickoff-redo
$EDITOR STORYBOARD.md
```

First prompt, typed into the assistant:

```text
Read STORYBOARD.md. Write PLAN.md as docs/WORKFLOW.md describes it: a slide
list with a title under 30 characters, a role and a time for each slide, the
figure or clip each slide gets and the numbers it needs, and the study-only
pages. The budget is 15 minutes; make the times sum to it and show me the
sum. Do not write any slides yet.
```

The lecturer edits `PLAN.md` by hand: two titles, one minute moved. Then:

```text
Keep my edits to PLAN.md. Write slides.qmd from it with a labelled
placeholder for every figure and clip, notes with Line / Ask / Say / Status
on every slide, and build it so that I can read the timing report.
```

```sh
lk build .
```

## Points to make

- The storyboard is the lecturer's and is written first, in prose; the plan is the contract for everything after.
- Titles, claims and purpose are never delegated (`docs/WORKFLOW.md`); the assistant proposes, the lecturer decides.
- The sum against the budget is the first check, and the build prints it: `slides N  planned X min  budget 15 min  ok`.
- A placeholder is a figure: the deck builds, and the gap is visible on the slide.

## Artefacts

- `before/STORYBOARD.md`: as the lecturer wrote it.
- `after/PLAN-proposed.md`: the assistant's first version.
- `after/PLAN.md`: after the lecturer's edits.
- `after/timing.txt`: the report of the placeholder build.

## Notes

The templates for both files are in `docs/WORKFLOW.md`, and `lk new` writes them with a line of guidance under each heading. The kickoff's own `STORYBOARD.md` and `PLAN.md` are in `examples/kickoff`; they are the model of what this episode produces, with the review rounds that followed recorded in the deck's `README.md`.
