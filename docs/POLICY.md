# Presentation policy

The writing rules of a deck. Each rule comes with the reason it exists and, where one exists, the command that checks it. The rules are short because they point at LAYOUT.md for the geometry and at WORKFLOW.md for the method. An assistant reads this page before it writes a slide.

## Titles under 30 characters

A title names what the slide shows, in under 30 characters, so that it fits one line of the title block in both outputs. A second line crosses into the content area (LAYOUT.md). Check: `lk review shoot`, and the timing report, which lists every title.

## One line per bullet at the live font

A bullet is one line at the live deck's 26 px root font. A bullet that wraps is two bullets, or one shorter one. Bullets carry what the audience should read; what the lecturer says goes in the notes. Check: `lk review shoot` shows a wrapped bullet at once; `lk review measure` reports the height the text leaves.

## A visual on every slide, as large as the slide allows

Every slide has a figure, a clip or an equation, at the largest height the text beside it leaves (the table in LAYOUT.md). A slide of bullets alone is a notes page, not a slide. A figure is drawn at display size and never upscaled. Check: `lk review measure` prints the free pixels above the foot; `lk review figs` previews the figures at size.

## Quiz and pause slides carry their answers

A slide that asks the room a question also holds the answer: a `.fragment .live-only` block for the live deck, a `.study-only` block for the PDF. The study reader is not in the room, and the lecturer should not have to remember. Check: `lk review frags` lists the fragments; the study PDF shows the answer in place.

## Verified claims only, with the source in FACTS.md

Every claim on a slide, every number and every date is in `FACTS.md` with its source and the date it was checked. A claim without a source is listed to confirm in `FACTS.md` and worded as unconfirmed on the slide, or left out. Numbers come from scripts and configs, never from memory. Check: none by machine; the lecturer signs off `FACTS.md` before publishing (WORKFLOW.md).

## Redraw published figures from digitised values

A figure from a publication is not reproduced. It is redrawn with the kit from digitised values, or recomputed from the paper's data where they are public, and it cites the source and says it was redrawn from digitised values, on the slide and in `MANIFEST.md`. The deck's figures stay in the deck's style, and the deck stays free of reuse terms. Check: `MANIFEST.md`, read at publishing.

## Colour means something

Colour is a signal with a fixed meaning. The roles label slides (the eyebrow) and colour spans; the marks colour the parts of figures and clips.

| Token | Meaning |
| --- | --- |
| `concept` | the idea being taught |
| `caveat` | where it breaks, what it does not say |
| `example` | a worked case, a demonstration |
| `anchor` | a fixed point to remember and return to |
| `question` | a question to the room, a quiz, a pause |
| `input` | what enters a model: the stimulus, the data |
| `state` | what a model holds: parameters, activity |
| `update` | what changes: a step of a fit, a learning signal |
| `context` | what surrounds: modulation, a prior, the task |

The `prf` preset relabels the roles WHERE, HOW, WHAT, WHEN on the concept, example, anchor and question colours. Domain colours (the models of a project) are project tokens and keep one meaning across a project's decks. Nothing is coloured for decoration. The values live in `_brand.yml` (THEMING.md). Check: `lk review contrast <_brand.yml>` for legibility; the meaning is reviewed by eye.

## Missing data become a labelled placeholder

A figure or clip whose data are not there yet is a dashed box in the caveat colour with a label saying what is missing. The deck always builds, the gap is visible on the slide and in the review PNGs, and nobody mistakes a draft for a result. `make_assets.py` writes the placeholder when its input is missing; the build writes one when a figure fails to compile or a clip cannot be found. Check: `lk review shoot` shows every placeholder.

## Speaker notes: Line, Ask, Say, Status

Every slide has notes of up to four lines. Line: the one sentence the slide exists for. Ask: the question to the room. Say: what is said and not shown. Status: draft, reviewed or final, with what is open. The notes are the lecturer's script and the record of what the slide is for. They show in the speaker view and never in the frame or in the PDF.

## Study-only pages for what the live budget drops

What the live budget cannot hold and the reader needs is a `.study-only` slide with `time=0`: a derivation, a table, the rest of a long bibliography, the second half of a long figure. The live deck stays within its minutes; the study PDF stays complete. Check: the timing reports of the two renders agree.

## Provenance: MANIFEST.md lists every image

Every image, figure and clip in the deck has an entry in `MANIFEST.md` with its origin (the script and data, the cited source it was redrawn from, or where an external image came from) and its licence. Logos and wordmarks are not ours: names are set in type instead. The deck's own content carries a licence that its README states; the example decks use CC BY 4.0 for content and MIT for code. Check: `MANIFEST.md` complete before publishing (WORKFLOW.md).

## In one table

| Rule | Check |
| --- | --- |
| Titles under 30 characters | `lk review shoot`; the timing report |
| One line per bullet | `lk review shoot`, `lk review measure` |
| A visual on every slide, as large as it allows | `lk review measure`, `lk review figs` |
| Quiz slides carry their answers | `lk review frags`; the study PDF |
| Verified claims only | `FACTS.md`, signed off by the lecturer |
| Published figures redrawn and cited | `MANIFEST.md` |
| Colour means something | `lk review contrast`; review by eye |
| Missing data become placeholders | `lk review shoot` |
| Notes with Line / Ask / Say / Status | the speaker view |
| Study-only pages for what live drops | the timing report |
| Every image in `MANIFEST.md` | `MANIFEST.md` before publishing |
