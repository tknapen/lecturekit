# Notices

lecturekit is MIT licensed (see `LICENSE`). The example deck's content
(`examples/features/slides.qmd` and its notes and figure sources) is
CC BY 4.0, Tomas Knapen.

Third-party components:

| Component | Where | Licence | Notes |
| --- | --- | --- | --- |
| Quarto, Pandoc, Reveal.js | fetched by the user; Reveal.js is bundled into every live build by Quarto | GPL 2+ (Pandoc), MIT (Reveal.js), MIT (Quarto) | nothing redistributed by this repository |
| TeX Gyre Heros, Pagella, Pagella Math | system fonts, or copied into `_extensions/lecturekit/fonts/` by the extraction | GUST Font License | the licence file is copied beside the fonts when they are bundled |
| Roboto | system font (`fonts-roboto`) for the dark preset, or bundled | Apache 2.0 (classic release) or OFL 1.1 (current release) | the licence of the release used is copied beside the files when bundled |
| Chicago Manual of Style author-date CSL | `_extensions/lecturekit/lecturekit.csl`, modified to set citation names in italics | CC BY-SA 3.0 (Citation Style Language styles) | derived from Pandoc's default style |
| Manim Community | optional dependency of the clips extra | MIT | not bundled |
| manim8 (SciAnim Studio) | optional dependency, second release | MIT | not bundled |
| 3Blue1Brown-derived kit modules (`nmnet`, `nmpix`, `nmfield`) | to arrive with the extraction | see note | written fresh for Manim Community after scenes in 3Blue1Brown's videos repository, used as storyboards; the per-clip docstring names the scene followed; their licence terms are checked before these modules ship |
| Logos and wordmarks of institutions and projects | none bundled | their owners | the example figures use names in type, not logos |

Provenance rules carried as policy: a figure redrawn from a publication cites
the source and says it was redrawn from digitised values; `MANIFEST.md` in
every project lists each image with its origin and licence.
