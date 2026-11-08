# Third-party material and licences

The code in this repository (the Quarto extension, the filters, the kits, the tools) is under the MIT licence in
`LICENSE`. The content of `examples/kickoff` and `examples/features` (slides, notes, storyboard, the figures'
sources) is by Tomas Knapen under CC BY 4.0. The following material comes from elsewhere.

| Component | Where | Origin | Licence | Notes |
|---|---|---|---|---|
| TeX Gyre Heros and Pagella (OpenType), TeX Gyre Pagella Math | `_extensions/lecturekit/fonts/` | GUST e-foundry | GUST Font License (`fonts/GUST-FONT-LICENSE.txt`) | loaded by file in both outputs; copied into a live build by Quarto |
| Roboto (Regular, Bold, Italic, Bold Italic) | `_extensions/lecturekit/fonts/roboto/` | Google | Apache License 2.0 (`fonts/roboto/LICENSE.txt`) | the dark preset |
| Reveal.js | bundled into every live build by Quarto, with its licence | Hakim El Hattab and contributors | MIT | not stored in this repository |
| Quarto, Pandoc, Dart Sass | installed by the user | Posit; John MacFarlane and contributors | MIT; GPL 2 or later | used at build time, not redistributed |
| TeX Live or TinyTeX | installed by the user | the TeX Live team | per package | used at build time |
| PyMuPDF | an optional dependency (`figures`, `review`, `dev` extras) | Artifex | AGPL 3 (or commercial) | used at build time to turn PDF figures into SVG and PNG; nothing of it is distributed; poppler's `pdftocairo` is the fallback |
| Playwright and Chromium | an optional dependency (`review`, `dev` extras) | Microsoft; the Chromium authors | Apache 2.0; BSD | the review tools |
| Manim Community | an optional dependency (`clips` extra) | the Manim Community | MIT | used to render clips |
| manim8 (SciAnim Studio) | an optional dependency (`manim8` extra; second release) | Tomas Knapen | MIT | not bundled |
| `src/lecturekit/manim/nmnet.py`, `nmpix.py`, `nmfield.py` | this repository | written for Manim Community after scenes in 3Blue1Brown's videos repository (github.com/3b1b/videos), used as storyboards only | the code is MIT; the storyboards' licence terms are to be verified before a release that includes these three modules (the kickoff example does not use them) | each clip's docstring names the scene it follows |
| Names of software packages and institutions in the example's figures | `examples/kickoff` | their owners | not ours | set in type; no logos or wordmarks are reproduced |

Two provenance rules carry into every project as policy: a figure redrawn from a publication cites the source and
says it was redrawn from digitised values; `MANIFEST.md` lists every image with its origin and licence.
