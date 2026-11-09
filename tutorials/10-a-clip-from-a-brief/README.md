# Episode 10: A clip from a brief

Length: 8 minutes. Needs manim8 0.1.0a0 through lecturekit's `manim8` extra, on Python 3.12 or later.

## Goal

A manim8 clip from a one-paragraph brief, through checkpoints and review, into a slide through the seam, in both presets.

## What the viewer sees

A new project made with `lk new --manim8`: its `clips/` is a manim8 workspace with the deck's two bridged styles, a family and a starter project. The brief typed. The manim8 skill turns it into a validated `animation.yaml` and `storyboard.yaml` with named checkpoints, renders the checkpoints with layout reports, and offers proposals; the lecturer accepts or rejects them in the review server. `lk clips` builds the family's render environment on its first run, generates the scene, renders the final video with `scianim render --json`, copies the full movie and every checkpoint PNG into `assets/clips/`, and writes the `clips.json` entry from the render manifest; the movie block on the slide picks it up. The still in the PDF is the last checkpoint, or the one the slide names. The clip is in the deck's style, through the style `lk theme --manim8` wrote; `lk clips --mode dark` renders it again under the dark style for the dark build.

## Commands and the brief

```sh
pip install "lecturekit[clips,manim8]"   # manim8 at its v0.1.0a0 tag; Python 3.12 or later (docs/INSTALL.md)
scianim skill install                    # the manim8 skill, where the agent finds it
lk new sweep-lecture --manim8 --budget 20
cd sweep-lecture
# clips/styles/lecturekit_paper/0.1.0 and lecturekit_dark/0.1.0, clips/families/sweep_lecture/first_clip
# the brief goes to the manim8 skill; the project lands in clips/families/sweep_lecture/bar_sweep/
lk theme . --manim8 0.1.0                # selects the paper style in bar_sweep, through a manim8 proposal
lk clips . --only bar_sweep              # sync (once), codegen, render --json; assets/clips and clips.json
lk clips . --only bar_sweep --mode dark  # under lecturekit_dark@0.1.0, into assets/clips/dark
lk build .
lk build . --profile dark
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

`still="bar_on_field"` on the block would print the first checkpoint instead of the last; `lk clips --still bar_sweep=bar_on_field` makes that the entry's own still.

## Points to make

- The seam is the same as for a kit clip: `clips.json` names the files, the slide names the clip (`docs/CLIPS.md`). The entry adds the manim8 job, its cache key and every checkpoint.
- Checkpoints are the study PDF's still by construction, where the kit needs a chosen frame.
- A second `lk clips` with nothing changed is a cache hit in manim8: no rendering, the same job.
- The style bridge maps the brand's tokens to manim8's palette roles; a restyle is a new style version, and `lk clips` renders against the newest (`docs/THEMING.md`). The dark preset is the same clip under another style: colours and fonts change, timing does not.
- Proposals that touch equations or sources need the lecturer's sign-off, the same rule as `FACTS.md`.

## Artefacts

- `before/brief.txt`: the paragraph.
- `after/clips/families/sweep_lecture/bar_sweep/`: `animation.yaml`, `storyboard.yaml`, `proposals/applied/`; the checkpoint PNGs and layout reports from the review.
- `after/assets/clips/clips.json`, `after/assets/clips/dark/clips.json` and the stills; the MP4s if small.
- `after/slide-live.png`, `after/slide-live-dark.png` and `after/slide-study.png`.

## Notes

manim8 is integrated as an optional extra, pinned to its git tag until its first PyPI release, not as a submodule; lecturekit runs `scianim` and reads the manifest it prints. Renders, job records and the family's `.venv` stay out of git (the project's `.gitignore`); the family's `uv.lock` is committed. Its pattern library surveys 3Blue1Brown's scenes and carries the same licence note as the kit's derived modules (`docs/CLIPS.md`).
