# Episode 1: One source, two outputs

Length: 6 minutes.

## Goal

Clone, install and build the kickoff deck. See the live deck and the study PDF side by side, and the timing report the build prints.

## What the viewer sees

A terminal on one half of the screen, a browser on the other. The clone, the install, one build command. The live deck opens in the browser, the PDF beside it: the same slide in both, the eyebrow, the title in capitals, the figure at the same size. Back in the terminal, the timing report: seven timed slides and the references, 15 minutes planned against a budget of 15. In the browser, S opens the speaker view with the notes and the pacing clock; on the first content slide the clip plays, a click pauses it, R replays it.

## Commands

```sh
git clone https://github.com/tknapen/lecturekit
cd lecturekit
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
quarto check
lk build examples/kickoff
open examples/kickoff/_build/slides-live.html    # xdg-open on Linux
open examples/kickoff/_build/slides-study.pdf
```

Then in the browser: arrow keys through the deck; S for the speaker view; on slide 2 (Why we are here) a click on the clip, space, then R; P resets the pacing clock.

## The report as printed

```text
  min     at  role         slide
    2      2  concept      Why we are here
    2      4  explanation  Credit where credit is due
    2      6  concept      What we proposed: an engine
    2      8  concept      What we proposed: a community
    3     11  explanation  Where we stand: prfmodel 0.2.0
    2     13  concept      The person who built it
    2     15  summary      Two days
    -     15  explanation  References
slides 8  planned 15 min  untimed 1  budget 15 min  ok
(per slide in examples/kickoff/_build/timing.txt)
```

## Points to make

- One file, `slides.qmd`; two outputs, `_build/slides-live.html` and `_build/slides-study.pdf`.
- The heading carries the role and the minutes; the report sums them against the budget in the front matter.
- The figures are the same TikZ files in both outputs, at the same size: the live deck caps a figure at 8.8 px per mm of its print height and never upscales it.
- Nothing on these slides was drawn by hand: `make_assets.py` wrote the figures from the proposal's numbers and the recorded run, and the build ran it first.

## Artefacts

- `before/`: empty; the episode starts from a fresh clone.
- `after/timing.txt`: the report as written to `examples/kickoff/_build/timing.txt`.
- `after/slide-02-live.png` and `after/slide-02-study.png`: the first content slide from both outputs, for the side-by-side.

## Notes

The install steps, TeX included, are in `docs/INSTALL.md`; `tools/install.sh` does them in one go and ends by building both example decks. The clip plays because the review tools and the browser read the deck over a local server or from the built folder; `resources: [assets/**]` in `_quarto.yml` is what put the clip beside the deck (`docs/AUTHORING.md`).
