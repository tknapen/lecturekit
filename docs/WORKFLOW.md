# Workflow

The per-deck method as a checklist. Nothing in the build enforces it; it is what makes every number on a slide traceable to a script and every claim to a source. The lecturer storyboards and reviews, the assistant builds, and the rounds iterate on screenshots of the live deck. The files the checklist names are written by `lk new` as templates; the templates are at the end of this page.

## Who does what

The lecturer writes `STORYBOARD.md`, decides the titles and the claims, reads every review round, and signs off `FACTS.md` and `MANIFEST.md`. The assistant drafts `PLAN.md`, runs the simulations, writes `make_assets.py`, the figures, the clips, `slides.qmd` and the notes, runs the build and the review commands, fixes what they report, and keeps `README.md` current.

Never delegated: what the lecture is for, the titles, the claims and their sources, the credit given, and the decision that ends a review round. An assistant proposes these; the lecturer decides.

## The checklist

1. Storyboard. The lecturer writes `STORYBOARD.md`: what the minutes are for, the one line the audience takes home, the beats in order, the credit to give. In the lecturer's voice; no slides yet.
2. Plan. The assistant turns the storyboard into `PLAN.md`: a slide list with a title under 30 characters, a role and a time per slide, the figure or clip each slide gets and the data it needs, and the study-only pages. The times sum to the budget. The lecturer edits by hand; the plan is the contract for everything that follows.
3. Simulations. Every number that will appear on a slide comes from a script under `sims/` (or the project's `lib/`), run from a config file and writing a JSON summary per run. No number is typed from memory.
4. Numbers into `assets/data/`. The summaries a deck uses are copied into the deck's `assets/data/*.json`, so that the deck folder holds everything its figures are made from.
5. Figures and clips from those numbers. `make_assets.py` reads `assets/data/` and writes `assets/figures/*.tikz` (FIGURES.md); clip scenes under `anim/` read the same data, and `lk clips` renders them into `assets/clips/` and writes `clips.json` (CLIPS.md). A figure whose data are missing is written as a labelled placeholder, so the deck builds.
6. Slides with notes. `slides.qmd` follows the plan slide for slide, each heading with its role and time, each slide with Line / Ask / Say / Status notes (AUTHORING.md). `lk build` prints the timing report against the budget.
7. Review rounds. `lk review shoot` writes one PNG per slide; `lk review measure`, `lk review frags` and `lk review overflow` report what the eye misses (LAYOUT.md). The lecturer reads the PNGs and answers slide by slide; the assistant fixes and rebuilds. A round ends when the lecturer says so.
8. Facts and provenance before publishing. `FACTS.md` lists every claim with its source and the date it was checked; `MANIFEST.md` lists every image with its origin and licence (POLICY.md). Items still to confirm are listed as such, never dropped silently.
9. The log. `README.md` records each revision: the date, what changed, what the round decided, what is open. It is also the tour of the deck for a reader: how to build it and what to look at.
10. Publish. Both outputs are built from a clean tree and committed beside the sources in the project's published folder, so that the lecture can be read without the engine.

## The commands in one place

| Command | What it answers |
| --- | --- |
| `lk build [dir] [--profile dark] [--to live\|study]` | Does it build, and how do the times add up against the budget? |
| `lk review shoot <deck.html> [--out dir] [--fragments]` | What does every slide look like, and every fragment step? |
| `lk review measure <deck.html>` | Where does the content end on each slide, and how many pixels are free above the foot? |
| `lk review frags <deck.html>` | Which fragments does each slide have; is a clip's `.fragment` inside `.live-only`? |
| `lk review overflow <deck.log>` | Which frames of the study PDF overflow? |
| `lk review figs <dir>` | Do the TikZ figures read at display size? |
| `lk review contrast <_brand.yml>` | Does every text and role colour pass WCAG AA on each surface? |
| `lk clips [dir]` | Are the clips rendered from their current sources, and is `clips.json` up to date? |

## Templates

`lk new` writes these files with the headings below and one line of guidance under each. Replace the guidance with content and keep the headings, so that a reader of any deck finds the same structure.

### STORYBOARD.md

```markdown
# Storyboard: <deck title>

## Purpose
What these minutes are for, in one or two sentences; what the audience should be able to do afterwards.

## Audience
Who is in the room and what they already know.

## The line
The one sentence the audience takes home.

## Beats
The moves of the lecture in order, three to six, each with what the audience should think or do at that point.

## Credit and lineage
Whose work is shown and who is to be named; what this lecture descends from.

## Constraints
Time, room, what must be in, what is off limits.

## Open questions
What the lecturer has not decided yet.
```

### PLAN.md

```markdown
# Plan: <deck title>

## Budget
Total minutes. The slide times below sum to it; `lk build` prints the sum.

## Slides
| # | Title (under 30 characters) | Role | Time | Visual (figure or clip; the script and data it comes from) | Notes status |
| - | --- | --- | --- | --- | --- |

## Study-only pages
What the live budget drops and the study PDF keeps: derivations, tables, extra figures.

## Data needed
Which simulations or scripts produce which numbers, and where they land in assets/data.

## Open items
What is missing before the deck can be reviewed.
```

### FACTS.md

```markdown
# Facts: <deck title>

Every claim a slide makes, with its source. One entry per claim.

## Checked
| Claim as stated on the slide | Slide | Source (DOI and page, table or figure; or script, config and run) | Checked on | By |
| --- | --- | --- | --- | --- |

## To confirm
Claims still on a slide without a verified source, who will confirm them, and by when.

## Dropped
Claims removed from the deck and why, so that they do not come back.
```

### MANIFEST.md

```markdown
# Manifest: <deck title>

Every image, figure and clip in the deck, with its origin and licence.

| File | Origin (script and data; redrawn from a cited source using digitised values; or external) | Licence | Regenerates on restyle | Date |
| --- | --- | --- | --- | --- |

## Notes
For a redrawn figure: the source citation and what was digitised. For an external image: where it was obtained and the licence text. For a fixed PNG: the script that regenerates it, or the statement that it stays as it is.
```

### README.md

```markdown
# <deck title>

## Build
The commands to build and review the deck.

## Tour
Which slide shows what, and what to look at.

## Log
Dated entries, newest first: what changed, what the review round decided, what is open.
```

## Where the pieces are defined

| Piece | Page |
| --- | --- |
| The dialect | AUTHORING.md |
| Geometry and its checks | LAYOUT.md |
| Writing and provenance rules | POLICY.md |
| Figures from numbers | FIGURES.md |
| Clips | CLIPS.md |
| The theme | THEMING.md |
| Installing the tools | INSTALL.md |
