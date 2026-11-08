# Figures

Figures are drawn from numbers, by a script, at display size, in the deck's colours by name. The drawing language is TikZ; the build compiles each figure once and places it in both outputs. AUTHORING.md has the ways to put a figure on a slide, LAYOUT.md the heights a slide allows; this page is about making the figures.

## make_assets.py on the TikZ kit

Each deck has a `make_assets.py`. It reads the deck's data, `assets/data/*.json`, the summaries the simulations wrote (WORKFLOW.md), and writes one `.tex` file per figure into `assets/figures/`, one `tikzpicture` each. The build runs it as the project's pre-render step; `python make_assets.py [name ...]` runs it by hand. The slide places the file:

```markdown
\nmfigureh{4.2cm}{assets/figures/lineage.tex}
```

`make_assets.py` begins `from lecturekit.tikz import *`: the TikZ kit, the module every deck's figure script imports. What it gives:

| Name | What it is |
| --- | --- |
| `INK`, `MUTED`, `HAIR`, `PAPER`, `SLIDE` | the TikZ colour names `nmInk`, `nmMuted`, `nmHairline`, `nmPaper`, `nmSlide`; `SLIDE` is the slide surface, and the only name for it |
| `tint(col, pct)` | `col!pct!nmSlide`: a tint of a colour towards the slide surface, for a fill or stroke that fades into the slide (`tint(BLUE, 6)` for a card's fill) |
| `BLUE`, `TEAL`, `ORANGE`, `PURPLE`, `CAVEAT` | `nmConcept`, `nmState`, `nmUpdate`, `nmContext`, `nmCaveat`: the figures' names for the colours they draw with |
| `CONCEPT`, `EXAMPLE`, `ANCHOR`, `QUESTION`, `INPUT` | the role colours and the input mark by their token names |
| `GAUSS`, `DOG`, `CSS`, `DN`, `FUTURE` | the project tokens of the worked example, the four pRF models and future work (drawn dotted) |
| `STYLE` | the `tikzpicture` options every figure starts with: 1 cm units, nodes in footnotesize sans in ink with 1.5 pt inner sep |
| `SMALL`, `TINY`, `HEAD` | font strings for a node: scriptsize, tiny, footnotesize bold |
| `PX_PER_CM`, `PT_PER_CM` | 88 live pixels and 28.45 pt per centimetre |
| `FIGURE_HEIGHTS` | the heights that leave room for text: `full` 5.6 cm, `one_bullet` 4.8 cm, `two_bullets` 4.2 cm, `column` 4.4 cm |
| `color(name)` | the TikZ name of a brand token: `color('concept')` is `nmConcept` |
| `hex(name)` | the value of a token (`#175B8E` for `concept` in the paper preset), for a script that must write a raster image |
| `Panel(x0, y0, w, h, u, v)` | maps data coordinates to page coordinates inside a rectangle; `pt`, `path`, `fill`, `hline`, `vline`, and `axes` with ticks, labels and a rotated axis title |
| `stack(L, x, y, items)` | a column of notes under each other from a top-left corner, each `(text, colour)`, heights estimated so nothing overlaps; returns the y below the last |
| `clipped_path(P, xs, ys, style, lo, hi)` | a curve drawn only where its values lie in a range, as separate segments |
| `writer(fig_dir)` | `write(name, lines)` for one deck: wraps the lines in a `tikzpicture` with `STYLE` and saves `assets/figures/<name>.tex` |
| `box(L, x, y, w, h, title, body, col)` | a rounded box with a bold title and a small body |
| `contours(P, A, Bl, Z, levels)` | contour lines of a field through matplotlib, drawn in a panel, tinted towards the slide for higher levels (through `tint`) |
| `load_data(path)` | a JSON summary written by a simulation |
| `escape(text)` | escapes what breaks a TikZ label: `%` above all, and `\`, `&`, `#`, `_` |
| `nohyphen(text)` | prefixes `\hyphenchar\font=-1 ` so a wrapped node does not hyphenate |
| `polyline(points)` | `(x,y) -- (x,y) -- ...` for a `\draw` of sampled data |
| `np`, `Path`, `math` | re-exported for the script |

A figure's lines are TikZ strings; the kit draws nothing itself. The kickoff example's `make_assets.py` is the model: six schematics 13 cm wide, each a function that appends to a list and ends in `write('name', L)`, an `ALL` dictionary of the functions, and a `__main__` that draws the named ones or all.

Every number in a figure comes from `assets/data/` or from a fact recorded in `FACTS.md`, never from a literal nobody can trace; the script runs again at any time and writes the same files; the figure names its colours.

Two names a figure never uses: the literal colour `white`, and TikZ's `col!pct` tints. TikZ mixes `!pct` with white, so on a dark surface both come out as light cards. The slide surface is `SLIDE` (`nmSlide`), never `white`; a fill or stroke that fades into the slide is `tint(BLUE, 6)`, never `f'{BLUE}!6'`. The kickoff's `make_assets.py` and its shipped `bar-bold.tex` follow this, and the figures therefore restyle with the dark preset without an edit.

## Drawn at display size

`\nmfigureh{Hcm}` is a cap, not a target, and the live deck shows a figure at its natural size, never larger. A figure is therefore drawn at the size it will have on the slide: 12 to 13 cm wide for a full-width slide (the text width is 14.2 cm), about 4.2 cm high above two one-line bullets, 4.8 cm above one, 5.6 cm alone (LAYOUT.md). The coordinates in the file are the centimetres of the slide, the labels are footnotesize and scriptsize as the styles set them, and a figure for a 4.2 cm slot is 4.2 cm tall in the file. The same figure scaled down from a larger drawing has labels too small to read from the back of the room.

```sh
lk review figs examples/kickoff            # every assets/figures/*.tex
lk review figs examples/kickoff shelf      # one, by name
```

compiles each figure standalone with the brand's fonts and colours, as the build does, writes a PNG at 88 px per cm to `review/figs/`, and prints the natural size in cm, which is what `\nmfigureh` compares its cap with; a figure wider than the 14 cm slide is flagged (it is scaled down on the page). `--brand FILE --mode dark` previews a figure in a preset; `--out DIR` moves the PNGs. Failures print the first error of the log.

## File naming and placement

`assets/figures/<name>.tex`, one `tikzpicture` each, lower-case names with hyphens, the same name as the function that writes it. The slide places the file with `\nmfigureh{Hcm}{assets/figures/<name>.tex}` (bare or in a `{=latex}` block), `\nmfigure{...}` to cap the width only, or `![](assets/figures/<name>.tex){height=Hcm}`; a `.tikz` extension works as well. Paths are relative to the deck folder. The study PDF inputs the file in the frame, the live deck gets the compiled SVG.

## Two-stage figures

A figure that builds up on the live deck exists as two files written by the same code path from the same data, `name-0.tex` (the first state) and `name.tex` (the final), so that they align to the pixel. The stage file draws the later elements inside an invisible scope rather than leaving them out, so that both files have the same bounding box and the stack does not jump:

```python
write('engine', L + L2)
write('engine-0', L + ['\\begin{scope}[opacity=0]'] + L2 + ['\\end{scope}'])
```

The slide stacks them live and prints the final one in the PDF (AUTHORING.md, Reveals). `lk review frags` reports an r-stack whose steps differ in size; `lk review shoot --fragments` writes one PNG per step.

## The named styles

Every figure is compiled with the deck's fonts, the colour tokens and `_extensions/lecturekit/beamer/tikz-styles.tex`, which defines styles available in both outputs, so a figure can name a style and never a value:

| Style | What it sets |
| --- | --- |
| `nm` | the base: 0.8 pt lines in ink, footnotesize sans text |
| `nm/box` | a node with an ink outline, rounded corners, 5 pt padding, centred text and a fill in the slide colour (`nmSlide`) |
| `nm/arrow` | a path with a Latex arrow head |
| `nm/hairline` | a 0.4 pt line in the hairline colour, for axes, grids and guides |
| `nm/muted` | scriptsize text in muted, for annotations |
| `nm/<role>` | outline and text in the role's colour: `nm/concept`, `nm/caveat`, `nm/example`, `nm/anchor`, `nm/question` |
| `nm/<role> text` | text only in the role's colour, for a bare label |

Marks and project tokens are used as colours directly: `draw=nmInput`, `fill=nmGauss!10!nmSlide`, `text=nmUpdate`. The TikZ libraries loaded are `arrows.meta`, `positioning`, `calc`, `fit`, `backgrounds`, `shapes.geometric` and `decorations.pathreplacing`; `amsmath` is available for labels. The feature deck's `pipeline.tex` uses the styles alone:

```latex
\begin{tikzpicture}[x=1cm,y=1cm,every node/.style={font=\sffamily\footnotesize,text=nmInk,inner sep=1.5pt},node distance=0.9cm]
  \node[nm/box] (src) {slides.qmd};
  \node[nm/box, nm/concept, right=of src] (lk) {lecturekit filter};
  \node[nm/box, above right=0.2cm and 0.9cm of lk, nm/anchor] (live) {live deck\\Reveal.js};
  \node[nm/box, below right=0.2cm and 0.9cm of lk, nm/example] (study) {study PDF\\Beamer};
  \draw[nm/arrow] (src) -- (lk);
  \draw[nm/arrow] (lk) -- (live);
  \draw[nm/arrow] (lk) -- (study);
  \node[nm/muted, below=0.35cm of src] {one source};
  \node[nm/muted, below=0.35cm of study] {two outputs};
\end{tikzpicture}
```

The kit's own figures set their styles inline from the constants instead; both are fine, as long as no literal colour appears.

## Published figures

A figure from a paper is not reproduced. It is redrawn from digitised values, the points read off the published figure with a digitiser or taken from the paper's source data, and those values go into `assets/data/` with a note of where they came from. The slide cites the source and says the figure was redrawn from digitised values; `MANIFEST.md` records the source, what was digitised and the licence situation (POLICY.md). Where the data are public, the figure is recomputed from them instead, which is better still; where a simulation of our own shows the same thing, it replaces the published figure.

## Placeholders

A figure whose data are missing is still a figure. `make_assets.py` writes a labelled placeholder when its input is absent, so that the deck builds and the gap is visible; on the page the theme's `\lkplaceholder{4cm}{what is missing}` draws a dashed box in the caveat colour with the label. The build adds its own layer: a figure that fails to compile, or whose file cannot be read, becomes a dashed box reading `figure missing: <name>` in the live deck and `\lkplaceholder` in the PDF, with the figure's name and the path of its log printed during the build. Nobody mistakes a draft for a result.

## Traps

- A `%` in a label is a TeX comment: `50%` comments out the rest of the line and the figure compiles to something else or fails. Write `50\%`, or pass the text through `escape()`.
- A wrapped node (`text width=`) hyphenates unless the font is told not to: put `\hyphenchar\font=-1 ` at the start of the node text (`\hyphenpenalty` does not work there), or use `nohyphen()`. Set the breaks yourself with `\\` where the wording matters.
- Font strings are raw TeX: `font=\sffamily\scriptsize\bfseries`.
- A rotated axis title is set with `anchor=south` at a fixed distance left of the axis; a rotated node's `above=` shift moves it along the page, over the tick labels (`Panel.axes` does this).
- The other special characters, `&`, `#`, `_`, `$`, need escaping when they are text.
- Colours are tokens, never hex values: a literal survives a restyle and shows it. `white` is a literal too: the slide surface is `SLIDE`, and a tint is `tint(col, pct)`, never `col!pct`, which mixes with white and makes a light card on a dark surface.

The build names the failing figure and its log in `_lecturekit/tikz/<hash>.log`; a label that compiled but reads wrong shows in `lk review figs` and in `lk review shoot`.

## What the build does with a figure

The filter wraps the picture in a `standalone` document (12 pt, `tikz`, a 1 pt border) with `fontspec` and `unicode-math`, the brand's fonts and colour definitions, the named styles and `figure-preamble.tex` (sans as the default family, so footnotesize and scriptsize render as on the page), and compiles it with XeLaTeX into `_lecturekit/tikz/<hash>.pdf`, the hash being that of the whole standalone source. For the live deck it converts the PDF to an SVG with text as paths (PyMuPDF, else poppler's `pdftocairo`, else `dvisvgm`), so that no web font is needed, sized at 1280 px per 453.54 pt page so that the figure keeps its proportion on the study page, and places an `<img class="tikz">` under a `max-height` cap at 8.8 px per mm. `NM_FIGURE_FORMAT=png` produces 2x PNGs instead. For the study PDF `\nmfigureh` inputs the file in the frame and scales it down to the text width and the height when it is larger, never up. A figure whose source has not changed is not compiled again.
