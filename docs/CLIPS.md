# Clips

A clip is a short animation that plays in the live deck and prints as a still in the study PDF. The clip shows the mechanism and nothing else; the slide supplies the claim. This page gives the rules a clip follows, the seam between a deck and whatever rendered the clip (`assets/clips/clips.json` and the `clip=` form of the movie block), what `lk clips` does, the Manim kit in brief, and manim8 as the second release's layer.

## Rules

- Render at 1280 by 720 with a white background (the slide colour); the multiply blend handles paper slides. The kit sets this when it is imported; `lk clips --size WxH` or the environment variable `NM_CLIP_SIZE` changes it, and the frame stays 9 scene units high. Rendering on the paper colour directly is also fine for a clip that will only ever sit on a paper slide.
- No titles or captions in the clip: the slide carries the title, the speaker the words. A legend, tick labels and a marker inside the drawing are part of the mechanism and stay.
- Every clip has a static equivalent in the study PDF: the still that `lk clips` writes and `clip=` places, or a `.study-only` figure drawn from the same numbers (the kickoff's `bar-bold.tex` and its clip share one forward model).
- Clips play without browser controls. A click or the space bar pauses and resumes the clip; R replays it from the start; space does not advance the slide while a clip is shown. A clip starts when its slide appears and stops when the slide is left.
- Browsers cache clips by file name: a re-rendered clip that looks unchanged on screen needs a new file name.
- `aspect` is the clip's pixel ratio. The `clip=` form reads it from `clips.json`; the `src=` form takes `aspect="4:3"` or `"1:1"` for a clip in a column, or any `W:H` for a clip cropped to its content. A wrong aspect letterboxes the clip and wastes height.
- A clip on a key press: `::: {.fragment}` around `:::: {.live-only}` around the `.movie`, never the other way round. A sequence of clips is an `.r-stack` inside `.live-only`, each later clip in a `.fragment`; the step's clip starts when its fragment appears and the earlier one stops. Check: `lk review frags <live.html>` prints, per step, whether each clip is shown and playing, and flags a clip's fragment outside `.live-only`.
- Colours in a clip are tokens from the brand (`INK`, `BLUE`, `GAUSS`, `token('dn')`), never values, and the background is the brand's slide colour, so a restyle can re-render the clip in the new palette. It must: a rendered video is pixels and does not follow a restyle until `lk clips` re-renders it with `LECTUREKIT_MODE=dark` (and `LECTUREKIT_BRAND` naming a separate preset file such as `_brand-dark.yml`). This is the known limit of the one-instruction restyle (THEMING.md).

## The seam: clips.json and clip=

`assets/clips/clips.json` maps clip names to files and facts about them. `lk clips` writes it; a hand-written entry for a committed MP4 is valid too, as the kickoff's slide 1 could carry for its shipped `bar-bold.mp4`.

```json
{
  "bar-bold": {
    "video": "assets/clips/bar-bold.mp4",
    "still": "assets/clips/bar-bold.png",
    "width": 1280,
    "height": 720,
    "duration": 20.0,
    "source": "anim/clip_bar_bold.py:BarBold",
    "revision": "a1b2c3d4e5f6"
  }
}
```

| Field | Meaning |
| --- | --- |
| `video` | the MP4, relative to the deck folder (`mp4` is accepted as an alias) |
| `still` | the PNG the study PDF prints and the live deck shows as poster (`png` is accepted as an alias) |
| `width`, `height` | the pixel size of the video after cropping; the deck's `aspect` |
| `duration` | seconds; informative |
| `source` | where the clip comes from: the scene file and class, the manim8 project, or a note such as `assets/clips (pre-existing)` |
| `revision` | what rendered this version: a hash of the scene source for a kit clip, the render manifest's revision for a manim8 clip; a stale clip is visible by it |

The deck names the clip:

```markdown
::: {.movie clip="bar-bold" height=4cm}
A one-line caption, small and muted under the clip; on the page it follows the still.
:::
```

The entry supplies the video, the still and the aspect, so the block needs no `.live-only` wrapper: the live deck gets a boxed autoplaying video with the still as poster, the study PDF gets the still at `height=` (default 4 cm) through `\lkimageh`, which never upscales. A name that is not in the index and has no `src=` stops the build with "is not in assets/clips/clips.json (run lk clips)". The older `src=` form stays for a clip with a `.study-only` figure instead of a still (AUTHORING.md, Movies). Paths are relative to the deck folder, and `resources: [assets/**]` in `_quarto.yml` copies them into the build.

The MP4, the PNG and `clips.json` are committed with the deck, so that a reader who clones the project, or a build where Manim is not installed, still has the clip. A changed `revision` is how a stale committed file is noticed.

## lk clips

```sh
lk clips [deck] [--only name ...] [--size 1280x720] [--crop]
```

renders every scene under the deck's `anim/clip_*.py`. Each file holds one or more Manim `Scene` classes on the kit (`from kit import *`); the clip's name is the file's stem after `clip_`, with underscores as hyphens (`clip_bar_bold.py` gives `bar-bold`), and a second scene in the same file appends its class name. `--only` takes clip names (`bar-bold`, `bar_bold` or the class `BarBold` all name the kickoff's clip). The scene is rendered with Manim at 1280 by 720 on white (`--size 1920x1080` or `NM_CLIP_SIZE` for another size; the kit reads it), 30 frames per second, without a title, with `LECTUREKIT_BRAND` pointing at the deck's brand so the colours follow it. The video is copied to `assets/clips/<name>.mp4`; its last frame becomes the still `<name>.png`, unless the scene class sets `still = <seconds>` to name another moment. `--crop` trims the video and the still to the content's bounding box (plus a margin, to even sizes), for a clip in a column; `clips.json` records the resulting shape, which the deck uses as the clip's aspect. Manim's own output goes to `anim/media/`, which git ignores. Rendering takes a minute or two per clip; ffmpeg is found on the path or through `imageio-ffmpeg`.

Projects under `clips/families/<family>/<name>/` (a manim8 workspace, holding a `storyboard.yaml`) are rendered through `scianim render --profile final` in the same run: the final video and the named checkpoint PNG are copied into `assets/clips/` and the render manifest supplies the dimensions, duration and revision. This is the second release's layer (below); `lk clips` finds the workspace from the project root.

A restyle does not reach a rendered clip until it is rendered again: `lk clips` after the brand change, with `LECTUREKIT_MODE=dark` so that `nmstyle` reads the dark side of the brand (the slide colour becomes the background, the tokens the colours), and with `LECTUREKIT_BRAND` naming the preset's brand file when it is a separate file, as `_brand-dark.yml` is in the examples (THEMING.md). The figures follow a restyle at the next build because they name `nmSlide` and tint towards it; the clips are the part that costs a render.

## The Manim kit, in brief

A deck's `anim/kit.py` is two lines (`lk new` writes it): `from lecturekit.manim import *` and `HERE` and `DATA`, the deck's `anim/` and `assets/data/`. Every clip starts with `from kit import *` and gets the house style (`nmstyle`: the bundled TeX Gyre fonts registered with Pango, the colours of the deck's `_brand.yml`, `label()`, `Frame` with `inv()` and `scale`, `normal_pdf`), networks (`nmnet`), pixel grids and convolutions (`nmpix`), two-dimensional flows (`nmfield`) and the population receptive field primitives (`nmprf`: `VisualField`, `HeightSurface`, `FeatureStack`, `TracePanel`, `Dial`, `Bars`, `clip_size`, the numpy fields and colour ramps). MANIM.md is the reference. Manim Community 0.22 needs Pillow below 11.3: `pip install lecturekit[clips]`.

The kickoff's clip, `anim/clip_bar_bold.py`, is the model: a docstring that says what the clip shows and in which stages, a numpy forward model shared with the static figure (`anim/bar_model.py`), the recorded run in `assets/data/s01.json` as the numbers, a `VisualField`, a `Frame` for the traces, `always_redraw` traces that draw up to a `ValueTracker`, and a schedule of events in simulated seconds.

## manim8, the second release

manim8 (SciAnim Studio) turns a brief in plain language or YAML into a validated `animation.yaml` and `storyboard.yaml` of registered components with named checkpoints, renders the checkpoints with layout reports and frame-exact videos, and offers a review server, write-once revisions and typed feedback. It and the kit are two layers, and both are worth keeping: the kit is unconstrained and makes a data-driven clip from a simulation in an afternoon; manim8 is reproducible and reviewable, with checkpoints that are the study PDF's still by construction, where the kit needs a chosen frame.

The integration is a dependency, not a submodule: `pip install lecturekit[manim8]`, pinned to a tag until manim8's first release on PyPI. A project holds a manim8 workspace in `clips/` (`workspace.yaml`, `families/<family>/<clip>/`), one manim8 project per clip; `lk clips` renders them through the seam above and the deck names the clip like any other, `::: {.movie clip="fit_search"}`. The style comes from the bridge that `lk theme --manim8 VERSION` writes (THEMING.md); a restyle is a new style version and `lk clips` re-renders against it. Proposals that touch equations or sources need the lecturer's sign-off in manim8, which is the same rule as `FACTS.md`. Episode 10 of the tutorials shows a clip made from a brief entering a slide.

## Licence note

The kit's `nmnet`, `nmpix` and `nmfield` modules were written fresh for Manim Community after scenes in 3Blue1Brown's videos repository, used as storyboards only (decision of 1 November 2026); each clip's docstring names the scene it follows and `NOTICE.md` carries the entry. The kickoff's clip uses none of them.
