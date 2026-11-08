# Theming

One `_brand.yml` is the single source of truth for a deck's look. Every colour in it becomes a token with one name in each language: `nm<Name>` in LaTeX for Beamer and TikZ, `--nm-<name>` in the live deck's CSS, `<NAME>` in Python for the kits. The fonts are read the same way. Nothing else defines a colour or a font, so a restyle is an edit to this file and a rebuild. The TikZ figures, the Lua filter and the Beamer theme refer to colours by name only, which is what makes this possible.

`_brand.yml` is Quarto's brand file (the brand.yml format). Quarto applies it to the live deck itself (its typography and semantic colours); the extension reads the same file for everything Quarto does not cover: the engine's own tokens in the live deck, the Beamer side, the standalone TikZ figures and the Python kits. The kickoff example's `_brand.yml` is the paper preset.

## From palette to tokens

Every entry of `color.palette` becomes a token. Palette keys are spelled as the LaTeX colour name wants them, and the other two spellings follow:

| In `_brand.yml` | LaTeX (Beamer, TikZ) | CSS (live deck) | Python (`lecturekit.tokens`) |
| --- | --- | --- | --- |
| `ink` | `nmInk` | `--nm-ink` | `INK` |
| `concept` | `nmConcept` | `--nm-concept` | `CONCEPT` |
| `gauss` | `nmGauss` | `--nm-gauss` | `GAUSS` |
| `DoG`, `CSS`, `DN` | `nmDoG`, `nmCSS`, `nmDN` | `--nm-DoG`, `--nm-CSS`, `--nm-DN` | `DOG`, `CSS`, `DN` |
| `role-concept` | `nmRoleConcept` | `--nm-role-concept` | `ROLE_CONCEPT` |

The LaTeX name capitalises the first letter and each letter after a hyphen or underscore and keeps the rest as written; the CSS variable keeps the key as written; Python upper-cases it and turns hyphens into underscores. brand.yml's semantic names (`foreground`, `background`, `primary`, `secondary`, `tertiary`, `success`, `info`, `warning`, `danger`, `light`, `dark`, `link`) are resolved against the palette and emitted as tokens too (`nmForeground`, `--nm-foreground`, `FOREGROUND`); the engine does not read them, Quarto does, for its own HTML styling. Keep `foreground`, `background` and `link` on the engine's tokens so that Quarto and the theme agree.

How the tokens reach each consumer:

| Consumer | Mechanism |
| --- | --- |
| Study PDF | The filter writes `_lecturekit/tokens.tex` beside the source at every render: one `\definecolor{nm<Name>}{HTML}{...}` per colour, the fontspec lines, and the named TikZ styles. `beamer/lecturekit.tex` inputs it first, so the title page gets the tokens too, and provides the paper preset's values as fall-backs for a deck without a brand. |
| TikZ figures | The standalone document of each figure carries the same colour definitions, font lines and named styles ahead of `beamer/figure-preamble.tex`. The cache key is a hash of that whole source, so a token change recompiles every figure at the next build. |
| Live deck | The filter inlines `<style>:root{--nm-<name>:...}</style>` into the deck, adds `@font-face` rules for bundled families the brand names without files, and writes `_lecturekit/tokens.css` for the review tools. `reveal/theme.scss` colours everything with `var(--nm-*)`, with the paper preset as fall-back. |
| Python | `from lecturekit.tokens import INK, CONCEPT, GAUSS, rgb` reads the nearest `_brand.yml` upwards from the working directory, or the file named by `LECTUREKIT_BRAND`; `LECTUREKIT_MODE=dark` selects the dark side of a unified brand file. `lecturekit.theme.load_brand(path, mode)` returns the tokens of a given file. `lk theme [dir] [--brand FILE] [--mode light\|dark]` writes `_lecturekit/tokens.tex`, `tokens.css`, `tokens.py` and `tokens.json` for scripts outside the build; the render rewrites the first two. |

## The engine's tokens

The names the engine itself reads, which every brand file defines:

| Token | Used for |
| --- | --- |
| `paper` | the warm surface of goals, summary, section and pause slides |
| `slide` | the slide surface; the background of clips, placeholders and the pacing clock |
| `ink` | text, headings and emphasis (`**strong**`) unless `heading` and `body` are set |
| `muted` | the eyebrow of the title page, the foot, sub-item markers, captions, dates, the subtitle, `[text]{.muted}` spans, axes in figures |
| `hairline` | the foot rule, grids and guides in figures |
| `concept`, `caveat`, `example`, `anchor`, `question` | the five role colours: eyebrows, rules, coloured spans, the TikZ `nm/<role>` styles; `concept` also colours links, `caveat` the placeholders and the pacing clock when behind, `anchor` the clock when ahead |
| `input`, `state`, `update`, `context` | the four marks: `.blue`, `.teal`, `.orange`, `.purple` and `.mark-<name>` spans, list bullets (`input`), and the kits' colours for the parts of figures and clips |

Two optional tokens: `heading` for titles and eyebrows, `body` for running text. When absent, both fall back to `ink`. The dark preset uses the split: light-purple `heading`, green `body`, green-tinted white `ink` for emphasis.

Project tokens: a project adds its own entries to the palette, the four pRF model colours in the example (`gauss`, `DoG`, `CSS`, `DN`, `future`, distinguishable under deutan, protan and tritan vision against each other and against the ink), and they appear under the same three names (`nmDoG`, `--nm-DoG`, `DOG`). The engine knows nothing about them; the project's figures and clips do (`lecturekit.tikz.GAUSS`, `lecturekit.manim.DOG`, `token('dn')`), and POLICY.md asks that each keeps one meaning across a project's decks.

## Fonts

The engine bundles TeX Gyre Heros (sans, the body), TeX Gyre Pagella (serif, the titles) and Roboto (the dark preset) in `_extensions/lecturekit/fonts/`, under the GUST font licence and Apache 2.0, and TeX Gyre Pagella Math for mathematics. Three cases:

- A bundled family is loaded from its files whatever the brand says about its source, so a build needs no installed font. The paper preset names the two TeX Gyre families with `source: file` and the files in the vendored extension; the live deck gets Quarto's `@font-face` rules from the same entries.
- A family declared with `source: file` in the brand is used from its files, resolved against the brand file's directory. The upright regular file becomes the main file; a file of weight 600 or more (or `bold`, `semibold`) the `BoldFont`; the italic files `ItalicFont` and `BoldItalicFont`. The font files and their licence travel with the project.
- Any other family is loaded by name through fontspec and must be installed on the machine.

`typography.base` is the body family (sans), `typography.headings` the title family (serif). Beamer gets them as `\setmainfont` (the serif), `\setsansfont` (the sans) and the two letterspaced families of the theme, `\nmSerifCaps` at 2 percent of the em for titles and `\nmSansCaps` at 8 percent for labels, separate families on purpose: `\addfontfeature{LetterSpace=...}` on a family with a fixed `NFSSFamily` rewrites that family globally and the tracking leaks into body text. Mathematics is always TeX Gyre Pagella Math from the bundle (`\setmathfont` in `tokens.tex`); a sans body such as Roboto has no math companion, so the dark preset keeps the serif math font.

```yaml
typography:
  fonts:
    - family: TeX Gyre Heros
      source: file
      files:
        - path: _extensions/lecturekit/fonts/texgyreheros-regular.otf
          weight: 400
        - path: _extensions/lecturekit/fonts/texgyreheros-bold.otf
          weight: 700
        - path: _extensions/lecturekit/fonts/texgyreheros-italic.otf
          weight: 400
          style: italic
        - path: _extensions/lecturekit/fonts/texgyreheros-bolditalic.otf
          weight: 700
          style: italic
  base:
    family: TeX Gyre Heros
    size: 30px
    line-height: 1.4
  headings:
    family: TeX Gyre Pagella
    weight: 400
```

The Manim kit registers the bundled files with Pango and reads the brand's families, so a clip's labels follow the deck (MANIM.md).

## Presets as profiles

A preset is a second brand file and a Quarto profile that selects it:

```yaml
# _quarto-dark.yml
project:
  output-dir: _build-dark
brand: _brand-dark.yml
brand-mode: dark
```

`lk build --profile dark` (or `quarto render --profile dark`) builds the deck in the preset into `_build-dark/`; the default build is untouched. `brand-mode: dark` makes the filters read the dark variant when a brand file carries `light` and `dark` sections; a single-variant file, as in the examples, is read as it is. `lk new` writes both presets.

## What a restyle regenerates

| Part | On a rebuild | Why |
| --- | --- | --- |
| Live deck colours and fonts | yes | the CSS variables and Quarto's typography come from the brand |
| Study PDF | yes | `tokens.tex` is rewritten at every render |
| TikZ figures | yes | the compiled source embeds the tokens, so a change invalidates the cache; the figures name colours, never values. The slide surface in a figure is `nmSlide` (`SLIDE` in the kit), never `white`, and a tint is `tint(col, pct)`, which mixes towards the slide, never `col!pct`, which mixes with white: a figure that breaks this comes out as a light card on the dark preset (FIGURES.md) |
| Figures written by `make_assets.py` | only when the script bakes in values | a figure that names tokens (`nmConcept`, `nm/concept`, `SLIDE`) needs nothing; one that writes a value computed from `lecturekit.tokens` needs `make_assets.py` run again, which the build does as the pre-render step |
| Clips | only with `lk clips` | a rendered video is pixels: it does not follow a restyle until `lk clips` re-renders it, with `LECTUREKIT_MODE=dark` (the kit's `nmstyle` reads the brand's slide colour as the background and the tokens as the colours), and with `LECTUREKIT_BRAND` naming the preset's brand file when the preset is a separate file, as `_brand-dark.yml` is in the examples. A minute or two per clip. This is the known limit of the one-instruction restyle |
| The workshop-role icons | yes | the eyebrow icons are CSS masks filled with the role colour in the browser and TikZ drawn in the role colour on the page |
| PNG images | no | they are outside the theme by nature. `MANIFEST.md` names the script that wrote each one, and the restyle re-runs it or states that the image stays |

## The contrast check

```sh
lk review contrast _brand.yml
lk review contrast _brand-dark.yml --mode dark
```

checks every text colour (`ink`, `body`, `muted`, `heading`, `foreground`) and every role and mark colour on each surface (`slide`, `paper`, `background`) against WCAG AA: 4.5:1 for text, 3:1 for the roles and marks (eyebrows and large titles), or 4.5:1 for everything with `--strict`. Failures are printed with the nearest tint or shade of the same hue that passes, so that a restyle can take the suggestion or argue with it. It runs in the continuous build on both presets. A palette that passes is legible; whether its colours still read as distinct from one another is judged by eye in `lk review shoot`.

## Worked example: the restyle in one instruction

The instruction, roughly as it is typed:

```text
Restyle the whole kickoff deck: black background, light-purple titles and
eyebrows, green body text with green-tinted white for emphasis, Roboto for
everything, headings included. Keep the role colours distinguishable on
black, keep the figures and the clip consistent with the new palette, and
show me every slide when you are done.
```

What the assistant does, and what the viewer sees:

1. Writes `_brand-dark.yml` from the paper preset: surfaces black (`paper` and `slide` #000000); `ink` a green-tinted white (#E6F4EA) for emphasis; `body` a green (#8FD8B0) and `muted` a dimmer green (#6FA98A); `heading` light purple (#C9B6F2) for titles and eyebrows; `hairline` dark grey (#2A2A2A); the role and model colours lifted to tints that reach WCAG AA on black (concept #8FB8E8, caveat #F08C83, example #E8B960, anchor #5FD1C4, question #C9B6F2; DoG #F0C060, CSS #F28CB0, DN #5FD1D1). Roboto as `base` and `headings`, from the bundled files. Math keeps the serif math font, because Roboto has no math companion.
2. Writes `_quarto-dark.yml` and runs `lk build examples/kickoff --profile dark`. The TikZ figures recompile with the new tokens because they name colours rather than values; the live deck picks up the variables; Beamer loads Roboto through `tokens.tex`.
3. Runs `lk clips` with `LECTUREKIT_MODE=dark` and `LECTUREKIT_BRAND` pointing at the dark brand file, so the clip's background, ink and model colours follow. A minute or two of rendering; until it has run, the live deck plays the paper clip on a black slide, which is the one part of the restyle that is not a rebuild away.
4. Runs `lk review contrast examples/kickoff/_brand-dark.yml --mode dark`, which prints the pairs that fail with suggested values, and `lk review shoot examples/kickoff/_build-dark/slides-live.html --out review/dark --sheet`, which writes every slide as a PNG for the viewer to compare with the paper version.

What carries over by construction: colours, fonts, the role eyebrows and their icons, the figures (they name `nmSlide` and tint towards it, so no card stays white), the PDF, and the clip once re-rendered. What still needs judgement, and the episode shows rather than hides: a palette designed for white paper does not survive inversion unchanged. The amber of the DoG model and the magenta of the CSS model lose their separation on black; the light-grey stimulus apertures of the clips become dark-grey patches; a hairline that was visible on white vanishes. The second half of the work is the assistant proposing adjusted tints, the contrast tool confirming them, and one or two figures being judged by eye. Fixed PNG images are regenerated by their scripts or stay as they are, and the assistant says which.

The one-instruction restyle works because the design put the style in one place, and the remaining ten percent is taste, checked by a tool and decided by a person.

## The manim8 style bridge

`lk theme [dir] --manim8 0.1.0` also writes a manim8 style version, `styles/<brand>/<version>/style.yaml`, inheriting manim8's `default@0.5.0` and mapping the brand's tokens to manim8's palette roles: `background` from `slide`, `foreground` from `ink`, `secondary_text` from `muted`, `muted` from `hairline`, `primary_signal` from `input`, `normalization_pool` from `update`, `emphasis` from `concept`, `warning` from `caveat`, `comparison` from `context`, `neutral` from `muted`; the project tokens travel as extra palette entries, and the typography roles (title, body, annotation, axis and tick labels, caption) take the brand's heading and body families with sans fall-backs. manim8's rule that a style change is a new version, never an edit, suits the restyle: the dark preset yields a new version such as `lecturekit-dark@0.1.0`, and `lk clips` re-renders the manim8 clips against it (CLIPS.md). manim8 is the second release's layer; the bridge is in place now.
