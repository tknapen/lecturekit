# Episode 11: A clip on key presses

Length: 8 minutes. Runs on `examples/features`. Needs lecturekit 0.4.0; the manim8 half needs manim8 through
lecturekit's `manim8` extra, on Python 3.12 or later (docs/INSTALL.md).

## Goal

One clip, presented in parts: the lecturer marks where it may stop in the storyboard, renders it, writes the slide
that holds it at those stops, and presents it, each part started by a key and held exactly on the frame where it
ends; the study PDF prints the holds as a strip.

## What the viewer sees

The feature deck's manim8 clip, `tuning_sweep`: a toy tuning curve whose gain doubles, then whose width doubles. The
lecturer wants the room to predict each change before it happens, so the clip should hold before the sweep of the
gain and after it.

1. The storyboard. In `clips/families/features/tuning_sweep/storyboard.yaml` the lecturer adds `stop: true` and a
   short `label` to the two snapshots, `gain_low` and `gain_high`. `scianim validate` refuses both: the reveal of
   the curve and the sweep of the gain run into them, and a stop needs 0.3 s with nothing moving before it, because
   the player may pause that early. The fix is a timing change, and the lecturer makes it: the sweep starts at 1.3 s
   instead of 0.9 s and lasts 0.7 s instead of 1.3 s, and `gain_low` moves from 0.88 s to 1.2 s. Validation passes;
   `scianim timing` lists the three parts.
2. The render. `lk clips . --only tuning_sweep` renders the clip; the manifest's `result.stops` gives each stop's
   frame (36 and 69) and rest, and `clips.json` gets a format 2 entry: the stops as candidates, a still of exactly
   each frame, the rest measured on the pixels. `--mode dark` does the same for the dark preset.
3. The slide. A movie block with `stops="gain_low gain_high"`, a caption, and a `.stop` block with the prompt for
   the first hold. `lk build . --strict` prints the clip's parts and prompts in the timing report.
4. Presenting. The slide appears and part 1 plays: the curve is drawn and holds at gain 1. The prompt is in the
   speaker notes, first. Right: the gain doubles, and the clip holds. A key pressed while a part plays lets it play
   on to the next stop. Left holds the previous stop at once. Leaving the slide and coming back holds the last
   frame without playing. R replays the part that ends at the hold.
5. The check and the PDF. `lk review frags` walks the slide with real keys and prints, per step, the frame
   expected and the frame shown. The study PDF's page shows three panels: gain 1, gain 2 and the end.

The same slide works for the other two producers, which the deck's slides 11 and 13 show: an MP4 made elsewhere,
brought in with `lk clips adopt bar_steps.mp4 --name bar_steps --stops left=1.4 centre=3.2 right=5.0`, and a kit
scene with `checkpoint(self, "narrowed", label="half the width", rest=0.6)` between two animations.

## Commands and prompts

The prompt that starts it:

```text
On the tuning_sweep slide I want the room to predict each change before it plays. Make gain_low and gain_high
stops in the storyboard, labelled "gain 1" and "gain 2", render the clip in both presets, and hold the slide at
both stops with my prompt at the first: "Ask: the gain doubles next. Where does the peak go, and does the curve
widen?"
```

The storyboard, after the fix:

```yaml
    actions:
      - id: raise_gain
        kind: vary_parameter
        target: gain_curve
        parameter: g
        to: 2
        at_seconds: 1.3          # was 0.9: the reveal ends at 0.85 s, and gain_low needs 0.3 s of rest
        duration_seconds: 0.7    # was 1.3: gain_high needs 0.3 s of rest, and the scene fades from 2.35 s
        value_label: "gain g"
    snapshots:
      - id: gain_low
        at_seconds: 1.2          # was 0.88
        stop: true
        label: "gain 1"
        description: "The toy curve at gain 1 and width 0.8, peaking at r = 1 over x = 0, before the sweep."
      - id: gain_high
        at_seconds: 2.3
        stop: true
        label: "gain 2"
        description: "The same curve at gain 2: the peak at r = 2, the width unchanged; the readout reads g = 2.0."
```

What validation said before the fix:

```text
error   stop 'gain_low' at 0.88s has no rest before it: the reveal of 'gain_curve' runs 0-0.85s. ...
error   stop 'gain_high' at 2.3s has no rest before it: the motion of 'raise_gain' runs 0.9-2.2s. ...
```

```sh
cd examples/features
scianim validate clips/families/features/tuning_sweep
scianim timing clips/families/features/tuning_sweep      # three parts: 1.2, 1.1 and 3.7 s
lk clips . --only tuning_sweep
lk clips . --only tuning_sweep --mode dark
lk build . --strict && lk build . --profile dark --strict
lk review frags _build/slides-live.html --slides 12
```

The slide:

```markdown
## A manim8 clip in parts {role=example time=1.5}

::: {.movie clip="tuning_sweep" stops="gain_low gain_high"}
The storyboard marks stops (`stop: true`); the deck chooses which to hold.

:::: {.stop ref="gain_low"}
Ask: the gain doubles next. Where does the peak go, and does the curve widen?
::::
:::: {.stop ref="gain_high"}
Say: the peak doubled in place; next the width grows.
::::
:::
```

`lk review frags` on it:

```text
12  A manim8 clip in parts  (2 fragments)
      a clip in parts: tuning_sweep, 3 parts, start=auto, 2 key(s)
      step 0: hold 1 of 3, frame 36 (1.200 s), shown 36, paused at frame 34, key to hold 0.99 s
      step 1: hold 2 of 3, frame 69 (2.300 s), shown 69, paused at frame 67, key to hold 1.17 s
      step 2: hold 3 of 3, frame 179 (5.967 s), shown 179, paused at frame 177, key to hold 3.74 s
      backward entry: hold 3 of 3, frame 179 (5.967 s), shown 179, paused at frame 177, key to hold 0.14 s
      jump to the first cue: hold 2 of 3, frame 69 (2.300 s), shown 69, key to hold 0.15 s
      <- the hold 2 (gain_high) has no "Ask:" in its notes
```

## Points to make

- A stop is a reveal and a prompt: the lecturer chooses it (POLICY.md, Clips in stages). The storyboard offers
  candidates; the slide holds at the ones it names.
- The clip stays one movie. A hold is a frame number, not a time, and while the clip holds the room sees the still
  of exactly that frame.
- The rest before a stop is what lets the player pause a frame or two early and then seek, unseen. manim8 refuses a
  stop without it, and the deck refuses one with fewer than three frames of unchanged picture.
- A prompt costs about a minute: the timing report counts one per "Ask:", and warns CLIP>TIME when the slide's
  `time=` does not cover them. On the feature deck only the first hold carries one, to keep the deck in its
  budget, and `lk review frags` points out the hold that has none.
- `start=key` opens the slide on frame 0 for a prediction before anything moves; the kit slide uses it.

## Artefacts

- `before/storyboard.yaml`: the storyboard without stops, as in lecturekit 0.3.1 (`git show 959c3e4:examples/features/clips/families/features/tuning_sweep/storyboard.yaml`).
- `after/storyboard.yaml`, `after/clips.json` (the `tuning_sweep` entry), the stills `tuning_sweep.f0036.png`,
  `tuning_sweep.f0069.png` and `tuning_sweep.f0179.png`.
- `after/frags.txt`: the walk above; `after/slide-12-f0.png` to `after/slide-12-f2.png` from `lk review frags`.
- `after/study-page-12.png`: the strip.

## Notes

Stops need manim8 at the commit lecturekit's `manim8` extra names (manim8's ADR-045). Without manim8, the episode
can be followed on slide 11, whose clip is drawn by `make_clips.py` and adopted with its stops in seconds, or on
slide 13, a kit scene that `lk clips` renders with Manim alone.
