# Layout rules

The geometry of a slide in both outputs, the traps that cost us build rounds, and the command that checks each rule. Measured on the live deck at its design size (1280 by 720 CSS pixels, Reveal margin 0.03) and on the Beamer study PDF (16:9, 160 by 90 mm). Figures in the source are sized in centimetres through `\nmfigureh{Hcm}{file.tex}` or `{height=Hcm}`; one centimetre of figure height is 88 live pixels (8.8 px per mm: a 720 px slide for a 90 mm frame, plus a tenth for the smaller body type).

The type scale is the same relative to the slide in both outputs: 12 pt body on 15 pt leading and a 20 pt frame title on the 160 mm page, 30 px body and 54 px titles on the 1280 px slide (policy of 14 October 2026; the measured body is 10.6 pt, which is 30 px). Slide numbers in the review tools are 1-based, as the foot shows them: the title slide is 1.

## The live frame

| Region | Position | Notes |
| --- | --- | --- |
| Eyebrow (role label) and rule | top, about 40 to 75 px | set by the slide's `role=`; 22 px letterspaced capitals, a 53 px rule in the role colour |
| Title | one line ends at about 150 px; a second title line costs about 55 px of figure | keep titles under 30 characters; the title is set in 54 px serif capitals |
| Figure or clip | from about 170 px down | `\nmfigureh` sets a maximum height; the SVG is never upscaled beyond its natural size |
| Bullets | above the foot, bottom-aligned | one line at the live font (30 px) is about 70 characters |
| Foot (short title, slide number) | top edge at about 677 px | 18 px capitals above a hairline, 22 px from the bottom; nothing may cross it; `shoot` reports what does |

The slide's content area has 45 px gutters left and right and 70 px of padding at the bottom. Budgets that work: two single-line bullets leave 4.1 to 4.4 cm for the figure; one bullet leaves about 4.8 cm; a bullet that wraps to two lines takes 0.4 cm from the figure. An r-stack (staged figure) needs about 0.2 cm less than a plain figure. Columns (`::: {.columns}`) share the width; a figure in a column is sized by the column, not the slide. The same numbers are in `lecturekit.tikz.FIGURE_HEIGHTS`: `full` 5.6 cm, `one_bullet` 4.8 cm, `two_bullets` 4.2 cm, `column` 4.4 cm.

Check: `lk review measure <deck>/_build/slides-live.html` prints, per slide, the bottom edge of the content, the foot limit, the free pixels between them, the number of title lines and the wrapping bullets, and flags OVERFULL, two-line titles and titles over 30 characters; `--slide N` prints one slide's boxes (title, figure with its natural size, columns, first paragraph, bullets, foot).

## Figures

- `\nmfigureh{Hcm}` is a cap, not a target. A TikZ figure drawn 6 cm wide displays at its natural size even when the cap allows more, so draw figures at the size they should appear (12 to 13 cm wide for a full-width slide, about 4.2 cm high for two bullets). `lk review figs <deck>` prints each figure's natural size in cm and warns when a figure is wider than the 14 cm slide.
- Staged figures (`name-0.tex`, `name.tex` in an r-stack) must have identical bounding boxes: draw the hidden stage inside `\begin{scope}[opacity=0] ... \end{scope}` rather than leaving it out. `lk review frags` reports an r-stack whose steps differ in size.
- Text in TikZ nodes: `%` must be written `\%`; a wrapped node (`text width=`) hyphenates unless the font is told not to: put `\hyphenchar\font=-1 ` at the start of the node text (`\hyphenpenalty` does not work there). Font strings are raw: `font=\sffamily\scriptsize\bfseries`. `lecturekit.tikz.escape` and `nohyphen` do both.
- A figure that embeds a PNG writes the PNG from a script (`assets/images/`) and names that script in `MANIFEST.md`, so a restyle can regenerate it.
- Colours are named (`nmInk`, `nmConcept`, `nmGauss`, ...), never literal hex codes, so that the theme owns them (THEMING.md).

## Clips

- A clip in a column or on a key press: the fragment wraps the live-only block, never the other way round: `::: {.fragment}` > `:::: {.live-only}` > `::: {.movie src=... aspect="W:H"}`. The reverse order covers the slide. `lk review frags` flags a clip's `.fragment` outside `.live-only`.
- `aspect=` is the clip's pixel ratio, from `assets/clips/clips.json` (written by `lk clips`); the `clip="name"` form reads it from there. A wrong aspect letterboxes the clip and wastes height.
- Clips play without browser controls: click or space pauses and resumes, R replays. Space does not advance a slide while a clip is shown. Browsers cache clips by file name: a re-rendered clip that looks unchanged on screen needs a new file name.
- A clip slide (one `.movie` in `.live-only`) gives the clip everything below the title at 16:9, so a clip under a two-line title still clears the foot; a clip among other content is 440 px tall.
- Every clip has a static equivalent in the study PDF (a `.study-only` figure, or the still that `clip=` places), as the policy requires.

Check: `lk review frags <live.html> [--slides N ...]` writes a PNG per fragment step and prints which fragments are visible, where the images sit and whether a clip is shown and playing.

## Study PDF

- `lk review overflow <deck>` reads the Beamer log beside the source and maps each overfull frame to its title; a slide with two columns and a tall figure overflows first. Make the columns `::: {.columns .live-only}` and give the PDF a single figure, or shorten the bullets.
- The bibliography appends to the last slide unless the deck ends with `## References {.references .allowframebreaks role=explanation}`.
- Display math in the source is `$$ ... $$`; it renders in both outputs.
- A quiz or pause slide carries its answer in a `study-only` block or in the next slide's notes; the live deck may hide it behind a fragment, the PDF never does.
- The page holds about nine bullet lines without a figure; with a figure of 3 cm, four lines; with 4 cm, two (POLICY.md).

## Checks

| Rule | Command |
| --- | --- |
| Nothing crosses the foot or the right edge; no console or load errors; titles on one line | `lk review shoot <deck>/_build/slides-live.html [--sheet] [--fragments] [--scale 2] [--against DIR]` (`review/shots/slide-NN.png`, `report.json`, a contact sheet; `--against` lists the slides whose pixels changed since an earlier round) |
| A staged slide builds as intended; a clip is shown and playing at the right step; a clip's fragment is inside `.live-only` | `lk review frags <deck>/_build/slides-live.html [--slides N ...] [--out DIR]` |
| Where the title, figure, bullets and foot sit; free pixels above the foot; a figure's natural size | `lk review measure <deck>/_build/slides-live.html [--slide N]` |
| A figure's natural size and look before it enters a slide | `lk review figs <deck> [name ...] [--brand FILE] [--mode dark]` (`review/figs/<name>.png` at 88 px per cm) |
| The study PDF fits; no missing characters or undefined colours | `lk review overflow <deck>` or `lk review overflow <deck>/slides.log [--min PT]` |
| The plan fits the budget | printed after every build; per slide in `<deck>/_build/timing.txt` |
| Text and role colours are legible on the surfaces | `lk review contrast <deck>/_brand.yml [--mode dark] [--strict]` |

The review tools serve the built deck over loopback and switch transitions off before measuring, so a screenshot taken right after a slide change shows that slide alone. Their output goes to `review/` beside `_build/`, which git ignores.
