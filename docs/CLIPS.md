# Clips

A clip is a short animation that plays in the live deck and prints as a still in the study PDF. The clip shows the mechanism and nothing else; the slide supplies the claim. This page gives the rules a clip follows, the seam between a deck and whatever rendered the clip (`assets/clips/clips.json` and the `clip=` form of the movie block), what `lk clips` does, a clip in parts (the stops where a deck may hold a clip, from each producer, and what the deck does with them), `lk clips adopt` for an MP4 made elsewhere, the Manim kit in brief, and manim8, the second producer.

## Rules

- Render at 1280 by 720 with a white background (the slide colour); the multiply blend handles paper slides. The kit sets this when it is imported; `lk clips --size WxH` or the environment variable `NM_CLIP_SIZE` changes it, and the frame stays 9 scene units high. A manim8 clip renders at its project's `output` in `animation.yaml` (`lk new --manim8` starts projects at 1280 by 720 and 30 fps); `--size` does not reach it, and `lk clips` warns when a manim8 clip is not at the deck's size (`--size` when given, else 1280 by 720) or not at 30 fps. Rendering on the paper colour directly is also fine for a clip that will only ever sit on a paper slide.
- No titles or captions in the clip: the slide carries the title, the speaker the words. A legend, tick labels and a marker inside the drawing are part of the mechanism and stay.
- Every clip has a static equivalent in the study PDF: the still that `lk clips` writes and `clip=` places, or a `.study-only` figure drawn from the same numbers (the kickoff's `bar-bold.tex` and its clip share one forward model).
- Clips play without browser controls. A click or the space bar pauses and resumes the clip; R replays it from the start; space does not advance the slide while a clip is shown. A clip starts when its slide appears and stops when the slide is left. A clip in parts (below) takes the same keys with a meaning of its own: at a hold, Space plays the next part, and R replays the part that ends there.
- Browsers cache clips by file name. Every entry `lk clips` writes carries the `sha256` of the delivered video, which changes with every render, so that a deck can version the clip's URL by it (`?v=` and its first eight hex digits); a clip named by `src=` alone has no such version, and a re-rendered one that looks unchanged on screen needs a new file name.
- `aspect` is the clip's pixel ratio. The `clip=` form reads it from `clips.json`; the `src=` form takes `aspect="4:3"` or `"1:1"` for a clip in a column, or any `W:H` for a clip cropped to its content. A wrong aspect letterboxes the clip and wastes height.
- A clip on a key press: `::: {.fragment}` around `:::: {.live-only}` around the `.movie`, never the other way round. A sequence of clips is an `.r-stack` inside `.live-only`, each later clip in a `.fragment`; the step's clip starts when its fragment appears and the earlier one stops. Check: `lk review frags <live.html>` prints, per step, whether each clip is shown and playing, and flags the reverse order (a `.fragment` inside the clip's `.live-only` box) and a hidden clip that plays.
- Colours in a clip are tokens from the brand (`INK`, `BLUE`, `GAUSS`, `token('dn')`), never values, and the background is the brand's slide colour, so a restyle can re-render the clip in the new palette. It must: a rendered video is pixels and does not follow a restyle until `lk clips --mode dark` renders the dark preset's clips into `assets/clips/dark/` (below). This is the known limit of the one-instruction restyle (THEMING.md).

## The seam: clips.json and clip=

`assets/clips/clips.json` maps clip names to files and facts about them. `lk clips` writes it, and `lk clips adopt` adds an entry for an MP4 made elsewhere (below); an entry written by hand for a committed MP4 is valid too. Every entry `lk clips` writes is `format: 2`: besides the files, it says how many frames the video has, at what times, and where a deck may hold it. A kit clip with two checkpoints and a manim8 clip:

```json
{
  "bar-bold": {
    "format": 2,
    "video": "assets/clips/bar-bold.mp4",
    "sha256": "3f2a9c1e...",
    "still": "assets/clips/bar-bold.png",
    "poster": "assets/clips/bar-bold.f0000.png",
    "width": 1280,
    "height": 720,
    "fps": 30.0,
    "frames": 600,
    "duration": 20.0,
    "stops": [
      {"id": "first_sweep", "frame": 204, "pts": 6.8, "label": "rightward sweep",
       "still": "assets/clips/bar-bold.f0204.png", "rest_before": 9, "rest_after": 9, "frozen": []},
      {"id": "second_sweep", "frame": 402, "pts": 13.4, "label": "second sweep",
       "still": "assets/clips/bar-bold.f0402.png", "rest_before": 9, "rest_after": 8, "frozen": []}
    ],
    "end": {"frame": 599, "pts": 19.966667, "still": "assets/clips/bar-bold.f0599.png"},
    "checkpoints": {"first_sweep": "assets/clips/bar-bold.f0204.png",
                    "second_sweep": "assets/clips/bar-bold.f0402.png"},
    "source": "anim/clip_bar_bold.py:BarBold",
    "revision": "a1b2c3d4e5f6",
    "producer": "kit"
  },
  "divisive_normalization": {
    "format": 2,
    "video": "assets/clips/divisive_normalization.mp4",
    "sha256": "8579834e...",
    "still": "assets/clips/divisive_normalization.rebalanced.png",
    "poster": "assets/clips/divisive_normalization.f0000.png",
    "width": 1920,
    "height": 1080,
    "fps": 30.0,
    "frames": 540,
    "duration": 18.0,
    "stops": [
      {"id": "pool_raised", "frame": 390, "pts": 13.0, "label": "pool raised",
       "notes": "After the first sweep the curve is compressed to a fifth of its slope ...",
       "still": "assets/clips/divisive_normalization.f0390.png", "rest_before": 15, "rest_after": 15,
       "frozen": []}
    ],
    "end": {"frame": 539, "pts": 17.966667, "still": "assets/clips/divisive_normalization.f0539.png"},
    "source": "clips/families/neuro/divisive_normalization",
    "revision": "working",
    "producer": "manim8",
    "job": {"id": "job_20261109T083620_428a09", "cache_key": "sha256:0211b9fc...", "registry_version": "0.5.0",
            "style": "lecturekit_paper@0.1.0"},
    "checkpoints": {
      "excitation_visible": "assets/clips/divisive_normalization.excitation_visible.png",
      "pool_raised": "assets/clips/divisive_normalization.pool_raised.png",
      "rebalanced": "assets/clips/divisive_normalization.rebalanced.png"
    }
  }
}
```

| Field | Meaning |
| --- | --- |
| `format` | `2` for every entry `lk clips` writes: the entry carries `frames`, `sha256`, `poster`, `stops` and `end`. An entry without it (an older lecturekit's, or one written by hand) keeps the meaning of the fields below that it has |
| `video` | the MP4, relative to the deck folder (`mp4` is accepted as an alias); for a manim8 clip, the full movie of the job, never a scene's section. `lk clips` delivers it with its index first (`+faststart`, by stream copy), so a browser can seek in it before the whole file has arrived |
| `sha256` | of the delivered video; it changes with every render |
| `still` | the PNG the study PDF prints for a clip shown whole (`png` is accepted as an alias): the last frame of a kit or adopted clip unless the scene names another, for a manim8 clip the latest checkpoint unless `lk clips --still CLIP=ID` names another |
| `poster` | frame 0 as a PNG: what a clip in parts shows before it starts |
| `width`, `height` | the pixel size of the video after cropping; the deck's `aspect` |
| `fps` | frames per second of the delivered video, as decoding it gives |
| `frames` | the number of frames, counted by decoding the delivered video (never the container's figure) |
| `duration` | seconds; informative |
| `stops` | candidate stops, in time order: frames where a deck may hold the clip until the presenter's next key (below). The deck chooses among them; an empty list says the clip has none |
| `stops[].id` | the stop's name, an exact slug (`[a-z][a-z0-9_]*`), never `start`, `end` or `all` |
| `stops[].frame` | the 0-based frame the hold shows; authoritative |
| `stops[].pts` | that frame's presentation time in seconds, as ffprobe reads it from the delivered video |
| `stops[].label` | plain text of 1 to 40 characters for the study strip and the speaker; the id with spaces by default |
| `stops[].notes` | what the producer says the frame shows (manim8: the snapshot's description); left out when there is none |
| `stops[].still` | that exact frame as a PNG, `<name>.fNNNN.png`, extracted by its number (`select=eq(n,K)`) from the delivered video |
| `stops[].rest_before`, `rest_after` | frames of unchanged picture just before and just after the stop: no grey level differs by more than 6 of 255 with the video scaled to 160 pixels wide (a keyframe in a still rest is coded afresh and differs by up to 5). They are measured on the producer's frames, before a crop or a scale re-encodes them |
| `stops[].frozen` | manim8 only: the ids of the camera orbits that keep turning through the stop; empty elsewhere |
| `end` | the last frame: its `frame`, `pts` and `still` |
| `source` | where the clip comes from, relative to the deck: the scene file and class, the manim8 project's folder, or the adopted file (its name alone when it lies outside the deck) |
| `revision` | what rendered this version: a hash of the scene source for a kit clip, of the file for an adopted one; for a manim8 clip the revision that was rendered, `working` or `rev_NNNN`; a stale clip is visible by it |
| `producer` | `kit`, `manim8`, or `external` for an adopted or indexed file |
| `job` | manim8 only: the job's `id`, its `cache_key`, the component `registry_version` and the `style` it rendered under |
| `checkpoints` | the PNGs `still=` can name by id: for a manim8 clip every checkpoint of the job, copied beside the clip; for a kit or adopted clip each stop's still |

A value that is not known is left out of the entry, never written as `null`.

The deck names the clip:

```markdown
::: {.movie clip="bar-bold" height=4cm}
A one-line caption, small and muted under the clip; on the page it follows the still.
:::
```

The entry supplies the video, the still and the aspect, so the block needs no `.live-only` wrapper: the live deck gets a boxed autoplaying video with the still as poster, the study PDF gets the still at `height=` (default 4 cm) through `\lkimageh`, which never upscales. `still=` on the block overrides the entry's still: a path as before, or the id of one of the entry's `checkpoints` (`still="pool_raised"`). A name that is not in the index and has no `src=` stops the build with "is not in assets/clips/clips.json (run lk clips)". The older `src=` form stays for a clip with a `.study-only` figure instead of a still (AUTHORING.md, Movies). Paths are relative to the deck folder, and `resources: [assets/**]` in `_quarto.yml` copies them into the build.

Names: `-` and `_` are the same in a clip name wherever a name is looked up, so `clip="bar_bold"` finds `bar-bold`, and `lk clips --only divisive-normalization` finds the manim8 project `divisive_normalization`. Kit clips keep their hyphenated names (`clip_bar_bold.py` gives `bar-bold`); manim8 projects are named with underscores, as manim8's ids must be. Two clips whose names differ only in a hyphen or an underscore are an error in `lk clips`, which renders nothing until one is renamed.

The dark preset has an index of its own: `lk clips --mode dark` writes `assets/clips/dark/clips.json` and the files beside it, and a dark build of the deck looks a clip up there first and falls back to `assets/clips/clips.json`, so a clip that has no dark rendering yet still plays. The `src=` form follows the same rule: in a dark build `src="assets/clips/x.mp4"` plays `assets/clips/dark/x.mp4` when that file exists (and takes its still beside it). A dark build that still plays a clip drawn for the paper preset says so: `lk build` lists the movie and slide as a warning, and `lk build --strict` fails on it, as the engine's continuous build does for the example decks.

The MP4s, the PNGs and both `clips.json` files are committed with the deck, so that a reader who clones the project, or a build where Manim is not installed, still has the clip. A changed `revision` is how a stale committed file is noticed.

## lk clips

```sh
lk clips [deck] [--only name ...] [--size 1280x720] [--crop] [--mode light|dark]
         [--still CLIP=ID ...] [--revision [CLIP=]REV ...] [--profile final] [--no-sync] [--no-cache]
```

renders every scene under the deck's `anim/clip_*.py` and every manim8 project under `clips/families/` (found in the deck, else at the project root), and writes the index. `lk clips adopt` brings in an MP4 made elsewhere (below).

Kit scenes. Each file holds one or more Manim `Scene` classes on the kit (`from kit import *`); the clip's name is the file's stem after `clip_`, with underscores as hyphens (`clip_bar_bold.py` gives `bar-bold`), and a second scene in the same file appends its class name. `--only` takes clip names, in either spelling, or a scene's class (`bar-bold`, `bar_bold` and `BarBold` all name the kickoff's clip), and is repeatable (`--only a b` and `--only a --only b` name both); a name that matches no clip is an error. The scene is rendered with Manim at 1280 by 720 on white (`--size 1920x1080` or `NM_CLIP_SIZE` for another size; the kit reads it), 30 frames per second, without a title, with `LECTUREKIT_BRAND` pointing at the deck's brand so the colours follow it. Manim runs with `--save_sections`, so that each `checkpoint()` in the scene (MANIM.md) opens a section whose first frame is a stop. The video is copied to `assets/clips/<name>.mp4` with its index first; its last frame becomes the still `<name>.png`, unless the scene class sets `still = <seconds>` or `still = "<checkpoint id>"`, or `--still bar-bold=12.5` (or `=first_sweep`) names another. A scene without `checkpoint()` calls gives an entry with no stops. Manim's own output goes to `anim/media/`, which git ignores. Rendering takes a minute or two per clip; ffmpeg is found on the path or through `imageio-ffmpeg`.

manim8 projects. For each project with a `storyboard.yaml` (a project still without one is skipped), `lk clips`

1. builds the family's render environment when its `.venv` is missing (`scianim family env sync <family>`, once; `--no-sync` reports it instead);
2. generates the working copy's scene module (`scianim codegen <project>`);
3. renders it with `scianim render <project> --profile final --json`, adding `--style` for the preset (below) and `--revision` when `lk clips --revision rev_0002` asks for an approved revision instead of the working copy;
4. reads the manifest that `--json` prints, for a fresh job and a cache hit alike, and refuses a manifest `schema_version` it does not know;
5. prints the manifest's warnings (`result.warnings`: a substituted font, a fidelity note) with the clip's name, and warns when the movie is not at the deck's size or 30 fps (Rules, above);
6. copies the job's full movie (`result.videos[0]`) to `assets/clips/<name>.mp4`, with its index first, and every checkpoint PNG to `assets/clips/<name>.<snapshot_id>.png`, and writes the entry from the manifest and the movie: size and duration from the manifest, frames and frame rate from decoding the movie, the revision, the job, the checkpoints, the still, and the stops of `result.stops` (below).

The still is the checkpoint with the latest time, or the one `--still divisive_normalization=pool_raised` names for that run (a number there is a second of the movie); a choice that should last belongs on the movie block, `still="pool_raised"`. A second run with nothing changed is a cache hit in manim8: nothing is rendered, and the entry is written again from the same job; `--no-cache` makes manim8 render the job anyway (the continuous integration does, so that a render is tested), and the entry then names the new job.

Every producer. `--crop` trims the video and the stills to the content's bounding box against the slide colour (plus a margin, to even sizes), for a clip in a column; for a kit clip the box holds the content of the first and last frames, the stops and the still, for a manim8 clip the content of every checkpoint. `clips.json` records the resulting shape, which the deck uses as the clip's aspect. A crop re-encodes the video, with a keyframe forced at every stop, and `lk clips` checks that the frame count did not change; without a crop the video is copied stream for stream, and its frames and keyframes are the producer's. Under `lk clips`, Manim and manim8 run with a fontconfig that adds the extension's bundled fonts (TeX Gyre Heros and Pagella, Roboto) to the system's, written to `_lecturekit/fonts.conf`, so a clip that `lk clips` renders finds the deck's faces by name on any machine; a `FONTCONFIG_FILE` already set is left alone. manim8 itself registers no fonts. A job rendered outside `lk clips` (a `scianim render` in the workspace) on a machine without the faces falls back to another family and says so in its manifest's warnings; manim8's cache keys follow the font families its environment finds (manim8's ADR-044), so that job is not a cache hit for `lk clips`. With a manim8 whose cache key ignores fonts it would be, and `lk clips` then renders it once more, with the fonts (once: the new job is the one the index records), when a warning says a face was replaced by one the extension does not bundle; with `FONTCONFIG_FILE` set it only prints the warning. To preview in the workspace with the deck's faces, run `scianim` with `FONTCONFIG_FILE=<deck>/_lecturekit/fonts.conf` (written by the first `lk clips`).

Failures. A clip that cannot be made is reported with its producer and a one-line reason (manim8's own message where it gave one, with its hint when its last line only says that a command exited; "Manim is not installed: pip install 'lecturekit[clips]'" when Manim is missing), the index is saved after every clip, the remaining clips are made, and `lk clips` exits 1 at the end with the list of failures. A clip's files are made in a hidden staging folder inside the preset's clips folder and moved in together once all of them exist, and an unknown `--still` is refused before anything is copied, so a clip that fails leaves its files and its entry as they were.

Presets. `--mode dark` (or `LECTUREKIT_MODE=dark`) makes the dark preset's clips: kit scenes render with `LECTUREKIT_MODE=dark` and `LECTUREKIT_BRAND` set to the dark brand (the file the project's `_quarto-dark.yml` names, else `_brand-dark.yml`, else the dark side of `_brand.yml`), so `nmstyle` takes the dark slide colour as the background and the dark tokens as the colours; manim8 projects render with `--style lecturekit_dark@<newest version>`, the bridged dark style that `lk theme --manim8` wrote. The files and their own `clips.json` go to `assets/clips/dark/`. In the paper preset a manim8 project that selects the bridged paper style renders under its newest version; a project that selects another style keeps it. A bridged style changes colours and fonts, never timing, so one generated scene renders under both.

## A clip in parts

A clip in parts is one video that the live deck holds at chosen frames, each part started by the presenter's next key; the study PDF prints the holds. The producer marks the frames where a deck may hold the clip, its stops; `clips.json` lists them as candidates, with a still of each and the rest around it; the deck chooses which to hold. The clip stays one movie: nothing is cut, and a hold is exact because it is a frame number, not a time.

### The producer side: stops

Each producer has one way to name the candidates:

- a kit scene calls `checkpoint(self, "first_sweep", label="rightward sweep", rest=0.6)` where the clip may hold (MANIM.md). It waits half the rest, opens a Manim section of type `lecturekit.checkpoint`, and waits the other half; the stop is the section's first frame, the sum of the frames of the sections before it in Manim's sections index. `lk clips` checks that the sections add up to the movie's decoded frames and that each checkpoint section's first frame is the movie's frame there, and fails the clip otherwise, as it does for a checkpoint with no frames after it (two checkpoints with nothing between them, or one at the end of the scene) and for one at the first frame;
- a manim8 snapshot marked `stop: true`, with its `label` and, for a camera orbit that may turn through it, `stop_through` (manim8's ADR-045). manim8 validates the stop and lists it in the manifest's `result.stops` with its frame, its time and its rests. `lk clips` cross-checks each one: its frame must be its time on the movie's frame grid, and its still must be manim8's checkpoint picture of that frame (a mean difference of at most 1 of 255), or the clip fails; a stop where no play starts, or whose rest holds a play that moves, is a warning, which a draft render can give. A manifest without `result.stops` gives no candidates;
- an adopted MP4 names its stops in seconds, `lk clips adopt sweep.mp4 --name sweep --stops 4.0 8.0` (below), each snapped to the nearest frame.

The rest before a stop is what hides the live deck's early pause: it pauses a frame or two before the stop, and up to 0.3 s before it in a browser without `requestVideoFrameCallback`, then seeks to the stop's frame. `lk clips` measures both rests on the pixels, whatever the producer says, and warns about a stop with fewer than three frames of unchanged picture before it, which a deck refuses; 0.3 s before the stop (9 frames at 30 fps, `checkpoint(..., rest=0.6)`) is the usual amount. A stop that is not a keyframe is a warning, not an error: the hold is exact, and only the seek to it is slower. Every stop sits strictly between the first and the last frame, on a frame of its own; two stops closer than 0.5 s are a warning.

A barcode clip, whose every frame shows its own number, has no rest at any stop: it serves to check that the stills are the frames they name, not as a clip in parts.

### The deck side: stops=

```markdown
## A clip in parts {role=example time=1.5}

::: {.movie clip="bar_steps" stops="left centre right"}
The caption, under the clip and on the study page.

:::: {.stop ref="left"}
Ask: the bar rests left of centre. Where does it stop next?
::::
:::
```

`stops=` names candidates of the entry, in time order (or `all`); `start=key` opens the slide on frame 0 instead of playing part 1 at once; a `.stop` block holds the speaker notes of one hold (`start`, a stop's id or `end`); `study=` chooses the study page: a strip of the holds after each part (the default), `final`, or a list of holds. AUTHORING.md has the whole dialect and the checks that stop the build; POLICY.md the rule (a clip in parts is a reveal, with a prompt at each hold before the last).

What the live deck does. The filter writes the video without Reveal's autoplay, a still of every boundary (frame 0, each chosen stop, the last frame) in the same box, and one empty fragment per key. The runtime makes the video agree with the number of fragments shown: Right plays the next part and holds on its last frame; a key pressed while a part plays lets it play on to the next stop; Left holds the previous stop at once and never plays backwards; entering the slide backwards, by a jump or from a URL holds that step's frame at once. To hold, it pauses the video a frame or two before the stop, seeks to the middle of the stop's frame, and shows that frame's still over the video while it holds, so the room sees exactly the frame `clips.json` names, whatever the browser has painted. Only the main window loads the video; the speaker view's previews show the stills. The study PDF prints the strip (`\lkstrip`, LAYOUT.md).

Check: `lk review frags <live.html>` walks each clip in parts with real keys and reports, per step, the frame expected, the frame shown, where the pause landed and the time from key to hold, then a backward entry and a jump; it exits 1 when a hold is off its frame.

### The feature deck: one clip in parts from each producer

| Slide | Clip | Producer | How its stops are made |
| --- | --- | --- | --- |
| 11 A clip in parts | `bar_steps` | an MP4 made elsewhere | `make_clips.py` draws a bar that rests at three places, 0.6 s still on each side, and calls `adopt` with `left=1.4 centre=3.2 right=5.0` |
| 12 A manim8 clip in parts | `tuning_sweep` | manim8 | `stop: true` on the snapshots `gain_low` and `gain_high` of `clips/families/features/tuning_sweep/storyboard.yaml`; `lk clips . --only tuning_sweep` |
| 13 A kit clip in parts | `gauss-parts` | a kit scene | `checkpoint(self, "narrowed", label="half the width", rest=0.6)` in `anim/clip_gauss_parts.py`; `lk clips . --only gauss-parts`; `start=key` on the slide |

## lk clips adopt

```sh
lk clips adopt <mp4> --name NAME [--stops S ...] [--labels L ...] [--mode light|dark] [--crop] [--size WxH] [--deck DIR]
```

brings an MP4 made elsewhere into the deck (the current folder, or `--deck`): it copies the file to `assets/clips/<NAME>.mp4` (`assets/clips/dark/` with `--mode dark`) with its index first, by stream copy, writes the poster, a still for each stop, the end still and the study still `<NAME>.png` (the last frame), and adds the format 2 entry to the preset's `clips.json`. A stop is a second of the video, or `ID=SECONDS` to name it; a bare second gets the id `stop_1`, `stop_2` and so on by its position, and `--labels` gives one label per stop in the same order. `--crop` and `--size 1280x720` re-encode the video as H.264, with a keyframe forced at every stop and the frame count checked. A stop that no deck could hold (at the first or last frame, after the end, two on one frame, an id that is not a slug) is refused before anything is copied, as is a name that one of the deck's kit scenes or manim8 projects renders. Adopting the same name again replaces the entry and its stills. The older `lecturekit.clips.index_existing`, which lists the MP4s already in the clips folder without copying or measuring them, remains for its callers; it writes entries without `format`.

## The Manim kit, in brief

A deck's `anim/kit.py` is two lines (`lk new` writes it): `from lecturekit.manim import *` and `HERE` and `DATA`, the deck's `anim/` and `assets/data/`. Every clip starts with `from kit import *` and gets the house style (`nmstyle`: the bundled TeX Gyre fonts registered with Pango, the colours of the deck's `_brand.yml`, `label()`, `Frame` with `inv()` and `scale`, `normal_pdf`), networks (`nmnet`), pixel grids and convolutions (`nmpix`), two-dimensional flows (`nmfield`), the population receptive field primitives (`nmprf`: `VisualField`, `HeightSurface`, `FeatureStack`, `TracePanel`, `Dial`, `Bars`, `clip_size`, the numpy fields and colour ramps) and `checkpoint()`, the frames where a deck may hold the clip (`nmcheckpoint`). MANIM.md is the reference. Manim Community 0.22 needs Pillow below 11.3: `pip install lecturekit[clips]`.

The kickoff's clip, `anim/clip_bar_bold.py`, is the model: a docstring that says what the clip shows and in which stages, a numpy forward model shared with the static figure (`anim/bar_model.py`), the recorded run in `assets/data/s01.json` as the numbers, a `VisualField`, a `Frame` for the traces, `always_redraw` traces that draw up to a `ValueTracker`, and a schedule of events in simulated seconds.

## manim8

manim8 (SciAnim Studio) turns a brief in plain language or YAML into a validated `animation.yaml` and `storyboard.yaml` of registered components with named checkpoints, renders the checkpoints with layout reports and frame-exact videos, and offers a review server, write-once revisions and typed feedback. It and the kit are two layers, and both are worth keeping: the kit is unconstrained and makes a data-driven clip from a simulation in an afternoon; manim8 is reproducible and reviewable, with checkpoints that are the study PDF's still by construction, where the kit needs a chosen frame.

The integration is a dependency, not a submodule. lecturekit's `manim8` extra, on Python 3.12 or later, installs manim8 and its contracts from the manim8 commit that INSTALL.md names (the release 0.1.0a0 with stops); manim8 builds each family's render environment, Manim included, with uv, which it brings along. lecturekit runs the `scianim` command and reads what it prints; it imports nothing of manim8.

A project's manim8 workspace is `clips/`, one manim8 project per clip under `clips/families/<family>/`. `lk new --manim8` makes it: `scianim workspace init clips`, the bridged styles of the project's presets in `clips/styles/` (THEMING.md), a family that defaults to the paper style, and a starter project, `first_clip`, at 1280 by 720 and 30 fps in that style, waiting for its storyboard. In an existing project, `lk new --manim8 .` adds the workspace and nothing else. A family made by hand takes the paper style with `scianim family init <family> --style lecturekit_paper@0.1.0`; without `--style`, manim8 pins its own house style, a near-black page, and `lk theme --manim8` would select the paper style in it afterwards. `scianim skill install` gives the agent the manim8 skill that turns a brief into the project's specification and storyboard. `lk clips` renders the projects through the seam above, and the deck names the clip like any other, `::: {.movie clip="first_clip"}`.

What is committed: the specifications, storyboards, styles, each family's `uv.lock`, and the copies in `assets/clips/`. What is not: each project's `renders/` and `.scianim/` and each family's `.venv/`, which the scaffold's `.gitignore` and the one `scianim workspace init` writes both leave out. manim8 reads `clips/workspace.yaml`; lecturekit does not.

The style comes from the bridge that `lk theme --manim8 VERSION` writes and selects (THEMING.md); a restyle is a new style version, and the next `lk clips` renders against it. Proposals that touch equations or sources need the lecturer's sign-off in manim8, which is the same rule as `FACTS.md`. Episode 10 of the tutorials shows a clip made from a brief entering a slide.

## Licence note

The kit's `nmnet`, `nmpix` and `nmfield` modules were written fresh for Manim Community after scenes in 3Blue1Brown's videos repository, used as storyboards only (decision of 1 November 2026); each clip's docstring names the scene it follows and `NOTICE.md` carries the entry. The kickoff's clip uses none of them.
