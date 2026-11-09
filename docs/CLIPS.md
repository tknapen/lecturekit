# Clips

A clip is a short animation that plays in the live deck and prints as a still in the study PDF. The clip shows the mechanism and nothing else; the slide supplies the claim. This page gives the rules a clip follows, the seam between a deck and whatever rendered the clip (`assets/clips/clips.json` and the `clip=` form of the movie block), what `lk clips` does, the Manim kit in brief, and manim8, the second producer.

## Rules

- Render at 1280 by 720 with a white background (the slide colour); the multiply blend handles paper slides. The kit sets this when it is imported; `lk clips --size WxH` or the environment variable `NM_CLIP_SIZE` changes it, and the frame stays 9 scene units high. A manim8 clip renders at its project's `output` in `animation.yaml` (`lk new --manim8` starts projects at 1280 by 720 and 30 fps); `--size` does not reach it, and `lk clips` warns when the two differ. Rendering on the paper colour directly is also fine for a clip that will only ever sit on a paper slide.
- No titles or captions in the clip: the slide carries the title, the speaker the words. A legend, tick labels and a marker inside the drawing are part of the mechanism and stay.
- Every clip has a static equivalent in the study PDF: the still that `lk clips` writes and `clip=` places, or a `.study-only` figure drawn from the same numbers (the kickoff's `bar-bold.tex` and its clip share one forward model).
- Clips play without browser controls. A click or the space bar pauses and resumes the clip; R replays it from the start; space does not advance the slide while a clip is shown. A clip starts when its slide appears and stops when the slide is left.
- Browsers cache clips by file name: a re-rendered clip that looks unchanged on screen needs a new file name.
- `aspect` is the clip's pixel ratio. The `clip=` form reads it from `clips.json`; the `src=` form takes `aspect="4:3"` or `"1:1"` for a clip in a column, or any `W:H` for a clip cropped to its content. A wrong aspect letterboxes the clip and wastes height.
- A clip on a key press: `::: {.fragment}` around `:::: {.live-only}` around the `.movie`, never the other way round. A sequence of clips is an `.r-stack` inside `.live-only`, each later clip in a `.fragment`; the step's clip starts when its fragment appears and the earlier one stops. Check: `lk review frags <live.html>` prints, per step, whether each clip is shown and playing, and flags a clip's fragment outside `.live-only`.
- Colours in a clip are tokens from the brand (`INK`, `BLUE`, `GAUSS`, `token('dn')`), never values, and the background is the brand's slide colour, so a restyle can re-render the clip in the new palette. It must: a rendered video is pixels and does not follow a restyle until `lk clips --mode dark` renders the dark preset's clips into `assets/clips/dark/` (below). This is the known limit of the one-instruction restyle (THEMING.md).

## The seam: clips.json and clip=

`assets/clips/clips.json` maps clip names to files and facts about them. `lk clips` writes it; a hand-written entry for a committed MP4 is valid too, as the kickoff's slide 1 could carry for its shipped `bar-bold.mp4`. A kit clip and a manim8 clip:

```json
{
  "bar-bold": {
    "video": "assets/clips/bar-bold.mp4",
    "still": "assets/clips/bar-bold.png",
    "width": 1280,
    "height": 720,
    "fps": 30.0,
    "duration": 20.0,
    "source": "anim/clip_bar_bold.py:BarBold",
    "revision": "a1b2c3d4e5f6",
    "producer": "kit"
  },
  "divisive_normalization": {
    "video": "assets/clips/divisive_normalization.mp4",
    "still": "assets/clips/divisive_normalization.rebalanced.png",
    "width": 1920,
    "height": 1080,
    "fps": 30.0,
    "duration": 18.0,
    "source": "clips/families/neuro/divisive_normalization",
    "revision": "working",
    "producer": "manim8",
    "job": {"id": "job_20261109T083620_428a09", "cache_key": "sha256:0211b9fc...", "registry_version": "0.5.0",
            "style": "lecturekit_paper@0.1.0"},
    "checkpoints": {
      "excitation_visible": "assets/clips/divisive_normalization.excitation_visible.png",
      "rebalanced": "assets/clips/divisive_normalization.rebalanced.png"
    }
  }
}
```

| Field | Meaning |
| --- | --- |
| `video` | the MP4, relative to the deck folder (`mp4` is accepted as an alias); for a manim8 clip, the full movie of the job, never a scene's section |
| `still` | the PNG the study PDF prints and the live deck shows as poster (`png` is accepted as an alias); for a manim8 clip, the latest checkpoint unless `lk clips --still CLIP=ID` names another |
| `width`, `height` | the pixel size of the video after cropping; the deck's `aspect` |
| `fps` | frames per second |
| `duration` | seconds; informative |
| `source` | where the clip comes from, relative to the deck: the scene file and class, or the manim8 project's folder |
| `revision` | what rendered this version: a hash of the scene source for a kit clip; for a manim8 clip the revision that was rendered, `working` or `rev_NNNN`; a stale clip is visible by it |
| `producer` | `kit`, `manim8`, or `external` for a file that was only indexed |
| `job` | manim8 only: the job's `id`, its `cache_key`, the component `registry_version` and the `style` it rendered under |
| `checkpoints` | manim8 only: every checkpoint of the job, by snapshot id, as a PNG copied beside the clip |

A value that is not known is left out of the entry, never written as `null`.

The deck names the clip:

```markdown
::: {.movie clip="bar-bold" height=4cm}
A one-line caption, small and muted under the clip; on the page it follows the still.
:::
```

The entry supplies the video, the still and the aspect, so the block needs no `.live-only` wrapper: the live deck gets a boxed autoplaying video with the still as poster, the study PDF gets the still at `height=` (default 4 cm) through `\lkimageh`, which never upscales. `still=` on the block overrides the entry's still: a path as before, or, for a manim8 clip, the id of one of its checkpoints (`still="pool_raised"`). A name that is not in the index and has no `src=` stops the build with "is not in assets/clips/clips.json (run lk clips)". The older `src=` form stays for a clip with a `.study-only` figure instead of a still (AUTHORING.md, Movies). Paths are relative to the deck folder, and `resources: [assets/**]` in `_quarto.yml` copies them into the build.

Names: `-` and `_` are the same in a clip name wherever a name is looked up, so `clip="bar_bold"` finds `bar-bold`, and `lk clips --only divisive-normalization` finds the manim8 project `divisive_normalization`. Kit clips keep their hyphenated names (`clip_bar_bold.py` gives `bar-bold`); manim8 projects are named with underscores, as manim8's ids must be. Two clips whose names differ only in a hyphen or an underscore are an error in `lk clips`, which renders nothing until one is renamed.

The dark preset has an index of its own: `lk clips --mode dark` writes `assets/clips/dark/clips.json` and the files beside it, and a dark build of the deck looks a clip up there first and falls back to `assets/clips/clips.json`, so a clip that has no dark rendering yet still plays.

The MP4s, the PNGs and both `clips.json` files are committed with the deck, so that a reader who clones the project, or a build where Manim is not installed, still has the clip. A changed `revision` is how a stale committed file is noticed.

## lk clips

```sh
lk clips [deck] [--only name ...] [--size 1280x720] [--crop] [--mode light|dark]
         [--still CLIP=ID ...] [--revision [CLIP=]REV ...] [--profile final] [--no-sync]
```

renders every scene under the deck's `anim/clip_*.py` and every manim8 project under `clips/families/` (found in the deck, else at the project root), and writes the index.

Kit scenes. Each file holds one or more Manim `Scene` classes on the kit (`from kit import *`); the clip's name is the file's stem after `clip_`, with underscores as hyphens (`clip_bar_bold.py` gives `bar-bold`), and a second scene in the same file appends its class name. `--only` takes clip names, in either spelling, or a scene's class (`bar-bold`, `bar_bold` and `BarBold` all name the kickoff's clip); a name that matches no clip is an error. The scene is rendered with Manim at 1280 by 720 on white (`--size 1920x1080` or `NM_CLIP_SIZE` for another size; the kit reads it), 30 frames per second, without a title, with `LECTUREKIT_BRAND` pointing at the deck's brand so the colours follow it. The video is copied to `assets/clips/<name>.mp4`; its last frame becomes the still `<name>.png`, unless the scene class sets `still = <seconds>` or `--still bar-bold=12.5` names another second. Manim's own output goes to `anim/media/`, which git ignores. Rendering takes a minute or two per clip; ffmpeg is found on the path or through `imageio-ffmpeg`.

manim8 projects. For each project with a `storyboard.yaml` (a project still without one is skipped), `lk clips`

1. builds the family's render environment when its `.venv` is missing (`scianim family env sync <family>`, once; `--no-sync` reports it instead);
2. generates the working copy's scene module (`scianim codegen <project>`);
3. renders it with `scianim render <project> --profile final --json`, adding `--style` for the preset (below) and `--revision` when `lk clips --revision rev_0002` asks for an approved revision instead of the working copy;
4. reads the manifest that `--json` prints, for a fresh job and a cache hit alike, and refuses a manifest `schema_version` it does not know;
5. copies the job's full movie (`result.videos[0]`) to `assets/clips/<name>.mp4` and every checkpoint PNG to `assets/clips/<name>.<snapshot_id>.png`, and writes the entry from the manifest: size, frame rate and duration from the movie, the revision, the job, the checkpoints, and the still.

The still is the checkpoint with the latest time, or the one `--still divisive_normalization=pool_raised` names (a number there is a second of the movie). A second run with nothing changed is a cache hit in manim8: nothing is rendered, and the entry is written again from the same job.

Both producers. `--crop` trims the video and the stills to the content's bounding box against the slide colour (plus a margin, to even sizes), for a clip in a column; for a manim8 clip the box holds the content of every checkpoint. `clips.json` records the resulting shape, which the deck uses as the clip's aspect. Manim and manim8 run with a fontconfig that adds the extension's bundled fonts (TeX Gyre Heros and Pagella, Roboto) to the system's, written to `_lecturekit/fonts.conf`, so a clip finds the deck's faces by name on any machine; a `FONTCONFIG_FILE` already set is left alone.

Failures. A clip that cannot be made is reported with its producer and a one-line reason (manim8's own message where it gave one; "Manim is not installed: pip install 'lecturekit[clips]'" when Manim is missing), the index is saved after every clip, the remaining clips are made, and `lk clips` exits 1 at the end with the list of failures.

Presets. `--mode dark` (or `LECTUREKIT_MODE=dark`) makes the dark preset's clips: kit scenes render with `LECTUREKIT_MODE=dark` and `LECTUREKIT_BRAND` set to the dark brand (the file the project's `_quarto-dark.yml` names, else `_brand-dark.yml`, else the dark side of `_brand.yml`), so `nmstyle` takes the dark slide colour as the background and the dark tokens as the colours; manim8 projects render with `--style lecturekit_dark@<newest version>`, the bridged dark style that `lk theme --manim8` wrote. The files and their own `clips.json` go to `assets/clips/dark/`. In the paper preset a manim8 project that selects the bridged paper style renders under its newest version; a project that selects another style keeps it. A bridged style changes colours and fonts, never timing, so one generated scene renders under both.

## The Manim kit, in brief

A deck's `anim/kit.py` is two lines (`lk new` writes it): `from lecturekit.manim import *` and `HERE` and `DATA`, the deck's `anim/` and `assets/data/`. Every clip starts with `from kit import *` and gets the house style (`nmstyle`: the bundled TeX Gyre fonts registered with Pango, the colours of the deck's `_brand.yml`, `label()`, `Frame` with `inv()` and `scale`, `normal_pdf`), networks (`nmnet`), pixel grids and convolutions (`nmpix`), two-dimensional flows (`nmfield`) and the population receptive field primitives (`nmprf`: `VisualField`, `HeightSurface`, `FeatureStack`, `TracePanel`, `Dial`, `Bars`, `clip_size`, the numpy fields and colour ramps). MANIM.md is the reference. Manim Community 0.22 needs Pillow below 11.3: `pip install lecturekit[clips]`.

The kickoff's clip, `anim/clip_bar_bold.py`, is the model: a docstring that says what the clip shows and in which stages, a numpy forward model shared with the static figure (`anim/bar_model.py`), the recorded run in `assets/data/s01.json` as the numbers, a `VisualField`, a `Frame` for the traces, `always_redraw` traces that draw up to a `ValueTracker`, and a schedule of events in simulated seconds.

## manim8

manim8 (SciAnim Studio) turns a brief in plain language or YAML into a validated `animation.yaml` and `storyboard.yaml` of registered components with named checkpoints, renders the checkpoints with layout reports and frame-exact videos, and offers a review server, write-once revisions and typed feedback. It and the kit are two layers, and both are worth keeping: the kit is unconstrained and makes a data-driven clip from a simulation in an afternoon; manim8 is reproducible and reviewable, with checkpoints that are the study PDF's still by construction, where the kit needs a chosen frame.

The integration is a dependency, not a submodule. `pip install "lecturekit[manim8]"` on Python 3.12 or later installs manim8 and its contracts from manim8's `v0.1.0a0` tag (INSTALL.md); manim8 builds each family's render environment, Manim included, with uv, which it brings along. lecturekit runs the `scianim` command and reads what it prints; it imports nothing of manim8.

A project's manim8 workspace is `clips/`, one manim8 project per clip under `clips/families/<family>/`. `lk new --manim8` makes it: `scianim workspace init clips`, the bridged styles of the project's presets in `clips/styles/` (THEMING.md), a family that defaults to the paper style, and a starter project, `first_clip`, at 1280 by 720 and 30 fps in that style, waiting for its storyboard. In an existing project, `lk new --manim8 .` adds the workspace and nothing else. `scianim skill install` gives the agent the manim8 skill that turns a brief into the project's specification and storyboard. `lk clips` renders the projects through the seam above, and the deck names the clip like any other, `::: {.movie clip="first_clip"}`.

What is committed: the specifications, storyboards, styles, each family's `uv.lock`, and the copies in `assets/clips/`. What is not: each project's `renders/` and `.scianim/` and each family's `.venv/`, which the scaffold's `.gitignore` and the one `scianim workspace init` writes both leave out. manim8 reads `clips/workspace.yaml`; lecturekit does not.

The style comes from the bridge that `lk theme --manim8 VERSION` writes and selects (THEMING.md); a restyle is a new style version, and the next `lk clips` renders against it. Proposals that touch equations or sources need the lecturer's sign-off in manim8, which is the same rule as `FACTS.md`. Episode 10 of the tutorials shows a clip made from a brief entering a slide.

## Licence note

The kit's `nmnet`, `nmpix` and `nmfield` modules were written fresh for Manim Community after scenes in 3Blue1Brown's videos repository, used as storyboards only (decision of 1 November 2026); each clip's docstring names the scene it follows and `NOTICE.md` carries the entry. The kickoff's clip uses none of them.
