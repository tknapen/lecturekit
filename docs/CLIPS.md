# Clips

A clip is a short animation that plays in the live deck and prints as a still in the study PDF. This page specifies the seam between a deck and whatever renders the clip: the `.movie` block in the source, the `assets/clips/clips.json` index, and what `lk clips` writes into it. Two renderers feed the seam: scenes on the Manim kit (`lecturekit.manim`, being extracted from the course project) and, from the second release, manim8 projects.

## The movie block

```markdown
::: {.movie clip="bar_bold" still="assets/clips/bar_bold.png" aspect=1.78 height=4.4cm}
A bar sweeps the visual field; the BOLD response of one voxel follows.
:::
```

| Attribute | Required | Meaning |
| --- | --- | --- |
| `clip` | yes | A clip name, resolved through `clips.json`, or a path with an extension (`.mp4`, `.webm`), used as is. `src` is an alias. |
| `still` | no | Path of the still. Default: the entry's `still`; for a path clip, a `.png` of the same name beside it, if it exists. |
| `aspect` | no | Width over height of the clip's box. Default: the entry's `width / height`. Without either, the box takes the video's size when it loads. |
| `height` | no | Maximum height, `4.4cm` or `352px`, at 80 px per cm. The study PDF uses 4.2cm when absent; the live deck sets no cap. |

The Div's content is the caption, set small and muted under the clip in both outputs. The filter rewrites the block and keeps none of its own classes: a fragment is a `.fragment` Div around it, inside `.live-only` (LAYOUT.md).

## clips.json

`assets/clips/clips.json` maps clip names to files and facts about them. `lk clips` writes it; a hand-written entry is valid too.

```json
{
  "bar_bold": {
    "video": "assets/clips/bar_bold.mp4",
    "still": "assets/clips/bar_bold.png",
    "width": 1920,
    "height": 1080,
    "duration": 12.0,
    "revision": "a1b2c3d",
    "source": "anim/clip_bar_bold.py"
  }
}
```

| Field | Meaning |
| --- | --- |
| `video` | Path of the MP4 (or WebM), relative to the deck folder. `mp4` is accepted as an alias. |
| `still` | Path of the PNG the study PDF prints and the live deck shows as poster. `png` is accepted as an alias. |
| `width`, `height` | Pixel size of the video after cropping; the default `aspect`. |
| `duration` | Seconds. Informative; read by the review tools. |
| `revision` | What rendered this version: a hash of the scene source for a kit clip, the render manifest's revision for a manim8 clip. A stale clip is visible by it. |
| `source` | Where the clip comes from: the scene file, the manim8 project, or a note such as `synthetic stand-in`. |

Paths are relative to the deck folder, and `resources: [assets/**]` in `_quarto.yml` copies them into the build (AUTHORING.md).

## lk clips: kit scenes

`lk clips [dir]` renders every scene under the deck's `anim/clip_*.py`. Each file holds one Manim scene class on the kit (`from lecturekit.manim import *`); its docstring says what it shows and, for a scene after one of 3Blue1Brown's, names the scene it follows (see the licence note). The scene is rendered at 1920 by 1080, cropped to its content, and written as `assets/clips/<name>.mp4`; the last frame becomes `assets/clips/<name>.png`, unless the scene names a `still` checkpoint, in which case that frame is used. The entry in `clips.json` gets the cropped size, the duration and the revision. Colours in a scene are tokens (`lecturekit.tokens`), so a restyle re-renders the clip in the new palette: `lk clips` after `lk theme`.

Rendering takes a minute or two per clip. The kit is being extracted from the course project and is not in this repository yet; until it is, a deck can point `clip=` at a committed MP4 and PNG, as `examples/features` does with a synthetic stand-in.

## lk clips: manim8 projects (second release)

A project may hold a manim8 workspace in `clips/` (`workspace.yaml`, `families/<family>/<name>/`), one manim8 project per clip. For each project listed there, `lk clips` runs `scianim render --profile final`, copies the final MP4 and the named checkpoint's PNG into `assets/clips/`, and writes the entry from the render manifest: dimensions, duration, the revision hash, and `source` pointing at the project. The checkpoint is the study PDF's static equivalent, which the method requires and which manim8 produces by construction. Which checkpoint becomes the still is decided where the project is listed in `clips/`, not in the deck; the deck's `still=` stays a file path override. The deck names the clip like any other: `::: {.movie clip="fit_search"}`. The style comes from the bridge that `lk theme --manim8` writes (THEMING.md). manim8 is an optional extra (`pip install lecturekit[manim8]`), pinned to a tag until its first release on PyPI.

## Live behaviour

The filter emits `<video class="lk-clip" muted playsinline preload="auto" data-autoplay>` with the still as poster, inside a box with the aspect and the height cap. Reveal starts the clip when its slide appears; `movie.js` starts it when its fragment appears and pauses it when the fragment is hidden. A click on the clip pauses and resumes it. R replays the clips of the current slide from the start, skipping those in fragments not yet shown. Controls are hidden and sound is off. A clip that cannot be resolved renders as a dashed placeholder reading `clip missing: <name>`.

## Study PDF

The still is placed with `\lkfigureh{<height>}{<still>}`: as wide as the line allows, at most the given height, never upscaled; the caption follows. A clip without a still becomes `\lkplaceholder{<height>}{clip: <name>}`, and the build still succeeds. Choose the still for the reader: the end state of the animation, or the checkpoint that carries the point.

## Keep the fallback files committed

The MP4 and PNG of every clip are committed in `assets/clips/` together with `clips.json`. The continuous build may re-render them, but a reader who clones the project, or the Pages site when the renderer is unavailable, must still see the clip. A changed `revision` is how a stale committed file is noticed.

## Licence note

The kit's `nmnet`, `nmpix` and `nmfield` modules were written fresh for Manim Community after scenes in 3Blue1Brown's videos repository, used as storyboards. The project's record says those storyboards are under CC BY-NC-SA 4.0; the repository's current terms are to be verified before the modules ship. Each clip's docstring names the scene it follows, and `NOTICE.md` carries the entry. If the terms turn out restrictive, the three modules go in a separate folder under their own licence or stay out of the first release. The bar-and-BOLD clip uses none of them.
