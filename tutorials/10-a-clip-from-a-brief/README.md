# Episode 10: A clip from a brief

Length: 8 minutes. Second release: this episode waits for manim8's first tagged release and for `lk clips` to drive it.

## Goal

A manim8 clip from a one-paragraph brief, through checkpoints and review, into a slide through the seam.

## What the viewer sees

The brief typed. The manim8 skill turns it into a validated `animation.yaml` and `storyboard.yaml` with named checkpoints, renders the checkpoints with layout reports, and offers proposals; the lecturer accepts or rejects them in the review server. `scianim render --profile final` produces the video. `lk clips` copies the MP4 and the checkpoint PNG into `assets/clips/`, writes the `clips.json` entry from the render manifest, and the movie block on the slide picks it up. The still in the PDF is the named checkpoint. The clip is in the deck's style, through the style version `lk theme --manim8` wrote.

## Commands and the brief

```sh
uv pip install -e ".[clips,manim8]"
lk theme . --manim8 0.1.0           # writes styles/<brand>/0.1.0/style.yaml
cd clips                            # the project's manim8 workspace
# the brief goes to the manim8 skill; the project lands in clips/families/<family>/bar_sweep/
cd ..
lk clips .                          # runs scianim render --profile final, fills assets/clips and clips.json
lk build .
```

```text
A bar sweeps the visual field from left to right in eight steps. One
voxel's receptive field sits right of centre; its response rises as the bar
crosses it and falls after. Show the field, the bar and the response trace
together; a checkpoint when the bar is on the field, and one at the end.
```

The block in `slides.qmd`:

```markdown
::: {.movie clip="bar_sweep" height=4.4cm}
A bar crosses one receptive field; the response follows.
:::
```

## Points to make

- The seam is the same as for a kit clip: `clips.json` names the files, the slide names the clip (`docs/CLIPS.md`).
- Checkpoints are the study PDF's still by construction, where the kit needs a chosen frame.
- The style bridge maps the brand's tokens to manim8's palette roles; a restyle is a new style version, and `lk clips` re-renders against it (`docs/THEMING.md`).
- Proposals that touch equations or sources need the lecturer's sign-off, the same rule as `FACTS.md`.

## Artefacts

- `before/brief.txt`: the paragraph.
- `after/clips/families/<family>/bar_sweep/`: `animation.yaml`, `storyboard.yaml`, the checkpoint PNGs and layout reports.
- `after/assets/clips/clips.json` and the still; the MP4 if small.
- `after/slide-live.png` and `after/slide-study.png`.

## Notes

manim8 is integrated as an optional extra, pinned to a tag until its first PyPI release, not as a submodule. Its pattern library surveys 3Blue1Brown's scenes and carries the same licence note as the kit's derived modules (`docs/CLIPS.md`).
