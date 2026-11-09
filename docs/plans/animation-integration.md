# Animation across lecturekit, manim8 and lecturekit-expo: audit and plan

9 November 2026. State examined:

- lecturekit at `521078f` (branch `claude/vigilant-dirac-gkw52u`);
- manim8 at `01afcbf` (branch `claude/scianim-handoff`; manim8's `main` holds only a LICENSE);
- lecturekit-expo at `5f98efd` (`main`).

This document answers four requests:

1. an audit of how the three repositories work together (section 1);
2. how animation can become part of the examples rather than an attachment to them (section 2);
3. how to split a clip into parts separated by key presses in the live deck (section 3);
4. what an author does when they want finer control over one slide's animation (section 4).

Section 5 orders the work across the three repositories into milestones. Section 6 lists what the lecturer has to
decide.

**Method.** Readers took each side of every join. An empirical run then installed manim8, rendered an example and
fed it through `lk clips` and `lk build`. Each interoperability finding was given to an adversarial verifier. The
designs in sections 3 and 4 each came from several independent drafts, scored and merged, and a completeness review
then reconciled them. The segmentation runtime was prototyped and tested in headless Chromium; the prototype is in
`segmentation-prototype/`.

Statements below are marked as verified (read in code, or run) unless they are proposals. Path references are to
the repository named in the surrounding text.

## 1. Interoperability audit

### 1.1 What was checked

The audit followed one clip from installation to the slide:

1. install manim8;
2. build its render environment;
3. render a project;
4. bring the result into a deck with `lk clips`;
5. style it with `lk theme --manim8`;
6. build both outputs;
7. play it in the live deck and check it with `lk review`;
8. run all of it in continuous integration.

Each step was read on both sides of the join and then run in a scratch copy, with Python 3.12 and 3.13, Quarto 1.11.9
(reveal.js 5.1.0), Manim 0.22.1 in a manim8 family environment, and headless Chromium driven by real key presses.

The cross-check produced 24 findings. Two verifiers then tried to refute each one against the code. None was
refuted; 13 held as stated and 11 held after a correction. The corrected statements are the ones given here.

The parts work on their own:

- lecturekit's tests pass, 15 of 15 with its venv on PATH.
- manim8's unit tests pass: 190 pass and 1 is skipped.
- `scianim snapshot` and `scianim render --profile final` produce the 18 s `divisive_normalization` clip, with four
  in-flow checkpoints, in about 22 s.
- After two hand edits, a style bridged from a lecturekit brand validates and renders in TeX Gyre Heros.
- With a still copied in by hand, the manim8 clip appears correctly in both the live deck and the study PDF.

The failures are all at the joins.

### 1.2 Findings

Severity:

- **blocker**: the documented integration cannot work;
- **major**: it works only by hand, or silently gives a wrong result;
- **minor**: friction or a latent fault;
- **drift**: docs, pins or copies out of step.

| ID | Sev. | Fix in | Finding |
| --- | --- | --- | --- |
| I1 | blocker | manim8, lecturekit | No install route works. The `manim8` extra points at manim8's `main`, which holds only a LICENSE. The code is on `claude/scianim-handoff`. There are no tags, and nothing is on PyPI. pip cannot install even the right branch, because `manim8-core==0.1.0a0` resolves only through a uv workspace source; uv can install it. manim8 needs Python 3.12; lecturekit allows 3.11. |
| I2 | major | manim8 | Only an editable manim8 checkout can build a family environment. Any other install writes a family pyproject that asks the index for the unpublished `manim8-bridge`. A checkout writes relative path sources, which break when the workspace is committed and cloned elsewhere. |
| I3 | major | lecturekit | `lk clips` copies the newest MP4 under `renders/`. That file is the last scene's section, not the movie: 12 s of an 18 s clip in the run. It also reads top-level `width`, `height`, `duration` and `revision` keys that manim8's manifest does not have. The real values are in `result.videos[0]` and `job.revision_id`, so the copied clip's `revision` is always `unknown`. |
| I4 | blocker | lecturekit | Stills are looked for in `<clip>/checkpoints/`, which manim8 never writes, so every manim8 clip gets `"still": null`. `still_checkpoint` exists, but nothing passes it. |
| I5 | blocker | lecturekit | `"still": null` decodes to a truthy `pandoc.json.null` and crashes the live build at `dual-output.lua:68`. Quarto 1.11 also redefines `error()` as a logger, so none of the filter's own checks stops a build: a movie without a still is silently dropped from the PDF, and the build exits 0. |
| I6 | major | lecturekit | `lk theme --manim8` writes the style name `lecturekit-paper` (with a hyphen) and the palette keys `CSS`, `DN`, `DoG` (with capitals). manim8's slugs reject all four, for every brand in the kickoff and the expo. |
| I7 | major | lecturekit | Nothing selects the bridged style in a project's `animation.yaml`, and nothing passes the mode or brand to `scianim render`, so clips keep manim8's house style. `family init` without `--style` gives a near-black background. |
| I8 | major | lecturekit | `lk clips` runs neither `scianim codegen` nor `family env sync`. It stops on the first failing clip with a traceback, and saves the index only at the end. |
| I9 | major | lecturekit | In the documented clip `.r-stack`, the first step's video keeps playing hidden, because the pause loop searches only descendants. Entering the slide backwards plays every step at once. |
| I10 | major | lecturekit | R does not replay a clip: Quarto's support plugin binds R to Scroll View, and Reveal ignores `preventDefault`. P resets the pacing clock and also goes back. |
| I20 | major | lecturekit | `lk review frags` flags as misplaced exactly the form the docs prescribe (`.fragment` > `.live-only` > `.movie`), and passes the reverse. |
| I11 | minor | all three | No CI anywhere renders a clip or runs `lk clips`, and every expo review step ends in `\|\| true`. No test covers `render_manim8`, clip naming, `--crop`, style validity, a clip in a fragment, or the Space and R keys. |
| I12 | minor | expo | The expo pins lecturekit to a moving branch with no lock file. The version check compares only the major version, so filter changes made without a version bump go unreported. |
| I13 | minor | lecturekit, expo | Kit clip names use hyphens. manim8 project ids must be underscore slugs, and the expo declares hyphenated names. A kit clip and a manim8 clip of the same name overwrite each other silently. |
| I14 | minor | lecturekit | `--size` and `--crop` never reach manim8. manim8 clips arrive at 1920x1080 and at the project's frame rate, which is 60 fps for `gabor_filter`. |
| I15 | minor | manim8, lecturekit | manim8 registers no fonts, so it finds lecturekit's bundled TeX Gyre and Roboto only if fontconfig already has them. |
| I16 | minor | lecturekit | The bridge maps text greys onto manim8's fill roles (`neutral` gets `muted`), and leaves every `<role>_soft` tint at manim8's value. |
| I17 | drift | expo | `manim8_kinds` names kinds that do not exist: `plot` and `caption`. |
| I18 | minor | lecturekit | `lk new --vendor-only` fails on the expo's symlinked `_extensions`. Its `--force` upgrade silently replaces the copy that all projects share. |
| I19 | minor | lecturekit | `lk build` sets no `QUARTO_PYTHON`, so `make_assets.py` fails unless the venv is activated. |
| I21 | minor | lecturekit, manim8 | Neither the scaffold nor `workspace init` ignores `renders/`, `.scianim/` or the family `.venv`. The expo has committed Beamer auxiliary files. |
| I22 | drift | lecturekit | CLIPS.md and tutorials 05 and 10 describe things that do not exist: a `workspace.yaml` that lecturekit reads, the skill, and `--only bar`. `lk docs` points at an empty `main`. |
| I23 | drift | expo | PLAN.md promises `lk clips --preview`, a two-preset matrix and gated checks, none of which exist. |
| I24 | drift | lecturekit, expo | The scaffold templates name `example.tikz` for a `.tex` file and fix `budget: 45`. As a result, every expo deck reports 45 minutes against the 20 to 30 in its `expo.yaml`. |

### 1.3 Four causes

**manim8 has not been released, and everything downstream assumes it has (I1, I2).** The code lives on a branch and
the default branch is empty. The render side is reachable only from an editable checkout. Meanwhile lecturekit's
extra, its docs, tutorial 10 and the expo's PLAN all describe a tagged, installable manim8. Until manim8 has three
things, no manim8 instruction in the other two repositories can be followed on a second machine:

- a default branch with code;
- a tag;
- a way for a family environment to obtain `manim8-bridge` without the checkout.

**lecturekit's join was written against manim8's specification, not its output, and was never run (I3, I4, I6, I7,
I8, I13 to I16).** Each mismatch is small. Together they mean that the one documented path, `lk clips` on a
`clips/` workspace, puts the wrong video in the deck with no still, and the build then fails. The fixes are
mechanical once lecturekit reads the manifest manim8 actually writes:

- the movie from `result.videos[0]`;
- the still from the frame of a named snapshot;
- the revision from `job.revision_id` and `job.cache_key`.

A recorded manifest checked in as a test fixture would have caught all of them.

**lecturekit's clip runtime has faults of its own (I5, I9, I10, I19, I20).** They are independent of manim8. They
matter more than their count suggests, because key-press segmentation builds on exactly this code: the fragment
handler, the key bindings, the frags check and the filter's error path. Quarto's redefinition of `error()` is a
general hazard: every `error()` in `dual-output.lua` is advisory today.

**The expo has drifted from its own plan and from the registry (I12, I17, I18, I21, I23, I24).** It cannot yet be
manim8's proving ground:

- it has no clip workspace;
- it has no clip tooling in CI;
- its kind names do not exist;
- its clip names cannot be manim8 ids;
- it pins its engine in a way that hides regressions.

**A structural point: nobody owns the join.** manim8 contains no reference to lecturekit. Its only external contract
is `schemas/artifact_manifest.schema.json`, and `scianim render` has no machine-readable output. So lecturekit
guesses, by file name, by modification time, and by keys that do not exist. The durable fix is for manim8 to own a
small export contract (M6): `scianim render --json` prints the manifest of the job just run, cache hits included.
lecturekit then refuses a manifest `schema_version` it does not know and records `job.registry_version`.

## 2. Making animation integral to the examples

### 2.1 Where it stands

**Kickoff deck.** The kickoff has one clip, `bar-bold` (a kit scene, 18.8 s). The plan mentions it only as the
visual cell of slide 1, "clip `bar-bold.mp4`; PDF: `bar-bold.tex`" (`examples/kickoff/PLAN.md:7`). Its five
stages exist only in the scene's docstring (`anim/clip_bar_bold.py:6-13`). The deck uses the older `src=` form, and
has no `clips.json` and no still. The figure twin `bar-bold.tex` has no generator, although `MANIFEST.md` and the
README say it regenerates from `make_assets.py`: `ALL` at `make_assets.py:300` lists six figures and not
`bar_bold`. The simulation behind `assets/data/s01.json` is not in the repository. Its metadata names prfmodel 0.1.0,
while slide 5 says 0.2.0 is installed and slide 1's notes speak of "the forward model you will be running this
afternoon".

**Features deck.** Its two clip slides share a 1.5 s synthetic stand-in. It does not exercise any of:

- `aspect=` and `still=`;
- a clip inside a fragment, or an `.r-stack` of clips;
- a `--crop` clip;
- a clip on a paper slide;
- any manim8 render.

**Method and templates.**

- *Plan.* `docs/WORKFLOW.md` has no clip column in the plan, and its storyboard template assumes "the only clip"
  (`:88`).
- *Timing.* The `duration` in `clips.json` is "informative" (`CLIPS.md:39`), and the filter never reads it.
- *Review.* No review command looks inside a clip. `frags` reports only whether a clip is shown and whether it is
  playing.
- *Facts.* FACTS.md has nothing on claims made inside a clip.
- *Engagement.* `POLICY.md:72` requires an `ENGAGEMENT.md` with "predict-then-reveal before every clip stage". No
  deck, template or workflow step produces one.

**Expo.** The expo names eleven clips in its `expo.yaml` files. None appears in a storyboard, none is rendered, and
no project has `clips/`.

The pattern is the same throughout: a clip is something attached to a finished slide, not something planned,
checked and costed with it.

### 2.2 What integral means, concretely

A clip is integral when five things hold:

1. It is a row in the plan before it is rendered, with its stages, duration, still and source numbers.
2. One simulation feeds the figure, the clip and the numbers on the slide.
3. Its seconds, and the prompts at its stops, count against the slide's `time=`.
4. The review loop looks at its frames, not at one arbitrary frame and a playing flag.
5. FACTS.md covers what a viewer can read off it.

The changes below implement these five (proposed throughout).

**One naming rule.** A clip name is a slug, `^[a-z][a-z0-9_]{0,63}$`. This is manim8's rule
(`scianim_core/common.py:17`), applied to both producers and to stop ids:

- `clip_bar_bold.py` gives `bar_bold`;
- a duplicate name is a fatal error;
- hyphenated `clip=` names get a one-release alias.

This closes I13.

**STORYBOARD template.** It gains a section "What moves". For each moment the audience must see in motion, it
records:

- what changes, and why a still or a staged figure cannot carry it;
- the stages in order;
- where the room predicts;
- where the numbers come from.

A moment that a staged figure can carry is a figure, not a clip.

**PLAN template.** The slide table gains `Clip s` and `Numbers from` columns, and a new `## Clips` table becomes
the contract that review parses:

| clip | slide | role | producer and source | rung | stages (clip s) | stops | s | still | numbers from | study equivalent |
|---|---|---|---|---|---|---|---|---|---|---|
| `bar_bold` | 1 | mechanism | kit `anim/clip_bar_bold.py:BarBold` | R8 | sweep_right 0.8; delay 5.9; sweep_back 6.57; blank 12.82; hold 16.22 | none | 18.8 | end | `assets/data/s01.json` | `bar-bold.tex` |

Field rules:

- **role**: one of `mechanism` (runs the process the title claims), `dial` (sweeps one parameter), `answer` (plays
  after a prediction) or `build` (assembles a picture, usually with stops).
- **rung**: the rung of section 4.
- **stages**: the candidate stop points.
- **stops**: the stages the live deck will wait at.

The kickoff stage times above are computed from the scene and `s01.json`. They match the keyframes measured in
`bar-bold.mp4`.

**FACTS template.** It gains a table "What the clips show". A clip asserts whatever a viewer can read off it: a
lag, a position, an order. Each such reading is a row, checked against the data file the clip was rendered from.
For the kickoff, the rows are:

- the BOLD peak lags the overlap peak by 5 s (`summary.median_peak_lag_s`, peaks at 19 and 24 s);
- one illustrative population at (2.5, 1.5) deg with sigma 1 deg;
- the prfmodel version conflict above, marked "to confirm".

**ENGAGEMENT.md.** It becomes a template, as POLICY.md already requires. Its columns are slide, device, prompt,
stop, answer shown at, and "keep if short".

**MANIFEST template.** It gains a column "From (data file, sha12)" and a revision column.

**Scaffold.**

- `lk new --budget N` replaces the fixed 45 minutes (I24).
- `lk new --manim8` writes a `clips/families/<slug>/` family, an `animation.yaml` template at 1280x720 and 30 fps,
  and the bridged style.
- The scaffold's `.gitignore` covers `clips/**/renders/`, `clips/**/.scianim/`, `clips/**/.venv/` and the Beamer
  auxiliary files (I21).

**Timing.**

- `resolve_clip` returns the entry's `duration`, and the filter adds it to the slide's timing entry.
- `timing.txt` gains a `clip s` column.
- A slide whose clip seconds plus about a minute per "Ask:" exceed its `time=` is flagged `CLIP>TIME`. The minute
  per prompt is POLICY.md:72's own estimate.

### 2.3 One simulation for figure, clip and numbers

```text
sims/<sim>/run.py, config.yaml, README.md   writes assets/data/<sim>.json (+ <sim>_<table>.csv for manim8 bindings)
assets/data/<sim>.json                       {"meta": {"provenance": {script, config_sha256, code_sha256, software, seed}}, ...}
make_assets.py                               each figure declares the data files it reads
anim/clip_*.py                               data = ('s01.json',)
clips/families/<f>/<clip>/animation.yaml     extensions.lecturekit: {bind, data, preview}
```

**What manim8 accepts as data today (verified).**

- Source paths must stay inside the project: `RelPath` refuses `..` (`common.py:33-46`).
- `asset://` resolves under the family's or the workspace's `assets/` (`families/resolve.py:182-197`).
- JSON is not a manim8 source type (`animation.py:22`).

**How lecturekit bridges the gap (proposed).**

- *CSV for clips.* A simulation writes a CSV for any table a manim8 clip binds. `lk clips --sync` copies it into
  the family's `assets/`.
- *Scalar values.* A pRF centre or a gain lives in the storyboard as a literal. `extensions.lecturekit.bind` maps
  each one to its data key; `extensions` is the one place manim8 tolerates unknown keys (`animation.py:161-162`).
- *When a value differs.* `--sync` writes and validates a `revise_storyboard` proposal with one claim per number,
  then stops. Applying it is the lecturer's call, because a data change touches what the slide claims.
- *`lk review data`* checks that:
  - every named data file exists and has provenance;
  - each clip's data hash equals the current file;
  - each bound value equals the storyboard literal.

### 2.4 Looking at clips in review

**`lk review clips <deck> [--sheet] [--strict]`.** It extracts frames at each stage, each stop and the still, plus
six evenly spaced frames, and writes a labelled strip per clip. It checks:

- the declared stages against the index;
- the planned duration against the rendered one, within 10%;
- the still against its frame;
- for manim8 clips, the deck's frame at each checkpoint against manim8's own PNG of that snapshot (this check alone
  would have caught I3);
- a keyframe at each stop (a warning only);
- the background against the slide token;
- the size and frame rate.

**The contact sheet.** `lk review shoot` seeks each clip to its still and, with `--fragments`, to each stop. This
needs a review server that answers Range requests: Chromium could not seek clips served by the current
`SimpleHTTPRequestHandler` (`review/browser.py:26`).

**Feedback.** Review comments name the clip and the stage. For a manim8 clip, the strip frames are checkpoints, so a
comment maps directly onto `scianim feedback add --snapshot <id>`.

### 2.5 The decks

**Kickoff.**

- Wire `bar_bold` through `clip=` with a still.
- Restore `bar_bold()` in `make_assets.py` so that the TikZ twin regenerates as the README claims.
- Fix the stale provenance: "Clip A04 (slide 4)", `anim/render_clips.py`, and the import comment at `vfield.py:8`.
- Add PLAN, FACTS and ENGAGEMENT rows, and a `sims/s01_bar_run/` that records how `s01.json` was made. It is not
  run in CI, because prfmodel needs JAX.

Two choices are the lecturer's:

- Slide 1 shows two bullets beside the clip, against POLICY.md:48 (a clip stands alone on its live slide): move them
  to study-only, or record the exception.
- After M7, slide 1 could become an `.r-stack` of a short manim8 clip cut from the `prf_tuning` example, then
  `bar_bold`. The Gaussian surface would be seen from above until it reads as the disc that `bar_bold` starts from.
  Here the order is the explanation: what a pRF is, then how it is measured.

The kickoff gets no stops. Its clip has no rests, its slide is a two-minute welcome, and its prompt is a show of
hands.

**Features: the test deck for every movie form.** A small numpy simulation, `sims/sweep.py`, replaces the
synthetic stand-in. It feeds a kit scene, a two-scene manim8 project and a TikZ figure. One slide per form:

| # | Form | What it pins |
|---|---|---|
| 1 | `src=` in `.live-only` with a `.study-only` figure | the paired form |
| 2 | `clip=` kit clip with a still | the join |
| 3 | `clip=` with `still=` and `aspect="4:3"` in a column | the overrides |
| 4 | a `--crop` clip | crop shape; keyframes and frame count kept |
| 5 | `.fragment` > `.live-only` > `.movie` | a clip started by a key press (I20) |
| 6 | `.live-only` > `.r-stack` of clips | sequence pause and back navigation (I9) |
| 7 | a clip on a paper slide | the multiply blend |
| 8 | `clip=` of the two-scene manim8 clip | the full movie, not a section (I3); a frame-exact still (I4) |
| 9 | a clip in parts (section 3), one kit and one adopted | stops, holds, strip, notes |
| 10 | an adopted external MP4 | rung R9 |
| 11 | the dark build on clips rendered in the dark mode | restyle |

A further slide whose clip exceeds its `time=` shows `CLIP>TIME` in the build. The engine's tests build the deck
and run `frags` forward and backward on forms 5, 6 and 9. They also check the index fields and the number of
`\lkimageh` calls per study frame.

**Expo.** The first real manim8 clip goes to **divisive-normalization**, for five reasons:

1. manim8 ships the seed (`examples/.../divisive_normalization`, two scenes, 18 s).
2. The audit rendered it at the final profile.
3. Its two scenes are exactly where the join breaks worst (I3).
4. Registered kinds suffice.
5. It is the author's own topic.

Three changes are needed:

- The example's equation is labelled as not a general model, so it has to become the Carandini and Heeger form.
  That is a change to what the clip claims, and needs the lecturer's sign-off.
- The clip-internal captions go, per POLICY.md.
- The output becomes 1280x720 at 30 fps.

The second project is **signal-detection**: the first manim8 clip with stops, and the first in the dark preset
(section 4.5).

The expo needs:

- pins by SHA;
- a CI job that installs Cairo, Pango and the fonts, builds manim8's three wheels at the pinned SHA (the only route
  shown to render outside a checkout), and runs `lk clips --strict`, `lk review clips --strict` and
  `lk review data`, with no `|| true`;
- `tools/check_meta.py`, which checks that `minutes` equals the budget, that clip names agree between PLAN and
  `clips.json`, and that kinds are registered;
- a reel page built from every project's `clips.json`.

**Tutorials.**

- **03** asks for "What moves" and the clips table.
- **04** becomes "One simulation, three outputs".
- **05** uses `bar_bold`, and the index with its stages.
- **06** gains a clip review round.
- **10** is rewritten for the pinned install and `lk new --manim8`.
- **New: "A clip on key presses"** (section 3).
- **New: "More control over a clip"** (section 4).

## 3. Key-press segmentation

### 3.1 The choice

There were three candidate designs.

1. **One file per part, in an `.r-stack`.** This reuses today's sequence pattern. But it cuts one mechanism into
   files, flickers at the swaps unless the next file is preloaded, and inherits I9.
2. **One reveal slide per part**, as manim-slides 5.7 exports. This makes back navigation simple, but breaks
   lecturekit's slide counting, timing and study pairing.
3. **One file, held at stops.** Empty Reveal fragments act as cues; the runtime pauses near each stop, then seeks to
   the stop's exact frame.

The proposal is the third. Three independent designs were scored. The strongest, which put the presenter first, was
merged with the contract and authoring ideas of the other two, and its riskiest claims were prototyped. In headless
Chromium with Quarto 1.11.9 (`segmentation-prototype/`):

- **Exact holds.** Pausing and then setting `currentTime` to the middle of the stop frame held exactly that frame,
  forward and backward, mid-GOP, at 30 and 60 fps. The check read the frame index both from the video and from
  screenshots. Keyframes at the stops are not needed for exactness; they only shorten seeks.
- **Where the pause lands.** It lands *early*, never late. With `requestVideoFrameCallback` and a two-frame guard,
  the last frame shown was one to two frames before the stop. The `timeupdate` fallback paused 75 to 290 ms early.
  The rest that hides this must therefore sit *before* the stop.
- **Backward entry.** Coming back from the next slide fires only `slidechanged`, with every cue already visible. The
  runtime held the final frame and never played.
- **No hidden playback.** No segmented clip played hidden in any run, sampled every 20 ms. A deck-wide guard, run on
  every Reveal event, also fixed I9's hidden r-stack playback.
- **Keys and the speaker window.** Keys bound through `Reveal.configure({keyboard})` run before Quarto's plugin
  bindings, so R replays without turning on Scroll View (I10). Space and R pressed in the speaker window reach the
  main deck through `window.opener`. The speaker previews never load the clip.
- **No Range support.** A server without Range support makes the video unseekable. Fetching it into a Blob only then
  passed all checks.
- **Totals.** 52 of 52 checks passed with and without Range support, 9 of 9 in the speaker window and 9 of 9 under
  random key mashing. The committed copy was re-run from scratch and passed again.

Not yet tested: Firefox, WebKit, `file://` (the documented way to open the live deck, so it belongs in the first
milestone's acceptance), `quarto preview`, 1080p clips on the lecture laptop, a hidden tab and the degraded path.

### 3.2 Authoring

**In the deck** (proposed):

```markdown
## Criterion and hit rate {time=4}

::: {.movie clip="criterion_roc" stops="neutral" start=key}
The criterion moves; hits and false alarms trade along one curve.

:::: {.stop ref="start"}
Ask: if the criterion moves right, which rate falls faster?
::::
:::: {.stop ref="neutral"}
Ask: where will the point be when the criterion reaches 2?
::::
:::
```

- **`stops=`** names stop ids from the clip's index entry, in time order, or `all`. Without it the clip plays
  through as today. Segmentation is opt-in because POLICY.md:17 allows a reveal only where the order is the
  explanation.
- **`start=`**: with `auto` (the default), part 1 plays when the slide appears. With `key`, the slide opens on frame
  0 and the first key starts part 1, which suits predict-then-reveal.
- **`.stop ref=<id|start|end>`** holds the speaker notes for the hold at that point.
- **`study=`** chooses the PDF output: `strip` (the default with `stops=`), `final`, or a list of ids.
- **`still=<id>`** names the single still for an unsegmented clip. The deck, not the producer, chooses stops and
  stills.

The build fails on each of these:

- an unknown or out-of-order id;
- `stops=` on the `src=` form;
- a stop with less than three frames of rest before it;
- more than five stops;
- two segmented clips on one slide;
- any other fragment on the slide;
- a segmented movie inside `.fragment` or `.r-stack`.

These checks need I5 fixed first, so that a filter error actually stops the build.

**In a manim8 storyboard** (a manim8 ADR, proposed). `Snapshot` gains three defaulted fields:

```yaml
- id: neutral
  at_seconds: 6.8
  description: "Criterion at d'/2: hit rate equals one minus the false-alarm rate."
  stop: true
  label: "c = d'/2"
  stop_through: []        # orbit_camera ids allowed to move through this stop
```

A snapshot is the right carrier. Its time is already a breakpoint of the generated scene (`codegen/generate.py:189`,
`:201`), and its state is the first frame of the next play (`scene.py:146-153`). One line therefore buys a
frame-exact hold reached by the real animation flow, plus a reviewed still.

Validation, in `planning/checks.py` beside `check_actions`, refuses:

- a stop whose checkpoint is approximate (time-based updaters);
- any reveal, action (lead-in included) or scene fade active in the 0.3 s before the stop;
- a stop at a scene start or on the last frame, within 0.5 s of another stop, or on another stop's frame;
- an orbit active across a stop, unless it is named in `stop_through`. Naming it turns the error into a recorded
  warning.

A proposal rule can split an orbit at the stops. The new fields are excluded from scene fingerprints, as `patterns`
is (`planning/dependencies.py:157`), because they change no picture.

Applied to `gabor_filter`, the three natural stops each have exactly 0.3 s of rest before them. Its single 0 to 26 s
orbit, however, fails the orbit rule until it is split or waived. The orbit in `prf_tuning` fails the same way.

Until this ADR lands, lecturekit treats every reached snapshot as a candidate stop. The manifest already records
their times in `result.reached`.

**In a kit scene** (proposed): `checkpoint(self, id, label=None, rest=0.0)` waits half the rest, opens a Manim
section of type `lecturekit.checkpoint`, then waits the other half. Manim reserves section types for third-party
tools, and 0.22.1 has both `next_section(..., section_type=)` and `--save_sections`. A stop's frame is the sum of
`nb_frames` over the earlier sections. The same call names a study still, generalising today's `still = <seconds>`.

**For an adopted MP4** (proposed): `lk clips adopt <mp4> --name --stops 4.0 8.0 --labels ...` replaces
`index_existing`, which only tests call. It measures the rests in the pixels, and refuses stops whose rest is under
three frames.

### 3.3 The data contract: `clips.json` format 2

```json
"criterion_roc": {
  "format": 2, "producer": "manim8", "rung": "R3",
  "video": "assets/clips/criterion_roc.mp4", "sha256": "3f2a9c1e...",
  "poster": "assets/clips/criterion_roc.f0000.png", "still": "assets/clips/criterion_roc.f0599.png",
  "width": 1280, "height": 720, "fps": 30, "frames": 600, "duration": 20.0,
  "revision": "rev_0002", "job": {"id": "job_...", "cache_key": "..."},
  "source": "clips/families/sdt/criterion_roc", "data": {"assets/data/sdt.json": "a1b2c3d4e5f6"},
  "stops": [{"id": "neutral", "frame": 204, "pts": 6.8, "label": "c = d'/2", "notes": "...",
             "still": "assets/clips/criterion_roc.f0204.png", "rest_before": 30, "rest_after": 15, "frozen": []}],
  "end": {"frame": 599, "pts": 19.966667, "still": "assets/clips/criterion_roc.f0599.png"}
}
```

**Fields and their meaning.**

- `stops` holds candidates; the deck chooses among them.
- `frame` is authoritative. `pts` is the measured presentation time, and the runtime seeks to `pts + 0.5/fps`. This
  tolerates kit output, whose frame times sit up to 0.65 ms off the frame grid.
- Stills are extracted from the delivered video by frame number. manim8's checkpoint PNG serves only as a
  cross-check, at a mean difference of at most 1.0.
- `poster` is frame 0. The current last-frame poster would show the ending before part 1.
- `sha256` versions the URL (`?v=`), which removes the stale-cache problem in CLIPS.md:11.
- Absent keys are omitted, never written as `null` (I5).
- An entry without `format: 2` keeps today's meaning.

**From a manim8 manifest**, once I3 and I4 are fixed:

- the video and its size, frame rate and frame count come from `result.videos[0]`;
- the revision comes from `job.revision_id`;
- the stops come from `result.stops` once the ADR lands, from `result.reached` before.

Before an entry is written, lecturekit cross-checks it:

- `round(t * fps)` must equal the frame;
- a play must start at that frame;
- the plays over the rest must be static;
- the extracted still must match the checkpoint PNG.

A failure stops only that clip (I8).

**Encoding.**

- Every producer's output is remuxed to `+faststart` by stream copy.
- Any re-encode (`--crop`, `--size`) passes `-force_key_frames` at the stops and checks that the frame count is
  unchanged. Today's crop drops the keyframes at play boundaries.

### 3.4 The live runtime

The filter emits the video without `data-autoplay`. Quarto leaves `autoPlayMedia` unset, so Reveal then never
starts it. The source goes in `data-lk-src`, which only the main window turns into `src`; the speaker previews never
load the clip. Each boundary gets a still image, and each key press an empty fragment cue.

Let k be the number of visible cues. State k holds on boundary k+1 with `start=auto`, or on boundary k with
`start=key`. The runtime never moves Reveal. It only makes the video agree with k, and a still covers every seek, so
Reveal's fragment index, the URL hash, the overview, the speaker previews and linear navigation all stay true.

| Input | Action |
|---|---|
| enter with k = 0 | `auto`: play part 1 from frame 0; `key`: hold frame 0 |
| enter with k > 0 (back from the next slide, a jump, a hash) | hold the state's frame at once; never play |
| next key while a part plays | extend the target: play through the coming stop |
| next key while holding | play from the hold to the next stop |
| previous key | hold the earlier state's frame at once; never play backwards |
| frame watcher reaches the target (rVFC, 2-frame guard; `timeupdate` 0.3 s early as fallback) | pause, seek to the stop frame, confirm, hold |
| Space or a click | toggle a playing part; at an intermediate hold, advance; at the final hold, nothing |
| Shift+Space | previous |
| R | replay the part that ends at the current hold |
| overview opened during a part | pause; resume on close if nothing moved |
| `play()` refused by the browser | show the still of the part's start, never a hold the room has not seen |
| a play the runtime did not start | pause it, and re-seek the hold |
| seek unconfirmed after 2 s, or a media error | degraded: stills follow the cues, keys move Reveal only |
| leaving the slide | pause, show the static still |

**Keys.** Space, R and the pacing reset (moved from P to T) are bound through `Reveal.configure({keyboard})`. The
capture-phase listener in `live-head.html` goes. P returns to Reveal's "previous". These are deck-wide changes:
ordinary clips and flash slides need their Space, R and click handling re-homed in the same binding, and
AUTHORING.md:300 and tutorial 01 must be updated.

**Notes.** After a backward entry, the runtime dispatches a synthetic `resumed` event on the next tick, so that the
notes plugin re-posts the current cue's notes instead of the slide's.

**Loading.** Clips on the current slide and its neighbours get `src`. If the file is not seekable once its metadata
is in, it is fetched into a Blob.

### 3.5 Study PDF, notes and timing

**Study PDF.**

- `study=strip` prints the hold after each part, numbered and labelled, through a new `\lkstrip` beside
  `\lkimageh`, which never upscales. These are the "static stages" that POLICY.md:48 already puts on the study page.
- The whole strip stays inside the one-bullet figure budget, 4.8 cm (LAYOUT.md:17).
- Three panels fit in one row of about 45 by 25 mm; four to six panels take two rows.
- More than six panels is a build error that points to `study=`.

**Notes.** Each cue's notes are composed in POLICY.md:72's order: the "Ask:" first, then the `.stop` text, then a
part header ("part 2 of 3, 5.5 s"), then the producer's description. `frags` reports any stop without an "Ask:".

**Timing.** `timing.txt` gains a line per segmented clip, with its parts and its prompts. The pacing box shows the
current part.

### 3.6 Review, tests and order of work

**`lk review frags`.** For each step it reports the expected hold (frame and pts), the frame on screen, the last
frame shown before the pause, and the time from key to hold. It also walks a backward entry and a jump.

**Tests.**

- The prototype's barcode clips become the oracle: every frame encodes its own index, in three encodings.
- pytest covers the index writer, the manim8 mapping against a recorded manifest, the kit section sums and the Lua
  output.
- Playwright runs on Chromium in CI and on Firefox and WebKit nightly, pinned to Quarto 1.11.9. `lk build` warns on
  an untested Quarto version, because the runtime depends on reveal.js 5.1.0's event order.

**Order of work.**

1. Fix I5, I9 with I10, and I20, and add the Range-capable review server (M1, M2).
2. Then the external and kit producers, end to end on the features deck (M3, M4).
3. Then manim8 clips with candidates from `result.reached`, needing no manim8 change (M7).
4. Then the manim8 ADR (M8), and the expo's signal-detection slide (M10).

## 4. Escalation: more control over one slide's animation

### 4.1 Before the ladder

First ask whether the slide needs a clip at all. A moment that a staged figure can carry, such as two or three
states compared, is a TikZ `.r-stack`. It has identical bounding boxes, a study page that shows every state, and no
render. A clip is for what is only clear in motion.

Today, because manim8 cannot be installed (I1, I2), only the bottom rungs reach a slide:

1. a kit clip played through (R8);
2. after M3 and M4, a kit clip with checkpoints and stops;
3. a sequence of different clips in an `.r-stack`, after I9 is fixed;
4. an adopted MP4 (R9).

### 4.2 The ladder

The guarantees at stake:

| Code | Guarantee |
|---|---|
| T | colour and font tokens |
| M | motion tokens |
| C | frame-exact checkpoints reached by the animation flow |
| S | key-press stops |
| R | write-once revisions |
| V | review UI and typed feedback |
| P | proposal record with claims |
| L | lockfile |
| Y | restyle by re-render |
| K | the lecturekit join with a study still |

The table describes the state after the milestones of section 5. Today, S and K hold on no manim8 rung.

| Rung | Typical wish | What the author or agent edits | Record | Gives up | Decides |
|---|---|---|---|---|---|
| R0 intent | "they should predict before the criterion moves" | the brief, the patterns, the PLAN clip row | spec, PLAN | nothing | lecturer; agent drafts |
| R1 comment | "too fast here", "the readout overlaps the curve" | feedback on a snapshot, a time or (proposed) an action | feedback, answering proposal, revision | nothing | agent applies; lecturer reviews |
| R2 feel | "every move in this clip lands hard" | per-clip motion overrides (proposed allowlist); deck-wide, a new style version | proposal; style version; README log | nothing | agent (clip), lecturer (deck) |
| R3 retime and stop | "pause before the point appears", "wait for a key" | times, lead-ins, snapshots, `stop`; proposed `after`, `with`, `link`, `mark` | proposal, revision, `stale` reason | nothing | agent for timing; lecturer for every stop, since a stop is a reveal |
| R4 restage | "dim the noise curve while the point moves" | registered objects, actions, patterns | as R3 | nothing; equation, data or mechanism changes are `touches_science` | agent proposes |
| R5 builder object | "the ROC drawn as the criterion moves" | `kind: custom` builder in `code/` with declared parameters (proposed) | builder proposal with diff, claims and tests (proposed) | T, Y partial unless the builder uses the public API | lecturer accepts the code |
| R6 builder motion | "a flat zoom onto one k-space line" | a `custom_action` returning a `Track` (proposed) | as R5 | C if the code adds time-based updaters | lecturer |
| R7 pinned scene | per-frame coupling no track can express | `code/pinned_<scene>.py` after `scianim pin` (proposed) | pin proposal, hashes | regeneration from YAML for that scene; T, M, Y, V partial | lecturer, with the list of losses read out |
| R8 kit scene | kit primitives, "a simulation in an afternoon" | `anim/clip_<name>.py` | record beside the script; README log | M, C, R, V, P, L; S only with kit `checkpoint()` | lecturer |
| R9 adopted clip | "I have an animation from elsewhere" | MP4, stops, licence in MANIFEST | record, MANIFEST row | everything except K and declared stops; restyle included | lecturer, licence included |

What the current code supports (verified):

- **R1.** The rule that answers feedback fires only on "too fast", "too quick" or "too slow"
  (`agent/feedback_proposals.py:229-231`), so "this sweep feels rushed" gets no proposal today. It also refuses
  rather than shifting later actions, and a feedback record cannot name an action.
- **R2.** A project may override only palette, charts, `transition_seconds`, `reveal_seconds` and alignment
  (`styles/resolve.py:29-36`). Scene-level overrides are dead code, and are not needed, because each clip is one
  project. `lk theme --manim8` carries no motion, so a bridged deck inherits a 0.5 s rest, not `tomas_scientific`'s
  1.0 s.
- **R3.** All times are absolute. `drop_impact` keeps its fall and impact in sync by hand.
- **R5.** Builders are called once, as objects (`generate.py:178-179`). They move only through registered actions,
  or through an undocumented, never-rendered route: a dummy data binding that makes `vary_parameter` accept them.
  Custom code escapes the proposal record entirely: proposals target only `animation.yaml` and `storyboard.yaml`
  (`proposals.py:18-25`), although `WORKFLOW_PLAN.md:88` says otherwise. No rendered custom example exists.
- **R6.** The bridge already has the right abstraction: a `Track` with `apply(fraction)`, played frame-exactly by
  `run_until` and split by checkpoints (`scene.py:113-143`, `:1439-1469`). No YAML names one.
- **R7.** Hand edits to the generated module render, and their hash enters the job key. But the next `codegen`
  overwrites them silently, and `stale` cannot see them.
- **R8.** Importing the kit sets Manim's global configuration (`nmstyle.py:47-49`). So kit primitives cannot be used
  inside a manim8 worker, and there is no path back up from R8 to R5.
- **Approval.** `lk clips` renders the working copy, not an approved revision (`clips.py:216`), which bypasses the
  skill's approval gate.

### 4.3 Moving up, and coming down

**Moving up.** The agent applies these rules and writes the result into the clip's record.

1. **Claim check first.** A wish that changes an equation, data, a source, the mechanism shown or the order of the
   argument is a `touches_science` proposal, whatever the rung. It waits for the lecturer.
2. **Lowest rung.** Classify the wish by the table and try it at the lowest rung that could express it. Pace,
   easing and rests stay at R1 to R3; a climb for them is refused.
3. **Evidence.** Climb only on one of three kinds:
   - a validator or registry refusal, quoted;
   - a fragile workaround, such as more than two absolute times kept in sync by hand, a dummy binding, or a
     stand-in model;
   - the same wish rejected in two review rounds.
4. **One rung per climb.** Skip a rung only when the refusal is structural: no object can move a camera, so a
   camera wish skips R5.
5. **The price, in three lines:**
   - *gives up*: the guarantees lost;
   - *needs sign-off on*: code, claims, stops;
   - *way back*: the revision to return to, and the need whose arrival would undo the climb.
6. **The lower version stays.** It remains renderable until the higher one is approved, and the record names the
   active producer.
7. **Gates are asked, not enforced.** They are asked for and recorded with the person's words, as ADR-042 already
   treats them.

**Coming down.** Every record above R4 lists its *needs* in manim8's vocabulary: a missing function, a planned
pattern, a missing kind. After a manim8 upgrade, the agent lists the clips whose needs are now met. For each, it
writes the lower-rung version, renders the same snapshot ids, and shows both through `scianim compare`. Identical
pixels are not expected; the lecturer approves.

**Promotion.** A builder moves twice:

1. From `code/` to the family's `components/` when a second clip in the family uses it. This needs family components
   hashed into revisions and job keys (proposed).
2. Into the registry when two lecture projects record the same *need*. Promote the need, not the builder. A
   promotion needs a parameter model, a bridge implementation and a registry bump (ADR-003), plus a recipe scene in
   manim8's examples (ADR-040). The expo scene that drove it is copied there as the recipe.

This makes the expo's "a builder that two projects need is promoted" (`PLAN.md:20-22`) operable. Two projects rarely
write the same builder; they do record the same need. The census of needs belongs in `lecturekit-expo/tools/`,
reading `scianim patterns list --json`. "At most one custom builder" becomes a CI warning: "at most one clip above
R4 per project".

### 4.4 What has to be built, in order

ADR numbers are assigned at merge. The log ends at ADR-042, and ADR-035 is reserved.

| Phase | What is built | Repository and ADR |
|---|---|---|
| 0 | The join (M6, M7): installable manim8, `render --json`, `lk clips` reading the real manifest, rendering the approved revision | manim8 ADR "What a consumer reads from a render"; dated CLIPS.md entries |
| 1 | The per-clip record `ladder.yaml`: `rung`, `producer`, `wish`, `evidence`, `gives_up`, `needs`, `way_back`, `decided_by`, `approved_revision`, `history` | lecturekit owns the schema, since there are three producers and manim8 is one of them |
| 1 | Custom code under proposals: `create_builder`, `revise_builder`, `pin_scene`, `promote_builder`, with diffs, claims and tests; family components hashed | manim8 ADR |
| 2 | Feedback that names an action; the agent classifies the lecturer's words into the rule's classes | manim8 ADR |
| 2 | Stops (section 3.2) | manim8 ADR |
| 2 | Relative times (`after`, `with`, `link`, `mark`), resolved to absolute seconds before codegen, so the bridge does not change. The pace rule can then shift what depends on an action, which delivers `PROJECT_SPEC.md:424` | manim8 ADR |
| 2 | Per-clip motion overrides through the project allowlist; `lk theme --manim8` writes a motion block | manim8 ADR amending ADR-028 and ADR-038 |
| 3 | The builder contract: declared `parameters` (replacing the dummy-binding route), a typed arguments model, a public `scianim_bridge.builder` API, `scianim builder check`, and the first rendered custom example | manim8 ADR |
| 3 | `custom_action`: a builder-supplied `Track` in YAML | manim8 ADR |
| 4 | Pinned scenes: codegen emits one method per storyboard scene, `pin` and `unpin`, codegen refuses to overwrite a pinned scene | manim8 ADR amending SKILL.md:94 |
| 4 | Kit `checkpoint()`; the kit importable without global configuration; a kit revision that hashes `kit.py`, the data and the lecturekit version | lecturekit |
| 5 | The needs check after an upgrade, the census, promotion | expo `tools/`, manim8 |

The approval gate interacts with restyling. A revision renders with its own frozen resolved style
(`render/jobs.py:104-108`). A dark preset therefore needs either a new approved revision per preset, or a manim8
change: "render a revision under another published style", recorded in the manifest and the cache key. The second
is proposed. Rendering a dark clip overwrites `<name>.mp4` today, because both presets read one `clips.json`, so
lecturekit also needs a per-preset index (`assets/clips/<mode>/`).

**Surfacing.**

- *manim8's SKILL.md* gains a section "When the person wants finer control": the table, the climb rule, the price
  in three lines, and "one rung per proposal".
- *lecturekit's CLIPS.md* gains "More control over a clip", with the same rung names for every producer.
- *The PLAN clips table* carries the rung.
- *`lk clips`* prints one line per clip with its rung, stops and needs.
- *The expo gallery* shows the rung.

### 4.5 Worked example: the signal-detection slide

The expo device is "a criterion that slides on a keypress; the ROC drawn as it moves". The project is a skeleton, so
every step is proposed. Validation results marked verified were run against `scianim_core`.

**R0.**

- *Claims.* Equal-variance Gaussian signal detection (Macmillan and Creelman 2005, chapter 1; the lecturer confirms
  the locator). d′ = 1.5, labelled illustrative. F = 1 − Φ(c), H = 1 − Φ(c − d′).
- *Patterns.* `linked_views` and `sweep_with_readout`, both available.
- *One clip.* The two hyphenated clips in `expo.yaml` become one, `criterion_roc`, because linked views need one
  clock. That is the lecturer's call.

**R3 and R4: the criterion.** This part validates today (verified).

- A `function_plot` with two `exp` series and a marker at `x: c`, which follows a `vary_parameter` on c.
- Two sweeps, each with a lead-in and a rest.
- Snapshots `liberal`, `neutral` and `conservative`.

The stops follow section 3: `start=key stops="neutral"`. The room predicts before the first sweep and again at
neutral. A stop at the clip's start or end is refused, because the key start and the end hold already cover those
moments. Two prompts at about a minute each set `time=`.

**The ROC: the evidence at R4.**

| Option | Result |
|---|---|
| (a) exact ROC | refused. Φ is not callable: the enforced expression whitelist (`expressions.py:14-29`) has no `erf` (verified) |
| (b) logistic stand-in | validates (verified). At the same c it is within 0.0095 per coordinate; as a curve it departs by up to 0.090, at F ≈ 0.011. It is a different model drawn under a Gaussian claim, so it is `touches_science` and is declined |
| (c) exact zROC (`x + d`, marker at `−c`) | validates (verified). But it changes the representation the slide argues from |
| (d) exact static ROC from a CSV written by the deck's simulation, bound to a `scientific_plot` | keeps T and Y. But no point moves with c, because only `scale` and `smooth` transforms accept a parameter |
| (e) "drawn as it moves" | needs a stroke-drawing reveal driven by a parameter, an open gap (`IMPLEMENTATION_PLAN.md:243-244`). The planned `trace_the_path` is a fading trail, which is something else |

**The priced choice.**

| Option | Gives up | Sign-off on | Way back |
|---|---|---|---|
| R4 with (c) or (d) | the familiar curve, or the moving point | the representation | none needed |
| R5 builder `roc_trace` | T, Y partial | the code and the F and H claims | the R3 revision; needs `ncdf`, `parametric_reveal` |
| wait for manim8 | nothing | nothing | blocked until a release exists (I1) |

**R5, if chosen.** A `create_builder` proposal for `code/roc_trace.py`, marked `touches_science`. It draws the
curve from the start value of c to the current c, and a dot at (1 − Φ(c), 1 − Φ(c − d′)) computed with
`math.erf`. Its tests pin three points:

- c = −0.5 gives (0.6915, 0.9772);
- c = 0.75 gives (0.2266, 0.7734);
- c = 2.0 gives (0.0228, 0.3085).

Two further tests check purity, and check that the builder's d′ equals the plot's. `rebuild` is a pure function of
c and adds no updater, so checkpoints stay exact and the stops remain valid.

**Review.** The lecturer says "the move to conservative feels rushed". Today no rule answers it. With feedback that
names `to_conservative` and the agent's classification, the pace rule lengthens the sweep from 3 s to 3.75 s. With
relative timing, the linked ROC sweep and the stop follow. The wish stays at R1 to R3.

**Coming down.** When drift diffusion's moving bound records the same `parametric_reveal` need, the census shows two
projects. manim8 then promotes a parameter-driven reveal, with the signal-detection scene copied in as its recipe.
The clip's history reads R0, R3, R5, R4.

## 5. Roadmap

M1 to M5 need no manim8 and can start now. M6 is the only cross-repository blocker, and it starts with a
maintainer's decision: publish wheels, or pin by git.

| M | Repo; needs | Work | Acceptance | Closes |
|---|---|---|---|---|
| M1 | lecturekit | `pandoc.json.null` treated as nil, no nulls written; filter errors fail `lk build`; `QUARTO_PYTHON`; frags check inverted | an index with `"still": null` builds; a `clip=` movie without a still makes `lk build` exit 1; `.venv/bin/lk build` passes with the venv off PATH | I5, I19, I20 |
| M2 | lecturekit; M1 | event-driven guard; keys through `Reveal.configure` (Space, R, T; P is previous); clips load in the main window only; notes re-post; Range-capable review server; barcode clip; Playwright CI pinned to Quarto 1.11.9 | features form 6 and a plain clip: no hidden playback forward, backward or on a jump; R replays with Scroll View off; Space in the speaker window pauses; all over Range, no-Range and `file://` | I9, I10, part of I11 |
| M3 | lecturekit; M1 | slug names with alias; `format: 2` writer (decoded frames, pts, sha256, poster at frame 0, stills by frame, pixel rests, faststart); `lk clips adopt`; kit `checkpoint()`; per-clip errors and incremental saves; keyframes kept on `--crop` and `--size` | adopt's stills equal ffmpeg's frame `K`; a crop keeps a keyframe per checkpoint and the frame count; one failing kit scene leaves the others indexed | I13; kit halves of I8, I14 |
| M4 | lecturekit; M2, M3 | `stops=`, `start=`, `.stop`, `study=`, `still=`; cue emission and fatal checks; the segmented runtime; `\lkstrip`; notes in POLICY order; `CLIP>TIME`; frags per stop; features forms 2 to 7, 9, 10; docs; tutorial | the prototype's 52 checks on three servers; study panels at least 18 mm high; each fatal case fails the build | section 3 for kit and adopted clips |
| M5 | lecturekit; M3 | templates (Clips table with rung, What moves, FACTS clip table, ENGAGEMENT, MANIFEST); `lk new --budget`; `.gitignore`; `vendor_extension` and symlinks; kickoff wiring and `bar_bold()`; `lk review clips` and `lk review data`; tutorials 03 to 06 | `lk new --budget 20` reports 20; `lk review clips examples/kickoff --strict` passes; `bar-bold.tex` regenerates byte for byte | I18, I21, I22 (tutorial 05), I24; section 2 |
| M6 | manim8 | code on `main` and a tag; release-mode family environments that resolve the bridge and core; `render --json` for fresh and cached jobs | in a fresh container with only uv: install at the tag, init, sync, render `divisive_normalization` twice with `--json`: an 18.0 s movie both times, the second a cache hit | I2; manim8 halves of I1, I3 |
| M7 | lecturekit; M3, M6 | extra pinned to the tag on Python 3.12; `lk clips` runs sync and codegen, renders the approved revision, reads `--json`, copies `result.videos[0]`, extracts and cross-checks stills, takes candidates from `reached`; valid bridged style, written into `animation.yaml` by proposal; `neutral` and `*_soft` mapped; bundled fonts through fontconfig; docs; a CI render; features form 8 | features two-scene clip: index sha256 equals the manifest's, full duration, `rev_NNNN`, each checkpoint frame within mean difference 1.0 of its PNG; `scianim validate` gives 0 errors on every bridged brand | I1, I3, I4, I6, I7 (one mode), I8, I14 to I16, I22 |
| M8 | manim8; M6 | stops ADR: fields, validation, `frame_index`, `result.stops`, fingerprint exclusion, orbit split proposal | `divisive_normalization` with two stops: a keyframe at each stop and `frame_index == round(t*fps)`; `gabor_filter` fails until its orbit is split; flipping `stop` leaves fingerprints unchanged | section 3.2 (manim8) |
| M9 | expo; M5, M7 | pins by SHA; template regenerated; slug names and registered kinds; clips CI job without `\|\| true`; full-version check plus a scheduled build against the engine heads; the divisive-normalization clips with the equation signed off; reel | a clean runner renders, reviews strictly and builds; a filter change pushed without a version bump is reported | I11, I12, I17, I21, I23, I24 (expo) |
| M10 | all; M4, M8, M9 | render a revision under another style (manim8); per-preset index (lecturekit); signal-detection at R3 in paper and dark | frags holds exact frames at start, neutral and end in both presets | I7 per preset; I23 dark |
| M11 | manim8; M8 | feedback naming an action; relative times and marks; per-clip motion; `lk theme --manim8` writes motion | "feels rushed" on `to_conservative` yields 3 s to 3.75 s with the linked sweep and stop shifted | section 4, phase 2 |
| M12 | manim8, then expo; M11 | custom code under proposals; builder contract and check; first rendered custom recipe; signal-detection at R5 with `ladder.yaml`; needs census | the `roc_trace` tests pass; `scianim compare` shows R3 against R5; the census lists `parametric_reveal` | section 4, phases 1 and 3 |

Later work, not yet milestones: `custom_action`, pinned scenes, using the kit inside builders, and automated
promotion.

## 6. Decisions for the lecturer

1. **How manim8 is distributed.** Publish the three wheels, or pin by git SHA with subdirectory sources. Until this
   is decided, every manim8 step waits.
2. **manim8's scope.** Does manim8 take stops, relative timing and marks into its contract, given
   PROJECT_SPEC.md:1086 ("not slide decks or narrated lectures")? The design keeps each clip one movie, but the
   field exists for a presenter.
3. **Who owns stops and stills.** The deck owns the choice (proposed), so manim8 gets no `study` field.
4. **Who may add a stop.** A stop is a reveal: propose and wait (proposed), or a timing change the agent may apply.
5. **Segmented playback.** The proposals, and their alternatives:
   - a key pressed mid-part plays through to the coming stop, rather than cutting to it;
   - Space advances at an intermediate hold and does nothing at the final hold;
   - the default start is `auto`;
   - the default study output is `strip`, capped at five stops;
   - an orbit across a stop is an error unless waived;
   - R is taken from Quarto's Scroll View deck-wide, P returns to "previous", and the pacing reset moves to T.
6. **The ladder record** lives in lecturekit (proposed), with the same schema for all three producers.
7. **Per-clip motion.** Which motion tokens may a project override, and does a bridged deck inherit a 0.5 s or a
   1.0 s rest?
8. **Expression functions.** Does manim8's expression whitelist gain special functions such as `ncdf`? This decides
   whether signal detection needs a builder at all.
9. **Custom actions and pinned scenes.** Do they enter manim8, or does "never edit generated code" stay absolute?
10. **Dark clips.** Render a revision under another published style, or approve a second revision per preset.
11. **The kickoff.** Whether the two bullets beside the clip move to study-only. Whether slide 1 gains the
    `prf_tuning` clip before `bar_bold`. Whether `s01.json` is regenerated with prfmodel 0.2.0, or the notes
    change.
12. **The expo.**
    - Divisive normalization's equation change.
    - Signal detection as one clip or two, the value of d′ and its locator, the stops, and ROC or zROC.
    - Whether R8 and R9 clips are allowed in the gallery.
