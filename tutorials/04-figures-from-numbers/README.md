# Episode 4: Figures from numbers

Length: 8 minutes.

## Goal

One function in the kickoff's `make_assets.py`, on the TikZ kit, turns recorded facts into a figure; a two-stage version for a fragment; a preview with `lk review figs`; why the figure is drawn at display size.

## What the viewer sees

`examples/kickoff/FACTS.md` with the numbers (the commit counts by author, checked 4 November 2026) and `assets/data/s01.json` with the recorded run behind the clip and its figure. The `shelf()` function in `make_assets.py`: a shelf of model cards 13 cm wide, each card a small drawing of what the model computes, colours as names (`GAUSS`, `DOG`, `CSS`, `DN`, `TEAL`), the slide surface as `SLIDE`, tints towards it with `tint()`, never a literal. The last line writes two files: `shelf.tex`, and `shelf-0.tex` with the "Your model" card inside an invisible scope, so that both have the same bounding box. `python make_assets.py shelf` writes them; `lk review figs` shows the PNGs and prints the natural size. The slide stacks the two as a fragment live and prints the final one in the PDF. To close: the same figure drawn twice as large and placed in the same slot, beside the original, so that the viewer sees the labels shrink below legibility.

## Commands

```sh
cd examples/kickoff
cat FACTS.md
$EDITOR make_assets.py                # shelf(), and the two write() calls at its end
python make_assets.py shelf
lk review figs . shelf shelf-0        # review/figs/shelf.png, the natural size in cm
lk build .
lk review frags _build/slides-live.html --slides 6
```

A prompt, if the assistant writes a figure:

```text
Add a figure to slide 6 from the commit counts in FACTS.md using
lecturekit.tikz: one bar per author, 13 cm wide and 4.2 cm tall, with a
stage-0 version that shows only the axis for the fragment. Styles and tokens
only, SLIDE for the surface, no literal colours or numbers that are not in
FACTS.md. Preview it with lk review figs and show me.
```

## Points to make

- Every number in the figure comes from `assets/data/` or from a fact recorded in `FACTS.md`; the script is re-runnable, and the build runs it first.
- `\nmfigureh` and the live `<img>` set a maximum and never upscale, so the figure is drawn at the size it will have: 13 cm wide, 4.2 cm tall above two bullets (`docs/LAYOUT.md`).
- The stage file draws the later elements inside `\begin{scope}[opacity=0]`, so that both files share a bounding box and the stack does not jump; `lk review frags` reports a stack whose steps differ in size.
- `%` in a label is a comment: `50\%`, or `escape()`. A wrapped node hyphenates unless told not to: `nohyphen()`.
- The slide surface is `SLIDE`, never `white`, and a tint is `tint(BLUE, 6)`, never `BLUE!6`: that is what lets the figures restyle in episode 7.

## Artefacts

- `before/FACTS.md` and `before/assets/data/s01.json`: the numbers.
- `before/make_assets.py`: as shipped.
- `after/assets/figures/shelf-0.tex` and `after/assets/figures/shelf.tex`.
- `after/figs/shelf.png` and `after/figs/shelf-0.png`: the previews; `after/slide-06-live-f0.png`, `after/slide-06-live-f1.png` and `after/slide-06-study.png`.

## Notes

The kit's API is listed in `docs/FIGURES.md`, one line per name; the kickoff's `make_assets.py` is the model of a figure script. `engine()` is the second two-stage figure of the deck (the forward half, then the fitting loop); `timeline()` is the one that draws the commit counts.
