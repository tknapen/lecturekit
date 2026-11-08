# Episode 6: The review loop

Length: 8 minutes. Recorded as one real session, with the waiting cut.

## Goal

A deliberately overfull slide, the three commands that catch it, the assistant's fix; then `FACTS.md` catching a wrong date.

## What the viewer sees

A third bullet and a taller figure are added to Credit where credit is due (slide 3) of the kickoff deck. `lk build` succeeds: overflow is not a build error. `lk review overflow` names the frame; `lk review shoot` shows the slide, with the bullet crossing the foot in `report.json`; `lk review measure` prints a negative free height. One prompt; the assistant moves the bullet to the notes and returns the figure to 4.1 cm; the three commands run clean, and `shoot --against` shows that only slide 3 changed. Then the release date on Where we stand (slide 6) is changed to 3 October; a second prompt; the assistant checks `FACTS.md` (0.2.0 on PyPI on 3 November 2026), corrects the slide and records the check with today's date.

## Commands and prompts

```sh
cd examples/kickoff
lk review shoot _build/slides-live.html --out review/round-0 --sheet   # the clean state, for --against
$EDITOR slides.qmd      # slide 3: a third bullet; the live figure to \nmfigureh{5.5cm}
lk build .
lk review overflow .
lk review shoot _build/slides-live.html --sheet
lk review measure _build/slides-live.html
```

```text
Slide 3 overflows in both outputs: see review/shots/slide-03.png and the
measure output. Fix it within docs/LAYOUT.md: keep the figure as large as
the slide allows and move what does not fit to the notes or to a study-only
block. Rebuild and run the three review commands again, and compare the
shots with review/round-0.
```

```sh
lk review shoot _build/slides-live.html --sheet --against review/round-0
```

```text
Slide 6 now says prfmodel 0.2.0 was released on 3 October. Check FACTS.md
and the sources it names, correct whichever is wrong, and record the check
in FACTS.md with today's date.
```

## Points to make

- Three commands, three questions: does the PDF overflow (`overflow`, from the Beamer log beside the source), what does the slide look like (`shoot`, one PNG per slide and what crosses the foot), how many pixels are free (`measure`, against the foot line at 677 px).
- The fix follows the rule table in `docs/LAYOUT.md`, not taste: two one-line bullets leave 4.1 to 4.4 cm; a third bullet costs the figure half a centimetre, which this slide does not have.
- `--against` turns a review round into a diff: the slides whose pixels changed, nothing else to look at.
- Every number on a slide traces to `FACTS.md`; a wrong one is caught by the file, not by memory.

## Artefacts

- `before/slides.qmd`: the overfull version.
- `after/slides.qmd`: fixed.
- `after/review-before.txt` and `after/review-after.txt`: the output of the three commands, before and after.
- `after/slide-03-before.png` and `after/slide-03-after.png`.
- `after/FACTS.md`: with the check recorded.

## Notes

The commands are described with their rules in `docs/LAYOUT.md`; the method's place for review rounds is stage 6 of `docs/WORKFLOW.md`. The Beamer log survives the render because the format keeps `slides.tex` and `slides.log` beside the source.
