# Layout

The geometry of a slide, stated so that it can be checked. Each rule names the command that checks it. The commands are `lk review measure`, `lk review shoot`, `lk review frags`, `lk review overflow` and `lk review figs`; they are summarised at the end.

## Two frames, one ruler

The live deck is a 1280 by 720 px frame. The study PDF is a 16 by 9 cm Beamer frame. The two share one ruler: 1 cm of the study frame is 80 px of the live frame. A height given in cm on a figure or a clip means the same size in both outputs, and the live deck shows what the PDF will print.

Reveal scales the frame into the browser window with a 4 percent margin (`margin: 0.04` in the format). The proportions below do not change with the window.

## The live frame

| Element | Where | Set in |
| --- | --- | --- |
| Eyebrow | top edge at 40 px, at the left gutter, 0.6 em uppercase | `.lk-eyebrow`, `reveal/theme.scss` |
| Title | top edge at 66 px; h2 at 1.55 em of the 26 px root, line height 1.1, so one line is about 44 px | `section > h2` |
| Title block | 0 to 150 px; content starts at 150 px | `--lk-title-block` |
| Gutters | 56 px left and right; content width 1168 px | `--lk-gutter` |
| Foot | hairline at 677 px; short title left, slide number right, 15 px text; hidden on the title slide | `--lk-foot-y`, `pacing.js` |
| Content area | 150 to 677 px: 527 px tall and 1168 px wide, which is 6.6 by 14.6 cm on the ruler | |

Root font 26 px with line height 1.3: a line of body text is about 34 px. A list item has a 0.25 em bottom margin, so a one-line bullet costs about 40 px, half a centimetre. Lists have no vertical margin of their own; a figure or clip gets a 0.3 em (8 px) top margin.

## The study frame

16 by 9 cm (`aspectratio: 169`), frames top-aligned (`classoption: t`). Text margins 0.7 cm left and right, which is 14.6 cm of text width and the same 56 px as the live gutters. The frame title block is 0.45 cm of air, the eyebrow line, the title at `\Large` in the heading font, and 0.15 cm: about 1.9 cm, the 150 px of the live frame. The footline takes 0.6 cm at the bottom, its hairline at about 8.4 cm, the 677 px of the live frame. Fonts come from `_brand.yml` through `_lecturekit/tokens.tex`.

## Figure heights

The content area holds a figure and some text, and the text costs height at about half a centimetre per one-line bullet. Rules of thumb, with 80 px per cm:

| Beside the figure | Figure height |
| --- | --- |
| Two one-line bullets | 4.1 to 4.4 cm (330 to 350 px) |
| One one-line bullet | about 4.6 to 4.9 cm |
| Nothing but the title | about 5 to 5.5 cm |
| Three one-line bullets | about 3.6 to 3.9 cm |

The study PDF is the tighter of the two outputs: a figure that fits there fits the live deck with room to spare. The live check is `lk review measure <deck.html>`, which prints per slide the bottom edge of the content and the free pixels above the foot line at 677 px, and flags overflow. The study check is `lk review overflow <deck.log>`, which reads the Beamer log for overfull boxes.

## Never upscaled: draw at display size

`\lkfigureh{height}{file}` places a figure with `max height` and `max width=\linewidth`. Both are maxima, never targets: a figure drawn 3 cm tall under `height=4.2cm` prints 3 cm tall. The live deck does the same: the `<img>` gets the figure's own height at 80 px per cm and a `max-height` at the given cap. A clip's `<video>` is capped the same way.

So TikZ is drawn at display size. A figure meant for a 4.2 cm slot is drawn 4.2 cm tall, in the font sizes of the preamble (`\small` labels, `\footnotesize` muted text), and its first line says so (`% drawn at display size, 4.2 cm tall`). The same figure scaled down from a larger drawing has labels too small to read from the back of the room. `lk review figs <dir>` previews the figures at that size; `lk review shoot <deck.html>` shows them in place.

## Titles

Titles are under 30 characters and fit one line. A second title line at 44 px runs from 110 to 154 px and crosses the 150 px line where the content starts; the live theme does not move the content, so title and content touch. In the study PDF the frame title is in the flow, and the second line costs about 0.6 cm of the content area, more than a bullet's worth. `lk review shoot <deck.html>` writes one PNG per slide; read the titles there and in the timing report, which lists them.

## Fragments and stacks

Fragments are `.fragment` Divs. The live deck reveals them step by step; the study PDF shows them all, in place, because the PDF shows the slide's final state. The height budget is therefore that of the final state. `lk review frags <deck.html>` lists the fragments per slide; `lk review shoot <deck.html> --fragments` writes one PNG per step so that each state can be measured.

A stack (`::: {.r-stack}`) puts several figures in one place and shows one at a time, which is how a two-stage figure (`name-stage1.tikz`, then `name.tikz`) is built up on the live deck. It is a live device: in the study PDF the stacked figures would print one under the other. Wrap the stack in `.live-only` and give the PDF the final figure in `.study-only`:

```markdown
::: {.r-stack .live-only}
![](assets/figures/pipeline-stage1.tikz){height=4.2cm}
![](assets/figures/pipeline.tikz){.fragment height=4.2cm}
:::
::: {.study-only}
![](assets/figures/pipeline.tikz){height=4.2cm}
:::
```

## Clips

A clip's `.fragment` goes on a wrapper Div, inside `.live-only`, and the study PDF gets the still in `.study-only`:

```markdown
::: {.live-only}
::: {.fragment}
::: {.movie clip="bar_bold" height=4.4cm}
:::
:::
:::
::: {.study-only}
![](assets/clips/bar_bold.png){height=4.4cm}
:::
```

Two reasons. The filter rewrites the `.movie` Div into a `<video>` and keeps none of its classes, so `.fragment` on the `.movie` Div itself does nothing. And a fragment is a live step: the study PDF gets the still where the reader needs it, with its own caption, rather than at the point of a step that does not exist on paper. `lk review frags <deck.html>` flags a clip's `.fragment` outside `.live-only`.

`aspect=` fixes the clip's box before the video loads, so that the slide does not jump; its default is the `width` over `height` of the clip's entry in `assets/clips/clips.json`, which `lk clips` writes. `height=` caps the box at 80 px per cm, as for figures.

## Display math

A display equation at the body size takes about one and a half lines, 50 to 60 px, plus the block margins. One display equation per slide; a derivation of several steps is a study-only slide, or fragments. The live deck keeps MathJax at the body size (the theme pins it at 100 percent). `lk review measure` counts an equation into the content's bottom edge like any other block.

## TikZ labels: two traps

A `%` in a label is a TeX comment: `50%` comments out the rest of the line, and the figure compiles to something else or fails. Write `50\%`. A label with `align=` or a `text width` is a paragraph, and TeX breaks lines and hyphenates it where it likes, at hyphens included. Put the breaks in yourself with `\\`, and keep words together with `\mbox{...}`. A failed compile is reported in the build output with the path of its log in `_lecturekit/tikz/`; a wrong label shows in `lk review figs` and in `lk review shoot`.

## Study PDF limits

Beamer columns do not shrink and the frame does not grow. A figure in a column is limited by the column's width as well as by its height, and a text column beside a tall figure must end above the footline on its own. `lk review overflow <deck.log>` reports every overfull box with its frame.

The bibliography is one frame, and neither output breaks it across pages. Four or five entries fit at the deck's size. More than that is two References slides, or a study-only second page. `lk review overflow` catches the PDF, `lk review measure` the live deck.

## The review commands

| Rule | Command |
| --- | --- |
| Content ends above the foot line at 677 px | `lk review measure <deck.html>` |
| Every slide reads right: titles on one line, figures at display size, nothing clipped | `lk review shoot <deck.html> [--out dir]`, `--fragments` for one PNG per step |
| Fragments where intended; a clip's `.fragment` inside `.live-only` | `lk review frags <deck.html>` |
| No overfull frame in the study PDF | `lk review overflow <deck.log>` |
| Figures readable at display size, labels as intended | `lk review figs <dir>` |

`<deck.html>` is `_build/slides-live.html`. `<deck.log>` is the Beamer log, `slides.log` beside the source; it survives the render when the Beamer format is given `latex-clean: false`.
