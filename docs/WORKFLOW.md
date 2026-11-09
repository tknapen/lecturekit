# The per-deck workflow

How a lecture goes from an intent to two shipped outputs, and who does what when a lecturer works with an assistant. The files are the state; the conversation is not. Each stage ends in something the lecturer can look at. `examples/kickoff` is the worked example: every file below exists there, filled in.

## Files of a deck

A deck is a Quarto project (AUTHORING.md). `lk new <dir>` writes the files the method prescribes, with one line of guidance under each heading, and vendors the engine's extension.

```text
<deck>/
├── _quarto.yml         the render list, output-dir _build, pre-render make_assets.py, resources assets/**, the two formats, brand
├── _brand.yml          the look, defined once: every colour and font (THEMING.md); _brand-dark.yml and _quarto-dark.yml for the dark preset
├── _extensions/lecturekit/   the vendored engine extension, pinned by committing it
├── STORYBOARD.md       the lecturer's intent: what the minutes are for, the argument, the moments to land
├── PLAN.md             the slide list with roles, planned minutes against the budget, and the figure or clip of each
├── slides.qmd          the source: one level-two heading per slide, roles and times, notes with Line / Ask / Say / Status
├── make_assets.py      the TikZ figures, drawn from numbers in assets/data on lecturekit.tikz
├── anim/               kit.py (two lines on lecturekit.manim), clip_*.py scenes; media/ is Manim's scratch
├── clips/              optional: a manim8 workspace (lk new --manim8), one project per clip under families/
├── sims/ or ../sims/   the simulations whose summaries land in assets/data (configs and results documented)
├── assets/             data/ (JSON summaries), figures/ (generated .tex), clips/ (mp4, png, clips.json; dark/ for the dark preset), images/ (scripted PNGs)
├── references.bib      checked against Crossref or PubMed; every cited DOI resolves
├── FACTS.md            every number and claim on a slide, its source and the date it was checked
├── MANIFEST.md         every image: origin, licence, the script that made it
├── README.md           the running log: what changed in each revision round and why
└── AGENTS.md           the project's own rules for an assistant; points at the engine's documentation (lk docs)
```

The build leaves `_build/` (both outputs, `timing.txt`, the copied assets), `_lecturekit/` (the tokens and the figure cache), `slides.tex`, `slides.log` and Beamer's auxiliary files beside the source, and the review tools leave `review/`; a manim8 workspace leaves `renders/` and `.scianim/` in each project and a `.venv/` in each family. The scaffold's `.gitignore` leaves all of these out. A project commits its sources and `assets/`, so that the lecture can be rebuilt, and may commit a built copy so that it can be read without the engine.

## Stages

1. Storyboard. The lecturer writes what the lecture is for, in prose: the audience, the one thing they must take away, the argument in order, the moments that need a figure or a clip, the time. Nothing is built before this.
2. Plan. The assistant turns the storyboard into `PLAN.md`: a slide per claim, a role per slide, minutes per slide against the budget (`budget:` in the deck header; `lk build` prints the plan against it), and for each slide the figure or clip and the numbers it needs. The lecturer edits the plan; this is the cheapest place to change a lecture.
3. Numbers. Every quantitative figure comes from a script: a simulation with a config, or digitised values from a publication with the method recorded. Summaries land in `assets/data/*.json`; a figure whose data are missing becomes a labelled placeholder, so the deck always builds.
4. Figures and clips. `make_assets.py` draws from the summaries on `lecturekit.tikz` (FIGURES.md); the build runs it as the project's pre-render step, and `python make_assets.py [name ...]` runs it by hand. Clips are scenes on the Manim kit in `anim/clip_*.py`, or manim8 projects in `clips/` made from a brief, both rendered by `lk clips <deck>` into `assets/clips/` with their stills and `clips.json`, and by `lk clips <deck> --mode dark` into `assets/clips/dark/` for the dark preset (CLIPS.md). `lk review figs <deck>` and the clip's frames are looked at before they enter a slide.
5. Slides. `slides.qmd`, with every slide carrying its role and time, a visual, bullets of one line each, and notes: `Line:` the sentence the slide exists for; `Ask:` the question to the room and its answer; `Say:` what to say; `Status:` where the numbers come from (`[SIM]`, `[DRAWN]`, `[LIT]`). `lk build <deck>` renders both outputs and prints the timing report.
6. Review rounds. Build; `lk review shoot <deck>/_build/slides-live.html --sheet` writes every slide as a PNG and a contact sheet; the lecturer reviews the PNGs or the live deck and lists changes by slide number; the assistant applies them, rebuilds, checks the layout rules (`lk review measure`, `lk review frags`) and the PDF (`lk review overflow <deck>`), and reports what changed and what it could not verify. `lk review shoot --against <earlier shots>` lists the slides that changed since the last round. Repeat.
7. Facts. Before publishing, `FACTS.md` lists every claim with its source and check date and `MANIFEST.md` every image with its licence. A claim that cannot be sourced leaves the slide or is marked as the lecturer's own.
8. Publish. Build both outputs from a clean tree; publish `_build/` (the continuous build does this to GitHub Pages, `quarto publish gh-pages` does it from a project folder) or commit the outputs beside the sources; the README's log records the round.

## Who does what

The lecturer owns the claims, the titles, the storyboard and what the lecture is for; decides every review round; checks numbers against sources when they matter; records the voice-over of a tutorial. The assistant builds, computes, draws, renders, checks layout and overflow, keeps the files consistent, and says plainly what it could not verify. Neither edits generated files (HTML, LaTeX, PDF) by hand.

## Rules that save rounds

- One claim per slide, stated in the title; under 30 characters.
- A visual on every slide, as large as the slide allows; whitespace around a figure is a defect.
- Bullets are one line each; dense sentences go to the notes or the study PDF.
- Reveal only where the order is the explanation; the PDF always shows the complete slide.
- Quiz and pause slides carry their answers.
- Published figures are redrawn from digitised values or replaced by our own simulation; never reproduced.
- Verified claims only; a date on every check.

## The commands in one place

| Command | What it answers |
| --- | --- |
| `lk new <dir> [--title T] [--budget MIN] [--manim8]` | A project with the files above and the vendored extension, its budget in minutes (45 by default); `--manim8` adds a manim8 workspace in `clips/`; `--vendor-only` adds the extension to an existing project, `--force` replaces it (a shared copy behind a link is never overwritten). |
| `lk build [dir] [--to live\|study] [--profile dark]` | Does it build, and how do the minutes add up against the budget? |
| `python make_assets.py [name ...]` | Are the figures current with the numbers in `assets/data`? |
| `lk clips [deck] [--only name ...] [--size WxH] [--crop] [--mode dark] [--still CLIP=ID] [--revision REV]` | Are the clips, kit and manim8, rendered from their current sources, and is `clips.json` up to date? Exits 1 when a clip failed. |
| `lk review shoot <live.html> [--sheet] [--fragments] [--against DIR]` | What does every slide look like, and what crosses the foot? |
| `lk review measure <live.html> [--slide N]` | How many pixels are free above the foot on each slide? |
| `lk review frags <live.html> [--slides N ...]` | Which fragments does each slide have; is a clip shown and playing at the right step? |
| `lk review overflow [deck \| slides.log]` | Which frames of the study PDF overflow? |
| `lk review figs [deck] [name ...]` | Do the figures read at display size, and how large are they? |
| `lk review contrast [_brand.yml] [--mode dark]` | Do the text and role colours pass WCAG AA on every surface? |
| `lk theme [dir] [--mode dark] [--manim8 VERSION]` | The brand's tokens as files for scripts outside the build; with `--manim8`, the bridged manim8 styles of both presets, the paper one selected in every manim8 project. |

## Templates

The four files as the kickoff example has them. Keep the shape; replace the content.

### STORYBOARD.md

```markdown
# Storyboard

The brief as given on <date> (the lecturer's words, condensed), and the shape that came out of it.

> The brief, quoted.

The audience: who is in the room and what they already know. The one thing to take away: one sentence.

The argument in order: the moves of the lecture, one clause each, in the order they are made.

Moments that need a visual: which slide moves (the only clip), which figures build in stages, which appear on a key press.

Tone: how it should sound; where every number comes from; names in type, no logos.
```

### PLAN.md

```markdown
# Plan

Budget <N> minutes (the header's `budget: N`); <n> timed slides plus title and references; the build reports <planned> of <N>.

| # | slide | role | min | visual | numbers from |
|---|---|---|---|---|---|
| 1 | Why we are here | concept | 2 | clip `bar-bold.mp4`; PDF: `bar-bold.tex` | `assets/data/s01.json`; the field's size from the proposal |
| 2 | Credit where credit is due | explanation | 2 | `lineage.tex` | proposal section 9; package records |
| | References | | | | `references.bib` |

Review rounds recorded in `README.md`: what each round changed, by slide.
```

### FACTS.md

```markdown
# Facts on the slides and where they come from

Checked <date> unless stated. A claim that is not here is not on a slide.

- <Source> (<edition, date>): the claims taken from it, with the numbers as stated on the slides.
- <Second source>: ...
```

### MANIFEST.md

```markdown
# Images and their origins

| asset | made by | origin | licence |
|---|---|---|---|
| `assets/figures/name.tex` | `make_assets.py` (`name`) | the data or document it is drawn from | ours |
| `assets/clips/name.mp4` | `lk clips` (`anim/clip_name.py`, scene `Name`) | as the figure; Manim Community 0.22 on the shared kit | ours |

No image in this deck is reproduced from a publication or a website.
```

### README.md

The deck's README is the tour and the log: how to build it (`lk build .`, the review commands, `lk clips .`), a table of the slides with their figures and what each carries, the items that were open before the talk, and dated log entries, one per revision round, saying what changed, why, and what remains unverified.
